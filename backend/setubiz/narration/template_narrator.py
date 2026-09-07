"""Template narrator — the default, and the offline fallback lane (PLAN.md §4, §10).

Jinja over the facts object. It cannot hallucinate because it cannot invent: every placeholder
resolves against `facts.numeric_index`. It is still put through the validator, and the test suite
asserts it always passes — that is what makes the catch-rate metric meaningful for the LLM lane.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

from setubiz.facts.builder import Facts
from setubiz.money import format_inr, format_lakh
from setubiz.narration.base import Report, ReportSection
from setubiz.schemas import Language

TEMPLATE_FILE = Path(__file__).resolve().parent / "templates" / "report_sections.yaml"


class _Numbers(dict):
    """Attribute access over the facts numeric index, with a clear error on a missing key."""

    def __getattr__(self, key: str) -> Decimal:
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(
                f"report template referenced {key!r}, which is not in facts.numeric_index — "
                "add it to the facts object rather than computing it in a template"
            ) from exc


@lru_cache
def _document() -> dict[str, Any]:
    return yaml.safe_load(TEMPLATE_FILE.read_text(encoding="utf-8"))


@lru_cache
def _environment() -> Environment:
    env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.globals["fmt"] = format_inr
    env.globals["lakh"] = format_lakh
    return env


def _context(facts: Facts, language: Language) -> dict[str, Any]:
    reasons = _document()["binding_reason"][facts.right_sizing.binding.value]
    return {
        "facts": facts,
        "n": _Numbers(facts.numeric_index),
        "v": facts.village,
        "tpl": facts.template,
        "scheme": facts.scheme,
        "rs": facts.right_sizing,
        "rec": facts.right_sizing.recommended_loan,
        "lang": language.value,
        "binding_reason_en": reasons["en"],
        "binding_reason_hi": reasons["hi"],
    }


def _chart_data(facts: Facts) -> dict[str, dict[str, Any]]:
    """Structured payloads the UI charts read. Same numbers, never re-derived on the client."""
    rs = facts.right_sizing
    seasonality = facts.threats.seasonality
    return {
        "loan_structure": {
            "max_loan": rs.max_loan,
            "recommended_loan": rs.recommended_loan,
            "headroom": rs.headroom,
            "required_capital": rs.required_capital,
            "debt_need": rs.debt_need,
            "binding": rs.binding.value,
            "dscr_threshold": rs.dscr_threshold,
        },
        "stress": {
            "dscr_threshold": rs.dscr_threshold,
            "stress_floor": rs.stress_floor,
            "max_loan": [
                {"year": r.year, "dscr": r.dscr, "debt_service": r.debt_service}
                for r in rs.max_loan_dscr
            ],
            "recommended": [
                {"year": r.year, "dscr": r.dscr, "debt_service": r.debt_service}
                for r in rs.recommended_dscr
            ],
            "scenarios": [
                {
                    "label": s.label,
                    "min_dscr": s.min_dscr,
                    "passes": s.passes,
                    "series": [{"year": r.year, "dscr": r.dscr} for r in s.by_year],
                }
                for s in rs.recommended_stress
            ],
        },
        "repayment": {
            "mode": rs.mode.value,
            "recommended": [
                r.__dict__
                for r in (
                    facts.amortization_recommended.schedule
                    if facts.amortization_recommended
                    else ()
                )
            ],
            "alternate_mode": (
                facts.amortization_alternate_mode.mode.value
                if facts.amortization_alternate_mode
                else None
            ),
            "alternate_instalment": (
                facts.amortization_alternate_mode.instalment
                if facts.amortization_alternate_mode
                else None
            ),
        },
        "market_reach": {
            "villages": [
                {
                    "name": n.village.name,
                    "name_hi": n.village.name_hi,
                    "distance_km": n.distance_km,
                    "households_2011": n.village.households_2011,
                    "lat": n.village.lat,
                    "lon": n.village.lon,
                }
                for n in facts.market.neighbours
            ],
            "income_segments": [
                {"label": s.label, "share": s.share, "households": s.households}
                for s in facts.market.income_segments
            ],
        },
        "competition": {
            "band": facts.competitors.band.model_dump(),
            "observed_osm": facts.competitors.osm_observed,
            "z_score": facts.competitors.z_score,
            "estimator": facts.competitors.method,
        },
        "stress_seasonality": (
            {
                "commodity": seasonality.commodity,
                "market": seasonality.market,
                "months": list(seasonality.months),
                "arrivals": list(seasonality.arrivals),
                "modal_price": list(seasonality.modal_price),
                "cv": seasonality.coefficient_of_variation,
                "peak_month": seasonality.peak_month,
                "trough_month": seasonality.trough_month,
            }
            if seasonality
            else {}
        ),
    }


class TemplateNarrator:
    name = "template"

    def narrate(self, facts: Facts, language: Language = Language.EN) -> Report:
        env = _environment()
        context = _context(facts, language)
        charts = _chart_data(facts)
        suffix = language.value

        sections: list[ReportSection] = []
        for spec in _document()["sections"]:
            body = env.from_string(spec[f"body_{suffix}"]).render(**context)
            sections.append(
                ReportSection(
                    id=spec["id"],
                    heading=spec[f"heading_{suffix}"],
                    body=" ".join(body.split()),
                    cites=tuple(spec.get("cites", ())),
                    data=charts.get(spec["id"], {}),
                )
            )

        sections.append(_swot_section(facts, language))
        sections.append(_threats_section(facts, language))
        return Report(language=language, narrator=self.name, sections=tuple(sections))


def _swot_section(facts: Facts, language: Language) -> ReportSection:
    en = language is Language.EN
    quadrants = {
        q: [i.text_en if en else i.text_hi for i in facts.swot.by_quadrant(q)]
        for q in ("strength", "weakness", "opportunity", "threat")
    }
    body = " ".join(line for lines in quadrants.values() for line in lines)
    return ReportSection(
        id="swot",
        heading="Strengths, weaknesses, opportunities and threats"
        if en
        else "ताकत, कमजोरी, अवसर एवं जोखिम",
        body=body,
        cites=tuple(dict.fromkeys(c for i in facts.swot.items for c in i.cites)),
        data={"quadrants": quadrants, "rules_fired": [i.id for i in facts.swot.items]},
    )


def _threats_section(facts: Facts, language: Language) -> ReportSection:
    en = language is Language.EN
    items = [
        {"id": t.id, "severity": t.severity, "text": t.text_en if en else t.text_hi}
        for t in facts.threats.threats
    ]
    return ReportSection(
        id="threats",
        heading="Risks to watch" if en else "ध्यान देने योग्य जोखिम",
        body=" ".join(i["text"] for i in items),
        cites=facts.threats.sources,
        data={
            "items": items,
            "price_band": facts.threats.price_band.model_dump()
            if facts.threats.price_band
            else None,
            "seasonality": _chart_data(facts)["stress_seasonality"],
        },
    )

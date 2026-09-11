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
        # Engine advisories about the competitor estimate itself. These fire when a block has no
        # Economic Census row for the category, which real data does hit -- and a band of 0-0
        # presented without that caveat reads as "no competition here", the opposite of what it
        # means. Rendering them is what keeps the band honest.
        "competitor_notes": tuple(
            n.text_en if language is Language.EN else n.text_hi for n in facts.competitors.notes
        ),
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

        sections.append(_alternatives_section(facts, language))
        sections.append(_swot_section(facts, language))
        sections.append(_threats_section(facts, language))
        return Report(language=language, narrator=self.name, sections=tuple(sections))


def _plural(count: int, word: str) -> str:
    """English pluralisation for the one section that counts things in prose.

    Hindi does not take an English plural, so the Hindi branches never call this.
    """
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _alternatives_section(facts: Facts, language: Language) -> ReportSection:
    """Sizes of the same business that do work.

    Built programmatically rather than from a Jinja template because the number of rows varies
    and because the honest empty case carries bilingual advisories the engine already wrote.
    """
    en = language is Language.EN
    alt = facts.alternatives
    label = alt.unit_label if en else (alt.unit_label_hi or alt.unit_label)

    rows = [
        {
            "units": c.units,
            "project_cost": c.project_cost,
            "loan": c.loan,
            "instalment": c.instalment,
            "min_dscr": c.min_dscr,
            "comfort": c.comfort,
            "self_financed": c.self_financed,
        }
        for c in alt.configurations
    ]

    if rows:
        lead = (
            (
                "One size of this business clears the appraisal norm and is fully funded by "
                "your savings plus the loan it supports."
                if len(rows) == 1
                else f"{len(rows)} sizes of this business clear the appraisal norm and are "
                f"fully funded by your savings plus the loan they support."
            )
            if en
            else f"इस व्यवसाय के {len(rows)} आकार ऐसे हैं जो मानक भी पूरा करते हैं और आपकी बचत "
            f"एवं ऋण से पूरी तरह वित्तपोषित भी हो जाते हैं।"
        )
        parts = [lead]
        for c in alt.configurations:
            if c.self_financed:
                parts.append(
                    f"{_plural(c.units, label)}: {format_inr(c.project_cost)}, no borrowing needed."
                    if en
                    else f"{c.units} {label}: {format_inr(c.project_cost)}, ऋण की आवश्यकता नहीं।"
                )
            else:
                parts.append(
                    f"{_plural(c.units, label)}: {format_inr(c.project_cost)}, borrow "
                    f"{format_inr(c.loan)}, {format_inr(c.instalment)} a quarter."
                    if en
                    else f"{c.units} {label}: {format_inr(c.project_cost)}, ऋण "
                    f"{format_inr(c.loan)}, प्रति तिमाही {format_inr(c.instalment)}।"
                )
    else:
        parts = [a.text_en if en else a.text_hi for a in alt.why_not]

    phased = None
    if alt.phased is not None:
        p = alt.phased
        phased = {
            "start_units": p.start_units,
            "target_units": p.target_units,
            "expansion_cost": p.expansion_cost,
            "annual_retained": p.annual_retained,
            "years_to_expand": p.years_to_expand,
        }
        parts.append(
            f"You could start at {_plural(p.start_units, label)} and reach "
            f"{_plural(p.target_units, label)} in about {_plural(p.years_to_expand, 'year')} "
            f"from what the business retains, without a second loan."
            if en
            else f"आप {p.start_units} {label} से शुरू करके लगभग {p.years_to_expand} वर्ष में "
            f"{p.target_units} तक पहुँच सकते हैं, बिना दूसरा ऋण लिए।"
        )

    return ReportSection(
        id="alternatives",
        heading="Sizes that work" if en else "जो आकार चल सकते हैं",
        body=" ".join(parts),
        cites=alt.sources,
        data={
            "unit_label": label,
            "configurations": rows,
            "considered": [
                {
                    "units": c.units,
                    "project_cost": c.project_cost,
                    "shortfall": c.shortfall,
                    "funded": c.funded,
                }
                for c in alt.considered
            ],
            "closest_units": alt.closest.units if alt.closest else None,
            "additional_margin_needed": alt.additional_margin_needed,
            "phased": phased,
        },
    )


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

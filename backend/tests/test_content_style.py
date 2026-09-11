"""House style for user-visible copy.

The em dash reads as an "AI-written" tell, and SIH evaluators actively penalise AI slop
(PLAN.md §0.8). Every string a beneficiary, a VLE operator or a judge reads on screen must be
free of it. Code comments and docstrings are out of scope; so are en dashes in numeric ranges
("8-16 enterprises") and the missing-value placeholder, which are typographically correct.

The file list is explicit on purpose: adding a new source of user-visible copy should be a
deliberate act that includes adding it here.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from setubiz.config import SAMPLE_DATA_DIR
from setubiz.eligibility import SocialCategory, assess
from setubiz.facts import build_facts
from setubiz.facts.provenance import SOURCES
from setubiz.finance.cost_templates import list_templates
from setubiz.narration import narrate
from setubiz.narration.template_narrator import TEMPLATE_FILE
from setubiz.schemas import AdvisoryRequest, Language

EM_DASH = "—"

#: Content files whose every line is read by a user.
CONTENT_FILES = [
    TEMPLATE_FILE,
    SAMPLE_DATA_DIR / "swot_rules.yaml",
    SAMPLE_DATA_DIR / "schemes" / "comparison.yaml",
    SAMPLE_DATA_DIR / "schemes" / "corporations.yaml",
    SAMPLE_DATA_DIR / "schemes" / "sca_directory.yaml",
    SAMPLE_DATA_DIR / "schemes" / "stacking.yaml",
    SAMPLE_DATA_DIR / "schemes" / "shg_routing.yaml",
    *sorted((SAMPLE_DATA_DIR / "cost_templates").glob("*.yaml")),
]

FRONTEND_STRINGS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "format.ts"


@pytest.mark.parametrize("path", CONTENT_FILES, ids=lambda p: p.name)
def test_content_files_have_no_em_dash(path: Path):
    text = path.read_text(encoding="utf-8")
    offenders = [
        f"{path.name}:{i}: {line.strip()}"
        for i, line in enumerate(text.splitlines(), 1)
        if EM_DASH in line
    ]
    assert not offenders, "em dash in user-visible copy:\n" + "\n".join(offenders)


def test_sample_data_notes_have_no_em_dash():
    for path in sorted(SAMPLE_DATA_DIR.glob("*.json")):
        note = json.loads(path.read_text(encoding="utf-8")).get("_meta", {}).get("note", "")
        assert EM_DASH not in note, path.name


def test_frontend_ui_strings_have_no_em_dash():
    """The three `'—'` missing-value placeholders are allowed; prose is not."""
    prose = [
        line
        for line in FRONTEND_STRINGS.read_text(encoding="utf-8").splitlines()
        if EM_DASH in line and "'—'" not in line and not line.strip().startswith(("*", "/*"))
    ]
    assert not prose, "em dash in frontend copy:\n" + "\n".join(prose)


def test_cost_template_labels_have_no_em_dash():
    for tpl in list_templates():
        fields = [tpl.name, tpl.name_hi or "", tpl.unit, tpl.source, *tpl.assumptions]
        for group in (tpl.fixed_capital, tpl.monthly_revenue, tpl.monthly_opex):
            fields += [li.item for li in group]
        for value in fields:
            assert EM_DASH not in value, f"{tpl.id}: {value}"


def test_source_titles_have_no_em_dash():
    for source in SOURCES.values():
        assert EM_DASH not in source.title, source.id
        assert EM_DASH not in (source.note or ""), source.id


def test_eligibility_text_has_no_em_dash():
    result = assess(
        SocialCategory.SC,
        Decimal("280000"),
        state="Jharkhand",
        activity_category="dairy",
        is_woman=True,
        has_prior_experience=False,
    )
    for line in (*result.reasons, *result.conditions, *(d.en for d in result.documents)):
        assert EM_DASH not in line, line


@pytest.mark.parametrize("category", ["dairy", "kirana", "tailoring", "poultry", "flour_mill"])
@pytest.mark.parametrize("language", [Language.EN, Language.HI])
def test_rendered_report_has_no_em_dash(category: str, language: Language):
    """The end-to-end check: whatever a user actually reads on screen."""
    facts = build_facts(
        AdvisoryRequest(
            village_query="Ratu",
            savings=Decimal("100000"),
            business_category=category,
            social_category="sc",
            annual_family_income=Decimal("280000"),
        )
    )
    result = narrate(facts, language, use_llm=False)

    for section in result.report.sections:
        assert EM_DASH not in section.heading, section.id
        assert EM_DASH not in section.body, f"{section.id}: {section.body}"
    for warning in facts.warnings:
        assert EM_DASH not in warning.text(language), warning.id
    for item in facts.swot.items:
        assert EM_DASH not in (item.text_en if language is Language.EN else item.text_hi), item.id
    for threat in facts.threats.threats:
        assert EM_DASH not in (threat.text_en if language is Language.EN else threat.text_hi)


def test_an_out_of_scope_margin_also_renders_clean():
    """A margin above ₹5,00,001 leaves the NSFDC envelope and takes its own copy path."""
    facts = build_facts(
        AdvisoryRequest(village_query="Ratu", savings=Decimal("600000"), business_category="dairy")
    )
    result = narrate(facts, Language.EN, use_llm=False)
    for section in result.report.sections:
        assert EM_DASH not in section.body, section.id
    for warning in facts.warnings:
        assert EM_DASH not in warning.text_en, warning.id
        assert EM_DASH not in warning.text_hi, warning.id

"""Numeric grounding — the anti-hallucination claim, under test (PLAN.md §3, §9)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from setubiz.facts import build_facts
from setubiz.narration import narrate
from setubiz.narration.pipeline import CATCH_RATE
from setubiz.narration.template_narrator import TemplateNarrator
from setubiz.narration.validator import (
    CatchRate,
    NumericGroundingValidator,
    ValidationReport,
    extract_numbers,
)
from setubiz.schemas import AdvisoryRequest, Language


@pytest.fixture
def facts():
    return build_facts(
        AdvisoryRequest(
            village_query="Ormanji",
            savings=Decimal("100000"),
            business_category="dairy",
            social_category="sc",
            annual_family_income=Decimal("280000"),
        )
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("₹9,00,000", Decimal("900000")),
        ("1,00,000 rupees", Decimal("100000")),
        ("44,729.31 a quarter", Decimal("44729.31")),
        ("8.0%", Decimal("8.0")),
        ("₹9.00 L", Decimal("900000")),
        ("1.25 Cr", Decimal("12500000")),
        ("2 lakh", Decimal("200000")),
        ("2810", Decimal("2810")),
    ],
)
def test_number_extraction_understands_indian_notation(text, expected):
    assert extract_numbers(text)[0].value == expected


@pytest.mark.parametrize(
    ("text", "resolution"),
    [("44,729", Decimal("1")), ("44,729.31", Decimal("0.01")), ("₹14.33 L", Decimal("1000"))],
)
def test_resolution_follows_how_precisely_the_figure_was_written(text, resolution):
    assert extract_numbers(text)[0].resolution == resolution


def test_extraction_ignores_prose_without_figures():
    assert extract_numbers("no numbers at all here") == []


@pytest.mark.parametrize(
    "category",
    [
        "dairy",
        "kirana",
        "tailoring",
        "poultry",
        "flour_mill",
        "tea_stall",
        "vegetable_vendor",
        "beauty_parlour",
    ],
)
@pytest.mark.parametrize("language", [Language.EN, Language.HI])
def test_template_narration_is_always_fully_grounded(category, language):
    facts = build_facts(
        AdvisoryRequest(
            village_query="Ratu",
            savings=Decimal("100000"),
            business_category=category,
            social_category="sc",
            annual_family_income=Decimal("280000"),
        )
    )
    report = TemplateNarrator().narrate(facts, language)
    result = NumericGroundingValidator().validate(report.prose, facts)
    assert result.passed, [(u.text, str(u.value)) for u in result.ungrounded]
    assert result.checked > 20
    assert result.grounded == result.checked


def test_an_invented_figure_is_caught(facts):
    validator = NumericGroundingValidator()
    good = "The recommended loan is ₹2,05,000."
    bad = "The recommended loan is ₹2,05,000, and 8,421 shops already sell milk here."

    assert validator.validate(good, facts).passed is True
    caught = validator.validate(bad, facts)
    assert caught.passed is False
    assert [u.value for u in caught.ungrounded] == [Decimal("8421")]
    assert "8,421" in caught.ungrounded[0].context


def test_a_plausible_but_wrong_restatement_is_caught(facts):
    """The dangerous case: a real-looking number that the engine never produced."""
    validator = NumericGroundingValidator()
    wrong = "At the maximum loan the quarterly instalment is ₹41,250."
    assert validator.validate(wrong, facts).passed is False


def test_rounding_within_tolerance_is_accepted(facts):
    validator = NumericGroundingValidator()
    exact = facts.numeric_index["quarterly_instalment_max"]  # 44729.31
    assert validator.validate(f"about ₹{int(exact):,}", facts).passed is True


def test_structural_percentages_are_permitted(facts):
    validator = NumericGroundingValidator()
    text = "The scheme funds 90% of the project against a 10% promoter contribution."
    assert validator.validate(text, facts).passed is True


def test_catch_rate_counter():
    counter = CatchRate()
    assert counter.rate == 0.0
    counter.record(ValidationReport(passed=True, checked=5))
    counter.record(ValidationReport(passed=False, checked=5))
    assert counter.generations == 2
    assert counter.rejections == 1
    assert counter.rate == 0.5
    assert counter.as_dict()["catch_rate"] == 0.5


def test_narrate_records_the_catch_rate_and_defaults_to_templates(facts):
    before = CATCH_RATE.generations
    result = narrate(facts, Language.EN, use_llm=False)
    assert result.report.narrator == "template"
    assert result.validation.passed is True
    assert CATCH_RATE.generations == before + 1


def test_llm_lane_is_off_unless_explicitly_enabled():
    from setubiz.narration.llm_narrator import LlmNarrator

    assert LlmNarrator.available() is False  # SETUBIZ_LLM_ENABLED is not set in tests


def test_llm_narrator_falls_back_to_the_template_report(facts):
    from setubiz.narration.llm_narrator import LlmNarrator

    report = LlmNarrator().narrate(facts, Language.EN)
    assert report.narrator == "template"  # unavailable -> deterministic draft is returned as-is

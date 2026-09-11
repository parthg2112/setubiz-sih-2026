"""Scheme stacking — saying "check this" is cheap, saying "yes" wrongly is not.

The asymmetry is the whole design: a `combinable` verdict cannot be constructed without a source,
while `needs_verification` is free. Wrongly telling an applicant two schemes stack makes them
build a project cost around assistance that never arrives.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from setubiz.config import get_settings
from setubiz.eligibility import SocialCategory, assess
from setubiz.eligibility.stacking import (
    StackingRule,
    StackVerdict,
    combinations,
    stacking_rules,
)
from setubiz.finance import route
from setubiz.finance.router import SchemeLogic


def test_a_combinable_verdict_cannot_exist_without_a_source():
    """The one rule that makes the rest of this engine trustworthy."""
    with pytest.raises(ValidationError, match="needs a source"):
        StackingRule(
            schemes=("nsfdc_term_loan", "pmegp"),
            verdict=StackVerdict.COMBINABLE,
            reason_en="They stack.",
            reason_hi="ये साथ मिलती हैं।",
        )
    # The same rule with a source is fine.
    ok = StackingRule(
        schemes=("nsfdc_term_loan", "pmegp"),
        verdict=StackVerdict.COMBINABLE,
        reason_en="They stack.",
        reason_hi="ये साथ मिलती हैं।",
        source="https://example.gov.in/order.pdf",
    )
    assert ok.verdict is StackVerdict.COMBINABLE


def test_needs_verification_is_the_default_and_needs_no_source():
    rule = StackingRule(
        schemes=("nsfdc_term_loan", "pmmy"),
        reason_en="Confirm at the district office.",
        reason_hi="जिला कार्यालय से पुष्टि करें।",
    )
    assert rule.verdict is StackVerdict.NEEDS_VERIFICATION
    assert rule.source is None


def test_a_rule_needs_two_schemes_to_be_about_anything():
    with pytest.raises(ValidationError, match="at least two schemes"):
        StackingRule(schemes=("pmegp",), reason_en="x", reason_hi="y")


def test_shipped_rules_are_bilingual_and_never_claim_more_than_they_can_source():
    rules = stacking_rules()
    assert rules, "no stacking rules loaded"
    for rule in rules:
        assert rule.reason_en and rule.reason_hi, f"{rule.key}: missing a language"
        assert len(rule.schemes) >= 2
        if rule.verdict is StackVerdict.COMBINABLE:
            assert rule.source, f"{rule.key}: combinable without a source"
        # No subsidy arithmetic ships until someone produces a citable rate.
        assert rule.subsidy_delta_pct is None


def test_pairs_are_found_regardless_of_the_order_they_are_written_in():
    eligibility = assess(SocialCategory.SC, 450000, state="Jharkhand")
    result = combinations(eligibility, "nsfdc_term_loan")
    pairs = {frozenset(c.schemes) for c in result.needs_verification}
    assert frozenset(("nsfdc_term_loan", "pmegp")) in pairs
    assert frozenset(("nsfdc_term_loan", "cgtmse")) in pairs


def test_the_demo_persona_is_told_what_to_confirm_rather_than_a_guess():
    eligibility = assess(SocialCategory.SC, 280000, state="Jharkhand")
    result = combinations(eligibility, "nsfdc_term_loan")
    assert result.any_combination is True
    # Nothing is claimed as combinable while no rule carries a source.
    assert result.combinable == ()
    assert result.needs_verification
    assert all(c.subsidy_delta_pct is None for c in result.needs_verification)
    assert all(c.reason_en and c.reason_hi for c in result.needs_verification)


def test_a_micro_finance_applicant_gets_the_micro_finance_pairs():
    """Logic A and Logic B are different schemes and do not share a rule set."""
    eligibility = assess(SocialCategory.SC, 200000, state="Jharkhand")
    result = combinations(eligibility, "nsfdc_micro_finance")
    pairs = {frozenset(c.schemes) for c in result.needs_verification}
    assert frozenset(("nsfdc_micro_finance", "dri")) in pairs
    # The term loan's pairs must not leak into a micro finance report.
    assert frozenset(("nsfdc_term_loan", "pmegp")) not in pairs


def test_an_out_of_scope_applicant_has_no_routed_scheme_to_stack_against():
    eligibility = assess(SocialCategory.SC, 280000, state="Jharkhand")
    result = combinations(eligibility, None)
    assert result.any_combination is False
    assert result.considered == ()


def test_an_unknown_pair_is_simply_absent_rather_than_invented():
    """A scheme with no rule written for it produces silence, not a guess."""
    eligibility = assess(SocialCategory.SC, 280000, state="Jharkhand")
    result = combinations(eligibility, "some_scheme_nobody_has_written_rules_for")
    assert result.combinable == ()
    assert result.needs_verification == ()
    assert result.mutually_exclusive == ()
    # The anchor is still reported as considered, so the report can say what was looked at.
    assert result.considered[0] == "some_scheme_nobody_has_written_rules_for"


def test_a_data_directory_without_stacking_rules_degrades_to_silence(tmp_path, monkeypatch):
    """A custom SETUBIZ_DATA_DIR with no stacking.yaml must say nothing, not crash.

    Silence is the correct behaviour here: no rules means no claims about what combines, which is
    exactly the conservative answer.
    """
    import setubiz.eligibility.stacking as mod

    (tmp_path / "schemes").mkdir()
    monkeypatch.setenv("SETUBIZ_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    mod._rules_doc.cache_clear()
    mod.stacking_rules.cache_clear()
    try:
        assert mod.stacking_rules() == ()
    finally:
        get_settings.cache_clear()
        mod._rules_doc.cache_clear()
        mod.stacking_rules.cache_clear()


def test_verdicts_are_sorted_into_their_own_buckets(monkeypatch):
    """All three verdicts must reach the reader differently; amber is not green."""
    import setubiz.eligibility.stacking as mod

    crafted = (
        StackingRule(
            schemes=("nsfdc_term_loan", "pmegp"),
            verdict=StackVerdict.COMBINABLE,
            reason_en="Sourced yes.",
            reason_hi="स्रोत सहित हाँ।",
            source="https://example.gov.in/order.pdf",
            sequencing="pmegp must be sanctioned first",
            combined_cap=Decimal("2500000"),
        ),
        StackingRule(
            schemes=("nsfdc_term_loan", "pmmy"),
            verdict=StackVerdict.MUTUALLY_EXCLUSIVE,
            reason_en="Same purpose.",
            reason_hi="एक ही उद्देश्य।",
            source="https://example.gov.in/circular.pdf",
        ),
        StackingRule(
            schemes=("nsfdc_term_loan", "cgtmse"),
            reason_en="Ask the bank.",
            reason_hi="बैंक से पूछें।",
        ),
    )
    monkeypatch.setattr(mod, "stacking_rules", lambda: crafted)

    eligibility = assess(SocialCategory.SC, 280000, state="Jharkhand")
    result = combinations(eligibility, "nsfdc_term_loan")
    assert [c.schemes[1] for c in result.combinable] == ["pmegp"]
    assert [c.schemes[1] for c in result.mutually_exclusive] == ["pmmy"]
    assert [c.schemes[1] for c in result.needs_verification] == ["cgtmse"]
    # A sourced combination carries its sequencing and cap through to the reader.
    combo = result.combinable[0]
    assert combo.sequencing == "pmegp must be sanctioned first"
    assert combo.combined_cap == Decimal("2500000")
    # Only sourced, combinable schemes are cited as sources for the facts object.
    assert "pmegp" in result.sources
    assert "cgtmse" not in result.sources


def test_combination_names_are_carried_in_both_languages():
    eligibility = assess(SocialCategory.SC, 280000, state="Jharkhand")
    result = combinations(eligibility, "nsfdc_term_loan")
    for combo in result.needs_verification:
        assert all(combo.names)
        assert all(combo.names_hi)


@pytest.mark.parametrize(
    ("margin", "expected"),
    [
        (10000, "nsfdc_micro_finance"),
        (100000, "nsfdc_term_loan"),
        (600000, None),
    ],
)
def test_the_routed_scheme_id_matches_the_data_files(margin, expected):
    """The stacking rules key on the id in corporations.yaml, not on the A/B letter."""
    assert route(margin).logic_id == expected


def test_out_of_scope_routes_report_no_scheme_id():
    assert route(600000).logic is SchemeLogic.OUT_OF_SCOPE
    assert route(600000).logic_id is None

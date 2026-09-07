"""Category-aware eligibility — a verdict is code, never an opinion (PLAN.md §5)."""

from __future__ import annotations

import pytest

from setubiz.eligibility import SocialCategory, Verdict, assess, comparison_schemes, corporations
from setubiz.eligibility.rules import corporation_for, sca_for_state
from setubiz.money import money


def test_sc_routes_to_nsfdc_with_the_jan_2026_ceiling():
    r = assess(SocialCategory.SC, 450000, state="Jharkhand", activity_category="dairy")
    assert r.verdict is Verdict.ELIGIBLE
    assert r.corporation is not None and r.corporation.id == "nsfdc"
    assert r.income_ceiling == money(500000)
    assert "07-01-2026" in (r.corporation.income_ceiling_note or "")


def test_sc_above_the_ceiling_is_ineligible_with_a_stated_reason():
    r = assess("sc", 620000)
    assert r.verdict is Verdict.INELIGIBLE
    assert any("exceeds" in reason for reason in r.reasons)
    # An ineligible verdict must still hand the applicant somewhere to go.
    assert {s.id for s in r.comparison} >= {"pmmy", "pmegp"}


def test_safai_karamchari_has_no_income_ceiling():
    r = assess(SocialCategory.SAFAI_KARAMCHARI, 1200000, state="JH")
    assert r.verdict is Verdict.ELIGIBLE
    assert r.corporation is not None and r.corporation.id == "nskfdc"
    assert r.income_ceiling is None
    doc_text = " ".join(d.en for d in r.documents)
    assert "Safai karamchari occupation certificate" in doc_text


def test_obc_uses_the_three_lakh_ceiling():
    ok = assess(SocialCategory.OBC, 280000)
    over = assess(SocialCategory.EBC, 310000)
    assert ok.corporation is not None and ok.corporation.id == "nbcfdc"
    assert ok.income_ceiling == money(300000)
    assert ok.verdict is Verdict.ELIGIBLE
    assert over.verdict is Verdict.INELIGIBLE


def test_missing_income_is_a_condition_not_a_rejection():
    r = assess("sc")
    assert r.verdict is Verdict.ELIGIBLE_WITH_CONDITIONS
    assert any("income certificate" in c for c in r.conditions)


def test_categories_without_a_mosje_corporation_are_routed_elsewhere():
    for category in (SocialCategory.GENERAL, SocialCategory.ST):
        r = assess(category, 200000)
        assert r.verdict is Verdict.INELIGIBLE
        assert r.corporation is None
        assert r.comparison


def test_woman_applicant_gets_the_concessional_window_condition():
    r = assess("sc", 200000, is_woman=True)
    assert r.verdict is Verdict.ELIGIBLE_WITH_CONDITIONS
    assert any("Mahila" in c for c in r.conditions)
    assert r.is_woman is True


def test_no_prior_experience_triggers_the_pm_daksh_handoff():
    r = assess("sc", 200000, has_prior_experience=False)
    assert any("PM-DAKSH" in c for c in r.conditions)
    assert any(h["id"] == "pm_daksh" for h in r.handoffs)


def test_requested_loan_above_the_corporation_ceiling_is_rejected():
    r = assess("obc", 200000, requested_loan=money(2000000))
    assert r.verdict is Verdict.INELIGIBLE
    assert any("exceeds the" in reason for reason in r.reasons)


def test_sca_lookup_by_state_name_and_code():
    by_name = sca_for_state("Jharkhand", "nsfdc")
    by_code = sca_for_state("jh", "nsfdc")
    assert by_name is not None and by_name == by_code
    assert "Ranchi" in by_name.address
    assert sca_for_state(None, "nsfdc") is None
    assert sca_for_state("Goa", "nsfdc") is None
    # NSKFDC does not operate through the Maharashtra agency in our directory.
    assert sca_for_state("Maharashtra", "nskfdc") is None


def test_activity_documents_are_appended_to_the_common_checklist():
    generic = assess("sc", 200000)
    dairy = assess("sc", 200000, activity_category="dairy")
    assert len(dairy.documents) > len(generic.documents)
    assert any("veterinary" in d.en.lower() for d in dairy.documents)
    assert all(d.hi for d in dairy.documents)  # bilingual checklist, no gaps


def test_reference_data_loads_and_is_well_formed():
    corps = corporations()
    assert {c.id for c in corps} == {"nsfdc", "nskfdc", "nbcfdc"}
    assert all(c.source.startswith("http") for c in corps)
    assert corporation_for(SocialCategory.SC) is not None
    assert corporation_for(SocialCategory.GENERAL) is None
    schemes = comparison_schemes()
    assert {s.id for s in schemes} >= {"pmmy", "pmegp", "cgtmse", "dri", "stand_up_india"}
    assert all(s.loan_range[0] <= s.loan_range[1] for s in schemes)


@pytest.mark.parametrize("bad", ["brahmin", "unknown"])
def test_unknown_social_category_is_rejected(bad):
    with pytest.raises(ValueError):
        assess(bad, 200000)

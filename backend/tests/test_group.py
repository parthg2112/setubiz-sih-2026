"""Self-help group mode — a group is not an average.

The single-applicant path must be untouched, and a member who does not qualify must be named
rather than folded into a group-level verdict. Someone finding out at the counter that their
income put the whole application at risk is the failure this mode exists to prevent.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from setubiz.eligibility import Verdict
from setubiz.eligibility.group import assess_group, routing_doc
from setubiz.money import money
from setubiz.schemas import AdvisoryRequest, GroupMember

FOUR_WOMEN = (
    GroupMember(
        name="Sunita",
        social_category="sc",
        annual_family_income=180000,
        contribution=25000,
        is_woman=True,
    ),
    GroupMember(
        name="Rekha",
        social_category="sc",
        annual_family_income=210000,
        contribution=25000,
        is_woman=True,
    ),
    GroupMember(
        name="Anita",
        social_category="sc",
        annual_family_income=160000,
        contribution=25000,
        is_woman=True,
    ),
    GroupMember(
        name="Kiran",
        social_category="sc",
        annual_family_income=240000,
        contribution=25000,
        is_woman=True,
    ),
)


def test_pooled_contributions_become_the_margin():
    request = AdvisoryRequest(
        village_query="Ormanji", savings=1, business_category="dairy", members=FOUR_WOMEN
    )
    assert request.is_group is True
    assert request.pooled_margin == money(100000)


def test_a_single_applicant_is_untouched_by_group_mode():
    """The acceptance criterion: omitting members must change nothing at all."""
    request = AdvisoryRequest(village_query="Ormanji", savings=100000, business_category="dairy")
    assert request.is_group is False
    assert request.members == ()
    # The finance engine sees exactly what it saw before group mode existed.
    assert request.pooled_margin == request.savings


def test_a_group_of_one_is_a_mistake_not_a_group():
    with pytest.raises(ValueError, match="at least two members"):
        AdvisoryRequest(
            village_query="Ormanji",
            savings=1,
            business_category="dairy",
            members=(GroupMember(contribution=25000),),
        )


def test_every_member_is_assessed_in_their_own_right():
    group = assess_group(FOUR_WOMEN, state="Jharkhand", activity_category="dairy")
    assert len(group.members) == 4
    assert group.all_qualify is True
    assert group.mixed_categories is False
    assert group.shared_corporation_id == "nsfdc"
    assert all(m.corporation_name for m in group.members)


def test_a_failing_member_is_named_and_never_averaged_away():
    """The whole point: one member over the ceiling is a fact the group has to deal with."""
    mixed = (
        *FOUR_WOMEN[:3],
        GroupMember(
            name="Kiran", social_category="sc", annual_family_income=620000, contribution=25000
        ),
    )
    group = assess_group(mixed, state="Jharkhand", activity_category="dairy")
    assert group.all_qualify is False
    assert [m.name for m in group.failing] == ["Kiran"]
    assert group.failing[0].verdict is Verdict.INELIGIBLE
    assert any("exceeds" in r for r in group.failing[0].reasons)
    # The group is told who, by name, rather than given a softened summary.
    note = next(n for n in group.notes if n.id == "shg_member_ineligible")
    assert "Kiran" in note.text_en and "Kiran" in note.text_hi


def test_the_group_splits_cleanly_into_who_is_in_and_who_is_not():
    """The report states both halves, so neither can be quietly dropped."""
    mixed = (
        *FOUR_WOMEN[:3],
        GroupMember(
            name="Kiran", social_category="sc", annual_family_income=620000, contribution=25000
        ),
    )
    group = assess_group(mixed, state="Jharkhand", activity_category="dairy")
    assert [m.name for m in group.qualifying] == ["Sunita", "Rekha", "Anita"]
    assert [m.name for m in group.failing] == ["Kiran"]
    # Every member appears in exactly one of the two lists.
    assert len(group.qualifying) + len(group.failing) == len(group.members)


def test_a_mixed_category_group_is_told_the_rule_is_unconfirmed():
    """Routing policy is a research question, so the engine refuses to invent one."""
    mixed = (
        FOUR_WOMEN[0],
        GroupMember(
            name="Meena", social_category="obc", annual_family_income=160000, contribution=25000
        ),
    )
    group = assess_group(mixed, state="Jharkhand", activity_category="dairy")
    assert group.mixed_categories is True
    assert group.shared_corporation_id is None
    assert group.routing_policy is None
    note = next(n for n in group.notes if n.id == "shg_routing_unconfirmed")
    assert note.text_en and note.text_hi
    assert "District Welfare Officer" in note.text_en


def test_the_routing_file_ships_with_its_rule_deliberately_unset():
    doc = routing_doc()
    assert doc["policy"] is None, "a routing policy shipped without being researched"
    assert doc["source"] is None
    # The options are documented so filling one in is a one-line change.
    assert {p["id"] for p in doc["policies"]} == {"majority", "split", "single_category_only"}
    assert all(p["description_en"] and p["description_hi"] for p in doc["policies"])


def test_liability_is_split_equally_by_default():
    group = assess_group(FOUR_WOMEN, instalment=money(12000))
    assert [m.liability for m in group.members] == [money(3000)] * 4
    assert sum(m.liability for m in group.members) == money(12000)


def test_liability_can_follow_contribution_instead():
    uneven = (
        GroupMember(name="A", contribution=50000),
        GroupMember(name="B", contribution=25000),
        GroupMember(name="C", contribution=25000),
    )
    group = assess_group(uneven, instalment=money(10000), liability_split="proportional")
    assert [m.liability for m in group.members] == [money(5000), money(2500), money(2500)]


def test_a_group_with_no_loan_carries_no_liability():
    group = assess_group(FOUR_WOMEN, instalment=Decimal(0))
    assert all(m.liability == 0 for m in group.members)


def test_proportional_split_divides_by_the_total_contribution():
    from setubiz.eligibility.group import _liabilities

    members = (GroupMember(name="A", contribution=1), GroupMember(name="B", contribution=1))
    assert _liabilities(members, money(100), "proportional") == (money(50), money(50))


def test_a_data_directory_without_a_routing_file_degrades_to_unconfirmed(tmp_path, monkeypatch):
    import setubiz.eligibility.group as mod
    from setubiz.config import get_settings

    (tmp_path / "schemes").mkdir()
    monkeypatch.setenv("SETUBIZ_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    mod.routing_doc.cache_clear()
    try:
        assert mod.routing_doc()["policy"] is None
    finally:
        get_settings.cache_clear()
        mod.routing_doc.cache_clear()


def test_an_unrouted_category_still_appears_with_its_own_verdict():
    """A general-category member routes to no corporation, and is reported, not dropped."""
    mixed = (
        FOUR_WOMEN[0],
        GroupMember(
            name="Priya", social_category="general", annual_family_income=160000, contribution=25000
        ),
    )
    group = assess_group(mixed, state="Jharkhand")
    priya = next(m for m in group.members if m.name == "Priya")
    assert priya.corporation_id is None
    assert priya.verdict is Verdict.INELIGIBLE
    assert priya in group.failing

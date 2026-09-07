"""Scheme router — PS Logic A/B boundaries and NSFDC caps (PLAN.md §5)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from setubiz.finance.router import (
    ActivityKind,
    SchemeLogic,
    project_cost_from_margin,
    route,
)
from setubiz.money import money


def test_project_cost_is_margin_over_ten_percent():
    assert project_cost_from_margin(money(100000)) == money(1000000)


def test_logic_b_golden_vector():
    r = route(100000)
    assert r.logic is SchemeLogic.B
    assert r.project_cost == money(1000000)
    assert r.max_loan == money(900000)
    assert r.annual_rate == Decimal("0.080")
    assert r.quarterly_rate == Decimal("0.020")
    assert r.total_quarters == 28
    assert r.moratorium_quarters == 2
    assert r.repayment_quarters == 26
    assert r.capped is False
    assert r.sca_rate == Decimal("0.04")


def test_logic_a_caps_loan_at_125k_not_126k():
    """P = ₹1.40 L would give 90% = ₹1.26 L, but the scheme cap is ₹1.25 L."""
    r = route(14000)
    assert r.logic is SchemeLogic.A
    assert r.project_cost == money(140000)
    assert r.max_loan == money(125000)
    assert r.capped is True
    assert r.annual_rate == Decimal("0.065")
    assert r.total_quarters == 12
    assert r.moratorium_quarters == 1
    assert r.repayment_quarters == 11
    assert r.sca_rate == Decimal("0.025")


def test_logic_a_below_the_cap_is_not_capped():
    r = route(10000)
    assert r.logic is SchemeLogic.A
    assert r.max_loan == money(90000)
    assert r.capped is False


def test_logic_b_caps_at_45_lakh():
    r = route(500000)
    assert r.logic is SchemeLogic.B
    assert r.project_cost == money(5000000)
    assert r.max_loan == money(4500000)
    assert r.capped is False


@pytest.mark.parametrize(
    ("margin", "expected"),
    [
        (13999, SchemeLogic.A),
        (14000, SchemeLogic.A),  # P = ₹1,40,000 exactly → still Logic A
        (14001, SchemeLogic.B),  # P = ₹1,40,010 → Logic B
        (499999, SchemeLogic.B),
        (500000, SchemeLogic.B),  # P = ₹50,00,000 exactly → still Logic B
        (500001, SchemeLogic.OUT_OF_SCOPE),
    ],
)
def test_boundaries(margin, expected):
    assert route(margin).logic is expected


def test_out_of_scope_carries_referrals_not_an_exception():
    r = route(600000)
    assert r.in_scope is False
    assert r.max_loan == money(0)
    assert "pmegp" in r.referrals
    assert "PMEGP" in r.notes[0] or "PMEGP" in " ".join(r.notes)


def test_plantation_gets_a_twelve_month_moratorium():
    general = route(100000, ActivityKind.GENERAL)
    plantation = route(100000, ActivityKind.PLANTATION)
    construction = route(100000, "construction")
    assert general.moratorium_quarters == 2
    assert plantation.moratorium_quarters == 4
    assert construction.moratorium_quarters == 4
    assert plantation.repayment_quarters == 24


def test_logic_a_moratorium_is_inside_the_three_year_window():
    r = route(14000)
    assert r.total_quarters == 12
    assert r.repayment_quarters == 11
    assert "inside" in r.notes[0]


@pytest.mark.parametrize("bad", [0, -1, "-5000"])
def test_non_positive_margin_rejected(bad):
    with pytest.raises(ValueError, match="margin must be positive"):
        route(bad)

"""Golden quarterly amortization vectors (PLAN.md §5).

CORRECTION TO PLAN.md: vector A is stated there as ≈₹12,471/q. That figure is unreachable under
the r = annual/4 convention that vector B (₹44,729) matches to the paisa; ₹12,471 comes from
effective-annual compounding ((1.065)^0.25 − 1 = 1.5868%/q → ₹12,473.94), which contradicts
vector B. We use r = annual/4 throughout — the standard Indian quarterly-rest convention — and
the correct vector A instalment is ₹12,501.34. Do not quote ₹12,471 in the deck.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from setubiz.finance.amortization import (
    MoratoriumMode,
    amortize,
    amortize_route,
    both_moratorium_modes,
    quarterly_instalment,
)
from setubiz.finance.router import route
from setubiz.money import ZERO, money


def test_golden_vector_b_term_loan():
    """M ₹1,00,000 → P ₹10,00,000 → L ₹9,00,000 @ 8% (2%/q), 2q moratorium, 26 instalments."""
    r = route(100000)
    a = amortize_route(r, r.max_loan, MoratoriumMode.SERVICED)

    assert a.principal_amortized == money(900000)
    assert a.repayment_quarters == 26
    assert a.instalment == money("44729.31")
    assert len(a.schedule) == 28

    repayment_interest = sum((row.interest for row in a.schedule if row.phase == "repayment"), ZERO)
    # PLAN.md's "total interest ≈ ₹2.63 L" is the repayment-phase figure.
    assert abs(repayment_interest - money(262962)) < money(100)
    # With the moratorium interest serviced quarterly (₹18,000 × 2) the all-in figure is higher.
    assert a.total_interest == money(repayment_interest + money(36000))


def test_golden_vector_a_micro_finance():
    """P ₹1,40,000 → L capped at ₹1,25,000 @ 6.5% (1.625%/q), 1q moratorium, 11 instalments."""
    r = route(14000)
    a = amortize_route(r, r.max_loan, MoratoriumMode.SERVICED)

    assert a.loan == money(125000)
    assert a.quarterly_rate == Decimal("0.01625")
    assert a.repayment_quarters == 11
    assert a.instalment == money("12501.34")  # supersedes PLAN.md's ₹12,471 — see module docstring


def test_quarterly_instalment_formula():
    assert quarterly_instalment(money(900000), Decimal("0.02"), 26) == money("44729.31")
    assert quarterly_instalment(money(120000), Decimal("0"), 12) == money(10000)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"principal": money(1000), "rate": Decimal("0.02"), "n": 0}, "instalments must be"),
        ({"principal": money(0), "rate": Decimal("0.02"), "n": 4}, "principal must be"),
        ({"principal": money(1000), "rate": Decimal("-0.01"), "n": 4}, "rate must be"),
    ],
)
def test_quarterly_instalment_rejects_bad_input(kwargs, message):
    with pytest.raises(ValueError, match=message):
        quarterly_instalment(**kwargs)


@pytest.mark.parametrize(
    ("loan", "rate", "quarters", "moratorium", "mode"),
    [
        (900000, Decimal("0.08"), 28, 2, MoratoriumMode.SERVICED),
        (900000, Decimal("0.08"), 28, 2, MoratoriumMode.CAPITALIZED),
        (125000, Decimal("0.065"), 12, 1, MoratoriumMode.SERVICED),
        (125000, Decimal("0.065"), 12, 1, MoratoriumMode.CAPITALIZED),
        (50000, Decimal("0.065"), 12, 0, MoratoriumMode.SERVICED),
        (4500000, Decimal("0.08"), 28, 4, MoratoriumMode.CAPITALIZED),
    ],
)
def test_schedule_invariants(loan, rate, quarters, moratorium, mode):
    a = amortize(loan, rate, quarters, moratorium, mode)

    assert len(a.schedule) == quarters
    assert a.schedule[-1].closing == ZERO
    assert sum((row.principal for row in a.schedule), ZERO) == a.principal_amortized
    assert a.total_outflow == sum((row.instalment for row in a.schedule), ZERO)
    assert sum(a.debt_service_by_year()) == a.total_outflow

    repayment = [row for row in a.schedule if row.phase == "repayment"]
    interests = [row.interest for row in repayment]
    assert interests == sorted(interests, reverse=True)  # interest falls as principal amortizes
    # Cash-flow identity, true in every phase and both modes.
    assert all(row.closing == row.opening + row.interest - row.instalment for row in a.schedule)


def test_capitalized_moratorium_costs_more_than_servicing_it():
    modes = both_moratorium_modes(money(900000), Decimal("0.08"), 28, 2)
    serviced = modes[MoratoriumMode.SERVICED]
    capitalized = modes[MoratoriumMode.CAPITALIZED]

    assert capitalized.principal_amortized > serviced.principal_amortized
    assert capitalized.instalment > serviced.instalment
    assert capitalized.total_interest > serviced.total_interest
    # Capitalized: nothing is paid at all during the moratorium.
    assert all(row.instalment == ZERO for row in capitalized.schedule if row.phase == "moratorium")
    # Serviced: exactly the interest is paid, principal untouched.
    assert all(
        row.instalment == row.interest and row.opening == row.closing
        for row in serviced.schedule
        if row.phase == "moratorium"
    )


def test_capitalized_principal_is_loan_compounded_over_the_moratorium():
    a = amortize(900000, Decimal("0.08"), 28, 2, MoratoriumMode.CAPITALIZED)
    assert a.principal_amortized == money(Decimal(900000) * Decimal("1.02") ** 2)


def test_debt_service_by_year_groups_four_quarters():
    a = amortize(900000, Decimal("0.08"), 28, 2, MoratoriumMode.SERVICED)
    by_year = a.debt_service_by_year()
    assert len(by_year) == 7
    # Year 1 = 2 moratorium interest payments + 2 instalments.
    assert by_year[0] == money(Decimal("18000") * 2 + Decimal("44729.31") * 2)
    assert by_year[1] == money(Decimal("44729.31") * 4)


def test_final_instalment_absorbs_the_rounding_residue():
    a = amortize(900000, Decimal("0.08"), 28, 2, MoratoriumMode.SERVICED)
    assert a.final_instalment != a.instalment
    assert abs(a.final_instalment - a.instalment) < money(1)
    assert a.schedule[-1].closing == ZERO


def test_debt_service_of_an_empty_schedule_is_empty():
    a = amortize(900000, Decimal("0.08"), 28, 2)
    empty = a.__class__(**{**a.__dict__, "schedule": ()})
    assert empty.debt_service_by_year() == []


def test_zero_moratorium_schedule_is_all_repayment():
    a = amortize(100000, Decimal("0.065"), 12, 0)
    assert all(row.phase == "repayment" for row in a.schedule)
    assert a.repayment_quarters == 12


@pytest.mark.parametrize(
    ("loan", "quarters", "moratorium", "message"),
    [
        (0, 12, 1, "loan must be positive"),
        (-5, 12, 1, "loan must be positive"),
        (1000, 12, 12, "moratorium must be"),
        (1000, 12, -1, "moratorium must be"),
    ],
)
def test_amortize_rejects_bad_input(loan, quarters, moratorium, message):
    with pytest.raises(ValueError, match=message):
        amortize(loan, Decimal("0.08"), quarters, moratorium)

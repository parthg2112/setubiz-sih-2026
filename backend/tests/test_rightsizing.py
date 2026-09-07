"""Right-sizing — the product thesis under test (PLAN.md §1, §5)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from setubiz.finance.amortization import MoratoriumMode, amortize
from setubiz.finance.cost_templates import (
    find_template_for_category,
    list_templates,
    load_template,
)
from setubiz.finance.rightsizing import (
    BindingConstraint,
    dscr_by_year,
    largest_loan_meeting,
    min_dscr,
    right_size,
)
from setubiz.finance.router import route
from setubiz.money import money


def test_dairy_template_required_capital_matches_plan(dairy):
    assert dairy.fixed_capital_total == money(346000)
    assert dairy.monthly_opex_total == money(21600)
    assert dairy.working_capital == money(64800)
    assert dairy.required_capital == money(410800)  # PLAN.md §5's "≈₹4.1 L required"
    assert dairy.monthly_net == money(7800)
    assert dairy.annual_noi == money(93600)


def test_the_demo_moment_max_loan_fails_dscr(dairy, logic_b_route):
    """₹4.1 L needed, ₹9 L borrowable — and ₹9 L is not serviceable."""
    rs = right_size(logic_b_route, dairy)

    assert rs.max_loan == money(900000)
    assert rs.max_loan_min_dscr < rs.dscr_threshold
    assert rs.max_loan_passes is False
    assert rs.recommended_loan < rs.max_loan
    assert rs.headroom == rs.max_loan - rs.recommended_loan
    assert rs.recommended_min_dscr >= rs.dscr_threshold
    assert any(w.id == "overborrowing" for w in rs.warnings)
    assert all(w.text_en and w.text_hi for w in rs.warnings)  # bilingual at source


def test_recommended_loan_is_bound_by_stress_and_reported_as_such(dairy, logic_b_route):
    rs = right_size(logic_b_route, dairy)
    assert rs.binding is BindingConstraint.STRESS
    assert rs.recommended_loan == money(205000)
    # The green number must survive a −15% revenue year at DSCR ≥ 1.0.
    mild = rs.recommended_stress[0]
    assert mild.revenue_factor == Decimal("0.85")
    assert mild.passes is True
    # The red number does not.
    assert rs.max_loan_stress[0].passes is False


def test_recommended_loan_is_rounded_down_to_the_configured_step(dairy, logic_b_route):
    rs = right_size(logic_b_route, dairy)
    assert rs.recommended_loan % money(1000) == 0


def test_capital_shortfall_is_surfaced_not_hidden(dairy, logic_b_route):
    rs = right_size(logic_b_route, dairy)
    assert rs.debt_need == money(310800)  # ₹4,10,800 required − ₹1,00,000 margin
    assert rs.capital_shortfall == rs.debt_need - rs.recommended_loan
    assert any(w.id == "capital_shortfall" for w in rs.warnings)


def test_capital_need_binds_when_cash_flow_is_strong(logic_b_route):
    """A comfortable unit is capped by what it actually needs, not by DSCR."""
    kirana = load_template("kirana_store")
    rs = right_size(logic_b_route, kirana, enforce_stress_floor=False)
    assert rs.binding is BindingConstraint.CAPITAL_NEED
    assert rs.recommended_loan == rs.debt_need
    # Rounding must never manufacture a shortfall when need is what binds.
    assert rs.capital_shortfall == 0
    assert not any(w.id == "capital_shortfall" for w in rs.warnings)


def test_scheme_cap_binds_when_the_unit_costs_more_than_the_ps_formula_allows(dairy):
    """Margin ₹30,000 → PS project cost ₹3 L, but the dairy template needs ₹4.1 L."""
    small_margin = route(30000)
    fat = dairy.model_copy(
        update={
            "monthly_revenue": (
                dairy.monthly_revenue[0].model_copy(update={"amount": money(900000)}),
            )
        }
    )
    rs = right_size(small_margin, fat)
    assert rs.max_loan == money(270000)
    assert rs.debt_need > rs.max_loan
    assert rs.binding is BindingConstraint.SCHEME_CAP
    assert rs.recommended_loan == rs.max_loan
    assert rs.max_loan_passes is True
    assert rs.capital_shortfall > 0


def test_loss_making_unit_is_not_viable_at_any_loan_size(logic_b_route, dairy):
    broke = dairy.model_copy(
        update={
            "monthly_revenue": (
                dairy.monthly_revenue[0].model_copy(update={"amount": money(5000)}),
            )
        }
    )
    rs = right_size(logic_b_route, broke)
    assert rs.annual_noi < 0
    assert rs.binding is BindingConstraint.NOT_VIABLE
    assert rs.recommended_loan == 0
    assert rs.recommended_dscr == ()
    assert any(w.id == "not_viable" for w in rs.warnings)


def test_out_of_scope_route_short_circuits(dairy):
    rs = right_size(route(600000), dairy)
    assert rs.recommended_loan == 0
    assert rs.max_loan == 0
    assert rs.warnings[0].id == "out_of_scope"
    assert "outside the NSFDC envelope" in rs.warnings[0].text_en


def test_dscr_falls_monotonically_with_loan_size(dairy, logic_b_route):
    noi = dairy.annual_noi
    ratios = [
        min_dscr(noi, money(amount), logic_b_route, MoratoriumMode.SERVICED)
        for amount in (100000, 200000, 400000, 900000)
    ]
    assert ratios == sorted(ratios, reverse=True)


def test_largest_loan_meeting_returns_ceiling_when_everything_passes(logic_b_route):
    got = largest_loan_meeting(
        money(10_000_000), logic_b_route, MoratoriumMode.SERVICED, Decimal("1.5"), money(900000)
    )
    assert got == money(900000)


def test_largest_loan_meeting_is_zero_without_income(logic_b_route):
    assert (
        largest_loan_meeting(
            money(0), logic_b_route, MoratoriumMode.SERVICED, Decimal("1.5"), money(900000)
        )
        == 0
    )
    assert (
        largest_loan_meeting(
            money(90000), logic_b_route, MoratoriumMode.SERVICED, Decimal("1.5"), money(0)
        )
        == 0
    )


def test_min_dscr_of_a_zero_loan_is_unbounded(logic_b_route):
    assert min_dscr(money(93600), money(0), logic_b_route, MoratoriumMode.SERVICED) > 100


def test_dscr_by_year_marks_a_debt_free_year_as_unbounded():
    a = amortize(900000, Decimal("0.08"), 28, 4, MoratoriumMode.CAPITALIZED)
    rows = dscr_by_year(money(93600), a, Decimal("1.5"))
    assert rows[0].debt_service == 0  # nothing paid in a fully capitalized first year
    assert rows[0].dscr > 100
    assert rows[0].passes is True
    assert len(rows) == 7


def test_dscr_by_year_is_empty_for_an_empty_schedule(logic_b_route):
    a = amortize(900000, Decimal("0.08"), 28, 2)
    assert len(dscr_by_year(money(93600), a, Decimal("1.5"))) == 7


def test_a_stricter_threshold_lowers_the_recommendation(dairy, logic_b_route):
    lenient = right_size(
        logic_b_route, dairy, dscr_threshold=Decimal("1.2"), enforce_stress_floor=False
    )
    strict = right_size(
        logic_b_route, dairy, dscr_threshold=Decimal("2.0"), enforce_stress_floor=False
    )
    assert strict.recommended_loan < lenient.recommended_loan


def test_both_moratorium_modes_can_be_right_sized(dairy, logic_b_route):
    serviced = right_size(logic_b_route, dairy, MoratoriumMode.SERVICED)
    capitalized = right_size(logic_b_route, dairy, MoratoriumMode.CAPITALIZED)
    assert serviced.mode is MoratoriumMode.SERVICED
    assert capitalized.mode is MoratoriumMode.CAPITALIZED
    assert capitalized.recommended_loan > 0


def test_every_shipped_template_loads_and_is_internally_consistent():
    templates = list_templates()
    assert len(templates) >= 5
    for tpl in templates:
        assert tpl.required_capital == tpl.fixed_capital_total + tpl.working_capital
        assert tpl.annual_noi == tpl.monthly_net * 12
        assert tpl.source
        assert tpl.assumptions


def test_template_scaling_is_linear(dairy):
    doubled = dairy.scaled(2)
    assert doubled.required_capital == dairy.required_capital * 2
    assert doubled.annual_noi == dairy.annual_noi * 2
    assert "× 2" in doubled.unit
    with pytest.raises(ValueError, match="units must be positive"):
        dairy.scaled(0)


def test_templates_are_findable_by_business_category():
    assert find_template_for_category("dairy").id == "dairy_2_animal"
    assert find_template_for_category("space_tourism") is None


def test_unknown_template_id_is_a_clear_error():
    with pytest.raises(KeyError, match="unknown cost template"):
        load_template("no_such_unit")

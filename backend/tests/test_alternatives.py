"""The size search — "start smaller" is not advice unless it says what smaller means.

The regression tests here matter more than the feature tests: adding a scaling schema to five
published cost templates must not move a single one of their figures.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from setubiz.finance import list_templates, load_template, route
from setubiz.finance.alternatives import COMFORT_MARGIN, viable_configurations
from setubiz.finance.cost_templates import CostTemplate, LineItem
from setubiz.finance.rightsizing import BindingConstraint
from setubiz.money import money

#: The published figures, as they stood before the scaling schema existed.
PUBLISHED = {
    "atta_chakki": (180000, 32200, 17100, 34200, 214200, 181200),
    "backyard_poultry": (129000, 39380, 34800, 69600, 198600, 54960),
    "dairy_2_animal": (346000, 29400, 21600, 64800, 410800, 93600),
    "kirana_store": (170000, 46200, 18100, 18100, 188100, 337200),
    "tailoring_unit": (95000, 43800, 27000, 54000, 149000, 201600),
}


@pytest.mark.parametrize("template_id", sorted(PUBLISHED))
def test_scaling_schema_does_not_move_any_published_figure(template_id):
    """At base_units every scaling branch is the identity, so the old numbers must survive."""
    tpl = load_template(template_id)
    fixed, revenue, opex, working, required, noi = PUBLISHED[template_id]
    assert tpl.fixed_capital_total == money(fixed)
    assert tpl.monthly_revenue_total == money(revenue)
    assert tpl.monthly_opex_total == money(opex)
    assert tpl.working_capital == money(working)
    assert tpl.required_capital == money(required)
    assert tpl.annual_noi == money(noi)


def test_resizing_to_the_base_size_is_the_identity():
    for tpl in list_templates():
        assert tpl.at_units(tpl.base_units) is tpl


def test_every_template_declares_a_searchable_range():
    for tpl in list_templates():
        low, high = tpl.unit_range
        assert low >= 1 and high >= low
        assert low <= tpl.base_units <= high, f"{tpl.id}: base size sits outside its own range"
        assert tpl.base_units in tpl.candidate_sizes()


def test_candidate_sizes_step_for_a_trade_counted_in_hundreds():
    """Poultry is sized in birds, so it must not enumerate 1,751 indistinguishable flocks."""
    poultry = load_template("backyard_poultry")
    assert poultry.candidate_sizes() == (250, 500, 750, 1000, 1250, 1500, 1750, 2000)
    assert load_template("dairy_2_animal").candidate_sizes() == (1, 2, 3, 4, 5, 6)


def test_line_items_scale_by_their_own_rule(dairy):
    four = dairy.at_units(4)
    by_item = {li.item: li.amount for li in four.fixed_capital}
    assert by_item["2 crossbred cows @ ₹75,000"] == money(300000)  # linear: doubled
    assert by_item["Chaff cutter, feed trough and equipment"] == money(25000)  # fixed
    assert by_item["Milk cans and utensils"] == money(8000)  # step: one set covers four
    six = dairy.at_units(6)
    cans = {li.item: li.amount for li in six.fixed_capital}["Milk cans and utensils"]
    assert cans == money(16000)  # a second set at five animals


def test_step_scaling_requires_a_capacity():
    with pytest.raises(ValueError, match="step_capacity"):
        LineItem(item="Shed", amount=Decimal(100), scaling="step")
    with pytest.raises(ValueError, match="step_capacity"):
        LineItem(item="Shed", amount=Decimal(100), scaling="step", step_capacity=0)


def test_a_template_range_must_be_sane(dairy):
    with pytest.raises(ValueError, match="ascending and positive"):
        dairy.model_copy(update={"unit_range": (4, 2)}).model_validate(
            dairy.model_copy(update={"unit_range": (4, 2)}).model_dump()
        )
    with pytest.raises(ValueError, match="unit_step must be positive"):
        CostTemplate.model_validate(dairy.model_dump() | {"unit_step": 0})


def test_labour_line_detection_decides_whether_phasing_is_honest():
    """Retained earnings are only real once the family has been paid."""
    assert load_template("dairy_2_animal").has_labour_line is True
    assert load_template("tailoring_unit").has_labour_line is True
    assert load_template("kirana_store").has_labour_line is True
    assert load_template("atta_chakki").has_labour_line is True
    # The one template that costs no labour at all.
    assert load_template("backyard_poultry").has_labour_line is False


def test_the_demo_persona_cannot_fund_any_dairy_size(dairy, logic_b_route):
    """₹1,00,000 of savings does not close the gap at any herd size, and we say so."""
    result = viable_configurations(logic_b_route, dairy)
    assert result.any_viable is False
    assert result.configurations == ()
    assert result.closest is not None and result.closest.units == 4
    assert result.additional_margin_needed == money(48800)
    assert {a.id for a in result.why_not} == {"closest_configuration", "additional_margin"}
    assert all(a.text_en and a.text_hi for a in result.why_not)


def test_a_bigger_unit_needs_less_of_the_applicants_own_money(dairy, logic_b_route):
    """The counterintuitive result, and the reason this feature is worth having.

    Fixed running costs are spread over more output, so the operating margin climbs from 14% at
    one animal to 33% at four, and the shortfall falls with size rather than rising.
    """
    rows = {c.units: c for c in viable_configurations(logic_b_route, dairy).considered}
    assert rows[1].shortfall > rows[2].shortfall > rows[3].shortfall > rows[4].shortfall


def test_raising_the_margin_makes_a_configuration_viable(dairy):
    result = viable_configurations(route(150000), dairy)
    assert result.any_viable is True
    best = result.configurations[0]
    assert best.units == 4
    assert best.funded is True
    assert best.shortfall == 0
    assert best.loan > 0 and best.instalment > 0
    assert best.min_dscr >= Decimal("1.5")
    assert best.comfort == "comfortable"


def test_configurations_are_ranked_safest_first(dairy):
    result = viable_configurations(route(400000), dairy)
    dscrs = [c.min_dscr for c in result.configurations]
    assert dscrs == sorted(dscrs, reverse=True)


def test_a_tight_configuration_is_labelled_tight(dairy, logic_b_route):
    """Sitting just above the norm is not the same as clearing it comfortably."""
    threshold = Decimal("1.5")
    rows = viable_configurations(logic_b_route, dairy).considered
    sample = rows[1]
    tight = sample.__class__(**{**sample.__dict__, "min_dscr": threshold + Decimal("0.10")})
    comfy = sample.__class__(**{**sample.__dict__, "min_dscr": threshold + COMFORT_MARGIN})
    assert tight.comfort == "tight"
    assert comfy.comfort == "comfortable"


def test_a_unit_the_applicant_can_simply_buy_needs_no_loan(dairy):
    """Enough savings and the answer is "you do not need to borrow", not a loan of zero."""
    result = viable_configurations(route(1200000), dairy)
    assert result.any_viable is True
    cheapest = min(result.configurations, key=lambda c: c.project_cost)
    assert cheapest.self_financed is True
    assert cheapest.loan == 0
    assert cheapest.instalment == 0


def test_phasing_is_offered_only_when_the_surplus_actually_covers_the_step(dairy):
    plan = viable_configurations(route(150000), dairy).phased
    assert plan is not None
    assert plan.start_units == 4 and plan.target_units == 5
    assert plan.annual_retained > 0
    assert plan.years_to_expand >= 1
    # The plan must actually fund itself within the years it claims.
    assert plan.annual_retained * plan.years_to_expand >= plan.expansion_cost


def test_phasing_is_withheld_where_the_template_pays_no_labour():
    """Poultry's surplus is not net of household drawings, so phasing would overstate it."""
    poultry = load_template("backyard_poultry")
    result = viable_configurations(route(300000), poultry)
    assert result.phased is None


def test_phasing_is_withheld_when_nothing_is_viable(dairy, logic_b_route):
    assert viable_configurations(logic_b_route, dairy).phased is None


def test_phasing_is_withheld_at_the_largest_size(dairy):
    """There is nothing to expand into once the biggest size is the viable one."""
    capped = dairy.model_copy(update={"unit_range": (4, 4)})
    result = viable_configurations(route(150000), capped)
    assert result.any_viable is True
    assert result.phased is None


def test_phasing_is_withheld_when_the_step_is_unreachable(dairy):
    """A surplus that cannot fund the next size in five years is not a plan."""
    expensive = dairy.model_copy(
        update={
            "fixed_capital": tuple(
                li.model_copy(update={"amount": li.amount * 40}) if li.scaling == "linear" else li
                for li in dairy.fixed_capital
            )
        }
    )
    result = viable_configurations(route(150000), expensive)
    assert result.phased is None


def test_a_single_size_template_still_explains_itself(dairy, logic_b_route):
    """A template with one size and no viable row must not return silence."""
    one = dairy.model_copy(update={"unit_range": (2, 2)})
    result = viable_configurations(logic_b_route, one)
    assert result.any_viable is False
    assert result.why_not
    assert result.closest is not None and result.closest.units == 2


def test_an_unservicable_business_is_reported_not_ranked(dairy, logic_b_route):
    """A size whose cash flow cannot service anything is never offered as an option."""
    hopeless = dairy.model_copy(
        update={
            "monthly_revenue": tuple(
                li.model_copy(update={"amount": Decimal(1)}) for li in dairy.monthly_revenue
            )
        }
    )
    result = viable_configurations(logic_b_route, hopeless)
    assert result.any_viable is False
    assert all(c.binding is BindingConstraint.NOT_VIABLE for c in result.considered)
    assert result.why_not


def test_a_unit_you_can_afford_but_that_loses_money_is_still_refused(dairy):
    """Affordable is not the same as viable, and the difference has to be said out loud."""
    loss_making = dairy.model_copy(
        update={
            "monthly_revenue": tuple(
                li.model_copy(update={"amount": Decimal(1)}) for li in dairy.monthly_revenue
            )
        }
    )
    # One size only, and a margin that already covers it, so nothing needs borrowing.
    result = viable_configurations(route(400000), loss_making.model_copy(
        update={"unit_range": (1, 1)}
    ))
    assert result.any_viable is False
    assert all(c.shortfall == 0 for c in result.considered)
    assert result.closest is None
    assert result.additional_margin_needed is None
    assert [a.id for a in result.why_not] == ["no_size_considered"]


def test_the_search_never_returns_an_empty_result_without_an_explanation(dairy, logic_b_route):
    for margin in (50000, 100000, 150000, 400000):
        result = viable_configurations(route(margin), dairy)
        assert result.any_viable or result.why_not, f"silent empty result at margin {margin}"

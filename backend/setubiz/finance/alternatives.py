"""What actually works: a bounded search over unit sizes (PLAN.md §5).

The engine already answers "can this applicant service the unit as costed?". When the answer is
no, telling someone to "start smaller" without saying what smaller means is not advice. This
module enumerates the sizes the template permits, re-costs the unit at each, and reports which
ones the applicant can both service and afford.

It is a loop over a handful of integers, not an optimiser. That is deliberate: a judge can check
every row by hand, and there is no objective function to argue about.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from setubiz.config import get_settings
from setubiz.finance.amortization import MoratoriumMode, amortize_route
from setubiz.finance.cost_templates import CostTemplate
from setubiz.finance.rightsizing import BindingConstraint, RightSizing, right_size
from setubiz.finance.router import SchemeRoute
from setubiz.money import ZERO, format_inr, q
from setubiz.schemas import Advisory

#: A configuration clearing the norm by less than this is reported as tight rather than
#: comfortable. A unit sitting at 1.51 against a 1.50 norm is one bad month from trouble, and
#: saying so is the whole point of the product.
COMFORT_MARGIN = Decimal("0.25")

Comfort = Literal["comfortable", "tight"]


@dataclass(frozen=True)
class Configuration:
    """One candidate size, fully costed and appraised."""

    units: int
    unit_label: str
    project_cost: Decimal
    debt_need: Decimal
    loan: Decimal
    instalment: Decimal
    annual_noi: Decimal
    min_dscr: Decimal
    binding: BindingConstraint
    shortfall: Decimal

    @property
    def funded(self) -> bool:
        """Whether the loan this unit can service actually covers what the unit costs.

        A configuration with a shortfall is not an option; it is the same dead end the applicant
        already has, at a different size.
        """
        return self.shortfall <= 0

    @property
    def self_financed(self) -> bool:
        """The applicant's own margin already covers the unit; no borrowing needed."""
        return self.funded and self.loan <= 0

    @property
    def viable(self) -> bool:
        """Affordable *and* worth doing.

        `annual_noi` is checked on its own rather than trusting the binding constraint: an
        out-of-scope route short-circuits right-sizing before it can report NOT_VIABLE, so a
        business that loses money every month would otherwise be offered as an option purely
        because the applicant happens to be able to pay for it.
        """
        return (
            self.funded and self.annual_noi > 0 and self.binding is not BindingConstraint.NOT_VIABLE
        )

    @property
    def comfort(self) -> Comfort:
        return (
            "tight"
            if self.min_dscr < get_settings().dscr_threshold + COMFORT_MARGIN
            else ("comfortable")
        )


@dataclass(frozen=True)
class PhasedPlan:
    """Start smaller, expand from retained earnings rather than from a second loan."""

    start_units: int
    target_units: int
    start_cost: Decimal
    expansion_cost: Decimal
    annual_retained: Decimal
    years_to_expand: int


@dataclass(frozen=True)
class AlternativeSet:
    base_units: int
    unit_label: str
    unit_label_hi: str | None
    #: Every size enumerated, in ascending order, whether or not it works.
    considered: tuple[Configuration, ...]
    #: The ones that clear DSCR and are fully funded, best first.
    configurations: tuple[Configuration, ...]
    #: When nothing is funded: the size that comes closest, and roughly what it would take.
    closest: Configuration | None
    additional_margin_needed: Decimal | None
    phased: PhasedPlan | None
    why_not: tuple[Advisory, ...]
    sources: tuple[str, ...] = ("finance_engine", "nabard_templates")

    @property
    def any_viable(self) -> bool:
        return bool(self.configurations)


def _configuration(
    units: int, sized: CostTemplate, rs: RightSizing, scheme: SchemeRoute, mode: MoratoriumMode
) -> Configuration:
    instalment = ZERO
    if rs.recommended_loan > 0:
        instalment = amortize_route(scheme, rs.recommended_loan, mode).instalment
    return Configuration(
        units=units,
        unit_label=sized.unit_label,
        project_cost=rs.required_capital,
        debt_need=rs.debt_need,
        loan=rs.recommended_loan,
        instalment=instalment,
        annual_noi=rs.annual_noi,
        min_dscr=rs.recommended_min_dscr,
        binding=rs.binding,
        shortfall=rs.capital_shortfall,
    )


def _phased(
    funded: tuple[Configuration, ...], considered: tuple[Configuration, ...], template: CostTemplate
) -> PhasedPlan | None:
    """Offer a phased build only when the arithmetic actually supports it.

    Retained earnings are net operating income less debt service. That is only a household's
    genuine surplus where the template already pays the family for its labour, which four of the
    five do; `backyard_poultry` does not, so phasing is not offered for it rather than being
    offered on an assumption the data does not support.
    """
    if not funded or not template.has_labour_line:
        return None

    start = funded[0]
    bigger = [c for c in considered if c.units > start.units]
    if not bigger:
        return None

    target = bigger[0]
    # A recommended loan always clears the DSCR norm, so this is positive by construction. No
    # guard needed: were it ever zero or negative, the accumulation below simply never reaches
    # the expansion cost and the plan is withheld anyway.
    retained = q(start.annual_noi - start.instalment * 4)
    expansion = q(target.project_cost - start.project_cost)
    years = 0
    accumulated = ZERO
    # Five years is the outer edge of a plan anyone can sensibly hold to.
    while accumulated < expansion and years < 5:
        accumulated = q(accumulated + retained)
        years += 1
    if accumulated < expansion:
        return None

    return PhasedPlan(
        start_units=start.units,
        target_units=target.units,
        start_cost=start.project_cost,
        expansion_cost=expansion,
        annual_retained=retained,
        years_to_expand=years,
    )


def _why_not(
    closest: Configuration | None, extra_margin: Decimal | None, label: str, label_hi: str
) -> tuple[Advisory, ...]:
    """Never return an empty result with no explanation."""
    if closest is None:
        return (
            Advisory(
                id="no_size_considered",
                text_en="This business has no alternative sizes to compare.",
                text_hi="इस व्यवसाय के लिए तुलना करने योग्य कोई अन्य आकार नहीं है।",
            ),
        )

    out = [
        Advisory(
            id="closest_configuration",
            text_en=(
                f"No size of this business can be both serviced and fully funded from your "
                f"savings plus the loan it supports. The closest is {closest.units} {label}"
                f"{'s' if closest.units != 1 else ''}, which still leaves a gap."
            ),
            text_hi=(
                f"इस व्यवसाय का कोई भी आकार आपकी बचत और मिलने वाले ऋण से पूरी तरह वित्तपोषित नहीं "
                f"हो पाता। सबसे नज़दीक {closest.units} {label_hi} है, फिर भी कमी रह जाती है।"
            ),
        )
    ]
    if extra_margin is not None and extra_margin > 0:
        gap = format_inr(extra_margin)
        out.append(
            Advisory(
                id="additional_margin",
                text_en=(
                    f"About {gap} more of your own money would close that gap at "
                    f"{closest.units} {label}{'s' if closest.units != 1 else ''}. A larger unit "
                    f"often needs less of your own money, not more, because its running costs are "
                    f"spread over more output."
                ),
                text_hi=(
                    f"{closest.units} {label_hi} पर यह कमी पूरी करने के लिए लगभग {gap} "
                    f"की अतिरिक्त अपनी पूँजी चाहिए। बड़ी इकाई में प्रायः अपनी पूँजी कम लगती "
                    f"है, क्योंकि खर्च अधिक उत्पादन पर बँट जाता है।"
                ),
            )
        )
    return tuple(out)


def viable_configurations(
    scheme: SchemeRoute,
    template: CostTemplate,
    mode: MoratoriumMode | str = MoratoriumMode.SERVICED,
    *,
    dscr_threshold: Decimal | None = None,
    stress_floor: Decimal | None = None,
) -> AlternativeSet:
    """Enumerate the sizes this template permits and report which ones work.

    `route()` is deliberately called by the caller and reused for every size: the applicant's own
    savings do not change when the unit does, and neither does the scheme ceiling that follows
    from them.
    """
    mode = MoratoriumMode(mode)

    considered: list[Configuration] = []
    for units in template.candidate_sizes():
        sized = template.at_units(units)
        rs = right_size(
            scheme, sized, mode, dscr_threshold=dscr_threshold, stress_floor=stress_floor
        )
        considered.append(_configuration(units, sized, rs, scheme, mode))
    rows = tuple(considered)

    # Fully funded and actually serviceable. Ranked by headroom over the norm, then by the
    # cheapest unit that achieves it, so the safest affordable plan leads.
    ranked = tuple(
        sorted((c for c in rows if c.viable), key=lambda c: (-c.min_dscr, c.project_cost))
    )

    closest: Configuration | None = None
    extra_margin: Decimal | None = None
    why_not: tuple[Advisory, ...] = ()
    if not ranked:
        candidates = [c for c in rows if c.shortfall > 0]
        closest = min(candidates, key=lambda c: c.shortfall) if candidates else None
        # Every extra rupee of margin reduces the debt need by a rupee while the serviceable loan
        # is unchanged, so the shortfall is what it would take. Stated as "about" because the
        # binding constraint can shift once the numbers move.
        extra_margin = closest.shortfall if closest else None
        why_not = _why_not(
            closest,
            extra_margin,
            template.unit_label,
            template.unit_label_hi or template.unit_label,
        )

    return AlternativeSet(
        base_units=template.base_units,
        unit_label=template.unit_label,
        unit_label_hi=template.unit_label_hi,
        considered=rows,
        configurations=ranked,
        closest=closest,
        additional_margin_needed=extra_margin,
        phased=_phased(ranked, rows, template),
        why_not=why_not,
    )

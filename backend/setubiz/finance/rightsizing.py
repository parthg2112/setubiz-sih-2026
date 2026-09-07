"""Right-sizing — the product thesis: capacity to borrow ≠ capacity to repay (PLAN.md §1, §5).

The PS formula (Project Cost = Margin ÷ 10%) yields the *maximum* loan. This module computes the
loan the business can actually service: NABARD appraisal DSCR ≥ 1.5, stress-tested at −15%/−30%,
never above the scheme cap, and never above what the unit actually needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from setubiz.config import get_settings
from setubiz.finance.amortization import AmortizationResult, MoratoriumMode, amortize
from setubiz.finance.cost_templates import CostTemplate
from setubiz.finance.router import SchemeRoute
from setubiz.money import ZERO, floor_to, format_inr, q

#: Reported when a year carries no debt service at all (capitalized moratorium year).
UNBOUNDED_DSCR = Decimal("999")


class BindingConstraint(str, Enum):
    DSCR = "dscr"  # base-case repayment capacity
    STRESS = "stress"  # survives a −15% revenue year
    SCHEME_CAP = "scheme_cap"  # NSFDC ceiling bites before cash flow does
    CAPITAL_NEED = "capital_need"  # the unit simply does not need more money
    NOT_VIABLE = "not_viable"  # NOI ≤ 0: no loan is serviceable


@dataclass(frozen=True)
class DscrYear:
    year: int
    noi: Decimal
    debt_service: Decimal
    dscr: Decimal
    passes: bool


@dataclass(frozen=True)
class StressResult:
    label: str
    revenue_factor: Decimal
    annual_noi: Decimal
    min_dscr: Decimal
    floor: Decimal
    passes: bool
    by_year: tuple[DscrYear, ...]


@dataclass(frozen=True)
class RightSizing:
    scheme: SchemeRoute
    template_id: str
    mode: MoratoriumMode
    dscr_threshold: Decimal
    stress_floor: Decimal

    required_capital: Decimal
    debt_need: Decimal
    annual_noi: Decimal

    max_loan: Decimal
    recommended_loan: Decimal
    binding: BindingConstraint
    headroom: Decimal  # max_loan − recommended_loan, the red-vs-green gap

    max_loan_dscr: tuple[DscrYear, ...]
    recommended_dscr: tuple[DscrYear, ...]
    max_loan_min_dscr: Decimal
    recommended_min_dscr: Decimal
    max_loan_stress: tuple[StressResult, ...]
    recommended_stress: tuple[StressResult, ...]

    capital_shortfall: Decimal
    warnings: tuple[str, ...] = field(default=())

    @property
    def max_loan_passes(self) -> bool:
        return self.max_loan_min_dscr >= self.dscr_threshold


def _annual_noi(template: CostTemplate, revenue_factor: Decimal = Decimal("1")) -> Decimal:
    return q((q(template.monthly_revenue_total * revenue_factor) - template.monthly_opex_total) * 12)


def dscr_by_year(
    annual_noi: Decimal, amort: AmortizationResult, threshold: Decimal
) -> tuple[DscrYear, ...]:
    """DSCR = net operating income ÷ debt service, computed per loan year."""
    rows: list[DscrYear] = []
    for idx, ds in enumerate(amort.debt_service_by_year(), start=1):
        if ds <= 0:
            ratio = UNBOUNDED_DSCR
        else:
            ratio = q(annual_noi / ds, Decimal("0.01"))
        rows.append(
            DscrYear(
                year=idx, noi=annual_noi, debt_service=ds, dscr=ratio, passes=ratio >= threshold
            )
        )
    return tuple(rows)


def min_dscr(annual_noi: Decimal, loan: Decimal, scheme: SchemeRoute, mode: MoratoriumMode) -> Decimal:
    if loan <= 0:
        return UNBOUNDED_DSCR
    amort = amortize(loan, scheme.annual_rate, scheme.total_quarters, scheme.moratorium_quarters, mode)
    ratios = [row.dscr for row in dscr_by_year(annual_noi, amort, Decimal("0"))]
    return min(ratios) if ratios else UNBOUNDED_DSCR


def largest_loan_meeting(
    annual_noi: Decimal,
    scheme: SchemeRoute,
    mode: MoratoriumMode,
    target: Decimal,
    ceiling: Decimal,
    tolerance: Decimal = Decimal("100"),
) -> Decimal:
    """Largest loan whose worst-year DSCR still clears `target`. DSCR falls monotonically in L."""
    if annual_noi <= 0 or ceiling <= 0:
        return ZERO
    if min_dscr(annual_noi, ceiling, scheme, mode) >= target:
        return ceiling
    lo, hi = ZERO, ceiling
    while hi - lo > tolerance:
        mid = q((lo + hi) / 2)
        if min_dscr(annual_noi, mid, scheme, mode) >= target:
            lo = mid
        else:
            hi = mid
    return lo


def _stress(
    template: CostTemplate,
    loan: Decimal,
    scheme: SchemeRoute,
    mode: MoratoriumMode,
    factors: tuple[Decimal, ...],
    floor: Decimal,
) -> tuple[StressResult, ...]:
    out: list[StressResult] = []
    for factor in factors:
        noi = _annual_noi(template, factor)
        drop = int((Decimal("1") - factor) * 100)
        if loan <= 0:
            out.append(
                StressResult(
                    label=f"revenue -{drop}%",
                    revenue_factor=factor,
                    annual_noi=noi,
                    min_dscr=UNBOUNDED_DSCR,
                    floor=floor,
                    passes=True,
                    by_year=(),
                )
            )
            continue
        amort = amortize(
            loan, scheme.annual_rate, scheme.total_quarters, scheme.moratorium_quarters, mode
        )
        by_year = dscr_by_year(noi, amort, floor)
        worst = min((r.dscr for r in by_year), default=UNBOUNDED_DSCR)
        out.append(
            StressResult(
                label=f"revenue -{drop}%",
                revenue_factor=factor,
                annual_noi=noi,
                min_dscr=worst,
                floor=floor,
                passes=worst >= floor,
                by_year=by_year,
            )
        )
    return tuple(out)


def right_size(
    scheme: SchemeRoute,
    template: CostTemplate,
    mode: MoratoriumMode | str = MoratoriumMode.SERVICED,
    *,
    dscr_threshold: Decimal | None = None,
    stress_floor: Decimal | None = None,
    enforce_stress_floor: bool | None = None,
) -> RightSizing:
    """Compute the recommended loan and everything needed to defend it on screen."""
    settings = get_settings()
    mode = MoratoriumMode(mode)
    threshold = dscr_threshold if dscr_threshold is not None else settings.dscr_threshold
    floor = stress_floor if stress_floor is not None else settings.stress_dscr_floor
    enforce = (
        enforce_stress_floor if enforce_stress_floor is not None else settings.enforce_stress_floor
    )

    noi = template.annual_noi
    required = template.required_capital
    debt_need = max(ZERO, q(required - scheme.margin))
    max_loan = scheme.max_loan
    warnings: list[str] = []

    if not scheme.in_scope:
        return RightSizing(
            scheme=scheme,
            template_id=template.id,
            mode=mode,
            dscr_threshold=threshold,
            stress_floor=floor,
            required_capital=required,
            debt_need=debt_need,
            annual_noi=noi,
            max_loan=ZERO,
            recommended_loan=ZERO,
            binding=BindingConstraint.SCHEME_CAP,
            headroom=ZERO,
            max_loan_dscr=(),
            recommended_dscr=(),
            max_loan_min_dscr=UNBOUNDED_DSCR,
            recommended_min_dscr=UNBOUNDED_DSCR,
            max_loan_stress=(),
            recommended_stress=(),
            capital_shortfall=debt_need,
            warnings=("Project cost is outside the NSFDC envelope; see referral schemes.",),
        )

    candidates: dict[BindingConstraint, Decimal] = {
        BindingConstraint.SCHEME_CAP: max_loan,
        BindingConstraint.CAPITAL_NEED: debt_need,
    }
    if noi <= 0:
        recommended = ZERO
        binding = BindingConstraint.NOT_VIABLE
        warnings.append(
            "The unit's monthly operating surplus is zero or negative — no loan size is "
            "serviceable. Revisit prices, scale or the cost template before borrowing."
        )
    else:
        candidates[BindingConstraint.DSCR] = largest_loan_meeting(
            noi, scheme, mode, threshold, max_loan
        )
        if enforce and settings.stress_factors:
            stressed_noi = _annual_noi(template, settings.stress_factors[0])
            candidates[BindingConstraint.STRESS] = largest_loan_meeting(
                stressed_noi, scheme, mode, floor, max_loan
            )
        binding = min(candidates, key=lambda k: (candidates[k], _tiebreak(k)))
        # Round to a bankable figure — but never below what the unit needs when need is what binds,
        # or the rounding itself would manufacture a capital shortfall.
        if binding is BindingConstraint.CAPITAL_NEED:
            recommended = candidates[binding]
        else:
            recommended = floor_to(candidates[binding], settings.recommended_loan_step)

    max_amort = amortize(
        max_loan, scheme.annual_rate, scheme.total_quarters, scheme.moratorium_quarters, mode
    )
    max_rows = dscr_by_year(noi, max_amort, threshold)
    max_min = min((r.dscr for r in max_rows), default=UNBOUNDED_DSCR)

    if recommended > 0:
        rec_amort = amortize(
            recommended, scheme.annual_rate, scheme.total_quarters, scheme.moratorium_quarters, mode
        )
        rec_rows = dscr_by_year(noi, rec_amort, threshold)
        rec_min = min((r.dscr for r in rec_rows), default=UNBOUNDED_DSCR)
    else:
        rec_rows, rec_min = (), UNBOUNDED_DSCR

    shortfall = max(ZERO, q(debt_need - recommended))
    if shortfall > 0 and binding is not BindingConstraint.NOT_VIABLE:
        warnings.append(
            f"Cash flow supports only {format_inr(recommended)} of the {format_inr(debt_need)} "
            "of debt this unit needs. Increase promoter contribution, start at a smaller scale, "
            "or phase the investment."
        )
    if max_min < threshold:
        warnings.append(
            f"At the maximum permissible loan of {format_inr(max_loan)} the worst-year DSCR is "
            f"{max_min}, below the {threshold} appraisal norm — this is the borrowing level that "
            "causes the defaults the scheme is trying to prevent."
        )

    return RightSizing(
        scheme=scheme,
        template_id=template.id,
        mode=mode,
        dscr_threshold=threshold,
        stress_floor=floor,
        required_capital=required,
        debt_need=debt_need,
        annual_noi=noi,
        max_loan=max_loan,
        recommended_loan=recommended,
        binding=binding,
        headroom=q(max_loan - recommended),
        max_loan_dscr=max_rows,
        recommended_dscr=rec_rows,
        max_loan_min_dscr=max_min,
        recommended_min_dscr=rec_min,
        max_loan_stress=_stress(
            template, max_loan, scheme, mode, settings.stress_factors, floor
        ),
        recommended_stress=_stress(
            template, recommended, scheme, mode, settings.stress_factors, floor
        ),
        capital_shortfall=shortfall,
        warnings=tuple(warnings),
    )


def _tiebreak(constraint: BindingConstraint) -> int:
    """When two constraints land on the same rupee, report the one that actually bit.

    A cash-flow constraint that merely saturates at the ceiling has not bound anything — the
    ceiling has. So hard limits win ties over DSCR/stress.
    """
    order = {
        BindingConstraint.SCHEME_CAP: 0,
        BindingConstraint.CAPITAL_NEED: 1,
        BindingConstraint.STRESS: 2,
        BindingConstraint.DSCR: 3,
        BindingConstraint.NOT_VIABLE: 4,
    }
    return order[constraint]

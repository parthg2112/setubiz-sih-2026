"""Quarterly amortization with the two NSFDC moratorium treatments (PLAN.md §5).

Quarterly rest convention: r = annual / 4. This reproduces PLAN.md's golden vector B
(₹9,00,000 @ 8%, 26 instalments → ₹44,729.31/q) to the paisa. See tests/test_amortization.py
for why golden vector A in PLAN.md (₹12,471) is superseded by ₹12,501.34.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from setubiz.finance.router import SchemeRoute
from setubiz.money import ZERO, money, q


class MoratoriumMode(str, Enum):
    #: Interest is serviced quarterly during the moratorium; principal is untouched.
    SERVICED = "serviced"
    #: Nothing is paid during the moratorium; accrued interest is added to principal.
    CAPITALIZED = "capitalized"


@dataclass(frozen=True)
class ScheduleRow:
    quarter: int
    year: int
    phase: str  # "moratorium" | "repayment"
    opening: Decimal
    interest: Decimal
    principal: Decimal
    instalment: Decimal
    closing: Decimal


@dataclass(frozen=True)
class AmortizationResult:
    mode: MoratoriumMode
    loan: Decimal
    principal_amortized: Decimal  # L, or L·(1+r)^m under CAPITALIZED
    annual_rate: Decimal
    quarterly_rate: Decimal
    moratorium_quarters: int
    repayment_quarters: int
    instalment: Decimal
    schedule: tuple[ScheduleRow, ...]
    total_interest: Decimal
    total_outflow: Decimal

    @property
    def final_instalment(self) -> Decimal:
        return self.schedule[-1].instalment

    def debt_service_by_year(self) -> list[Decimal]:
        """Total cash outflow per loan year — the denominator of DSCR."""
        if not self.schedule:
            return []
        years = max(row.year for row in self.schedule)
        out = [ZERO for _ in range(years)]
        for row in self.schedule:
            out[row.year - 1] += row.instalment
        return [q(v) for v in out]


def quarterly_instalment(principal: Decimal, rate: Decimal, n: int) -> Decimal:
    """EMI_q = L·r(1+r)ⁿ / ((1+r)ⁿ − 1); degenerates to L/n at zero rate."""
    if n <= 0:
        raise ValueError("number of instalments must be positive")
    if principal <= 0:
        raise ValueError("principal must be positive")
    if rate < 0:
        raise ValueError("rate must be non-negative")
    if rate == 0:
        return q(principal / n)
    growth = (Decimal(1) + rate) ** n
    return q(principal * rate * growth / (growth - Decimal(1)))


def amortize(
    loan: Decimal | int | float | str,
    annual_rate: Decimal,
    total_quarters: int,
    moratorium_quarters: int = 0,
    mode: MoratoriumMode | str = MoratoriumMode.SERVICED,
    *,
    quarterly_rate: Decimal | None = None,
) -> AmortizationResult:
    """Build the full quarterly schedule. The last instalment absorbs the rounding residue."""
    principal = money(loan)
    mode = MoratoriumMode(mode)
    if principal <= 0:
        raise ValueError("loan must be positive")
    if moratorium_quarters < 0 or moratorium_quarters >= total_quarters:
        raise ValueError("moratorium must be non-negative and shorter than the tenure")

    r = annual_rate / 4 if quarterly_rate is None else quarterly_rate
    n = total_quarters - moratorium_quarters
    rows: list[ScheduleRow] = []
    balance = principal

    for i in range(1, moratorium_quarters + 1):
        interest = q(balance * r)
        if mode is MoratoriumMode.SERVICED:
            instalment, closing = interest, balance
        else:
            instalment, closing = ZERO, q(balance + interest)
        rows.append(
            ScheduleRow(
                quarter=i,
                year=math.ceil(i / 4),
                phase="moratorium",
                opening=balance,
                interest=interest,
                principal=ZERO,
                instalment=instalment,
                closing=closing,
            )
        )
        balance = closing

    amortized_principal = balance
    instalment = quarterly_instalment(amortized_principal, r, n)

    for k in range(1, n + 1):
        quarter = moratorium_quarters + k
        interest = q(balance * r)
        if k == n:
            principal_part = balance
            pay = q(principal_part + interest)
        else:
            pay = instalment
            principal_part = q(pay - interest)
        closing = q(balance - principal_part)
        rows.append(
            ScheduleRow(
                quarter=quarter,
                year=math.ceil(quarter / 4),
                phase="repayment",
                opening=balance,
                interest=interest,
                principal=principal_part,
                instalment=pay,
                closing=closing,
            )
        )
        balance = closing

    total_interest = q(sum((row.interest for row in rows), ZERO))
    total_outflow = q(sum((row.instalment for row in rows), ZERO))
    return AmortizationResult(
        mode=mode,
        loan=principal,
        principal_amortized=amortized_principal,
        annual_rate=annual_rate,
        quarterly_rate=r,
        moratorium_quarters=moratorium_quarters,
        repayment_quarters=n,
        instalment=instalment,
        schedule=tuple(rows),
        total_interest=total_interest,
        total_outflow=total_outflow,
    )


def amortize_route(
    scheme: SchemeRoute, loan: Decimal, mode: MoratoriumMode | str = MoratoriumMode.SERVICED
) -> AmortizationResult:
    return amortize(
        loan, scheme.annual_rate, scheme.total_quarters, scheme.moratorium_quarters, mode
    )


def both_moratorium_modes(
    loan: Decimal, annual_rate: Decimal, total_quarters: int, moratorium_quarters: int
) -> dict[MoratoriumMode, AmortizationResult]:
    """PLAN.md §5 requires both treatments be displayed, never one silently chosen."""
    return {
        m: amortize(loan, annual_rate, total_quarters, moratorium_quarters, m)
        for m in MoratoriumMode
    }

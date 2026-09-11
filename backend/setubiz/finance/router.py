"""Scheme router — PS Logic A/B, encoded from the real NSFDC scheme pages (PLAN.md §0.1, §5).

Micro Finance Scheme : https://www.dosje.gov.in/schemes-and-services/micro-finance-scheme/
Term Loan Scheme     : https://www.dosje.gov.in/schemes-and-services/2998/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from setubiz.money import money, q

MARGIN_SHARE = Decimal("0.10")  # promoter contribution; PS "10% margin"
LOAN_SHARE = Decimal("0.90")  # NSFDC finances 90% of the unit cost

LOGIC_A_MAX_PROJECT = money("140000")
LOGIC_B_MAX_PROJECT = money("5000000")
LOGIC_A_LOAN_CAP = money("125000")
LOGIC_B_LOAN_CAP = money("4500000")

#: Margin above which the project cost leaves the scheme envelope entirely (₹50 L / 10%).
OUT_OF_SCOPE_MARGIN = LOGIC_B_MAX_PROJECT * MARGIN_SHARE  # ₹5,00,000


class SchemeLogic(str, Enum):
    A = "A"  # Micro Finance Scheme
    B = "B"  # Term Loan Scheme
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ActivityKind(str, Enum):
    GENERAL = "general"
    PLANTATION = "plantation"
    CONSTRUCTION = "construction"


@dataclass(frozen=True)
class SchemeRoute:
    logic: SchemeLogic
    scheme_name: str
    margin: Decimal
    project_cost: Decimal
    max_loan: Decimal
    annual_rate: Decimal
    total_quarters: int
    moratorium_quarters: int
    capped: bool
    #: NSFDC → State Channelizing Agency on-lending rate for this logic (PLAN.md §0.1).
    sca_rate: Decimal | None = None
    referrals: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    sources: tuple[str, ...] = field(default=())

    @property
    def quarterly_rate(self) -> Decimal:
        return self.annual_rate / 4

    @property
    def logic_id(self) -> str | None:
        """The scheme id as it appears in `corporations.yaml` under `logics:`.

        The stacking layer keys its rules on this, so it must be the id the data files use and
        not the A/B letter. An out-of-scope route has no scheme, and therefore nothing to stack.
        """
        if self.logic is SchemeLogic.A:
            return "nsfdc_micro_finance"
        if self.logic is SchemeLogic.B:
            return "nsfdc_term_loan"
        return None

    @property
    def in_scope(self) -> bool:
        return self.logic is not SchemeLogic.OUT_OF_SCOPE

    @property
    def repayment_quarters(self) -> int:
        return self.total_quarters - self.moratorium_quarters


def project_cost_from_margin(margin: Decimal) -> Decimal:
    """PS formula: Project Cost = Margin ÷ 10%. This yields the *maximum*, not the right, loan."""
    return q(margin / MARGIN_SHARE)


def route(
    margin: Decimal | int | float | str,
    activity_kind: ActivityKind | str = ActivityKind.GENERAL,
) -> SchemeRoute:
    """Route a promoter's margin money to the applicable NSFDC scheme logic."""
    m = money(margin)
    if m <= 0:
        raise ValueError("margin must be positive")
    kind = ActivityKind(activity_kind)
    p = project_cost_from_margin(m)

    if p <= LOGIC_A_MAX_PROJECT:
        uncapped = q(p * LOAN_SHARE)
        loan = min(uncapped, LOGIC_A_LOAN_CAP)
        return SchemeRoute(
            logic=SchemeLogic.A,
            scheme_name="NSFDC Micro Finance Scheme",
            margin=m,
            project_cost=p,
            max_loan=loan,
            annual_rate=Decimal("0.065"),
            total_quarters=12,  # 3 years
            moratorium_quarters=1,  # 3 months, inside the 3-year window
            capped=loan < uncapped,
            sca_rate=Decimal("0.025"),
            notes=("3-month moratorium falls inside the 3-year repayment window, not after it.",),
            sources=("nsfdc_micro_finance",),
        )

    if p <= LOGIC_B_MAX_PROJECT:
        uncapped = q(p * LOAN_SHARE)
        loan = min(uncapped, LOGIC_B_LOAN_CAP)
        moratorium = 4 if kind in (ActivityKind.PLANTATION, ActivityKind.CONSTRUCTION) else 2
        return SchemeRoute(
            logic=SchemeLogic.B,
            scheme_name="NSFDC Term Loan Scheme",
            margin=m,
            project_cost=p,
            max_loan=loan,
            annual_rate=Decimal("0.080"),
            total_quarters=28,  # 7 years
            moratorium_quarters=moratorium,
            capped=loan < uncapped,
            sca_rate=Decimal("0.04"),
            notes=(
                "12-month moratorium applies to plantation/construction activities."
                if moratorium == 4
                else "6-month moratorium; quarterly instalments within 7 years.",
            ),
            sources=("nsfdc_term_loan",),
        )

    return SchemeRoute(
        logic=SchemeLogic.OUT_OF_SCOPE,
        scheme_name="Beyond NSFDC scheme envelope",
        margin=m,
        project_cost=p,
        max_loan=money(0),
        annual_rate=Decimal("0"),
        total_quarters=0,
        moratorium_quarters=0,
        capped=False,
        referrals=("pmegp", "pmmy", "stand_up_india"),
        notes=(
            "Project cost exceeds ₹50.00 L, the NSFDC Term Loan ceiling. "
            "Refer to PMEGP / MUDRA / Stand-Up India.",
        ),
        sources=("nsfdc_term_loan",),
    )

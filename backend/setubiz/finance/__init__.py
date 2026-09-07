"""Deterministic financial structuring. No ML, no LLM, 100% test-covered (PLAN.md §5)."""

from setubiz.finance.amortization import (
    AmortizationResult,
    MoratoriumMode,
    ScheduleRow,
    amortize,
    both_moratorium_modes,
    quarterly_instalment,
)
from setubiz.finance.cost_templates import CostTemplate, list_templates, load_template
from setubiz.finance.rightsizing import (
    BindingConstraint,
    RightSizing,
    StressResult,
    dscr_by_year,
    right_size,
)
from setubiz.finance.router import (
    OUT_OF_SCOPE_MARGIN,
    ActivityKind,
    SchemeLogic,
    SchemeRoute,
    route,
)

__all__ = [
    "OUT_OF_SCOPE_MARGIN",
    "ActivityKind",
    "AmortizationResult",
    "BindingConstraint",
    "CostTemplate",
    "MoratoriumMode",
    "RightSizing",
    "ScheduleRow",
    "SchemeLogic",
    "SchemeRoute",
    "StressResult",
    "amortize",
    "both_moratorium_modes",
    "dscr_by_year",
    "list_templates",
    "load_template",
    "quarterly_instalment",
    "right_size",
    "route",
]

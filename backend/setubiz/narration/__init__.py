"""Language layer. It explains the facts object; it never adds to it (PLAN.md §2, §3)."""

from setubiz.narration.base import Narrator, Report, ReportSection
from setubiz.narration.pipeline import CATCH_RATE, narrate
from setubiz.narration.template_narrator import TemplateNarrator
from setubiz.narration.validator import (
    CatchRate,
    NumericGroundingValidator,
    ValidationReport,
    extract_numbers,
)

__all__ = [
    "CATCH_RATE",
    "CatchRate",
    "Narrator",
    "NumericGroundingValidator",
    "Report",
    "ReportSection",
    "TemplateNarrator",
    "ValidationReport",
    "extract_numbers",
    "narrate",
]

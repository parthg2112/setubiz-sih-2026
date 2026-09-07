"""Language layer. It explains the facts object; it never adds to it (PLAN.md §2, §3)."""

from setubiz.narration.base import Narrator, Report, ReportSection
from setubiz.narration.llm_narrator import LlmNarrator
from setubiz.narration.local_narrator import LocalLlamaNarrator
from setubiz.narration.paraphrase import ParaphraseNarrator
from setubiz.narration.pipeline import CATCH_RATE, narrate, select_narrator
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
    "LlmNarrator",
    "LocalLlamaNarrator",
    "Narrator",
    "NumericGroundingValidator",
    "ParaphraseNarrator",
    "Report",
    "ReportSection",
    "TemplateNarrator",
    "ValidationReport",
    "extract_numbers",
    "narrate",
    "select_narrator",
]

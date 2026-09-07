"""Narration entry point: pick a narrator, validate its output, record the catch rate."""

from __future__ import annotations

from dataclasses import dataclass

from setubiz.facts.builder import Facts
from setubiz.narration.base import Report
from setubiz.narration.llm_narrator import LlmNarrator
from setubiz.narration.template_narrator import TemplateNarrator
from setubiz.narration.validator import CatchRate, NumericGroundingValidator, ValidationReport
from setubiz.schemas import Language

#: Process-wide counter surfaced at /api/v1/metrics — the "validator caught N%" claim.
CATCH_RATE = CatchRate()


@dataclass(frozen=True)
class NarrationResult:
    report: Report
    validation: ValidationReport


def narrate(
    facts: Facts, language: Language = Language.EN, *, use_llm: bool | None = None
) -> NarrationResult:
    """Narrate and validate. The template lane is the default and the fallback."""
    wants_llm = LlmNarrator.available() if use_llm is None else use_llm
    narrator = LlmNarrator() if wants_llm and LlmNarrator.available() else TemplateNarrator()

    report = narrator.narrate(facts, language)
    validation = NumericGroundingValidator().validate(report.prose, facts)
    CATCH_RATE.record(validation)
    return NarrationResult(report=report, validation=validation)

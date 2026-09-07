"""Narration entry point: pick a lane, validate its output, record the catch rate.

The ladder is cloud, then local, then template. Every rung is validated identically, so the
catch-rate metric stays comparable across lanes, and the bottom rung always works: the template
narrator needs no network, no key and no weights.
"""

from __future__ import annotations

from dataclasses import dataclass

from setubiz.facts.builder import Facts
from setubiz.narration.base import Narrator, Report
from setubiz.narration.llm_narrator import LlmNarrator
from setubiz.narration.local_narrator import LocalLlamaNarrator
from setubiz.narration.template_narrator import TemplateNarrator
from setubiz.narration.validator import CatchRate, NumericGroundingValidator, ValidationReport
from setubiz.schemas import Language

#: Process-wide counter surfaced at /api/v1/metrics: the "validator caught N%" claim.
CATCH_RATE = CatchRate()


@dataclass(frozen=True)
class NarrationResult:
    report: Report
    validation: ValidationReport


def select_narrator(use_llm: bool | None = None) -> Narrator:
    """Highest available rung. `use_llm=False` forces the deterministic lane."""
    if use_llm is False:
        return TemplateNarrator()
    if LlmNarrator.available():
        return LlmNarrator()
    if LocalLlamaNarrator.available():
        return LocalLlamaNarrator()
    return TemplateNarrator()


def narrate(
    facts: Facts, language: Language = Language.EN, *, use_llm: bool | None = None
) -> NarrationResult:
    """Narrate and validate. The template lane is the default and the fallback."""
    narrator = select_narrator(use_llm)
    report = narrator.narrate(facts, language)
    validation = NumericGroundingValidator().validate(report.prose, facts)
    CATCH_RATE.record(validation)
    return NarrationResult(report=report, validation=validation)

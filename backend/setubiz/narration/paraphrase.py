"""Shared machinery for the two generative lanes, cloud and local (PLAN.md §3).

Both lanes obey the same contract: they **paraphrase the deterministic template report**, they are
never given freedom to compute, and every generation is checked by the numeric-grounding validator
before it is allowed on screen. A generation that fails is regenerated; if every attempt fails, the
template report ships unchanged. There is therefore no input under which a generative lane can make
the output worse than the offline one.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from setubiz.config import get_settings
from setubiz.facts.builder import Facts
from setubiz.narration.base import Report, ReportSection
from setubiz.narration.template_narrator import TemplateNarrator
from setubiz.narration.validator import NumericGroundingValidator, ValidationReport
from setubiz.schemas import Language

SYSTEM_PROMPT = """\
You rewrite a rural business advisory report so a first-time entrepreneur with limited schooling \
can follow it. You are a translator of tone, not an analyst.

Absolute rules:
- Never introduce a number, percentage, ratio or amount that is not already in the draft.
- Never remove a number that is in the draft.
- Never change a verdict, a recommendation, or the direction of a comparison.
- Never add advice, causes, predictions or context that is not in the draft.
- Keep every section, in order, with the same section ids.
- Short sentences. Plain words. No marketing tone. No emoji. Never use an em dash.
"""


def sections_schema(section_ids: list[str]) -> dict[str, Any]:
    """JSON schema for the rewritten sections. Anti-hallucination layer 1 on the cloud lane."""
    return {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["sections"],
            "properties": {
                "sections": {
                    "type": "array",
                    "minItems": len(section_ids),
                    "maxItems": len(section_ids),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "body"],
                        "properties": {
                            "id": {"type": "string", "enum": section_ids},
                            "body": {"type": "string"},
                        },
                    },
                }
            },
        },
    }


class ParaphraseNarrator(ABC):
    """Template draft in, validated paraphrase out, template draft on any doubt."""

    name: str

    def __init__(self, validator: NumericGroundingValidator | None = None) -> None:
        self.validator = validator or NumericGroundingValidator()
        self.base = TemplateNarrator()
        self.last_validation: ValidationReport | None = None
        self.attempts_used = 0

    @staticmethod
    @abstractmethod
    def available() -> bool:
        """True only when this lane can actually run right now."""

    @abstractmethod
    def _generate(self, payload: str, section_ids: list[str]) -> str | None:
        """Return the model's raw JSON text, or None if the lane could not produce one."""

    def narrate(self, facts: Facts, language: Language = Language.EN) -> Report:
        draft = self.base.narrate(facts, language)
        if not self.available():
            return draft

        section_ids = [s.id for s in draft.sections]
        payload = json.dumps(
            {
                "language": language.value,
                "sections": [{"id": s.id, "body": s.body} for s in draft.sections],
            },
            ensure_ascii=False,
        )

        for attempt in range(1, get_settings().llm_max_attempts + 1):
            self.attempts_used = attempt
            text = self._generate(payload, section_ids)
            if text is None:
                return draft

            try:
                rewritten = {s["id"]: s["body"] for s in json.loads(text)["sections"]}
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

            prose = " ".join(rewritten.get(s.id, s.body) for s in draft.sections)
            report = self.validator.validate(prose, facts)
            self.last_validation = report
            if not report.passed:
                continue  # layer 2 caught it: regenerate rather than ship a wrong number

            return Report(
                language=language,
                narrator=self.name,
                sections=tuple(
                    ReportSection(
                        id=s.id,
                        heading=s.heading,
                        body=rewritten.get(s.id, s.body),
                        cites=s.cites,
                        data=s.data,
                    )
                    for s in draft.sections
                ),
            )

        return draft  # every attempt was caught: ship the deterministic report

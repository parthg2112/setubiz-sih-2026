"""Optional LLM narration lane, off by default (PLAN.md §3).

Three anti-hallucination layers, in order:
  1. Structured output — `output_config.format` makes a schema-invalid response impossible.
     (This is the cloud equivalent of the GBNF grammar constraint on the local llama.cpp lane.)
  2. Numeric grounding — every figure must exist in `facts.numeric_index`, else regenerate.
  3. Verdict fidelity — eligibility and loan verdicts are copied from the facts object, never
     restated by the model, so they cannot drift.

The model paraphrases the template narrator's own output. It is never given freedom to compute.
"""

from __future__ import annotations

import json
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
- Short sentences. Plain words. No marketing tone. No emoji.
"""


def _schema(section_ids: list[str]) -> dict[str, Any]:
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


class LlmNarrator:
    """Paraphrases the template report. Falls back to it whenever anything is off."""

    name = "llm"

    def __init__(self, validator: NumericGroundingValidator | None = None) -> None:
        self.validator = validator or NumericGroundingValidator()
        self.base = TemplateNarrator()
        self.last_validation: ValidationReport | None = None
        self.attempts_used = 0

    @staticmethod
    def available() -> bool:
        settings = get_settings()
        if not settings.llm_enabled:
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def narrate(self, facts: Facts, language: Language = Language.EN) -> Report:
        draft = self.base.narrate(facts, language)
        if not self.available():
            return draft

        import anthropic

        settings = get_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        section_ids = [s.id for s in draft.sections]
        payload = json.dumps(
            {"language": language.value, "sections": [{"id": s.id, "body": s.body} for s in draft.sections]},
            ensure_ascii=False,
        )

        for attempt in range(1, settings.llm_max_attempts + 1):
            self.attempts_used = attempt
            try:
                response = client.messages.create(
                    model=settings.llm_model,
                    max_tokens=16000,
                    system=SYSTEM_PROMPT,
                    thinking={"type": "adaptive"},
                    output_config={"effort": settings.llm_effort, "format": _schema(section_ids)},
                    messages=[{"role": "user", "content": payload}],
                )
            except Exception:  # network, auth, rate limit — the offline lane must still work
                return draft

            if response.stop_reason == "refusal":
                return draft

            text = "".join(b.text for b in response.content if b.type == "text")
            try:
                rewritten = {s["id"]: s["body"] for s in json.loads(text)["sections"]}
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

            prose = " ".join(rewritten.get(s.id, s.body) for s in draft.sections)
            report = self.validator.validate(prose, facts)
            self.last_validation = report
            if not report.passed:
                continue  # layer 2 caught it — regenerate rather than ship a wrong number

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

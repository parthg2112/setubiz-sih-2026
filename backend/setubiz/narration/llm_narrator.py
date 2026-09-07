"""Cloud narration lane, off by default (PLAN.md §3).

Anti-hallucination layer 1 here is `output_config.format`: the response is constrained to the
section schema, so a schema-invalid generation is structurally impossible. Layers 2 and 3 (numeric
grounding, verdict fidelity) live in `paraphrase.ParaphraseNarrator` and apply to every lane.
"""

from __future__ import annotations

from setubiz.config import get_settings
from setubiz.narration.paraphrase import SYSTEM_PROMPT, ParaphraseNarrator, sections_schema


class LlmNarrator(ParaphraseNarrator):
    name = "llm"

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

    def _generate(self, payload: str, section_ids: list[str]) -> str | None:
        import anthropic

        settings = get_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        try:
            response = client.messages.create(
                model=settings.llm_model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                thinking={"type": "adaptive"},
                output_config={
                    "effort": settings.llm_effort,
                    "format": sections_schema(section_ids),
                },
                messages=[{"role": "user", "content": payload}],
            )
        except Exception:  # network, auth, rate limit: the offline lane must still work
            return None

        if response.stop_reason == "refusal":
            return None
        return "".join(b.text for b in response.content if b.type == "text")

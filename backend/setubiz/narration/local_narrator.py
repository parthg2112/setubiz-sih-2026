"""Offline narration lane: Llama 3.1 8B Instruct Q4_K_M via llama.cpp (PLAN.md §3, §10).

This is the answer to "what happens when the network dies at the venue", and the CSC/VLE story
where a shared terminal has no reliable uplink. The weights are not shipped; the lane advertises
itself as unavailable until a GGUF is present, and the deterministic template report serves in the
meantime.

Anti-hallucination layer 1 on this lane is a **GBNF grammar**, exactly as PLAN.md §3 specifies:
llama.cpp constrains sampling to the grammar, so a response that is not the section object cannot
be produced at all, rather than being rejected after the fact.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from setubiz.config import get_settings
from setubiz.narration.paraphrase import SYSTEM_PROMPT, ParaphraseNarrator


def sections_grammar(section_ids: list[str]) -> str:
    """GBNF for `{"sections": [{"id": <one of the ids>, "body": "..."}, ...]}`.

    Each entry is pinned to its own id in order, so the model can neither reorder, drop nor invent
    a section. Only the body text is free, which is the only thing this lane is allowed to change.
    """
    if not section_ids:
        raise ValueError("cannot build a grammar with no sections")

    entries = ' "," ws '.join(f"entry-{i}" for i in range(len(section_ids)))
    rules = [
        'root ::= "{" ws "\\"sections\\"" ws ":" ws "[" ws ' + entries + ' ws "]" ws "}"',
        "ws ::= [ \\t\\n]*",
        # A JSON string body: printable characters and the standard escapes, no control bytes.
        'body ::= "\\"" ( [^"\\\\\\x00-\\x1F] | "\\\\" ["\\\\/bfnrt] )* "\\""',
    ]
    for i, section_id in enumerate(section_ids):
        rules.append(
            f'entry-{i} ::= "{{" ws "\\"id\\"" ws ":" ws "\\"{section_id}\\"" ws "," ws '
            '"\\"body\\"" ws ":" ws body ws "}"'
        )
    return "\n".join(rules)


def model_path() -> Path | None:
    configured = get_settings().local_llm_model_path
    if configured is None:
        return None
    path = Path(configured).expanduser()
    return path if path.is_file() else None


@lru_cache(maxsize=1)
def _load_model(path: str, n_ctx: int, threads: int | None) -> Any:
    """Loading an 8B GGUF takes seconds and hundreds of MB, so do it once per process."""
    from llama_cpp import Llama

    return Llama(
        model_path=path,
        n_ctx=n_ctx,
        n_threads=threads,
        verbose=False,  # llama.cpp is chatty and the CLI report must stay readable
    )


class LocalLlamaNarrator(ParaphraseNarrator):
    name = "local_llama"

    @staticmethod
    def available() -> bool:
        settings = get_settings()
        if not settings.local_llm_enabled:
            return False
        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            return False
        return model_path() is not None

    def _generate(self, payload: str, section_ids: list[str]) -> str | None:
        from llama_cpp import LlamaGrammar

        settings = get_settings()
        path = model_path()
        if path is None:  # pragma: no cover - available() already checked this
            return None

        try:
            model = _load_model(str(path), settings.local_llm_n_ctx, settings.local_llm_threads)
            grammar = LlamaGrammar.from_string(sections_grammar(section_ids), verbose=False)
            response = model.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": payload},
                ],
                grammar=grammar,
                max_tokens=settings.local_llm_max_tokens,
                temperature=0.2,  # paraphrase, do not invent
            )
        except Exception:  # a missing backend, an OOM, a corrupt GGUF: fall back, never crash
            return None

        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):  # pragma: no cover - shape is llama.cpp's
            return None


def describe() -> dict[str, Any]:
    """What `/api/v1/metrics` reports about this lane."""
    settings = get_settings()
    path = model_path()
    try:
        import llama_cpp  # noqa: F401

        runtime = True
    except ImportError:
        runtime = False
    return {
        "enabled": settings.local_llm_enabled,
        "runtime_installed": runtime,
        "weights_present": path is not None,
        "model_path": str(path) if path else None,
        "available": LocalLlamaNarrator.available(),
    }


__all__ = ["LocalLlamaNarrator", "describe", "model_path", "sections_grammar"]

"""The offline narration lane (PLAN.md §3, §10).

The weights are a 4.7 GB download this repo does not ship, so what is tested here is everything
that does not need them: the GBNF grammar, the availability gate, the fallback, and the promise
that turning the lane on can never make the demo worse. Generation quality on the real model is
explicitly unverified; see docs/PRD-COVERAGE.md.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from setubiz.config import get_settings
from setubiz.facts import build_facts
from setubiz.narration import narrate, select_narrator
from setubiz.narration.local_narrator import (
    LocalLlamaNarrator,
    describe,
    model_path,
    sections_grammar,
)
from setubiz.narration.paraphrase import sections_schema
from setubiz.schemas import AdvisoryRequest, Language

SECTIONS = ["headline", "market_reach", "loan_structure"]


@pytest.fixture
def facts():
    return build_facts(
        AdvisoryRequest(
            village_query="Ormanji",
            savings=Decimal("100000"),
            business_category="dairy",
            social_category="sc",
            annual_family_income=Decimal("280000"),
        )
    )


# --- GBNF grammar ---


def test_grammar_pins_every_section_id_in_order():
    grammar = sections_grammar(SECTIONS)
    for i, section_id in enumerate(SECTIONS):
        assert f"entry-{i} ::=" in grammar
        assert f'\\"{section_id}\\"' in grammar
    # The root must chain the entries in the declared order, so nothing can be reordered.
    root = next(line for line in grammar.splitlines() if line.startswith("root ::="))
    positions = [root.index(f"entry-{i}") for i in range(len(SECTIONS))]
    assert positions == sorted(positions)


def _rule_references(body: str) -> set[str]:
    """Identifiers in a GBNF rule body, ignoring string literals and character classes.

    A regex cannot do this: the grammar is full of escaped quotes (`\\"id\\"`) and character-class
    escapes (`\\x00-\\x1F`) whose innards look exactly like rule names.
    """
    names, buffer = set(), ""
    in_string = in_class = escaped = False
    for ch in body:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if in_string:
            in_string = ch != '"'
            continue
        if in_class:
            in_class = ch != "]"
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "[":
            in_class = True
            continue
        if ch.isalnum() or ch in "-_":
            buffer += ch
            continue
        if buffer:
            names.add(buffer)
            buffer = ""
    if buffer:
        names.add(buffer)
    return names


def test_grammar_declares_every_rule_it_references():
    grammar = sections_grammar(SECTIONS)
    defined = {line.split("::=")[0].strip() for line in grammar.splitlines() if "::=" in line}
    referenced: set[str] = set()
    for line in grammar.splitlines():
        if "::=" in line:
            referenced |= _rule_references(line.split("::=", 1)[1])
    assert referenced <= defined, f"undefined rules: {sorted(referenced - defined)}"
    assert {"root", "ws", "body"} <= defined
    assert all(f"entry-{i}" in defined for i in range(len(SECTIONS)))


def test_grammar_body_rule_excludes_raw_control_characters():
    """A raw newline inside a JSON string would make the response unparseable."""
    body = next(line for line in sections_grammar(SECTIONS).splitlines() if line.startswith("body"))
    assert "\\x00-\\x1F" in body


def test_grammar_rejects_an_empty_section_list():
    with pytest.raises(ValueError, match="no sections"):
        sections_grammar([])


def test_grammar_and_cloud_schema_agree_on_the_section_set():
    """Both lanes must accept exactly the same shape, or the two reports would diverge."""
    schema = sections_schema(SECTIONS)
    item = schema["schema"]["properties"]["sections"]["items"]
    assert item["properties"]["id"]["enum"] == SECTIONS
    grammar = sections_grammar(SECTIONS)
    assert all(f'\\"{s}\\"' in grammar for s in SECTIONS)


# --- availability gate ---


def test_lane_is_off_by_default():
    assert get_settings().local_llm_enabled is False
    assert LocalLlamaNarrator.available() is False
    assert model_path() is None


def test_enabling_without_weights_does_not_make_it_available(monkeypatch):
    monkeypatch.setenv("SETUBIZ_LOCAL_LLM_ENABLED", "1")
    get_settings.cache_clear()
    assert get_settings().local_llm_enabled is True
    assert LocalLlamaNarrator.available() is False  # no GGUF configured


def test_a_configured_path_that_does_not_exist_is_not_weights(monkeypatch, tmp_path):
    monkeypatch.setenv("SETUBIZ_LOCAL_LLM_ENABLED", "1")
    monkeypatch.setenv("SETUBIZ_LOCAL_LLM_MODEL_PATH", str(tmp_path / "missing.gguf"))
    get_settings.cache_clear()
    assert model_path() is None
    assert LocalLlamaNarrator.available() is False


def test_a_directory_is_not_weights(monkeypatch, tmp_path):
    monkeypatch.setenv("SETUBIZ_LOCAL_LLM_ENABLED", "1")
    monkeypatch.setenv("SETUBIZ_LOCAL_LLM_MODEL_PATH", str(tmp_path))
    get_settings.cache_clear()
    assert model_path() is None


def test_describe_reports_the_lane_state_for_metrics():
    state = describe()
    assert state["enabled"] is False
    assert state["weights_present"] is False
    assert state["available"] is False
    assert set(state) == {
        "enabled",
        "runtime_installed",
        "weights_present",
        "model_path",
        "available",
    }


# --- fallback behaviour ---


def test_narrating_without_weights_returns_the_template_report(facts):
    report = LocalLlamaNarrator().narrate(facts, Language.EN)
    assert report.narrator == "template"
    assert report.sections


def test_enabling_the_lane_without_weights_never_breaks_the_demo(facts, monkeypatch):
    monkeypatch.setenv("SETUBIZ_LOCAL_LLM_ENABLED", "1")
    get_settings.cache_clear()
    result = narrate(facts, Language.HI)
    assert result.report.narrator == "template"
    assert result.validation.passed is True


def test_a_generation_failure_falls_back_rather_than_raising(facts, monkeypatch):
    """`_generate` returning None is the "the lane could not run" signal."""
    narrator = LocalLlamaNarrator()
    monkeypatch.setattr(LocalLlamaNarrator, "available", staticmethod(lambda: True))
    monkeypatch.setattr(narrator, "_generate", lambda payload, ids: None)
    assert narrator.narrate(facts, Language.EN).narrator == "template"


def test_unparseable_output_is_retried_then_falls_back(facts, monkeypatch):
    attempts: list[str] = []
    narrator = LocalLlamaNarrator()
    monkeypatch.setattr(LocalLlamaNarrator, "available", staticmethod(lambda: True))
    monkeypatch.setattr(
        narrator, "_generate", lambda payload, ids: attempts.append("x") or "not json"
    )
    assert narrator.narrate(facts, Language.EN).narrator == "template"
    assert len(attempts) == get_settings().llm_max_attempts


def test_an_ungrounded_paraphrase_is_rejected(facts, monkeypatch):
    """The whole point: a fluent local model inventing a figure must not reach the screen."""
    narrator = LocalLlamaNarrator()
    monkeypatch.setattr(LocalLlamaNarrator, "available", staticmethod(lambda: True))
    monkeypatch.setattr(
        narrator,
        "_generate",
        lambda payload, ids: json.dumps(
            {"sections": [{"id": s, "body": "There are 8,421 dairies here."} for s in ids]}
        ),
    )
    report = narrator.narrate(facts, Language.EN)
    assert report.narrator == "template"
    assert narrator.last_validation is not None
    assert narrator.last_validation.passed is False


def test_a_grounded_paraphrase_is_accepted(facts, monkeypatch):
    narrator = LocalLlamaNarrator()
    monkeypatch.setattr(LocalLlamaNarrator, "available", staticmethod(lambda: True))
    monkeypatch.setattr(
        narrator,
        "_generate",
        lambda payload, ids: json.dumps(
            {"sections": [{"id": s, "body": "Plain words, no new numbers."} for s in ids]}
        ),
    )
    report = narrator.narrate(facts, Language.EN)
    assert report.narrator == "local_llama"
    assert all(s.body == "Plain words, no new numbers." for s in report.sections)
    # Headings, citations and chart payloads come from the deterministic draft, never the model.
    assert all(s.cites or s.id == "data_note" for s in report.sections)
    assert report.section("stress").data


# --- the ladder ---


def test_the_ladder_falls_all_the_way_to_the_template_lane():
    assert select_narrator().name == "template"
    assert select_narrator(use_llm=False).name == "template"


def test_local_lane_is_chosen_when_it_is_the_only_one_available(monkeypatch):
    monkeypatch.setattr(LocalLlamaNarrator, "available", staticmethod(lambda: True))
    assert select_narrator().name == "local_llama"
    # An explicit opt-out still forces the deterministic lane.
    assert select_narrator(use_llm=False).name == "template"

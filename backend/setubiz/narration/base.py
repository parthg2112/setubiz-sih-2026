"""The language layer's contract: it explains, it never decides (PLAN.md §2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from setubiz.facts.builder import Facts
from setubiz.schemas import Language


@dataclass(frozen=True)
class ReportSection:
    id: str
    heading: str
    body: str
    cites: tuple[str, ...] = ()
    #: Structured payload for the UI (chart series, tables). Never narrated prose.
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Report:
    language: Language
    narrator: str
    sections: tuple[ReportSection, ...]

    def section(self, section_id: str) -> ReportSection | None:
        return next((s for s in self.sections if s.id == section_id), None)

    @property
    def prose(self) -> str:
        return "\n\n".join(f"{s.heading}\n{s.body}" for s in self.sections)


@runtime_checkable
class Narrator(Protocol):
    name: str

    def narrate(self, facts: Facts, language: Language) -> Report: ...

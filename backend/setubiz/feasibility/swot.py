"""SWOT from a rule library over computed metrics — never from a language model (PLAN.md §4).

Conditions are evaluated by a tiny comparator interpreter, not `eval`, so a YAML file can never
become code execution. Every emitted line carries the source ids it depends on.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from typing import Any

import yaml

from setubiz.config import get_settings

QUADRANTS = ("strength", "weakness", "opportunity", "threat")

_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}


@dataclass(frozen=True)
class SwotItem:
    id: str
    quadrant: str
    text_en: str
    text_hi: str
    cites: tuple[str, ...]


@dataclass(frozen=True)
class Swot:
    items: tuple[SwotItem, ...]
    metrics: dict[str, Any]

    def by_quadrant(self, quadrant: str) -> tuple[SwotItem, ...]:
        return tuple(i for i in self.items if i.quadrant == quadrant)

    @property
    def strengths(self) -> tuple[SwotItem, ...]:
        return self.by_quadrant("strength")

    @property
    def weaknesses(self) -> tuple[SwotItem, ...]:
        return self.by_quadrant("weakness")

    @property
    def opportunities(self) -> tuple[SwotItem, ...]:
        return self.by_quadrant("opportunity")

    @property
    def threats(self) -> tuple[SwotItem, ...]:
        return self.by_quadrant("threat")


@lru_cache
def load_rules() -> tuple[dict[str, Any], ...]:
    path = get_settings().data_dir / "swot_rules.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = tuple(doc["rules"])
    for rule in rules:
        if rule["quadrant"] not in QUADRANTS:
            raise ValueError(f"rule {rule['id']!r} has unknown quadrant {rule['quadrant']!r}")
    return rules


def _compare(condition: dict[str, Any], metrics: dict[str, Any]) -> bool:
    metric, op, value = condition["metric"], condition["op"], condition["value"]
    if op not in _OPS:
        raise ValueError(f"unsupported operator {op!r} in SWOT rules")
    if metric not in metrics:
        return False
    left = metrics[metric]
    if left is None:
        return False
    if isinstance(left, Decimal) and isinstance(value, (int, float)):
        value = Decimal(str(value))
    elif isinstance(left, float) and isinstance(value, (int, float)):
        value = float(value)
    return bool(_OPS[op](left, value))


def _matches(when: dict[str, Any], metrics: dict[str, Any]) -> bool:
    if "all" in when:
        return all(_matches(c, metrics) for c in when["all"])
    if "any" in when:
        return any(_matches(c, metrics) for c in when["any"])
    return _compare(when, metrics)


def evaluate(metrics: dict[str, Any]) -> Swot:
    """Fire every rule whose condition holds. Deterministic, ordered, explainable."""
    items: list[SwotItem] = []
    for rule in load_rules():
        if not _matches(rule["when"], metrics):
            continue
        items.append(
            SwotItem(
                id=rule["id"],
                quadrant=rule["quadrant"],
                text_en=" ".join(rule["text_en"].format(**metrics).split()),
                text_hi=" ".join(rule["text_hi"].format(**metrics).split()),
                cites=tuple(rule.get("cites", ())),
            )
        )
    return Swot(items=tuple(items), metrics=metrics)

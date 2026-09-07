"""NABARD-style Model Bankable Project cost templates (PLAN.md §5, §6).

A template turns "I want to start a dairy" into a defensible *required capital* and a monthly
cash-flow line — the numerator of DSCR. Values are unit-economics, not predictions.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from setubiz.config import get_settings
from setubiz.finance.router import ActivityKind
from setubiz.money import ZERO, q


class LineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item: str
    item_hi: str | None = None
    amount: Decimal


class CostTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    name_hi: str | None = None
    category: str
    unit: str
    activity_kind: ActivityKind = ActivityKind.GENERAL
    source: str
    fixed_capital: tuple[LineItem, ...]
    working_capital_months: int = 3
    monthly_revenue: tuple[LineItem, ...]
    monthly_opex: tuple[LineItem, ...]
    assumptions: tuple[str, ...] = ()

    @property
    def fixed_capital_total(self) -> Decimal:
        return q(sum((li.amount for li in self.fixed_capital), ZERO))

    @property
    def monthly_revenue_total(self) -> Decimal:
        return q(sum((li.amount for li in self.monthly_revenue), ZERO))

    @property
    def monthly_opex_total(self) -> Decimal:
        return q(sum((li.amount for li in self.monthly_opex), ZERO))

    @property
    def working_capital(self) -> Decimal:
        return q(self.monthly_opex_total * self.working_capital_months)

    @property
    def required_capital(self) -> Decimal:
        return q(self.fixed_capital_total + self.working_capital)

    @property
    def monthly_net(self) -> Decimal:
        return q(self.monthly_revenue_total - self.monthly_opex_total)

    @property
    def annual_noi(self) -> Decimal:
        """Net operating income before debt service — the DSCR numerator."""
        return q(self.monthly_net * 12)

    def scaled(self, units: Decimal | int) -> CostTemplate:
        """Linear scaling of a one-unit template (2 cows → 4 cows). Coarse but auditable."""
        f = Decimal(units)
        if f <= 0:
            raise ValueError("units must be positive")

        def _scale(items: tuple[LineItem, ...]) -> tuple[LineItem, ...]:
            return tuple(li.model_copy(update={"amount": q(li.amount * f)}) for li in items)

        return self.model_copy(
            update={
                "fixed_capital": _scale(self.fixed_capital),
                "monthly_revenue": _scale(self.monthly_revenue),
                "monthly_opex": _scale(self.monthly_opex),
                "unit": f"{self.unit} × {units}",
            }
        )


def _templates_dir() -> Path:
    return get_settings().data_dir / "cost_templates"


@lru_cache
def _load_all() -> dict[str, CostTemplate]:
    out: dict[str, CostTemplate] = {}
    for path in sorted(_templates_dir().glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        tpl = CostTemplate.model_validate(raw)
        out[tpl.id] = tpl
    return out


def list_templates() -> list[CostTemplate]:
    return list(_load_all().values())


def load_template(template_id: str) -> CostTemplate:
    templates = _load_all()
    if template_id not in templates:
        raise KeyError(f"unknown cost template {template_id!r}; have {sorted(templates)}")
    return templates[template_id]


def find_template_for_category(category: str) -> CostTemplate | None:
    for tpl in _load_all().values():
        if tpl.category == category:
            return tpl
    return None

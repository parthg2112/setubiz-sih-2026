"""NABARD-style Model Bankable Project cost templates (PLAN.md §5, §6).

A template turns "I want to start a dairy" into a defensible *required capital* and a monthly
cash-flow line — the numerator of DSCR. Values are unit-economics, not predictions.
"""

from __future__ import annotations

import math
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from setubiz.config import get_settings
from setubiz.finance.router import ActivityKind
from setubiz.money import ZERO, q

#: How a line item responds to a change in unit size.
#:
#: ``linear`` -- the cost is per unit: two cows cost twice one cow.
#: ``step``   -- one purchase serves up to ``step_capacity`` units, then another is needed. A shed
#:               built for four animals costs the same whether one or four stand in it.
#: ``fixed``  -- the cost never changes: a licence fee is a licence fee.
Scaling = Literal["linear", "step", "fixed"]


class LineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item: str
    item_hi: str | None = None
    amount: Decimal
    scaling: Scaling = "linear"
    #: Units covered by one purchase. Required for ``step``, meaningless otherwise.
    step_capacity: int | None = None

    @model_validator(mode="after")
    def _step_needs_a_capacity(self) -> LineItem:
        if self.scaling == "step" and (self.step_capacity is None or self.step_capacity < 1):
            raise ValueError(f"{self.item!r}: step scaling needs a step_capacity of 1 or more")
        return self

    def at_units(self, units: int, base_units: int) -> Decimal:
        """This item's amount when the unit is sized at ``units`` instead of ``base_units``.

        Every branch is the identity at ``units == base_units``, which is what makes the existing
        published figures a regression test rather than a coincidence.
        """
        if self.scaling == "fixed":
            return self.amount
        if self.scaling == "step":
            capacity = self.step_capacity or 1
            purchases = math.ceil(units / capacity)
            base_purchases = math.ceil(base_units / capacity)
            return q(self.amount * Decimal(purchases) / Decimal(base_purchases))
        return q(self.amount * Decimal(units) / Decimal(base_units))


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

    #: How many units the published amounts above describe. `dairy_2_animal` is two animals, so
    #: its figures are a two-animal unit and `at_units(1)` halves the per-animal lines.
    base_units: int = 1
    unit_label: str = "unit"
    unit_label_hi: str | None = None
    #: Inclusive bounds the size search may enumerate. Kept in the template because the sensible
    #: range is a property of the trade, not of the applicant: a 12-animal backyard dairy is not a
    #: smaller version of the same business.
    unit_range: tuple[int, int] = (1, 1)
    #: Granularity of the search. Animals and machines come one at a time; birds come by the
    #: batch, so poultry steps in 250s rather than offering 1,751 indistinguishable sizes.
    unit_step: int = 1

    @model_validator(mode="after")
    def _range_is_sane(self) -> CostTemplate:
        low, high = self.unit_range
        if low < 1 or high < low:
            raise ValueError(f"{self.id}: unit_range must be ascending and positive")
        if self.unit_step < 1:
            raise ValueError(f"{self.id}: unit_step must be positive")
        return self

    def candidate_sizes(self) -> tuple[int, ...]:
        """The sizes the search may consider, always including the published base size."""
        low, high = self.unit_range
        sizes = set(range(low, high + 1, self.unit_step))
        sizes.add(self.base_units)
        return tuple(sorted(s for s in sizes if low <= s <= high))

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

    @property
    def has_labour_line(self) -> bool:
        """Whether opex already pays the household for its own work.

        Four of the five templates cost labour explicitly, so their `annual_noi` is already net of
        what the family draws. `backyard_poultry` does not, and treating its surplus as retained
        earnings would quietly assume the family lives on nothing.
        """
        return any(
            "labour" in li.item.lower() or "wage" in li.item.lower() or "help" in li.item.lower()
            for li in self.monthly_opex
        )

    def at_units(self, units: int) -> CostTemplate:
        """The same business costed at a different size.

        Per-line-item rules, not a blanket multiplier: the cows scale, the shed steps, the chaff
        cutter does not move. `working_capital_months` is a duration and never scales; working
        capital moves because opex does.
        """
        if units < 1:
            raise ValueError("units must be positive")

        def _scale(items: tuple[LineItem, ...]) -> tuple[LineItem, ...]:
            return tuple(
                li.model_copy(update={"amount": li.at_units(units, self.base_units)})
                for li in items
            )

        if units == self.base_units:
            return self
        return self.model_copy(
            update={
                "fixed_capital": _scale(self.fixed_capital),
                "monthly_revenue": _scale(self.monthly_revenue),
                "monthly_opex": _scale(self.monthly_opex),
                "base_units": units,
                "unit": f"{units} {self.unit_label}" + ("s" if units != 1 else ""),
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

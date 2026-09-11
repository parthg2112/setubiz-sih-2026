"""Which schemes may be held together (PLAN.md §5).

Applicants do not know that schemes combine. A concessional term loan can sit alongside a capital
subsidy; a guarantee cover can remove a collateral demand. The engine evaluated each scheme in
isolation, so nobody was ever told.

The governing rule here is asymmetric on purpose. Telling someone two schemes stack when they do
not is worse than telling them to check: they build a project cost around assistance that never
arrives, and discover it at the sanction counter. So `combinable` requires a citable source and
the model refuses to be constructed without one, while `needs_verification` is free.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from functools import lru_cache
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from setubiz.config import get_settings
from setubiz.eligibility.rules import EligibilityResult


class StackVerdict(str, Enum):
    COMBINABLE = "combinable"
    MUTUALLY_EXCLUSIVE = "mutually_exclusive"
    #: The honest default. No authoritative source found, so the applicant is told to confirm.
    NEEDS_VERIFICATION = "needs_verification"


class StackingRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    schemes: tuple[str, ...]
    verdict: StackVerdict = StackVerdict.NEEDS_VERIFICATION
    reason_en: str
    reason_hi: str
    source: str | None = None
    #: Which of the two must be sanctioned first, where that matters.
    sequencing: str | None = None
    #: Cap on total assistance when both are held.
    combined_cap: Decimal | None = None
    #: Percentage points the effective subsidy rises by. Null until someone produces a rate;
    #: the UI shows no percentage while it is null rather than computing one from prose.
    subsidy_delta_pct: Decimal | None = None

    @model_validator(mode="after")
    def _combinable_needs_a_source(self) -> StackingRule:
        if self.verdict is StackVerdict.COMBINABLE and not self.source:
            raise ValueError(
                f"{'+'.join(self.schemes)}: a combinable verdict needs a source. Without one the "
                "verdict is needs_verification."
            )
        if len(self.schemes) < 2:
            raise ValueError("a stacking rule needs at least two schemes")
        return self

    @property
    def key(self) -> frozenset[str]:
        return frozenset(self.schemes)


class SchemeCombination(BaseModel):
    """One pair as it will be shown, with the display names resolved."""

    model_config = ConfigDict(frozen=True)

    schemes: tuple[str, ...]
    names: tuple[str, ...]
    names_hi: tuple[str, ...]
    verdict: StackVerdict
    reason_en: str
    reason_hi: str
    source: str | None
    sequencing: str | None
    combined_cap: Decimal | None
    subsidy_delta_pct: Decimal | None


class StackingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    combinable: tuple[SchemeCombination, ...] = ()
    needs_verification: tuple[SchemeCombination, ...] = ()
    mutually_exclusive: tuple[SchemeCombination, ...] = ()
    #: Ids considered, so the report can say what was and was not looked at.
    considered: tuple[str, ...] = ()
    sources: tuple[str, ...] = ("mosje_corporations",)

    @property
    def any_combination(self) -> bool:
        return bool(self.combinable or self.needs_verification)


def _stacking_path():
    return get_settings().data_dir / "schemes" / "stacking.yaml"


@lru_cache
def _rules_doc() -> dict[str, Any]:
    path = _stacking_path()
    if not path.exists():
        return {"rules": []}
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@lru_cache
def stacking_rules() -> tuple[StackingRule, ...]:
    return tuple(StackingRule.model_validate(r) for r in _rules_doc().get("rules", ()))


def _rule_for(a: str, b: str) -> StackingRule | None:
    key = frozenset((a, b))
    for rule in stacking_rules():
        if rule.key == key:
            return rule
    return None


def combinations(eligibility: EligibilityResult, scheme_id: str | None) -> StackingResult:
    """Pair the applicant's routed scheme against every scheme the report already shows.

    This deliberately does not claim the applicant is *eligible* for the comparison schemes.
    Nothing in the codebase assesses PMEGP or CGTMSE eligibility, so the engine speaks only to
    whether two schemes may be held together, which is a different question and the one the
    applicant cannot look up for themselves.
    """
    if scheme_id is None:
        return StackingResult(considered=())

    others = tuple(s.id for s in eligibility.comparison)
    considered = (scheme_id, *others)

    combinable: list[SchemeCombination] = []
    needs_check: list[SchemeCombination] = []
    exclusive: list[SchemeCombination] = []
    by_id = {s.id: s for s in eligibility.comparison}

    for other in others:
        rule = _rule_for(scheme_id, other)
        if rule is None:
            continue
        scheme = by_id[other]
        combination = SchemeCombination(
            schemes=(scheme_id, other),
            names=(scheme_id.replace("_", " "), scheme.name),
            names_hi=(scheme_id.replace("_", " "), scheme.name_hi or scheme.name),
            verdict=rule.verdict,
            reason_en=rule.reason_en,
            reason_hi=rule.reason_hi,
            source=rule.source,
            sequencing=rule.sequencing,
            combined_cap=rule.combined_cap,
            subsidy_delta_pct=rule.subsidy_delta_pct,
        )
        if rule.verdict is StackVerdict.COMBINABLE:
            combinable.append(combination)
        elif rule.verdict is StackVerdict.MUTUALLY_EXCLUSIVE:
            exclusive.append(combination)
        else:
            needs_check.append(combination)

    return StackingResult(
        combinable=tuple(combinable),
        needs_verification=tuple(needs_check),
        mutually_exclusive=tuple(exclusive),
        considered=considered,
        sources=("mosje_corporations", *(c.schemes[1] for c in combinable)),
    )

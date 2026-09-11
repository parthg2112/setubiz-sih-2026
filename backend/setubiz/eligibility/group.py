"""Self-help group mode (PLAN.md §5).

Four women pooling Rs 25,000 each have Rs 1,00,000 of margin and a shared unit with better
economics than any of them could reach alone. The engine assumed a single applicant throughout.

Eligibility stays per member. A group is not an average: if one member's income is over the
ceiling, that is a fact about that member which the group has to deal with before filing, and
hiding it inside a group-level verdict would send them to the counter to find out.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from setubiz.config import get_settings
from setubiz.eligibility.rules import EligibilityResult, SocialCategory, Verdict, assess
from setubiz.money import ZERO, q
from setubiz.schemas import Advisory, GroupMember


class MemberAssessment(BaseModel):
    """One member's own verdict, kept whole rather than folded into a group average."""

    model_config = ConfigDict(frozen=True)

    index: int
    name: str | None
    social_category: str
    contribution: Decimal
    #: Share of the group instalment this member carries.
    liability: Decimal
    corporation_id: str | None
    corporation_name: str | None
    verdict: Verdict
    reasons: tuple[str, ...]
    conditions: tuple[str, ...]

    @property
    def qualifies(self) -> bool:
        return self.verdict is not Verdict.INELIGIBLE


class GroupEligibility(BaseModel):
    model_config = ConfigDict(frozen=True)

    members: tuple[MemberAssessment, ...]
    pooled_margin: Decimal
    liability_split: str
    #: Set only when every member routes to the same corporation.
    shared_corporation_id: str | None
    mixed_categories: bool
    #: Which routing policy was applied, or None when the rule has not been confirmed.
    routing_policy: str | None
    notes: tuple[Advisory, ...] = ()
    sources: tuple[str, ...] = ("mosje_corporations",)

    @property
    def qualifying(self) -> tuple[MemberAssessment, ...]:
        return tuple(m for m in self.members if m.qualifies)

    @property
    def failing(self) -> tuple[MemberAssessment, ...]:
        return tuple(m for m in self.members if not m.qualifies)

    @property
    def all_qualify(self) -> bool:
        return not self.failing


def _routing_path():
    return get_settings().data_dir / "schemes" / "shg_routing.yaml"


@lru_cache
def routing_doc() -> dict[str, Any]:
    path = _routing_path()
    if not path.exists():
        return {"policy": None}
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _liabilities(
    members: tuple[GroupMember, ...], instalment: Decimal, split: str
) -> tuple[Decimal, ...]:
    """Split the group instalment. Equal by default; proportional where the group agreed to it."""
    if instalment <= 0:
        return tuple(ZERO for _ in members)
    if split == "proportional":
        total = sum((m.contribution for m in members), ZERO)
        if total > 0:
            return tuple(q(instalment * m.contribution / total) for m in members)
    return tuple(q(instalment / Decimal(len(members))) for m in members)


def assess_group(
    members: tuple[GroupMember, ...],
    *,
    state: str | None = None,
    activity_category: str | None = None,
    instalment: Decimal = ZERO,
    liability_split: str = "equal",
) -> GroupEligibility:
    """Run the existing per-member assessment and report the group position without averaging."""
    shares = _liabilities(members, instalment, liability_split)

    assessments: list[MemberAssessment] = []
    for i, (member, liability) in enumerate(zip(members, shares, strict=True), start=1):
        result: EligibilityResult = assess(
            SocialCategory(member.social_category),
            member.annual_family_income,
            state=state,
            activity_category=activity_category,
            is_woman=member.is_woman,
        )
        assessments.append(
            MemberAssessment(
                index=i,
                name=member.name,
                social_category=member.social_category,
                contribution=member.contribution,
                liability=liability,
                corporation_id=result.corporation.id if result.corporation else None,
                corporation_name=result.corporation.name if result.corporation else None,
                verdict=result.verdict,
                reasons=result.reasons,
                conditions=result.conditions,
            )
        )

    corporations = {m.corporation_id for m in assessments if m.corporation_id}
    mixed = len(corporations) > 1
    shared = next(iter(corporations)) if len(corporations) == 1 else None

    doc = routing_doc()
    policy = doc.get("policy")

    notes: list[Advisory] = []
    if mixed and not policy:
        # The rule is a policy question, not something to infer from the lending rules.
        notes.append(
            Advisory(
                id="shg_routing_unconfirmed",
                text_en=doc.get("unconfirmed_en", "Confirm group routing with the SCA."),
                text_hi=doc.get("unconfirmed_hi", "समूह की रूटिंग एससीए से पुष्टि करें।"),
            )
        )
    failing = [m for m in assessments if not m.qualifies]
    if failing:
        names = ", ".join(m.name or f"member {m.index}" for m in failing)
        notes.append(
            Advisory(
                id="shg_member_ineligible",
                text_en=(
                    f"{names} does not currently qualify. The group can still apply, but that "
                    f"member's share has to be resolved before filing."
                ),
                text_hi=(
                    f"{names} इस समय पात्र नहीं हैं। समूह फिर भी आवेदन कर सकता है, किंतु आवेदन "
                    f"से पहले उस सदस्य का हिस्सा तय करना होगा।"
                ),
            )
        )

    return GroupEligibility(
        members=tuple(assessments),
        pooled_margin=q(sum((m.contribution for m in members), ZERO)),
        liability_split=liability_split,
        shared_corporation_id=shared,
        mixed_categories=mixed,
        routing_policy=policy,
        notes=tuple(notes),
    )

"""Category-aware scheme routing and eligibility verdicts (PLAN.md §0.2, §5).

SC → NSFDC (₹5.00 L ceiling w.e.f. 07-01-2026) · safai karamchari → NSKFDC (no ceiling)
OBC/EBC → NBCFDC (₹3.00 L ceiling). Women is a cross-cutting flag, not a corporation.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from functools import lru_cache
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from setubiz.config import get_settings
from setubiz.money import format_inr, money


class SocialCategory(str, Enum):
    SC = "sc"
    ST = "st"
    SAFAI_KARAMCHARI = "safai_karamchari"
    OBC = "obc"
    EBC = "ebc"
    GENERAL = "general"


class Verdict(str, Enum):
    ELIGIBLE = "eligible"
    ELIGIBLE_WITH_CONDITIONS = "eligible_with_conditions"
    INELIGIBLE = "ineligible"


class Corporation(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    name_hi: str | None = None
    social_categories: tuple[str, ...]
    income_ceiling: Decimal | None = None
    income_ceiling_note: str | None = None
    max_loan: Decimal
    finance_share: Decimal
    portal: str
    source: str


class DocumentItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    en: str
    hi: str | None = None


class ComparisonScheme(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    name_hi: str | None = None
    ministry: str
    loan_range: tuple[Decimal, Decimal]
    collateral_free: bool
    highlights: tuple[str, ...]
    when_to_prefer: str
    #: Hindi mirror of `when_to_prefer`; the comparison cards pick it in a Hindi report.
    when_to_prefer_hi: str | None = None
    portal: str


class Sca(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: str
    state_code: str
    corporations: tuple[str, ...]
    name: str
    name_hi: str | None = None
    address: str
    channel: str


class EligibilityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    verdict: Verdict
    corporation: Corporation | None
    social_category: SocialCategory
    annual_family_income: Decimal | None
    income_ceiling: Decimal | None
    reasons: tuple[str, ...]
    #: Hindi mirrors of `reasons`, authored with them so a Hindi report never quotes English.
    reasons_hi: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    conditions_hi: tuple[str, ...] = ()
    documents: tuple[DocumentItem, ...] = ()
    sca: Sca | None = None
    handoffs: tuple[dict[str, Any], ...] = ()
    comparison: tuple[ComparisonScheme, ...] = ()
    is_woman: bool = False
    sources: tuple[str, ...] = ()


def _schemes_dir():
    return get_settings().data_dir / "schemes"


@lru_cache
def _corporations_doc() -> dict[str, Any]:
    return yaml.safe_load((_schemes_dir() / "corporations.yaml").read_text(encoding="utf-8"))


@lru_cache
def _comparison_doc() -> dict[str, Any]:
    return yaml.safe_load((_schemes_dir() / "comparison.yaml").read_text(encoding="utf-8"))


@lru_cache
def _sca_doc() -> dict[str, Any]:
    return yaml.safe_load((_schemes_dir() / "sca_directory.yaml").read_text(encoding="utf-8"))


@lru_cache
def corporations() -> tuple[Corporation, ...]:
    return tuple(Corporation.model_validate(c) for c in _corporations_doc()["corporations"])


@lru_cache
def comparison_schemes() -> tuple[ComparisonScheme, ...]:
    return tuple(ComparisonScheme.model_validate(s) for s in _comparison_doc()["schemes"])


def corporation_for(category: SocialCategory) -> Corporation | None:
    for corp in corporations():
        if category.value in corp.social_categories:
            return corp
    return None


def sca_for_state(state: str | None, corporation_id: str | None) -> Sca | None:
    if not state:
        return None
    key = state.strip().lower()
    for raw in _sca_doc()["agencies"]:
        sca = Sca.model_validate(raw)
        matches_state = key in (sca.state.lower(), sca.state_code.lower())
        if matches_state and (corporation_id is None or corporation_id in sca.corporations):
            return sca
    return None


def _documents(
    corporation_id: str | None, activity_category: str | None
) -> tuple[DocumentItem, ...]:
    doc = _corporations_doc()["documents"]
    items = [DocumentItem.model_validate(d) for d in doc["common"]]
    if corporation_id:
        for d in doc.get("by_corporation", {}).get(corporation_id, []):
            items.append(DocumentItem.model_validate(d))
    if activity_category:
        for d in doc.get("by_activity", {}).get(activity_category, []):
            items.append(DocumentItem.model_validate(d))
    return tuple(items)


def assess(
    social_category: SocialCategory | str,
    annual_family_income: Decimal | int | float | str | None = None,
    *,
    state: str | None = None,
    activity_category: str | None = None,
    is_woman: bool = False,
    has_prior_experience: bool = True,
    requested_loan: Decimal | None = None,
) -> EligibilityResult:
    """Return a verdict plus everything the applicant must carry to the SCA counter."""
    category = SocialCategory(social_category)
    income = None if annual_family_income is None else money(annual_family_income)
    corp = corporation_for(category)
    reasons: list[str] = []
    reasons_hi: list[str] = []
    conditions: list[str] = []
    conditions_hi: list[str] = []
    handoffs = tuple(_comparison_doc().get("handoffs", ()))

    if corp is None:
        reasons.append(
            f"The {category.value.upper()} category is not served by an MoSJE apex corporation "
            "(NSFDC / NSKFDC / NBCFDC). Route to a general-purpose scheme instead."
        )
        reasons_hi.append(
            "इस श्रेणी की सेवा कोई एमओएसजेई शीर्ष निगम (एनएसएफडीसी / एनएसकेएफडीसी / "
            "एनबीसीएफडीसी) नहीं करता। इसके बजाय सामान्य-उद्देश्य योजनाओं की ओर देखें।"
        )
        return EligibilityResult(
            verdict=Verdict.INELIGIBLE,
            corporation=None,
            social_category=category,
            annual_family_income=income,
            income_ceiling=None,
            reasons=tuple(reasons),
            reasons_hi=tuple(reasons_hi),
            comparison=comparison_schemes(),
            is_woman=is_woman,
            sources=("mosje_corporations",),
        )

    ceiling = corp.income_ceiling
    verdict = Verdict.ELIGIBLE
    corp_label_hi = corp.name_hi or corp.name
    reasons.append(f"{category.value.upper()} applicants are served by {corp.name}.")
    reasons_hi.append(f"इस श्रेणी के आवेदकों की सेवा {corp_label_hi} करता है।")

    if ceiling is None:
        reasons.append(corp.income_ceiling_note or "No income ceiling applies.")
        reasons_hi.append("कोई आय सीमा लागू नहीं है।")
    elif income is None:
        verdict = Verdict.ELIGIBLE_WITH_CONDITIONS
        conditions.append(
            f"Annual family income was not provided. Eligibility requires it to be at or below "
            f"{format_inr(ceiling)}; carry an income certificate to the SCA."
        )
        conditions_hi.append(
            f"वार्षिक पारिवारिक आय नहीं दी गई। पात्रता के लिए आय {format_inr(ceiling)} तक "
            "होनी चाहिए; एससीए के पास आय प्रमाणपत्र ले जाएँ।"
        )
    elif income > ceiling:
        verdict = Verdict.INELIGIBLE
        reasons.append(
            f"Annual family income of {format_inr(income)} exceeds the {format_inr(ceiling)} "
            f"ceiling for {corp.name}."
        )
        reasons_hi.append(
            f"वार्षिक पारिवारिक आय {format_inr(income)}, {corp_label_hi} की "
            f"{format_inr(ceiling)} सीमा से अधिक है।"
        )
    else:
        reasons.append(
            f"Annual family income of {format_inr(income)} is within the "
            f"{format_inr(ceiling)} ceiling."
        )
        reasons_hi.append(
            f"वार्षिक पारिवारिक आय {format_inr(income)}, {format_inr(ceiling)} सीमा के भीतर है।"
        )

    if requested_loan is not None and requested_loan > corp.max_loan:
        verdict = Verdict.INELIGIBLE if verdict is Verdict.ELIGIBLE else verdict
        reasons.append(
            f"Requested loan of {format_inr(requested_loan)} exceeds the "
            f"{format_inr(corp.max_loan)} ceiling for {corp.name}."
        )
        reasons_hi.append(
            f"माँगा गया ऋण {format_inr(requested_loan)}, {corp_label_hi} की "
            f"{format_inr(corp.max_loan)} सीमा से अधिक है।"
        )

    if is_woman:
        conditions.append(
            "Women beneficiaries qualify for the corporation's Mahila Samridhi / Mahila "
            "Adhikarita concessional window. Ask the SCA to apply it."
        )
        conditions_hi.append(
            "महिला लाभार्थियाँ निगम की महिला समृद्धि / महिला अधिकारिता रियायती खिड़की के लिए "
            "पात्र हैं। एससीए से इसे लागू करने को कहें।"
        )
    if not has_prior_experience:
        conditions.append(
            "No prior experience in the chosen activity, so complete a PM-DAKSH course before "
            "disbursement; SCAs treat this as a strengthening factor."
        )
        conditions_hi.append(
            "चुनी गई गतिविधि में पूर्व अनुभव नहीं है, इसलिए वितरण से पहले पीएम-दक्ष पाठ्यक्रम "
            "पूरा करें; एससीए इसे सुदृढ़ीकरण मानते हैं।"
        )
    if conditions and verdict is Verdict.ELIGIBLE:
        verdict = Verdict.ELIGIBLE_WITH_CONDITIONS

    return EligibilityResult(
        verdict=verdict,
        corporation=corp,
        social_category=category,
        annual_family_income=income,
        income_ceiling=ceiling,
        reasons=tuple(reasons),
        reasons_hi=tuple(reasons_hi),
        conditions=tuple(conditions),
        conditions_hi=tuple(conditions_hi),
        documents=_documents(corp.id, activity_category),
        sca=sca_for_state(state, corp.id),
        handoffs=handoffs,
        comparison=comparison_schemes(),
        is_woman=is_woman,
        sources=("mosje_corporations", corp.id),
    )

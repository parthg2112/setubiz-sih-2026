"""Deterministic eligibility. A verdict here is code, never a language-model opinion."""

from setubiz.eligibility.rules import (
    ComparisonScheme,
    Corporation,
    DocumentItem,
    EligibilityResult,
    SocialCategory,
    Verdict,
    assess,
    comparison_schemes,
    corporations,
    sca_for_state,
)

__all__ = [
    "ComparisonScheme",
    "Corporation",
    "DocumentItem",
    "EligibilityResult",
    "SocialCategory",
    "Verdict",
    "assess",
    "comparison_schemes",
    "corporations",
    "sca_for_state",
]

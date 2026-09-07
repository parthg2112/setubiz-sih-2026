"""Numeric grounding — layer 2 of the anti-hallucination stack (PLAN.md §3).

Every number that appears in narrated prose must already exist in `facts.numeric_index` (or be
derivable from a locked table such as the repayment schedule). Anything else is a hallucination
regardless of how plausible it reads, and the generation is rejected and retried.

The catch rate this produces is a headline metric, not an internal detail — surface it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from setubiz.facts.builder import Facts

#: ₹1,00,000 · 44,729.31 · 8.0% · ₹9.00 L · 1.25 Cr · 2810 · -₹15,924 (a loss is still a figure)
_NUMBER = re.compile(
    r"(?<![\w.])"
    r"(?P<sign>[-−])?\s*"
    r"(?:₹\s*)?"
    r"(?P<digits>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"\s*(?P<suffix>L\b|lakh|Cr\b|crore|%)?",
    re.IGNORECASE,
)

_MULTIPLIER = {
    "l": Decimal("100000"),
    "lakh": Decimal("100000"),
    "cr": Decimal("10000000"),
    "crore": Decimal("10000000"),
}

#: Structural constants, not estimates: the 10% margin / 90% loan split, the stress percentages,
#: and the per-1,000-household denominator. Permitted without appearing in the facts index.
_STRUCTURAL = {
    Decimal("10"),
    Decimal("15"),
    Decimal("30"),
    Decimal("90"),
    Decimal("100"),
    Decimal("1000"),
}


@dataclass(frozen=True)
class ExtractedNumber:
    text: str
    value: Decimal
    #: The place value of the last written digit — "₹44,729" is 1, "₹14.33 L" is 1000.
    #: Tolerance comes from how precisely a figure was stated, not from a blanket percentage.
    resolution: Decimal


@dataclass(frozen=True)
class UngroundedNumber:
    text: str
    value: Decimal
    context: str


@dataclass
class ValidationReport:
    passed: bool
    checked: int
    ungrounded: tuple[UngroundedNumber, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def grounded(self) -> int:
        return self.checked - len(self.ungrounded)


@dataclass
class CatchRate:
    """Rolling counter of how often the validator rejected a generation."""

    generations: int = 0
    rejections: int = 0

    def record(self, report: ValidationReport) -> None:
        self.generations += 1
        if not report.passed:
            self.rejections += 1

    @property
    def rate(self) -> float:
        return 0.0 if not self.generations else round(self.rejections / self.generations, 4)

    def as_dict(self) -> dict[str, float | int]:
        return {
            "generations": self.generations,
            "rejections": self.rejections,
            "catch_rate": self.rate,
        }


def extract_numbers(text: str) -> list[ExtractedNumber]:
    """Pull every quotable figure out of prose, normalizing lakh/crore to rupees."""
    found: list[ExtractedNumber] = []
    for match in _NUMBER.finditer(text):
        suffix = (match.group("suffix") or "").lower().rstrip(".")
        digits = match.group("digits").replace(",", "")
        try:
            value = Decimal(digits)
        except InvalidOperation:  # pragma: no cover - regex cannot produce this
            continue
        resolution = Decimal(1).scaleb(-len(digits.partition(".")[2]))
        if suffix in _MULTIPLIER:
            value *= _MULTIPLIER[suffix]
            resolution *= _MULTIPLIER[suffix]
        if match.group("sign"):
            value = -value
        found.append(ExtractedNumber(match.group(0).strip(), value, resolution))
    return found


class NumericGroundingValidator:
    """Rejects prose containing a figure the facts object never computed.

    Known limit, worth stating before a judge asks: this catches *invented* figures, not
    *misattributed* ones. A number lifted from row 14 of the repayment schedule and captioned as
    something else is grounded and passes here — verdict fidelity, not this layer, guards that.
    """

    def __init__(self, slack_factor: Decimal = Decimal("0.5")) -> None:
        #: Half of the stated figure's own resolution: "₹44,729" tolerates ₹0.50, "₹14.33 L" ₹500.
        self.slack_factor = slack_factor

    def _allowed(self, facts: Facts) -> set[Decimal]:
        allowed = facts.allowed_numbers() | _STRUCTURAL
        allowed |= {Decimal(s.year.split("-")[0]) for s in facts.sources if s.year}
        allowed |= {Decimal(n) for n in range(0, 13)}  # quarter and month ordinals
        # Digits inside locked reference strings the report quotes verbatim.
        allowed |= {n.value for n in extract_numbers(facts.verbatim_text())}
        return allowed

    def _is_grounded(self, number: ExtractedNumber, allowed: set[Decimal]) -> bool:
        slack = max(Decimal("0.01"), number.resolution * self.slack_factor)
        return any(abs(number.value - candidate) <= slack for candidate in allowed)

    def validate(self, text: str, facts: Facts) -> ValidationReport:
        allowed = self._allowed(facts)
        ungrounded: list[UngroundedNumber] = []
        numbers = extract_numbers(text)

        for number in numbers:
            if self._is_grounded(number, allowed):
                continue
            start = max(0, text.find(number.text) - 40)
            ungrounded.append(
                UngroundedNumber(
                    text=number.text,
                    value=number.value,
                    context="…" + text[start : start + 100].replace("\n", " ") + "…",
                )
            )

        return ValidationReport(
            passed=not ungrounded,
            checked=len(numbers),
            ungrounded=tuple(ungrounded),
            notes=(f"{len(numbers)} figures checked against {len(allowed)} grounded values.",),
        )

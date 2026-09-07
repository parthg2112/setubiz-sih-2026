"""Decimal money helpers. All financial arithmetic uses Decimal; floats never touch a rupee."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Union

Money = Decimal

PAISE = Decimal("0.01")
RUPEE = Decimal("1")
ZERO = Decimal("0")

Numeric = Union[int, float, str, Decimal]


def money(value: Numeric) -> Decimal:
    """Coerce to Decimal quantized to paise. Floats go via str to avoid binary artefacts."""
    if isinstance(value, float):
        value = repr(value)
    return Decimal(value).quantize(PAISE, rounding=ROUND_HALF_UP)


def q(value: Decimal, exp: Decimal = PAISE) -> Decimal:
    return value.quantize(exp, rounding=ROUND_HALF_UP)


def floor_to(value: Decimal, step: Decimal) -> Decimal:
    """Round down to the nearest `step` (e.g. nearest ₹1,000 for a recommended loan)."""
    if step <= 0:
        raise ValueError("step must be positive")
    return (value // step) * step


def format_inr(value: Decimal | int | float, *, paise: bool = False) -> str:
    """Indian digit grouping: 900000 -> '₹9,00,000'.

    Rupees are rounded, never truncated — the numeric-grounding validator tolerates half of the
    displayed resolution, and truncation would push a figure just outside it.
    """
    d = money(value)
    negative = d < 0
    d = -d if negative else d
    whole = int(d if paise else q(d, RUPEE))
    frac = (d - whole).quantize(PAISE) if paise else ZERO
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join([*parts, tail])
    out = f"₹{s}"
    if paise:
        out += f".{str(frac)[2:].ljust(2, '0')}"
    return ("-" + out) if negative else out


def format_lakh(value: Decimal | int | float) -> str:
    """Compact Indian scale used in narration: '₹9.00 L', '₹1.25 Cr'."""
    d = money(value)
    if abs(d) >= Decimal("10000000"):
        return f"₹{q(d / Decimal('10000000'), Decimal('0.01'))} Cr"
    if abs(d) >= Decimal("100000"):
        return f"₹{q(d / Decimal('100000'), Decimal('0.01'))} L"
    return format_inr(d)

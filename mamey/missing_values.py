"""One rule for missing values: a blank or placeholder cell is missing evidence, never a measured zero.

Readers parse optional numbers and identifiers through these helpers, so a blank, `NA`, `n/a`, `-`, `nan` or
`None` cell stays missing all the way to the table, figure or sentence that shows it. Writers show a missing value
as blank (or a caller-chosen label such as `n.t.`), never as 0, 0% or a match.
"""
from __future__ import annotations

import math
from typing import Any

MISSING_TOKENS = frozenset({"", "na", "n/a", "nan", "none", "null", "-", "--", "unbound", "not available"})


def is_missing(value: Any) -> bool:
    """True for None, a NaN float, or text that is blank or a placeholder token (case and spaces ignored)."""
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    if isinstance(value, (int, bool)):
        return False
    return str(value).strip().casefold() in MISSING_TOKENS


def optional_text(value: Any) -> str | None:
    """The stripped text, or None when the value is missing."""
    return None if is_missing(value) else str(value).strip()


def optional_float(value: Any) -> float | None:
    """A finite float, or None when the value is missing or not a finite number."""
    if is_missing(value):
        return None
    try:
        number = float(str(value).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def optional_int(value: Any) -> int | None:
    """An integer, or None when the value is missing, fractional or not a number."""
    number = optional_float(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def same_identity(a: Any, b: Any) -> bool:
    """True only when both values are present and equal as text. Two missing values never match."""
    left, right = optional_text(a), optional_text(b)
    return left is not None and right is not None and left == right


def display(value: Any, missing: str = "", fmt: str | None = None) -> str:
    """Text for a table cell: the formatted value, or `missing` when the value is missing. Never invents 0."""
    if is_missing(value):
        return missing
    if fmt is not None:
        number = optional_float(value)
        return missing if number is None else format(number, fmt)
    return str(value).strip()

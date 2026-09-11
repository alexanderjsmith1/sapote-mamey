"""mamey.precision — kill false precision in reported similarity numbers (W26).

A KnownClusterBlast cumulative score or an "AA identity %" reads like a hard
measurement. The biology behind it is fuzzier than the digits imply, and a reader
(or a downstream prose layer) over-trusts it. These helpers bin and round those
numbers and force the "= similarity, not identity" qualifier to travel with them, so
the structured output can never present a bare, over-precise similarity figure.

Nothing here invents data; it only *presents* an existing number at honest precision.
"""
from __future__ import annotations

SIMILARITY_DISCLAIMER = "similarity, not identity"


def similarity_band(score: float | int | None) -> str:
    """Bin a KnownClusterBlast-style cumulative/percent score into high/moderate/low.
    Returns 'unresolved' for None. Bands are deliberately coarse — the point is to
    stop a 2-significant-figure number implying 2-significant-figure certainty."""
    if score is None:
        return "unresolved"
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "unresolved"
    # Normalise: KCB cumulative scores are often 0–100-ish percents; clamp sanely.
    if s >= 70:
        return "high"
    if s >= 40:
        return "moderate"
    if s > 0:
        return "low"
    return "none"


def round_identity(pct: float | int | None) -> int | None:
    """Round an identity percentage to the nearest 5% — honest precision for an
    alignment identity that was never meaningful to the integer."""
    if pct is None:
        return None
    try:
        return int(round(float(pct) / 5.0) * 5)
    except (TypeError, ValueError):
        return None


def round_bitscore(bs: float | int | None) -> int | None:
    """Bitscores to the nearest integer — 'BS=563.5' implies a precision the score
    does not carry."""
    if bs is None:
        return None
    try:
        return int(round(float(bs)))
    except (TypeError, ValueError):
        return None


def kcb_display(score: float | int | None, raw_label: str | None = None) -> str:
    """Human/structured display for a KCB hit: a band + the mandatory disclaimer,
    with the raw label kept but de-emphasised. Never returns a bare percentage."""
    band = similarity_band(score)
    if band in ("unresolved", "none"):
        return f"{band} ({SIMILARITY_DISCLAIMER})"
    label = f" — {raw_label}" if raw_label else ""
    return f"{band} similarity ({SIMILARITY_DISCLAIMER}){label}"

"""Refuse governance prose in a figure caption.

A figure caption is publication text: what was done, and what the reader is looking at. Agent
governance language ("judgment deferred", "class-level", "no compound, structure or potency claim is
implied") is written for the operator, not the reader. Baked into a rendered figure it reads as
hedging, and it has to be deleted by hand before submission.

Claim-safety is preserved where it actually operates: the analysis documents, the reply to the
operator, and the fact that the figure reports calls and deposited metadata rather than conclusions.

Usage:
    from caption_guard import check_caption, CaptionGovernanceError
    check_caption(text)                      # raises on a violation
    check_caption(text, raises=False)        # returns the list of findings
"""
from __future__ import annotations

import re

__all__ = ["BLOCKED", "CaptionGovernanceError", "check_caption", "scan_paths"]


class CaptionGovernanceError(ValueError):
    """Raised when a caption carries operator-governance prose."""


# Phrase -> why it does not belong in a caption.
BLOCKED: dict[str, str] = {
    "judgment deferred": "names the operator's review process, not the figure",
    "judgement deferred": "names the operator's review process, not the figure",
    "class-level": "governance vocabulary; state the actual threshold instead",
    "no compound": "reassurance about what the figure does not prove",
    "structure, or potency": "reassurance about what the figure does not prove",
    "potency claim": "reassurance about what the figure does not prove",
    "claim is implied": "reassurance about what the figure does not prove",
    "not biological absence": "belongs in the methods text, phrased as what was tested",
    "claim-safe": "governance vocabulary",
    "judgment is deferred": "names the operator's review process, not the figure",
}

_WS = re.compile(r"\s+")


def _normalise(text: str) -> str:
    return _WS.sub(" ", (text or "")).lower()


def check_caption(text: str, *, raises: bool = True) -> list[tuple[str, str]]:
    """Return [(phrase, reason)] found in `text`. Raise when `raises` and any are found."""
    flat = _normalise(text)
    found = [(p, why) for p, why in BLOCKED.items() if p in flat]
    # A phrase implied by a longer one is reported once, by the longest match.
    found = [(p, w) for p, w in found if not any(p != q and p in q for q, _ in found)]
    if found and raises:
        detail = "; ".join(f"{p!r} ({w})" for p, w in found)
        raise CaptionGovernanceError(f"CAPTION_GOVERNANCE_PROSE: {detail}")
    return found


def scan_paths(paths) -> dict[str, list[tuple[str, str]]]:
    """Map path -> findings for every caption file that violates the rule."""
    out: dict[str, list[tuple[str, str]]] = {}
    for p in paths:
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        hits = check_caption(text, raises=False)
        if hits:
            out[str(p)] = hits
    return out

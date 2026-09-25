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

__all__ = ["BLOCKED", "CaptionGovernanceError", "CaptionUnreadableError", "check_caption", "scan_paths"]


class CaptionGovernanceError(ValueError):
    """Raised when a caption carries operator-governance prose."""


class CaptionUnreadableError(OSError):
    """Raised when a caption file cannot be read, so it could not be checked."""


# Phrase -> why it does not belong in a caption.
BLOCKED: dict[str, str] = {
    "judgment deferred": "names the operator's review process, not the figure",
    "judgement deferred": "names the operator's review process, not the figure",
    "no compound": "reassurance about what the figure does not prove",
    "structure, or potency": "reassurance about what the figure does not prove",
    "potency claim": "reassurance about what the figure does not prove",
    "claim is implied": "reassurance about what the figure does not prove",
    "not biological absence": "belongs in the methods text, phrased as what was tested",
    "claim-safe": "governance vocabulary",
    "judgment is deferred": "names the operator's review process, not the figure",
    # Alex 2026-09-24: claim-safety statements are removed from figures entirely, footers and
    # internal-notes band included. A key reads "isolate from this study", not "query strain".
    "query strain": "internal pipeline role; the key reads 'isolate from this study'",
    "not identity": "reassurance about what the figure does not prove",
    "not compound identity": "reassurance about what the figure does not prove",
    "not production": "reassurance about what the figure does not prove",
    "not potency": "reassurance about what the figure does not prove",
    "not bioactivity": "reassurance about what the figure does not prove",
    "not novelty": "reassurance about what the figure does not prove",
    "descriptive screening": "governance vocabulary; state the assay and threshold instead",
    "claim safety": "governance vocabulary",
}

# "class-level" is legitimate scientific vocabulary when it modifies a following noun
# ("class-level composition", "class-level phylogenetic placement") but is governance
# hedging when used as a standalone predicate ("screening signal is class-level;" /
# "class-level." / "class-level,"). Matched separately from BLOCKED, which is a flat
# substring check that cannot tell the two apart.
_CLASS_LEVEL_STANDALONE = re.compile(r"\bclass-level\b(?!\s+[a-z])")
# The lookahead above exempts ANY following lowercase word, which is right for
# "class-level distribution" but wrong for governance qualifiers: "class-level only",
# "class-level hypotheses only", "class-level read only" all survive it. Those are the
# hedging forms, so they get their own pattern.
_CLASS_LEVEL_QUALIFIED = re.compile(r"\bclass-level\s+(?:only\b|hypothes\w*|read\b)")
_CLASS_LEVEL_REASON = "governance vocabulary; state the actual threshold instead"

_WS = re.compile(r"\s+")


def _normalise(text: str) -> str:
    return _WS.sub(" ", (text or "")).lower()


def check_caption(text: str, *, raises: bool = True) -> list[tuple[str, str]]:
    """Return [(phrase, reason)] found in `text`. Raise when `raises` and any are found."""
    flat = _normalise(text)
    found = [(p, why) for p, why in BLOCKED.items() if p in flat]
    if _CLASS_LEVEL_STANDALONE.search(flat) or _CLASS_LEVEL_QUALIFIED.search(flat):
        found.append(("class-level", _CLASS_LEVEL_REASON))
    # A phrase implied by a longer one is reported once, by the longest match.
    found = [(p, w) for p, w in found if not any(p != q and p in q for q, _ in found)]
    if found and raises:
        detail = "; ".join(f"{p!r} ({w})" for p, w in found)
        raise CaptionGovernanceError(f"CAPTION_GOVERNANCE_PROSE: {detail}")
    return found


def scan_paths(paths, *, strict: bool = True) -> dict[str, list[tuple[str, str]]]:
    """Map path -> findings for every caption file that violates the rule.

    A caption that cannot be read has NOT been checked, so it is never reported as clean.
    With `strict` (the default) an unreadable path raises; otherwise it is returned under the
    reserved key "__unreadable__" so the caller still sees it. A guard that silently skips its
    input fails open, which is the failure this checker exists to prevent.
    """
    out: dict[str, list[tuple[str, str]]] = {}
    unreadable: list[tuple[str, str]] = []
    for p in paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            if strict:
                raise CaptionUnreadableError(f"CAPTION_UNREADABLE: {p}: {exc}") from exc
            unreadable.append((str(p), f"unreadable, not checked: {exc}"))
            continue
        hits = check_caption(text, raises=False)
        if hits:
            out[str(p)] = hits
    if unreadable:
        out["__unreadable__"] = unreadable
    return out

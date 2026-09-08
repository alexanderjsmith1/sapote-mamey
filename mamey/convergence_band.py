"""convergence_band.py — say how STRONG a per-gene MIBiG convergence is, not just how big.

DISPLAY-ONLY, POST-SEAL. Nothing here scores, gates, routes, or writes into a sealed package. It
turns a bare percentage into a percentage plus a calibrated word, so a reader cannot quote a weak
similarity as though it were convergence.

WHY THIS EXISTS
    Measured across the cohort's 323,672 per-gene MIBiG hits (engine 1.9.119):

        >= 80%   21,984 hits    6.8%   strong
        60-79%  104,167 hits   32.2%   moderate
        40-59%  197,521 hits   61.0%   weak / very weak
        < 40%        (in the same 61.0% band)

    So a *typical* per-gene MIBiG hit is weak, and an unbanded ranking of "most shared compounds"
    surfaces promiscuous, low-identity similarity — it reads as though a whole cohort shares one
    compound. Banded to >= 80% the same query returns hopene, ectoine, spore pigment and
    desferrioxamine: the conserved housekeeping and iron-acquisition metabolites one would expect
    to be genuinely conserved across ~200 actinomycetes.

CLAIM CEILING (travels with every label this emits)
    A band describes the STRENGTH OF SIMILARITY to the nearest characterised neighbour. It is not
    a confidence in a product, a structure, an activity, or a novelty call. "strong" means the
    sequence resemblance is strong — never that the strain makes the compound. Judgment deferred.
"""
from __future__ import annotations

from typing import Optional

__all__ = ["band", "annotate", "is_reference_dark", "BANDS", "BAND_NOTE",
           "STRONG_MIN", "MODERATE_MIN", "REFERENCE_DARK_BELOW"]

# ---- SHARED VOCABULARY CONTRACT --------------------------------------------------------------
# Other modules must IMPORT these rather than hard-coding 60 / 80, so the whole cut speaks one
# language. Agreed across chats for v9.7.349 (see the cross-chat coordination memos):
#   * BLIZZARD_BLUE_02  - lead-page convergence bands
#   * CLAUDE_AUG3_02    - reference-dark novelty (imports REFERENCE_DARK_BELOW, not a literal 60)
#   * any figure or roster quoting a per-gene identity
# Changing a number here changes it everywhere on purpose. Do not fork these values.
STRONG_MIN = 80.0            # >= this is 'strong'; only 6.8% of per-gene MIBiG hits reach it
MODERATE_MIN = 60.0          # >= this is 'moderate'; below it is weak
REFERENCE_DARK_BELOW = MODERATE_MIN   # 'reference-dark' == weaker than moderate, i.e. < 60%

# (inclusive lower bound, label). Ordered high -> low; first match wins.
BANDS: tuple[tuple[float, str], ...] = (
    (STRONG_MIN, "strong"),
    (MODERATE_MIN, "moderate"),
    (40.0, "weak"),
    (0.0, "very weak"),
)

BAND_NOTE = (
    "Convergence bands describe the strength of SIMILARITY to the nearest characterised "
    "neighbour, not confidence in a product. Cohort-calibrated: only 6.8% of per-gene MIBiG hits "
    "reach >=80% (strong); 61% fall below 60%. Similarity is not identity; judgment deferred."
)


def _as_float(pct) -> Optional[float]:
    """Percentages arrive from CSV as strings, sometimes empty, sometimes with a trailing %."""
    if pct is None:
        return None
    if isinstance(pct, (int, float)):
        return float(pct)
    s = str(pct).strip().rstrip("%").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def band(pct) -> str:
    """Band label for a percent identity. Returns '' when there is no value.

    An absent value is NOT banded as weak — missing evidence and weak evidence are different
    statements, and conflating them is exactly the error this module exists to prevent.
    """
    v = _as_float(pct)
    if v is None:
        return ""
    for lo, label in BANDS:
        if v >= lo:
            return label
    return ""


def annotate(pct, *, parens: bool = True) -> str:
    """'72.5% (moderate)' — the percentage with its band, for direct rendering.

    Returns the value unchanged when it cannot be banded, and '' when there is no value at all,
    so a caller can drop it straight into an f-string without special-casing blanks.
    """
    v = _as_float(pct)
    if v is None:
        return ""
    b = band(v)
    txt = f"{v:g}%"
    if not b:
        return txt
    return f"{txt} ({b})" if parens else f"{txt} {b}"


def is_reference_dark(pct) -> Optional[bool]:
    """True when a per-gene identity is below the shared reference-dark cutoff (< 60%).

    Returns **None** when there is no value — because "we did not measure this gene" and "this gene
    is reference-dark" are different claims, and a missing BLASTp/MIBiG result must never be
    counted as evidence of divergence. Callers should branch on `is None` explicitly rather than
    treating the result as falsy.

    This is the single source of the cutoff for the v9.7.349 cut; import it instead of writing 60.
    """
    v = _as_float(pct)
    if v is None:
        return None
    return v < REFERENCE_DARK_BELOW

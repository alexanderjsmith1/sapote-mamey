"""Comparator-coverage scoring wire (CAT-01-class feature, D1 / v9.7.338 prototype).

WHAT THIS IS
------------
A bounded, auditable *routing-prior* transform that turns the two-denominator
MIBiG comparator-coverage evidence (produced by the sibling evidence layer
``mamey/mibig_comparator_coverage.py``) into a small, capped adjustment on the
AB / AF capacity axes computed in ``scoring.triage_bgcs``.

It is a **capacity** signal only. Like every other Mamey routing prior it sorts
BGCs for the judgment layer; it makes **no** structure, production, expression,
or bioactivity claim. The contribution is bounded to |delta| <= ``PRIOR_CAP``
points, which is far smaller than the KCB-driven ``DIAGNOSTIC_BONUS`` (25) and
the class keyword weights, so it can nudge near-threshold ordering but cannot
manufacture a lead on its own.

THE EVIDENCE (two denominators)
-------------------------------
A MIBiG comparator that BLASTs against a query BGC covers some of the query's
genes. There are two honest denominators for "how much of the pathway does this
comparator explain":

  * ``coverage_all_locus``  = matched query genes / ALL query genes in the locus
                              (raw ``query_gene_share``). Low when the BGC has
                              many genes the comparator does not touch.
  * ``coverage_core``       = matched query genes / RECOGNIZABLE (core) query
                              genes (raw ``recognizable_gene_share``). High when
                              the comparator explains the recognizable backbone.

The classic failure a single denominator hides: a comparator with
``coverage_core`` = 1.0 but ``coverage_all_locus`` = 0.14 is a *sub-pathway /
partial* match dressed up as a full one. Requiring BOTH denominators to be
non-trivial (geometric mean) de-weights that partial match relative to a
comparator that covers the locus on both.

WHAT THE WIRE DOES
------------------
* ADDS a bounded positive prior ONLY for a comparator that is, simultaneously:
    - class-CONCORDANT with the BGC's own product class,
    - high within-BGC specificity (UNIQUE or CLEAR — it dominates the locus,
      not one of several co-equal families),
    - non-colliding (its matched genes are not a transport/regulatory-only
      promiscuous overlap), and
    - high on BOTH coverage denominators.
* DE-WEIGHTS (bounded negative) diffuse / ambiguous comparators:
    - CO_DOMINANT within-BGC specificity (two families tie — ambiguous),
    - class-DISCORDANT comparators (never positive — cannot lend capacity
      credit to a class it does not match),
    - cohort-promiscuous comparators (the same reference is the dominant hit
      across a large fraction of the cohort — a housekeeping/transport magnet).
* NEUTRALISES (exactly zero) a collision-flagged transport/regulatory-only
  comparator — it is uninformative for capacity, so it earns nothing.

GUARD PRECEDENCE (hard override — see the ``guard_suppressed`` arg)
------------------------------------------------------------------
The mis-anchor and primary-metabolism / mobile-element guards in
``triage_bgcs`` are HARD overrides. Where any of them fire, this wire contributes
**nothing at all** (neither bonus nor penalty): those guards have already
decided the locus's anchor is spurious, and a comparator-coverage prior must not
re-litigate that decision. ``apply_comparator_coverage`` returns the base scores
unchanged whenever ``guard_suppressed`` is true.

NO KCB DOUBLE-COUNT
-------------------
``comparator_prior`` is a pure function of the coverage-evidence dict ONLY. It
never reads ``kcb_top``, ``closest_candidate_kcb_product``, the KCB keyword max,
or the ``DIAGNOSTIC_BONUS`` — those channels are already scored in
``triage_bgcs``. The prior rewards the *structural* properties of the coverage
(specificity + two-denominator depth), which the class-name keyword max does not
capture, and it is bounded small so it cannot re-add the KCB channel's weight.
"""
from __future__ import annotations

from math import sqrt
from typing import Any, Mapping, Optional

# ---------------------------------------------------------------------------
# Bound + tuning constants (routing priors — reviewers may tune; record in the
# changelog because near-threshold batch ordering depends on them).
# ---------------------------------------------------------------------------
PRIOR_CAP: float = 6.0            # hard bound on |contribution|, points on the axis
POS_MAX: float = 6.0              # max positive bonus for a perfect concordant/UNIQUE/full-coverage comparator
CORE_MIN_FOR_BONUS: float = 0.5   # a comparator must explain >=50% of the recognizable core to earn ANY bonus
NEG_DISCORDANT: float = -5.0      # class-mismatch comparator (never positive)
NEG_CO_DOMINANT: float = -3.0     # ambiguous within-BGC (two families tie)
NEG_PROMISCUOUS: float = -3.0     # cohort-promiscuous reference (housekeeping/transport magnet)
PREVALENCE_PROMISCUOUS: float = 0.5   # promiscuous when prevalence in OTHER strains is STRICTLY > 0.5
# v9.7.410: promiscuity may only be asserted once the cohort denominator (other
# strains, focal excluded) reaches this floor; otherwise the de-weight is skipped
# ("not assessable"), never applied.  Mirrors
# mibig_comparator_coverage.COHORT_PREVALENCE_MIN_OTHER_STRAINS (N >= 4 with focal).
PREVALENCE_MIN_OTHER_STRAINS: int = 3
_PREVALENCE_FLAG_PROMISCUOUS = "PROMISCUOUS_DE_WEIGHT"
_PREVALENCE_FLAGS_NOT_ASSESSABLE = ("NOT_ASSESSABLE_SMALL_COHORT", "NOT_COMPUTED")

_SPEC_FACTOR = {"UNIQUE": 1.0, "CLEAR": 0.6, "CO_DOMINANT": 0.0}


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _f(d: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    """First present key coerced to float (accepts the sibling's field names or the raw
    convergence-row field names as fallbacks)."""
    for k in keys:
        if k in d and d[k] is not None:
            try:
                return float(d[k])
            except (TypeError, ValueError):
                return default
    return default


def _s(d: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        if k in d and d[k] is not None:
            return str(d[k]).strip()
    return default


def _specificity(cov: Mapping[str, Any]) -> str:
    """Within-BGC specificity UNIQUE / CLEAR / CO_DOMINANT.

    Prefers the evidence layer's explicit ``specificity`` field; falls back to
    deriving it from raw convergence-row dominance fields so the wire also works
    when handed raw ``*_3_mibig_convergence.json`` rows (used by the impact
    reference implementation)."""
    spec = _s(cov, "specificity", "within_bgc_specificity").upper()
    if spec in _SPEC_FACTOR:
        return spec
    # derive from dominance geometry
    n_comparators = cov.get("n_comparators")
    dominant = cov.get("dominant_reference")
    margin = _f(cov, "dominance_gene_margin", default=-1.0)
    dom_status = _s(cov, "dominance_status").upper()
    if n_comparators is not None:
        try:
            if int(n_comparators) <= 1:
                return "UNIQUE"
        except (TypeError, ValueError):
            pass
    if dominant is True and margin >= 2:
        return "CLEAR"
    if dominant is True and 0 <= margin < 2:
        return "CO_DOMINANT"
    if "MIXED" in dom_status:
        return "CO_DOMINANT"
    return ""


def _prevalence_fraction(cov: Mapping[str, Any]) -> float:
    """Cohort prevalence as a fraction in [0, 1].

    Accepts a numeric ``cohort_prevalence`` / ``comparator_prevalence`` or the
    evidence layer's ``"K/N"`` string (``cohort_prevalence`` column of
    ``*_3b_comparator_coverage.csv``); falls back to
    ``cohort_strain_count / cohort_total_strains``."""
    for k in ("cohort_prevalence", "comparator_prevalence"):
        v = cov.get(k)
        if v is None:
            continue
        if isinstance(v, str) and "/" in v:
            num, _, den = v.partition("/")
            try:
                d = float(den)
                return float(num) / d if d > 0 else 0.0
            except (TypeError, ValueError):
                return 0.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
    den = _f(cov, "cohort_total_strains", default=0.0)
    return _f(cov, "cohort_strain_count", default=0.0) / den if den > 0 else 0.0


def _prevalence_denominator(cov: Mapping[str, Any]) -> int:
    """Number of OTHER strains the prevalence was measured over (0 = unknown)."""
    n = _f(cov, "cohort_total_strains", "cohort_other_strains", "cohort_size", default=0.0)
    if n <= 0:
        v = cov.get("cohort_prevalence")
        if isinstance(v, str) and "/" in v:
            n = _f({"d": v.partition("/")[2]}, "d", default=0.0)
    return int(n) if n > 0 else 0


def _promiscuous(cov: Mapping[str, Any]) -> bool:
    """True only when cohort promiscuity is both ASSESSABLE and ASSERTED.

    Precedence: an explicit evidence-layer ``cohort_prevalence_flag`` wins
    (``PROMISCUOUS_DE_WEIGHT`` -> True; ``NOT_ASSESSABLE_SMALL_COHORT`` /
    ``NOT_COMPUTED`` / anything else -> False).  Without a flag, the numeric
    prevalence must be measured over at least ``PREVALENCE_MIN_OTHER_STRAINS``
    other strains AND exceed ``PREVALENCE_PROMISCUOUS`` STRICTLY.  An unknown
    denominator is "not assessable" and earns no penalty."""
    flag = _s(cov, "cohort_prevalence_flag").upper()
    if flag:
        return flag == _PREVALENCE_FLAG_PROMISCUOUS
    if _prevalence_denominator(cov) < PREVALENCE_MIN_OTHER_STRAINS:
        return False
    return _prevalence_fraction(cov) > PREVALENCE_PROMISCUOUS


def comparator_prior(cov: Optional[Mapping[str, Any]]) -> tuple[float, str, str]:
    """Pure transform: coverage-evidence dict -> (delta, axis, note).

    ``delta`` is bounded to [-PRIOR_CAP, +PRIOR_CAP]. ``axis`` is 'ab' | 'af' |
    '' (empty -> caller routes to the BGC's current lead axis). ``note`` is a
    short human-auditable reason. NO guard logic, NO KCB fields — evidence dict
    only, so "does not double-count KCB" is verifiable by inspection.

    Precedence (first match wins):
      collision(transport/regulatory-only) -> 0.0        (uninformative; earns nothing)
      class DISCORDANT                      -> NEG_DISCORDANT   (never positive)
      CO_DOMINANT within-BGC                -> NEG_CO_DOMINANT  (ambiguous)
      cohort-promiscuous reference          -> NEG_PROMISCUOUS
      else (concordant, UNIQUE/CLEAR)       -> bounded positive on two-denominator depth
    """
    if not cov:
        return 0.0, "", ""
    axis = _s(cov, "axis", "scored_axis").lower()
    if axis not in ("ab", "af"):
        axis = ""

    # collision: a transport/regulatory-only overlap is uninformative for capacity -> exactly nothing.
    if bool(cov.get("collision", cov.get("collision_flag", False))):
        return 0.0, axis, "collision:transport/regulatory-only comparator — no capacity credit"

    concord = _s(cov, "class_concordance", "concordance").upper()
    spec = _specificity(cov)

    # class mismatch can never earn a positive bonus.
    if concord == "DISCORDANT":
        return NEG_DISCORDANT, axis, "class-mismatch comparator — de-weighted (no positive credit)"

    # ambiguous within-BGC (two families tie) -> de-weight.
    if spec == "CO_DOMINANT":
        return NEG_CO_DOMINANT, axis, "co-dominant comparator (ambiguous within-BGC) — de-weighted"

    # cohort-promiscuous reference (housekeeping/transport magnet) -> de-weight.
    # v9.7.410: only when the cohort is large enough to assess (denominator of
    # OTHER strains >= PREVALENCE_MIN_OTHER_STRAINS) and the fraction is STRICTLY
    # above the cut.  An evidence-layer flag, when present, is authoritative.
    if _promiscuous(cov):
        prevalence = _prevalence_fraction(cov)
        return NEG_PROMISCUOUS, axis, f"cohort-promiscuous comparator (prevalence={prevalence:.2f}) — de-weighted"

    # positive branch: only class-CONCORDANT + high specificity + high two-denominator coverage.
    if concord != "CONCORDANT":
        return 0.0, axis, "comparator not class-concordant — neutral (no bonus)"
    spec_factor = _SPEC_FACTOR.get(spec, 0.0)
    if spec_factor <= 0.0:
        return 0.0, axis, "comparator specificity not UNIQUE/CLEAR — neutral (no bonus)"
    cov_core = _f(cov, "coverage_core", "recognizable_gene_share", default=0.0)
    cov_all = _f(cov, "coverage_all_locus", "query_gene_share", default=0.0)
    if cov_core < CORE_MIN_FOR_BONUS:
        return 0.0, axis, f"comparator core coverage {cov_core:.2f} < {CORE_MIN_FOR_BONUS} — neutral (partial/weak)"
    # two-denominator depth: geometric mean, so a partial (high-core / low-locus) match is de-emphasised.
    cov_factor = sqrt(max(0.0, cov_core) * max(0.0, cov_all))
    delta = POS_MAX * spec_factor * cov_factor
    delta = _clamp(delta, 0.0, POS_MAX)
    note = (f"high-specificity comparator ({spec}, concordant): "
            f"core={cov_core:.2f} locus={cov_all:.2f} -> +{delta:.2f} capacity prior")
    return _clamp(delta, -PRIOR_CAP, PRIOR_CAP), axis, note


def read_evidence(bgc: Any, scans: Any = None) -> Optional[Mapping[str, Any]]:
    """Locate the per-BGC comparator-coverage evidence, defensively.

    Looked up in order (first hit wins), so the wire is decoupled from exactly
    how the sibling evidence layer lands its output:
      1. ``bgc.mibig_comparator_coverage``            (per-BGC dict on the record)
      2. ``scans.mibig_comparator_coverage['per_bgc'][bgc_id]``
    A list value (multiple comparators) is reduced to the dominant/first entry.
    Returns None when no evidence is present -> the wire is a no-op.
    """
    ev: Any = None
    ev = getattr(bgc, "mibig_comparator_coverage", None)
    if ev is None and scans is not None:
        try:
            blob = getattr(scans, "mibig_comparator_coverage", None)
            if isinstance(blob, Mapping):
                per_bgc = blob.get("per_bgc") or {}
                ev = per_bgc.get(getattr(bgc, "bgc_id", None))
        except Exception:
            ev = None
    if ev is None:
        return None
    if isinstance(ev, (list, tuple)):
        if not ev:
            return None
        # prefer an explicitly dominant entry, else the first
        for e in ev:
            if isinstance(e, Mapping) and e.get("dominant_reference") is True:
                return e
        ev = ev[0]
    return ev if isinstance(ev, Mapping) else None


def apply_comparator_coverage(bgc: Any, base_ab: float, base_af: float, *,
                              guard_suppressed: bool, scans: Any = None) -> tuple[float, float]:
    """The scoring hook. Returns possibly-adjusted (base_ab, base_af).

    HARD guard precedence: when ``guard_suppressed`` is true (primary-metabolism,
    mobile-element, or any mis-anchor guard fired), the wire contributes NOTHING
    and the base scores are returned unchanged.

    The bounded delta is routed to the comparator's family axis when the evidence
    supplies one, otherwise to the BGC's current lead axis (so it reinforces /
    de-weights the axis the comparator actually concerns rather than inventing
    cross-axis credit).
    """
    cov = read_evidence(bgc, scans)
    if cov is None:
        return base_ab, base_af
    if guard_suppressed:
        return base_ab, base_af  # guard is a hard override — bonus AND penalty suppressed
    delta, axis, _note = comparator_prior(cov)
    if delta == 0.0:
        return base_ab, base_af
    if axis == "af" or (axis == "" and base_af >= base_ab):
        base_af = base_af + delta
    else:
        base_ab = base_ab + delta
    return base_ab, base_af

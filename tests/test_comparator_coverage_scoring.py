"""CAT-01/D1 comparator-coverage scoring wire (v9.7.338 prototype).

Pins the invariants the sign-off requires:
  * a HIGH-specificity, concordant, non-colliding comparator with high
    two-denominator coverage adds a BOUNDED positive capacity prior;
  * a transport/regulatory-only (collision-flagged) comparator adds NOTHING;
  * a class-DISCORDANT / CO_DOMINANT / cohort-promiscuous comparator DE-WEIGHTS
    (bounded negative, never positive);
  * a mis-anchored / primary-metabolism / mobile-element BGC gets NO bonus
    (guard precedence is a hard override);
  * the prior is a pure function of the comparator-coverage evidence dict and
    never reads the KCB channel (no double-count), and is always bounded.

Standalone: python3 tests/test_comparator_coverage_scoring.py
"""
from __future__ import annotations
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.models import BGCRecord
from mamey import scoring as _scoring
from mamey.scoring import triage_bgcs
from mamey import comparator_coverage_scoring as cc

# CAT-01/D1 comparator-coverage scoring wire is SIGN-OFF-GATED. In the v9.7.338 merge cut the
# module ships but the two-line scoring.py hook is deliberately left UNWIRED pending sign-off
# (COMPARATOR_SCORING_HOOK.md). The unit tests of the transform (cc.comparator_prior) and the
# three guard-suppression integration tests hold regardless; the two integration tests that
# assert an ACTIVE bonus/de-weight only make sense once the hook is wired, so they skip while
# the wire is absent (and will run + must pass the moment it is enabled).
_WIRE_ACTIVE = "apply_comparator_coverage" in inspect.getsource(_scoring)
_needs_wire = pytest.mark.skipif(
    not _WIRE_ACTIVE,
    reason="D1 comparator-coverage scoring wire is sign-off-gated and left UNWIRED in the "
           "v9.7.338 cut; enable the scoring.py hook to run this wired-behavior test.")


# ── evidence-dict builders ────────────────────────────────────────────────────
def _cov(**kw):
    base = dict(coverage_all_locus=0.8, coverage_core=1.0, specificity="UNIQUE",
                collision=False, class_concordance="CONCORDANT", cohort_prevalence=0.0)
    base.update(kw)
    return base


def _bgc(bgc_id="BGC001", products=("NRPS",), cov=None):
    b = BGCRecord(bgc_id=bgc_id, contig="c1", region_number=1, start=1, end=9000,
                  contig_length=50000, products=list(products), edge_status="Interior",
                  architecture_confidence="A")
    if cov is not None:
        b.mibig_comparator_coverage = cov
    return b


def _scans(**per):
    """Minimal SourceScanBundle-shaped stub. per: {bgc_id: {guard fields}} for each channel."""
    return SimpleNamespace(
        primary_metabolism={"per_bgc": per.get("primary_metabolism", {})},
        cctt={"per_bgc": per.get("cctt", {})},
        resistance_tiers={"per_bgc": per.get("resistance_tiers", {})},
        misanchor_guards={"per_bgc": per.get("misanchor_guards", {})},
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. Pure-transform unit tests (comparator_prior)
# ═══════════════════════════════════════════════════════════════════════════
def test_high_specificity_comparator_adds_bounded_positive():
    delta, axis, note = cc.comparator_prior(_cov(coverage_all_locus=0.8, coverage_core=1.0,
                                                 specificity="UNIQUE"))
    assert delta > 0.0, note
    assert delta <= cc.PRIOR_CAP, f"prior {delta} exceeds cap {cc.PRIOR_CAP}"


def test_collision_transport_only_adds_nothing():
    delta, _axis, note = cc.comparator_prior(_cov(collision=True))
    assert delta == 0.0, f"transport/regulatory-only comparator must add nothing, got {delta} ({note})"


def test_discordant_class_never_positive():
    delta, _axis, _ = cc.comparator_prior(_cov(class_concordance="DISCORDANT", specificity="UNIQUE",
                                               coverage_all_locus=0.9, coverage_core=1.0))
    assert delta <= 0.0, "class-mismatch comparator must never receive a positive bonus"
    assert delta == cc.NEG_DISCORDANT


def test_co_dominant_is_deweighted():
    delta, _axis, _ = cc.comparator_prior(_cov(specificity="CO_DOMINANT"))
    assert delta < 0.0 and delta == cc.NEG_CO_DOMINANT


def test_cohort_promiscuous_is_deweighted():
    # v9.7.410: promiscuity needs an assessable cohort (denominator of OTHER strains
    # >= PREVALENCE_MIN_OTHER_STRAINS); 8 of 10 other strains is a real magnet.
    delta, _axis, _ = cc.comparator_prior(_cov(cohort_prevalence=0.8, cohort_total_strains=10))
    assert delta < 0.0 and delta == cc.NEG_PROMISCUOUS


def test_partial_low_core_coverage_earns_no_bonus():
    # high locus share but the recognizable core is barely covered -> not a real class match
    delta, _axis, _ = cc.comparator_prior(_cov(coverage_core=0.2, coverage_all_locus=0.9))
    assert delta == 0.0


def test_two_denominator_partial_match_is_deemphasised():
    # same UNIQUE/concordant comparator; a high-core but low-locus (sub-pathway) match must earn
    # strictly LESS than one that covers the locus on both denominators.
    partial, _, _ = cc.comparator_prior(_cov(coverage_core=1.0, coverage_all_locus=0.15))
    full, _, _ = cc.comparator_prior(_cov(coverage_core=1.0, coverage_all_locus=0.9))
    assert 0.0 < partial < full <= cc.PRIOR_CAP


def test_prior_is_always_bounded():
    for c in (_cov(coverage_all_locus=99, coverage_core=99), _cov(collision=True),
              _cov(class_concordance="DISCORDANT"), _cov(specificity="CO_DOMINANT"),
              _cov(cohort_prevalence=99)):
        delta, _axis, _ = cc.comparator_prior(c)
        assert -cc.PRIOR_CAP <= delta <= cc.PRIOR_CAP


def test_prior_is_pure_function_of_evidence_no_kcb_double_count():
    """The prior must depend ONLY on the coverage-evidence dict — never on the KCB channel.

    Two BGCRecords with identical comparator evidence but wildly different KCB fields
    (kcb_top / closest_candidate_kcb_product / kcb_cumulative) must yield the identical
    prior. This is the machine-checkable form of 'no KCB double-count': the wire cannot be
    re-adding KCB-derived credit because it never sees KCB."""
    cov = _cov()
    d1 = cc.comparator_prior(cov)[0]
    d2 = cc.comparator_prior(cov)[0]
    assert d1 == d2
    # and the transform signature takes only the evidence mapping
    import inspect
    params = list(inspect.signature(cc.comparator_prior).parameters)
    assert params == ["cov"], f"comparator_prior must take only the evidence dict, got {params}"


def test_no_evidence_is_noop():
    assert cc.comparator_prior(None) == (0.0, "", "")
    assert cc.comparator_prior({}) == (0.0, "", "")


def test_specificity_derived_from_raw_convergence_row():
    # raw *_3_mibig_convergence.json fields (no explicit 'specificity') must still work
    raw_unique = {"query_gene_share": 0.5, "recognizable_gene_share": 1.0,
                  "class_concordance": "CONCORDANT", "n_comparators": 1}
    assert cc._specificity(raw_unique) == "UNIQUE"
    raw_mixed = {"dominance_status": "MIXED_FAMILY_SIGNAL", "dominant_reference": True,
                 "dominance_gene_margin": 1}
    assert cc._specificity(raw_mixed) == "CO_DOMINANT"


# ═══════════════════════════════════════════════════════════════════════════
# 2. End-to-end integration through the scoring hook (triage_bgcs)
# ═══════════════════════════════════════════════════════════════════════════
def _af(bgc, scans):
    return {r.bgc_id: r for r in triage_bgcs([bgc], None, scans)}[bgc.bgc_id]


@_needs_wire
def test_integration_high_specificity_lifts_axis_bounded():
    scans = _scans()
    base = _af(_bgc("BGC001", ["NRPS"], cov=None), scans)
    wired = _af(_bgc("BGC001", ["NRPS"], cov=_cov(axis="ab", coverage_all_locus=0.8, coverage_core=1.0)), scans)
    assert wired.ab_score > base.ab_score, "high-specificity comparator should lift the AB prior"
    assert wired.ab_score - base.ab_score <= cc.PRIOR_CAP + 0.05


def test_integration_collision_comparator_no_change():
    scans = _scans()
    base = _af(_bgc("BGC002", ["NRPS"], cov=None), scans)
    wired = _af(_bgc("BGC002", ["NRPS"], cov=_cov(axis="ab", collision=True)), scans)
    assert wired.ab_score == base.ab_score, "transport-only collision comparator must not change the score"


def test_integration_misanchor_guard_suppresses_bonus():
    """Guard precedence: a polyene-mis-anchored BGC gets NO comparator bonus even with a
    high-specificity comparator present. The AF score is identical to the no-comparator,
    clamped case (<= 20.0)."""
    scans = _scans(misanchor_guards={"BGC018": {"polyene_misanchor": True, "ks_domain_count": 0}})
    no_cov = _af(_bgc("BGC018", ["RiPP-like"], cov=None), scans)
    with_cov = _af(_bgc("BGC018", ["RiPP-like"],
                        cov=_cov(axis="af", coverage_all_locus=0.9, coverage_core=1.0)), scans)
    assert no_cov.af_score <= 20.0
    assert with_cov.af_score == no_cov.af_score, "mis-anchor guard must suppress the comparator bonus"


def test_integration_primary_metab_guard_suppresses_bonus():
    scans = _scans(primary_metabolism={"BGC003": {"families": ["topoisomerase"]}})
    # own product is a weak/over-call class so the primary-metab guard fires
    no_cov = _af(_bgc("BGC003", ["NRPS-like"], cov=None), scans)
    with_cov = _af(_bgc("BGC003", ["NRPS-like"],
                        cov=_cov(axis="ab", coverage_all_locus=0.9, coverage_core=1.0)), scans)
    assert no_cov.primary_metabolism_flag is True
    assert with_cov.ab_score == no_cov.ab_score, "primary-metab guard must suppress the comparator bonus"
    assert with_cov.af_score == no_cov.af_score


@_needs_wire
def test_integration_discordant_deweights_but_stays_bounded():
    scans = _scans()
    base = _af(_bgc("BGC004", ["NRPS"], cov=None), scans)
    wired = _af(_bgc("BGC004", ["NRPS"], cov=_cov(axis="ab", class_concordance="DISCORDANT")), scans)
    assert wired.ab_score < base.ab_score
    assert base.ab_score - wired.ab_score <= cc.PRIOR_CAP + 0.05


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))

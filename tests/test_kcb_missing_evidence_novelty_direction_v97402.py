"""v9.7.402 — audit W402-23 (Codex CODEX_402_DEEP_AUDIT_FEATURE_FOUNDRY_24H_2026-09-02 /
strategic-roadmap ACT-004): `scoring.py`'s novelty calculation used to add +5 for
`kcb_cumulative is None` (KCB evidence UNAVAILABLE — no comparator, a parser-degraded run, an
antiSMASH JSON that failed to parse) — the SAME direction as the `riq_score < 0.5` branch, which
fires on OBSERVED low similarity. Missing evidence is unknown, not a novelty observation; the two
must not be conflated. This locks the corrected behavior: removing/lacking KCB input can no longer
increase novelty relative to a present-but-unremarkable KCB value, and the two existing legitimate
branches (KCB overwhelming-cumulative penalty, RiQ observed-low-similarity bonus) are unaffected.
"""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.models import BGCRecord
from mamey.scoring import triage_bgcs


def _bgc(bgc_id, kcb=None, riq=None):
    return BGCRecord(bgc_id=bgc_id, contig="c1", region_number=1, start=1, end=9000, contig_length=20000,
                     products=["other"], edge_status="Interior", architecture_confidence="A",
                     kcb_cumulative=kcb, riq_score=riq,
                     kcb_evidence_state=("KNOWNCLUSTERBLAST_OBSERVED" if kcb is not None else "UNKNOWN_KCB"))


def _scans():
    return SimpleNamespace(primary_metabolism={"per_bgc": {}}, cctt={"per_bgc": {}},
                           resistance_tiers={"per_bgc": {}})


def _by_id(recs):
    return {r.bgc_id: r for r in recs}


def test_missing_kcb_does_not_increase_novelty_vs_present_unremarkable_kcb():
    # the audit's own acceptance test, directly: removing KCB input must never increase novelty.
    bgcs = [_bgc("DARK", kcb=None), _bgc("PRESENT", kcb=100)]  # 100 is present, unremarkable (not >10000)
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["DARK"].novelty_score <= recs["PRESENT"].novelty_score


def test_missing_kcb_alone_adds_no_novelty_credit():
    bgcs = [_bgc("DARK", kcb=None)]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["DARK"].novelty_score == 30.0   # base novelty for an "other"-class BGC, unmodified


def test_explicit_unknown_state_cannot_apply_stale_kcb_penalty():
    b = _bgc("STALE", kcb=90000)
    b.kcb_evidence_state = "UNKNOWN_KCB"
    rec = _by_id(triage_bgcs([b], None, _scans()))["STALE"]
    assert rec.novelty_score == 30.0


def test_overwhelming_kcb_cumulative_penalty_still_applies():
    bgcs = [_bgc("SWAMPED", kcb=90000)]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["SWAMPED"].novelty_score == 15.0   # 30 - 15, legitimate branch untouched


def test_observed_low_riq_similarity_still_earns_novelty_credit():
    # the legitimate branch: OBSERVED dissimilarity (riq_score present and low) is real evidence,
    # unlike a missing kcb_cumulative — must remain untouched by this fix.
    bgcs = [_bgc("DISSIMILAR", kcb=100, riq=0.2)]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["DISSIMILAR"].novelty_score == 40.0   # 30 + 10, legitimate branch untouched


def test_missing_riq_alone_adds_no_novelty_credit():
    bgcs = [_bgc("NO_RIQ", kcb=100, riq=None)]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["NO_RIQ"].novelty_score == 30.0   # already correct pre-patch; locked here alongside

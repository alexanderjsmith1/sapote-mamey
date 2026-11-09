"""Wet-lab matrix KCB terms read the engine's percent bands, not the cumulative score.

Ruling (6 Nov): move tools/build_wetlab_matrix.py from the KCB cumulative-score gate (> 5,000) to
the antiSMASH percent bands in mamey.precision. Before, a cumulative score of 8,000 on a 30%
similarity hit earned "Strong KCB" and a missing score counted as "No KCB" (+4 for Arch A). Now a
blank or out-of-range percent is missing and moves no KCB term.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("build_wetlab_matrix_464r3", ROOT / "tools" / "build_wetlab_matrix.py")
wl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wl)

from mamey.precision import KCB_PCT_HIGH, KCB_PCT_MODERATE  # noqa: E402

OBS = "KNOWNCLUSTERBLAST_OBSERVED"


def _b(**kw):
    row = {"edge_status": "Interior", "architecture_confidence": "A", "length_kb": 40, "products": ["NRPS"]}
    row.update(kw)
    return row


def _terms(b):
    return [t for t, _, _ in wl.score_bgc(b, "T1")[1]]


def test_high_percent_earns_strong_kcb_whatever_the_cumulative_score():
    terms = _terms(_b(kcb_similarity_pct=KCB_PCT_HIGH, kcb_cumulative=900, kcb_evidence_state=OBS))
    assert any(t.startswith("Strong KCB") for t in terms)


def test_large_cumulative_score_on_a_low_percent_is_not_strong():
    terms = _terms(_b(kcb_similarity_pct=30, kcb_cumulative=8000, kcb_evidence_state=OBS))
    assert not any(t.startswith("Strong KCB") for t in terms)
    assert not any(t.startswith("No KCB") for t in terms)


def test_missing_percent_is_missing_not_no_kcb():
    for value in (None, "", "n/a", 250, "not a number"):
        b = _b(kcb_similarity_pct=value, kcb_cumulative=0, length_kb=3, edge_status="Edge")
        base, terms, notes = wl.score_bgc(b, "T1")
        names = [t for t, _, _ in terms]
        assert not any(t.startswith(("Strong KCB", "No KCB", "tiny unanchored")) for t in names), value
        assert any("KCB percent: missing" in n for n in notes)
        assert wl.action_scores(b, base, "T1")[3] == "NOT_EVALUATED"  # missing percent, no RiQ


def test_unknown_state_wins_over_a_stale_percent():
    assert not any(t.startswith("Strong KCB") for t in _terms(_b(kcb_similarity_pct=95, kcb_evidence_state="UNKNOWN_KCB")))


def test_observed_no_hits_is_the_no_kcb_term():
    terms = _terms(_b(kcb_evidence_state="KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED"))
    assert "No KCB + strong diagnostic (Arch A)" in terms


def test_dereplication_follows_the_moderate_band():
    b = _b(kcb_similarity_pct=KCB_PCT_MODERATE, kcb_evidence_state=OBS)
    assert wl.action_scores(b, wl.score_bgc(b, "T1")[0], "T1")[3] == "HIGH"
    b = _b(kcb_similarity_pct=KCB_PCT_MODERATE - 1, kcb_cumulative=5000, kcb_evidence_state=OBS)
    assert wl.action_scores(b, wl.score_bgc(b, "T1")[0], "T1")[3] == "LOW"

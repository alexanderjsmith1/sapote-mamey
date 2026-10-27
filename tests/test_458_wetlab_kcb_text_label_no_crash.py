"""The wet-lab matrix scores a BGC that has a KCB text label but no cumulative score.

score_bgc and action_scores ran float(kcb_cumulative or kcb_top or 0); kcb_top is the MIBiG
identity text, so any BGC without a cumulative score raised ValueError and stopped the matrix.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("build_wetlab_matrix_458k", ROOT / "tools" / "build_wetlab_matrix.py")
wl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wl)


def test_text_label_without_score_scores_as_zero():
    b = {"edge_status": "Interior", "architecture_confidence": "A", "kcb_cumulative": None,
         "kcb_top": "streptomycin (60% of genes show similarity)", "length_kb": 40}
    base, _, _ = wl.score_bgc(b, "T1")
    assert wl.action_scores(b, base, "T1")[3] == "LOW"   # no KCB number -> dereplication LOW


def test_numeric_score_is_still_used():
    b = {"edge_status": "Interior", "architecture_confidence": "A", "kcb_cumulative": 5000,
         "kcb_top": "x", "length_kb": 40}
    base, _, _ = wl.score_bgc(b, "T1")
    assert wl.action_scores(b, base, "T1")[3] == "HIGH"   # kcb > 1000

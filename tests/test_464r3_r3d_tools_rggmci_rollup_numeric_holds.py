"""RG-GMCI cohort rollup: a missing, nonfinite or out-of-range tier field is a listed hold, not zero
and not a crash."""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rggmci_rollup_r3d", ROOT / "tools" / "rggmci_cohort_rollup.py")
RR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RR)

COLS = ["pair", "rggmci_confidence", "subject_tiling_verdict", "terminus_override_note", "rggmci_score",
        "complementary_disjoint_refs", "n_shared_subjects", "a_core_fraction", "b_core_fraction",
        "interpretation_guard", "bgc_a", "contig_a", "bgc_b", "contig_b"]


def _row(**kw):
    row = {"pair": "p1", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
           "subject_tiling_verdict": "COMPLEMENTARY_SPLIT", "terminus_override_note": "", "rggmci_score": "30",
           "complementary_disjoint_refs": "4", "n_shared_subjects": "1", "a_core_fraction": "0.3",
           "b_core_fraction": "0.3", "interpretation_guard": "", "bgc_a": "a", "contig_a": "c1",
           "bgc_b": "b", "contig_b": "c2"}
    row.update(kw)
    return row


def test_infinite_count_does_not_crash_and_is_held():
    row = _row(complementary_disjoint_refs="inf")
    assert RR.confidence_tier(row) == "NEEDS-REVIEW"
    assert RR.numeric_holds(row) == ["complementary_disjoint_refs:malformed"]


def test_missing_and_out_of_range_fields_are_listed_not_zeroed():
    row = _row(a_core_fraction="", b_core_fraction="1.7", n_shared_subjects="-2")
    assert RR.numeric_holds(row) == ["n_shared_subjects:out_of_range", "a_core_fraction:missing",
                                     "b_core_fraction:out_of_range"]
    assert RR.confidence_tier(row) == "NEEDS-REVIEW"


def test_clean_row_is_unchanged():
    assert RR.numeric_holds(_row()) == []
    assert RR.confidence_tier(_row()) == "CONFIRMABLE"


def test_board_is_written_with_a_held_row(tmp_path):
    pkg = tmp_path / "pkgs" / "STRAIN_A"
    pkg.mkdir(parents=True)
    with (pkg / "STRAIN_A_4A_RGGMCI_ranked_pairs.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerow(_row(complementary_disjoint_refs="inf", rggmci_score="nan"))
        w.writerow(_row(pair="p2", rggmci_score="10"))
    assert RR.main(["--packages", str(tmp_path / "pkgs"), "--out-prefix", str(tmp_path / "out" / "R")]) == 0
    board = (tmp_path / "out" / "R_board.md").read_text()
    assert "numeric hold: complementary_disjoint_refs:malformed" in board
    rows = list(csv.DictReader((tmp_path / "out" / "R_evidence.csv").open()))
    assert [r["pair"] for r in rows] == ["p2", "p1"]
    assert rows[1]["numeric_hold"] == "complementary_disjoint_refs:malformed"
    assert rows[1]["confidence_tier"] == "NEEDS-REVIEW"

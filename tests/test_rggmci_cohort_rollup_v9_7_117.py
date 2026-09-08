"""v9.7.117: RG-GMCI cohort rollup — pool per-strain ranked_pairs, rank by genuineness, tier.

Unit tests pin the verdict classification + confidence tiering on synthetic rows (no data needed);
a real-data test cross-checks a real package if the package is present (env-supplied path, no strain literal).
"""
import os
import sys
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rggmci_cohort_rollup as RR  # noqa: E402


def _row(**kw):
    base = {"subject_tiling_verdict": "", "terminus_override_note": "",
            "complementary_disjoint_refs": "0", "n_shared_subjects": "0",
            "interpretation_guard": "", "a_core_fraction": "0.2", "b_core_fraction": "0.2",
            "rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "rggmci_score": "30"}
    base.update(kw)
    return base


# --- effective verdict + terminus promotion ---

def test_complementary_is_genuine():
    assert RR.effective_verdict(_row(subject_tiling_verdict="COMPLEMENTARY_SPLIT")) == "COMPLEMENTARY_SPLIT"


def test_paralog_is_not_promoted():
    assert RR.effective_verdict(_row(subject_tiling_verdict="OVERLAPPING_PARALOG")) == "OVERLAPPING_PARALOG"


def test_terminus_override_promotes_insufficient():
    r = _row(subject_tiling_verdict="INSUFFICIENT_SUBJECT_DATA",
             terminus_override_note="PROMOTED_FROM_INSUFFICIENT_SUBJECT_DATA_severed_arm")
    assert RR.effective_verdict(r) == "TERMINUS_TRUNCATION_SPLIT"


def test_terminus_override_does_not_demote_complementary():
    r = _row(subject_tiling_verdict="COMPLEMENTARY_SPLIT", terminus_override_note="severed_arm")
    assert RR.effective_verdict(r) == "COMPLEMENTARY_SPLIT"


# --- confidence tiering ---

def test_confirmable_needs_strong_disjoint_low_shared():
    r = _row(complementary_disjoint_refs="4", n_shared_subjects="1",
             a_core_fraction="0.3", b_core_fraction="0.3")
    assert RR.confidence_tier(r) == "CONFIRMABLE"


def test_distant_caution_forces_review():
    r = _row(complementary_disjoint_refs="5", n_shared_subjects="0",
             interpretation_guard="DISTANT_ON_REFERENCE_CAUTION", a_core_fraction="0.3", b_core_fraction="0.3")
    assert RR.confidence_tier(r) == "NEEDS-REVIEW"


def test_weak_disjoint_is_review():
    assert RR.confidence_tier(_row(complementary_disjoint_refs="1")) == "NEEDS-REVIEW"


def test_middle_is_likely():
    r = _row(complementary_disjoint_refs="2", n_shared_subjects="3",
             a_core_fraction="0.1", b_core_fraction="0.1")
    assert RR.confidence_tier(r) == "LIKELY"


# --- rollup excludes paralogs, queues mixed ---

def test_rollup_excludes_paralog_and_queues_mixed(tmp_path):
    import csv
    pkg = tmp_path / "AS-900"
    pkg.mkdir()
    f = pkg / "AS-900_4A_RGGMCI_ranked_pairs.csv"
    rows = [
        _row(pair="BGC1+BGC2", subject_tiling_verdict="COMPLEMENTARY_SPLIT",
             complementary_disjoint_refs="4", n_shared_subjects="1",
             a_core_fraction="0.3", b_core_fraction="0.3"),
        _row(pair="BGC3+BGC4", subject_tiling_verdict="OVERLAPPING_PARALOG"),
        _row(pair="BGC5+BGC6", subject_tiling_verdict="MIXED_SUBJECT_SIGNAL"),
        _row(pair="BGC7+BGC8", subject_tiling_verdict="INSUFFICIENT_SUBJECT_DATA"),
    ]
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    s = RR.rollup(str(tmp_path))
    assert s["n_high"] == 4
    assert s["n_genuine"] == 1
    assert s["n_complementary"] == 1
    assert s["n_excluded_paralog"] == 1
    assert s["n_review"] == 1   # the mixed one; insufficient is neither


# --- real-data cross-check, env-supplied, no strain literal in source ---

_RP = os.environ.get("RGGMCI_RANKED_PAIRS",
                     "/data/mamey-local/_local_rggmci_ranked_pairs.csv")


@pytest.mark.skipif(not os.path.exists(_RP), reason="no real ranked_pairs present (set RGGMCI_RANKED_PAIRS)")
def test_real_data_classification_matches_manual(tmp_path):
    import shutil
    sid = os.path.basename(_RP).split("_4A_RGGMCI")[0]
    pkg = tmp_path / sid
    pkg.mkdir()
    shutil.copy(_RP, pkg / os.path.basename(_RP))
    s = RR.rollup(str(tmp_path))
    # the rollup's counts must equal a direct verdict tally of the HIGH subset
    import csv
    high = [r for r in csv.DictReader(open(_RP)) if "HIGH" in r["rggmci_confidence"].upper()]
    assert s["n_high"] == len(high)
    assert s["n_genuine"] == s["n_complementary"] + s["n_terminus"]
    assert s["n_genuine"] + s["n_excluded_paralog"] + s["n_review"] <= s["n_high"]


def test_is_high_no_substring_false_match():
    """Bug Hunt v9.7.117: _is_high must anchor on the real HIGH confidence token, not bare substring
    — a bare `'HIGH' in conf` would false-match 'NOT_HIGH_CONFIDENCE' / 'HIGHLY_UNCERTAIN'."""
    assert RR._is_high("HIGH_RG_GMCI_RESCUE")
    assert RR._is_high("HIGH")                          # legacy bare form
    assert not RR._is_high("LOW_SHARED_REFERENCE_SIGNAL")
    assert not RR._is_high("MODERATE_RG_GMCI_CANDIDATE")
    assert not RR._is_high("HIGHLY_UNCERTAIN_REJECT")   # substring landmine
    assert not RR._is_high("NOT_HIGH_CONFIDENCE")       # negation landmine
    assert not RR._is_high("")
    assert not RR._is_high(None)


def test_nested_savework_copy_not_double_counted(tmp_path):
    """Bug Hunt v9.7.117: a stale ranked_pairs copy in a nested _savework/ dir must NOT double-count.
    The recursive glob would otherwise inflate every cohort total."""
    import csv

    def _write(path, n):
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(_row(pair="").keys()))
            w.writeheader()
            for i in range(n):
                w.writerow(_row(pair=f"P{i}", subject_tiling_verdict="COMPLEMENTARY_SPLIT",
                                complementary_disjoint_refs="4", n_shared_subjects="1",
                                a_core_fraction="0.3", b_core_fraction="0.3"))

    pkg = tmp_path / "AS-900"
    (pkg / "_savework").mkdir(parents=True)
    _write(pkg / "AS-900_4A_RGGMCI_ranked_pairs.csv", 2)
    _write(pkg / "_savework" / "AS-900_4A_RGGMCI_ranked_pairs.csv", 2)   # stale dup
    s = RR.rollup(str(tmp_path))
    assert s["n_high"] == 2          # dedup'd, not 4
    assert s["n_genuine"] == 2


def test_distinct_strains_both_counted(tmp_path):
    import csv

    def _write(path, n):
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(_row(pair="").keys()))
            w.writeheader()
            for i in range(n):
                w.writerow(_row(pair=f"P{i}", subject_tiling_verdict="COMPLEMENTARY_SPLIT",
                                complementary_disjoint_refs="4", n_shared_subjects="1",
                                a_core_fraction="0.3", b_core_fraction="0.3"))

    (tmp_path / "AS-900").mkdir()
    (tmp_path / "AS-901").mkdir()
    _write(tmp_path / "AS-900" / "AS-900_4A_RGGMCI_ranked_pairs.csv", 2)
    _write(tmp_path / "AS-901" / "AS-901_4A_RGGMCI_ranked_pairs.csv", 3)
    s = RR.rollup(str(tmp_path))
    assert s["n_high"] == 5

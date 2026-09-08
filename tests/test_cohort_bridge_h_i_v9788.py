"""v9.7.88 9.7.88-H + 9.7.88-I: cohort high/moderate prefix-match and manifest-short fallback."""
from __future__ import annotations
import json, csv, os, tempfile
from mamey.cohort_figures import _strain_summary_row


def _pkg_with(tmp, ranked_rows, manifest_short=None):
    pkg = os.path.join(tmp, "package"); os.makedirs(pkg, exist_ok=True)
    with open(os.path.join(pkg, "S_4A_RGGMCI_ranked_pairs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["bgc_a", "bgc_b", "rggmci_confidence",
                                          "rggmci_score", "good_geometry_references",
                                          "supporting_references"])
        w.writeheader()
        for r in ranked_rows:
            w.writerow(r)
    if manifest_short is not None:
        with open(os.path.join(pkg, "manifest_short.json"), "w") as f:
            json.dump(manifest_short, f)
    return pkg


def test_h_full_tier_labels_counted():
    tmp = tempfile.mkdtemp()
    pkg = _pkg_with(tmp, [
        {"bgc_a": "B1", "bgc_b": "B2", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "rggmci_score": "20", "good_geometry_references": "2", "supporting_references": "5"},
        {"bgc_a": "B3", "bgc_b": "B4", "rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE",
         "rggmci_score": "10", "good_geometry_references": "1", "supporting_references": "3"},
    ])
    row, _ = _strain_summary_row("S", pkg, {})
    assert row["high_pairs"] == 1, "HIGH_RG_GMCI_RESCUE must count as high (prefix match)"
    assert row["moderate_pairs"] == 1


def test_i_manifest_fallback_for_counts():
    tmp = tempfile.mkdtemp()
    pkg = _pkg_with(tmp, [], manifest_short={
        "raw_bgcs": 57, "corrected_bgcs": 36.5, "assembly_tier": "POOR", "interior_pct": 36.8})
    # empty result dict -> must fall back to manifest_short, not zero out
    row, _ = _strain_summary_row("S", pkg, {})
    assert row["raw_bgcs"] == 57
    assert row["corrected_bgcs"] == 36.5
    assert row["assembly_tier"] == "POOR"

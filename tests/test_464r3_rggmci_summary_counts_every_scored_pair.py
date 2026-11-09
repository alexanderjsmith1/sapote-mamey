"""SUMMARY.tsv counts every scored pair, not only the rows kept after the 1,000-pair display cap."""
from mamey.rggmci import RGGMCI_MAX_RANKED_PAIRS, SUMMARY_COLUMNS, result_summary


def _pair(i, confidence):
    return {"pair": f"P{i}", "rggmci_confidence": confidence, "contig_a": "c1", "contig_b": "c2",
            "both_at_contig_ends": True}


def test_capped_result_reports_total_and_kept_rows():
    kept = [_pair(i, "HIGH_RG_GMCI_RESCUE") for i in range(3)]
    kept += [_pair(i, "MODERATE_RG_GMCI_CANDIDATE") for i in range(3, RGGMCI_MAX_RANKED_PAIRS)]
    result = {"regions": [{}] * 50, "ranked_pairs": kept, "pairs_total": 1360, "high_pairs": 3,
              "moderate_pairs": 1200}
    row = result_summary("g", result)
    assert row["scored_pairs"] == 1360
    assert row["pairs_exported"] == RGGMCI_MAX_RANKED_PAIRS
    assert row["high"] == 3 and row["moderate"] == 1200
    assert SUMMARY_COLUMNS.index("pairs_exported") == SUMMARY_COLUMNS.index("scored_pairs") + 1


def test_uncapped_result_counts_agree():
    pairs = [_pair(0, "MODERATE_RG_GMCI_CANDIDATE")]
    row = result_summary("g", {"regions": [{}], "ranked_pairs": pairs, "pairs_total": 1, "high_pairs": 0,
                               "moderate_pairs": 1})
    assert row["scored_pairs"] == row["pairs_exported"] == 1

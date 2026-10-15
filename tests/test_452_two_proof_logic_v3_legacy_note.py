"""Two-proof logic version 3 (.452): a legacy _4A without the overlap column keeps its verdict, and the receipt says
the overlap count was absent and read as zero (owner ruling, 14 Oct 2026)."""
import csv

from mamey.rescue_two_proof import TWO_PROOF_LOGIC_VERSION, two_proof_join, write_4d_csv

# AMBIGUOUS takes the disjoint-reference fallback, the only path that reads the overlap column.
BASE = {"contig_a": "NODE_1_length_9000_cov_10", "contig_b": "NODE_2_length_8000_cov_10",
        "rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "rggmci_score": "0.9", "functional_rescue_class": "AMBIGUOUS",
        "bgc_a": "BGC001", "bgc_b": "BGC002", "complementary_disjoint_refs": "4"}


def _write_4a(path, row):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row)); w.writeheader(); w.writerow(row)
    return str(path)


def _rows(tmp_path, row):
    rows, _, _ = two_proof_join(_write_4a(tmp_path / "S_4A_RGGMCI_ranked_pairs.csv", row), {"cross_contig_clades": []})
    out = write_4d_csv(rows, tmp_path / "S_4D.csv", "S")
    return rows, list(csv.DictReader(open(out)))


def test_version_is_three():
    assert TWO_PROOF_LOGIC_VERSION == "3"


def test_legacy_row_keeps_its_verdict_and_says_the_count_was_absent(tmp_path):
    rows, written = _rows(tmp_path, dict(BASE))
    assert written[0]["verdict"] == "RGGMCI_ONLY"
    assert "overlap count absent" in written[0]["claim_note"] and "read as zero" in written[0]["claim_note"]
    assert written[0]["two_proof_logic_version"] == "3"
    assert "_overlap_column_absent" not in written[0]


def test_measured_zero_overlap_has_no_legacy_note(tmp_path):
    _, written = _rows(tmp_path, dict(BASE, overlapping_subject_refs="0"))
    assert written[0]["verdict"] == "RGGMCI_ONLY"
    assert "overlap count absent" not in written[0]["claim_note"]


def test_blank_overlap_still_holds(tmp_path):
    _, written = _rows(tmp_path, dict(BASE, overlapping_subject_refs=""))
    assert written[0]["verdict"] == "LOGIC_EVIDENCE_HOLD"
    assert "overlap count absent" not in written[0]["claim_note"]

"""Ruling 7 (6 Nov 2026): a 4A table with no overlapping_subject_refs column is held as unmeasured,
exactly like a blank cell. It never reads as zero overlap and never lets the logic proof pass."""
import csv
from mamey.rescue_two_proof import _logic_proof, _logic_proof_state, two_proof_join, write_4d_csv

FALLBACK = {"rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "functional_rescue_class": "AMBIGUOUS",
            "complementary_disjoint_refs": "4"}


def test_missing_column_is_unresolved_not_present():
    assert _logic_proof_state(dict(FALLBACK)) == "UNRESOLVED_NO_OVERLAP_COLUMN"
    assert not _logic_proof(dict(FALLBACK))
    assert _logic_proof_state(dict(FALLBACK, overlapping_subject_refs="")) == "UNRESOLVED"
    assert _logic_proof(dict(FALLBACK, overlapping_subject_refs="0"))


def test_missing_column_row_is_logic_evidence_hold_in_4d(tmp_path):
    row = {"contig_a": "NODE_1", "contig_b": "NODE_2", "bgc_a": "BGC001", "bgc_b": "BGC002", **FALLBACK}
    path = tmp_path / "S_4A_RGGMCI_ranked_pairs.csv"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row)); w.writeheader(); w.writerow(row)
    rows, summary, counts = two_proof_join(str(path), {"cross_contig_clades": []})
    assert counts["LOGIC_EVIDENCE_HOLD"] == 1 and counts["RGGMCI_ONLY"] == 0
    out = write_4d_csv(rows, tmp_path / "S_4D.csv", "S")
    written = list(csv.DictReader(open(out)))[0]
    assert written["verdict"] == "LOGIC_EVIDENCE_HOLD"
    assert "held as unmeasured" in written["claim_note"]

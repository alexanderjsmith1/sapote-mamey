"""A blank or malformed overlap count holds the two-proof logic fallback instead of passing it (P300-144)."""
import csv
import os

import pytest

from mamey.rescue_two_proof import _logic_proof, two_proof_join, write_4d_csv


def _row(ov, cdr="6", frc="AMBIGUOUS"):
    return {"rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "functional_rescue_class": frc,
            "complementary_disjoint_refs": cdr, "overlapping_subject_refs": ov}


def _write_4a(path, rows):
    cols = ["contig_a", "contig_b", "rggmci_confidence", "rggmci_score", "functional_rescue_class",
            "complementary_disjoint_refs", "overlapping_subject_refs", "bgc_a", "bgc_b"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    return path


@pytest.mark.parametrize("ov", ["", "  ", "n/a", "0.5", "-1", "nan", "inf", "1e0", None])
def test_unreadable_overlap_does_not_pass_the_fallback(ov):
    assert not _logic_proof(_row(ov))


@pytest.mark.parametrize("cdr", ["inf", "3.5"])
def test_unreadable_disjoint_count_is_not_positive_evidence(cdr):
    assert not _logic_proof(_row("0", cdr=cdr))


def test_measured_counts_keep_their_outcome():
    assert _logic_proof(_row("0"))
    assert _logic_proof(_row(" 0 "))
    assert _logic_proof(_row("0.0"))
    assert not _logic_proof(_row("1"))
    assert not _logic_proof(_row("0", cdr="2"))
    assert _logic_proof(_row("", frc="COMPLEMENTARY"))       # independent proof, unaffected


def test_blank_overlap_without_ks_is_a_hold_not_rescue_or_weak(tmp_path):
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_1", "contig_b": "NODE_2", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "AMBIGUOUS", "complementary_disjoint_refs": "6",
         "overlapping_subject_refs": ""},
        {"contig_a": "NODE_3", "contig_b": "NODE_4", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "AMBIGUOUS", "complementary_disjoint_refs": "6",
         "overlapping_subject_refs": "0"},
    ])
    rows, summary, counts = two_proof_join(a4, {"cross_contig_clades": []})
    verds = {(r["contig_a"], r["contig_b"]): r["verdict"] for r in rows}
    assert verds[("NODE_1", "NODE_2")] == "LOGIC_EVIDENCE_HOLD"
    assert verds[("NODE_3", "NODE_4")] == "RGGMCI_ONLY"              # measured zero: unchanged
    assert counts["LOGIC_EVIDENCE_HOLD"] == 1 and counts["RGGMCI_ONLY"] == 1 and counts["WEAK"] == 0
    assert "1 LOGIC_EVIDENCE_HOLD" in summary
    out = write_4d_csv(rows, os.path.join(tmp_path, "X_4D.csv"), "X")
    with open(out, newline="") as fh:
        written = list(csv.DictReader(fh))
    hold = [r for r in written if r["verdict"] == "LOGIC_EVIDENCE_HOLD"]
    assert len(hold) == 1 and "NOT a rescue" in hold[0]["interpretation"]


def test_blank_overlap_with_ks_is_multi_channel_hold_not_two_proof(tmp_path):
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_1", "contig_b": "NODE_2", "rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE",
         "functional_rescue_class": "BOTH_CORE", "complementary_disjoint_refs": "4",
         "overlapping_subject_refs": "not_computed"},
    ])
    rows, _, counts = two_proof_join(a4, {"cross_contig_clades": [{"clade_id": "KSC01",
                                                                   "contigs": ["NODE_1", "NODE_2"]}]})
    assert [r["verdict"] for r in rows] == ["MULTI_CHANNEL_HOLD"]
    assert counts["TWO_PROOF_RESCUE"] == 0

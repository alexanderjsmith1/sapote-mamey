"""Deterministic tests for the _4D two-proof rescue join (Cerulean C06 gate). No shipped data."""
import csv
import os

from mamey.rescue_two_proof import two_proof_join, write_4d_csv, _logic_proof


def _scan(clades):
    return {"cross_contig_clades": clades}


def _write_4a(path, rows):
    cols = ["contig_a", "contig_b", "rggmci_confidence", "rggmci_score",
            "functional_rescue_class", "complementary_disjoint_refs", "bgc_a", "bgc_b"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    return path


def test_logic_proof_gate():
    # COMPLEMENTARY is the genuine split signature (clusterblast_genes.py: one fragment core,
    # the other accessory) -- it alone satisfies the biosynthetic-logic complementarity proof.
    assert _logic_proof({"rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "functional_rescue_class": "COMPLEMENTARY"})
    assert _logic_proof({"rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE",
                         "functional_rescue_class": "COMPLEMENTARY", "complementary_disjoint_refs": "3"})
    # BOTH_CORE is documented paralogy ("corroborates an OVERLAPPING_PARALOG subject-tiling
    # verdict"), NOT complementarity -- it must NOT satisfy the logic proof on its own.
    assert not _logic_proof({"rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "functional_rescue_class": "BOTH_CORE"})
    # ...but strong independent subject-tiling corroboration (cdr>=3) still carries a BOTH_CORE row.
    assert _logic_proof({"rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
                         "functional_rescue_class": "BOTH_CORE", "complementary_disjoint_refs": "3"})
    # ACCESSORY_ONLY never passes
    assert not _logic_proof({"rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "functional_rescue_class": "ACCESSORY_ONLY"})
    # AMBIGUOUS with too few disjoint refs fails
    assert not _logic_proof({"rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE",
                             "functional_rescue_class": "AMBIGUOUS", "complementary_disjoint_refs": "1"})
    # low confidence fails regardless
    assert not _logic_proof({"rggmci_confidence": "LOW", "functional_rescue_class": "COMPLEMENTARY"})


def test_two_proof_and_refdark(tmp_path):
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_1", "contig_b": "NODE_2", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "COMPLEMENTARY", "rggmci_score": "29"},
        {"contig_a": "NODE_3", "contig_b": "NODE_4", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "ACCESSORY_ONLY"},                        # logic fails
    ])
    # KS clade links NODE_1+NODE_2 (matches the strong _4A pair) AND NODE_5+NODE_6 (reference-dark)
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_1", "NODE_2"]},
                  {"clade_id": "KSC02", "contigs": ["NODE_5", "NODE_6"]}])
    rows, summary, counts = two_proof_join(a4, scan)
    assert counts["TWO_PROOF_RESCUE"] == 1      # NODE_1+2
    assert counts["KS_CLADE_ONLY"] >= 1         # NODE_5+6 reference-dark
    assert counts["WEAK"] == 1                  # NODE_3+4 (logic failed, no KS)
    verds = {(r["contig_a"], r["contig_b"]): r["verdict"] for r in rows}
    assert verds[("NODE_1", "NODE_2")] == "TWO_PROOF_RESCUE"
    assert ("NODE_5", "NODE_6") in verds and verds[("NODE_5", "NODE_6")] == "KS_CLADE_ONLY"


def test_4d_csv_claim_safe(tmp_path):
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [])
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_5", "NODE_6"]}])
    rows, _, _ = two_proof_join(a4, scan)
    out = write_4d_csv(rows, os.path.join(tmp_path, "X_4D.csv"), "X")
    body = open(out).read()
    assert "not a merge" in body.lower() and "judgment deferred" in body.lower()


def test_missing_4a_degrades(tmp_path):
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_5", "NODE_6"]}])
    rows, summary, counts = two_proof_join("/no/such/_4A.csv", scan)
    assert counts["KS_CLADE_ONLY"] >= 1 and counts["TWO_PROOF_RESCUE"] == 0   # KS-only still surfaces

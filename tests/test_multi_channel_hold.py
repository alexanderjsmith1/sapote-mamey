"""'.368' MULTI_CHANNEL_HOLD surfacer — the owner-ruled two-proof advisory verdict.

Rulings encoded here (both 2026-08-17):
  * Cerulean (two-proof): RG-GMCI homology + KS-clade homology = proof-1 + proof-1, NOT proof-1 + proof-2.
    A HIGH/MODERATE RG-GMCI pair that FAILS the complementarity (logic) proof, with KS-clade co-membership,
    is a HOLD (two homology channels concordant, complementarity owed), NEVER a rescue. Surfacer only.
  * Amber (_4B owner): the KS-clade partition is unchanged; _4B stays byte-identical (no cross-subtype bridge).
  * AS-922 control: the in-engine KS channel is containment single-linkage, not "any shared ancestor UFBoot",
    so the naive-backbone false positive cannot arise here.

No shipped data; deterministic.
"""
import csv
import os

from mamey.rescue_two_proof import two_proof_join, write_4d_csv, TWO_PROOF_LOGIC_VERSION


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


def test_multi_channel_hold_fires_on_ranked_but_logic_failed_with_ks(tmp_path):
    # RG-GMCI ranked HIGH but complementarity (logic) FAILED (ACCESSORY_ONLY); KS-clade groups the same pair.
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_18", "contig_b": "NODE_48", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "ACCESSORY_ONLY"},
    ])
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_18", "NODE_48"]}])
    rows, summary, counts = two_proof_join(a4, scan)
    verds = {(r["contig_a"], r["contig_b"]): r["verdict"] for r in rows}
    assert verds[("NODE_18", "NODE_48")] == "MULTI_CHANNEL_HOLD"
    assert counts["MULTI_CHANNEL_HOLD"] == 1
    # it is a HOLD, never a rescue
    assert counts["TWO_PROOF_RESCUE"] == 0
    assert "MULTI_CHANNEL_HOLD" in summary


def test_moderate_confidence_paralog_with_ks_is_hold(tmp_path):
    # MODERATE + AMBIGUOUS + too few disjoint refs (logic fails), KS present -> HOLD.
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_22", "contig_b": "NODE_48", "rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE",
         "functional_rescue_class": "AMBIGUOUS", "complementary_disjoint_refs": "1"},
    ])
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_22", "NODE_48"]}])
    rows, _, counts = two_proof_join(a4, scan)
    verds = {(r["contig_a"], r["contig_b"]): r["verdict"] for r in rows}
    assert verds[("NODE_22", "NODE_48")] == "MULTI_CHANNEL_HOLD"


def test_logic_pass_with_ks_is_two_proof_not_hold(tmp_path):
    # COMPLEMENTARY (logic) remains the SOLE gate for a real rescue.
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_1", "contig_b": "NODE_2", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "COMPLEMENTARY"},
    ])
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_1", "NODE_2"]}])
    _, _, counts = two_proof_join(a4, scan)
    assert counts["TWO_PROOF_RESCUE"] == 1 and counts["MULTI_CHANNEL_HOLD"] == 0


def test_low_confidence_with_ks_is_not_hold(tmp_path):
    # Below HIGH/MODERATE, KS present but RG-GMCI signal too weak to call a concordance -> KS_CLADE_ONLY, not HOLD.
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_7", "contig_b": "NODE_9", "rggmci_confidence": "LOW",
         "functional_rescue_class": "ACCESSORY_ONLY"},
    ])
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_7", "NODE_9"]}])
    rows, _, counts = two_proof_join(a4, scan)
    verds = {(r["contig_a"], r["contig_b"]): r["verdict"] for r in rows}
    assert verds[("NODE_7", "NODE_9")] == "KS_CLADE_ONLY"
    assert counts["MULTI_CHANNEL_HOLD"] == 0


def test_ranked_logic_failed_without_ks_is_weak(tmp_path):
    # No KS co-membership -> cannot be a multi-channel concordance -> WEAK, unchanged behavior.
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_3", "contig_b": "NODE_4", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "ACCESSORY_ONLY"},
    ])
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_90", "NODE_91"]}])  # unrelated clade
    rows, _, counts = two_proof_join(a4, scan)
    verds = {(r["contig_a"], r["contig_b"]): r["verdict"] for r in rows}
    assert verds[("NODE_3", "NODE_4")] == "WEAK"
    assert counts["MULTI_CHANNEL_HOLD"] == 0


def test_reference_dark_stays_ks_clade_only(tmp_path):
    # A KS-clade pair RG-GMCI NEVER ranked (not in _4A) is reference-dark KS_CLADE_ONLY, NOT a multi-channel hold.
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [])
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_5", "NODE_6"]}])
    rows, _, counts = two_proof_join(a4, scan)
    verds = {(r["contig_a"], r["contig_b"]): r["verdict"] for r in rows}
    assert verds[("NODE_5", "NODE_6")] == "KS_CLADE_ONLY"
    assert counts["MULTI_CHANNEL_HOLD"] == 0


def test_hold_is_surfaced_and_claim_safe_in_4d(tmp_path):
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_18", "contig_b": "NODE_48", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "ACCESSORY_ONLY"},
    ])
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_18", "NODE_48"]}])
    rows, _, _ = two_proof_join(a4, scan)
    out = write_4d_csv(rows, os.path.join(tmp_path, "X_4D.csv"), "X")
    body = open(out).read()
    assert "MULTI_CHANNEL_HOLD" in body
    assert "advisory HOLD" in body.lower() or "not a rescue" in body.lower()
    assert "not a merge" in body.lower() and "judgment deferred" in body.lower()
    # self-declared gate version bumped for the new verdict
    assert TWO_PROOF_LOGIC_VERSION == "2"
    assert (",2," in body) or body.rstrip().endswith(",2") or "two_proof_logic_version" in open(out).readline()


def test_multi_channel_hold_is_engine_neutral():
    # The surfacer lives in _4D, which is NOT in the determinism fingerprint -> no engine bump required.
    from mamey.packaging import DETERMINISM_WHITELIST
    assert "_4D_two_proof_rescue.csv" not in DETERMINISM_WHITELIST
    # _4B (the KS partition Amber owns) is unchanged and still whitelisted.
    assert "_4B_pks_ks_fragment_scan.csv" in DETERMINISM_WHITELIST

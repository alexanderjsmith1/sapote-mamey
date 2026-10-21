"""A two-proof rescue needs a HIGH RG-GMCI pair on both routes (owner ruling, 20 Oct, .455).

Before, the KS route accepted a MODERATE pair as TWO_PROOF_RESCUE while the class-routed non-KS route needed HIGH."""
import os

from mamey.rescue_two_proof import two_proof_join
from tests.test_rescue_two_proof import _scan, _write_4a


def _join(tmp_path, confidence):
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_1", "contig_b": "NODE_2", "rggmci_confidence": confidence,
         "functional_rescue_class": "COMPLEMENTARY", "rggmci_score": "12"}])
    rows, _, counts = two_proof_join(a4, _scan([{"clade_id": "KSC01", "contigs": ["NODE_1", "NODE_2"]}]))
    return rows[0], counts


def test_high_pair_with_both_proofs_is_a_rescue(tmp_path):
    row, counts = _join(tmp_path, "HIGH_RG_GMCI_RESCUE")
    assert row["verdict"] == "TWO_PROOF_RESCUE" and counts["TWO_PROOF_RESCUE"] == 1


def test_moderate_pair_with_both_proofs_is_not_a_rescue_and_keeps_its_clade(tmp_path):
    row, counts = _join(tmp_path, "MODERATE_RG_GMCI_CANDIDATE")
    assert row["verdict"] == "RGGMCI_ONLY" and counts["TWO_PROOF_RESCUE"] == 0
    assert row["ks_clade_id"] == "KSC01"

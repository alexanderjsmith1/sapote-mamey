"""A two-proof row whose members are absent from the manifest cannot keep a rescue label (P300-111)."""
import csv

import pytest

from mamey import nonks_second_proof as N
from mamey.rescue_two_proof import write_4d_csv

MANIFEST = {
    "strain_id": "SYN-1",
    "bgcs": [
        {"bgc_id": "BGC001", "contig": "NODE_1_length_9000_cov_3.1", "region_number": 1,
         "start": 1, "end": 4000, "products": ["NRPS"]},
        {"bgc_id": "BGC002", "contig": "NODE_2_length_8000_cov_2.9", "region_number": 2,
         "start": 1, "end": 3000, "products": ["NRPS"]},
    ],
}


def _row(verdict, a="BGC001", b="BGC002", ca="NODE_1", cb="NODE_2"):
    return {"contig_a": ca, "contig_b": cb, "verdict": verdict, "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
            "rggmci_score": "9", "functional_rescue_class": "COMPLEMENTARY",
            "ks_clade_id": "C1" if verdict == "TWO_PROOF_RESCUE" else "", "bgc_a": a, "bgc_b": b}


@pytest.mark.parametrize("policy", ["ks_clade_v2", "nonks_position_v1"])
@pytest.mark.parametrize("verdict", ["TWO_PROOF_RESCUE", "RGGMCI_ONLY"])
def test_stale_member_holds_the_rescue(policy, verdict):
    out = N.apply_policy([_row(verdict, b="BGC099", cb="NODE_9")], MANIFEST, policy=policy)[0]
    assert out["verdict"] == "UNBOUND_MEMBER_HOLD"
    assert out["identity_b"].startswith("IDENTITY_HOLD: bgc_b 'BGC099' absent from the manifest")
    assert verdict in out["identity_b"]
    assert out["identity_a"] == "SYN-1 / NODE_1_length_9000_cov_3.1 / region001 / BGC001"


def test_both_members_missing_are_both_named():
    out = N.apply_policy([_row("TWO_PROOF_RESCUE", a="", b="")], MANIFEST)[0]
    assert out["verdict"] == "UNBOUND_MEMBER_HOLD"
    assert out["identity_a"].startswith("IDENTITY_HOLD: bgc_a")
    assert out["identity_b"].startswith("IDENTITY_HOLD: bgc_b")


def test_bound_rescue_and_reference_dark_rows_are_unchanged():
    bound = N.apply_policy([_row("TWO_PROOF_RESCUE")], MANIFEST)[0]
    assert bound["verdict"] == "TWO_PROOF_RESCUE"
    assert bound["identity_b"] == "SYN-1 / NODE_2_length_8000_cov_2.9 / region002 / BGC002"
    dark = N.apply_policy([_row("KS_CLADE_ONLY", a="", b="")], MANIFEST)[0]
    assert dark["verdict"] == "KS_CLADE_ONLY" and dark["identity_a"] == dark["identity_b"] == ""


def test_held_row_writes_through_the_existing_4d_columns(tmp_path):
    rows = N.apply_policy([_row("TWO_PROOF_RESCUE", b="BGC099", cb="NODE_9"), _row("TWO_PROOF_RESCUE")], MANIFEST)
    out = write_4d_csv(rows, tmp_path / "SYN-1_4D_two_proof_rescue.csv", "SYN-1")
    with open(out, newline="") as handle:
        written = list(csv.DictReader(handle))
    assert [r["verdict"] for r in written] == ["TWO_PROOF_RESCUE", "UNBOUND_MEMBER_HOLD"]
    assert written[1]["identity_b"].startswith("IDENTITY_HOLD")

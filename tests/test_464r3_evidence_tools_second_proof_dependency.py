"""Every 4D row names how its second-proof channel depends on the candidate's own source."""
import csv
import os
from mamey.rescue_two_proof import two_proof_join, write_4d_csv
from mamey import split_evidence_layers
from tests.test_rescue_two_proof import _scan, _write_4a


def test_ks_clade_row_is_labelled_same_source(tmp_path):
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_1", "contig_b": "NODE_2", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "COMPLEMENTARY", "rggmci_score": "29"}])
    rows, summary, _ = two_proof_join(a4, _scan([{"clade_id": "KSC01", "contigs": ["NODE_1", "NODE_2"]}]))
    out = write_4d_csv(rows, os.path.join(tmp_path, "X_4D.csv"), "X")
    row = next(csv.DictReader(open(out)))
    assert row["second_proof_channel"] == "KS_CLADE"
    assert row["second_proof_source_dependency"].startswith("SAME_SOURCE")
    assert "not independent source evidence" in summary


def test_layers_module_does_not_call_its_layers_independent_evidence():
    first = split_evidence_layers.__doc__.splitlines()[0]
    assert not first.startswith("Independent")
    assert "not\nindependent source evidence" in split_evidence_layers.__doc__ or \
        "not independent source evidence" in split_evidence_layers.__doc__.replace("\n", " ")

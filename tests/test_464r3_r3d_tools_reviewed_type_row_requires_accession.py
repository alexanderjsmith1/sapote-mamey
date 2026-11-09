"""An affirmative reviewed type row with a blank `accession` cell is a hold, as the guide states."""
import csv

import pytest
from tools import _placement_report_metadata as contract

TIP = "NR_000001_1_Genus_alpha_strain_A1_16S_ribosomal_RNA_partial_sequence"
LABEL = "NR_000001.1 Genus alpha strain A1 16S ribosomal RNA, partial sequence"


def _table(path, row):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
    return str(path)


def _row(**updates):
    row = dict(tip=TIP, accession="NR_000001.1", source_accession="NR_000001.1", taxon="Genus alpha",
               strain="A1", role="type_reference", type_strain_of="Genus alpha",
               type_evidence="synthetic explicit type-material record", review_state="REVIEWED",
               source_url="https://example.org/synthetic/NR_000001.1",
               strain_identity_basis="synthetic exact deposited strain A1")
    row.update(updates)
    return row


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_accession_on_affirmative_row_is_held(tmp_path, value):
    path = _table(tmp_path / "reviewed.tsv", _row(accession=value))
    with pytest.raises(ValueError, match="HOLD_TYPE_ACCESSION_MISSING"):
        contract.reviewed_type_map([path], {TIP: LABEL})


def test_matching_accession_is_admitted(tmp_path):
    path = _table(tmp_path / "reviewed.tsv", _row())
    assert TIP in contract.reviewed_type_map([path], {TIP: LABEL})["roles"]

"""Mode B templates name the full contig, so ingest accepts cards built on them.

Node_ID drops a SPAdes coverage decimal (NODE_1_length_613749_cov_47.990239 ->
NODE_1_length_613749_cov_47). Ingest compares the card's node with the package's full Contig,
so a card built on a template that printed Node_ID was rejected as a locus mismatch.
"""
import csv

import pytest

from mamey.mode_b_receipt import _card_identity_mismatch
from mamey.modeb_template_emitter import _header_block

FULL = "NODE_1_length_613749_cov_47.990239"
SHORT = "NODE_1_length_613749_cov_47"


def _package(tmp_path):
    with open(tmp_path / "STRAINX_2_inventory.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["BGC_ID", "Contig", "Node_ID", "antiSMASH_Region"])
        w.writeheader()
        w.writerow({"BGC_ID": "BGC001", "Contig": FULL, "Node_ID": SHORT, "antiSMASH_Region": "region001"})
    return tmp_path


@pytest.mark.parametrize("schema", ["modeb_full48_current", "modeb_current50_v2"])
def test_header_names_full_contig_and_ingest_accepts_it(tmp_path, schema):
    facts = {"bgc_id": "BGC001", "node": SHORT, "contig": FULL, "strain_id": "STRAINX",
             "region": "region001", "products": "NRPS"}
    header = _header_block(facts, {"schema_version": schema, "sections": []})
    assert f"node: {FULL} |" in header
    assert f"/ {FULL} / region001 / BGC001" in header
    assert _card_identity_mismatch(header, _package(tmp_path), "STRAINX", "BGC001") is None


def test_missing_contig_falls_back_to_node():
    facts = {"bgc_id": "BGC001", "node": SHORT, "contig": "—", "strain_id": "STRAINX"}
    assert f"node: {SHORT} |" in _header_block(facts, {"schema_version": "modeb_full48_current", "sections": []})

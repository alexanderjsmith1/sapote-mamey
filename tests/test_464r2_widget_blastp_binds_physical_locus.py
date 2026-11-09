"""The widget admits a BLASTp row only when every physical claim it makes matches the locus.

Before this card the widget checked strain, BGC alias, gene label and length. A row naming a
different contig, node, region or protein hash was shown as PRESENT for the current locus.
Claims are read by `blastp_physical_binding.row_claims`, one shared reader: column names are
normalized against one alias table, and query text fields are parsed for key=value tokens,
the engine's pipe and space headers and bare NODE / region / r<n> / <n>aa tokens.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from mamey import widget_deliverable as w
from mamey.widget_deliverable import _gene_evidence_rows, _protein_hashes

GENES = [{"strain": "EXAMPLE", "bgc_id": "BGC001", "locus_tag": "ctg1_5", "aa_length": "300",
          "contig": "CTG_A.1", "region": "region001", "source_gbk": "CTG_A.region001.gbk"}]
INVENTORY = [{"BGC_ID": "BGC001", "Contig": "CTG_A.1", "Node_ID": "CTG_A.1", "Region": "1"}]
BASE = {"strain": "EXAMPLE", "bgc_id": "BGC001", "gene": "ctg1_5", "aa_length": "300",
        "hit_rank": "1", "subject_acc": "WP_000000001.1", "subject_def": "synthetic",
        "pct_identity": "90", "bitscore": "100"}


def _run(row, genes=GENES, hashes=None):
    rows, receipt = _gene_evidence_rows(
        strain="EXAMPLE", genes=genes, inventory=INVENTORY, mibig=[], clusterblast=[],
        blastp_batches={"nr": [([row], "blastp_nr/BGC001_top10.csv")]}, protein_hashes=hashes)
    return rows[0]["blastp_channel_status"]["nr"], receipt["channels"]["nr"]


def test_codex_probe_row_with_wrong_contig_region_and_hash_is_held():
    status, channel = _run({**BASE, "contig": "CTG_B.1", "region": "region002",
                            "protein_sha256": "f" * 64})
    assert status == "HOLD_NOT_ESTABLISHED_FOR_EXACT_CURRENT_LOCUS"
    assert channel["rows_admitted"] == 0
    assert channel["status"] == "HOLD_NO_EXACT_CURRENT_ROWS"
    assert channel["physical_binding_holds"] == {"BLASTP_CONTIG_MISMATCH": 1}
    assert channel["physical_binding_held_rows"][0]["source_row_number"] == 1


@pytest.mark.parametrize("extra,reason", [
    ({"full_node": "CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"Full_Node_ID": "CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"Node_ID": "CTG_B.1"}, "BLASTP_NODE_MISMATCH"),
    ({"query_node": "CTG_B.1"}, "BLASTP_NODE_MISMATCH"),
    ({"node_id": "NODE_7"}, "BLASTP_NODE_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5 contig=CTG_B.1 region=region002"}, "BLASTP_CONTIG_MISMATCH"),
    ({"query_id": "EXAMPLE|BGC001|ctg1_5|contig=CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5 region=region009"}, "BLASTP_REGION_MISMATCH"),
    ({"query_region": "region002"}, "BLASTP_REGION_MISMATCH"),
    ({"contig": "unknown"}, "BLASTP_PHYSICAL_CLAIM_UNVERIFIABLE"),
    ({"query_bgc": "BGC002"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_aa_length": "300 aa"}, "BLASTP_QUERY_ECHO_UNREADABLE"),
    ({"query_aa_length": "nan"}, "BLASTP_PHYSICAL_CLAIM_UNVERIFIABLE"),
    ({"protein_sha256": "b" * 64}, "BLASTP_PROTEIN_HASH_NOT_CHECKABLE"),
])
def test_every_conflicting_or_unreadable_claim_is_held(extra, reason):
    status, channel = _run({**BASE, **extra})
    assert status != "PRESENT"
    assert channel["physical_binding_holds"] == {reason: 1}


def test_hash_is_checked_against_the_package_protein():
    good = hashlib.sha256(b"MSRT").hexdigest()
    hashes = {("BGC001", "ctg1_5"): good}
    assert _run({**BASE, "protein_sha256": "a" * 64}, hashes=hashes)[1]["physical_binding_holds"] == {
        "BLASTP_PROTEIN_HASH_MISMATCH": 1}
    status, channel = _run({**BASE, "protein_sha256": good.upper()}, hashes=hashes)
    assert status == "PRESENT" and channel["rows_admitted_physically_bound"] == 1


def test_matching_claims_are_admitted_and_counted_as_bound():
    status, channel = _run({**BASE, "contig": "CTG_A.1", "Node_ID": "CTG_A.1", "region": "1",
                            "query_title": "EXAMPLE|BGC001|ctg1_5 contig=CTG_A.1 region=region001",
                            "query_strain": "example", "query_bgc": "BGC001",
                            "query_locus": "ctg1_5", "query_aa_length": "300"})
    assert status == "PRESENT"
    assert channel["rows_admitted_physically_bound"] == 1
    assert channel["rows_admitted_without_physical_columns"] == 0


def test_a_row_without_physical_columns_is_admitted_and_labelled():
    status, channel = _run(dict(BASE))
    assert status == "PRESENT"
    assert channel["rows_admitted_physically_bound"] == 0
    assert channel["rows_admitted_without_physical_columns"] == 1
    assert channel["physical_binding_holds"] == {}


def test_protein_hashes_follow_the_engine_normalization():
    text = ">ctg1_5 bgc=BGC001\nmsr t*\n>ctg1_6 bgc=BGC001\nMKV\n>dup bgc=BGC002\nMA\n>dup bgc=BGC002\nMB\n"
    hashes = _protein_hashes(text)
    assert hashes[("BGC001", "ctg1_5")] == hashlib.sha256(b"MSRT").hexdigest()
    assert ("BGC002", "dup") not in hashes


def _package(tmp_path, blastp_row):
    p = tmp_path / "package"
    (p / "blastp_nr").mkdir(parents=True)
    (p / "manifest.json").write_text(json.dumps({"strain_id": "EXAMPLE"}), encoding="utf-8")
    (p / "EXAMPLE_2_inventory.csv").write_text(
        "BGC_ID,Contig,Node_ID,Region\nBGC001,CTG_A.1,CTG_A.1,1\n", encoding="utf-8")
    (p / "EXAMPLE_gene_by_gene_all_bgcs.csv").write_text(
        "strain,bgc_id,locus_tag,aa_length,contig,region,source_gbk\n"
        "EXAMPLE,BGC001,ctg1_5,4,CTG_A.1,region001,CTG_A.region001.gbk\n", encoding="utf-8")
    (p / "EXAMPLE_proteins.faa").write_text(">ctg1_5 bgc=BGC001\nMSRT\n", encoding="utf-8")
    header = list(blastp_row)
    (p / "blastp_nr" / "BGC001_top10.csv").write_text(
        ",".join(header) + "\n" + ",".join(blastp_row[k] for k in header) + "\n", encoding="utf-8")
    return p


def _model_status(path):
    source = w.PackageSource(path)
    try:
        model = w._load_model(source)
    finally:
        source.close()
    gene = model["genes"][0]
    return gene["blastp_channel_status"]["nr"], model["gene_evidence_receipt"]["channels"]["nr"]


def test_end_to_end_a_node_conflict_in_the_package_is_held(tmp_path):
    row = {**BASE, "aa_length": "4", "Node_ID": "CTG_OTHER"}
    status, channel = _model_status(_package(tmp_path, row))
    assert status == "HOLD_NOT_ESTABLISHED_FOR_EXACT_CURRENT_LOCUS"
    assert channel["physical_binding_holds"] == {"BLASTP_NODE_MISMATCH": 1}


def test_end_to_end_the_package_protein_hash_binds(tmp_path):
    row = {**BASE, "aa_length": "4", "protein_sha256": hashlib.sha256(b"MSRT").hexdigest()}
    status, channel = _model_status(_package(tmp_path, row))
    assert status == "PRESENT"
    assert channel["rows_admitted_physically_bound"] == 1


# Round 2c: cases from the second attack review (planted on a real package there).
@pytest.mark.parametrize("extra,reason", [
    ({"query_title": "EXAMPLE|BGC001|slot=1|gene=ctg9_9|node=CTG_A.1|aa=999"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_title": "BGC009_ctg9_9 contig=CTG_A.1 node=CTG_A.1"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_id": "EXAMPLE|BGC001|ctg1_5|999aa"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_id": "EXAMPLE|BGC001|ctg9_9"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_title": "OTHER|BGC009|ctg9_9"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"locus_tag": "ctg9_9"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_gene": "ctg9_9"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"BGC_ID": "BGC009"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_bgc_id": "BGC009"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"qlen": "999"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_length": "999"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"strain_id": "OTHER"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5 [contig=CTG_B.1]"}, "BLASTP_CONTIG_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5;contig=CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5,contig=CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5 contig:CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5 contig = CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5 CONTIG=CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5 NODE_9"}, "BLASTP_NODE_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5 region009"}, "BLASTP_REGION_MISMATCH"),
    ({"query_title": "EXAMPLE BGC001 ctg1_5 Region009"}, "BLASTP_REGION_MISMATCH"),
    ({"query_title": "EXAMPLE BGC001 ctg1_5 node_9"}, "BLASTP_NODE_MISMATCH"),
    ({"query_title": "EXAMPLE BGC001 ctg1_5 r9"}, "BLASTP_REGION_MISMATCH"),
    ({"query_id": "NODE_9|BGC001|ctg1_5"}, "BLASTP_NODE_MISMATCH"),
    ({"query_id": "CTG_B.1|BGC001|ctg1_5"}, "BLASTP_IDENTITY_MISMATCH"),
    ({"query_title": "EXAMPLE|BGC001|ctg1_5 contig_name_unknown_form"}, "BLASTP_UNPARSED_LOCATION_TEXT"),
    ({"CONTIG": "CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"contig_id": "CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"record_id": "CTG_B.1"}, "BLASTP_CONTIG_MISMATCH"),
    ({"NODE": "NODE_9"}, "BLASTP_NODE_MISMATCH"),
    ({"REGION": "region009"}, "BLASTP_REGION_MISMATCH"),
    ({"region_number": "9"}, "BLASTP_REGION_MISMATCH"),
    ({"sha256": "f" * 64}, "BLASTP_PROTEIN_HASH_NOT_CHECKABLE"),
    ({"protein_hash": "f" * 64}, "BLASTP_PROTEIN_HASH_NOT_CHECKABLE"),
    ({"contig_strand_note": "x"}, "BLASTP_UNPARSED_LOCATION_TEXT"),
    ({"contig": "NA"}, "BLASTP_PHYSICAL_CLAIM_UNVERIFIABLE"),
    ({"contig": "CTG_A.2"}, "BLASTP_CONTIG_MISMATCH"),
])
def test_round_2c_conflicts_are_held(extra, reason):
    status, channel = _run({**BASE, **extra})
    assert status != "PRESENT", extra
    assert channel["physical_binding_holds"] == {reason: 1}, extra


@pytest.mark.parametrize("extra", [
    {"region": "r1"}, {"region": "Region001"}, {"contig": "CTG_A"}, {"contig": "ctg_a.1"},
    {"query_strain": "example"}, {"contig": ""}, {"length": "120"},
    {"query_title": "EXAMPLE BGC001 ctg1_5 region1"},
    {"query_title": "EXAMPLE|BGC001|slot=1|gene=ctg1_5|node=CTG_A.1|aa=300"},
    {"qseqid": "EXAMPLE|BGC001|ctg1_5|300aa", "qlen": "300"},
    {"query_title": "EXAMPLE|BGC001|ctg1_5 kind=biosynthetic start=10 end=900 strand=+"},
    {"subject_contig": "NZ_OTHER.1", "source_file_sha256": "a" * 64},
])
def test_correctly_bound_rows_are_not_over_held(extra):
    status, channel = _run({**BASE, **extra})
    assert status == "PRESENT", (extra, channel["physical_binding_holds"])


def test_spades_short_node_names_bind_only_their_own_contig():
    genes = [{**GENES[0], "contig": "NODE_12_length_51234_cov_8.9"}]
    inventory = [{"BGC_ID": "BGC001", "Contig": "NODE_12_length_51234_cov_8.9", "Node_ID": "NODE_12", "Region": "1"}]
    def run(extra):
        rows, receipt = _gene_evidence_rows(
            strain="EXAMPLE", genes=genes, inventory=inventory, mibig=[], clusterblast=[],
            blastp_batches={"nr": [([{**BASE, **extra}], "x.csv")]})
        return rows[0]["blastp_channel_status"]["nr"]
    assert run({"node": "NODE_12"}) == "PRESENT"
    assert run({"contig": "NODE_12"}) == "PRESENT"
    assert run({"node": "NODE_120"}) != "PRESENT"
    assert run({"node": "NODE_12_length_999_cov_1"}) != "PRESENT"


def test_gene_table_and_inventory_must_agree_before_any_claim():
    genes = [{**GENES[0], "region": "region002"}]
    rows, receipt = _gene_evidence_rows(
        strain="EXAMPLE", genes=genes, inventory=INVENTORY, mibig=[], clusterblast=[],
        blastp_batches={"nr": [([{**BASE, "region": "region002"}], "x.csv")]})
    assert rows[0]["blastp_channel_status"]["nr"] != "PRESENT"
    assert receipt["channels"]["nr"]["physical_binding_holds"] == {"BLASTP_LOCUS_TABLES_DISAGREE": 1}


def test_engine_shaped_online_overlay_rows_are_admitted():
    row = {"locus_tag": "ctg1_5", "aa_length": "300", "blastp_accession": "WP_1", "pct_identity": "90",
           "bitscore": "100", "channel": "nr", "query_strain": "EXAMPLE", "query_bgc": "BGC001",
           "query_locus": "ctg1_5", "query_aa_length": "300", "source_file_sha256": "a" * 64,
           "locus_rekey_state": "", "source_query_bgc": "BGC001"}
    rows, receipt = _gene_evidence_rows(
        strain="EXAMPLE", genes=GENES, inventory=INVENTORY, mibig=[], clusterblast=[],
        blastp_batches={"online": [([row], "blastp_online/BGC001_online_blastp.csv")]})
    assert rows[0]["blastp_channel_status"]["online"] == "PRESENT"
    bad = dict(row, query_bgc="BGC009")
    rows, receipt = _gene_evidence_rows(
        strain="EXAMPLE", genes=GENES, inventory=INVENTORY, mibig=[], clusterblast=[],
        blastp_batches={"online": [([bad], "x.csv")]})
    assert rows[0]["blastp_channel_status"]["online"] != "PRESENT"


def test_receipt_counts_bound_unbound_and_unparsed_rows():
    rows = [dict(BASE), {**BASE, "contig": "CTG_A.1"},
            {**BASE, "query_title": "EXAMPLE|BGC001|ctg1_5 regionX_part"}]
    _, receipt = _gene_evidence_rows(
        strain="EXAMPLE", genes=GENES, inventory=INVENTORY, mibig=[], clusterblast=[],
        blastp_batches={"nr": [(rows, "x.csv")]})
    ch = receipt["channels"]["nr"]
    assert ch["rows_admitted_physically_bound"] == 1
    assert ch["rows_admitted_without_physical_columns"] == 1
    assert ch["rows_with_unparsed_location_text"] == 1

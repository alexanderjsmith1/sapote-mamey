"""Independent channel admission: never promote other or unbound channels to nr."""
import csv
import json
import pytest
from mamey.genome_explore import scan_divergence, conservation_background
from mamey.authored_verify import _bgc_context_from_package

KEY = "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"
IDENTITY = "SYNTHETIC-001 / NODE_1_length_1000_cov_1 / region001 / BGC001"

def make_package(tmp_path, headers, rows):
    root = tmp_path / KEY
    root.mkdir()
    record = {"bgc_id": KEY, "bgc_alias": "BGC001", "strain": "SYNTHETIC-001",
              "contig": "NODE_1_length_1000_cov_1", "region_number": 1, "products": []}
    manifest = {"strain_id": "SYNTHETIC-001", "bgcs": [record],
                "source_scans": {"clusterblast_genes": {"per_gene_best_hit": {KEY: [{"pct_identity": 99}]}}}}
    (root / "manifest.json").write_text(json.dumps(manifest))
    (root / "blastp_online").mkdir()
    with (root / "blastp_online" / (KEY + "_online_blastp.csv")).open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return root

def assert_refused(root):
    row = scan_divergence(root)[0]
    assert row["median_id"] is None
    assert row["n_genes"] == 0
    assert row["source"] != "nr"
    assert row["source_status"] == "INVALID"
    assert conservation_background(root) == (None, 0)
    context = _bgc_context_from_package(str(root), KEY) or {}
    assert context.get("conservation_median_id") is None

@pytest.mark.parametrize("channel", ["clustered_nr", "swissprot", "ebi", "unknown", ""])
def test_other_or_unbound_channel_cannot_become_nr(tmp_path, channel):
    assert_refused(make_package(tmp_path, ["pct_identity", "channel", "source_channel"], [[65, channel, channel]]))

@pytest.mark.parametrize("first,second", [("nr", "swissprot"), ("clustered_nr", "nr")])
def test_conflicting_channel_fields_are_refused(tmp_path, first, second):
    assert_refused(make_package(tmp_path, ["pct_identity", "channel", "source_channel"], [[75, first, second]]))

def test_mixed_nr_curated_rows_do_not_become_a_pooled_nr_median(tmp_path):
    assert_refused(make_package(tmp_path, ["pct_identity", "channel", "source_channel"], [[97, "nr", "nr"], [20, "swissprot", "swissprot"]]))

@pytest.mark.parametrize("extra", ["channel", "blastp_organism"])
def test_duplicate_nonidentity_headers_are_refused(tmp_path, extra):
    assert_refused(make_package(tmp_path, ["pct_identity", "channel", "source_channel", extra, extra], [[75, "nr", "nr", "one", "two"]]))

def test_legacy_unbound_numeric_rows_require_admission(tmp_path):
    assert_refused(make_package(tmp_path, ["pct_identity"], [[75]]))

@pytest.mark.parametrize("value,tier", [(0, "DIVERGENT"), (75, "VARIABLE"), (100, "GENUS_CONSERVED")])
def test_explicit_nr_preserves_finite_boundaries(tmp_path, value, tier):
    root = make_package(tmp_path, ["pct_identity", "channel", "source_channel"], [[value, "nr", "nr"]])
    row = scan_divergence(root)[0]
    assert row["median_id"] == value and row["source"] == "nr"
    assert row["divergence_tier"] == tier
    assert conservation_background(root) == (value, 1)


def test_ordinary_nr_writer_declares_channel_and_preserves_foreign_merge(tmp_path):
    from mamey.blastp_ingest import write_nr_overlay
    root = make_package(tmp_path, ["pct_identity", "channel", "source_channel"], [])
    def fresh(gene):
        return {"BGC_ID": KEY, "query_locus": gene, "query_len": "100", "pct_identity": "75",
                "bitscore": "100", "subject_acc": "CONTROL_ACCESSION", "subject_desc": "synthetic control",
                "sciname": "Synthetic comparator", "hit_rank": 1}
    write_nr_overlay(root, [fresh("gene_1")])
    path = root / "blastp_online" / (KEY + "_online_blastp.csv")
    with path.open() as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames
        rows = list(reader)
    assert rows and all(row["channel"] == row["source_channel"] == "nr" for row in rows)
    assert scan_divergence(root)[0]["source"] == "nr"
    rows[0]["channel"] = rows[0]["source_channel"] = "swissprot"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    write_nr_overlay(root, [fresh("gene_2")])
    with path.open() as handle:
        merged = list(csv.DictReader(handle))
    assert {row["channel"] for row in merged} == {"nr", "swissprot"}
    assert_refused(root)

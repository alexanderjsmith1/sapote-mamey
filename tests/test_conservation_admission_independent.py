"""Independent conservation controls: valid data, invalid observations, actual source."""
import json
from pathlib import Path
import pytest
from mamey.genome_explore import scan_divergence, conservation_background
from mamey.authored_verify import _bgc_context_from_package

IDENTITY = "SYNTHETIC-001 / NODE_1_length_1000_cov_1 / region001 / BGC001"
KEY = "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"

def package(tmp_path, values, cb=(65,)):
    root=tmp_path/KEY; root.mkdir()
    record={"bgc_id":KEY,"bgc_alias":"BGC001","strain":"SYNTHETIC-001",
            "contig":"NODE_1_length_1000_cov_1","region_number":1,"products":[]}
    manifest={"strain_id":"SYNTHETIC-001","bgcs":[record],
              "source_scans":{"clusterblast_genes":{"per_gene_best_hit":{KEY:[{"pct_identity":v} for v in cb]}}}}
    (root/"manifest.json").write_text(json.dumps(manifest))
    if values is not None:
        overlay=root/"blastp_online"; overlay.mkdir()
        (overlay/(KEY+"_online_blastp.csv")).write_text(
            "pct_identity,blastp_organism,channel,source_channel\n"+"".join(str(v)+",synthetic control,nr,nr\n" for v in values))
    return root

@pytest.mark.parametrize("invalid", ["NaN", "inf", "-inf", "-1", "101", "not-a-number"])
def test_mixed_invalid_nr_cannot_become_a_subset_median_or_cb_fallback(tmp_path,invalid):
    root=package(tmp_path,[50,invalid],cb=(99,))
    row=scan_divergence(root)[0]
    assert row["median_id"] is None
    assert row["n_genes"]==0
    assert row["divergence_tier"] in {"NO_EVIDENCE","INVALID_EVIDENCE"}
    ctx=_bgc_context_from_package(str(root),KEY) or {}
    assert ctx.get("conservation_median_id") is None

@pytest.mark.parametrize("values", [[],["NO_HIT"],[""]])
def test_unavailable_nr_preserves_actual_clusterblast_source(tmp_path,values):
    row=scan_divergence(package(tmp_path,values))[0]
    assert row["median_id"]==65
    assert row["source"]=="clusterblast"
    assert row["divergence_tier"]=="UNCONFIRMED_CHECK_NR"

@pytest.mark.parametrize("value,tier", [(0,"DIVERGENT"),(75,"VARIABLE"),(100,"GENUS_CONSERVED")])
def test_finite_boundary_percentages_remain_observed_nr(tmp_path,value,tier):
    row=scan_divergence(package(tmp_path,[value,"NO_HIT"]))[0]
    assert row["median_id"]==value
    assert row["n_genes"]==1
    assert row["source"]=="nr"
    assert row["divergence_tier"]==tier

@pytest.mark.parametrize("invalid", ["NaN","inf","-1","101","not-a-number"])
def test_background_refuses_corrupt_observation(tmp_path,invalid):
    root=package(tmp_path,[95,invalid])
    assert conservation_background(root)==(None,0)


@pytest.mark.parametrize("payload", [
    "wrong_header\n75\n",
    "pct_identity,pct_identity\n75,95\n",
    "pct_identity,blastp_organism\n75,control,unexpected\n",
    'pct_identity,blastp_organism\n75,"unterminated\n',
])
def test_malformed_nr_csv_is_invalid_instead_of_admitted_or_unavailable(tmp_path,payload):
    root=package(tmp_path,[],cb=(99,))
    (root/"blastp_online"/(KEY+"_online_blastp.csv")).write_text(payload)
    row=scan_divergence(root)[0]
    assert row["median_id"] is None
    assert row.get("source_status")=="INVALID"
    assert row["divergence_tier"] in {"NO_EVIDENCE","INVALID_EVIDENCE"}

@pytest.mark.parametrize("payload", ["pct_identity,channel\n75,nr\n", 'pct_identity,blastp_organism,source_channel\n"75","synthetic, control",nr\n'])
def test_minimal_and_quoted_named_csv_remain_valid(tmp_path,payload):
    root=package(tmp_path,[],cb=(99,))
    (root/"blastp_online"/(KEY+"_online_blastp.csv")).write_text(payload)
    row=scan_divergence(root)[0]
    assert row["median_id"]==75 and row["source"]=="nr"

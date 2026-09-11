"""Native ClusterBlast optional metrics must not inherit CSV ragged-row rules."""
import json
import pytest
from mamey.clusterblast_genes import _parse_hit_rows
from mamey.genome_explore import scan_divergence

KEY = "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"
IDENTITY = "SYNTHETIC-001 / NODE_1_length_1000_cov_1 / region001 / BGC001"

@pytest.mark.parametrize("score,coverage", [("120", "NA"), ("NA", "80"), ("NA", "NA")])
def test_native_clusterblast_optional_null_metrics_preserve_identity(tmp_path, score, coverage):
    hit = _parse_hit_rows("Table of Blast hits\nquery_gene\tsubject_gene\t75\t" + score + "\t" + coverage + "\t1e-20\n")[0]
    assert hit.pct_identity == 75
    row = {"query_gene": hit.query_gene, "subject_gene": hit.subject_gene,
           "pct_identity": hit.pct_identity, "pct_coverage": hit.pct_coverage,
           "blast_score": hit.blast_score, "evalue": hit.evalue,
           "reference": "synthetic reference", "reference_source": "clusterblast", "reference_rank": 1}
    root = tmp_path / KEY
    root.mkdir()
    manifest = {"strain_id": "SYNTHETIC-001", "bgcs": [{"bgc_id": KEY, "bgc_alias": "BGC001",
                 "strain": "SYNTHETIC-001", "contig": "NODE_1_length_1000_cov_1", "region_number": 1}],
                "source_scans": {"clusterblast_genes": {"per_gene_best_hit": {KEY: [row]}}}}
    (root / "manifest.json").write_text(json.dumps(manifest))
    observation = scan_divergence(root)[0]
    assert observation["median_id"] == 75
    assert observation["source"] == "clusterblast"
    assert observation["source_status"] == "ADMITTED"
    assert observation["divergence_tier"] == "UNCONFIRMED_CHECK_NR"

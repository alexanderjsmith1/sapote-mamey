"""Empty retained channels do not establish that an upstream search ran."""
import csv
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("eb461", Path(__file__).resolve().parents[1] / "tools/evidence_bundle.py")
eb = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(eb)


def test_empty_channel_does_not_assert_search_completion(tmp_path):
    package = tmp_path / "public package"
    package.mkdir()
    # Identity copied from the shipped public region-only fixture; no hit values invented.
    with (package / "Micromonospora_humida_JAFEUC01_2_inventory.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["BGC_ID", "Contig", "antiSMASH_Region", "Strain"])
        writer.writerow(["BGC001", "JAFEUC010000001.1", "region002", "Micromonospora_humida_JAFEUC01"])
    (package / "Micromonospora_humida_JAFEUC01_4A2_ClusterBlast_per_gene.csv").write_text("bgc_id,query_gene,reference\n")
    bundle = eb.build_evidence_bundle(package)
    channel = bundle["bgcs"]["BGC001"]["channels"]["per_gene_clusterblast"]
    assert channel["deficit"] == "ABSENT_NO_ROWS"
    eb.write_evidence_bundle(bundle, tmp_path / "report")
    rendered = next((tmp_path / "report").glob("*.md")).read_text()
    assert "search completion is unverified" in rendered
    assert "SCANNED-BUT-EMPTY" not in " ".join(bundle["claim_safety"])

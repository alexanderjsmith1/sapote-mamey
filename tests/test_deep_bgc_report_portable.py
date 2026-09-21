import csv
import json
from pathlib import Path
import pytest
from mamey.deep_bgc_report import DeepBGCReportError, build_deep_report

IDENTITY = {"strain": "SYNTHETIC-001", "full_node_or_contig": "contig_demo_0001_complete", "region": "region001", "bgc_alias": "BGC007"}

def locus():
    return dict(IDENTITY, canonical_gene_count=2, boundary={"status": "OVERMERGED_SUSPECTED", "note": "Flanking genes require review."}, whole_region_matched_cds=2, whole_region_total_cds=4,
                comparator_components=[{"name":"component_A", "matched_cds":2, "local_total_cds":2, "core_completeness":"complete", "gene_order":"conserved"}],
                genes=[{"gene_id":"gene_001", "start":100, "end":500, "strand":"+", "role":"core", "product":"synthase", "domains":["PF00001"], "protein_sha256":"a"*64},
                       {"gene_id":"gene_002", "start":600, "end":900, "strand":"-", "role":"tailoring", "product":"oxidoreductase", "domains":[], "protein_sha256":"b"*64}])

def write_json(tmp_path, data):
    path = tmp_path / "locus.json"; path.write_text(json.dumps(data)); return path

def write_evidence(tmp_path, **changes):
    row = dict(IDENTITY, gene_id="gene_001", protein_sha256="a"*64, channel="MIBiG", result="class comparator")
    row.update(changes); path = tmp_path / "evidence.tsv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=row, delimiter="\t"); writer.writeheader(); writer.writerow(row)
    return path

def test_builds_report_roster_map_and_receipt(tmp_path):
    receipt = build_deep_report(write_json(tmp_path, locus()), tmp_path / "out", write_evidence(tmp_path))
    assert receipt["exact_locus"] == "SYNTHETIC-001 / contig_demo_0001_complete / region001 / BGC007"
    assert set(p.name for p in (tmp_path / "out").iterdir()) == {"DEEP_BGC_REPORT.md", "GENE_ROSTER.tsv", "LOCUS_MAP.svg", "REPORT_RECEIPT.json"}
    text = (tmp_path / "out/DEEP_BGC_REPORT.md").read_text()
    assert "2/4 (50.0%)" in text and "component_A" in text and "not an isolated match" in text

@pytest.mark.parametrize("change", [
    {"region":"region002"}, {"bgc_alias":"BGC999"}, {"full_node_or_contig":"contig_other_complete"},
    {"gene_id":"gene_outside"}, {"protein_sha256":"c"*64},
])
def test_refuses_identity_and_gene_slice_mismatch(tmp_path, change):
    with pytest.raises(DeepBGCReportError):
        build_deep_report(write_json(tmp_path, locus()), tmp_path / "out", write_evidence(tmp_path, **change))
    assert not (tmp_path / "out").exists()

def test_refuses_declared_gene_count_mismatch_before_output(tmp_path):
    data = locus(); data["canonical_gene_count"] = 3
    with pytest.raises(DeepBGCReportError, match="gene-slice mismatch"):
        build_deep_report(write_json(tmp_path, data), tmp_path / "out")
    assert not (tmp_path / "out").exists()

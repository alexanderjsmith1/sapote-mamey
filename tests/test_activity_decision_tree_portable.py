import csv, json
import pytest
from mamey.activity_decision_tree import ActivityDecisionTreeError, build_activity_decision_trees

IDENTITY={"strain":"SYNTHETIC-001","full_node_or_contig":"contig_demo_0001_complete","region":"region001","bgc_alias":"BGC007"}

def setup(tmp_path, receipt_identity=None, **changes):
    root=tmp_path/"reports"; (root/"one").mkdir(parents=True)
    (root/"one/REPORT_RECEIPT.json").write_text(json.dumps({"identity":receipt_identity or IDENTITY}))
    row=dict(IDENTITY, report_receipt="one/REPORT_RECEIPT.json", hypothesis="pigment-family chemistry", target_genes="gene_001", claim_ceiling="Class-level hypothesis only")
    row.update(changes); leads=tmp_path/"leads.tsv"
    with leads.open("w", newline="") as handle:
        writer=csv.DictWriter(handle, fieldnames=row, delimiter="\t"); writer.writeheader(); writer.writerow(row)
    return leads,root

def test_builds_five_gate_tree(tmp_path):
    leads,root=setup(tmp_path); build_activity_decision_trees(leads,root,tmp_path/"out")
    text=(tmp_path/"out/ACTIVITY_DECISION_TREES.md").read_text()
    assert "Expression gate" in text and "Genetic linkage gate" in text and "Claim gate" in text

@pytest.mark.parametrize("change", [{"bgc_alias":"BGC008"},{"region":"region002"},{"claim_ceiling":""},{"report_receipt":"../escape.json"}])
def test_refuses_mismatch_missing_ceiling_and_path_escape(tmp_path, change):
    leads,root=setup(tmp_path, **change)
    with pytest.raises(ActivityDecisionTreeError): build_activity_decision_trees(leads,root,tmp_path/"out")
    assert not (tmp_path/"out").exists()

def test_refuses_receipt_identity_mismatch(tmp_path):
    leads,root=setup(tmp_path, receipt_identity=dict(IDENTITY, region="region009"))
    with pytest.raises(ActivityDecisionTreeError, match="identity mismatch"):
        build_activity_decision_trees(leads,root,tmp_path/"out")

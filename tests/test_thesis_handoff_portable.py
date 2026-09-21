import csv,json,zipfile
import pytest
from mamey.thesis_handoff import ThesisHandoffError,build_thesis_handoff

ID={"strain":"SYNTHETIC-001","full_node_or_contig":"contig_demo_0001_complete","region":"region001","bgc_alias":"BGC007"}

def setup(tmp_path,receipt_identity=None,**changes):
    root=tmp_path/"inputs";root.mkdir();(root/"report.md").write_text("# report\n");(root/"map.svg").write_text("<svg/>\n")
    (root/"receipt.json").write_text(json.dumps({"identity":receipt_identity or ID}))
    row=dict(ID,report_receipt="receipt.json",report_markdown="report.md",locus_map="map.svg",activity_tree="",gaps="expression; metabolomics",claim_ceiling="Class-level hypothesis only");row.update(changes)
    index=tmp_path/"index.tsv"
    with index.open("w",newline="") as h:w=csv.DictWriter(h,fieldnames=row,delimiter="\t");w.writeheader();w.writerow(row)
    return index,root

def test_builds_portable_crc_checked_handoff(tmp_path):
    index,root=setup(tmp_path);receipt=build_thesis_handoff(index,root,tmp_path/"out")
    assert receipt["zip_crc"]=="PASS"
    with zipfile.ZipFile(tmp_path/"out/THESIS_HANDOFF.zip") as zf:
        assert zf.testzip() is None and "INDEX.md" in zf.namelist()
    text=(tmp_path/"out/INDEX.md").read_text(); assert str(tmp_path) not in text and "SYNTHETIC-001 / contig_demo_0001_complete / region001 / BGC007" in text

@pytest.mark.parametrize("change",[{"report_markdown":"../escape.md"},{"gaps":""},{"claim_ceiling":""},{"bgc_alias":"BGC008"}])
def test_refuses_escape_missing_governance_and_identity_mismatch(tmp_path,change):
    index,root=setup(tmp_path,**change)
    with pytest.raises(ThesisHandoffError):build_thesis_handoff(index,root,tmp_path/"out")
    assert not (tmp_path/"out").exists()

def test_refuses_receipt_identity_mismatch(tmp_path):
    index,root=setup(tmp_path,receipt_identity=dict(ID,region="region009"))
    with pytest.raises(ThesisHandoffError,match="identity mismatch"):build_thesis_handoff(index,root,tmp_path/"out")

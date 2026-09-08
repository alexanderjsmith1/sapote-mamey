"""Every evidence CSV source row must survive typed determinism comparison."""
import csv
import json
import pytest
from tools.determinism_fingerprint import fingerprint_pair, compare_reports, report_ok

IDENTITY="SYNTHETIC-001 / CP123456.1 / region001 / BGC001"
KEY="SYNTHETIC-001__CP123456.1__region001__BGC001"

def package(root,first="1",filename="synthetic_gene_evidence.csv",identical=False):
    root.mkdir(parents=True)
    (root/"manifest.json").write_text(json.dumps({"strain_id":"SYNTHETIC-001"}))
    fields=["strain","bgc_id","contig","region","query_gene","Score"]
    rows=[dict(zip(fields,["SYNTHETIC-001","BGC001","CP123456.1","region001","gene_a",first])),
          dict(zip(fields,["SYNTHETIC-001","BGC001","CP123456.1","region001","gene_b","2"]))]
    if identical:rows[1]=dict(rows[0])
    with (root/filename).open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return root

def report(result):
    return {"inventory_coverage":{"complete":True},"inputs":{"case":{**result,"status":"PASS" if result["non_timestamp_byte_parity"] else "FAIL_PARITY"}}}

def test_multiple_rows_for_one_locus_survive_without_identity_hold(tmp_path):
    left=package(tmp_path/KEY/"left");right=package(tmp_path/KEY/"right")
    result=fingerprint_pair("case",left,right)
    assert len(result["canonical_csv_cells"])==2
    assert not result["identity_holds"] and report_ok(report(result))

def test_identical_repeated_rows_are_preserved_as_distinct_source_records(tmp_path):
    left=package(tmp_path/KEY/"left",identical=True);right=package(tmp_path/KEY/"right",identical=True)
    result=fingerprint_pair("case",left,right)
    assert len(result["canonical_csv_cells"])==2
    assert not result["identity_holds"]

def test_earlier_row_change_retains_complete_identity_and_source_row(tmp_path):
    left=package(tmp_path/KEY/"left");right=package(tmp_path/KEY/"right",first="9")
    result=fingerprint_pair("case",left,right)
    assert result["typed_bgc_cell_differences"]==[{"file":"synthetic_gene_evidence.csv","identity":IDENTITY,"source_row":2,"column":"Score","left":"1","right":"9"}]

def test_cross_report_comparison_keeps_earlier_row_change(tmp_path):
    left=package(tmp_path/KEY/"left");right=package(tmp_path/KEY/"right",first="9")
    old=report(fingerprint_pair("case",left,left));new=report(fingerprint_pair("case",right,right))
    result=compare_reports(new,old)
    assert not result["match"]
    assert any(r.get("identity")==IDENTITY and r.get("source_row")==2 and r.get("column")=="Score" and r.get("baseline")=="1" and r.get("current")=="9" for r in result["changes"])

def test_filename_separator_does_not_corrupt_emitted_identity(tmp_path):
    filename="synthetic|gene_evidence.csv"
    left=package(tmp_path/KEY/"left",filename=filename);right=package(tmp_path/KEY/"right",first="9",filename=filename)
    result=fingerprint_pair("case",left,right)
    assert result["typed_bgc_cell_differences"]==[{"file":filename,"identity":IDENTITY,"source_row":2,"column":"Score","left":"1","right":"9"}]

@pytest.mark.parametrize("damage",["duplicate_header","short_row","long_row","missing_alias"])
def test_identity_bearing_multirow_tables_cannot_hide_malformed_records(tmp_path,damage):
    left=package(tmp_path/KEY/"left");right=package(tmp_path/KEY/"right")
    for pkg in (left,right):
        path=pkg/"synthetic_gene_evidence.csv"
        with path.open(newline="") as handle:records=list(csv.reader(handle))
        if damage=="duplicate_header":
            records[0].append("Score")
            for record in records[1:]:record.append("hidden")
        elif damage=="short_row":records[1].pop()
        elif damage=="long_row":records[1].append("extra")
        else:records[1][1]=""
        with path.open("w",newline="") as handle:csv.writer(handle).writerows(records)
    result=fingerprint_pair("case",left,right)
    assert result["identity_holds"]
    assert not report_ok(report(result))

def test_report_schema_change_requires_explicit_baseline_rebinding(tmp_path):
    left=package(tmp_path/KEY/"left")
    pair=fingerprint_pair("case",left,left)
    current={**report(pair),"schema_version":"mamey_determinism_fingerprint_v3"}
    baseline={**report(pair),"schema_version":"mamey_determinism_fingerprint_v2"}
    comparison=compare_reports(current,baseline)
    assert not comparison["match"]
    assert any(change.get("column")=="schema_version" for change in comparison["changes"])

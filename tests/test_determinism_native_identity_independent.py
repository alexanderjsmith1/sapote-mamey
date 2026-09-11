"""Independent native CSV determinism coverage and incomplete-report controls."""
import csv
import json
import pytest
from mamey.crosswalk import infer_node_id
from tools.determinism_fingerprint import fingerprint_pair, report_ok

STRAIN="SYNTHETIC-001"
CONTIG="NODE_1_length_1000_cov_1.5"

def row(contig=CONTIG, alias="BGC001", score="1"):
    return {"BGC_ID":alias,"Contig":contig,"Node_ID":infer_node_id(contig,""),"antiSMASH_Region":"region001","Score":score}

def package(root, rows):
    root.mkdir(parents=True)
    (root/"manifest.json").write_text(json.dumps({"strain_id":STRAIN}))
    for filename in ("synthetic_2_inventory.csv","synthetic_4_triage_board.csv"):
        with (root/filename).open("w",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=list(row()));writer.writeheader();writer.writerows(rows)
    return root

def pair(tmp_path, left, right, *, fixture_contig=CONTIG):
    root=tmp_path/f"SYNTHETIC-001__{fixture_contig}__region001__BGC001"
    return fingerprint_pair("synthetic",package(root/"left",left),package(root/"right",right))

def report(result):
    return {"inventory_coverage":{"complete":True},"inputs":{"synthetic":{**result,"status":"PASS" if result["non_timestamp_byte_parity"] else "FAIL_PARITY"}}}

@pytest.mark.parametrize("contig",[CONTIG,"ctg10_extra_suffix","scaffold_42_segment_A","CP123456.1"])
def test_native_rows_retained_with_full_contig_identity(tmp_path,contig):
    result=pair(tmp_path,[row(contig)],[row(contig)],fixture_contig=contig)
    identity=f"{STRAIN} / {contig} / region001 / BGC001"
    assert not result["identity_holds"]
    assert len(result["canonical_csv_cells"])==2
    assert all(key.endswith("|"+identity) for key in result["canonical_csv_cells"])
    assert report_ok(report(result))

def test_native_changed_score_has_typed_full_identity_difference(tmp_path):
    result=pair(tmp_path,[row(score="1")],[row(score="2")])
    assert len(result["typed_bgc_cell_differences"])==2
    assert all(change["column"]=="Score" and change["identity"]==f"{STRAIN} / {CONTIG} / region001 / BGC001" for change in result["typed_bgc_cell_differences"])
    assert not report_ok(report(result))

def test_real_identity_conflict_cannot_pass_even_with_identical_bytes(tmp_path):
    damaged=row();damaged["Node_ID"]="NODE_9_length_1000_cov_1"
    result=pair(tmp_path,[damaged],[damaged])
    assert result["non_timestamp_byte_parity"]
    assert result["identity_holds"]
    assert not report_ok(report(result))

def test_normalized_collision_keeps_both_physical_rows(tmp_path):
    rows=[row(),row("NODE_1_length_1000_cov_1.9","BGC002")]
    assert rows[0]["Node_ID"]==rows[1]["Node_ID"]
    result=pair(tmp_path,rows,rows)
    assert not result["identity_holds"] and len(result["canonical_csv_cells"])==4

def test_duplicate_csv_identity_is_a_hold_not_silent_overwrite(tmp_path):
    rows=[row("CP123456.1",score="1"),row("CP123456.1",score="2")]
    result=pair(tmp_path,rows,rows,fixture_contig="CP123456.1")
    assert result["identity_holds"]
    assert not report_ok(report(result))

@pytest.mark.parametrize("csv_text",[
    "BGC_ID,Contig,Node_ID,antiSMASH_Region,Score,Score\nBGC001,CP123456.1,CP123456.1,region001,1,2\n",
    "BGC_ID,Contig,Node_ID,antiSMASH_Region,Score\nBGC001,CP123456.1,CP123456.1,region001\n",
    "BGC_ID,Contig,Node_ID,antiSMASH_Region,Score\nBGC001,CP123456.1,CP123456.1,region001,1,extra\n",
])
def test_malformed_inventory_cannot_claim_complete_typed_coverage(tmp_path,csv_text):
    root=tmp_path/"SYNTHETIC-001__CP123456.1__region001__BGC001"
    left=package(root/"left",[row("CP123456.1")]);right=package(root/"right",[row("CP123456.1")])
    for pkg in (left,right):(pkg/"synthetic_2_inventory.csv").write_text(csv_text)
    result=fingerprint_pair("synthetic",left,right)
    assert result["identity_holds"]
    assert not report_ok(report(result))

def test_repeated_alias_across_three_full_contigs_never_resurrects_rows(tmp_path):
    rows=[row(f"NODE_1_length_1000_cov_1.{n}") for n in (5,6,7)]
    result=pair(tmp_path,rows,rows)
    assert result["canonical_csv_cells"]=={}
    assert not report_ok(report(result))

def test_actual_package_case_status_reflects_identity_hold(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import tools.determinism_fingerprint as determinism
    case_root=tmp_path/"SYNTHETIC-001__NODE_1_length_1000_cov_1.5__region001__BGC001"
    case_root.mkdir();(case_root/"synthetic.zip").write_bytes(b"synthetic source fixture")
    monkeypatch.setattr(determinism,"ROOT",case_root)
    def fake_run(command,cwd,env):
        out=Path(command[command.index("--outdir")+1])
        damaged=row();damaged["Node_ID"]="NODE_9_length_1000_cov_1"
        package(out/STRAIN/"package",[damaged])
        return SimpleNamespace(returncode=0,stdout="",stderr="")
    from pathlib import Path
    monkeypatch.setattr(determinism,"_run",fake_run)
    case={"id":"synthetic_case","strain":STRAIN,"input":"synthetic.zip","mode":"gold","flags":[]}
    result=determinism._run_package_case(case,case_root/"runs",{})
    assert result["identity_holds"]
    assert result["status"]!="PASS"


def test_package_pair_cli_status_reflects_identity_hold(tmp_path):
    from tools.determinism_fingerprint import main
    root=tmp_path/"SYNTHETIC-001__NODE_1_length_1000_cov_1.5__region001__BGC001"
    damaged=row();damaged["Node_ID"]="NODE_9_length_1000_cov_1"
    left=package(root/"left",[damaged]);right=package(root/"right",[damaged])
    output=root/"report.json"
    assert main(["--package-pair","synthetic_case",str(left),str(right),"--out",str(output)])==1
    result=json.loads(output.read_text())["inputs"]["synthetic_case"]
    assert result["identity_holds"]
    assert result["status"]=="HOLD_IDENTITY"


def test_failed_package_preserves_both_streams_and_full_logs(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import hashlib
    import tools.determinism_fingerprint as determinism
    stdout="progress\n"*300+"ACTUAL_INPUT_REFUSAL: conflicting fixture records\n"
    stderr="SCHEMA_WARNING: unknown version; results still permitted\n"
    monkeypatch.setattr(determinism,"_run",lambda *args: SimpleNamespace(returncode=1,stdout=stdout,stderr=stderr))
    case={"id":"synthetic_case","strain":STRAIN,"input":"synthetic.zip","mode":"gold","flags":[]}
    root=tmp_path/"SYNTHETIC-001__NODE_1_length_1000_cov_1.5__region001__BGC001"
    result=determinism._run_package_case(case,root,{})
    assert result["status"]=="RUN_FAILED"
    assert "ACTUAL_INPUT_REFUSAL" in result["error"]
    assert "SCHEMA_WARNING" in result["error"]
    run=result["runs"][0]
    for stream,value in [("stdout",stdout),("stderr",stderr)]:
        assert run[stream+"_tail"]==value[-1000:]
        log=root/run[stream+"_log"]
        assert log.read_bytes()==value.encode("utf-8")
        assert hashlib.sha256(log.read_bytes()).hexdigest()==run[stream+"_sha256"]
    assert not (root/case["id"]/"B.stdout.log").exists()


@pytest.mark.parametrize("duplicate",[False,True])
def test_actual_crosswalk_producer_uses_typed_native_identity(tmp_path,duplicate):
    from mamey.models import BGCRecord
    from tools.determinism_fingerprint import _csv_cells
    bgc=BGCRecord(bgc_id="BGC001",contig=CONTIG,region_number=1,start=1,end=100,contig_length=1000,node_id=infer_node_id(CONTIG,""),antismash_region="region001")
    data=bgc.crosswalk_dict();data["strain"]=STRAIN
    root=tmp_path/f"{STRAIN}__{CONTIG}__region001__BGC001";root.mkdir()
    (root/"manifest.json").write_text(json.dumps({"strain_id":STRAIN}))
    with (root/"synthetic_2b_bgc_crosswalk.csv").open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(data));writer.writeheader();writer.writerows([data]*(2 if duplicate else 1))
    cells,holds=_csv_cells(root)
    if duplicate:assert not cells and holds
    else:
        assert not holds and len(cells)==1
        assert next(iter(cells)).endswith(f"{STRAIN} / {CONTIG} / region001 / BGC001")

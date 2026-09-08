"""HitTable rejection must precede workbook/package publication."""
from pathlib import Path
import hashlib
import subprocess
import sys
import pytest
from mamey import blastp_ingest as bi

VALID = "query001,subject001,90,20,0,0,1,20,1,20,1e-20,100"

@pytest.mark.parametrize("payload", [
    b"unstructured prose\n",
    b"query001,subject001,90\n",
    (VALID+",100,extra\n").encode(),
    (VALID+'\n"unterminated').encode(),
    (VALID+"\n").encode()+b"\xff",
    b"<html>request failed</html>\n",
    (VALID+"\n<html>request failed</html>\n").encode(),
    (","+VALID.split(",",1)[1]+"\n").encode(),
    VALID.replace("subject001", "").encode(),
])
def test_malformed_table_is_rejected_as_whole(tmp_path, payload):
    hits=tmp_path/"hits.csv"
    hits.write_bytes(payload)
    with pytest.raises(ValueError, match="BLASTP_HIT_TABLE_INVALID"):
        bi.parse_hit_table(hits)

@pytest.mark.parametrize("payload,count", [
    (b"",0), (b"# BLASTP\n# 0 hits found\n\n",0),
    ((VALID+"\n").encode(),1), ((VALID+",95\r\n").encode(),1),
    (("\ufeff"+VALID+"\n").encode(),1),
    ((VALID.replace("query001", '"query,001"')+"\n").encode(),1),
])
def test_supported_tables_remain_admitted(tmp_path,payload,count):
    hits=tmp_path/"hits.csv"; hits.write_bytes(payload)
    rows=bi.parse_hit_table(hits)
    assert len(rows)==count
    if rows:
        assert rows[0]["subject_acc"]=="subject001"
        assert rows[0]["bitscore"]=="100"
        if len(payload.split(b","))==12:
            assert rows[0]["positives_pct"]==""

def test_reader_does_not_use_unbounded_read_text(tmp_path,monkeypatch):
    hits=tmp_path/"hits.csv"; hits.write_text(VALID+"\n")
    def forbidden(*args,**kwargs):
        raise AssertionError("whole-file preflight is forbidden")
    monkeypatch.setattr(Path,"read_text",forbidden)
    assert len(bi.parse_hit_table(hits))==1

def test_cli_invalid_table_preserves_all_outputs(tmp_path):
    import openpyxl
    master=tmp_path/"master.xlsx"
    wb=openpyxl.Workbook(); wb.active["A1"]="sentinel"; wb.save(master)
    package=tmp_path/"package"; package.mkdir()
    (package/"sentinel.txt").write_text("unchanged")
    hits=tmp_path/"hits.csv"; hits.write_text(VALID+"\nshort,row\n")
    def inventory():
        return {str(p.relative_to(tmp_path)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in tmp_path.rglob("*") if p.is_file()}
    before=inventory()
    root=Path(__file__).resolve().parents[1]
    proc=subprocess.run([sys.executable,str(root/"mamey_run.py"),"ingest-blastp",
        "--master",str(master),"--strain","TEST-01","--hit-table",str(hits),
        "--package",str(package)],cwd=root,capture_output=True,text=True,timeout=120)
    assert proc.returncode!=0
    assert "BLASTP_HIT_TABLE_INVALID" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert inventory()==before

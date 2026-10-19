"""Static unexecuted library and public front-door controls using a tiny property-only SDF."""
import json
from pathlib import Path
import pytest
from mamey import npatlas_provision as tool, packaging
from tools import npatlas_provision as front

def _source(tmp_path):
    p=tmp_path/"source.sdf"; p.write_text(">  <name>\nsynthetic record\n\n$$$$\n")
    return p

@pytest.mark.parametrize("kind", ["file", "symlink"])
def test_front_door_preserves_foreign_predictable_temp(tmp_path, kind):
    source=_source(tmp_path); out=tmp_path/"out.json"; fixed=tmp_path/"out.json.tmp"
    protected=tmp_path/"protected"; protected.write_text("foreign source evidence")
    if kind=="file": fixed.write_text("foreign staging bytes")
    else: fixed.symlink_to(protected)
    before=fixed.read_bytes(); original_source=source.read_bytes()
    assert front.main(["provision","--source",str(source),"--out",str(out)])==0
    assert fixed.read_bytes()==before and source.read_bytes()==original_source
    assert protected.read_text()=="foreign source evidence"
    assert json.loads(out.read_text())["compounds"][0]["name"]=="synthetic record"

def test_replace_failure_retains_old_output_and_foreign_temporary(tmp_path, monkeypatch):
    source=_source(tmp_path);out=tmp_path/"out.json";out.write_text("prior output")
    fixed=tmp_path/"out.json.tmp";fixed.write_text("foreign staging bytes")
    def failed(*a,**k):raise OSError("synthetic publication failure")
    monkeypatch.setattr(packaging.os,"replace",failed)
    with pytest.raises(OSError):tool.provision(str(source),str(out),[])
    assert out.read_text()=="prior output"
    assert fixed.read_text()=="foreign staging bytes"

def test_fresh_subset_receipt_binds_published_bytes(tmp_path):
    source=_source(tmp_path);out=tmp_path/"out.json"
    receipt=tool.provision(str(source),str(out),[])
    assert receipt.included_count==1 and receipt.excluded_count==0
    assert receipt.output_sha256==tool.sha256_file(str(out))

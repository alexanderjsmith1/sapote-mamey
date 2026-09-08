"""Generic adverse fixtures for workflow and BiG-SCAPE admission."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
import pytest
from mamey import sapote_workflow as wf
ROOT = Path(__file__).resolve().parents[1]

def tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def package(tmp_path):
    pkg = tmp_path / "package"; pkg.mkdir()
    (pkg / "judgment").mkdir(); (pkg / "mode_b_templates").mkdir()
    identity = {"strain": "SYN-A", "contig": "NODE_1_length_10000_cov_20", "region": "region001", "bgc_id": "BGC001"}
    (pkg / "manifest.json").write_text(json.dumps({"strain": "SYN-A", "bgcs": [identity]}))
    (pkg / "gate_validation.json").write_text(json.dumps({"status":"MAMEY_COMPLETE"}))
    (pkg / "checksums_sha256.txt").write_text("fixture marker")
    for suffix in ("4_triage_board", "4c_AB_lead_board", "4c_AF_lead_board"):
        (pkg / ("SYN-A_" + suffix + ".csv")).write_text("BGC_ID\nBGC001\n")
    filename = "SYN-A_NODE_1_length_10000_cov_20_region001_BGC001_mode_b.md"
    (pkg / "mode_b_templates" / filename).write_text("## §1 Template")
    (pkg / "judgment" / filename).write_text("".join(f"## §{i} Section {i}\n" + "generic evidence text " * 9 + "\n" for i in range(1,5)))
    return pkg

def test_cli_adapter_forwards_strict(tmp_path, monkeypatch, capsys):
    pkg = package(tmp_path)
    calls=[]
    monkeypatch.setattr(wf, "_run_verify_modeb", lambda p,c: calls.append(c) or 1, raising=False)
    wf.workflow_command(SimpleNamespace(package=str(pkg), strict=True, as_json=True))
    output=json.loads(capsys.readouterr().out)
    assert calls, "CLI strict adapter must invoke verifier"
    assert output["steps"]["W4"]["status"] == wf.PENDING

@pytest.mark.parametrize("stub", [False,True])
def test_strict_does_not_credit_stale_register(tmp_path, stub):
    pkg=package(tmp_path)
    card=next((pkg / "judgment").glob("*.md"))
    if stub: card.write_text("stale stub")
    else: card.unlink()
    (pkg / "judgment_register.json").write_text(json.dumps({"bgcs":{"BGC001":{"status":"COMPLETE"}}}))
    assert wf.s4_modeb(str(pkg),None,{"strict":True})[0] == wf.PENDING

def test_malformed_register_list_fails_closed(tmp_path):
    pkg=package(tmp_path)
    (pkg / "judgment_register.json").write_text(json.dumps({"bgcs":[None]}))
    assert wf.s4_modeb(str(pkg),None,{"strict":True})[0] == wf.PENDING

@pytest.mark.parametrize("payload", ["{broken", '{"hard_excluded":null}', '{"hard_excluded":"SYN-A"}', '[]'])
def test_malformed_exclusions_refused(tmp_path,monkeypatch,payload):
    official=tmp_path / "official"; official.mkdir(); (official / "exclusions.json").write_text(payload)
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA",str(official))
    with pytest.raises((ValueError,RuntimeError)):
        tool("bigscape_prep")._hard_excluded()

def test_existing_staging_output_is_not_recertified(tmp_path,monkeypatch):
    official=tmp_path / "official"; official.mkdir(); (official / "exclusions.json").write_text('{"hard_excluded":["SYN-A"]}')
    out=tmp_path / "out"; out.mkdir(); stale=out / "SYN-A_NODE_1_length_10000_cov_20_region001_BGC001.gbk"; stale.write_text("stale")
    inputs=tmp_path / "inputs"; inputs.mkdir()
    env=dict(os.environ,MAMEY_OFFICIAL_DATA=str(official),PYTHONDONTWRITEBYTECODE="1")
    result=subprocess.run([sys.executable,str(ROOT / "tools/bigscape_prep.py"),"--inputs",str(inputs),"--out",str(out),"--allow-mixed"],capture_output=True,text=True,env=env)
    assert result.returncode == 2 and "non-empty" in result.stderr
    assert not (out / "STRICTNESS_MANIFEST.tsv").exists()
    assert stale.read_text()=="stale"

def database(tmp_path,names):
    db=tmp_path / "tiny.sqlite"
    with sqlite3.connect(db) as c:
        c.executescript("CREATE TABLE family(id TEXT,cutoff TEXT,bin_label TEXT,run_id INTEGER); CREATE TABLE gbk(id INTEGER,path TEXT); CREATE TABLE bgc_record(id INTEGER,gbk_id INTEGER,product TEXT,category TEXT); CREATE TABLE bgc_record_family(record_id INTEGER,family_id TEXT); INSERT INTO family VALUES('f','0.3','NRPS',1);")
        for i,name in enumerate(names,1):
            c.execute("INSERT INTO gbk VALUES(?,?)",(i,name)); c.execute("INSERT INTO bgc_record VALUES(?,?,?,?)",(i,i,"NRPS","NRPS")); c.execute("INSERT INTO bgc_record_family VALUES(?,'f')",(i,))
    return db

@pytest.mark.parametrize("consumer",["bigscape_known_novel","bigscape_cross_strain"])
def test_generic_strain_multiple_contigs_not_cross_strain(tmp_path,consumer):
    db=database(tmp_path,["SYN-A_NODE_1_length_10000_cov_20.region001.gbk","SYN-A_NODE_2_length_11000_cov_21.region001.gbk"])
    assert tool(consumer).build_rows(db,1,min_strains=2)==[]

"""Receipt-only synthetic files; no figures or detector data."""
import argparse
import hashlib
import json
from tools.hplc_trace_panels import _receipt


def test_nested_run_tables_keep_distinct_receipt_paths(tmp_path):
    outputs=[]
    for strain in ('synthetic_A','synthetic_B'):
        p=tmp_path/strain/'runs.tsv';p.parent.mkdir();p.write_text(strain+'\n');outputs.append(p)
    args=argparse.Namespace(cmd='pages',max_native_points=6002,bins=3000)
    _receipt(tmp_path,args,[],outputs,{})
    rec=json.loads((tmp_path/'receipt.json').read_text())
    assert rec['outputs']=={p.relative_to(tmp_path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs}


def test_flat_panel_receipt_keys_remain_unchanged(tmp_path):
    p=tmp_path/'panel.tsv';p.write_text('synthetic\n')
    _receipt(tmp_path,argparse.Namespace(cmd='panels',max_native_points=6002,bins=3000),[],[p],{})
    assert set(json.loads((tmp_path/'receipt.json').read_text())['outputs'])=={'panel.tsv'}

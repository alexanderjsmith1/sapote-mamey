"""Explicit tree audit evidence; no path guesses, timestamps or scientific verdicts."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pytest

pytest.importorskip('Bio')
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tree_trust_workflow',ROOT/'tools/tree_trust_audit.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def bound(tmp_path):
    tree=tmp_path/'tree.nwk';tree.write_text("(('A tip':1,B:1):1,Reference:1);")
    meta=tmp_path/'metadata.tsv';meta.write_text('tip\tlabel\nA tip\tSpecies alpha\nB\tSpecies beta\nReference\tSpecies gamma\n')
    render=tmp_path/'render.png';render.write_bytes(b'bound render bytes')
    receipt=tmp_path/'render.json';receipt.write_text(json.dumps({'tree_sha256':sha(tree),'metadata_sha256':sha(meta),'render_sha256':sha(render)}))
    gate=tmp_path/'gate.py';gate.write_text('import sys\nsys.exit(0)\n')
    entry={'tree':tree.name,'metadata':meta.name,'render':render.name,'render_receipt':receipt.name,'outgroups':['Reference']}
    return entry,gate


def test_hash_bound_inputs_pass_only_mechanical_scope(tmp_path,bound):
    entry,gate=bound
    result=mod.audit(entry,tmp_path,gate)
    assert result['verdict']=='MECHANICAL_PASS'
    assert 'scientific acceptance unverified' in result['scope']
    assert result['checks']['outgroup_membership']['status']=='PASS'


def test_fresh_timestamp_cannot_rescue_stale_receipt(tmp_path,bound):
    entry,gate=bound
    (tmp_path/'metadata.tsv').write_text((tmp_path/'metadata.tsv').read_text().replace('Species beta','Species changed'))
    os.utime(tmp_path/'render.png',(9999999999,9999999999))
    result=mod.audit(entry,tmp_path,gate)
    assert result['verdict']=='FAIL' and result['checks']['render_binding']['status']=='FAIL'


def test_missing_explicit_metadata_never_guesses_sibling(tmp_path,bound):
    entry,gate=bound;del entry['metadata']
    assert mod.audit(entry,tmp_path,gate)['checks']['metadata']['status']=='FAIL'


@pytest.mark.parametrize('metadata', ['tip\tlabel\nA tip\tA\nA tip\tduplicate\nB\tB\nReference\tR\n',
    'tip\tlabel\nA tip\t(unnamed)\nB\tB\nReference\tR\n',
    'tip\tlabel\nA tip\tA\nReference\tR\n'])
def test_invalid_metadata_fails(tmp_path,bound,metadata):
    entry,gate=bound;(tmp_path/'metadata.tsv').write_text(metadata)
    assert mod.audit(entry,tmp_path,gate)['checks']['metadata']['status']=='FAIL'


def test_unknown_gate_and_missing_outgroup_remain_unverified(tmp_path,bound):
    entry,gate=bound;entry['outgroups']=[]
    row=mod.audit(entry,tmp_path)
    assert row['verdict']=='UNVERIFIED'
    assert row['checks']['gate']['status']=='UNVERIFIED'
    assert row['checks']['outgroup_membership']['status']=='UNVERIFIED'


@pytest.mark.parametrize('code,status',[(2,'FAIL'),(3,'UNVERIFIED'),(1,'UNVERIFIED')])
def test_gate_return_codes_not_inferred_from_stdout(tmp_path,bound,code,status):
    entry,gate=bound;gate.write_text(f"import sys\nprint('PASS')\nsys.exit({code})\n")
    row=mod.audit(entry,tmp_path,gate)
    assert row['verdict']==status and row['gate_exit']==code


def test_missing_gate_is_unverified(tmp_path,bound):
    entry,gate=bound
    assert mod.audit(entry,tmp_path,tmp_path/'missing.py')['verdict']=='UNVERIFIED'


def test_empty_manifest_and_existing_output_refused(tmp_path,bound):
    entry,gate=bound;manifest=tmp_path/'manifest.json';output=tmp_path/'audit.json'
    manifest.write_text(json.dumps({'trees':[]}))
    assert mod.main(['--manifest',str(manifest),'--output',str(output)])==2
    assert not output.exists()
    manifest.write_text(json.dumps({'trees':[entry]}));output.write_text('existing')
    assert mod.main(['--manifest',str(manifest),'--output',str(output),'--gate',str(gate)])==2
    assert output.read_text()=='existing'


def test_cli_binds_manifest_relative_paths(tmp_path,bound,monkeypatch):
    entry,gate=bound;manifest=tmp_path/'manifest.json';output=tmp_path/'audit.json'
    manifest.write_text(json.dumps({'trees':[entry]}));monkeypatch.chdir(ROOT)
    assert mod.main(['--manifest',str(manifest),'--output',str(output),'--gate',str(gate)])==0
    assert json.loads(output.read_text())['trees'][0]['verdict']=='MECHANICAL_PASS'


def test_extra_metadata_rows_refuse_even_with_matching_receipt(tmp_path,bound):
    entry,gate=bound
    meta=tmp_path/'metadata.tsv'
    meta.write_text(meta.read_text()+'Extra\tSpecies extra\n')
    receipt=tmp_path/'render.json'
    data=json.loads(receipt.read_text());data['metadata_sha256']=sha(meta);receipt.write_text(json.dumps(data))
    row=mod.audit(entry,tmp_path,gate)
    assert row['checks']['metadata']['status']=='FAIL'
    assert 'Extra' in row['checks']['metadata']['detail']

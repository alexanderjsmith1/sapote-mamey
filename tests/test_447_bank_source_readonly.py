"""Read-only source inspection and real-bank first-generation synchronization."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import pytest
from mamey import bank_transaction as B
from mamey.comparative_pairs import load_bank
from tools import ingest_package as I

ROOT=Path(__file__).resolve().parents[1]


def source(root):
    root.mkdir()
    (root/'mamey').mkdir();(root/'tools').mkdir()
    (root/'pyproject.toml').write_text('[project]\nname="mamey"\n[tool.sapote]\nversion="fixture"\n')
    for name in ('mamey/__init__.py','mamey/bank_transaction.py','tools/ingest_package.py'):(root/name).write_text('# synthetic source marker\n')
    return root


def snapshot(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}


def entry():
    return {'workflow_version':'v1','sid':'SYN','strain':{'sid':'SYN'},'bgcs':[], 'scan_agg':{},'tfbs':{},'rggmci_full':{},'tigrfam':{},'coupling':{},'resistance_coupling':{},'modeb_verdicts':[]}


def test_empty_bundle_source_read_is_byte_and_path_immutable(tmp_path):
    root=source(tmp_path/'source');before=snapshot(root)
    assert B._empty_bundle_source(root)
    with B.reader(root):pass
    assert load_bank(root/'bgc_data.json')=={'strains':{},'bgcs':[]}
    assert snapshot(root)==before and not (root/'.ingest.lock').exists()


def test_cooperating_writer_cannot_create_first_bank_inside_unlocked_source(tmp_path):
    root=source(tmp_path/'source');before=snapshot(root)
    with B.reader(root):
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(I.merge,entry(),root,True)
            with pytest.raises(B.BankError,match='SOURCE_DESTINATION_REFUSED'):future.result(timeout=3)
    assert snapshot(root)==before


def test_partial_or_unrelated_source_markers_do_not_bypass_bank_lock(tmp_path):
    root=tmp_path/'bank';root.mkdir();(root/'pyproject.toml').write_text('[project]\nname="mamey"\n')
    with B.reader(root):pass
    assert (root/'.ingest.lock').exists()


@pytest.mark.parametrize('state',['bgc_data.json','gene_data.json','deep_data.json','.ingest_transactions','.ingest_pending.json','.ingest_state.json'])
def test_marker_bearing_actual_bank_state_never_uses_source_bypass(tmp_path,state):
    root=source(tmp_path/'source')
    target=root/state
    if state=='.ingest_transactions':target.mkdir()
    else:target.write_text('{}')
    assert not B._empty_bundle_source(root)
    with B.lock(root):pass
    assert (root/'.ingest.lock').exists()


def test_marker_bearing_legacy_bank_reader_waits_for_first_writer(tmp_path,monkeypatch):
    root=source(tmp_path/'source');(root/'bgc_data.json').write_text('{"strains":{},"bgcs":[]}')
    prepared=threading.Event();release=threading.Event();reader_started=threading.Event()
    def boundary(name):
        if name=='prepared':prepared.set();assert release.wait(5)
    monkeypatch.setattr(B,'_boundary',boundary)
    def read():reader_started.set();return load_bank(root/'bgc_data.json')
    with ThreadPoolExecutor(max_workers=2) as pool:
        writer=pool.submit(I.merge,entry(),root,True);assert prepared.wait(5)
        reader=pool.submit(read);assert reader_started.wait(3)
        try:
            with pytest.raises(TimeoutError):reader.result(timeout=.1)
        finally:release.set()
        writer.result(timeout=5);result=reader.result(timeout=5)
    assert set(result['strains'])=={'SYN'}
    B.coherent(root)


def test_actual_default_comparative_consumer_does_not_mutate_source(tmp_path):
    assert B._empty_bundle_source(ROOT), 'this probe requires an empty current source tree'
    before=snapshot(ROOT)
    command="from mamey.master_workbook import update_e2_comparative_pairs; print(update_e2_comparative_pairs('bgc_data.json', 'unused.xlsx'))"
    run=subprocess.run([sys.executable,'-c',command],cwd=ROOT,capture_output=True,text=True,
                       env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    assert run.returncode==0,run.stderr
    assert 'NOT_ENOUGH_STRAINS' in run.stdout
    assert snapshot(ROOT)==before and not (ROOT/'.ingest.lock').exists()


def test_prior_package_readonly_behavior_and_source_marker_symlink_refusal(tmp_path):
    package=tmp_path/'package';package.mkdir();(package/'manifest.json').write_text('{}')
    with B.reader(package):pass
    assert not (package/'.ingest.lock').exists()
    with pytest.raises(B.BankError,match='PACKAGE_DESTINATION_REFUSED'):
        with B.lock(package,writer=True):pass
    root=source(tmp_path/'source');(root/'tools/ingest_package.py').unlink()
    external=tmp_path/'external';external.write_text('# marker');(root/'tools/ingest_package.py').symlink_to(external)
    assert not B._empty_bundle_source(root)

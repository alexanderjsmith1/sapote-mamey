"""First-generation bank reader and embedding lock controls, synthetic only."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextlib import contextmanager
import json
import threading
import pytest
from mamey import bank_transaction as B
from mamey.comparative_pairs import load_bank
from tools import ingest_package as I


def entry(sid):
    return {'workflow_version':'v1','sid':sid,'strain':{'sid':sid},'bgcs':[{'sid':sid,'bgc_id':'BGC001'}],
            'scan_agg':{},'tfbs':{},'rggmci_full':{},'tigrfam':{},'coupling':{},
            'resistance_coupling':{},'modeb_verdicts':[]}


def test_first_generation_reader_waits_for_writer_before_state_inspection(tmp_path,monkeypatch):
    bank=tmp_path/'legacy';bank.mkdir()
    (bank/'bgc_data.json').write_text(json.dumps({'strains':{},'bgcs':[]}))
    prepared=threading.Event();release=threading.Event();attempt=threading.Event()
    original_lock=B.lock
    @contextmanager
    def observed_lock(*args,**kwargs):
        if not kwargs.get('writer',False):attempt.set()
        with original_lock(*args,**kwargs) as root:yield root
    monkeypatch.setattr(B,'lock',observed_lock)
    def boundary(name):
        if name=='prepared':
            prepared.set()
            assert release.wait(5), 'test writer barrier timed out'
    monkeypatch.setattr(B,'_boundary',boundary)
    with ThreadPoolExecutor(max_workers=2) as pool:
        writer=pool.submit(I.merge,entry('SYN'),bank,True)
        assert prepared.wait(5)
        assert not (bank/B.PENDING).exists() and not (bank/B.STATE).exists()
        reader=pool.submit(load_bank,bank/'bgc_data.json')
        try:
            assert attempt.wait(2), 'reader bypassed bank lock before metadata inspection'
            with pytest.raises(TimeoutError):reader.result(timeout=.1)
        finally:release.set()
        writer.result(timeout=5)
        result=reader.result(timeout=5)
    assert set(result['strains'])=={'SYN'}
    B.coherent(bank)


@pytest.mark.parametrize('raise_error',[False,True])
def test_embedded_validate_releases_only_its_reader_context(tmp_path,monkeypatch,raise_error):
    bank=tmp_path/'bank';I.merge(entry('SYN'),bank,True)
    monkeypatch.setattr(I,'find_snapshot',lambda pkg:'unused')
    original_load=I.load
    def load(path,*args,**kwargs):
        if path=='unused':
            if raise_error:raise ValueError('synthetic bad snapshot')
            return {}
        return original_load(path,*args,**kwargs)
    monkeypatch.setattr(I,'load',load)
    monkeypatch.setattr(I,'build_entry',lambda *a:entry('SYN'))
    prior=len(B._reader_locks())
    try:
        if raise_error:
            with pytest.raises(ValueError):I.validate('SYN',tmp_path/'unused',bank)
        else:I.validate('SYN',tmp_path/'unused',bank)
        assert len(B._reader_locks())==prior
        with ThreadPoolExecutor(max_workers=1) as pool:
            writer=pool.submit(I.merge,entry('SYN2'),bank,True)
            try:writer.result(timeout=3)
            finally:B.release_reader_locks()
    finally:B.release_reader_locks()
    assert 'SYN2' in load_bank(bank/'bgc_data.json')['strains']


def test_malformed_legacy_soft_fallback_is_locked_and_package_stays_readonly(tmp_path):
    bank=tmp_path/'legacy';bank.mkdir();(bank/'bgc_data.json').write_text('malformed')
    assert load_bank(bank/'bgc_data.json')=={'strains':{},'bgcs':[]}
    assert (bank/'.ingest.lock').exists()
    pkg=tmp_path/'pkg';pkg.mkdir();(pkg/'manifest.json').write_text('{}')
    (pkg/'bgc_data.json').write_text(json.dumps({'strains':{},'bgcs':[]}))
    assert load_bank(pkg/'bgc_data.json')=={'strains':{},'bgcs':[]}
    assert not (pkg/'.ingest.lock').exists()

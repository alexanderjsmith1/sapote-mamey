"""Only synthetic bank fixtures and short local processes; no scientific data."""
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from mamey import bank_transaction as B
from tools import ingest_package as I

ROOT=Path(__file__).resolve().parent.parent

def entry(sid='SYN-A',version='v1'):
    return {'workflow_version':version,'sid':sid,'strain':{'sid':sid},'bgcs':[{'sid':sid,'bgc_id':'BGC001','products':'synthetic-'+sid,'length_kb':1,'edge_status':'Interior'}],'scan_agg':{},'tfbs':{},'rggmci_full':{},'tigrfam':{},'coupling':{},'resistance_coupling':{},'modeb_verdicts':[{'strain':sid,'bgc':'BGC001','status':'CANDIDATE','modeb_class':'','note':''}]}

def snap(bank):return {n:(bank/n).read_bytes() if (bank/n).exists() else None for n in B.STORES+(B.STATE,)}

def seed(tmp_path):
    bank=tmp_path/'bank';I.merge(entry(),bank,allow_dup=True);return bank

BOUNDARIES=['prepared','pending']+['published:'+n for n in B.STORES]+['published:deep_data.json','committed','cleared']

@pytest.mark.parametrize('boundary',BOUNDARIES)
def test_failure_at_every_boundary_coherent_or_recoverable(tmp_path,monkeypatch,boundary):
    bank=seed(tmp_path);before=snap(bank)
    def fault(n):
        if n==boundary:raise RuntimeError('synthetic interruption '+n)
    monkeypatch.setattr(B,'_boundary',fault)
    with pytest.raises(RuntimeError):I.merge(entry('SYN-B'),bank,allow_dup=True)
    monkeypatch.setattr(B,'_boundary',lambda _:None)
    if boundary=='prepared':
        assert snap(bank)==before;B.coherent(bank)
    elif boundary=='cleared':
        B.coherent(bank)
        assert 'SYN-B' in json.loads((bank/'bgc_data.json').read_text())['strains']
    else:
        with pytest.raises(B.BankError,match='RECOVERY_REQUIRED'):
            with B.reader(bank):pass
        result=B.recover(bank,'rollback')
        assert result['state']=='ROLLED_BACK' and snap(bank)==before
        assert len(list((bank/'.ingest_transactions').iterdir()))==2

@pytest.mark.parametrize('boundary',['pending','published:gene_data.json','committed'])
def test_explicit_finish_republishes_exact_validated_after_image(tmp_path,monkeypatch,boundary):
    bank=seed(tmp_path)
    monkeypatch.setattr(B,'_boundary',lambda n: (_ for _ in ()).throw(RuntimeError()) if n==boundary else None)
    with pytest.raises(RuntimeError):I.merge(entry('SYN-B'),bank,allow_dup=True)
    monkeypatch.setattr(B,'_boundary',lambda _:None)
    B.recover(bank,'finish');B.coherent(bank)
    assert sorted(json.loads((bank/'bgc_data.json').read_text())['strains'])==['SYN-A','SYN-B']

@pytest.mark.parametrize('file',['gene_data.json','rggmci_full.json','tigrfam.json','tfbs_coupling.json','resistance_coupling.json','strains.json','modeb_verdicts.csv'])
def test_all_malformed_stores_refuse_before_changes(tmp_path,file):
    bank=tmp_path/'legacy';bank.mkdir()
    (bank/'bgc_data.json').write_text(json.dumps({'strains':{},'bgcs':[]}))
    (bank/file).write_text('not JSON or CSV')
    before=snap(bank)
    with pytest.raises(B.BankError):I.merge(entry(),bank,allow_dup=True)
    assert snap(bank)==before and not (bank/B.PENDING).exists()

def test_schema_staged_and_failed_dedup_never_establishes_marker(tmp_path):
    bank=tmp_path/'bank';bank.mkdir()
    with pytest.raises(SystemExit):I.merge({**entry(),'workflow_version':None},bank)
    assert not (bank/'SCHEMA_VERSION').exists()
    I.merge(entry(),bank)
    before=snap(bank)
    with pytest.raises(SystemExit):I.merge(entry('SYN-B','v2'),bank)
    assert snap(bank)==before

@pytest.mark.parametrize('damage',['image','prior_state','symlink'])
def test_recovery_preflight_no_partial_restore(tmp_path,monkeypatch,damage):
    bank=seed(tmp_path);monkeypatch.setattr(B,'_boundary',lambda n: (_ for _ in ()).throw(RuntimeError()) if n=='published:gene_data.json' else None)
    with pytest.raises(RuntimeError):I.merge(entry('SYN-B'),bank,allow_dup=True)
    j=json.loads((bank/B.PENDING).read_text());tx=bank/'.ingest_transactions'/j['transaction']
    if damage=='image':(tx/'before'/'tigrfam.json').write_text('changed')
    if damage=='prior_state':(tx/'before'/B.STATE).write_text('{}')
    if damage=='symlink':
        (bank/'tigrfam.json').unlink();(bank/'tigrfam.json').symlink_to(tmp_path/'escape')
    before=snap(bank)
    with pytest.raises(B.BankError):B.recover(bank,'rollback')
    assert snap(bank)==before and (bank/B.PENDING).exists()

def test_reader_real_atlas_refuses_pending_before_outputs(tmp_path,monkeypatch):
    bank=seed(tmp_path);monkeypatch.setattr(B,'_boundary',lambda n: (_ for _ in ()).throw(RuntimeError()) if n=='pending' else None)
    with pytest.raises(RuntimeError):I.merge(entry('SYN-B'),bank,allow_dup=True)
    output=tmp_path/'atlas'
    run=subprocess.run([sys.executable,str(ROOT/'tools/generate_bgc_atlas.py'),'--banked-dir',str(bank),'--strain','SYN-A','--out',str(output)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    assert run.returncode!=0 and 'BANK_RECOVERY_REQUIRED' in run.stderr
    assert not output.exists()

def test_committed_hash_tamper_reader_refusal(tmp_path):
    bank=seed(tmp_path);(bank/'gene_data.json').write_text('{}')
    with pytest.raises(B.BankError,match='BYTES_MISMATCH'):
        with B.reader(bank):pass

def test_unknown_lock_backend_refuses(monkeypatch,tmp_path):
    import builtins
    old=builtins.__import__
    def intercept(name,*a,**k):
        if name in ('fcntl','msvcrt'):raise ImportError('synthetic unavailable')
        return old(name,*a,**k)
    monkeypatch.setattr(builtins,'__import__',intercept)
    with pytest.raises(B.BankError,match='LOCK_BACKEND_UNAVAILABLE'):
        with B.lock(tmp_path,writer=True):pass
    assert not (tmp_path/'bgc_data.json').exists()

def package(root,sid,version):
    p=root/sid;p.mkdir()
    snapshot={'workflow_version':version,'strain_id':sid,'taxonomy':'synthetic','assembly':{'genome_bp':1,'contigs':1,'n50':1,'gc_pct':50,'largest_contig':1},'bgc_counts':{'raw':0,'corrected':0,'interior':0,'edge':0,'full_contig':0},'bgcs':[],'source_scans':{}}
    (p/'manifest.json').write_text(json.dumps(snapshot));(p/(sid+'_Project_Memory_Snapshot.json')).write_text(json.dumps(snapshot));return p

@pytest.mark.parametrize('matching',[True,False])
def test_concurrent_public_main_schema_admission(tmp_path,matching):
    bank=tmp_path/'bank';p1=package(tmp_path,'SYN-A','v1');p2=package(tmp_path,'SYN-B','v1' if matching else 'v2')
    commands=[[sys.executable,str(ROOT/'tools/ingest_package.py'),'--package',str(p),'--banked-dir',str(bank),'--merge','--allow-dup'] for p in (p1,p2)]
    procs=[subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}) for cmd in commands]
    outputs=[p.communicate(timeout=20) for p in procs];codes=[p.returncode for p in procs]
    strains=json.loads((bank/'bgc_data.json').read_text())['strains']
    if matching:assert codes==[0,0] and set(strains)=={'SYN-A','SYN-B'}
    else:assert codes.count(0)==1 and len(strains)==1 and 'SCHEMA GATE' in ''.join(x[1] for x in outputs)
    B.coherent(bank)

def test_writer_waits_for_reader_entire_snapshot(tmp_path):
    bank=seed(tmp_path)
    script="from tools.ingest_package import merge; import json,sys; merge(json.loads(sys.argv[1]),sys.argv[2],allow_dup=True)"
    with B.reader(bank):
        p=subprocess.Popen([sys.executable,'-c',script,json.dumps(entry('SYN-B')),str(bank)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        # Process startup happens before its print below only after merge; with
        # reader held it cannot finish. Bounded communicate timeout proves hold.
        with pytest.raises(subprocess.TimeoutExpired):p.communicate(timeout=0.3)
        assert 'SYN-B' not in json.loads((bank/'bgc_data.json').read_text())['strains']
    p.communicate(timeout=20);assert p.returncode==0

def test_enrichment_transaction_does_not_stale_commit(tmp_path,monkeypatch):
    bank=seed(tmp_path)
    sys.path.insert(0,str(ROOT/'tools'))
    from _bankio import transactional_call
    def callback(stage):
        data=json.loads((stage/'gene_data.json').read_text());data['domain_arch']=[]
        (stage/'gene_data.json').write_text(json.dumps(data))
        (stage/'deep_data.json').write_text(json.dumps({'bgc_profile':[]}))
        return 0
    transactional_call(bank,callback)
    B.coherent(bank)
    assert (bank/'deep_data.json').exists()
    before=snap(bank)
    def bad(stage):
        (stage/'gene_data.json').write_text('{}');return 0
    with pytest.raises(B.BankError):transactional_call(bank,bad)
    assert snap(bank)==before

def test_intake_init_then_public_merge_is_coherent(tmp_path):
    sys.path.insert(0,str(ROOT/'tools'))
    from tools.mamey_intake import init_banked
    bank=tmp_path/'bank'
    created=init_banked(str(bank));assert 'bgc_data.json' in created
    B.coherent(bank);assert not (bank/'SCHEMA_VERSION').exists()
    p=package(tmp_path,'SYN-A','v1')
    run=subprocess.run([sys.executable,str(ROOT/'tools/ingest_package.py'),'--package',str(p),'--banked-dir',str(bank),'--merge'],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    assert run.returncode==0,run.stderr
    B.coherent(bank);assert (bank/'SCHEMA_VERSION').read_text()=='v1'

def test_comparative_reader_does_not_hide_pending_as_empty(tmp_path,monkeypatch):
    from mamey.comparative_pairs import load_bank
    bank=seed(tmp_path);monkeypatch.setattr(B,'_boundary',lambda n: (_ for _ in ()).throw(RuntimeError()) if n=='pending' else None)
    with pytest.raises(RuntimeError):I.merge(entry('SYN-B'),bank,allow_dup=True)
    with pytest.raises(B.BankError,match='RECOVERY_REQUIRED'):load_bank(bank/'bgc_data.json')

def test_schema_gate_failed_input_does_not_establish_marker(tmp_path):
    p=package(tmp_path,'SYN-A','v1');bank=tmp_path/'bank';bank.mkdir()
    assert I._schema_gate(p,bank)=='v1'
    assert not (bank/'SCHEMA_VERSION').exists()
    (p/'manifest.json').write_text('{}')
    with pytest.raises(SystemExit):I._schema_gate(p,bank,force=True)
    assert not (bank/'SCHEMA_VERSION').exists()

def test_forced_schema_drift_explicitly_receipted(tmp_path):
    bank=seed(tmp_path)
    state=I.merge(entry('SYN-B','v2'),bank,allow_dup=True,force_schema=True)
    assert state['schema_admission']=={'incoming_version':'v2','force_schema':True}
    assert (bank/'SCHEMA_VERSION').read_text()=='v1'

def test_no_reader_lock_write_inside_package(tmp_path):
    pkg=tmp_path/'package';pkg.mkdir();(pkg/'manifest.json').write_text('{}')
    with B.reader(pkg):pass
    assert not (pkg/'.ingest.lock').exists()
    with pytest.raises(B.BankError,match='PACKAGE_DESTINATION'):
        with B.lock(pkg,writer=True):pass

def test_incoming_locus_binding_refused_before_stage(tmp_path):
    bank=seed(tmp_path);before=snap(bank);e=entry('SYN-B');e['bgcs'][0]['sid']='SYN-A'
    with pytest.raises(B.BankError,match='LOCUS_BINDING'):I.merge(e,bank,allow_dup=True)
    assert snap(bank)==before

def test_embedded_reader_scope_releases_locks_after_return(tmp_path):
    bank=seed(tmp_path)
    @B.reader_scope
    def read():
        B.hold_reader(bank)
        return json.loads((bank/'bgc_data.json').read_text())
    read()
    assert not B._reader_locks()
    # A subsequent writer in the same interpreter must not deadlock.
    I.merge(entry('SYN-B'),bank,allow_dup=True)
    assert 'SYN-B' in json.loads((bank/'bgc_data.json').read_text())['strains']

@pytest.mark.parametrize('tool',['build_id_resolver','build_lead_tiers'])
def test_table_consumers_refuse_interrupted_bank_before_output(tmp_path,monkeypatch,tool):
    bank=seed(tmp_path);monkeypatch.setattr(B,'_boundary',lambda n: (_ for _ in ()).throw(RuntimeError()) if n=='published:gene_data.json' else None)
    with pytest.raises(RuntimeError):I.merge(entry('SYN-B'),bank,allow_dup=True)
    out=tmp_path/'table.csv'
    result=subprocess.run([sys.executable,str(ROOT/'tools'/f'{tool}.py'),'--banked-dir',str(bank),'--out',str(out)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    assert result.returncode!=0 and 'BANK_RECOVERY_REQUIRED' in result.stderr
    assert not out.exists()

def test_first_failed_transaction_rolls_back_missing_schema_and_stores(tmp_path,monkeypatch):
    bank=tmp_path/'bank';monkeypatch.setattr(B,'_boundary',lambda n: (_ for _ in ()).throw(RuntimeError()) if n=='published:SCHEMA_VERSION' else None)
    with pytest.raises(RuntimeError):I.merge(entry(),bank,allow_dup=True)
    B.recover(bank,'rollback')
    assert all(not (bank/n).exists() for n in B.STORES+(B.STATE,))
    assert not (bank/B.PENDING).exists()

def test_thread_reader_scopes_do_not_release_each_others_locks(tmp_path):
    import threading
    bank=seed(tmp_path);ready=threading.Event();done=threading.Event();status=[]
    @B.reader_scope
    def first():
        B.hold_reader(bank);ready.set();done.wait(2);status.append(len(B._reader_locks()))
    thread=threading.Thread(target=first);thread.start();assert ready.wait(2)
    @B.reader_scope
    def second():B.hold_reader(bank)
    second();done.set();thread.join(2)
    assert not thread.is_alive() and status==[1] and not B._reader_locks()

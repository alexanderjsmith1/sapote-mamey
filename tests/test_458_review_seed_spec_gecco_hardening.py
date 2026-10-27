"""Synthetic refusal/receipt tests; no clustering, alignments, or figure rendering."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, sys
import pytest
BASE=Path(os.environ.get('M5_REVIEW_BASE',str(Path(__file__).resolve().parents[1])))
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'tools'))
def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,BASE/'tools'/filename)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
seed=module('seed_review','bigscape_seeded.py')
mrc=module('mrc_review','multi_reference_comparison.py')

CORE='SYN-A / NODE_SYN_length_10000_cov_20 / region001 / BGC001'

def test_c119_late_environment_change_refused(tmp_path):
    code="import os,runpy,sys,types;fake=types.ModuleType('big_scape.__main__');fake.main=lambda:0;sys.modules['big_scape']=types.ModuleType('big_scape');sys.modules['big_scape.__main__']=fake;os.environ['PYTHONHASHSEED']='0';m=runpy.run_path("+repr(str(BASE/'tools/bigscape_seeded.py'))+");raise SystemExit(m['main'](['--receipt',"+repr(str(tmp_path/'refused.json'))+"]))"
    r=subprocess.run([sys.executable,'-c',code],env={**os.environ,'PYTHONHASHSEED':'random','PYTHONPATH':str(BASE)},capture_output=True,text=True)
    assert r.returncode==2,r.stdout+r.stderr
    assert not (tmp_path/'refused.json').exists()


def test_c121_failed_serialization_keeps_starting(tmp_path,monkeypatch):
    p=tmp_path/'receipt.json';p.write_text('{"status":"STARTING"}')
    def fail(*a,**kw):raise OSError('interrupted write')
    monkeypatch.setattr(seed.json,'dump',fail)
    with pytest.raises(OSError):seed.atomic_receipt(p,{'status':'EXITED'})
    assert json.loads(p.read_text())=={'status':'STARTING'}
    assert not list(tmp_path.glob('*.tmp'))


def test_c121_replace_failure_keeps_starting(tmp_path,monkeypatch):
    p=tmp_path/'receipt.json';p.write_text('{"status":"STARTING"}')
    def fail(*a):raise OSError('replace failed')
    monkeypatch.setattr(seed.os,'replace',fail)
    with pytest.raises(OSError):seed.atomic_receipt(p,{'status':'EXITED'})
    assert json.loads(p.read_text())['status']=='STARTING'
    assert not list(tmp_path.glob('*.tmp'))


def test_c121_successful_final_receipt(tmp_path):
    p=tmp_path/'receipt.json';p.write_text('{"status":"STARTING"}')
    seed.atomic_receipt(p,{'status':'EXITED'});assert json.loads(p.read_text())['status']=='EXITED'


@pytest.mark.parametrize('aggregate',['rank','summed_bitscore','genes_present'])
def test_c128_all_producer_aggregate_columns_block_native_search(tmp_path,aggregate,monkeypatch):
    regions=tmp_path/'regions';regions.mkdir();p=regions/'q.gbk';p.write_text('retained bytes')
    pin=hashlib.sha256(p.read_bytes()).hexdigest();spec=tmp_path/'SPEC.tsv'
    header='region_file\tlabel\taccession\trole\tidentity\tsha256\tlocus\t'+aggregate+'\n'
    spec.write_text(header+f'q.gbk\tQuery\tQ\tquery\t{CORE}\t{pin}\t{CORE}\t1\n'+f'q.gbk\tRef\tR\tpublic\tR\t{pin}\t{CORE}\t1\n')
    # Distinct source file per row is part of the existing SPEC contract.
    (regions/'r.gbk').write_bytes(p.read_bytes());spec.write_text(spec.read_text().replace('q.gbk\tRef','r.gbk\tRef'))
    monkeypatch.setattr(mrc,'build',lambda *a,**k:pytest.fail('search must never start'))
    out=tmp_path/'out'
    with pytest.raises(ValueError,match='SAVED_PAIRS_REQUIRED'):mrc.main(['--spec',str(spec),'--out',str(out)])
    assert not out.exists()


def test_c121_actual_main_final_serialization_failure_keeps_starting(tmp_path,monkeypatch):
    import types
    numpy=types.ModuleType('numpy');numpy.random=types.SimpleNamespace(seed=lambda value:None);numpy.__version__='synthetic'
    external=types.ModuleType('big_scape.__main__');external.main=lambda:0
    monkeypatch.setitem(sys.modules,'numpy',numpy)
    monkeypatch.setitem(sys.modules,'big_scape',types.ModuleType('big_scape'))
    monkeypatch.setitem(sys.modules,'big_scape.__main__',external)
    monkeypatch.setattr(sys,'argv',list(sys.argv))
    real_dump=seed.json.dump;calls=[]
    def interrupted(obj,handle,*args,**kwargs):
        calls.append(obj['status'])
        if len(calls)==2:raise OSError('interrupted final serialization')
        return real_dump(obj,handle,*args,**kwargs)
    monkeypatch.setattr(seed.json,'dump',interrupted)
    receipt=tmp_path/'actual_main.json'
    with pytest.raises(OSError):seed.main(['--allow-unseeded','--receipt',str(receipt)])
    assert json.loads(receipt.read_text())['status']=='STARTING'
    assert not list(tmp_path.glob('*.tmp'))


def test_c126_undeclared_producer_reference_refuses_fallback(tmp_path,monkeypatch):
    from types import SimpleNamespace
    gene=tmp_path/'R.genes.tsv';gene.write_text('sequence_id\tprotein_id\tstart\tend\taverage_p\nc\tx\t1\t10\t0.5\n')
    mapping=tmp_path/'map.tsv';mapping.write_text('genome\tregion_file\tantismash_locus_tag\tgecco_protein_id\tgecco_start\tgecco_end\toverlap_share_of_shorter\taccepted_ge_50pct\tgecco_average_p\nOTHER\tother.gbk\tt\tx\t1\t10\t1\tyes\t0.5\n')
    model={'label':'Q','prots':{},'refs':[{'accession':'R','gbk':'r.gbk','genes':[]}]}
    monkeypatch.setattr(mrc,'_gecco_files',lambda d,a: None if a=='Q' else (gene,None,'genome'))
    monkeypatch.setattr(mrc,'_region_coordinates',lambda *a:('c',0))
    monkeypatch.setattr(mrc,'_seqio',lambda:SimpleNamespace(read=lambda *a:SimpleNamespace(features=[])))
    with pytest.raises(ValueError,match='GECCO_PRODUCER_SOURCE_UNDECLARED'):mrc.attach_gecco(model,tmp_path,mapping)


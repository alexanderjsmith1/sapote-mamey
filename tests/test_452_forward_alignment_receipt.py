"""Receipt tests use mocked execution and synthetic rows, never public-genome searches."""
import importlib.util, json, sys, types, subprocess, hashlib
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('forward_candidate',ROOT/'mamey/diamond_align.py')
da=importlib.util.module_from_spec(spec);spec.loader.exec_module(da)
ROW='q\ts\t81\t10\t1\t0\t1\t10\t1\t10\t1e-8\t25\t90\t80\n'

def inputs(tmp_path):
    q=tmp_path/'q.fa';r=tmp_path/'r.fa';exe=tmp_path/'diamond'
    q.write_text('>q\nMA\n');r.write_text('>r\nMA\n');exe.write_text('mock executable')
    return q,r,exe

@pytest.mark.parametrize('version_ok',[True,False])
def test_cli_records_actual_backend_command_inputs_and_unset_defaults(monkeypatch,tmp_path,version_ok):
    q,r,exe=inputs(tmp_path);calls=[]
    monkeypatch.setattr(da.shutil,'which',lambda _:str(exe))
    def run(argv,**kw):
        calls.append(argv)
        if argv[1]=='version':
            if not version_ok:raise subprocess.TimeoutExpired(argv,10)
            return subprocess.CompletedProcess(argv,0,'diamond version MOCK\n','')
        if argv[1]=='blastp':Path(argv[argv.index('--out')+1]).write_text(ROW)
        return subprocess.CompletedProcess(argv,0,'','')
    monkeypatch.setattr(da.subprocess,'run',run)
    result=da._align_fasta_cli(str(q),str(r),2,0,0,'ultra-sensitive')
    assert result['ok'] and result['hits'][0]['pident']==81
    p=result['provenance'];assert p['backend']=='diamond_cli'
    assert p['alignment_argv']==calls[-1] and '--ultra-sensitive' in calls[-1]
    assert '--evalue' not in calls[-1] and '--max-target-seqs' not in calls[-1]
    assert p['backend_defaults']=={'evalue':'NOT_EXPLICITLY_SET','max_target_seqs':'NOT_EXPLICITLY_SET'}
    assert p['inputs']['query']['sha256']==hashlib.sha256(q.read_bytes()).hexdigest()
    assert p['executable']['sha256']==hashlib.sha256(exe.read_bytes()).hexdigest()
    assert bool(p['engine_version_response'])==version_ok
    assert bool(p['warnings']) != version_ok
    json.dumps(p)

@pytest.mark.parametrize('metadata_ok',[True,False])
def test_binding_does_not_borrow_cli_version(monkeypatch,tmp_path,metadata_ok):
    q,r,exe=inputs(tmp_path)
    package=types.ModuleType('diamond4py');package.__file__=str(exe);package.Diamond=object
    native=types.ModuleType('diamond4py.libdiamond');native.__file__=str(exe)
    def main(*args):Path(args[args.index('--out')+1]).write_text(ROW)
    native.main=main
    monkeypatch.setitem(sys.modules,'diamond4py',package);monkeypatch.setitem(sys.modules,'diamond4py.libdiamond',native)
    def metadata_version(name):
        if not metadata_ok: raise RuntimeError('metadata unavailable')
        return 'PACKAGE-MOCK'
    monkeypatch.setattr(da.importlib.metadata,'version',metadata_version)
    monkeypatch.setattr(da,'build_db',lambda *a,**kw:{'ok':True,'db_path':'fixture.dmnd'})
    monkeypatch.setattr(da.subprocess,'run',lambda *a,**kw:pytest.fail('Binding must not probe CLI'))
    result=da.align_fasta(str(q),str(r),sensitivity='sensitive')
    assert result['ok'];p=result['provenance'];assert p['backend']=='diamond4py'
    assert p['engine_version_response'] is None and p['binding_package_version']==('PACKAGE-MOCK' if metadata_ok else None)
    assert p['alignment_argv'][0]=='blastp' and '--sensitive' in p['alignment_argv']
    assert p['diamond4py.libdiamond']['sha256']==hashlib.sha256(exe.read_bytes()).hexdigest()

def tool():
    sys.path.insert(0,str(ROOT/'tools'))
    spec=importlib.util.spec_from_file_location('rescue_candidate',ROOT/'tools/gap_directed_rescue.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_standalone_keeps_forward_provenance_and_list_contract(monkeypatch):
    from mamey import diamond_align
    m=tool();p={'backend':'mock','capture_state':'CAPTURED'}
    monkeypatch.setattr(diamond_align,'align_fasta',lambda *a,**kw:{'ok':True,'hits':[{'qseqid':'q'}],'provenance':p})
    hits=m.run_diamond([{'id':'g','aa':'MA'}],{'p':{'aa':'MA'}},1)
    assert isinstance(hits,list) and hits==[{'qseqid':'q'}] and hits.provenance==p

@pytest.mark.parametrize('precomputed',[True,False])
def test_final_receipt_carries_provenance_or_explicit_external_state(monkeypatch,tmp_path,precomputed):
    m=tool();monkeypatch.setattr(m,'load_reference',lambda p:([],'fixture'))
    monkeypatch.setattr(m,'run_diamond',lambda *a:m._AlignmentHits([],{'backend':'mock','capture_state':'CAPTURED'}))
    monkeypatch.setattr(m,'search',lambda *a:([],[]));monkeypatch.setattr(m,'split_genes',lambda *a:([],'not needed'))
    monkeypatch.setattr(m,'partner_checks',lambda *a,**kw:{})
    result=m.analyse_region('fixture',{},[],{'identity':'synthetic / record1 / region001 / BGC001'},'fixture.gbk','','fixture',tmp_path/'out',hits=[] if precomputed else None,figure=False,gene_table=False,write_proteins=False)
    saved=json.loads((tmp_path/'out/gap_rescue_receipt.json').read_text())
    assert saved['forward_alignment']==result['forward_alignment']
    assert saved['forward_alignment']['capture_state']==('PRECOMPUTED_UNVERIFIED' if precomputed else 'CAPTURED')

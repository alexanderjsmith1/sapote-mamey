"""Actual QC/main functions; all external commands/gate verdicts are synthetic mocks."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def runner():
    spec=importlib.util.spec_from_file_location('t23_t24_cut_runner',ROOT/'tools/run_planned_tree.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def gates(runner,monkeypatch,tmp_path,fault=None):
    tools=tmp_path/'tools';mamey=tmp_path/'mamey';tools.mkdir();mamey.mkdir()
    paths={'sanity':tools/'tree_sanity_check.py','postflight':tools/'phylo_postflight.py','evidence':mamey/'phylo_evidence.py'}
    for key,path in paths.items():
        if fault!=key+'_missing':path.write_text('# synthetic gate fixture; never executed\n')
    tree=tmp_path/'tree.nwk';tree.write_text('synthetic core tree bytes; not parsed\n')
    calls=[]
    def sanity_check(treefile,outgroup):
        calls.append(('sanity',treefile,outgroup))
        return fault!='sanity_refusal','[tree_sanity_check] MOCK_'+('FAIL' if fault=='sanity_refusal' else 'PASS')
    def support(text):
        calls.append(('support',text))
        if fault=='support_refusal':raise RuntimeError('MOCK_SUPPORT_REFUSAL')
        return {'label':'mock support','node_count':1,'sh_alrt_min':None,'ufboot_min':None,'weak_node_count':0}
    def load(path,name):
        key='sanity' if str(path).endswith('tree_sanity_check.py') else 'evidence'
        calls.append(('load',str(path)))
        if fault==key+'_loader_none':return None
        if fault==key+'_import_error':raise ImportError('MOCK_IMPORT_ERROR')
        return SimpleNamespace(check=sanity_check) if key=='sanity' else SimpleNamespace(_support=support)
    def postflight(command,**kwargs):
        calls.append(('postflight',command))
        if fault=='postflight_launch_error':raise PermissionError('MOCK_LAUNCH_ERROR')
        return SimpleNamespace(returncode=1 if fault=='postflight_refusal' else 0,stdout='MOCK_POSTFLIGHT')
    monkeypatch.setattr(runner,'_load_module',load)
    monkeypatch.setattr(runner.subprocess,'run',postflight)
    return tools,mamey,tree,calls,load


@pytest.mark.parametrize('fault',['sanity_missing','postflight_missing','evidence_missing',
    'sanity_loader_none','evidence_loader_none','sanity_import_error','evidence_import_error',
    'postflight_launch_error','sanity_refusal','postflight_refusal','support_refusal'])
def test_every_unavailable_or_refusing_mandatory_gate_fails_explicitly(runner,monkeypatch,tmp_path,fault):
    tools,mamey,tree,calls,_=gates(runner,monkeypatch,tmp_path,fault)
    ok,lines=runner.hard_tree_qc(str(tree),'synthetic_out',str(tools),str(mamey))
    assert ok is False
    identity='phylo_evidence' if fault.startswith(('evidence','support')) else 'tree_sanity_check' if fault.startswith('sanity') else 'phylo_postflight'
    assert any(identity in line and ('FAIL' in line or 'REFUSED' in line) for line in lines),lines


def test_all_available_mock_gate_passes_preserve_interface(runner,monkeypatch,tmp_path):
    tools,mamey,tree,calls,_=gates(runner,monkeypatch,tmp_path)
    ok,lines=runner.hard_tree_qc(str(tree),'synthetic_out',str(tools),str(mamey),'/synthetic/genomes')
    assert ok is True and isinstance(lines,list)
    assert any(call[0]=='sanity' for call in calls) and any(call[0]=='support' for call in calls)
    postflight=next(call[1] for call in calls if call[0]=='postflight')
    assert postflight[-2:]==['--genomes-dir','/synthetic/genomes']


def test_cached_gate_from_another_tree_cannot_mask_missing_own_gate(runner,monkeypatch,tmp_path):
    tools,mamey,tree,calls,_=gates(runner,monkeypatch,tmp_path,'sanity_missing')
    monkeypatch.setitem(sys.modules,'tree_sanity_check',SimpleNamespace(check=lambda *args,**kwargs:(True,'WRONG_CACHED_GATE')))
    ok,lines=runner.hard_tree_qc(str(tree),'synthetic_out',str(tools),str(mamey))
    assert not ok and 'WRONG_CACHED_GATE' not in '\n'.join(lines)


def main_fixture(runner,monkeypatch,tmp_path,ani_mode='success',qc_fault=None):
    tools,mamey,tree,qc_calls,load=gates(runner,monkeypatch,tmp_path,qc_fault)
    work=tmp_path/'work';work.mkdir()
    expected_tree=work/'iqtree.treefile';expected_contree=work/'iqtree.contree';alignment=work/'alignment.faa'
    engine_calls=[]
    execution=SimpleNamespace(ALIGNMENT_NAMES=['alignment.faa'],find_alignment=lambda path:str(alignment),
        declared_query_tips=lambda *args:['synthetic_query'],gtotree_retained_tips=lambda path:['synthetic_query','synthetic_out'],
        tip_retention=lambda *args:{'status':'TIPS_RETAINED','dropped':[],'unexpected':[],'runlog_claim':'MOCK_RETAINED'},
        format_dropped=lambda result:[],iqtree_completion=lambda prefix:{'status':'COMPLETE','support_nodes':1,'reasons':[],'contree':str(expected_contree),'last_log_line':'MOCK_FINISHED'})
    monkeypatch.setattr(runner,'_load_module',lambda path,name:execution if str(path).endswith('gtotree_execution_gate.py') else load(path,name))
    original_qc=runner.hard_tree_qc
    monkeypatch.setattr(runner,'hard_tree_qc',lambda treefile,outgroup:original_qc(treefile,outgroup,str(tools),str(mamey)))
    monkeypatch.setattr(runner,'preflight_genome_list',lambda *args:(['/synthetic/query.fna','/synthetic/out.fna'],[]))
    monkeypatch.setattr(runner,'_resolve',lambda names:None if names==['fastANI'] and ani_mode=='unavailable' else '/mock/fastANI' if names==['fastANI'] else '/mock/iqtree' if names==['iqtree','iqtree2'] else '/mock/GToTree')
    monkeypatch.setattr(runner,'gtotree_version',lambda path:(2,'MOCK_GTOTREE_VERSION'))
    monkeypatch.setattr(runner,'_hmm_dir_for',lambda path:'/synthetic/hmm')
    monkeypatch.setattr(runner,'resolve_hmm',lambda *args:('/synthetic/hmm/mock.hmm','/synthetic/hmm','mock-sha'))
    monkeypatch.setenv('Pfam_data_dir',str(work/'pfam')+'/')
    def run(command,log,env=None):
        engine_calls.append(command)
        if command[0]=='/mock/GToTree':alignment.write_text('mock alignment; not parsed\n');return 0
        if command[0]=='/mock/iqtree':
            expected_tree.write_text('mock core tree; not biological\n');expected_contree.write_text('mock consensus; not biological\n');return 0
        assert command[0]=='/mock/fastANI'
        if ani_mode=='launch_error':raise OSError('MOCK_FASTANI_LAUNCH_ERROR')
        attempt=Path(command[command.index('-o')+1])
        if ani_mode in ('success','partial_nonzero'):attempt.write_text('mock ANI bytes; no scientific interpretation\n')
        return 7 if ani_mode in ('nonzero','partial_nonzero') else 0
    monkeypatch.setattr(runner,'run',run)
    argv=['--genome-list','/synthetic/genomes.txt','--workdir',str(work),'--outgroup','synthetic_out','--approved']
    return SimpleNamespace(work=work,argv=argv,engine_calls=engine_calls,tree=expected_tree,contree=expected_contree,alignment=alignment)


@pytest.mark.parametrize('mode,status',[('nonzero','FASTANI_FAILED'),('partial_nonzero','FASTANI_FAILED'),
    ('unavailable','FASTANI_UNAVAILABLE'),('missing_output','FASTANI_OUTPUT_MISSING'),('launch_error','FASTANI_LAUNCH_FAILED')])
def test_requested_ani_failure_is_nonzero_typed_and_preserves_core_tree(runner,monkeypatch,tmp_path,capsys,mode,status):
    state=main_fixture(runner,monkeypatch,tmp_path,mode)
    rc=runner.main(state.argv+['--ani-refs','/synthetic/refs.txt','--ani-queries','/synthetic/queries.txt'])
    output=capsys.readouterr()
    receipt=json.loads((state.work/'run_status.json').read_text())
    assert rc==8 and receipt['status']==status and receipt['fastani'] is None
    assert receipt['core_tree_status']=='TREE_QC_PASSED' and receipt['fastani_stage']['output'] is None
    assert all(path.is_file() for path in [state.tree,state.contree,state.alignment])
    assert 'DONE.' not in output.out and 'boundary table=' not in output.out
    assert status in output.err and status in (state.work/'run_planned_tree.log').read_text()
    if mode in ('nonzero','partial_nonzero'):assert receipt['fastani_stage']['returncode']==7


@pytest.mark.parametrize('mode',['nonzero','missing_output','unavailable'])
def test_prior_ani_table_cannot_mask_a_requested_failure(runner,monkeypatch,tmp_path,mode):
    state=main_fixture(runner,monkeypatch,tmp_path,mode)
    prior=state.work/'fastani.tsv';prior.write_text('prior ANI artifact must remain unadvertised\n')
    assert runner.main(state.argv+['--ani-refs','/synthetic/refs.txt'])==8
    receipt=json.loads((state.work/'run_status.json').read_text())
    assert receipt['fastani'] is None and receipt['fastani_stage']['output'] is None
    assert prior.read_text()=='prior ANI artifact must remain unadvertised\n'
    if mode!='unavailable':
        command=next(cmd for cmd in state.engine_calls if cmd[0]=='/mock/fastANI')
        assert Path(command[command.index('-o')+1])!=prior


def test_current_mock_ani_success_publishes_verified_bytes(runner,monkeypatch,tmp_path,capsys):
    state=main_fixture(runner,monkeypatch,tmp_path)
    prior=state.work/'fastani.tsv';prior.write_text('old bytes\n')
    assert runner.main(state.argv+['--ani-refs','/synthetic/refs.txt'])==0
    receipt=json.loads((state.work/'run_status.json').read_text())
    assert receipt['status']=='DONE' and receipt['fastani']==str(prior)
    assert prior.read_text()=='mock ANI bytes; no scientific interpretation\n'
    assert receipt['fastani_stage']['output_sha256']==hashlib.sha256(prior.read_bytes()).hexdigest()
    command=next(cmd for cmd in state.engine_calls if cmd[0]=='/mock/fastANI')
    assert command[command.index('--ql')+1]=='/synthetic/genomes.txt'
    assert 'DONE.' in capsys.readouterr().out


def test_unrequested_ani_preserves_done_status_shape_without_ani_launch(runner,monkeypatch,tmp_path):
    state=main_fixture(runner,monkeypatch,tmp_path,'unavailable')
    assert runner.main(state.argv)==0
    receipt=json.loads((state.work/'run_status.json').read_text())
    assert receipt['status']=='DONE' and receipt['fastani'] is None and 'fastani_stage' not in receipt
    assert all(cmd[0]!='/mock/fastANI' for cmd in state.engine_calls)


@pytest.mark.parametrize('fault',['postflight_missing','evidence_missing','evidence_loader_none','evidence_import_error','sanity_missing'])
def test_main_actual_qc_failure_blocks_done_and_requested_ani(runner,monkeypatch,tmp_path,capsys,fault):
    state=main_fixture(runner,monkeypatch,tmp_path,qc_fault=fault)
    assert runner.main(state.argv+['--ani-refs','/synthetic/refs.txt'])==6
    receipt=json.loads((state.work/'run_status.json').read_text())
    assert receipt['status']=='TREE_QC_FAILED'
    assert all(cmd[0]!='/mock/fastANI' for cmd in state.engine_calls)
    assert 'DONE.' not in capsys.readouterr().out


def test_current_output_publication_failure_is_typed_and_preserves_prior_file(runner,monkeypatch,tmp_path):
    state=main_fixture(runner,monkeypatch,tmp_path)
    prior=state.work/'fastani.tsv';prior.write_text('prior bytes\n')
    monkeypatch.setattr(runner.os,'replace',lambda *args:(_ for _ in ()).throw(PermissionError('MOCK_PUBLISH_DENIED')))
    assert runner.main(state.argv+['--ani-refs','/synthetic/refs.txt'])==8
    receipt=json.loads((state.work/'run_status.json').read_text())
    assert receipt['status']=='FASTANI_OUTPUT_PUBLISH_FAILED' and receipt['fastani'] is None
    assert prior.read_text()=='prior bytes\n'
    assert receipt['fastani_stage']['returncode']==0
    assert 'MOCK_PUBLISH_DENIED' in receipt['fastani_stage']['detail']


def test_current_output_hash_read_failure_is_typed_and_not_published(runner,monkeypatch,tmp_path):
    state=main_fixture(runner,monkeypatch,tmp_path)
    original=runner._sha256
    def sha(path):
        if '.fastani_attempt_' in str(path):raise PermissionError('MOCK_OUTPUT_UNREADABLE')
        return original(path)
    monkeypatch.setattr(runner,'_sha256',sha)
    assert runner.main(state.argv+['--ani-refs','/synthetic/refs.txt'])==8
    receipt=json.loads((state.work/'run_status.json').read_text())
    assert receipt['status']=='FASTANI_OUTPUT_VALIDATION_FAILED' and receipt['fastani'] is None
    assert not (state.work/'fastani.tsv').exists()

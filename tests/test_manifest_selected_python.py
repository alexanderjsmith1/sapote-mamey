"""Selected interpreter at the real manifest CLI; admissions/subsets are bounded spies."""
from pathlib import Path
from types import SimpleNamespace as NS
import importlib.util,json,os,sys
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def tool(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'tools'))
    spec=importlib.util.spec_from_file_location('manifest_selected_python',ROOT/'tools/gen_release_manifest.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def fixture(tmp_path,tool):
    root=tmp_path/'source';(root/'mamey').mkdir(parents=True);(root/'tests').mkdir()
    (root/'mamey/__init__.py').write_text('__version__ = "9.9.9"\n')
    (root/'CITATION.cff').write_text("version: '8.8.8'\n")
    (root/'BUILD_STAMP.txt').write_text('build=20261017v888b\n')
    (root/'tests/test_consumer.py').write_text('# RELEASE_MANIFEST synthetic owner\n')
    (root/'RELEASE_MANIFEST.md').write_text('''**Cut/build date:** 2000-01-01
**Bundle version:** `sapote-mamey-v0.0.0`
**Engine:** Mamey v0.0.0
**Build stamp:** OLD
## Validation status

| Gate | Status |
| --- | --- |
| `sync_version --check` | PASS (engine 0.0.0, bundle 0.0.0) |
All four tiers share build stamp `OLD`.
All tracked version anchors at v0.0.0 / Mamey 0.0.0.
`MAMEY_CHATGPT_EXECUTION_PROMPT.md` updated to v0.0.0.
''')
    tool.apply_manifest_with_counts(root,2,0,'receipt-bound partitioned profile')
    alias=tmp_path/'venv prefix/bin/python';alias.parent.mkdir(parents=True);alias.symlink_to(sys.executable)
    return root,alias

@pytest.mark.parametrize('baseline',[True,False])
@pytest.mark.parametrize('refused',[False,True])
def test_structured_cli_uses_selected_locator_and_retains_admission_refusal(tool,tmp_path,monkeypatch,baseline,refused):
    root,alias=fixture(tmp_path,tool);before=(root/'RELEASE_MANIFEST.md').read_bytes();calls=[]
    def counts(source,receipt,digest,**kwargs):
        calls.append(kwargs)
        assert source==root and digest=='1'*64
        if refused:raise ValueError('synthetic selected-environment mismatch')
        return {'passed':2,'skipped':0},{'selected':'bound-spy'}
    def subset(files,source,**kwargs):
        assert kwargs['environment']=={'selected':'bound-spy'}
        return 1,0,0,'1 passed in 0.01s'
    monkeypatch.setitem(sys.modules,'_release_partition_runner',NS(verified_counts=counts,measure_manifest_subset=subset))
    args=['--root',str(root),'--python',str(alias),'--fixed-point' if baseline else '--check',
          '--partition-baseline' if baseline else '--partition-receipt',str(tmp_path/'receipt'),
          '--partition-receipt-sha256','1'*64,'--partition-admission',str(tmp_path/'admission')]
    assert tool.main(args)==(2 if refused else 0)
    assert calls[0]['python']==str(alias) and calls[0]['baseline']==baseline
    assert (root/'RELEASE_MANIFEST.md').read_bytes()==before

def test_invalid_interpreter_holds_before_source_mutation(tool,tmp_path):
    root,alias=fixture(tmp_path,tool);before=(root/'RELEASE_MANIFEST.md').read_bytes()
    assert tool.main(['--root',str(root),'--check','--python','python3 -B'])==2
    assert (root/'RELEASE_MANIFEST.md').read_bytes()==before

@pytest.mark.parametrize('kind',['health','subset'])
def test_child_helpers_keep_selected_locator(tool,tmp_path,monkeypatch,kind):
    alias='/chosen/lexical/python';seen=[]
    def run(argv,**kw):
        seen.append(argv)
        return NS(returncode=0,stdout='print_calls 12 direct terminal-emission calls\n1 passed in 0.01s\n',stderr='')
    monkeypatch.setattr(tool.subprocess,'run',run)
    if kind=='health':
        (tmp_path/'tools').mkdir();(tmp_path/'tools/repo_health.py').write_text('# spy only')
        assert tool.repo_health_print_calls(tmp_path,python=alias)==12
    else:assert tool._run_pytest_subset([tmp_path/'test_toy.py'],tmp_path,python=alias)[:3]==(1,0,0)
    assert seen[0][0]==alias

def test_unstructured_fixed_point_forwards_to_subset_and_health(tool,tmp_path,monkeypatch):
    root,alias=fixture(tmp_path,tool);seen=[]
    def subset(files,source,**kw):seen.append(('subset',kw['python']));return 1,0,0,'1 passed in 0.01s'
    def health(source,**kw):seen.append(('health',kw['python']));return None
    monkeypatch.setattr(tool,'_run_pytest_subset',subset);monkeypatch.setattr(tool,'repo_health_print_calls',health)
    assert tool.run_fixed_point(root,2,0,'fixture',python=str(alias))==(2,0,1)
    assert seen==[('subset',str(alias)),('health',str(alias)),('subset',str(alias))]


@pytest.mark.parametrize('selection', ['empty', 'omitted'])
def test_actual_cli_empty_selection_refuses_before_mutation_and_omission_works(tool,tmp_path,selection):
    import hashlib,subprocess
    root,_=fixture(tmp_path,tool)
    manifest=root/'RELEASE_MANIFEST.md'
    manifest.write_text(manifest.read_text().replace('Mamey v9.9.9','Mamey v0.0.0'))
    snapshot=lambda:{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in root.rglob('*') if p.is_file()}
    before=snapshot()
    argv=[sys.executable,'-B',str(ROOT/'tools/gen_release_manifest.py'),'--root',str(root),
          '--apply','--tests-passed','2','--tests-skipped','0']
    if selection=='empty':argv += ['--python','']
    result=subprocess.run(argv,cwd=tmp_path,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
                          capture_output=True,text=True,timeout=10)
    if selection=='empty':
        assert result.returncode==2,(result.stdout,result.stderr)
        assert 'selected interpreter refused' in result.stderr
        assert snapshot()==before
    else:
        assert result.returncode==0,(result.stdout,result.stderr)
        assert snapshot()!=before
        assert 'Mamey v9.9.9' in manifest.read_text()

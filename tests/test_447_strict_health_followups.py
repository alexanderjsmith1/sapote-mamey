"""Synthetic strict-health controls; no external tools, process payloads or scientific inputs."""
import ast
import builtins
import importlib.util
import math
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_pdf_import_failure_preserves_type_and_operator_cause(monkeypatch):
    from mamey import pdf_dependencies as module
    monkeypatch.setattr(module.importlib.util,'find_spec',lambda name:object())
    monkeypatch.setattr(module.shutil,'which',lambda name:None)
    original=builtins.__import__
    error=ImportError('synthetic embedded font module unavailable')
    def fail(name,*args,**kwargs):
        if name=='markdown_pdf':raise error
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',fail)
    result=module.status()
    assert result['primary_reportlab_embedded_fonts'] is False
    assert result['primary_error']=='PDF primary import unavailable: ImportError: synthetic embedded font module unavailable'
    assert not result['fallback_ready']


def test_pdf_ready_route_positive_control(monkeypatch):
    from mamey import pdf_dependencies as module
    monkeypatch.setattr(module.importlib.util,'find_spec',lambda name:object())
    monkeypatch.setattr(module.shutil,'which',lambda name:'/synthetic/'+name)
    original=builtins.__import__
    def available(name,*args,**kwargs):
        if name=='markdown_pdf':return SimpleNamespace(FONTS_EMBEDDED=True)
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',available)
    result=module.status()
    assert result['primary_reportlab_embedded_fonts'] is True and result['primary_error'] is None
    assert result['fallback_ready'] and result['publication_qa_ready']


@pytest.mark.parametrize('kill_race',[False,True])
@pytest.mark.parametrize('interrupt',[False,True])
def test_expected_exit_races_retain_original_failure_and_visible_cleanup_notes(kill_race,interrupt):
    original=KeyboardInterrupt('synthetic interrupt') if interrupt else subprocess.TimeoutExpired(['synthetic'],.1)
    calls=[]
    class Child:
        encoding='utf-8';errors=None;pid=42;returncode=None
        def poll(self):return self.returncode
        def wait(self,timeout=None):
            calls.append(('wait',timeout))
            if len([x for x in calls if x[0]=='wait'])==1:raise original
            if timeout==1 and kill_race:raise subprocess.TimeoutExpired(['synthetic'],1)
            self.returncode=3;return 3
        def terminate(self):calls.append(('terminate',None));raise ProcessLookupError('synthetic vanished')
        def kill(self):calls.append(('kill',None));raise ProcessLookupError('synthetic vanished')
    def start(cmd,stdout,**kwargs):stdout.write(b'diagnostics before race\r\n');return Child()
    node=next(x for x in ast.parse((ROOT/'tools/intake_harness.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='run_monitored')
    scope={'math':math,'time':time,'tempfile':tempfile,'subprocess':SimpleNamespace(Popen=start,STDOUT=subprocess.STDOUT,TimeoutExpired=subprocess.TimeoutExpired),'_HAVE_PSUTIL':False}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'synthetic-monitor','exec'),scope)
    with pytest.raises(type(original)) as caught:scope['run_monitored'](['synthetic'])
    assert caught.value is original and original.output=='diagnostics before race\n'
    expected=['child exited before terminate']+(['child exited before kill'] if kill_race else [])
    assert original.output_monitor_cleanup_races==expected
    assert len(original.__notes__)==len(expected)
    assert all('expected process race' in x for x in original.__notes__)
    assert calls[-1][0]=='wait'


def slides():
    spec=importlib.util.spec_from_file_location('strict_slides',ROOT/'tools/strain_slides.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def fixture(path,value):
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('knownclusterblast/SYN_NODE_1_length_120_c1.txt',
            '1. BGC0000001\nSource: synthetic class reference\nTable of Blast hits\nSYN_1\tsubject_1\t'+value+'\n')


@pytest.mark.parametrize('value',['NaN','inf','-inf','-1','100.1','not-numeric'])
def test_kcb_invalid_identity_refused_with_cause_and_closed_archive(tmp_path,monkeypatch,value):
    module=slides();path=tmp_path/'synthetic.zip';fixture(path,value)
    original=zipfile.ZipFile;opened=[]
    class Tracked(original):
        def __init__(self,*a,**kw):super().__init__(*a,**kw);opened.append(self)
    monkeypatch.setattr(zipfile,'ZipFile',Tracked)
    with pytest.raises(ValueError,match='STRAIN_SLIDE_KCB_UNVERIFIED') as caught:module.kcb_genes(path)
    assert value in str(caught.value) and 'SYN_1' in str(caught.value)
    assert isinstance(caught.value.__cause__,ValueError)
    assert len(opened)==1 and opened[0].fp is None


@pytest.mark.parametrize('value',['0','100','74.5'])
def test_kcb_valid_identity_retained_and_archive_closed(tmp_path,monkeypatch,value):
    module=slides();path=tmp_path/'synthetic.zip';fixture(path,value)
    original=zipfile.ZipFile;opened=[]
    class Tracked(original):
        def __init__(self,*a,**kw):super().__init__(*a,**kw);opened.append(self)
    monkeypatch.setattr(zipfile,'ZipFile',Tracked)
    result=module.kcb_genes(path)
    assert result['SYN_1'][0][3]==float(value)
    assert opened[0].fp is None

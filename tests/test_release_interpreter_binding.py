"""High-level/exporter selection shares a compatible absolute lexical interpreter."""
import importlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def api(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'tools'))
    return importlib.import_module('release_workflow')


def shell(tmp_path,choice,*,prefix='',stage=None):
    text=(ROOT/'tools/release_cut.sh').read_text()
    if '# BEGIN RELEASE PYTHON LOCATOR' in text:
        block=text.split('# BEGIN RELEASE PYTHON LOCATOR',1)[1].split('# END RELEASE PYTHON LOCATOR',1)[0]
    else:block='PYTHON="${PYTHON:-python3}"\n'
    code='CUT_FAILURE_STATUS=1; die(){ printf "%s\\n" "$*" >&2; exit "$CUT_FAILURE_STATUS"; };\n'+prefix+block
    if stage is not None:code+='\ncd "$1"\n'
    code+='\nprintf "%s" "$PYTHON"\n'
    return subprocess.run(['bash','-s','--',str(stage or tmp_path)],input=code,cwd=tmp_path,
        env=dict(os.environ,PYTHON=choice,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=5)


def test_environment_overrides_standing_exporter_selection_with_explicit_target(api,monkeypatch,tmp_path):
    monkeypatch.setenv('PYTHON','standing-wrong-stage-interpreter')
    environment=api.workflow_environment(sys.executable,tmp_path)
    assert environment['PYTHON']==str(api.support.resolve_interpreter(sys.executable))
    assert Path(environment['PYTHON']).is_absolute()


def test_python_selection_preserves_virtualenv_lexical_prefix(api,tmp_path):
    link=tmp_path/'venv prefix/bin/python';link.parent.mkdir(parents=True);link.symlink_to(sys.executable)
    selected,record=api.selected_interpreter(str(link))
    assert selected==link and selected.is_symlink()
    assert record['compatibility_response']=='SAPOTE_EXPORT_PYTHON_3_12_PLUS'
    assert len(record['locator_sha256'])==len(record['binary_sha256'])==64


def test_shell_relative_selection_is_pinned_before_stage_cd(tmp_path):
    selected=tmp_path/'bin/python selected';selected.parent.mkdir();selected.symlink_to(sys.executable)
    stage=tmp_path/'stage';stage.mkdir()
    result=shell(tmp_path,'./bin/python selected',stage=stage)
    assert result.returncode==0,result.stderr
    assert result.stdout==str(selected)


def test_shell_keeps_absolute_symlink_prefix(tmp_path):
    selected=tmp_path/'venv prefix/bin/python';selected.parent.mkdir(parents=True);selected.symlink_to(sys.executable)
    result=shell(tmp_path,str(selected))
    assert result.returncode==0 and result.stdout==str(selected)


@pytest.mark.parametrize('response',['','unrecognized','SAPOTE_EXPORT_PYTHON_3_12_PLUS extra'])
def test_zero_exit_nonpython_response_holds_in_both_entrypoints(api,tmp_path,response):
    selected=tmp_path/'not-python';selected.write_text('#!/bin/sh\nprintf "%s" '+repr(response)+'\nexit 0\n');selected.chmod(0o755)
    with pytest.raises(api.RegistryRefused) as caught:api.selected_interpreter(str(selected))
    assert caught.value.code==2
    result=shell(tmp_path,str(selected))
    assert result.returncode==2 and 'RELEASE-PYTHON-002' in result.stderr


def test_shell_function_is_not_an_executable_selection(tmp_path):
    result=shell(tmp_path,'fake_python',prefix='fake_python(){ return 0; };\n')
    assert result.returncode==2 and 'RELEASE-PYTHON-001' in result.stderr


def test_command_string_is_not_an_executable_selection(api,tmp_path):
    with pytest.raises(api.RegistryRefused):api.selected_interpreter('python3 -B')
    assert shell(tmp_path,'python3 -B').returncode==2

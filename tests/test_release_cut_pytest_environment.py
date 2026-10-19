"""Release orchestration must reject ambient pytest selection before preparing source."""
import ast
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]


def _shell_prefix(extra):
    script=(ROOT/'tools/release_cut.sh').read_text().split('DATE="',1)[0]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHON=sys.executable)
    env.pop('PYTEST_ADDOPTS',None);env.update(extra)
    return subprocess.run(['bash','-s','--','9.7.452','unused-source','unused-output'],input=script,
                          text=True,capture_output=True,env=env,timeout=5)


@pytest.mark.parametrize('override',['-k fast','-m not_public','--ignore=tests/public',' '])
def test_shell_refuses_ambient_options_before_source_access(override):
    result=_shell_prefix({'PYTEST_ADDOPTS':override})
    assert result.returncode!=0
    assert 'unset it and retry before source preparation' in result.stderr


def test_shell_without_override_keeps_admission_open():
    assert _shell_prefix({}).returncode==0


def _workflow_environment():
    tree=ast.parse((ROOT/'tools/release_workflow.py').read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='workflow_environment')
    def require(ok,message):
        if not ok: raise ValueError(message)
    ns={'os':os,'Path':Path,'contract':SimpleNamespace(require=require),
        'support':SimpleNamespace(resolve_interpreter=lambda _:Path(sys.executable))}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'workflow_environment','exec'),ns)
    return ns['workflow_environment']


def test_direct_workflow_refuses_override_before_source_access(monkeypatch):
    monkeypatch.setenv('PYTEST_ADDOPTS','-k fast')
    with pytest.raises(ValueError,match='unset it and retry before source preparation'):
        _workflow_environment()(sys.executable,Path('absent-source'))


def test_direct_workflow_without_override_preserves_environment(monkeypatch,tmp_path):
    monkeypatch.delenv('PYTEST_ADDOPTS',raising=False)
    monkeypatch.setenv('LANE_PROFILE_SENTINEL','preserved')
    result=_workflow_environment()(sys.executable,tmp_path)
    assert result['LANE_PROFILE_SENTINEL']=='preserved'
    assert result['PWD']==str(tmp_path.resolve())

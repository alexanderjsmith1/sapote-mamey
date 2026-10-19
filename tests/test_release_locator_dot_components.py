"""Normalize only dot components; symlink parents and venv invocation stay intact."""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def selection(tmp_path):
    selected = tmp_path / 'bin/python selected'
    selected.parent.mkdir()
    selected.symlink_to(sys.executable)
    return selected


def choice_and_environment(mode, selected):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    if mode == 'relative':
        choice = './bin/./python selected'
    elif mode == 'absolute':
        choice = str(selected.parent.parent) + '/./bin/./python selected'
    else:
        choice = 'python selected'
        env['PATH'] = './bin/.:/usr/bin:/bin'
    return choice, env


@pytest.mark.parametrize('mode', ['relative', 'absolute', 'path'])
@pytest.mark.parametrize('name,marker', [('release_cut.sh', 'RELEASE'), ('make_public_tier.sh', 'EXPORTER')])
def test_shell_dots_match_workflow_locator_spelling(tmp_path, selection, mode, name, marker):
    choice, env = choice_and_environment(mode, selection)
    env['PYTHON'] = choice
    text = (ROOT / 'tools' / name).read_text()
    block = text.split('# BEGIN ' + marker + ' PYTHON LOCATOR', 1)[1].split('# END ' + marker + ' PYTHON LOCATOR', 1)[0]
    script = 'set -eu\nCUT_FAILURE_STATUS=2; die(){ echo "$*" >&2; exit 2; };\n' + block + '\nprintf "%s" "$PYTHON"\n'
    process = subprocess.run(['/bin/bash', '-s'], input=script, cwd=tmp_path, env=env,
                             capture_output=True, text=True, timeout=5)
    assert process.returncode == 0, process.stdout + process.stderr
    assert process.stdout == str(selection)
    assert selection.is_symlink()


@pytest.mark.parametrize('mode', ['relative', 'absolute', 'path'])
def test_workflow_already_removes_only_dot_components(monkeypatch, tmp_path, selection, mode):
    choice, env = choice_and_environment(mode, selection)
    context = dict(os=os, Path=Path, shutil=shutil)
    tree = ast.parse((ROOT / 'tools/_release_validation.py').read_text())
    nodes = [node for node in tree.body if getattr(node, 'name', '') in {'ValidationRefused', 'resolve_interpreter'}]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<bound-resolver>', 'exec'), context)
    monkeypatch.chdir(tmp_path)
    if mode == 'path':
        monkeypatch.setenv('PATH', env['PATH'])
    result = context['resolve_interpreter'](choice)
    assert result == selection and result.is_symlink()

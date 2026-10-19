"""Run only locator blocks/functions, never source preparation or a release cut."""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def selected_path(tmp_path):
    caller = tmp_path / 'caller'
    physical = tmp_path / 'physical'
    for directory in (caller / 'bin', physical / 'bin', physical / 'nested'):
        directory.mkdir(parents=True)
    (caller / 'alias').symlink_to(physical / 'nested', target_is_directory=True)
    good = physical / 'bin/python'
    good.write_text('#!' + sys.executable + '\nimport sys\na=sys.argv[1:]\n'
                    'if a[:1]==["-B"]: a=a[1:]\n'
                    'assert a[0]=="-c"\nsys.argv=["-c",*a[2:]]\nexec(a[1])\n')
    bad = caller / 'bin/python'
    bad.write_text('#!' + sys.executable + '\nimport sys\nsys.exit(2)\n')
    good.chmod(0o755)
    bad.chmod(0o755)
    return caller, good


@pytest.mark.parametrize('name,marker', [('make_public_tier.sh', 'EXPORTER'), ('release_cut.sh', 'RELEASE')])
@pytest.mark.parametrize('via_path', [False, True])
def test_shell_locator_keeps_selected_executable_and_child_environment(tmp_path, selected_path, name, marker, via_path):
    caller, good = selected_path
    text = (ROOT / 'tools' / name).read_text()
    block = text[text.index('# BEGIN ' + marker + ' PYTHON LOCATOR'):
                 text.index('# END ' + marker + ' PYTHON LOCATOR')]
    script = tmp_path / 'locator.sh'
    script.write_text('set -euo pipefail\nCUT_FAILURE_STATUS=2\n'
                      'die(){ echo "$*" >&2; exit 2; }\n' + block +
                      '\n"$PYTHON" -c \'import os,sys; assert os.path.samefile(sys.argv[1],os.environ["PYTHON"]); sys.stdout.write("child locator retained")\' "$GOOD"\n')
    env = dict(os.environ, PYTHON='python' if via_path else './alias/../bin/python',
               GOOD=str(good), PYTHONDONTWRITEBYTECODE='1')
    if via_path:
        env['PATH'] = 'alias/../bin:/usr/bin:/bin'
    process = subprocess.run(['/bin/bash', str(script)], cwd=caller, env=env,
                             capture_output=True, text=True, timeout=10)
    assert process.returncode == 0, process.stdout + process.stderr
    assert process.stdout == 'child locator retained'


@pytest.mark.parametrize('via_path', [False, True])
def test_workflow_resolver_keeps_selected_executable(monkeypatch, selected_path, via_path):
    caller, good = selected_path
    context = dict(os=os, Path=Path, shutil=shutil)
    tree = ast.parse((ROOT / 'tools/_release_validation.py').read_text())
    nodes = [node for node in tree.body if getattr(node, 'name', '') in
             {'ValidationRefused', 'resolve_interpreter'}]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<bound-resolver>', 'exec'), context)
    monkeypatch.chdir(caller)
    if via_path:
        monkeypatch.setenv('PATH', 'alias/../bin:/usr/bin:/bin')
    selected = context['resolve_interpreter']('python' if via_path else './alias/../bin/python')
    assert selected.is_absolute()
    assert os.path.samefile(selected, good)
    assert '..' in selected.parts

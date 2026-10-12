"""Synthetic executable launch checks; no external engines or biological inputs."""
from pathlib import Path
import json
import os
import shlex
import shutil
import subprocess
import sys

from ._python_fixture_launcher import write_python_fixture


def test_spaced_venv_and_shell_characters_preserve_invocation_arguments_and_status(tmp_path):
    # A real interpreter symlink in a minimal venv layout proves invocation is not resolved away.
    venv = tmp_path / "venv $(touch INJECTED) 'quote' `literal`"
    python = venv / "bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(Path(sys.executable).resolve())
    (venv / "pyvenv.cfg").write_text(
        f"home = {Path(sys.base_prefix) / 'bin'}\ninclude-system-site-packages = false\n"
        f"version = {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n")
    bins = tmp_path / "tool bins ' $"; bins.mkdir()
    body = ("from __future__ import annotations\nimport json,os,sys\n"
            "print(json.dumps({'argv':sys.argv[1:],'python':sys.executable,'prefix':sys.prefix,"
            "'sentinel':os.environ['FIXTURE_SENTINEL']}))\n"
            "sys.stderr.write('fixture stderr\\n')\nraise SystemExit(17)\n")
    launcher = write_python_fixture(bins / "fixture tool", body, python=python)
    caller = tmp_path / "unrelated cwd"; caller.mkdir()
    arguments = ["two words", "", "literal ' $ ` chars", "--option=x y"]
    env = dict(os.environ, FIXTURE_SENTINEL="inherited value")
    result = subprocess.run([str(launcher), *arguments], cwd=caller, env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 17, result.stdout + result.stderr
    assert json.loads(result.stdout) == {'argv':arguments,'python':str(python),
                                        'prefix':str(venv),'sentinel':'inherited value'}
    assert result.stderr == 'fixture stderr\n'
    assert not (caller / "INJECTED").exists()
    assert shlex.quote(str(python)) in launcher.read_text()
    assert launcher.with_name(launcher.name + ".fixture.py").read_text() == body


def test_path_override_and_forced_primary_failure_remain_exact(tmp_path):
    bins = tmp_path / "fake bins"; bins.mkdir()
    # Same forced-renderer failure + exact interpreter delegation as the PDF fixture.
    body = ("import os,sys\n"
            "if len(sys.argv)>1 and sys.argv[1].endswith('render_deliverable_pdf.py'):raise SystemExit(1)\n"
            f"os.execv({sys.executable!r}, [{sys.executable!r}]+sys.argv[1:])\n")
    launcher = write_python_fixture(bins / "python3", body)
    env = dict(os.environ, PATH=str(bins)+os.pathsep+os.environ.get('PATH',''))
    failed = subprocess.run(['python3', str(tmp_path/'render_deliverable_pdf.py')], env=env,
                            capture_output=True, text=True, timeout=20)
    assert failed.returncode == 1 and failed.stdout == '' and failed.stderr == ''
    script = tmp_path / "other script.py"
    script.write_text("import json,sys\nprint(json.dumps({'argv':sys.argv[1:],'python':sys.executable,'prefix':sys.prefix}))\n")
    result = subprocess.run(['python3', str(script), 'argument with spaces'], env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'argv':['argument with spaces'], 'python':sys.executable,
                                        'prefix':sys.prefix}
    launcher.unlink()
    assert launcher.with_name(launcher.name + '.fixture.py').is_file()
    assert shutil.which('python3', path=str(bins)) is None

"""Catch host-specific temporary roots and unguarded sandbox launches before CI."""
from pathlib import Path
import ast
import os
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_TMP = "/" + "private/tmp"
SANDBOX = "sandbox" + "-exec"


def portability_violations(text, suffix=".py"):
    violations = []
    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        if PRIVATE_TMP in line:
            violations.append((number, "host-specific temporary root"))
    if suffix != ".py":
        for number, line in enumerate(lines, 1):
            if SANDBOX in line and not line.lstrip().startswith("#"):
                nearby = "\n".join(lines[max(0, number - 31):number + 10])
                if not any(guard in nearby for guard in ("sys.platform", "shutil.which", "command -v", "uname")):
                    violations.append((number, "unguarded sandbox command"))
        return violations
    tree = ast.parse(text)
    for node in ast.walk(tree):
        # Command lists, including assignments subsequently passed to subprocess.
        command_list = isinstance(node, (ast.List, ast.Tuple)) and any(
            isinstance(value, ast.Constant) and value.value == SANDBOX for value in ast.walk(node))
        command_string = (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                          and node.func.attr in {"run", "Popen", "call", "check_call", "check_output", "system"}
                          and node.args and isinstance(node.args[0], ast.Constant)
                          and isinstance(node.args[0].value, str) and SANDBOX in node.args[0].value)
        if not command_list and not command_string:
            continue
        nearby = "\n".join(lines[max(0, node.lineno - 31):node.lineno + 10])
        if not re.search(r"(?:if |require\().*(?:sys\.platform|shutil\.which)|=\s*admit_sandbox\(", nearby):
            violations.append((node.lineno, "unguarded sandbox command"))
    return violations


def test_test_and_tool_sources_are_portable():
    offenders = []
    for directory in ("tests", "tools", "deliverable_tools", "bundle_support"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.suffix in {".py", ".sh", ".R"} and path.is_file():
                offenders.extend((str(path.relative_to(ROOT)), line, reason)
                                 for line, reason in portability_violations(path.read_text(), path.suffix))
    assert not offenders, offenders


@pytest.mark.parametrize("text", [
    'root = ' + repr(PRIVATE_TMP),
    'subprocess.run([' + repr(SANDBOX) + ', "-f", profile])',
    'subprocess.run(' + repr(SANDBOX + ' -f profile') + ', shell=True)',
    'command = [shutil.which(' + repr(SANDBOX) + '), "-f", profile]',
])
def test_guard_rejects_regressions(text):
    assert portability_violations(text)


def test_guard_accepts_guarded_sandbox():
    text = 'if sys.platform == "darwin" and shutil.which(' + repr(SANDBOX) + '):\n'
    text += '    subprocess.run([' + repr(SANDBOX) + ', "-f", profile])\n'
    assert not portability_violations(text)


@pytest.mark.parametrize("tool", ["build_placement_panel_inputs.py", "placement_display.py"])
def test_installed_mamey_does_not_hide_tools_package(tmp_path, tool):
    # A separate import parent mimics pip-installed mamey without exposing tools.
    installed = tmp_path / "installed"
    installed.mkdir()
    (installed / "mamey").symlink_to(ROOT / "mamey", target_is_directory=True)
    script = ROOT / "tools" / tool
    code = """
import runpy, sys
from pathlib import Path
root, installed, script = map(Path, sys.argv[1:])
sys.path = [str(installed), str(root / 'tools')] + [p for p in sys.path if p and Path(p).resolve() != root]
import mamey.csv_safety
assert str(root) not in sys.path
runpy.run_path(str(script), run_name='portability_probe')
from tools import graft_integrity, _placement_report_metadata
"""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    result = subprocess.run([sys.executable, "-c", code, str(ROOT), str(installed), str(script)],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr

"""v9.7.361 (R3): bundle hooks must be workspace-portable.

The .356 cut shipped 23 hooks with a changelog line claiming they carried "no workspace/collection
specifics". That claim was false and was corrected at that seal: 13 of them hardcoded the authoring
machine path, so "a new user loads the complete guardrail set straight from the bundle" could not
work. This pins the fix.

Contract: every hook resolves its workspace root through $SAPOTE_WORKSPACE_ROOT, defaulting to the
original path so existing setups are unaffected. No hook may carry a BARE hardcoded path.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
import re as _re
from tests.conftest import hermetic_env  # v9.7.404 bytecode-leak fix
HARDCODED = _re.compile(r"/Users/[^/]+/|/home/[^/]+/")  # any personal home, name-free
ENV_VAR = "SAPOTE_WORKSPACE_ROOT"


def _hook_files():
    if not HOOKS.is_dir():
        pytest.skip("hooks/ not present in this tier")
    return [p for p in sorted(HOOKS.iterdir())
            if p.is_file() and p.suffix in {".sh", ".py"}]


def test_hooks_exist():
    assert _hook_files(), "no hooks found"


def test_no_hook_carries_a_bare_hardcoded_workspace_path():
    """A hardcoded path is permitted ONLY as the default of the env lookup."""
    offenders = []
    for p in _hook_files():
        text = p.read_text(errors="replace")
        if not HARDCODED.search(text):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if HARDCODED.search(line) and ENV_VAR not in line:
                offenders.append(f"{p.name}:{i}: {line.strip()[:90]}")
    assert not offenders, "bare hardcoded workspace path in hook(s):\n" + "\n".join(offenders)


def test_every_path_bearing_hook_honours_the_env_var():
    for p in _hook_files():
        text = p.read_text(errors="replace")
        if HARDCODED.search(text):
            assert ENV_VAR in text, f"{p.name} carries a workspace path but ignores ${ENV_VAR}"


def test_default_is_backward_compatible():
    """Unset env -> the original path, so an existing workspace keeps working unchanged."""
    probe = 'ROOT="${SAPOTE_WORKSPACE_ROOT:-/generic/default}"; printf %s "$ROOT"'
    out = subprocess.run(["bash", "-c", probe], capture_output=True, text=True,
                         env=hermetic_env(PATH="/usr/bin:/bin")).stdout
    assert out == "/generic/default"


def test_env_var_actually_overrides():
    probe = 'ROOT="${SAPOTE_WORKSPACE_ROOT:-/generic/default}"; printf %s "$ROOT"'
    out = subprocess.run(["bash", "-c", probe], capture_output=True, text=True,
                         env=hermetic_env(**{"PATH": "/usr/bin:/bin", ENV_VAR: "/srv/lab/sapote"})).stdout
    assert out == "/srv/lab/sapote"


def test_all_hooks_are_syntactically_valid():
    """A guardrail that cannot parse is not a guardrail."""
    bad = []
    for p in _hook_files():
        if p.suffix == ".sh":
            proc = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
            r = None if proc.returncode == 0 else (proc.stderr or "bash -n failed")
        else:
            # v9.7.404 (CLAUDE_404 bytecode leak, class A): this is a SYNTAX CHECK, like its
            # `bash -n` sibling branch. `python -m py_compile` WRITES __pycache__/*.pyc by design
            # and is not governed by -B or PYTHONDONTWRITEBYTECODE (they govern import caching,
            # not explicit compilation) -- it wrote 53 .pyc into the tree per full-suite run.
            # In-process compile() gives the same interpreter, same verdict, no subprocess, no
            # bytecode. tests/test_hermetic_env_guard_v97404.py forbids -m py_compile in tests/.
            try:
                compile(p.read_text(encoding="utf-8"), str(p), "exec")
                r = None
            except SyntaxError as exc:
                r = exc
        if r is not None:
            bad.append(f"{p.name}: {str(r).strip()[:120]}")
    assert not bad, "hook syntax errors:\n" + "\n".join(bad)


def test_no_real_collection_strain_id_in_hook_examples():
    """.356 finding: bgc_node_name_guard.sh used a real cohort strain in an example string.

    Example/help text should use a synthetic placeholder, independent of the AS-disclosure policy.
    """
    offenders = []
    for p in _hook_files():
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            for m in re.finditer(r"\bAS-(\d{2,4})\b", line):
                num = int(m.group(1))
                if not (900 <= num <= 999) and num != 48:   # synthetic band + public enterocin
                    offenders.append(f"{p.name}:{i}: {m.group(0)}")
    assert not offenders, "real collection strain id in hook text:\n" + "\n".join(offenders)

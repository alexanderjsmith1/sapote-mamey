"""v9.7.363: workspace-path portability across the WHOLE tree, plus public-repo hygiene.

.361 fixed hooks/ (13 files). .363 finishes the job: deliverable_tools/ (27 files) plus the
stragglers in tests/, tools/ and mamey/. The contract is unchanged — resolve through an env var,
default to the original path so existing setups are untouched — but it now holds everywhere, which
is what the GitHub release actually needs. Publishing a bare `/Users/<name>/...` exposes a username
and a private folder layout.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARDCODED = "/Users/<user>"
ENV_OK = ("SAPOTE_WORKSPACE_ROOT", "MAMEY_DATA_ROOT", "SAPOTE_ROOT", "CLAUDE_PROJECT_DIR")

# The single documented exception: this tool's job is to DETECT workspace paths leaking into Mode B
# cards, so its patterns must stay literal. Parametrising them would disable the guard.
DETECTION_PATTERN_FILES = {
    "tools/audit_modeb_support_card.py",
    "tests/test_audit_modeb_support_card.py",
    # The portability guard itself must contain the literal in order to search for it.
    "tests/test_workspace_path_portability.py",
    # v9.7.370: the hook-body portabilizer REWRITES the literal behind the env nesting, so its
    # search/replace pattern must itself stay literal (same class as the audit tool above).
    "sapote_hooks/portabilize_hook_bodies.py",
}

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}


def _code_files():
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in {".py", ".sh"}:
            continue
        if any(d in SKIP_DIRS for d in p.parts):
            continue
        yield p


def test_no_bare_workspace_path_in_code():
    """Every workspace path must sit behind an env lookup, not be hardcoded bare."""
    offenders = []
    for p in _code_files():
        rel = p.relative_to(ROOT).as_posix()
        if rel in DETECTION_PATTERN_FILES:
            continue
        text = p.read_text(errors="replace")
        if HARDCODED not in text:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if HARDCODED in line and not any(e in line for e in ENV_OK):
                offenders.append(f"{rel}:{i}: {line.strip()[:90]}")
    assert not offenders, (
        "bare hardcoded workspace path (publishing this exposes a username and private "
        "folder layout):\n" + "\n".join(offenders)
    )


def test_detection_pattern_exception_is_documented():
    """The exception must be justified in the file, so it is not mistaken for a miss."""
    p = ROOT / "tools/audit_modeb_support_card.py"
    if not p.exists():
        pytest.skip("audit_modeb_support_card.py not in this tier")
    assert "DETECTION PATTERNS" in p.read_text(errors="replace")


def test_env_override_actually_works():
    probe = 'import os; print(os.environ.get("SAPOTE_WORKSPACE_ROOT", "/Users/<user>/<workspace>"))'
    env = dict(os.environ); env["SAPOTE_WORKSPACE_ROOT"] = "/srv/lab/sapote"
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=env).stdout.strip()
    assert out == "/srv/lab/sapote"


def test_default_is_backward_compatible():
    probe = 'import os; print(os.environ.get("SAPOTE_WORKSPACE_ROOT", "/Users/<user>/<workspace>"))'
    env = {k: v for k, v in os.environ.items() if k != "SAPOTE_WORKSPACE_ROOT"}
    env.setdefault("PATH", "/usr/bin:/bin")
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=env).stdout.strip()
    assert out == "/Users/<user>/<workspace>"


def test_deliverable_tools_all_parse():
    """A genericisation pass that breaks a script is worse than the path it removed."""
    bad = []
    d = ROOT / "deliverable_tools"
    if not d.is_dir():
        pytest.skip("deliverable_tools/ not in this tier")
    for p in sorted(d.iterdir()):
        if p.suffix == ".py":
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
        elif p.suffix == ".sh":
            proc = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
            r = None if proc.returncode == 0 else (proc.stderr or "bash -n failed")
        else:
            continue
        if r is not None:
            bad.append(f"{p.name}: {str(r).strip()[:120]}")
    assert not bad, "syntax errors after path genericisation:\n" + "\n".join(bad)


# --- public-repo hygiene (v9.7.363) -------------------------------------------------------------

def test_gitignore_present_and_covers_the_obvious():
    gi = ROOT / ".gitignore"
    if not gi.exists():
        pytest.skip(".gitignore not in this tier")
    text = gi.read_text()
    for pat in ("__pycache__", ".pytest_cache", ".DS_Store"):
        assert pat in text, f".gitignore missing {pat!r}"


def test_ci_workflow_present_and_runs_the_real_gates():
    wf = ROOT / ".github/workflows/ci.yml"
    if not wf.exists():
        pytest.skip("CI workflow not in this tier")
    text = wf.read_text()
    assert "pytest -q" in text and "pytest tests/" not in text, "CI must use the configured full scope"
    import tomllib
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert set(config["tool"]["pytest"]["ini_options"]["testpaths"]) == {"tests", "tools", "deliverable_tools"}
    for gate in ("sync_version.py --check", "verify_release_identity.py",
                 "check_release_manifest.py", "repo_health.py --strict"):
        assert gate in text, f"CI should run the {gate} gate"


def test_zip_hygiene_allows_exactly_the_ci_dotfiles():
    """Widening ALLOWED_HIDDEN is deliberate and must stay narrow."""
    sys.path.insert(0, str(ROOT / "tools"))
    import preflight_zip_hygiene as pzh
    assert ".gitignore" in pzh.ALLOWED_HIDDEN
    assert ".github" in pzh.ALLOWED_HIDDEN
    # the gate must still reject arbitrary hidden entries — that is what caught _CANDIDATE_NOTES
    assert ".fullsuite_green" not in pzh.ALLOWED_HIDDEN
    assert len(pzh.ALLOWED_HIDDEN) <= 6, "ALLOWED_HIDDEN is drifting wide; keep it minimal"


def test_detection_pattern_exemptions_are_not_stale():
    """An exemption for a file that no longer contains the literal is a standing free pass.

    v9.7.421 (BC2): 6 of the 10 entries were stale — the guard SKIPS an exempted file entirely
    (`if rel in DETECTION_PATTERN_FILES: continue`), so an entry that no longer needs the exemption
    silently removes that file from the check forever. Two carried a justification that had become
    factually wrong: mamey/workspace_root.py and its test were exempted as "necessarily hold the
    literal" while containing zero occurrences of it.
    """
    stale = []
    for rel in sorted(DETECTION_PATTERN_FILES):
        p = ROOT / rel
        if not p.exists():
            stale.append(f"{rel} (file does not exist)")
            continue
        if HARDCODED not in p.read_text(errors="replace"):
            stale.append(f"{rel} (no longer contains the literal)")
    assert not stale, (
        "stale detection-pattern exemption(s) — each one permanently removes a file from the "
        "bare-workspace-path check for no reason:\n" + "\n".join(stale))

#!/usr/bin/env python3
"""TESTS — CLAUDE_409_identity_verify_content.

The hollow-integrity theme, proven with the bundle's own tools: when a source file is edited but
every version/engine/build STRING stays current, `tools/check_release_manifest.py` (checksum-based)
correctly FAILS, yet `tools/verify_release_identity.py` still PASSES — because it only cross-checked
strings, never file content. That is a false "identity-verified" on a modified tree.

This patch folds the checksum-manifest verdict into the identity gate. These tests demonstrate,
end to end against a small copy of actual identity probes and owner tools, made
self-consistent by the real disposable integrity phase (never the candidate):

  * FAIL-BEFORE  — the UNPATCHED identity gate PASSES (exit 0) on a tree with a benign in-manifest
                   file edited (version strings intact). The leak.
  * PASS-AFTER   — the PATCHED identity gate FAILS (exit 1) on the same tree, with a DISTINCT
                   `content:` finding naming the drifted file.
  * NO-FALSE-POS — the PATCHED gate still PASSES on the untouched pristine tree.
  * ROBUSTNESS   — run from an unrelated cwd with no --root, the UNPATCHED gate crashes with a raw
                   FileNotFoundError; the PATCHED gate resolves a sane default and never traces back.
  * CLEAR-ERROR  — pointed at a directory that is not a bundle root, the PATCHED gate exits 2 with a
                   plain-language message, not a traceback.

Actual probes and validators are copied byte-for-byte from the selected source. If the historical
lane patch is supplied, it is applied with `patch -p1 --fuzz=0` before fixture integrity generation.
Pristine here means owner-bound disposable inputs, not a claim about candidate release freshness.

Run:  pytest test_identity_verify_content.py -q
The default source is this test's containing bundle; an explicit SAPOTE_BUNDLE_ROOT can select
a historical source. Ambient sibling bundles never silently change the validator under test.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from ._python_fixture_launcher import write_python_fixture

HERE = Path(__file__).resolve().parent
PATCH = HERE / "CLAUDE_409_identity_verify_content.patch"
IDENTITY_FILES = (
    "AGENTS.md", "CLAUDE.md", "README.md", "TAG", "BUILD_STAMP.txt", "pyproject.toml",
    "mamey/__init__.py", "mamey/console.py", "tools/verify_release_identity.py",
    "tools/check_release_manifest.py", "tools/tracked_file_policy.py", "tools/_console.py",
    "tools/release_cut.sh", "tools/cut_preflight.sh",
)
PROTECTED_GENERATED = (
    "TIER_MANIFEST.txt", "SOURCE_CHECKSUMS_SHA256.txt", "RELEASE_MANIFEST.md",
    "docs/MAINTENANCE_INVENTORY.generated.json", "docs/MAINTENANCE_INVENTORY.generated.md",
)


def _bindings(root, names):
    return {name: (hashlib.sha256((root / name).read_bytes()).hexdigest(),
                   stat.S_IMODE((root / name).stat().st_mode))
            for name in names if (root / name).is_file()}


def _copy_identity_source(source, dest):
    """Copy actual identity inputs, not genomes, archives or stale generated proofs."""
    before = _bindings(source, (*IDENTITY_FILES, *PROTECTED_GENERATED))
    for name in IDENTITY_FILES:
        original = source / name
        assert original.is_file() and not any(p.is_symlink() for p in (original, *original.parents))
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
    assert _bindings(dest, IDENTITY_FILES) == _bindings(source, IDENTITY_FILES)
    assert _bindings(source, (*IDENTITY_FILES, *PROTECTED_GENERATED)) == before
    controls = dest.parent / (dest.name + "-owner-controls")
    controls.mkdir(exist_ok=True)
    (controls / "copy-provenance.json").write_text(json.dumps({
        "source_root": str(source), "copied_identity_files": list(IDENTITY_FILES),
        "source_sha256_and_modes": before,
    }, indent=2), encoding="utf-8")
    return before


def _refresh_integrity(tree):
    """Invoke the existing integrity-only owner; the package branch stays unselected."""
    control = tree.parent / (tree.name + "-owner-controls")
    control.mkdir(exist_ok=True)
    invocation = control / "bin" / "python3"
    invocation.parent.mkdir(exist_ok=True)
    write_python_fixture(invocation,
                         "import os, sys\nos.execv(sys.executable, [sys.executable, *sys.argv[1:]])\n")
    marker = (tree / "BUILD_STAMP.txt").read_text(encoding="utf-8")
    version = re.search(r"(?m)^version=(\S+)$", marker).group(1)
    stamp = re.search(r"(?m)^build=(\S+)$", marker).group(1)
    match = re.fullmatch(r"(\d{8})v" + re.escape(version.replace(".", "")) + r"([a-z])", stamp)
    assert match, "fixture stamp must be reproducible without changing identity markers"
    out = control / "must-remain-absent-output"
    assert not os.path.lexists(out)
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith("RELEASE_") or key in {"PYTEST_LOG", "PYTEST_RECEIPT", "PYTEST_RECEIPT_SHA256"}:
            env.pop(key)
    env.update(RELEASE_WORKFLOW_PHASE="integrity", RELEASE_DATE=match[1],
               PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(tree),
               PATH=str(invocation.parent) + os.pathsep + os.environ.get("PATH", ""))
    command = ["/bin/bash", str(tree / "tools/release_cut.sh"), version, str(tree), str(out), match[2]]
    result = subprocess.run(command, env=env, cwd=tree, text=True, capture_output=True, timeout=60)
    attempt = len(list(control.glob("integrity-*.json")))
    (control / f"integrity-{attempt}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    (control / f"integrity-{attempt}.json").write_text(json.dumps({
        "argv": command, "exit_code": result.returncode,
        "owner_sha256": hashlib.sha256((tree / "tools/release_cut.sh").read_bytes()).hexdigest(),
        "interpreter_invocation": sys.executable, "outputs": _bindings(tree, PROTECTED_GENERATED),
    }, indent=2), encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not os.path.lexists(out), "integrity-only phase must never enter archive construction"
    manifest = _run(tree / "tools/check_release_manifest.py", "--root", str(tree), "--quiet")
    assert manifest.returncode == 0, manifest.stdout + manifest.stderr
    return _bindings(tree, ("TIER_MANIFEST.txt", "SOURCE_CHECKSUMS_SHA256.txt"))


def _find_bundle_root() -> Path:
    env = os.environ.get("SAPOTE_BUNDLE_ROOT")
    if env:
        p = Path(env).resolve()
        if (p / "tools" / "verify_release_identity.py").is_file():
            return p
        raise RuntimeError(f"SAPOTE_BUNDLE_ROOT={p} has no tools/verify_release_identity.py")
    # The loaded source is authority unless a caller explicitly selects another.
    return HERE.parent


def _run(script: Path, *args: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, "-B", str(script), *args],
        capture_output=True, text=True, cwd=str(cwd) if cwd else None,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )


@pytest.fixture(scope="session")
def bundle_root() -> Path:
    return _find_bundle_root()


@pytest.fixture(scope="session")
def patched_bundle(tmp_path_factory, bundle_root) -> Path:
    """Actual gate/tools copied, historically patched if supplied, then owner-bound."""
    dest = tmp_path_factory.mktemp("patched_bundle") / "bundle"
    original = _copy_identity_source(bundle_root, dest)
    if PATCH.is_file():
        if shutil.which("patch") is None:
            pytest.skip("`patch` binary not available")
        r = subprocess.run(["patch", "-p1", "--fuzz=0", "-i", str(PATCH)],
                           cwd=str(dest), capture_output=True, text=True)
        assert r.returncode == 0, f"patch failed to apply cleanly:\n{r.stdout}\n{r.stderr}"
    _refresh_integrity(dest)
    yield dest
    assert _bindings(bundle_root, (*IDENTITY_FILES, *PROTECTED_GENERATED)) == original


@pytest.fixture()
def clean_tree(tmp_path, bundle_root) -> Path:
    """Actual selected inputs, made pristine by their real disposable owner."""
    dest = tmp_path / "tree"
    original = _copy_identity_source(bundle_root, dest)
    _refresh_integrity(dest)
    yield dest
    assert _bindings(bundle_root, (*IDENTITY_FILES, *PROTECTED_GENERATED)) == original


def _identity(bundle: Path) -> Path:
    return bundle / "tools" / "verify_release_identity.py"


# --------------------------------------------------------------------------------------------------
# The core demonstration: a content edit that leaves every version string current.
# --------------------------------------------------------------------------------------------------
def test_content_edit_flips_identity_fail_before_pass_after(patched_bundle, clean_tree, bundle_root):
    patched = _identity(patched_bundle)
    unpatched = _identity(bundle_root)

    # No false positive: the patched gate passes on the untouched tree.
    base = _run(patched, "--root", str(clean_tree), "--strict-membership")
    assert base.returncode == 0, f"patched gate should PASS on pristine tree:\n{base.stdout}\n{base.stderr}"
    assert "ADVISORY:" not in base.stdout
    pristine_integrity = _bindings(clean_tree, ("TIER_MANIFEST.txt", "SOURCE_CHECKSUMS_SHA256.txt"))
    assert _refresh_integrity(clean_tree) == pristine_integrity
    pristine_probes = _bindings(clean_tree, IDENTITY_FILES)

    # Edit a benign, in-manifest source file. It carries no version/engine/build string, so every
    # identity STRING check still passes — only the bytes (and thus the checksum) change.
    target = clean_tree / "mamey" / "console.py"
    assert target.is_file()
    original_bytes = target.read_bytes()
    target.write_text(target.read_text(encoding="utf-8") + "\n# benign edit\n", encoding="utf-8")

    # FAIL-BEFORE: the unpatched gate still reports identity PASS on the modified tree (the leak).
    # Only meaningful when an unpatched sibling bundle exists; in a bundle that already carries the
    # lane, bundle_root IS the patched gate and (correctly) fails here.
    if PATCH.is_file():
        before = _run(unpatched, "--root", str(clean_tree))
        assert before.returncode == 0, (
            "the UNPATCHED identity gate is expected to PASS here (string-only check) — that is the "
            f"leak this lane closes:\n{before.stdout}\n{before.stderr}"
        )
        assert "PASS" in before.stdout

    # PASS-AFTER: the patched gate FAILS, with a distinct content: finding naming the drifted file.
    after = _run(patched, "--root", str(clean_tree))
    assert after.returncode == 1, f"patched gate must FAIL on the modified tree:\n{after.stdout}\n{after.stderr}"
    assert "FAIL" in after.stdout
    assert "content:" in after.stdout, f"failure must be a distinct content finding:\n{after.stdout}"
    assert "console.py" in after.stdout, f"the drifted file should be named:\n{after.stdout}"
    target.write_bytes(original_bytes)
    assert _refresh_integrity(clean_tree) == pristine_integrity
    repaired = _run(patched, "--root", str(clean_tree), "--strict-membership")
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    assert "PASS" in repaired.stdout and "ADVISORY:" not in repaired.stdout
    assert _bindings(clean_tree, IDENTITY_FILES) == pristine_probes


def test_content_failure_is_distinct_in_json(patched_bundle, clean_tree):
    import json
    patched = _identity(patched_bundle)
    baseline = _run(patched, "--root", str(clean_tree), "--json", "--strict-membership")
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    assert json.loads(baseline.stdout)["status"] == "PASS"
    original = (clean_tree / "mamey/console.py").read_bytes()
    (clean_tree / "mamey" / "console.py").write_text(
        (clean_tree / "mamey" / "console.py").read_text(encoding="utf-8") + "\n# edit\n",
        encoding="utf-8",
    )
    r = _run(patched, "--root", str(clean_tree), "--json")
    assert r.returncode == 1, r.stdout
    payload = json.loads(r.stdout)
    assert payload["status"] == "FAIL"
    assert any(e.startswith("content:") for e in payload["errors"]), payload["errors"]
    assert any("console.py" in e for e in payload["errors"])
    (clean_tree / "mamey/console.py").write_bytes(original)
    _refresh_integrity(clean_tree)
    repaired = _run(patched, "--root", str(clean_tree), "--json", "--strict-membership")
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    assert json.loads(repaired.stdout)["status"] == "PASS"


# --------------------------------------------------------------------------------------------------
# Robustness bug: default root = CWD raised a raw FileNotFoundError when run from elsewhere.
# --------------------------------------------------------------------------------------------------
@pytest.mark.skipif(not PATCH.is_file(), reason="fail-before probe needs the unpatched sibling bundle (lane already folded here)")
def test_run_from_elsewhere_unpatched_crashes(bundle_root, tmp_path):
    foreign = tmp_path / "elsewhere"
    foreign.mkdir()
    r = _run(_identity(bundle_root), cwd=foreign)  # no --root -> old default "."
    assert r.returncode != 0
    assert "FileNotFoundError" in r.stderr, (
        f"the unpatched gate is expected to crash with a raw FileNotFoundError:\n{r.stderr}"
    )


def test_run_from_elsewhere_patched_no_crash(patched_bundle, tmp_path):
    foreign = tmp_path / "elsewhere"
    foreign.mkdir()
    r = _run(_identity(patched_bundle), cwd=foreign)  # no --root -> sane default bundle root
    assert "Traceback" not in r.stderr, f"patched gate must not traceback:\n{r.stderr}"
    assert "FileNotFoundError" not in r.stderr, f"patched gate must not raise FileNotFoundError:\n{r.stderr}"
    assert "release identity:" in r.stdout, f"patched gate should print a clean verdict:\n{r.stdout}\n{r.stderr}"
    assert r.returncode in (0, 1), f"expected a clean pass/fail verdict, got {r.returncode}"


def test_nonbundle_root_clear_error(patched_bundle, tmp_path):
    notbundle = tmp_path / "notbundle"
    notbundle.mkdir()
    r = _run(_identity(patched_bundle), "--root", str(notbundle))
    assert r.returncode == 2, f"expected exit 2 for a non-bundle root:\n{r.stdout}\n{r.stderr}"
    assert "Traceback" not in r.stderr, r.stderr
    assert "not a bundle root" in r.stdout, f"expected a clear message:\n{r.stdout}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

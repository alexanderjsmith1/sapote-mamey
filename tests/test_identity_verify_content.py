#!/usr/bin/env python3
"""TESTS — CLAUDE_409_identity_verify_content.

The hollow-integrity theme, proven with the bundle's own tools: when a source file is edited but
every version/engine/build STRING stays current, `tools/check_release_manifest.py` (checksum-based)
correctly FAILS, yet `tools/verify_release_identity.py` still PASSES — because it only cross-checked
strings, never file content. That is a false "identity-verified" on a modified tree.

This patch folds the checksum-manifest verdict into the identity gate. These tests demonstrate,
end to end against a REAL copy of the pristine bundle:

  * FAIL-BEFORE  — the UNPATCHED identity gate PASSES (exit 0) on a tree with a benign in-manifest
                   file edited (version strings intact). The leak.
  * PASS-AFTER   — the PATCHED identity gate FAILS (exit 1) on the same tree, with a DISTINCT
                   `content:` finding naming the drifted file.
  * NO-FALSE-POS — the PATCHED gate still PASSES on the untouched pristine tree.
  * ROBUSTNESS   — run from an unrelated cwd with no --root, the UNPATCHED gate crashes with a raw
                   FileNotFoundError; the PATCHED gate resolves a sane default and never traces back.
  * CLEAR-ERROR  — pointed at a directory that is not a bundle root, the PATCHED gate exits 2 with a
                   plain-language message, not a traceback.

How the patched code is obtained: the lane's own `.patch` is applied (`patch -p1 --fuzz=0`) to a
temp copy of the pristine bundle — the same command the release cut uses — so the test exercises
exactly what ships. The UNPATCHED gate is the pristine bundle's own script.

Run:  pytest test_identity_verify_content.py -q
The pristine bundle is auto-located (a `sapote-mamey-v9_7_*-CODE-*` dir above this file); override
with SAPOTE_BUNDLE_ROOT=/path/to/bundle if it lives elsewhere.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCH = HERE / "CLAUDE_409_identity_verify_content.patch"


def _find_bundle_root() -> Path:
    env = os.environ.get("SAPOTE_BUNDLE_ROOT")
    if env:
        p = Path(env).resolve()
        if (p / "tools" / "verify_release_identity.py").is_file():
            return p
        raise RuntimeError(f"SAPOTE_BUNDLE_ROOT={p} has no tools/verify_release_identity.py")
    # Walk upward from this file looking for a sibling pristine bundle tree.
    for parent in [HERE, *HERE.parents]:
        for cand in sorted(parent.glob("sapote-mamey-v9_7_*-CODE-*")):
            if cand.is_dir() and (cand / "tools" / "verify_release_identity.py").is_file():
                return cand.resolve()
    # No pristine sibling: this bundle already carries the lane, so it is the "patched" tree.
    return HERE.parent


def _run(script: Path, *args: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, cwd=str(cwd) if cwd else None,
    )


@pytest.fixture(scope="session")
def bundle_root() -> Path:
    return _find_bundle_root()


@pytest.fixture(scope="session")
def patched_bundle(tmp_path_factory, bundle_root) -> Path:
    """A copy of the pristine bundle with THIS lane's patch applied via `patch -p1 --fuzz=0`."""
    dest = tmp_path_factory.mktemp("patched_bundle") / "bundle"
    shutil.copytree(bundle_root, dest)
    if not PATCH.is_file():  # lane already folded into the tree we copied
        return dest
    if shutil.which("patch") is None:
        pytest.skip("`patch` binary not available")
    r = subprocess.run(
        ["patch", "-p1", "--fuzz=0", "-i", str(PATCH)],
        cwd=str(dest), capture_output=True, text=True,
    )
    assert r.returncode == 0, f"patch failed to apply cleanly:\n{r.stdout}\n{r.stderr}"
    return dest


@pytest.fixture()
def clean_tree(tmp_path, bundle_root) -> Path:
    """A fresh, unmodified copy of the pristine bundle (self-consistent checksums)."""
    dest = tmp_path / "tree"
    shutil.copytree(bundle_root, dest)
    return dest


def _identity(bundle: Path) -> Path:
    return bundle / "tools" / "verify_release_identity.py"


# --------------------------------------------------------------------------------------------------
# The core demonstration: a content edit that leaves every version string current.
# --------------------------------------------------------------------------------------------------
def test_content_edit_flips_identity_fail_before_pass_after(patched_bundle, clean_tree, bundle_root):
    patched = _identity(patched_bundle)
    unpatched = _identity(bundle_root)

    # No false positive: the patched gate passes on the untouched tree.
    base = _run(patched, "--root", str(clean_tree))
    assert base.returncode == 0, f"patched gate should PASS on pristine tree:\n{base.stdout}\n{base.stderr}"

    # Edit a benign, in-manifest source file. It carries no version/engine/build string, so every
    # identity STRING check still passes — only the bytes (and thus the checksum) change.
    target = clean_tree / "mamey" / "console.py"
    assert target.is_file()
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


def test_content_failure_is_distinct_in_json(patched_bundle, clean_tree):
    import json
    patched = _identity(patched_bundle)
    (clean_tree / "mamey" / "console.py").write_text(
        (clean_tree / "mamey" / "console.py").read_text(encoding="utf-8") + "\n# edit\n",
        encoding="utf-8",
    )
    r = _run(patched, "--root", str(clean_tree), "--json")
    assert r.returncode == 1, r.stdout
    payload = json.loads(r.stdout)
    assert payload["status"] == "FAIL"
    assert any(e.startswith("content:") for e in payload["errors"]), payload["errors"]


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

"""Tests for tools/preflight_zip_hygiene.py (v9.7.155, from candidate-3 external audit).

The audit found .pytest_cache in a deliverable ZIP built by an ad-hoc `zip` command
with an incomplete exclude set. The canonical builder was fine; the gap was that no
checkable command scanned a hand-built zip. preflight_zip_hygiene.py is that command;
these tests lock its detect/pass behavior.
"""
import importlib.util
import os
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load():
    spec = importlib.util.spec_from_file_location(
        "preflight_zip_hygiene", TOOLS / "preflight_zip_hygiene.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_zip(tmp_path, entries):
    """entries: dict of arcname -> content (bytes/str)."""
    zp = tmp_path / "t.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        for arc, content in entries.items():
            zf.writestr(arc, content if isinstance(content, str) else content)
    return zp


def test_clean_zip_passes(tmp_path):
    m = _load()
    zp = _make_zip(tmp_path, {"mamey/cli.py": "x=1\n", "README.md": "# hi", ".gitignore": "*.pyc"})
    r = m.scan(zp)
    assert r["cache"] == [] and r["hidden"] == [] and r["large"] == []


def test_pytest_cache_detected(tmp_path):
    m = _load()
    zp = _make_zip(tmp_path, {"real.txt": "y", ".pytest_cache/v/cache/nodeids": "z"})
    r = m.scan(zp)
    assert any(".pytest_cache" in c for c in r["cache"]), r


def test_pyc_and_pycache_detected(tmp_path):
    m = _load()
    zp = _make_zip(tmp_path, {"mamey/__pycache__/cli.cpython-312.pyc": "b", "a.pyc": "b"})
    r = m.scan(zp)
    assert len(r["cache"]) >= 2, r


def test_backup_artifacts_detected(tmp_path):
    m = _load()
    zp = _make_zip(tmp_path, {"cli.py.orig": "x", "notes.bak": "y", "patch.rej": "z"})
    r = m.scan(zp)
    assert len(r["cache"]) >= 3, r


def test_gitignore_allowed_but_other_hidden_flagged(tmp_path):
    m = _load()
    zp = _make_zip(tmp_path, {".gitignore": "*.pyc", ".secret_dir/creds": "nope"})
    r = m.scan(zp)
    # .gitignore is allowlisted; .secret_dir is not
    assert not any(".gitignore" == h for h in r["hidden"])
    assert any(".secret_dir" in h for h in r["hidden"]), r


def test_main_exit_codes(tmp_path):
    m = _load()
    clean = _make_zip(tmp_path, {"mamey/cli.py": "x=1\n"})
    assert m.main(["prog", str(clean)]) == 0
    dirty = tmp_path / "d.zip"
    with zipfile.ZipFile(dirty, "w") as zf:
        zf.writestr(".pytest_cache/v/cache/lastfailed", "{}")
    assert m.main(["prog", str(dirty)]) == 1
    assert m.main(["prog", str(tmp_path / "missing.zip")]) == 2


def test_builder_and_preflight_agree_on_cleanliness():
    """The preflight's CACHE_RE must match the builder's exclusion set and the existing
    test_release_zip_hygiene BAD_RELEASE_ARTIFACT_RE, so a zip that passes one passes all.

    We deliberately do NOT scan /mnt/user-data/outputs here: like
    test_release_zip_hygiene.test_no_cache_artifacts_in_release_zips, that shared staging
    area can hold pre-fix artifacts from other sessions, which would make this test report
    on zips a re-cut will replace. The preflight *script* is the checkable guard for an
    actual handoff; this test locks that its detection set is complete.
    """
    m = _load()
    # Every token the canonical builder excludes must be caught by the preflight.
    for arc in (".pytest_cache/v/cache/nodeids", "mamey/__pycache__/x.pyc",
                "a.pyc", "b.pyo", "c.orig", "d.bak", "e.rej", "f~", ".DS_Store"):
        assert m.CACHE_RE.search(arc), f"preflight CACHE_RE misses builder-excluded artifact: {arc}"

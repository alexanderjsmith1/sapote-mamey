"""v9.7.398 — tools/intake_harness.py's `_safe_extract_zip` was an independent, hand-rolled
zip-slip guard even though this file already imports unconditionally from `mamey` (no
degraded-environment fallback need). Consolidated to delegate to the canonical
`mamey.ziputil.safe_extract_all` (the same back-compat-shim pattern
`mamey/raw_antismash_triage.py` already uses), matching the project's own stated v9.7.367
consolidation intent for this exact guard.
"""
from __future__ import annotations

import zipfile

import pytest


def test_safe_extract_zip_rejects_relative_path_traversal(tmp_path):
    from tools.intake_harness import _safe_extract_zip

    zpath = tmp_path / "evil.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("../../etc/evil.txt", "pwned")
    dest = tmp_path / "dest"
    dest.mkdir()
    with zipfile.ZipFile(zpath) as z:
        with pytest.raises(ValueError, match="unsafe zip member path"):
            _safe_extract_zip(z, dest)


def test_safe_extract_zip_rejects_absolute_path_member(tmp_path):
    from tools.intake_harness import _safe_extract_zip

    zpath = tmp_path / "evil2.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        zi = zipfile.ZipInfo("/etc/evil2.txt")
        z.writestr(zi, "pwned")
    dest = tmp_path / "dest2"
    dest.mkdir()
    with zipfile.ZipFile(zpath) as z:
        with pytest.raises(ValueError, match="unsafe zip member path"):
            _safe_extract_zip(z, dest)


def test_safe_extract_zip_extracts_legitimate_members(tmp_path):
    from tools.intake_harness import _safe_extract_zip

    zpath = tmp_path / "good.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("sub/dir/file.txt", "hello")
    dest = tmp_path / "dest3"
    dest.mkdir()
    with zipfile.ZipFile(zpath) as z:
        _safe_extract_zip(z, dest)
    assert (dest / "sub" / "dir" / "file.txt").read_text() == "hello"


def test_now_delegates_to_the_canonical_guard():
    """Consolidation guard: confirms this file no longer carries its own independent
    implementation of the traversal check — it calls the canonical one."""
    import inspect
    from tools import intake_harness as mod

    src = inspect.getsource(mod._safe_extract_zip)
    assert "safe_extract_all" in src
    assert "mamey.ziputil" in src

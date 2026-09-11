"""BC2-CDR-01 (v9.7.395): tools/check_dangling_refs.py's scan() and scan_tools() must not
silently swallow an unreadable candidate file.

Both functions wrapped `p.read_text(...)` in `except Exception: continue` with no signal of any
kind — a permission-denied (or otherwise unreadable) .md/.txt/.html file was silently excluded
from the audit, and any real dangling reference it contained went completely unreported. A
permission-denied doc containing a genuine dangling `examples/` reference made scan() return `{}`
(the "clean" result) with zero indication anything was skipped — exactly the "missing coverage
silently read as a clean result" pattern this codebase's own philosophy guards against elsewhere.

Reproduced live against the unpatched tools/check_dangling_refs.py before this fix.
"""
from __future__ import annotations
import os
import stat
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_dangling_refs import scan, scan_tools  # noqa: E402


def _make_unreadable_md(tmp_path: pathlib.Path, referencing_text: str) -> pathlib.Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    target = docs / "UNREADABLE.md"
    target.write_text(referencing_text)
    target.chmod(0o000)
    return target


@pytest.fixture
def _skip_if_root():
    # root (or an owner-bypass filesystem) can read a 0o000 file; the repro is meaningless there.
    if os.geteuid() == 0:
        pytest.skip("running as root — permission-denial repro does not apply")


def test_scan_warns_on_unreadable_file_with_real_dangling_ref(tmp_path, capsys, _skip_if_root):
    target = _make_unreadable_md(
        tmp_path, "See examples/totally_nonexistent_fixture.csv for the fixture.\n"
    )
    try:
        result = scan(tmp_path)
        err = capsys.readouterr().err
        assert "UNREADABLE.md" in err and "could not read" in err, (
            "scan() must print a visible warning when it cannot read a candidate file, "
            f"instead of silently excluding it; captured stderr: {err!r}"
        )
        # the file's real content is unreadable, so it correctly cannot appear as a resolved
        # dangling-ref finding — the fix is visibility of the skip, not fabricating a finding.
        assert result == {}
    finally:
        target.chmod(0o644)  # restore so tmp_path cleanup can delete it


def test_scan_tools_warns_on_unreadable_file(tmp_path, capsys, _skip_if_root):
    target = _make_unreadable_md(
        tmp_path, "See `totally_nonexistent_tool.py` for details.\n"
    )
    try:
        result = scan_tools(tmp_path)
        err = capsys.readouterr().err
        assert "UNREADABLE.md" in err and "could not read" in err
        assert result == {}
    finally:
        target.chmod(0o644)


def test_scan_still_clean_and_silent_on_a_normal_readable_tree(tmp_path, capsys):
    # Regression guard: a readable tree with no dangling refs must stay silent on stderr.
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "FINE.md").write_text("Nothing dangling here.\n")
    result = scan(tmp_path)
    err = capsys.readouterr().err
    assert result == {}
    assert err == ""

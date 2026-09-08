"""tests/test_409_cli_breakers.py — CLAUDE_409_cli_breakers lane.

Fail-before / pass-after coverage for the three real-run CLI breakers in
development/audit/AUDIT_cli_code_bugs.md (rows cli_pyswrd_swallow #1,
cli_positional_pkg_mangled #4, cli_reader_writes_into_seal #5).

These tests do NOT need a full sealed package: each pins the exact fixed code path.
"""
import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

import mamey  # noqa: F401
from mamey import compare, diamond_align, cli

_BUNDLE = Path(mamey.__file__).resolve().parent.parent


def _load_tool(name):
    path = _BUNDLE / "tools" / name
    spec = importlib.util.spec_from_file_location(name[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# Finding #1  cli_pyswrd_swallow  (mamey/compare.py, mamey/diamond_align.py)
# --------------------------------------------------------------------------- #
def test_aligner_backend_rejects_pyswrd_that_cannot_execute(monkeypatch):
    """PASS-AFTER: an importable-but-unexecutable pyswrd (the arm64 SIMD case) is NOT
    selected; the smoke align raises and _aligner_backend falls through.
    FAIL-BEFORE: import success alone returned 'pyswrd'."""
    fake = types.ModuleType("pyswrd")

    def _boom(*a, **k):
        raise RuntimeError("no supported SIMD backend available")

    fake.search = _boom
    monkeypatch.setitem(sys.modules, "pyswrd", fake)
    # force the diamond branch to say "unavailable" so we exercise the pyswrd path
    monkeypatch.setattr(diamond_align, "diamond_available", lambda: (False, "test: no diamond"))
    assert compare._aligner_backend() != "pyswrd"


def test_align_genes_falls_back_when_pyswrd_raises(monkeypatch):
    """PASS-AFTER: a runtime failure in the pyswrd backend degrades to Biopython instead of
    being masked as an empty (0-hit) result.
    FAIL-BEFORE: _align_pyswrd swallowed the error to {} and align_genes returned empty."""
    monkeypatch.setattr(compare, "_aligner_backend", lambda: "pyswrd")

    def _raise(*a, **k):
        raise RuntimeError("pyswrd alignment could not execute: RuntimeError: SIMD")

    sentinel = {"geneA": {"sseqid": "geneB", "pident": 88.0, "qcovhsp": 90.0,
                          "backend": "biopython"}}
    monkeypatch.setattr(compare, "_align_pyswrd", _raise)
    monkeypatch.setattr(compare, "_align_biopython", lambda q, r: sentinel)
    out = compare.align_genes_to_proteome([("geneA", "MKV")], [("geneB", "MKV")], threads=1)
    assert out == sentinel


def test_align_pyswrd_no_longer_swallows_execution_failure(monkeypatch):
    """PASS-AFTER: _align_pyswrd raises (does not return {}) when pyswrd.search blows up, so the
    caller can distinguish a broken backend from a genuine 0-hit result."""
    fake = types.ModuleType("pyswrd")
    def _boom_search(*a, **k):
        raise RuntimeError("no SIMD")
    # monkeypatch.setattr (auto-restored) instead of a raw `fake.search = lambda` attr stub,
    # which test_no_raw_module_stub_leaks_v97397.py forbids (leaks to later tests in the process).
    monkeypatch.setattr(fake, "search", _boom_search, raising=False)
    monkeypatch.setitem(sys.modules, "pyswrd", fake)
    with pytest.raises(Exception):
        compare._align_pyswrd([("q", "MKV")], [("t", "MKV")], threads=1)


def test_diamond_cli_probe_makes_a_path_binary_visible(monkeypatch):
    """PASS-AFTER: a `diamond` executable on PATH is detected even when the diamond4py binding
    is absent (the conda/Homebrew CLI the old check never saw).
    FAIL-BEFORE: diamond_cli_available did not exist and diamond_available only tried the import."""
    assert hasattr(diamond_align, "diamond_cli_available")
    monkeypatch.setattr(diamond_align.shutil, "which",
                        lambda name: "/opt/conda/bin/diamond" if name == "diamond" else None)
    # binding import will fail in this env; CLI presence must make it available
    ok, reason = diamond_align.diamond_available()
    assert ok is True
    assert "diamond CLI" in reason


# --------------------------------------------------------------------------- #
# Finding #4  cli_positional_pkg_mangled  (mamey/cli.py _d3_tool_command)
# --------------------------------------------------------------------------- #
def test_positional_package_not_char_iterated(tmp_path, capsys):
    """PASS-AFTER: `domain-reference <pkg>` (positional) reaches the tool with the WHOLE path as
    one --package value; the empty temp dir yields the tool's own 'no domains' exit 1.
    FAIL-BEFORE: the str positional was iterated per-character -> the tool's isdir check errored
    `not a directory: <first char>` and argparse raised SystemExit(2)."""
    pkg = tmp_path / "workspace_pkg"
    pkg.mkdir()
    rc = cli.main(["domain-reference", str(pkg)])
    assert rc == 1  # 'no domains found' — NOT a SystemExit(2) 'not a directory: w'
    err = capsys.readouterr().err
    assert "not a directory" not in err


# --------------------------------------------------------------------------- #
# Finding #5  cli_reader_writes_into_seal  (tools/*.py _reader_out_dir)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tool_name,suffix", [
    ("realistic_bgc_count.py", "_realistic_count"),
    ("build_novelty_shortlist.py", "_novelty_shortlist"),
    ("build_domain_reference.py", "_domain_reference"),
])
def test_reader_out_dir_defaults_outside_package(tool_name, suffix, tmp_path):
    """PASS-AFTER: with no --out the reader targets a SIBLING dir OUTSIDE the package, so it can
    never add an untracked file that breaks `mamey validate` checksum_integrity.
    FAIL-BEFORE: _reader_out_dir did not exist; the default was the package dir itself (inside)."""
    mod = _load_tool(tool_name)
    assert hasattr(mod, "_reader_out_dir")
    pkg = tmp_path / "AS40" / "package"
    pkg.mkdir(parents=True)
    got = Path(mod._reader_out_dir(None, str(pkg), suffix)).resolve()
    pkg_r = pkg.resolve()
    assert got != pkg_r
    assert pkg_r not in got.parents  # sibling, not inside the package
    assert got.name == pkg_r.name + suffix


@pytest.mark.parametrize("tool_name", [
    "realistic_bgc_count.py", "build_novelty_shortlist.py", "build_domain_reference.py",
])
def test_reader_out_dir_refuses_explicit_inside_package(tool_name, tmp_path):
    """PASS-AFTER: an explicit --out that resolves inside the sealed package is refused."""
    mod = _load_tool(tool_name)
    pkg = tmp_path / "AS40" / "package"
    pkg.mkdir(parents=True)
    with pytest.raises(ValueError):
        mod._reader_out_dir(str(pkg / "sub"), str(pkg), "_x")

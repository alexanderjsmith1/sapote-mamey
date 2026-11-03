"""Synthetic metadata only: no release ZIPs, analysis or large allocations."""
import builtins
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/preflight_zip_hygiene.py"
spec = importlib.util.spec_from_file_location("zip_error_candidate", SCRIPT)
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
import zip_hygiene_allowlist as policy


def metadata(monkeypatch, name="docs/declared.pdf", size=None):
    calls = []
    class Archive:
        def __init__(self, path): calls.append(str(path))
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def infolist(self): return [SimpleNamespace(filename=name, file_size=size or tool.LARGE_LIMIT + 1)]
    monkeypatch.setattr(tool.zipfile, "ZipFile", Archive)
    return calls

@pytest.mark.parametrize("kind", ["bad_ceiling", "invalid_utf8", "permission", "io_error"])
def test_selected_allowlist_error_cannot_become_clean_scan(tmp_path, monkeypatch, capsys, kind):
    allow = tmp_path / "policy.tsv"
    allow.write_bytes(b'docs/declared.pdf\t10\treason\n')
    if kind == "bad_ceiling": allow.write_text("docs/declared.pdf\tBROKEN\treason\n")
    if kind == "invalid_utf8": allow.write_bytes(b'docs/declared.pdf\t10\t\xff\n')
    before = allow.read_bytes()
    original = Path.read_text
    def unreadable(path, *args, **kwargs):
        if path == allow and kind in {"permission", "io_error"}:
            raise (PermissionError if kind == "permission" else OSError)("synthetic policy unavailable")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", unreadable)
    loader = tool._load_path_allowlist
    monkeypatch.setattr(tool, "_load_path_allowlist", lambda: loader(allow))
    calls = metadata(monkeypatch)
    archive = tmp_path / "synthetic.zip"; archive.write_bytes(b"opaque fixture, metadata stubbed")
    with pytest.raises(ValueError, match="ZIP_HYGIENE_ALLOWLIST_HOLD") as caught:
        tool.main(["preflight_zip_hygiene.py", str(archive)])
    assert str(allow) in str(caught.value) and caught.value.__cause__ is not None
    assert not calls and " is clean" not in capsys.readouterr().out
    assert allow.read_bytes() == before
    assert archive.read_bytes() == b"opaque fixture, metadata stubbed"


def test_missing_optional_explicit_path_preserves_empty_policy(tmp_path):
    assert tool._load_path_allowlist(tmp_path / "missing.tsv") == {}


def test_readable_empty_optional_policy_preserves_empty_policy(tmp_path):
    p = tmp_path / "empty.tsv"; p.write_text("# no declarations\n")
    assert tool._load_path_allowlist(p) == {}

@pytest.mark.parametrize("size,violation", [(9, False), (11, True), (6 * 1024 * 1024, True)])
def test_readable_declared_ceiling_binds_pdf_metadata(tmp_path, monkeypatch, size, violation):
    p = tmp_path / "policy.tsv"; p.write_text("docs/declared.pdf\t10\treason\n")
    loader = tool._load_path_allowlist
    monkeypatch.setattr(tool, "_load_path_allowlist", lambda: loader(p))
    metadata(monkeypatch, size=size)
    assert bool(tool.scan(tmp_path / "opaque.zip")["large"]) is violation


def test_absent_policy_retains_existing_coarse_exemption(tmp_path, monkeypatch):
    loader = tool._load_path_allowlist
    monkeypatch.setattr(tool, "_load_path_allowlist", lambda: loader(tmp_path / "missing.tsv"))
    metadata(monkeypatch)
    assert tool.scan(tmp_path / "opaque.zip")["large"] == []


def test_unexpected_loader_bug_is_not_swallowed(tmp_path, monkeypatch):
    def broken(path): raise RuntimeError("synthetic loader bug")
    monkeypatch.setattr(policy, "load_allowlist", broken)
    with pytest.raises(RuntimeError, match="synthetic loader bug"):
        tool._load_path_allowlist(tmp_path / "selected.tsv")


def test_missing_helper_is_not_silently_treated_as_empty(tmp_path, monkeypatch):
    original = builtins.__import__
    def unavailable(name, *args, **kwargs):
        if name == "zip_hygiene_allowlist": raise ModuleNotFoundError("synthetic missing policy helper")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", unavailable)
    with pytest.raises(ModuleNotFoundError, match="synthetic missing policy helper"):
        tool._load_path_allowlist(tmp_path / "selected.tsv")

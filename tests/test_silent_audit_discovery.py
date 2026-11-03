"""Synthetic Python source, directory errors and reporting only."""
import errno
import importlib.util
import os
from pathlib import Path
import sys
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/silent_exit_audit.py"
spec = importlib.util.spec_from_file_location("isolated_silent_audit", SCRIPT)
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)

@pytest.mark.parametrize("error_number", [errno.EACCES, errno.ENOENT, errno.EIO])
@pytest.mark.parametrize("ratchet", [False, True], ids=["report", "ratchet"])
def test_mixed_readable_unavailable_scopes(tmp_path, monkeypatch, capsys, error_number, ratchet):
    good = tmp_path / "good"; good.mkdir(); (good / "clean.py").write_text("x = 1\n")
    bad = tmp_path / "bad"; bad.mkdir(); (bad / "hidden.py").write_text("x = 2\n")
    before = {p: p.read_bytes() for p in tmp_path.rglob('*.py')}
    scan = tool.os.scandir
    def unavailable(path):
        if Path(path) == bad: raise OSError(error_number, "synthetic directory error", str(bad))
        return scan(path)
    monkeypatch.setattr(tool.os, "scandir", unavailable)
    args = ["--root", str(tmp_path), "--scope", "good", "bad"] + (["--ceiling", "0"] if ratchet else [])
    code = tool.main(args)
    output = capsys.readouterr().out
    assert code == (1 if ratchet else 0)
    assert "NOT SCANNED: directory traversal failed:" in output and str(bad) in output
    assert "across 1 file(s)" in output
    assert ("cannot be certified" in output) == ratchet
    assert all(p.read_bytes() == data for p, data in before.items())


def test_nested_unavailable_directory_fails_ratchet(tmp_path, monkeypatch, capsys):
    root = tmp_path / "hooks"; root.mkdir(); (root / "clean.py").write_text("x = 1")
    bad = root / "nested"; bad.mkdir()
    scan = tool.os.scandir
    def unavailable(path):
        if Path(path) == bad: raise PermissionError(errno.EACCES, "synthetic denied", str(bad))
        return scan(path)
    monkeypatch.setattr(tool.os, "scandir", unavailable)
    assert tool.main(["--root", str(tmp_path), "--ceiling", "0"]) == 1
    assert str(bad) in capsys.readouterr().out


def test_direct_file_scope_remains_missing_folder_contract(tmp_path, capsys):
    (tmp_path / "single.py").write_text("x = 1")
    assert tool.main(["--root", str(tmp_path), "--scope", "single.py", "--ceiling", "0"]) == 1
    assert "scope folder(s) not found" in capsys.readouterr().out


def test_scope_root_symlink_walked_nested_symlink_reported(tmp_path, capsys):
    target = tmp_path / "target"; target.mkdir(); (target / "clean.py").write_text("x = 1")
    (tmp_path / "alias").symlink_to(target, target_is_directory=True)
    # Explicit scope symlink is walked; skipped descendant directory symlinks are reported.
    assert tool.main(["--root", str(tmp_path), "--scope", "alias", "--ceiling", "0"]) == 0
    assert "across 1 file(s)" in capsys.readouterr().out
    hooks = tmp_path / "hooks"; hooks.mkdir()
    (hooks / "nested_alias").symlink_to(target, target_is_directory=True)
    (hooks / "linked.py").symlink_to(target / "clean.py")
    assert tool.main(["--root", str(tmp_path), "--ceiling", "0"]) != 0
    text = capsys.readouterr().out
    assert "across 1 file(s)" in text and "NOT SCANNED" in text and "symlink" in text.lower()


def test_missing_and_unparsed_semantics_retained(tmp_path, capsys):
    hooks = tmp_path / "hooks"; hooks.mkdir(); (hooks / "broken.py").write_text("def f(:")
    assert tool.main(["--root", str(tmp_path), "--scope", "hooks", "missing", "--ceiling", "0"]) == 1
    output = capsys.readouterr().out
    assert "could not be parsed" in output and "scope folder(s) not found" in output
    assert tool.main(["--root", str(tmp_path)]) == 0
    assert "could not be parsed" in capsys.readouterr().out


@pytest.mark.parametrize("ratchet", [False, True], ids=["report", "ratchet"])
def test_selected_file_read_error_reports_nonzero(tmp_path, monkeypatch, capsys, ratchet):
    hooks = tmp_path / "hooks"; hooks.mkdir(); selected = hooks / "selected.py"
    selected.write_text("x = 1"); real_read = Path.read_bytes
    def denied(path):
        if path == selected: raise PermissionError("synthetic file read denied")
        return real_read(path)
    monkeypatch.setattr(Path, "read_bytes", denied)
    args = ["--root", str(tmp_path)] + (["--ceiling", "0"] if ratchet else [])
    assert tool.main(args) != 0
    text = capsys.readouterr().out
    assert "NOT SCANNED" in text and "selected.py" in text and "PermissionError" in text


def test_excluded_cache_stays_outside_coverage(tmp_path, monkeypatch, capsys):
    hooks = tmp_path / "hooks"; hooks.mkdir(); cache = hooks / "__pycache__"; cache.mkdir()
    (hooks / "clean.py").write_text("x = 1")
    scan = tool.os.scandir
    def unavailable(path):
        if Path(path) == cache: raise PermissionError("excluded directory reached")
        return scan(path)
    monkeypatch.setattr(tool.os, "scandir", unavailable)
    assert tool.main(["--root", str(tmp_path), "--ceiling", "0"]) == 0
    assert "NOT SCANNED" not in capsys.readouterr().out


@pytest.mark.parametrize("ratchet", [False, True], ids=["report", "ratchet"])
def test_explicit_empty_scope_is_unavailable_coverage(tmp_path, monkeypatch, capsys, ratchet):
    # A real default scope with a REVIEW finding must not be silently substituted.
    hooks = tmp_path / "hooks"; hooks.mkdir()
    (hooks / "review.py").write_text("import os\ndef main():\n    if not os.path.isfile('configured'):\n        return 0\n")
    def forbidden_walk(*args, **kwargs):
        pytest.fail("empty explicit scope must not traverse defaults or cwd")
    monkeypatch.setattr(tool.os, "walk", forbidden_walk)
    args = ["--root", str(tmp_path), "--scope"] + (["--ceiling", "0"] if ratchet else [])
    assert tool.main(args) == (1 if ratchet else 0)
    out = capsys.readouterr().out
    assert "NOT SCANNED: no scope folders selected" in out
    assert "across 0 file(s)" in out
    assert ("cannot be certified" in out) == ratchet


def test_omitted_scope_still_scans_default_hooks(tmp_path, capsys):
    hooks = tmp_path / "hooks"; hooks.mkdir()
    (hooks / "review.py").write_text("import os\ndef main():\n    if not os.path.isfile('configured'):\n        return 0\n")
    assert tool.main(["--root", str(tmp_path), "--ceiling", "0"]) == 1
    out = capsys.readouterr().out
    assert "1 REVIEW" in out and "across 1 file(s)" in out
    assert "no scope folders selected" not in out


@pytest.mark.parametrize("ratchet", [False, True])
def test_existing_empty_scope_cannot_be_certified(tmp_path, capsys, ratchet):
    (tmp_path / "hooks").mkdir()
    args = ["--root", str(tmp_path), "--scope", "hooks"]
    if ratchet:
        args += ["--ceiling", "0"]
    assert tool.main(args) == (1 if ratchet else 0)
    assert "NOT SCANNED: no Python files were parsed" in capsys.readouterr().out


@pytest.mark.parametrize("ratchet", [False, True])
def test_undecodable_source_is_not_certified(tmp_path, capsys, ratchet):
    hooks = tmp_path / "hooks"; hooks.mkdir()
    source = hooks / "invalid.py"; source.write_bytes(b"# invalid \xff\nvalue = 1\n")
    args = ["--root", str(tmp_path), "--scope", "hooks"]
    if ratchet: args += ["--ceiling", "0"]
    assert tool.main(args) == (1 if ratchet else 0)
    assert "could not be parsed" in capsys.readouterr().out
    assert source.read_bytes() == b"# invalid \xff\nvalue = 1\n"

def test_declared_source_encoding_remains_valid(tmp_path, capsys):
    hooks = tmp_path / "hooks"; hooks.mkdir()
    (hooks / "latin.py").write_bytes(b"# coding: latin-1\nvalue = \"\xe9\"\n")
    assert tool.main(["--root", str(tmp_path), "--scope", "hooks", "--ceiling", "0"]) == 0
    assert "1 file(s)" in capsys.readouterr().out


def test_each_source_is_read_once_for_validation_and_classification(tmp_path, monkeypatch, capsys):
    hooks = tmp_path / "hooks"; hooks.mkdir(); source = hooks / "fixture.py"
    source.write_bytes(b"def main():\n    if missing:\n        return 0\n")
    real_read = Path.read_bytes; calls = []
    def unstable(path):
        if path == source:
            calls.append(path)
            if len(calls) > 1: return b"{invalid"
        return real_read(path)
    monkeypatch.setattr(Path, "read_bytes", unstable)
    tool.main(["--root", str(tmp_path), "--scope", "hooks"])
    capsys.readouterr()
    assert len(calls) == 1


@pytest.mark.parametrize("ratchet", [False, True], ids=["report", "ratchet"])
@pytest.mark.parametrize("root_link", [False, True], ids=["nested", "scope-root"])
def test_symlinked_scope_not_certified(tmp_path, monkeypatch, capsys, ratchet, root_link):
    outside=tmp_path/"outside";outside.mkdir();(outside/"missed.py").write_text("x = 1")
    hooks=tmp_path/"hooks"
    if root_link:hooks.symlink_to(outside,target_is_directory=True)
    else:
        hooks.mkdir();(hooks/"clean.py").write_text("x = 1");(hooks/"linked").symlink_to(outside,target_is_directory=True)
    args=["--root",str(tmp_path)] + (["--ceiling", "0"] if ratchet else [])
    result=tool.main(args);text=capsys.readouterr().out
    if root_link:
        assert result == 0 and "across 1 file(s)" in text
    else:
        assert result != 0 and "NOT SCANNED" in text and "symlink" in text.lower()


@pytest.mark.parametrize("failure",["is_dir","is_symlink"])
@pytest.mark.parametrize("ratchet",[False,True],ids=["report","ratchet"])
def test_entry_classification_error_reports_incomplete_scan(tmp_path,monkeypatch,capsys,failure,ratchet):
    hooks=tmp_path/"hooks";hidden=hooks/"hidden";hidden.mkdir(parents=True)
    (hooks/"clean.py").write_text("value=1\n")
    (hidden/"source.py").write_text('import os\ndef main():\n    if not os.path.isdir("placeholder"):\n        return 0\n    print("done")\n    return 0\n')
    original=tool.os.scandir
    class EntryProxy:
        def __init__(self,entry):self.entry=entry
        def __getattr__(self,name):return getattr(self.entry,name)
        def is_dir(self,*args,**kwargs):
            if self.entry.name=="hidden" and failure=="is_dir":raise OSError("synthetic classification failure")
            return self.entry.is_dir(*args,**kwargs)
        def is_symlink(self):
            if self.entry.name=="hidden" and failure=="is_symlink":raise OSError("synthetic classification failure")
            return self.entry.is_symlink()
    class IterProxy:
        def __init__(self,path):self.iterator=original(path)
        def __enter__(self):self.iterator.__enter__();return self
        def __exit__(self,*args):return self.iterator.__exit__(*args)
        def __iter__(self):return self
        def __next__(self):return EntryProxy(next(self.iterator))
    monkeypatch.setattr(tool.os,"scandir",lambda path:IterProxy(path))
    args=["--root",str(tmp_path)]+(["--ceiling","0"] if ratchet else [])
    code=tool.main(args);output=capsys.readouterr().out
    assert code==(1 if ratchet else 0) and "NOT SCANNED: directory traversal failed" in output and str(hidden) in output
    assert ("cannot be certified" in output)==ratchet

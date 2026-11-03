import importlib.util
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/check_license_docs.py"

def load():
    spec = importlib.util.spec_from_file_location("grant_candidate", TOOL)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def run(tmp_path, monkeypatch, content):
    mod = load(); lic = tmp_path / "LICENSE-DOCS.txt"; lic.write_text(content)
    (tmp_path / "README.md").write_text("readme")
    monkeypatch.setattr(mod, "ROOT", tmp_path); monkeypatch.setattr(mod, "LIC", lic)
    return mod.main([])

@pytest.mark.parametrize("line", ["docs/missing path.md", "docs/**/*.md", "docs/missing.md # comment", "docs/missing", "docs/missing?.md"])
def test_mixed_unsupported_grant_refused(tmp_path, monkeypatch, capsys, line):
    assert run(tmp_path, monkeypatch, "README.md\n" + line + "\n") == 1
    assert "unrecognized" in capsys.readouterr().out

def test_prose_preserved_around_grant_block(tmp_path, monkeypatch):
    text = "Creative Commons Attribution\n\nThe following files are licensed under CC-BY-4.0:\n\n  README.md\n\nCopyright (c) 2026 Person\n\nYou are free to share.\n"
    assert run(tmp_path, monkeypatch, text) == 0

def test_unknown_in_grant_block_refused_even_after_blank(tmp_path, monkeypatch, capsys):
    text = "The following files are licensed under CC-BY-4.0:\n  README.md\n\n  docs/a missing.md\nCopyright (c) 2026 Person\n"
    assert run(tmp_path, monkeypatch, text) == 1
    assert "line 4" in capsys.readouterr().out

def test_no_end_boundary_refused(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, "The following files are licensed under CC-BY-4.0:\nREADME.md\n") == 1

def test_existing_missing_entry_refused(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, "README.md\ndocs/missing.md\n") == 1

def test_missing_glob_refused(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, "README.md\ndocs/*.md\n") == 1


@pytest.mark.parametrize("entry", ["../outside.md", "/tmp/absolute.md"])
def test_grant_path_escape_is_rejected(tmp_path,monkeypatch,capsys,entry):
    assert run(tmp_path,monkeypatch,"README.md\n"+entry+"\n") == 1
    assert "unsafe" in capsys.readouterr().out.lower()

def test_grant_file_symlink_outside_is_rejected(tmp_path,monkeypatch,capsys):
    external=tmp_path.parent/(tmp_path.name+"_external.md");external.write_text("external")
    (tmp_path/"link.md").symlink_to(external)
    assert run(tmp_path,monkeypatch,"README.md\nlink.md\n") == 1
    assert "unsafe" in capsys.readouterr().out.lower()

def test_glob_with_only_directory_is_missing(tmp_path,monkeypatch):
    (tmp_path/"docs/empty.md").mkdir(parents=True)
    assert run(tmp_path,monkeypatch,"README.md\ndocs/*.md\n") == 1

def test_glob_external_symlink_is_rejected_even_with_real_file(tmp_path,monkeypatch,capsys):
    external=tmp_path.parent/(tmp_path.name+"_external.md");external.write_text("external")
    docs=tmp_path/"docs";docs.mkdir();(docs/"real.md").write_text("ok");(docs/"outside.md").symlink_to(external)
    assert run(tmp_path,monkeypatch,"README.md\ndocs/*.md\n") == 1
    assert "unsafe" in capsys.readouterr().out.lower()

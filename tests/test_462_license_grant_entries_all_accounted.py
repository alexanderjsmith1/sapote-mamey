"""DREL-015: every entry in the CC-BY-4.0 grant list is parsed or the check fails (closed by R461_CODE_44)."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TITLE = "Creative Commons Attribution 4.0 International (CC-BY-4.0)"
HEADER = "The following files are licensed under CC-BY-4.0:"
END = "Copyright (c) 2026 Alexander J. Smith"


def _module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "check_license_docs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(text, tmp_path):
    mod = _module("check_license_docs_462")
    lic = tmp_path / "LICENSE-DOCS.txt"
    lic.write_text(text, encoding="utf-8")
    mod.LIC = lic
    return mod.main([])


def test_unparseable_entry_with_space_fails_and_is_named(tmp_path, capsys):
    rc = _run(f"{TITLE}\n\n{HEADER}\n\n  README.md\n  docs/missing file.md\n\n{END}\n", tmp_path)
    assert rc == 1
    assert "missing file.md" in capsys.readouterr().out


def test_prose_after_the_list_is_not_an_entry(tmp_path):
    assert _run(f"{TITLE}\n\n{HEADER}\n\n  README.md\n\n{END}\n\nYou are free to:\n  Share and adapt.\n", tmp_path) == 0


def test_shipped_license_file_still_passes():
    assert _module("check_license_docs_462b").main([]) == 0

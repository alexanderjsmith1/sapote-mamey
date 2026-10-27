"""check_license_docs fails when LICENSE-DOCS.txt holds no grant it can recognize.

A grant file whose lines match neither pattern used to print "0 grant(s) declared" and PASS.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("check_license_docs_458", ROOT / "tools" / "check_license_docs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_no_recognized_grant_is_a_failure(tmp_path, capsys):
    mod = _load()
    lic = tmp_path / "LICENSE-DOCS.txt"
    lic.write_text("# Docs are CC-BY-4.0.\nAll documentation in this bundle.\n", encoding="utf-8")
    mod.LIC = lic
    assert mod.main([]) == 1
    assert "no grants recognized" in capsys.readouterr().out


def test_a_recognized_grant_still_passes(tmp_path):
    mod = _load()
    lic = tmp_path / "LICENSE-DOCS.txt"
    lic.write_text("# Docs are CC-BY-4.0.\nREADME.md\n", encoding="utf-8")
    mod.LIC = lic
    assert mod.main([]) == 0

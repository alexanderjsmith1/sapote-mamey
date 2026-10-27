"""silent_exit_audit reports files it could not parse and scope folders it could not find.

A syntax-error file was counted as scanned with no findings, and a mistyped --scope walked
nothing; both printed a clean count, and in --ceiling mode both passed.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("silent_exit_audit_458", ROOT / "tools" / "silent_exit_audit.py")
sea = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sea)


def test_unparsable_file_is_reported_and_fails_ratchet(tmp_path, capsys):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "ok.py").write_text("x = 1\n")
    (hooks / "broken.py").write_text("def f(:\n")
    assert sea.main(["--root", str(tmp_path), "--ceiling", "0"]) == 1
    out = capsys.readouterr().out
    assert "could not be parsed" in out and "broken.py" in out and "across 1 file(s)" in out


def test_missing_scope_is_reported_and_fails_ratchet(tmp_path, capsys):
    assert sea.main(["--root", str(tmp_path), "--scope", "hokks", "--ceiling", "0"]) == 1
    assert "scope folder(s) not found" in capsys.readouterr().out


def test_report_mode_still_exits_zero(tmp_path, capsys):
    assert sea.main(["--root", str(tmp_path), "--scope", "hokks"]) == 0
    assert "NOT SCANNED" in capsys.readouterr().out

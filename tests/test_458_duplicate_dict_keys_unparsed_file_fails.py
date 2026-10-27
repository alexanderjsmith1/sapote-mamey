"""The duplicate-dict-key gate does not count an unparsable file as scanned and clean.

scan_file returned nothing on a SyntaxError, so the file was counted in "N file(s) scanned" and
the gate printed PASS without having looked inside it.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("check_duplicate_dict_keys_458", ROOT / "tools" / "check_duplicate_dict_keys.py")
ddk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ddk)


def test_syntax_error_file_blocks_pass(tmp_path, capsys):
    (tmp_path / "ok.py").write_text("x = {'a': 1}\n")
    (tmp_path / "broken.py").write_text("d = {'a': 1, 'a': 2\n")   # unclosed: the collision is hidden
    assert ddk.main(["--root", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "could not be parsed" in err and "broken.py" in err


def test_clean_tree_still_passes(tmp_path, capsys):
    (tmp_path / "ok.py").write_text("x = {'a': 1}\n")
    assert ddk.main(["--root", str(tmp_path)]) == 0
    assert "1 file(s) scanned" in capsys.readouterr().out

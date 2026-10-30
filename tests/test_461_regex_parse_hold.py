"""A regex gate cannot report PASS when Python source cannot be parsed."""
from tools import check_regex_interpolation as gate
import pytest

@pytest.mark.parametrize("mixed", [False, True])
def test_syntax_error_refuses_gate(tmp_path, capsys, mixed):
    bad = tmp_path / "broken.py"
    bad.write_text("VALUE = (\n")
    if mixed:
        (tmp_path / "valid.py").write_text("VALUE = 1\n")
    assert gate.main(["--root", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert "PASS" not in captured.out
    assert "broken.py" in captured.err

def test_valid_module_still_scans(tmp_path):
    source = tmp_path / "valid.py"
    source.write_text("VALUE = 1\n")
    assert gate.main(["--root", str(source)]) == 0

from pathlib import Path
import importlib.util
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("review_tool", ROOT / "tools/professionalism_linter.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

@pytest.mark.parametrize("json_mode", [False, True])
def test_unreadable_input_is_incomplete(tmp_path, capsys, json_mode):
    missing = tmp_path / "missing.md"
    rc = tool.main([str(missing)] + (["--json"] if json_mode else []))
    output = capsys.readouterr()
    assert rc == 2
    assert "cannot read" in output.err
    assert "clean." not in output.out
    if json_mode:
        import json
        assert json.loads(output.out) == {}  # existing findings schema

def test_incomplete_precedes_advisory_status(tmp_path, capsys):
    found = tmp_path / "found.md"
    found.write_text("This is clearly a novel species.\n")
    assert tool.main([str(found), str(tmp_path / "missing.md")]) == 2

@pytest.mark.parametrize("text, expected", [("A descriptive observation.", 0),
                                          ("This is clearly a novel species.", 1)])
def test_readable_status_contract(tmp_path, text, expected):
    source = tmp_path / "input.md"
    source.write_text(text)
    assert tool.main([str(source)]) == expected

"""The measured terminal-emission ceiling rejects new sites above 1246."""
import importlib.util
from pathlib import Path
import sys
import pytest

PATH=Path(__file__).resolve().parents[1]/"tools/repo_health.py"
spec=importlib.util.spec_from_file_location("ratchet_license_review",PATH);tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tool;spec.loader.exec_module(tool)

@pytest.mark.parametrize("count,expected",[(1246,"OK"),(1247,"WARN")])
def test_terminal_emission_ratchet_boundary(tmp_path,count,expected):
    src=tmp_path/"source.py";src.write_text("print('synthetic')\n"*count)
    result=tool.check_print_calls([src],tmp_path)
    assert result.status==expected

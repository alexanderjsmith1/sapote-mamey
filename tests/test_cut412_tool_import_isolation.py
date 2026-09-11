import importlib.util
from pathlib import Path
import sys
import pytest

@pytest.mark.parametrize("name", ["query_support_table", "collapse_query_groups"])
def test_tool_import_has_no_cli_io(name, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["isolated-import"])
    path = Path(__file__).resolve().parents[1] / "tools" / (name + ".py")
    spec = importlib.util.spec_from_file_location("_isolated_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)

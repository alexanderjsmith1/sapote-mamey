"""CSV parser limits must survive imports across former test partitions."""
import ast
import csv
import importlib
from pathlib import Path
import sys

import pytest


def _setter_modules():
    root = Path(__file__).resolve().parents[1]
    modules = []
    for directory in ("mamey", "tools"):
        for path in sorted((root / directory).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
            if any((isinstance(node.func, ast.Attribute) and node.func.attr == "field_size_limit")
                   or (isinstance(node.func, ast.Name) and node.func.id == "field_size_limit")
                   for node in calls):
                modules.append(".".join(path.relative_to(root).with_suffix("").parts))
    assert modules, "No CSV field-size modules discovered"
    return sorted(modules)


@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reverse"])
def test_csv_field_limit_survives_all_setter_imports(reverse):
    """Reload all discovered setters in the same interpreter, then cached-import validate."""
    previous = csv.field_size_limit()
    required = min(sys.maxsize, 2**31 - 1)
    try:
        csv.field_size_limit(required)
        for name in sorted(_setter_modules(), reverse=reverse):
            module = importlib.import_module(name)
            importlib.reload(module)
            assert csv.field_size_limit() >= required, name
        importlib.import_module("mamey.validate")
        assert csv.field_size_limit() >= required
    finally:
        csv.field_size_limit(previous)

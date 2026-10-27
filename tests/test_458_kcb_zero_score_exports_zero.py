"""A stored KnownClusterBlast score or protein-hit count of 0 exports as 0, not blank.

None means no KCB record; 0 is a parsed value. `x or ""` turned both into a blank cell.
Source-level guard: these writers sit inside the full package export.
"""
import ast
import pathlib

import pytest
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"\.(kcb_cumulative|kcb_protein_hits)\s+or\s+[\"']{2}")


def test_no_kcb_number_is_blanked_by_or():
    hits = []
    for rel in ("mamey/cli.py", "mamey/master_workbook.py"):
        for n, line in enumerate((ROOT / rel).read_text().splitlines(), 1):
            if PATTERN.search(line):
                hits.append(f"{rel}:{n}")
    assert hits == [], "zero KCB values exported as blank at: " + ", ".join(hits)


def _production_export_cells():
    cells = []
    tree = ast.parse((ROOT / "mamey/cli.py").read_text())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "writerow" and node.args and isinstance(node.args[0], ast.List)):
            for cell in node.args[0].elts:
                if any(isinstance(part, ast.Attribute) and part.attr in {"kcb_cumulative", "kcb_protein_hits"}
                       for part in ast.walk(cell)):
                    cells.append(("mamey/cli.py", cell))
    tree = ast.parse((ROOT / "mamey/master_workbook.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "kcb_score":
                    if any(isinstance(part, ast.Attribute) and part.attr == "kcb_cumulative"
                           and isinstance(part.value, ast.Name) and part.value.id == "_bgc"
                           for part in ast.walk(value)):
                        cells.append(("mamey/master_workbook.py", value))
    return cells


@pytest.mark.parametrize("value", [0, 0.0, None, 27])
def test_actual_export_expressions_keep_recorded_zero(value):
    from types import SimpleNamespace
    cells = _production_export_cells()
    assert len(cells) == 4, "cover all four production export cells"
    record = SimpleNamespace(kcb_cumulative=value, kcb_protein_hits=value)
    expected = "" if value is None else value
    for source, expression in cells:
        actual = eval(compile(ast.Expression(expression), source, "eval"),
                      {"__builtins__": {}}, {"bgc": record, "_bgc": record})
        assert actual == expected, f"{source}:{expression.lineno} lost {value!r}"

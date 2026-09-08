"""The card-workbook deliverable must use the shared atomic output path."""
from __future__ import annotations

import ast
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "build_card_workbook.py"


def test_card_workbook_uses_atomic_save_and_closes_readback_handle():
    text = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "_wbio"
        for alias in node.names
    }
    assert "atomic_save" in imports
    assert "wb.save(args.out)" not in text
    assert "atomic_save(wb, args.out)" in text
    assert "finally:\n        wb2.close()" in text

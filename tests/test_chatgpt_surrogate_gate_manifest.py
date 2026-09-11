from pathlib import Path
import ast


def test_chatgpt_surrogate_gate_exists_and_has_load_bearing_tests():
    root = Path(__file__).resolve().parents[1]
    tool = root / "tools" / "run_chatgpt_surrogate_gate.py"
    assert tool.exists()
    tree = ast.parse(tool.read_text(encoding="utf-8"))
    assign = next(
        node for node in ast.walk(tree)
        if (isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "SURROGATE_PYTEST_FILES")
        or (isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "SURROGATE_PYTEST_FILES" for t in node.targets))
    )
    tests = ast.literal_eval(assign.value)
    required = {
        "tests/test_chatgpt_safe_first_run_guard.py",
        "tests/test_chatgpt_safe_batch_size_guard.py",
        "tests/test_v97141_phase_receipt_and_status.py",
        "tests/test_validate_timing_receipt_parity.py",
        "tests/test_b2_registry_parity.py",
        "tests/test_workbook_populated_sheet_gate.py",
    }
    assert required.issubset(set(tests))
    assert 10 <= len(tests) <= 30


def test_chatgpt_surrogate_gate_doc_exists():
    root = Path(__file__).resolve().parents[1]
    doc = root / "docs" / "CHATGPT_SURROGATE_GATE_v9.7.141.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "not" in text and "replacement for the full partitioned pytest suite" in text
    assert "python tools/run_chatgpt_surrogate_gate.py" in text

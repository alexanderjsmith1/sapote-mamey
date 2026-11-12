"""A missing optional module must not hide other failures."""
import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "tools" / "run_chatgpt_surrogate_gate.py"
spec = importlib.util.spec_from_file_location("surrogate_gate_optional_test", PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

@pytest.mark.parametrize("output,declared,expected", [
    ("/usr/bin/python3: No module named pytest\n", {"pytest"}, True),
    ("Traceback (most recent call last):\n  File \"app.py\", line 2, in <module>\n    import extra\nModuleNotFoundError: No module named 'extra'\n", {"extra"}, True),
    ("No module named 'extra'", set(), False),
    ("No module named 'openpyxl'", {"pytest"}, False),
    ("FAILED: No module named pytest", {"pytest"}, False),
    ("No module named 'extra'\nFAILED test_other.py", {"extra"}, False),
    ("Traceback (most recent call last):\n  File \"app.py\", line 2, in <module>\n    import extra\nModuleNotFoundError: No module named 'extra'\nFAILED test_other.py", {"extra"}, False),
    ("Traceback (most recent call last):\n  File \"app.py\", line 2\n    import extra\nModuleNotFoundError: No module named 'extra'\n\nDuring handling of the above exception, another exception occurred:\nTraceback (most recent call last):\n  File \"app.py\", line 4\n    import other\nModuleNotFoundError: No module named 'other'", {"extra", "other"}, False),
])
def test_isolated_optional_diagnostic(output, declared, expected):
    assert gate._optional_missing_only(output, declared) is expected

@pytest.mark.parametrize("output,optional,expected", [
    ("No module named 'extra'", ["--optional-module", "extra"], "ENV-SKIP"),
    ("No module named 'extra'\nFAILED unrelated", ["--optional-module", "extra"], "FAIL"),
    ("No module named 'extra'", [], "FAIL"),
    ("No module named 'extra'\nFAILED unrelated", [], "FAIL"),
])
def test_gate_summary_does_not_hide_failure(tmp_path, monkeypatch, output, optional, expected):
    monkeypatch.setattr(gate, "_run", lambda *args: (1, 0.1, output))
    monkeypatch.setattr(gate, "PY_COMPILE_TARGETS", ["sentinel.py"])
    monkeypatch.setattr(gate, "BASH_SYNTAX_TARGETS", [])
    monkeypatch.setattr(gate, "SURROGATE_PYTEST_FILES", ["sentinel.py"])
    (tmp_path / "sentinel.py").touch()
    rc = gate.main(["--root", str(tmp_path), "--out", "out", "--skip-doctor", *optional])
    summary = json.loads((tmp_path / "out/surrogate_gate_summary.json").read_text())
    assert summary["steps"][0]["status"] == expected
    assert summary["status"] == ("PASS" if expected == "ENV-SKIP" else "FAIL")
    assert rc == (0 if expected == "ENV-SKIP" else 1)
    assert summary["optional_modules"] == (["extra"] if optional else [])

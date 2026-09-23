"""Mutation evidence requires a working baseline and a genuine assertion failure."""
import importlib.util
from pathlib import Path
import pytest


def load():
    p = Path(__file__).resolve().parents[1] / "tools/gate_mutation_probe.py"
    spec = importlib.util.spec_from_file_location("probe_evidence", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fixture(tmp_path, monkeypatch, test, mutation="False"):
    m = load()
    monkeypatch.setattr(m.tempfile, "tempdir", str(tmp_path))
    root = tmp_path / "source"
    root.mkdir()
    (root / "guard.py").write_text("ENABLED = True\n")
    (root / "test_guard.py").write_text(test)
    logs = tmp_path / "logs"
    logs.mkdir()
    row = dict(id="TEST", kind="guard", source="guard.py", old="True", new=mutation, tests="test_guard.py", consequence="generic guard")
    return m, root, logs, row


@pytest.mark.parametrize("test,mutation,expected", [
    ("def test_it(): assert False\n", "False", "HOLD_BASELINE_FAILED"),
    ("import missing_fixture_dependency\n", "False", "HOLD_BASELINE_FAILED"),
    ("import pytest\n@pytest.mark.skip(reason='not available')\ndef test_it(): pass\n", "False", "HOLD_NO_TESTS_EXECUTED"),
    ("from guard import ENABLED\ndef test_it(): assert ENABLED\n", "False", "BITES"),
    ("def test_it(): assert True\n", "False", "VACUOUS"),
    ("from guard import ENABLED\ndef test_it(): assert ENABLED\n", "None", "BITES"),
    ("from guard import ENABLED\ndef test_it(): assert ENABLED\n", "(broken syntax", "HOLD_MUTATION_EXECUTION_ERROR"),
])
def test_evidence_classification(tmp_path, monkeypatch, test, mutation, expected):
    m, root, logs, row = fixture(tmp_path, monkeypatch, test, mutation)
    result = m.run_one(root, row, logs)
    assert result["classification"] == expected
    assert (root / "guard.py").read_text() == "ENABLED = True\n"


@pytest.mark.parametrize("locator", ["absolute", "../external.py"])
def test_absolute_source_cannot_mutate_outside_copy(tmp_path, monkeypatch, locator):
    m, root, logs, row = fixture(tmp_path, monkeypatch, "def test_it(): assert True\n")
    outside = tmp_path / "external.py"
    outside.write_text("ENABLED = True\n")
    row["source"] = str(outside) if locator == "absolute" else locator
    result = m.run_one(root, row, logs)
    assert result["classification"] == "HOLD_UNSAFE_SOURCE"
    assert outside.read_text() == "ENABLED = True\n"

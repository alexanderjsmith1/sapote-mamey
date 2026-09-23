from pathlib import Path

import mamey.cohort_deliverable as cohort


ROOT = Path(__file__).resolve().parent.parent


def test_version_gate_loader_returns_the_shipped_gate_module():
    gate = cohort._load_version_gate()

    assert gate is not None
    assert Path(gate.__file__).resolve() == (
        ROOT / "tools" / "cohort_scoring_version_gate.py"
    ).resolve()
    assert callable(gate.assert_uniform_scoring_engine)


def test_version_gate_loader_returns_none_when_tool_is_missing(monkeypatch, tmp_path):
    package = tmp_path / "mamey"
    package.mkdir()
    monkeypatch.setattr(cohort, "__file__", str(package / "cohort_deliverable.py"))

    assert cohort._load_version_gate() is None

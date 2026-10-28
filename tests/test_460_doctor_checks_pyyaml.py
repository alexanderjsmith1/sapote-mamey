"""doctor checks PyYAML, a declared core dependency.

pyproject.toml lists PyYAML under core `dependencies`, and tools/render_bootstrap_contract.py imports it,
but `doctor` never checked it: a missing PyYAML gave no line at all. It is now reported like ijson, as a
core warning, without changing doctor's exit code.
"""
import tomllib

from tests.test_459_doctor_summary_and_zip_wording import ROOT, _absent, _doctor, _summary, synthetic_bundle  # noqa: F401


def test_pyyaml_is_a_declared_core_dependency():
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    assert any(d.lower().startswith("pyyaml") for d in deps)


def test_missing_pyyaml_is_reported_as_core(synthetic_bundle, monkeypatch, capsys):
    _absent(monkeypatch, "yaml")
    status, out = _doctor(capsys)
    assert "PyYAML absent" in out and "declared core dependency" in out
    summary = _summary(out)
    assert "core dependency" in summary and "PyYAML" in summary
    assert status == 0                      # a warning, like ijson: severity and exit code unchanged


def test_present_pyyaml_is_listed(synthetic_bundle, capsys):
    status, out = _doctor(capsys)
    assert "PyYAML (declared core" in out

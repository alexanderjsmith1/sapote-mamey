import sys
from types import SimpleNamespace
import pytest
from tools import mamey_pipeline as mod

@pytest.mark.parametrize("failed", ["validate", "explain", "figures", "missing_figures"])
def test_report_wrapper_propagates_required_stage_failure(tmp_path, monkeypatch, failed):
    package = tmp_path / "package"
    package.mkdir()
    (package / "source.txt").write_text("synthetic")
    engine = tmp_path / "engine"
    engine.mkdir()
    figures = tmp_path / "figures"
    if failed != "missing_figures": figures.mkdir()
    def run(command, **kwargs):
        stage = "validate" if "validate" in command else "explain" if "explain" in command else "figures"
        return SimpleNamespace(returncode=7 if stage == failed else 0, stdout="synthetic output", stderr="")
    monkeypatch.setattr(mod, "run", run)
    monkeypatch.setattr(sys, "argv", ["pipeline", "--strain", "SYN-A", "--package", str(package), "--engine", str(engine), "--figures", str(figures), "--out", str(tmp_path / "output")])
    assert mod.main() == 1
    assert (tmp_path / "output/REPORT_SYN-A.md").exists()

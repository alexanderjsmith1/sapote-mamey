"""Missing print-validation dependencies refuse before output creation."""
import builtins
from pathlib import Path

import pytest
from tools import protein_pcoa_render


def _arguments(tmp_path, *extra):
    return ["--kit", str(tmp_path / "missing-kit"), "--out", str(tmp_path / "out"),
            "--cohort-table", str(tmp_path / "cohorts.tsv"), "--panel", "sample=group", *extra]


@pytest.mark.parametrize("option", [["--min-text-pt", "8"], ["--page", "pcoa"]])
def test_missing_pypdf_refuses_selected_validation_before_output(tmp_path, monkeypatch, caplog, option):
    original = builtins.__import__
    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tools" and "_min_text_check" in fromlist:
            raise ModuleNotFoundError("pypdf unavailable", name="pypdf")
        return original(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", guarded)
    assert protein_pcoa_render.main(_arguments(tmp_path, *option)) == 2
    assert "needs pypdf" in caplog.text
    assert not (tmp_path / "out").exists()


def test_other_missing_dependencies_are_not_misreported(tmp_path, monkeypatch):
    original = builtins.__import__
    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tools" and "_min_text_check" in fromlist:
            raise ModuleNotFoundError("other module unavailable", name="unrelated_fixture")
        return original(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", guarded)
    with pytest.raises(ModuleNotFoundError, match="other module unavailable"):
        protein_pcoa_render.main(_arguments(tmp_path, "--min-text-pt", "8"))
    assert not (tmp_path / "out").exists()

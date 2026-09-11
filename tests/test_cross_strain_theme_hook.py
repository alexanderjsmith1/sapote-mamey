import inspect
import importlib.util
from pathlib import Path


def test_cross_strain_builder_accepts_theme():
    path = Path(__file__).resolve().parents[1] / "mamey" / "cross_strain_figures.py"
    spec = importlib.util.spec_from_file_location("cross_strain_theme_hook", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    assert "theme" in inspect.signature(mod.build_cross_strain_figures).parameters


def test_unknown_theme_is_rejected_before_output(tmp_path):
    path = Path(__file__).resolve().parents[1] / "mamey" / "cross_strain_figures.py"
    spec = importlib.util.spec_from_file_location("cross_strain_theme_hook_invalid", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    try:
        mod.build_cross_strain_figures(tmp_path / "missing", tmp_path / "out", theme="not-a-theme")
    except ValueError as exc:
        assert "unknown Sapote-Mamey report theme" in str(exc)
    else:
        raise AssertionError("unknown theme was accepted")
    assert not (tmp_path / "out").exists()

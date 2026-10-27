"""A requested --widget that fails makes domain_prevalence and scan_prevalence exit nonzero.

Both printed a warning and returned 0, so a caller checking the exit code saw success with no widget.
"""
import importlib.util
import pathlib
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_458w", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("name,argv", [
    ("domain_prevalence", ["--census", "c", "--gbk-domains", "g", "--out", "o", "--widget"]),
    ("scan_prevalence", ["--scan-db", "s", "--dataset-name", "d", "--out", "o", "--widget"]),
])
@pytest.mark.parametrize("widget_rc,want", [(1, 3), (0, 0)])
def test_widget_result_sets_the_exit_code(monkeypatch, name, argv, widget_rc, want):
    mod = _load(name)
    monkeypatch.setattr(mod, "build", lambda a: [])
    import subprocess
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(returncode=widget_rc, stderr="boom", stdout=""))
    assert mod.main(argv) == want

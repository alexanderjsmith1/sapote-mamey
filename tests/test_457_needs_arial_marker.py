"""The needs_arial marker (conftest.py): tests that need real Arial metrics are skipped where matplotlib finds no font named Arial,
as on a Linux runner that has only the metric-compatible Liberation Sans (GitHub CI, .456)."""
import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _conftest():
    spec = importlib.util.spec_from_file_location("sapote_root_conftest", ROOT / "conftest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_arial_probe_follows_matplotlib_font_lookup(monkeypatch):
    font_manager = pytest.importorskip("matplotlib.font_manager")
    mod = _conftest()
    monkeypatch.setattr(font_manager, "findfont", lambda *a, **k: "/fonts/Arial.ttf")
    assert mod._real_arial_present() is True

    def missing(*a, **k):
        raise ValueError("Font family 'Arial' not found.")
    monkeypatch.setattr(font_manager, "findfont", missing)
    assert mod._real_arial_present() is False


def test_marked_tests_are_skipped_without_arial(tmp_path):
    pytest.importorskip("matplotlib")
    (tmp_path / "test_probe.py").write_text(textwrap.dedent("""
        import pytest
        @pytest.mark.needs_arial
        def test_marked():
            pass
        def test_unmarked():
            pass
    """))
    (tmp_path / "conftest.py").write_text((ROOT / "conftest.py").read_text())
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers =\n    needs_arial: x\n    slow: x\n    network: x\n")
    plugin = tmp_path / "no_arial.py"
    plugin.write_text("from matplotlib import font_manager\n_o = font_manager.findfont\n"
                      "def _f(family=None, *a, **k):\n"
                      "    if family == 'Arial':\n        raise ValueError('not found')\n"
                      "    return _o(family, *a, **k)\n"
                      "font_manager.findfont = _f\n")
    base = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs", str(tmp_path / "test_probe.py")]
    env_no = {"PYTHONPATH": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}
    r_no = subprocess.run(base + ["-p", "no_arial"], cwd=tmp_path, env=env_no, capture_output=True, text=True, timeout=120)
    assert "1 passed, 1 skipped" in r_no.stdout, r_no.stdout + r_no.stderr
    assert "needs real Arial" in r_no.stdout

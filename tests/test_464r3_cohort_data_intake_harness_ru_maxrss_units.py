"""The no-psutil peak-memory fallback converts ru_maxrss with the platform's unit."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("_intake_harness_464r3", ROOT / "tools" / "intake_harness.py")
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)


def test_macos_ru_maxrss_is_bytes():
    # 715,800,576 bytes is about 715.8 MB, not 699,024 "MB".
    assert H.ru_maxrss_to_mb(715_800_576, "darwin") == pytest.approx(715.800576)


def test_linux_ru_maxrss_is_kib():
    assert H.ru_maxrss_to_mb(699_024, "linux") == pytest.approx(699_024 * 1024 / 1e6)


def test_fallback_path_uses_the_converter(monkeypatch):
    monkeypatch.setattr(H, "_HAVE_PSUTIL", False)
    import resource

    class Usage:
        ru_maxrss = 715_800_576 if sys.platform == "darwin" else 699_024

    monkeypatch.setattr(resource, "getrusage", lambda who: Usage())
    rc, wall, peak_mb, out = H.run_monitored([sys.executable, "-c", "print('ok')"])
    assert rc == 0 and "ok" in out
    assert peak_mb == pytest.approx(715.8, abs=0.1)


def test_report_names_the_measurement_method(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "_HAVE_PSUTIL", False)
    path = tmp_path / "report.md"
    H._write_report(str(path), "synthetic", [], [], None)
    text = path.read_text()
    assert "ru_maxrss (psutil not installed)" in text
    assert "MB = 10^6 bytes" in text

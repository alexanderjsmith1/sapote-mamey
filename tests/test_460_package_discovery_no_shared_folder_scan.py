"""Package discovery reads only MAMEY_PACKAGES; it never scans shared /tmp or upload folders.

tools/build_bgc_markers.py::find_packages and tools/build_deep_data.py::find_snaps also globbed
/tmp/*/SID*, /tmp/mamey_SID* and /mnt/user-data/uploads/SID* (an old hosted-sandbox path). Any SID
folder another run left there entered the bank unasked. bundle_support/install_sapote_addons.sh also
searched /mnt/user-data/uploads for wheels to install.
"""
import glob as _glob
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_460", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def patterns(monkeypatch):
    seen = []
    real = _glob.glob
    monkeypatch.setattr(_glob, "glob", lambda p, *a, **k: seen.append(str(p)) or real(p, *a, **k))
    return seen


@pytest.mark.parametrize("tool, fn", [("build_bgc_markers", "find_packages"), ("build_deep_data", "find_snaps")])
def test_only_the_named_package_folders_are_searched(tool, fn, tmp_path, monkeypatch, patterns, capsys):
    mod = _load(tool)
    monkeypatch.setenv("MAMEY_PACKAGES", str(tmp_path))
    getattr(mod, fn)()
    assert patterns and all(p.startswith(str(tmp_path)) for p in patterns), patterns


@pytest.mark.parametrize("tool, fn", [("build_bgc_markers", "find_packages"), ("build_deep_data", "find_snaps")])
def test_unset_packages_searches_nothing_and_says_so(tool, fn, monkeypatch, patterns, capsys):
    mod = _load(tool)
    monkeypatch.delenv("MAMEY_PACKAGES", raising=False)
    assert getattr(mod, fn)() == {}
    assert patterns == []
    assert "MAMEY_PACKAGES is not set" in capsys.readouterr().err


def test_addon_installer_does_not_search_the_hosted_upload_folder():
    text = (ROOT / "bundle_support" / "install_sapote_addons.sh").read_text(encoding="utf-8")
    assert "/mnt/user-data" not in text

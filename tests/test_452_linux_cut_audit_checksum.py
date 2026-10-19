"""cut_audit verify chooses an available SHA-256 checker without launching a suite."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("cut_audit_checksum_fixture", ROOT / "tools/cut_audit.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("available, expected", [
    ({"sha256sum": "/synthetic/sha256sum"}, ["/synthetic/sha256sum", "-c", "SOURCE_CHECKSUMS_SHA256.txt"]),
    ({"shasum": "/synthetic/shasum"}, ["/synthetic/shasum", "-a", "256", "-c", "SOURCE_CHECKSUMS_SHA256.txt"]),
    ({"sha256sum": "/synthetic/sha256sum", "shasum": "/synthetic/shasum"}, ["/synthetic/sha256sum", "-c", "SOURCE_CHECKSUMS_SHA256.txt"]),
])
def test_verify_selects_available_checksum_binary(tmp_path, monkeypatch, available, expected):
    module = _load(); (tmp_path / "SOURCE_CHECKSUMS_SHA256.txt").write_text("fixture")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/sync_version.py").write_text("# opaque version source; never executed\n")
    monkeypatch.setattr(module.shutil, "which", lambda name: available.get(name))
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        assert cmd == expected or cmd == ["unused", "tools/sync_version.py", "--check"]
        return 0, "fixture: OK\n"
    monkeypatch.setattr(module, "_run", run)
    assert module.verify(SimpleNamespace(tree=str(tmp_path), python="unused", zip=None, sha256=None)) == 0
    assert calls == [expected, ["unused", "tools/sync_version.py", "--check"]]


def test_verify_missing_checksum_tools_refuses_without_subprocess(tmp_path, monkeypatch, capsys):
    module = _load(); (tmp_path / "SOURCE_CHECKSUMS_SHA256.txt").write_text("fixture")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/sync_version.py").write_text("# opaque version source; never executed\n")
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    def forbidden(*a, **k): raise AssertionError("missing checker must not launch a child")
    monkeypatch.setattr(module, "_run", forbidden)
    assert module.verify(SimpleNamespace(tree=str(tmp_path), python="unused", zip=None, sha256=None)) == 1
    assert "sha256sum or shasum unavailable -> FAIL" in capsys.readouterr().out

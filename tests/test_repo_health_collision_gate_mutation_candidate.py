import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parent.parent


def _repo_health():
    name = "repo_health_collision_gate_candidate"
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "repo_health.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _fixture_root(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "check_duplicate_dict_keys.py").write_text("# fixture gate\n")
    return tmp_path


def test_collision_gate_maps_zero_exit_to_ok(monkeypatch, tmp_path):
    repo_health = _repo_health()
    root = _fixture_root(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    result = repo_health.check_collisions_gate(root)

    assert result.status == "OK"
    assert result.hits == []


def test_collision_gate_maps_nonzero_exit_to_fail_with_diagnostics(monkeypatch, tmp_path):
    repo_health = _repo_health()
    root = _fixture_root(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="duplicate key: tools/example.py:4\n",
            stderr="strict gate refused\n",
        ),
    )

    result = repo_health.check_collisions_gate(root)

    assert result.status == "FAIL"
    assert result.hits == ["duplicate key: tools/example.py:4", "strict gate refused"]


def test_collision_gate_surfaces_invocation_error_as_warning(monkeypatch, tmp_path):
    repo_health = _repo_health()
    root = _fixture_root(tmp_path)

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("duplicate-key-gate", 120)

    monkeypatch.setattr(subprocess, "run", _timeout)

    result = repo_health.check_collisions_gate(root)

    assert result.status == "WARN"
    assert "did not run" in result.detail

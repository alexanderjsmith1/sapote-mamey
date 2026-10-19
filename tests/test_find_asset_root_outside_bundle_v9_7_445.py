"""A copy of tools/find_asset.py outside a bundle (no importable mamey) must still find the workspace
registry by walking up to OFFICIAL_DATA/ASSET_REGISTRY.tsv, instead of exiting with 'no workspace root'.
The SessionStart guidance points every chat at <workspace>/Tools/find_asset.py, which is such a copy."""
import os, shutil, subprocess, sys
from pathlib import Path
import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def _workspace(tmp_path):
    ws = tmp_path / "ws"
    (ws / "Tools").mkdir(parents=True)
    (ws / "OFFICIAL_DATA").mkdir()
    for f in ("find_asset.py", "_console.py"):
        if not (TOOLS / f).exists():
            pytest.skip(f"{f} absent")
        shutil.copy(TOOLS / f, ws / "Tools" / f)
    (ws / "tst_db").write_text("x\n")
    (ws / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").write_text(
        "asset_id\tkind\tpath\tsize\tnote\ntst_asset\tdb\ttst_db\t1K\tsynthetic test asset\n")
    return ws


def _run(ws, cwd):
    env = {k: v for k, v in os.environ.items() if k not in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT")}
    # -I -S: neither inherited PYTHONPATH nor installed packages can mask fallback.
    # -B remains explicit because -I ignores PYTHONDONTWRITEBYTECODE.
    return subprocess.run([sys.executable, "-I", "-S", "-B", str(ws / "Tools" / "find_asset.py"), "tst_asset"],
                          cwd=cwd, env=env, capture_output=True, text=True)


def test_copy_run_from_workspace_root_finds_registry(tmp_path):
    ws = _workspace(tmp_path)
    r = _run(ws, ws)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "no workspace root configured" not in r.stderr + r.stdout, r.stderr
    assert str(ws / "tst_db") in r.stdout


def test_copy_run_from_elsewhere_uses_its_own_location(tmp_path):
    ws = _workspace(tmp_path)
    other = tmp_path / "elsewhere"; other.mkdir()
    r = _run(ws, other)
    assert r.returncode == 0, r.stderr + r.stdout
    assert str(ws / "tst_db") in r.stdout


def test_no_registry_anywhere_still_fails_loudly(tmp_path):
    ws = _workspace(tmp_path)
    (ws / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").unlink()
    r = _run(ws, tmp_path)
    assert r.returncode != 0 and "no workspace root configured" in r.stderr + r.stdout


def test_inherited_pythonpath_cannot_mask_local_registry(tmp_path, monkeypatch):
    ws = _workspace(tmp_path)
    other = tmp_path / "foreign workspace"; other.mkdir()
    injected = tmp_path / "inherited path"
    (injected / "mamey").mkdir(parents=True)
    (injected / "mamey" / "__init__.py").write_text("")
    (injected / "mamey" / "workspace_root.py").write_text(
        "def workspace_root(): return " + repr(str(other)) + "\n")
    monkeypatch.setenv("PYTHONPATH", str(injected))
    r = _run(ws, other)
    assert r.returncode == 0, r.stderr + r.stdout
    assert str(ws / "tst_db") in r.stdout
    assert not list(ws.rglob("__pycache__"))

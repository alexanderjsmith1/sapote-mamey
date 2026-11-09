"""`--purge-bytecode` clears the engine's caches and nothing else.

The purge used to walk the whole bundle and `rmtree` every folder named `__pycache__`. A
bundle-local `.venv`, or a `__pycache__` folder a user made under `runs/`, went with it, along
with any non-bytecode file inside. These tests build a throwaway bundle with such folders and
check that the purge leaves them alone.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
RUNNER = BUNDLE / "mamey_run.py"


def _fake_bundle(root: Path) -> Path:
    assert BUNDLE not in root.resolve().parents, "the throwaway bundle must live outside the shipped tree"
    pkg = root / "mamey"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        '__version__ = "0.0.0"\nBUNDLE_VERSION = "9.9.999"\nfrom . import sub\n', encoding="utf-8")
    (pkg / "sub" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (pkg / "cli.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    (root / "BUILD_STAMP.txt").write_text(
        "version=9.9.999\nbuild=TESTBUILDa\nengine=0.0.0\ntier=code\n", encoding="utf-8")
    shutil.copy2(RUNNER, root / "mamey_run.py")
    return root


def _run(root: Path, *args: str, write_bytecode: bool = True) -> subprocess.CompletedProcess:
    env = {**os.environ}
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    if not write_bytecode:
        env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "mamey_run.py", *args], cwd=root,
                          capture_output=True, text=True, timeout=120, env=env)


def _stage(tmp_path: Path):
    root = _fake_bundle(tmp_path / "bundle")
    venv_cache = root / ".venv" / "lib" / "python3.13" / "site-packages" / "foo" / "__pycache__"
    venv_cache.mkdir(parents=True)
    (root / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    (venv_cache / "foo.cpython-313.pyc").write_bytes(b"x")
    (venv_cache / "KEEP.txt").write_text("sentinel\n", encoding="utf-8")
    runs_cache = root / "runs" / "S" / "__pycache__"
    runs_cache.mkdir(parents=True)
    (runs_cache / "notes.txt").write_text("user notes\n", encoding="utf-8")
    (runs_cache / "x.cpython-313.pyc").write_bytes(b"x")
    tools_cache = root / "tools" / "__pycache__"
    tools_cache.mkdir(parents=True)
    (tools_cache / "t.cpython-313.pyc").write_bytes(b"x")
    (tools_cache / "README.txt").write_text("not bytecode\n", encoding="utf-8")
    assert _run(root).returncode == 0
    assert list((root / "mamey" / "__pycache__").glob("*.pyc")), "no engine bytecode was produced"
    return root, venv_cache, runs_cache, tools_cache


def test_purge_leaves_a_bundle_local_venv_and_runs_alone(tmp_path):
    root, venv_cache, runs_cache, _ = _stage(tmp_path)
    result = _run(root, "--purge-bytecode", write_bytecode=False)
    assert result.returncode == 0, result.stderr
    assert (venv_cache / "KEEP.txt").is_file()
    assert (venv_cache / "foo.cpython-313.pyc").is_file(), ".venv bytecode is not the engine's"
    assert (runs_cache / "notes.txt").is_file()
    assert (runs_cache / "x.cpython-313.pyc").is_file(), "runs/ is not an engine source folder"
    assert ".venv, runs/ and other folders were not touched" in result.stderr


def test_purge_clears_engine_bytecode(tmp_path):
    root, *_ = _stage(tmp_path)
    result = _run(root, "--purge-bytecode", write_bytecode=False)
    assert result.returncode == 0, result.stderr
    assert not list((root / "mamey").rglob("*.pyc"))
    assert not list((root / "tools").rglob("*.pyc"))
    assert "purged 3 __pycache__ directories under this bundle" in result.stderr, result.stderr


def test_purge_keeps_and_names_non_bytecode_files_in_an_engine_cache(tmp_path):
    root, _, _, tools_cache = _stage(tmp_path)
    result = _run(root, "--purge-bytecode", write_bytecode=False)
    assert (tools_cache / "README.txt").is_file()
    assert "PURGE_KEPT_NON_BYTECODE" in result.stderr
    assert str(tools_cache / "README.txt") in result.stderr


def test_purge_also_clears_bytecode_temp_files_and_finder_files(tmp_path):
    root = _fake_bundle(tmp_path / "bundle")
    cache = root / "tools" / "__pycache__"
    cache.mkdir(parents=True)
    for name in ("t.cpython-313.pyc", "t.cpython-313.pyc.4402", ".DS_Store"):
        (cache / name).write_bytes(b"x")
    result = _run(root, "--purge-bytecode", write_bytecode=False)
    assert result.returncode == 0, result.stderr
    assert not cache.exists(), "a cache holding only derived files should be removed"
    assert "PURGE_KEPT_NON_BYTECODE" not in result.stderr


def test_remediation_commands_point_at_the_engine_package_only():
    text = RUNNER.read_text(encoding="utf-8")
    assert "find {_HERE!r} -name __pycache__" not in text
    assert text.count("find {os.path.join(_HERE, 'mamey')!r} -name __pycache__") == 3

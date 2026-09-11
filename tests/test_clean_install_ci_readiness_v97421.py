"""Portable regressions for clean-install and CI wheel readiness.

These tests use only temporary source copies and virtual environments. They do
not contact an index, mutate the checked-out source tree, or treat an editable
install as proof of installed-wheel behavior.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "bootstrap.sh"
WHEELS = ROOT / "wheels"


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, timeout: int = 180):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def _source_copy(target: Path) -> Path:
    source = target / "source"
    shutil.copytree(
        ROOT,
        source,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.egg-info", "build", "dist"),
    )
    return source


def _wheel_from_current_interpreter(target: Path, *, python_executable: str = sys.executable) -> Path:
    """Build offline in isolation; a fresh test interpreter need not contain setuptools."""
    source = _source_copy(target)
    out = target / "dist"
    out.mkdir()
    proc = _run(
        [
            python_executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-index",
            "--find-links",
            str(source / "wheels"),
            "--wheel-dir",
            str(out),
            str(source),
        ],
        cwd=target,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    built = list(out.glob("mamey-*.whl"))
    assert len(built) == 1, built
    return built[0]


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory) -> Path:
    target = tmp_path_factory.mktemp("clean-wheel-build")
    builder = target / "builder environment"
    proc = _run([sys.executable, "-m", "venv", str(builder)], cwd=target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    python = builder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # Exercise the same fresh-interpreter condition as CI, including Python versions
    # whose venv does not seed setuptools. Never borrow the test runner's backend.
    return _wheel_from_current_interpreter(target, python_executable=str(python))


def test_wheel_resources_read_outside_checkout_from_clean_interpreter(built_wheel: Path, tmp_path: Path):
    venv = tmp_path / "clean interpreter"
    proc = _run([sys.executable, "-m", "venv", str(venv)], cwd=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    proc = _run([str(python), "-m", "pip", "install", "--no-deps", str(built_wheel)], cwd=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    outside = tmp_path / "outside checkout"
    outside.mkdir()
    code = textwrap.dedent(
        """
        import json
        from importlib.resources import files
        from pathlib import Path
        import sysconfig
        import mamey

        origin = Path(mamey.__file__).resolve()
        purelib = Path(sysconfig.get_paths()["purelib"]).resolve()
        assert origin.is_relative_to(purelib), (origin, purelib)
        sizes = {
            name: len((files("mamey") / name).read_bytes())
            for name in ("evidence_disagreements.html", "enzyme_neighborhoods.html")
        }
        assert all(sizes.values()), sizes
        print(json.dumps({"origin": str(origin), "purelib": str(purelib), "sizes": sizes}))
        """
    )
    proc = _run([str(python), "-I", "-c", code], cwd=outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    observed = json.loads(proc.stdout)
    assert "site-packages" in observed["origin"]


def test_offline_isolated_build_resolves_from_complete_bundled_wheels(tmp_path: Path):
    source = _source_copy(tmp_path)
    out = tmp_path / "dist"
    out.mkdir()
    proc = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-index",
            "--find-links",
            str(source / "wheels"),
            "--wheel-dir",
            str(out),
            str(source),
        ],
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(list(out.glob("mamey-*.whl"))) == 1


def test_offline_isolated_build_refuses_without_wheel_transitive_dependency(tmp_path: Path):
    source = _source_copy(tmp_path)
    incomplete = tmp_path / "incomplete-build-wheels"
    incomplete.mkdir()
    for pattern in ("setuptools-*.whl", "wheel-*.whl"):
        matches = list((source / "wheels").glob(pattern))
        assert len(matches) == 1, matches
        shutil.copy2(matches[0], incomplete / matches[0].name)
    out = tmp_path / "dist"
    out.mkdir()
    proc = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-index",
            "--find-links",
            str(incomplete),
            "--wheel-dir",
            str(out),
            str(source),
        ],
        cwd=tmp_path,
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode != 0, combined
    assert "packaging" in combined and "24.0" in combined, combined


def test_bundled_packaging_wheel_is_manifested_and_licensed():
    wheel = WHEELS / "packaging-26.3-py3-none-any.whl"
    assert wheel.is_file()
    with zipfile.ZipFile(wheel) as archive:
        metadata = archive.read("packaging-26.3.dist-info/METADATA").decode("utf-8")
        names = set(archive.namelist())
    assert "License-Expression: Apache-2.0 OR BSD-2-Clause" in metadata
    assert "packaging-26.3.dist-info/licenses/LICENSE.APACHE" in names
    assert "packaging-26.3.dist-info/licenses/LICENSE.BSD" in names
    manifest = (WHEELS / "WHEELS_MANIFEST.md").read_text(encoding="utf-8")
    assert "d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c" in manifest


def test_bootstrap_quotes_python_executable_path_with_spaces(tmp_path: Path):
    shim_dir = tmp_path / "python shim with spaces"
    shim_dir.mkdir()
    shim = shim_dir / "fake python"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"--version\" ]; then echo 'Python 3.12.99'; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    env = dict(os.environ, PYTHON=str(shim))
    proc = _run(["bash", str(BOOTSTRAP)], cwd=ROOT, env=env, timeout=30)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "==> python: Python 3.12.99" in proc.stdout
    assert "No such file or directory" not in proc.stderr


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--wheels"], "--wheels requires a local dependency directory"),
        (["--wheels", "does-not-exist"], "offline wheel directory not found"),
        (["--wheels", "--help"], "--wheels value must be a directory path, not another option"),
    ],
)
def test_bootstrap_refuses_invalid_wheel_directory_arguments(arguments: list[str], message: str):
    proc = _run(["bash", str(BOOTSTRAP), *arguments], cwd=ROOT, timeout=30)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert message in proc.stderr


def test_ci_installed_wheel_smoke_escapes_checkout_and_checks_all_entrypoints():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert 'python -m venv "$RUNNER_TEMP/mamey-wheel-smoke"' in workflow
    assert 'cd "$RUNNER_TEMP"' in workflow
    for command in ("mamey", "sapote-render", "sapote-documents"):
        assert f'bin/{command}"' in workflow
    for resource in ("evidence_disagreements.html", "enzyme_neighborhoods.html"):
        assert resource in workflow

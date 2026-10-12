"""Synthetic shell routes bind one Python invocation despite another Python on PATH."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import venv

import pytest

from ._python_fixture_launcher import write_python_fixture
from .test_442_make_verified_code_tarball_codex import _inputs, _route

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def shell_runtime(tmp_path):
    # A real isolated venv, not a wrapper resolving away the selected invocation.
    selected = tmp_path / "selected venv 'quoted' $ literal"
    venv.EnvBuilder(with_pip=False, symlinks=True).create(selected)
    python = selected / "bin/python"
    packages = selected / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    # Reuse installed render dependencies read-only; no installation or network access.
    import PIL
    import reportlab
    dependency_roots = sorted({str(Path(module.__file__).resolve().parent.parent)
                               for module in (PIL, reportlab)})
    (packages / "render-dependencies.pth").write_text("\n".join(dependency_roots) + "\n")
    # The call logger loads through a .pth import line, not sitecustomize.py: some base interpreters (conda)
    # ship their own stdlib sitecustomize, which shadows one placed in the venv and silently disables the log.
    (packages / "shell_python_call_log.py").write_text(
        "import json,os,sys\n"
        "with open(os.environ['SHELL_PYTHON_CALL_LOG'], 'a', encoding='utf-8') as log:\n"
        "    log.write(json.dumps({'argv':sys.argv, 'python':sys.executable, "
        "'prefix':sys.prefix, 'selection':os.environ.get('PYTHON')}) + '\\n')\n")
    (packages / "shell_python_call_log.pth").write_text("import shell_python_call_log\n")
    bins = tmp_path / "path bins"
    bins.mkdir()
    poison = tmp_path / "poison-called.txt"
    (bins / "python3").write_text(
        '#!/bin/sh\nprintf "poisoned python3\\n" >> "$SHELL_PYTHON_POISON_LOG"\nexit 97\n')
    (bins / "python3").chmod(0o755)
    log = tmp_path / "python-calls.jsonl"
    env = dict(os.environ, PATH=str(bins) + os.pathsep + os.environ.get("PATH", ""),
               SHELL_PYTHON_CALL_LOG=str(log), SHELL_PYTHON_POISON_LOG=str(poison))
    # Ambient Python startup overrides must not defeat the isolated venv assertion.
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    return {"python": python, "venv": selected, "bins": bins, "poison": poison,
            "log": log, "env": env}


def _selected_environment(runtime, selection):
    env = runtime["env"].copy()
    if selection == "explicit":
        env["PYTHON"] = str(runtime["python"])
    else:
        env.pop("PYTHON", None)
        # Legacy default remains a single python3 lookup in the caller's PATH.
        python = str(runtime["python"])
        write_python_fixture(runtime["bins"] / "python3",
                             f"import os,sys\nos.execv({python!r}, [{python!r}] + sys.argv[1:])\n")
    return env


def _calls(runtime, selection):
    assert not runtime["poison"].exists(), "PATH Python must not replace an explicit selection"
    calls = [json.loads(line) for line in runtime["log"].read_text().splitlines()]
    assert calls
    expected = str(runtime["python"]) if selection == "explicit" else "python3"
    for call in calls:
        assert call["python"] == str(runtime["python"])
        assert call["prefix"] == str(runtime["venv"])
        assert call["selection"] == expected
    return calls


@pytest.mark.parametrize("selection", ["explicit", "default"])
def test_verified_pair_and_nested_archive_checker_use_bound_spaced_venv(tmp_path, shell_runtime, selection):
    source, sealed_zip, receipt, out = _inputs(tmp_path)
    result = _route(source, sealed_zip, receipt, out,
                    env=_selected_environment(shell_runtime, selection))
    assert result.returncode == 0, result.stdout + result.stderr
    archive = out / (source.name + ".tar.gz")
    sidecar = out / (source.name + ".tar.gz.sha256")
    assert sidecar.read_text().split()[0] == hashlib.sha256(archive.read_bytes()).hexdigest()
    with tarfile.open(archive, "r:gz") as tar:
        assert source.name + "/mamey_run.py" in tar.getnames()
    calls = _calls(shell_runtime, selection)
    assert [Path(call["argv"][0]).name for call in calls] == [
        "-c", "-c", "-", "verify_release_tarball.py", "publish_verified_pair.py"]


@pytest.mark.parametrize("selection", ["explicit", "default"])
def test_real_primary_pdf_uses_bound_spaced_venv(tmp_path, shell_runtime, selection):
    source = tmp_path / "input space"
    source.mkdir()
    md = source / "report.md"
    md.write_text("# Bound Python\n\nSynthetic rendering fixture.\n")
    caller = tmp_path / "unrelated caller"
    caller.mkdir()
    out = tmp_path / "output space" / "report.pdf"
    result = subprocess.run(["bash", str(ROOT / "tools/md_to_pdf.sh"), str(md), str(out)],
                            cwd=caller, env=_selected_environment(shell_runtime, selection),
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "colorful reportlab" in result.stdout
    assert out.read_bytes().startswith(b"%PDF") and out.stat().st_size > 1000
    calls = _calls(shell_runtime, selection)
    assert [Path(call["argv"][0]).name for call in calls] == [
        "-c", "-c", "-c", "render_deliverable_pdf.py"]


def _command(route, source, sealed_zip, receipt, out, md):
    if route == "pdf":
        return ["bash", str(ROOT / "tools/md_to_pdf.sh"), str(md), str(out / "report.pdf")]
    if route == "producer":
        return ["bash", str(ROOT / "tools/make_release_tarball.sh"), str(source), str(out)]
    return ["bash", str(ROOT / "tools/make_verified_code_tarball.sh"),
            str(source), str(out), str(sealed_zip), str(receipt)]


@pytest.mark.parametrize("route", ["pdf", "producer", "verified"])
@pytest.mark.parametrize("selection", ["missing", "incompatible", "argument_string"])
def test_invalid_selected_python_refuses_before_creating_output(tmp_path, route, selection):
    source, sealed_zip, receipt, out = _inputs(tmp_path)
    md = tmp_path / "report.md"
    md.write_text("# Synthetic input\n")
    if selection == "missing":
        python = str(tmp_path / "missing interpreter")
    elif selection == "incompatible":
        # Execute the real preflight expression under a deliberately old version tuple.
        wrapper = tmp_path / "incompatible Python"
        write_python_fixture(wrapper,
                             "import sys\n"
                             "if len(sys.argv) > 1 and sys.argv[1] == '-c':\n"
                             "    sys.version_info = (3, 11, 0)\n"
                             "    exec(sys.argv[2])\n"
                             "raise SystemExit(99)\n")
        python = str(wrapper)
    else:
        python = sys.executable + " -I"  # One executable locator, not a command string.
    result = subprocess.run(_command(route, source, sealed_zip, receipt, out, md),
                            env=dict(os.environ, PYTHON=python),
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert "REFUSED: Python 3.12 or newer required" in result.stderr
    assert "PYTHON executable unavailable or incompatible: " + python in result.stderr
    assert not out.exists(), "Invalid selection must refuse before output-directory creation"


@pytest.mark.parametrize("route", ["pdf", "producer", "verified"])
def test_invalid_selected_python_preserves_existing_output(tmp_path, route):
    source, sealed_zip, receipt, out = _inputs(tmp_path)
    md = tmp_path / "report.md"
    md.write_text("# Synthetic input\n")
    out.mkdir()
    existing = {"report.pdf": b"existing PDF", source.name + ".tar.gz": b"existing archive",
                source.name + ".tar.gz.sha256": b"existing sidecar"}
    for name, content in existing.items():
        (out / name).write_bytes(content)
    result = subprocess.run(_command(route, source, sealed_zip, receipt, out, md),
                            env=dict(os.environ, PYTHON=str(tmp_path / "missing interpreter")),
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 2 and "REFUSED: Python 3.12 or newer required" in result.stderr
    assert result.stdout == ""
    assert {path.name: path.read_bytes() for path in out.iterdir()} == existing

"""v9.7.401: bootstrap's core fallback must install Mamey, not only dependencies.

The primary ``.[all]`` editable install may fail when optional compiled wheels are absent from an
offline wheel directory. The fallback must still perform an editable core install so the
``mamey`` console entry point and package metadata exist outside the source tree. A source-tree
smoke test alone cannot prove that installation happened because local imports resolve from the
current working directory.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "bootstrap.sh"


def test_all_extra_failure_falls_back_to_editable_core_install(tmp_path):
    if not BOOTSTRAP.is_file():
        pytest.skip("bootstrap.sh is a source-bundle surface and is not shipped in the sdist")
    shim_dir = tmp_path / "python shim with spaces"
    shim_dir.mkdir()
    shim = shim_dir / "fake python"
    log = tmp_path / "python-invocations.log"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$FAKE_PYTHON_LOG\"\n"
        "if [ \"${*: -1}\" = \".[all]\" ]; then exit 1; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)

    env = dict(os.environ)
    env["PYTHON"] = str(shim)
    env["FAKE_PYTHON_LOG"] = str(log)
    proc = subprocess.run(
        ["bash", str(BOOTSTRAP)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    calls = log.read_text(encoding="utf-8").splitlines()
    all_index = next(i for i, call in enumerate(calls) if call.endswith("-e .[all]"))
    assert calls[all_index + 1].endswith("-e ."), calls
    assert not calls[all_index + 1].endswith("openpyxl ijson"), calls

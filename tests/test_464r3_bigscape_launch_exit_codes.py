"""bigscape_launch.sh: launcher codes never collide with BiG-SCAPE's own; all pressed Pfam companions are required."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / "tools" / "bigscape_launch.sh"


def _fixture(tmp_path, external_rc, companions=("h3f", "h3i", "h3m", "h3p")):
    envbin = tmp_path / "env" / "bin"
    envbin.mkdir(parents=True)
    (envbin / "bigscape").write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then echo 'fixture 2'; exit 0; fi\n"
        "while [ \"$#\" -gt 0 ]; do if [ \"$1\" = \"-o\" ]; then shift; out=$1; fi; shift; done\n"
        "echo 'fixture log' > \"$out/run.log\"\n"
        f"exit {external_rc}\n", encoding="utf-8")
    (envbin / "fasttree").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    for name in ("bigscape", "fasttree"):
        (envbin / name).chmod(0o755)
    pfam = tmp_path / "Pfam-A.hmm"
    pfam.touch()
    for ext in companions:
        (tmp_path / f"Pfam-A.hmm.{ext}").touch()
    inp = tmp_path / "input"
    inp.mkdir()
    (inp / "q.region001.gbk").touch()
    env = os.environ.copy()
    env.update({"BIGSCAPE_ENV_BIN": str(envbin), "PFAM_HMM": str(pfam)})
    return subprocess.run(["bash", str(LAUNCHER), str(inp), str(tmp_path / "out"), "--label", "fx"],
                          capture_output=True, text=True, env=env)


@pytest.mark.parametrize("external_rc", [2, 3, 4, 1, 7])
def test_external_failure_gets_its_own_launcher_code(tmp_path, external_rc):
    r = _fixture(tmp_path, external_rc)
    assert r.returncode == 5, r.stderr
    assert f"BIGSCAPE_EXIT={external_rc}" in r.stdout
    assert "LAUNCHER_STAGE=bigscape" in r.stderr


def test_external_success_is_zero(tmp_path):
    r = _fixture(tmp_path, 0)
    assert r.returncode == 0, r.stderr


def test_missing_pressed_companion_is_a_setup_error(tmp_path):
    r = _fixture(tmp_path, 0, companions=("h3i",))
    assert r.returncode == 2
    assert "LAUNCHER_STAGE=setup" in r.stderr and "h3f" in r.stderr
    assert not (tmp_path / "out").exists()

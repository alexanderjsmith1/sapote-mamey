"""A successful external exit is insufficient if requested MIBiG references did not load."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest


LAUNCHER = Path(__file__).resolve().parents[1] / "tools" / "bigscape_launch.sh"


@pytest.mark.parametrize(
    ("log_line", "expected_code"),
    [
        ("Loading 2088 mibig GBKs", 0),
        ("Loading 0 mibig GBKs", 4),
        ("MIBiG load message absent", 4),
    ],
)
def test_requested_mibig_must_have_positive_loaded_count(tmp_path, log_line, expected_code):
    envbin = tmp_path / "env" / "bin"
    envbin.mkdir(parents=True)
    package = tmp_path / "fake_big_scape"
    package.mkdir()
    (envbin / "python").write_text(
        '#!/bin/sh\nprintf "%s\\n" "$FAKE_BIGSCAPE_PKG"\n', encoding="utf-8"
    )
    (envbin / "bigscape").write_text(
        """#!/bin/sh
if [ "$1" = "--version" ]; then echo 'BiG-SCAPE fixture 2'; exit 0; fi
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then shift; out=$1; fi
  shift
done
printf '%s\\n' "$FAKE_LOAD_LINE" > "$out/run.log"
exit 0
""",
        encoding="utf-8",
    )
    (envbin / "fasttree").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    for name in ("python", "bigscape", "fasttree"):
        (envbin / name).chmod(0o755)

    pfam = tmp_path / "Pfam-A.hmm"
    pfam.touch()
    (tmp_path / "Pfam-A.hmm.h3i").touch()
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "query.region001.gbk").touch()
    mibig = tmp_path / "mibig"
    mibig.mkdir()
    # The existing launcher requires >=2,000 input files. Tiny fixture files
    # exercise that input check without downloading the real database.
    for index in range(2000):
        (mibig / f"BGC{index:07d}.gbk").touch()
    output = tmp_path / "out"
    env = os.environ.copy()
    env.update({
        "BIGSCAPE_ENV_BIN": str(envbin),
        "PFAM_HMM": str(pfam),
        "FAKE_BIGSCAPE_PKG": str(package),
        "FAKE_LOAD_LINE": log_line,
    })
    result = subprocess.run(
        ["bash", str(LAUNCHER), str(input_dir), str(output),
         "--mibig-dir", str(mibig), "--mibig-name", "fixture"],
        env=env, text=True, capture_output=True, check=False,
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    assert (output / "run.log").read_text().strip() == log_line
    if expected_code:
        assert "did not prove a positive loaded MIBiG GBK count" in result.stderr

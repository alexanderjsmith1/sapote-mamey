from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_llm_companion_instruction_gate() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/audit_llm_companion_instructions.py"),
            "--bundle-root",
            str(ROOT),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "PASS"
    assert report["failures"] == 0
    assert report["checks"] >= 20

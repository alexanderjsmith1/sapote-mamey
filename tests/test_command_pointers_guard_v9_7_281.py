"""v9.7.281 (patch 46): the phantom-command guard passes on the shipped tree (no backticked
`mamey <token>` that isn't a live subcommand). This is the CI gate for F-01/F-02 class defects."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_no_phantom_mamey_command_pointers():
    r = subprocess.run([sys.executable, "tools/check_command_pointers.py"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"phantom command pointers found:\n{r.stdout}\n{r.stderr}"

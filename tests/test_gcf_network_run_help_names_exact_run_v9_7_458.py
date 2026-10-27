"""`figures gcf-network --run` help must not tell readers to take the largest run id.

The companion-tool protocol says to select the exact completed run and never blindly use the
maximum database id. The help text used to say "largest/latest is authoritative".
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gcf_network_run_help_names_exact_completed_run():
    out = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "figures", "gcf-network", "--help"],
                         cwd=ROOT, capture_output=True, text=True, timeout=120)
    text = " ".join((out.stdout + out.stderr).split())
    assert out.returncode == 0, text[-500:]
    assert "largest/latest is authoritative" not in text
    assert "exact completed BiG-SCAPE run id" in text

"""User-facing help uses American spelling (house rule): emit-modeb-template --help."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_emit_modeb_template_help_uses_american_spelling():
    out = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "emit-modeb-template", "--help"],
                         cwd=ROOT, capture_output=True, text=True, timeout=120)
    text = " ".join((out.stdout + out.stderr).split())
    assert out.returncode == 0, text[-500:]
    assert "neighbourhood" not in text
    assert "supported-anchor neighborhoods" in text

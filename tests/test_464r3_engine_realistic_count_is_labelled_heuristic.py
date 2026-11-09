"""`realistic-count` is described as a heuristic merged count, never a corrected BGC denominator."""
import subprocess
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]


def test_help_says_heuristic_and_not_a_validated_count():
    out = subprocess.run([sys.executable, "mamey_run.py", "--help"], cwd=BUNDLE,
                         capture_output=True, text=True, timeout=120).stdout
    text = " ".join(out.split())
    assert "corrected-denominator" not in text
    assert "heuristic merged-region count" in text
    assert "not a validated count of loci" in text


def test_tool_description_is_heuristic():
    out = subprocess.run([sys.executable, str(BUNDLE / "tools" / "realistic_bgc_count.py"), "--help"],
                         capture_output=True, text=True, timeout=120).stdout
    assert "corrected-denominator" not in out
    assert "Heuristic merged-region BGC count" in out

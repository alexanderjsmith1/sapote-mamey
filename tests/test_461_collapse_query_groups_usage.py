"""Cold help and incomplete arguments must not reach tree or annotation reads."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/collapse_query_groups.py"


def test_help_exits_successfully_without_input_files():
    result = subprocess.run([sys.executable, "-B", str(TOOL), "--help"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout and "annotation" in result.stdout and "out_prefix" in result.stdout
    assert "Traceback" not in result.stderr


def test_incomplete_arguments_have_usage_error():
    result = subprocess.run([sys.executable, "-B", str(TOOL)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2
    assert "usage:" in result.stderr and "Traceback" not in result.stderr

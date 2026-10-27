"""CLI usage must be parsed before the advisory tree inspection starts."""
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/signoff_check.py"


def invoke(tmp_path, *args):
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=tmp_path,
                          capture_output=True, text=True, timeout=10)


def test_help_does_not_inspect_a_file(tmp_path):
    result = invoke(tmp_path, "--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "could not parse" not in result.stdout


@pytest.mark.parametrize("args", [("--minutes",), ("--root",), ("--outgroup",),
                                  ("--minutes", "wrong"), ("--not-an-option",)])
def test_bad_usage_is_a_parser_error(tmp_path, args):
    result = invoke(tmp_path, *args)
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_findings_remain_advisory(tmp_path):
    result = invoke(tmp_path, "missing.treefile")
    assert result.returncode == 0
    assert "could not parse" in result.stdout


def test_explicit_root_and_quiet_empty_scan(tmp_path):
    result = invoke(tmp_path, "--root", str(tmp_path), "--minutes", "1.5", "--quiet-if-clean")
    assert result.returncode == 0
    assert result.stdout == ""


def test_repeatable_outgroups_stay_supported(tmp_path):
    tree = tmp_path / "tree.treefile"
    tree.write_text("((Streptomyces_a_1:1,Streptomyces_b_2:1)90:1,(Nocardia_a_3:1,Nocardia_b_4:1)95:1);")
    result = invoke(tmp_path, "--outgroup", "Nocardia_a_3", "--outgroup", "Nocardia_b_4", str(tree))
    assert result.returncode == 0
    assert "no _OUTGROUP-tagged tip" not in result.stdout

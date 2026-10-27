"""tools/export_figure_ready.py and tools/plot_examples.py answer --help with usage (exit 0), not a traceback.

Before: "--help" was read as a file path and ended in FileNotFoundError. The positional use is unchanged:
export_figure_ready.py <workbook> [out_dir], plot_examples.py [figure_ready_dir].
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("export_figure_ready.py", "plot_examples.py")


def _run(tool, *args):
    return subprocess.run([sys.executable, str(ROOT / "tools" / tool), *args], capture_output=True, text=True,
                          timeout=120, cwd=str(ROOT))


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage_and_exits_zero(tool, flag):
    out = _run(tool, flag)
    assert out.returncode == 0, out.stderr[-500:]
    assert out.stdout.startswith("usage:") and tool in out.stdout
    assert "Traceback" not in out.stderr and "FileNotFoundError" not in out.stderr


def test_export_positional_reaches_main(tmp_path):
    missing = tmp_path / "no_such_master.xlsx"
    out = _run("export_figure_ready.py", str(missing), str(tmp_path / "out"))
    assert out.returncode != 0
    assert str(missing) in out.stderr          # the first positional is still the workbook path
    assert "unrecognized" not in out.stderr and "usage:" not in out.stderr


def test_export_without_arguments_still_prints_the_docstring_and_exits_one():
    out = _run("export_figure_ready.py")
    assert out.returncode == 1
    assert "Usage:  python tools/export_figure_ready.py <master_workbook.xlsx> [out_dir]" in out.stdout + out.stderr


def test_plot_examples_positional_is_still_the_figure_ready_dir(tmp_path):
    pytest.importorskip("matplotlib")
    out = _run("plot_examples.py", str(tmp_path), "extra-words-are-ignored")
    assert out.returncode != 0                  # no CSVs there, so it stops at the first load ...
    assert str(tmp_path / "strain_summary.csv") in out.stderr   # ... and names the folder it was given
    assert "usage:" not in out.stderr

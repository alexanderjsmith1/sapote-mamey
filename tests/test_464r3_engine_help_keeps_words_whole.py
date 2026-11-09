"""Help text wraps at spaces only, so folder names survive a narrow terminal.

In a 40-column terminal argparse split `domain_level/figures/` into `doma` and
`in_level/figures/`, and `test_render_figures_outdir_help_names_each_set_default` failed.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_narrow_terminal_keeps_folder_names_whole():
    env = {**os.environ, "COLUMNS": "40"}
    out = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "render-figures", "--help"],
                         cwd=ROOT, capture_output=True, text=True, timeout=120, env=env).stdout
    words = out.split()
    for folder in ("figures_rendered/,", "domain_level/figures/,", "locus_maps/,", "cohort_figures/,"):
        assert folder in words, folder

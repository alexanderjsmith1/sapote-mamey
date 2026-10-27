"""`render-figures --outdir` help must give each figure set's real default folder
(mamey/chatgpt_commands.py render_figures_command), not one folder for all sets."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_render_figures_outdir_help_names_each_set_default():
    out = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "render-figures", "--help"],
                         cwd=ROOT, capture_output=True, text=True, timeout=120)
    text = " ".join((out.stdout + out.stderr).split())
    assert out.returncode == 0, text[-500:]
    for folder in ("figures_rendered/", "domain_level/figures/", "locus_maps/", "cohort_figures/",
                   "mamey_native_figures/"):
        assert folder in text, folder

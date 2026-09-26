"""The DAPR boards draw no claim wording; the ceiling goes to the caption sidecar (Alex, 2026-09-24).

tools/render_dapr_boards.py drew each board's note with ax.text, and main() built both notes with
"Class-level hypotheses; ...". The wording reached the canvas through a function argument, so no
literal draw-call scan listed it, and no test rendered the tool. Generic rows; runs the real CLI.
"""
import csv
import os
import pathlib
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")

BUNDLE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUNDLE))
TOOL = BUNDLE / "tools" / "render_dapr_boards.py"

BOARD_COLS = ["AN_Score", "strain", "BGC_ID", "Product_Class", "KCB_Provenance", "Rationale"]
FRAG_COLS = ["Tier", "Frag_Loss", "EFLS_Pairs", "RG_GMCI_HIGH"]


def _write(path, cols, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(rows)


def test_boards_draw_no_claim_text_and_keep_the_ceiling_in_the_caption(tmp_path):
    data, out = tmp_path / "data", tmp_path / "out"
    data.mkdir()
    row = ["3", "GEN-1", "GEN-1_r1", "T2PKS", "KCB~x", "data note"]
    _write(data / "c1_dapr_antibacterial.csv", BOARD_COLS, [row])
    _write(data / "c2_dapr_antifungal.csv", BOARD_COLS, [row])
    _write(data / "fragment_rescue_tiers.csv", FRAG_COLS, [["A", "1", "2", "3"]])
    probe = (
        "import runpy, sys\n"
        "import matplotlib; matplotlib.use('Agg')\n"
        "from matplotlib.figure import Figure\n"
        "from mamey.figure_policy import figure_text_violations, matplotlib_visible_text\n"
        "found = []\n"
        "orig = Figure.savefig\n"
        "def spy(self, *a, **k):\n"
        "    found.extend(figure_text_violations(matplotlib_visible_text(self)))\n"
        "    return orig(self, *a, **k)\n"
        "Figure.savefig = spy\n"
        f"sys.argv = ['render_dapr_boards.py', '--data', {str(data)!r}, '--out', {str(out)!r}]\n"
        f"runpy.run_path({str(TOOL)!r}, run_name='__main__')\n"
        "print('BANNED_DRAWN=' + repr(sorted(set(f.lower() for f in found))))\n"
    )
    env = dict(os.environ, PYTHONPATH=str(BUNDLE), MPLBACKEND="Agg")
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=env, cwd=BUNDLE)
    assert r.returncode == 0, r.stderr
    assert "BANNED_DRAWN=[]" in r.stdout, r.stdout
    for stem in ("fig_dapr_antibacterial", "fig_dapr_antifungal"):
        assert (out / f"{stem}.png").is_file()
        assert "Class-level hypotheses" in (out / f"{stem}_caption.txt").read_text()

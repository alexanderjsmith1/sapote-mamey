"""M5_452: tools/sapote_pub_layout.R save_pub() caption band. The internal notes were printed at 6.8 pt (BiG-SLiCE v5 figures failed the
8 pt read-back, 13 Oct 2026); FIGURE_STYLE.md publication artwork gate and the 8 pt floor: every text run in the saved PDF >= 8 pt.
Synthetic figure only."""
import math, shutil, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
needs_r = pytest.mark.skipif(not shutil.which("Rscript"), reason="Rscript unavailable")


def smallest_pt(pdf):
    from pypdf import PdfReader
    sizes = []
    def visit(text, cm, tm, font, fs):
        if text and text.strip():
            a, b, c, d = (cm[0] * tm[0] + cm[2] * tm[1], cm[1] * tm[0] + cm[3] * tm[1], cm[0] * tm[2] + cm[2] * tm[3], cm[1] * tm[2] + cm[3] * tm[3])
            sizes.append(fs * math.sqrt(abs(a * d - b * c)))
    PdfReader(str(pdf)).pages[0].extract_text(visitor_text=visit)
    return min(sizes)


@needs_r
def test_save_pub_internal_notes_are_at_least_8pt(tmp_path):
    (tmp_path / "pub.md").write_text("A synthetic public caption for the test figure.\n")
    (tmp_path / "int.md").write_text("Synthetic internal notes: tool versions, cutoffs and paths go here.\n")
    script = tmp_path / "t.R"
    script.write_text('suppressPackageStartupMessages(library(ggplot2))\n'
                      f'source("{ROOT / "tools/sapote_pub_layout.R"}")\n'
                      'p <- ggplot(data.frame(x = 1:3, y = 1:3), aes(x, y)) + geom_point() + theme_pub()\n'
                      f'save_pub(p, "FIG_TEST", "{tmp_path / "pub.md"}", "{tmp_path / "int.md"}", w = 7.2, h_body = 3, outdir = "{tmp_path / "out"}")\n')
    r = subprocess.run(["Rscript", str(script)], capture_output=True, text=True, env={"LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
                       "PATH": __import__("os").environ["PATH"], "HOME": str(tmp_path),
                       "PYTHONDONTWRITEBYTECODE": "1"})  # hermetic: no bytecode from any Python the child starts (J5 owner hold #219)
    assert r.returncode == 0, r.stderr
    assert smallest_pt(tmp_path / "out" / "FIG_TEST.pdf") >= 7.95

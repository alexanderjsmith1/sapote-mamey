"""Card attine_452_t01_whole_number_count_axis: the 16S histogram (T01) counts isolates, so its y-axis ticks are whole numbers.

With small counts ggplot's default breaks fall on halves (2.5, 7.5). The axis now keeps the default breaks when they are
whole and otherwise uses whole-number pretty breaks. Synthetic IDs only.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/taxonomy_T01_figures.py"


def render(tmp_path, values):
    cohort, data = tmp_path / "cohort.tsv", tmp_path / "data.tsv"
    cohort.write_text("strain\tgenus\tblock\n" + "".join(f"AS-9{70 + i}\tStreptomyces\tisolates\n" for i in range(len(values))))
    data.write_text("strain\tsimilarity\n" + "".join(f"AS-9{70 + i}\t{v}\n" for i, v in enumerate(values)))
    out = tmp_path / "fig"
    r = subprocess.run([sys.executable, str(TOOL), "--cohort", str(cohort), "--data", str(data), "--out", str(out),
                        "--layout", "moss", "--palette-set", "moss", "--dpi", "72"], capture_output=True, text=True, timeout=180)
    return r, out


def pdf_text(pdf):
    pypdf = pytest.importorskip("pypdf")
    return " ".join(p.extract_text() for p in pypdf.PdfReader(str(pdf)).pages)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_small_counts_get_whole_number_ticks(tmp_path):
    r, out = render(tmp_path, [99.9] * 7 + [98.0, 97.0])
    assert r.returncode == 0, r.stdout + r.stderr
    text = pdf_text(out.with_suffix(".pdf"))
    assert "2.5" not in text and "7.5" not in text
    assert "6" in text


def test_the_breaks_rule_keeps_whole_default_breaks():
    src = TOOL.read_text()
    assert "b[b == round(b)]" in src and "scales::breaks_extended()(l)" in src

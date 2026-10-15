"""Card attine_452_t06_legend_grid: the 16S-against-dDDH plot (T06) can lay its genus key out in --legend-columns columns,
filled row by row, so six genera make a 2 x 3 grid at a wide print width. The key was fixed at four rows (4 + 2 for six
genera); that stays the default, because three columns of long genus names do not fit one column (3.5 in) at 8 pt.
Synthetic IDs only."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERA = ["Streptomyces", "Pseudonocardia", "Pseudonocardiaceae", "Kribbella", "Amycolatopsis", "Actinophytocola"]


def render(tmp_path, *extra):
    cohort, data = tmp_path / "cohort.tsv", tmp_path / "data.tsv"
    cohort.write_text("strain\tgenus\tblock\n" + "".join(f"AS-{970 + i}\t{g}\tisolates\n" for i, g in enumerate(GENERA)))
    data.write_text("strain\tsimilarity\td4\n" + "".join(f"AS-{970 + i}\t{95.5 + i * 0.7:.2f}\t{30 + i * 9}\n" for i in range(6)))
    out = tmp_path / "fig"
    r = subprocess.run([sys.executable, str(ROOT / "tools/taxonomy_T06_figures.py"), "--cohort", str(cohort), "--data",
                        str(data), "--out", str(out), "--layout", "moss", "--palette-set", "attine", "--dpi", "72", *extra],
                       capture_output=True, text=True, timeout=300)
    return r, out


def key_rows(pdf):
    """Distinct baselines (rounded) of the genus names in the key."""
    pypdf = pytest.importorskip("pypdf")
    ys = []

    def visit(text, cm, tm, font, size):
        if text.strip() in GENERA:
            ys.append(round(tm[5] * cm[3] + cm[5]))
    for page in pypdf.PdfReader(str(pdf)).pages:
        page.extract_text(visitor_text=visit)
    return sorted(set(ys))


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_six_genera_make_two_rows_of_three(tmp_path):
    r, out = render(tmp_path, "--legend-columns", "3", "--print-width", "7.2")
    assert r.returncode == 0, r.stderr[-2000:]
    assert len(key_rows(out.with_suffix(".pdf"))) == 2


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_two_columns_make_three_rows(tmp_path):
    r, out = render(tmp_path, "--legend-columns", "2", "--print-width", "7.2")
    assert r.returncode == 0, r.stderr[-2000:]
    assert len(key_rows(out.with_suffix(".pdf"))) == 3


def test_zero_columns_refused(tmp_path):
    r, _ = render(tmp_path, "--legend-columns", "0")
    assert r.returncode != 0 and "legend-columns" in r.stderr


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_default_key_keeps_four_rows(tmp_path):
    r, out = render(tmp_path)
    assert r.returncode == 0, r.stderr[-2000:]
    assert len(key_rows(out.with_suffix(".pdf"))) == 4

"""Card attine_452_t01_t06_legend_title: the 16S histogram (T01) and the 16S-against-dDDH plot (T06) take a key title.

Both keys were fixed to "Genus (16S rRNA)". A cohort with an isolate placed only to family (e.g. a
"Pseudonocardiaceae" row) needs another title. The default is unchanged. Synthetic IDs only.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TITLE = "Genus (16S rRNA; family where unresolved)"


def render(tmp_path, tool, *extra):
    cohort, data = tmp_path / "cohort.tsv", tmp_path / "data.tsv"
    cohort.write_text("strain\tgenus\tblock\n" + "".join(f"AS-{970 + i}\t{g}\tisolates\n" for i, g in
                                                         enumerate(["Streptomyces"] * 3 + ["Pseudonocardiaceae"] * 3)))
    rows = [(f"AS-{970 + i}", 95.5 + i * 0.7, 30 + i * 9) for i in range(6)]
    if tool == "T01":
        data.write_text("strain\tsimilarity\n" + "".join(f"{s}\t{v:.2f}\n" for s, v, _ in rows))
    else:
        data.write_text("strain\tsimilarity\td4\n" + "".join(f"{s}\t{v:.2f}\t{d}\n" for s, v, d in rows))
    out = tmp_path / "fig"
    r = subprocess.run([sys.executable, str(ROOT / f"tools/taxonomy_{tool}_figures.py"), "--cohort", str(cohort), "--data",
                        str(data), "--out", str(out), "--layout", "moss", "--palette-set", "attine", "--dpi", "72", *extra],
                       capture_output=True, text=True, timeout=300)
    return r, out


def pdf_text(pdf):
    pypdf = pytest.importorskip("pypdf")
    return " ".join(p.extract_text() for p in pypdf.PdfReader(str(pdf)).pages)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
@pytest.mark.parametrize("tool", ["T01", pytest.param("T06", marks=pytest.mark.needs_arial)])
def test_legend_title_option_is_drawn_and_recorded(tmp_path, tool):
    r, out = render(tmp_path, tool, "--legend-title", TITLE)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(out.with_name(out.name + "_run.json").read_text())["legend_title"] == TITLE
    assert "family where unresolved" in pdf_text(out.with_suffix(".pdf"))


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
@pytest.mark.parametrize("tool", ["T01", pytest.param("T06", marks=pytest.mark.needs_arial)])
def test_default_title_is_unchanged(tmp_path, tool):
    r, out = render(tmp_path, tool)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(out.with_name(out.name + "_run.json").read_text())["legend_title"] == "Genus (16S rRNA)"
    assert "Genus (16S rRNA)" in pdf_text(out.with_suffix(".pdf"))


@pytest.mark.parametrize("tool", ["T01", "T06"])
def test_empty_title_is_refused(tmp_path, tool):
    r, _ = render(tmp_path, tool, "--legend-title", " ")
    assert r.returncode != 0 and "--legend-title must not be empty" in r.stderr

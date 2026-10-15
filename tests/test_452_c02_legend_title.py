"""Card attine_452_c02_legend_title: the genus composition plot (C02) takes a key title.

The key was fixed to "Genus (16S rRNA)". A roster with an isolate placed only to family (e.g. a
"Pseudonocardiaceae" row) needs another title. The default is unchanged. Synthetic IDs only.
"""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/genus_composition_figures.py"
spec = importlib.util.spec_from_file_location("composition_lt", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def roster(tmp_path):
    p = tmp_path / "isolates.tsv"
    rows = [dict(strain=f"AS-{971 + i}", group=g, genus=x) for i, (g, x) in
            enumerate([("Atta", "Streptomyces"), ("Atta", "Pseudonocardiaceae"), ("Acromyrmex", "Streptomyces")])]
    module.write_tsv(p, ["strain", "group", "genus"], rows)
    return p


def pdf_text(pdf):
    pypdf = pytest.importorskip("pypdf")
    return " ".join(pg.extract_text() for pg in pypdf.PdfReader(str(pdf)).pages)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_legend_title_option_is_drawn_and_recorded(tmp_path):
    out = tmp_path / "render"
    assert module.main(["--isolates", str(roster(tmp_path)), "--out", str(out), "--layout", "attine", "--groups", "Atta",
                        "Acromyrmex", "--palette-set", "attine", "--legend-title", "Genus or family (16S rRNA)"]) == 0
    assert json.loads((out / "RUN_INFO.json").read_text())["legend_title"] == "Genus or family (16S rRNA)"
    assert "Genus or family" in pdf_text(out / "C02_genus_composition.pdf")


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_default_title_is_unchanged(tmp_path):
    out = tmp_path / "render"
    assert module.main(["--isolates", str(roster(tmp_path)), "--out", str(out), "--layout", "attine", "--groups", "Atta",
                        "Acromyrmex", "--palette-set", "attine"]) == 0
    assert json.loads((out / "RUN_INFO.json").read_text())["legend_title"] == "Genus (16S rRNA)"


def test_empty_title_is_refused(tmp_path):
    with pytest.raises(ValueError, match="must not be empty"):
        module.main(["--isolates", str(roster(tmp_path)), "--out", str(tmp_path / "r"), "--layout", "attine", "--groups",
                     "Atta", "Acromyrmex", "--legend-title", " "])

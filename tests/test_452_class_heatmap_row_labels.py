"""Card 452_class_heatmap_row_labels.

Owner review of the classes-per-genome heatmap (moss layout): one genus label spanning a block of rows was confusing,
so every row now carries its own label, the genus in italics plus an optional row_note from the genome table in
brackets. `--row-labels per-block` restores the block label. Synthetic inputs only.
"""
import csv
import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("renderer_rowlabels", ROOT / "tools/bgc_classes_per_genome.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def put(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return path


@pytest.fixture
def inputs(tmp_path):
    genomes = [dict(strain="SYN-971", genus="Streptomyces", block="Streptomyces", row_note="habitat a"),
               dict(strain="SYN-972", genus="Streptomyces", block="Streptomyces", row_note="habitat b"),
               dict(strain="SYN-973", genus="Pseudonocardia", block="Pseudonocardia (habitat c)", row_note="habitat c")]
    g = put(tmp_path / "genomes.tsv", genomes)
    d = put(tmp_path / "data.tsv", [dict(strain=r["strain"], genus=r["genus"], display=c, family=f, count=n)
                                    for r, n in zip(genomes, (3, 1, 0)) for c, f in [("NRPS", "NRPS"), ("PKS", "PKS")]])
    t = put(tmp_path / "totals.tsv", [dict(strain=r["strain"], genus=r["genus"], regions=4, contig_edge=1, pct_edge=25)
                                      for r in genomes])
    return g, d, t


def test_row_labels_put_genus_and_note_on_every_row():
    labels = m.row_labels([dict(strain="X1", genus="Streptomyces", row_note="habitat a"),
                           dict(strain="X2", genus="Streptomyces", row_note=""),
                           dict(strain="X3", genus="Genus<b>", row_note="a & b")])
    assert labels == {"X1": "<i>Streptomyces</i> (habitat a)", "X2": "<i>Streptomyces</i>",
                      "X3": "<i>Genus&lt;b&gt;</i> (a &amp; b)"}


def test_genome_table_without_row_note_still_reads():
    assert m.row_labels([dict(strain="X1", genus="Nocardia")]) == {"X1": "<i>Nocardia</i>"}


def _pdf_text(pdf):
    pypdf = pytest.importorskip("pypdf")
    # rich-text runs come back without their inner spaces, so compare with all whitespace removed
    return re.sub(r"\s+", "", "".join(p.extract_text() for p in pypdf.PdfReader(str(pdf)).pages))


def _run(tmp_path, inputs, *extra):
    g, d, t = inputs
    out = tmp_path / ("out" + "_".join(extra))
    assert m.main(["--genomes", str(g), "--data", str(d), "--totals", str(t), "--out", str(out), "--layout", "moss",
                   "--palette-set", "moss", "--comparators", "Pseudonocardia (habitat c)", "--dpi", "100", *extra]) == 0
    return out


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript unavailable")
def test_every_row_is_labelled_by_default(tmp_path, inputs):
    out = _run(tmp_path, inputs)
    assert json.loads((out / "render_config.json").read_text())["row_labels"]["SYN-972"] == "<i>Streptomyces</i> (habitat b)"
    text = _pdf_text(out / (m.TOOL + ".pdf"))
    assert len(re.findall(r"Streptomyces", text)) == 2
    assert "(habitata)" in text and "(habitatb)" in text and "(habitatc)" in text
    assert json.loads((out / "RUN_INFO.json").read_text())["row_labels"] == "each-row"


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript unavailable")
def test_per_block_restores_one_label_per_block(tmp_path, inputs):
    out = _run(tmp_path, inputs, "--row-labels", "per-block")
    assert json.loads((out / "render_config.json").read_text())["row_labels"] is None
    text = _pdf_text(out / (m.TOOL + ".pdf"))
    assert len(re.findall(r"Streptomyces", text)) == 1
    assert "(habitata)" not in text

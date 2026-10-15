"""Card attine_452_b03_comparators: named comparator genomes and an explicit row order in B03.

An isolate placed only to family had a row with no public genomes. The owner asked (13 Oct) for related genomes
beside it. region_protein_references.py --comparators adds them as role "comparator" rows, taken as given with their
source recorded. region_protein_by_genus.py draws them as labelled points (italic name, roman strain), never in a box;
open = yes draws an open symbol (explained in the caption). --row-order sets the rows top to bottom. Synthetic data only.
"""
import csv
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def _load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, ROOT / "tools" / name)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


rpg = _load("region_protein_by_genus.py", "b03_cmp")
rpr = _load("region_protein_references.py", "b03_cmp_refs")


def _tsv(path, cols, rows):
    path.write_text("\t".join(cols) + "\n" + "".join("\t".join(str(v) for v in r) + "\n" for r in rows))
    return path


def _inputs(tmp_path):
    classified = _tsv(tmp_path / "classified.tsv", ["genome_key", "role", "genus", "strictness", "aa", "regions", "source"],
                      [(f"GCA_00000{i}", "reference", "Genusa", "loose", 100000 + 9000 * i, 20, "syn") for i in range(6)])
    genera = _tsv(tmp_path / "genera.tsv", ["strain", "genus"], [("SYN-970", "Genusa"), ("SYN-971", "Familyb")])
    totals = _tsv(tmp_path / "totals.tsv", ["strain", "amino_acids", "missing_CDS_lengths"],
                  [("SYN-970", 150000, 0), ("SYN-971", 250000, 0)])
    comps = _tsv(tmp_path / "comps.tsv", ["strain", "genus", "name", "strain_label", "amino_acids", "missing_CDS_lengths",
                                          "open", "source"],
                 [("GCA_000000901", "Genusc", "Genusc alpha", "DSM 1", 300000, 0, "no", "synthetic"),
                  ("GCA_000000902", "Genusc", "Genusc", "sp. GCA_000000902", 40000, 0, "yes", "synthetic")])
    return classified, genera, totals, comps


def test_references_tool_adds_comparators_with_their_source(tmp_path):
    classified, genera, totals, comps = _inputs(tmp_path)
    out = tmp_path / "data.tsv"
    assert rpr.main(["--classified", str(classified), "--isolate-genera", str(genera), "--isolate-totals", str(totals),
                     "--comparators", str(comps), "--out", str(out)]) == 0
    rows = list(csv.DictReader(out.open(), delimiter="\t"))
    cmp = [r for r in rows if r["role"] == "comparator"]
    assert [(r["strain"], r["open"]) for r in cmp] == [("GCA_000000901", "no"), ("GCA_000000902", "yes")]
    assert all(r["name"] == "" for r in rows if r["role"] != "comparator")
    info = json.loads(out.with_name("data_RUN_INFO.json").read_text())
    assert info["comparators"][0]["source"] == "synthetic" and len(info["comparators_sha256"]) == 64
    out2 = tmp_path / "plain.tsv"            # without --comparators the table is the old five columns
    rpr.main(["--classified", str(classified), "--isolate-genera", str(genera), "--isolate-totals", str(totals),
              "--out", str(out2)])
    assert out2.read_text().splitlines()[0].split("\t") == rpr.COLUMNS


def test_row_order_must_name_every_genus_once():
    assert rpg.row_order_list(None, {"A", "B"}) == []
    assert rpg.row_order_list("B, A", {"A", "B"}) == ["B", "A"]
    with pytest.raises(ValueError, match="missing"):
        rpg.row_order_list("A", {"A", "B"})
    with pytest.raises(ValueError, match="once"):
        rpg.row_order_list("A,B,B", {"A", "B"})


def test_comparator_needs_a_name():
    row = dict(strain="X", genus="G", amino_acids="1000", missing_CDS_lengths="0", role="comparator", name="", open="no")
    with pytest.raises(ValueError, match="needs a name"):
        rpg.validate([dict(row, strain="Y", role="reference"), row])   # two rows: the scatter preflight needs >= 2


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript unavailable")
def test_comparators_are_drawn_labelled_in_the_given_row_order(tmp_path):
    classified, genera, totals, comps = _inputs(tmp_path)
    data = tmp_path / "data.tsv"
    rpr.main(["--classified", str(classified), "--isolate-genera", str(genera), "--isolate-totals", str(totals),
              "--comparators", str(comps), "--out", str(data)])
    cap = tmp_path / "c.md"; cap.write_text("Synthetic caption.\n")
    out = tmp_path / "out"
    assert rpg.main(["--data", str(data), "--caption", str(cap), "--out", str(out),
                     "--row-order", "Genusa,Familyb,Genusc"]) == 0
    text = PdfReader(out / "region_protein_by_genus.pdf").pages[0].extract_text().replace(" ", "")
    assert "Genuscalpha" in text and "DSM1" in text and "sp.GCA_000000902" in text and "(n=2)" in text
    assert text.index("Genusa") < text.index("Familyb") < text.index("Genusc(n")
    boxes = list(csv.DictReader((out / "region_protein_by_genus_box_summary.tsv").open(), delimiter="\t"))
    assert len(boxes) == 1                      # comparators are never boxed
    assert json.loads((out / "render_config.json").read_text())["row_order"] == ["Genusa", "Familyb", "Genusc"]

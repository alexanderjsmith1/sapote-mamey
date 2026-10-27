"""Card 452_chitin_isolate_vs_references_panel: the chitin-genes-vs-references panel (K01) as a bundle tool.

Synthetic census tables only (AS-971.. isolates, REF_* references).
"""
import csv
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("chitin_k01", ROOT / "tools/chitin_isolate_vs_references.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

COLS = ["genus", "role", "strain_id", "Glyco_hydro_18", "Glyco_hydro_19", "LPMO_10", "CBM_5_12", "cds_searched"]


def put(path, header, rows):
    with path.open("w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(header)
        w.writerows(rows)
    return path


@pytest.fixture
def world(tmp_path):
    iso = put(tmp_path / "iso.tsv", COLS, [
        ["Streptomyces", "isolate", "AS-971", 9, 6, 2, 1, 7000],
        ["Streptomyces", "isolate", "AS-972", 0, 0, 0, 0, 6500],          # a true zero must be drawn
        ["Kribbella", "isolate", "AS-973", 12, 3, 4, 2, 7200]])
    refs = [["Streptomyces", "reference", f"REF_S{i}", i % 7, i % 3, 1, 0, 6000] for i in range(10)]
    refs += [["Kribbella", "reference", f"REF_K{i}", 3 + i % 4, 1, 2, 1, 6800] for i in range(6)]
    ref = put(tmp_path / "ref.tsv", COLS, refs)
    gen = put(tmp_path / "genomes.tsv", ["strain", "genus", "row_note"],
              [["AS-971", "Streptomyces", "habitat a"], ["AS-972", "Streptomyces", "habitat b"], ["AS-973", "Kribbella", ""]])
    return dict(iso=iso, ref=ref, gen=gen, tmp=tmp_path)


def run(w, out, *extra):
    return m.main(["--genomes", str(w["gen"]), "--isolates", str(w["iso"]), "--references", str(w["ref"]),
                   "--out", str(out), "--dpi", "100", *extra])


def numbers(out):
    return list(csv.DictReader(open(out / f"{m.STEM}_numbers.tsv"), delimiter="\t"))


def test_panel_numbers_and_zero_rows(world):
    out = world["tmp"] / "out"
    assert run(world, out) == 0
    rows = numbers(out)
    assert len(rows) == 3 * len(m.FAMILIES)
    chit = {r["isolate"]: r for r in rows if r["family"] == "chitinases"}
    assert chit["AS-971"]["count"] == "15" and chit["AS-971"]["above_ref_max"] == "True"   # 9 + 6 over a max of 6 + 2
    assert chit["AS-972"]["count"] == "0"
    assert chit["AS-973"]["n_references"] == "6"
    info = json.loads((out / "RUN_INFO.json").read_text())
    assert info["references_per_genus"] == {"Streptomyces": 10, "Kribbella": 6}
    assert set(info["inputs"]) == {"genomes", "isolates", "references"}
    assert b"Sapote-Mamey chitin_isolate_vs_references" in (out / f"{m.STEM}.png").read_bytes()


def test_every_text_run_is_at_least_8_pt_at_print_width(world):
    pypdf = pytest.importorskip("pypdf")
    out = world["tmp"] / "out"
    run(world, out)
    reader = pypdf.PdfReader(str(out / f"{m.STEM}.pdf"))
    width_in = float(reader.pages[0].mediabox.width) / 72
    assert abs(width_in - 7.2) < 0.01
    sizes, text = [], []
    for page in reader.pages:
        def visit(t, cm, tm, font_dict, font_size):
            if t and t.strip():
                a, b, c, d = (cm[0] * tm[0] + cm[2] * tm[1], cm[1] * tm[0] + cm[3] * tm[1],
                              cm[0] * tm[2] + cm[2] * tm[3], cm[1] * tm[2] + cm[3] * tm[3])
                sizes.append(font_size * math.sqrt(abs(a * d - b * c)))
                text.append(t)
        page.extract_text(visitor_text=visit)
    assert sizes and min(sizes) >= 7.99
    joined = "".join(text).replace(" ", "")
    assert "AS-971(habitata)" in joined and "AS-973" in joined


@pytest.mark.parametrize("bad, msg", [("genus", "no reference genomes"), ("census", "no census row"), ("dup", "listed twice")])
def test_refusals(world, bad, msg, capsys):
    if bad == "genus":
        put(world["gen"], ["strain", "genus"], [["AS-971", "Streptomyces"], ["AS-973", "Nocardia"]])
    elif bad == "census":
        put(world["gen"], ["strain", "genus"], [["AS-979", "Streptomyces"]])
    else:
        put(world["gen"], ["strain", "genus"], [["AS-971", "Streptomyces"], ["AS-971", "Streptomyces"]])
    with pytest.raises(SystemExit, match=msg):
        run(world, world["tmp"] / "o")


def test_never_overwrites(world):
    out = world["tmp"] / "out"
    run(world, out)
    with pytest.raises(SystemExit, match="earlier outputs"):
        run(world, out)


def test_consecutive_rows_share_a_band_only_when_adjacent():
    g = [dict(strain="A", genus="X"), dict(strain="B", genus="X"), dict(strain="C", genus="Y"), dict(strain="D", genus="X")]
    assert m.groups(g) == [("X", ["A", "B"], ""), ("Y", ["C"], ""), ("X", ["D"], "")]


def test_sections_split_a_genus_and_keep_row_order(world):
    """The owner, 13 Oct: lichen and mushroom rows at the bottom, away from the moss rows. A genus that appears in two
    sections gets two bands; the section names are recorded in RUN_INFO."""
    gen = put(world["tmp"] / "genomes_sec.tsv", ["strain", "genus", "row_note", "section"],
              [["AS-971", "Streptomyces", "habitat a", "Section one"], ["AS-973", "Kribbella", "", "Section one"],
               ["AS-972", "Streptomyces", "habitat b", "Section two"]])
    rows = m.read_tsv(gen)
    assert [(g, ss, sec) for g, ss, sec in m.groups(rows)] == [
        ("Streptomyces", ["AS-971"], "Section one"), ("Kribbella", ["AS-973"], "Section one"),
        ("Streptomyces", ["AS-972"], "Section two")]
    out = world["tmp"] / "out_sec"
    w = dict(world, gen=gen)
    assert run(w, out) == 0
    info = json.loads((out / "RUN_INFO.json").read_text())
    assert info["sections"] == ["Section one", "Section two"]
    assert info["isolates"] == ["AS-971", "AS-973", "AS-972"]
    # without a section column the layout is unchanged: no sections recorded
    out2 = world["tmp"] / "out_plain"
    assert run(world, out2) == 0
    assert json.loads((out2 / "RUN_INFO.json").read_text())["sections"] == []

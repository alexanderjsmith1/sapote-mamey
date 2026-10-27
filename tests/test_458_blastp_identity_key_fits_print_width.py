"""Card blastp_identity_key_fits_print_width (v9.7.458).

The by-class BLASTp identity figure put the genus key of a one-block genome set in a single row (ncol = number of genera).
With 9 genera the saved figure was 12.8 in wide, so at the 6.5 in thesis width its 8 pt text printed at about 4 pt
(Bee Fig. S18). The key now takes as many columns as the requested print width holds, measured from the rendered figure.
The five-panel stack is also taller than a page; --split-classes N writes pages of N panels with the same tables.
A synthetic set of 9 genomes, one per genus, in one block.
"""
import csv
import importlib.util
import json
import math
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
pypdf = pytest.importorskip("pypdf")

_spec = importlib.util.spec_from_file_location("_t451_key", Path(__file__).with_name("test_451_blastp_identity_figures.py"))
_t451 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_t451)
bif = _t451.bif

GENERA = ["Streptomyces", "Actinomadura", "Amycolatopsis", "Mangrovactinospora", "Micromonospora", "Nocardia",
          "Peterkaempfera", "Saccharopolyspora", "Streptosporangium"]
RULES = ["T1PKS: PKS_KS", "NRPS: Condensation", "lanthipeptide-class-i: LanB", "terpene: Terpene_synth", "ectoine: EctC"]
PRINT_WIDTH = 6.5
PAGE_HEIGHT = 9.0          # text block of the 6.5 in thesis page


@pytest.fixture
def nine(tmp_path):
    root = tmp_path / "ws"
    rows, lines = [], ["strain\tgenus\tblock\tgene_context"]
    for n, gen in enumerate(GENERA, 1):
        s = f"G{n}"
        tags = [(f"c{n}_{j}", f"biosynthetic (rule-based-clusters) {RULES[j % len(RULES)]}") for j in range(6)]
        _t451._context(root / f"pk/{s}.jsonl", tags)
        for j, (t, _) in enumerate(tags):
            rows.append(dict(strain=s, gene=t, channel="ncbi_nr", hit_rank=1, pct_identity=40.0 + 5 * j + n,
                             source_file=f"res/{s}.csv"))
        lines.append(f"{s}\t{gen}\tBee- and wasp-associated isolates\tpk/{s}.jsonl")
    _t451._store(tmp_path / "snap.sqlite", rows)
    (tmp_path / "genomes.tsv").write_text("\n".join(lines) + "\n")
    return dict(root=root, store=tmp_path / "snap.sqlite", genomes=tmp_path / "genomes.tsv", tmp=tmp_path)


def _run(w, out, *extra, width=PRINT_WIDTH):
    return bif.main(["--genomes", str(w["genomes"]), "--store", str(w["store"]), "--root", str(w["root"]), "--out", str(out),
                     "--binding", "locus_tag", "--figure", "by-class", "--print-width", str(width), *extra])


def _text_runs(pdf):
    runs = []
    for page in pypdf.PdfReader(str(pdf)).pages:
        def visit(text, cm, tm, font_dict, font_size):
            if text and text.strip():
                a, b, c, d = (cm[0] * tm[0] + cm[2] * tm[1], cm[1] * tm[0] + cm[3] * tm[1],
                              cm[0] * tm[2] + cm[2] * tm[3], cm[1] * tm[2] + cm[3] * tm[3])
                runs.append((font_size * math.sqrt(abs(a * d - b * c)), text.strip()))
        page.extract_text(visitor_text=visit)
    return runs


def _printed(pdf, width=PRINT_WIDTH):
    """-> (width in, height in, smallest text in pt) when the figure is printed at `width` or its own width if smaller."""
    box = pypdf.PdfReader(str(pdf)).pages[0].mediabox
    w, h = float(box.width) / 72, float(box.height) / 72
    scale = min(1.0, width / w)
    runs = _text_runs(pdf)
    assert runs
    return w, h, min(size for size, _ in runs) * scale


@pytest.mark.parametrize("width", [PRINT_WIDTH, 4.5])       # the thesis width, and a narrower one: the cap is measured
def test_nine_genus_key_fits_the_print_width_at_8_pt(nine, width):
    out = nine["tmp"] / f"one_{width}"
    assert _run(nine, out, width=width) == 0
    pdf = out / "BLASTP_IDENTITY_BY_CLASS.pdf"
    w, _, smallest = _printed(pdf, width)
    assert w <= width + 0.01, f"figure is {w:.2f} in wide at a {width} in print width"
    assert smallest >= 7.95, f"smallest text prints at {smallest:.2f} pt"
    text = " ".join(t for _, t in _text_runs(pdf))
    assert all(g in text for g in GENERA)              # every genus is still in the key


def test_split_classes_writes_pages_with_the_same_tables(nine):
    one, split = nine["tmp"] / "one", nine["tmp"] / "split"
    assert _run(nine, one) == 0
    assert _run(nine, split, "--split-classes", "2") == 0
    assert not (split / "BLASTP_IDENTITY_BY_CLASS.pdf").exists()
    pages = sorted(split.glob("BLASTP_IDENTITY_BY_CLASS_p*.pdf"))
    assert [p.stem for p in pages] == [f"BLASTP_IDENTITY_BY_CLASS_p{n}" for n in (1, 2, 3)]   # 5 classes, 2 per page
    assert all(p.with_suffix(".png").exists() for p in pages)
    titles = []
    for pdf in pages:
        w, h, smallest = _printed(pdf)
        assert w <= PRINT_WIDTH + 0.01 and h <= PAGE_HEIGHT, (pdf.name, w, h)
        assert smallest >= 7.95, (pdf.name, smallest)
        text = pypdf.PdfReader(str(pdf)).pages[0].extract_text().replace(" ", "")   # kerning splits "T erpene"
        titles += [c for c in bif.CLASSES if f"{c}coregenes" in text]
    assert titles == bif.CLASSES                        # each class drawn once, in order
    for name in ("BLASTP_IDENTITY_BY_CLASS_numbers.tsv", "CORE_GENES_WITHOUT_HIT.tsv", "GENE_VALUES.tsv"):
        assert (one / name).read_bytes() == (split / name).read_bytes(), name
    info = json.loads((split / "RUN_INFO.json").read_text())
    assert info["split_classes"] == 2 and [Path(f).name for f in info["figures"]] == [p.with_suffix(".png").name for p in pages]

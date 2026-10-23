"""tools/study_workflow_figure.py (card 018c0f08_452_study_workflow_figure): study-design chevrons from an explicit
stage table; 8 pt labels on a page exactly the print width; refusals. Synthetic images only."""
import json
from pathlib import Path
import pytest
pytest.importorskip("matplotlib")
from PIL import Image
from pypdf import PdfReader
from tools import study_workflow_figure as m


def setup(tmp_path, label2="3 genomes|sequenced", photo_missing=False):
    for name, col in (("a.png", (40, 120, 60)), ("b.png", (200, 180, 90))):
        Image.new("RGB", (400, 300), col).save(tmp_path / name)
    t = tmp_path / "stages.tsv"
    t.write_text("stage\tlabel\tphoto\tframe\tcrop\n"
                 "Collect\tSamples|collected\ta.png\tcircle\t0.5,0.5,0.9\n"
                 f"Isolate\t12 isolates|bioassayed in vitro\t{'none.png' if photo_missing else 'b.png'}\tcard\t\n"
                 f"Sequence\t{label2}\t\tcircle\t\n")
    return t


@pytest.mark.needs_arial
def test_renders_at_print_width_8pt(tmp_path):
    t = setup(tmp_path); out = tmp_path / "wf"
    assert m.main(["--stages", str(t), "--root", str(tmp_path), "--out", str(out)]) == 0
    page = PdfReader(str(out) + ".pdf").pages[0]; sizes = []
    text = page.extract_text(visitor_text=lambda x, cm, tm, f, s: sizes.append(abs(s * tm[0]) if tm[0] else s) if x.strip() else None)
    assert float(page.mediabox.width) == pytest.approx(7.2 * 72) and min(sizes) >= 8 - 1e-6
    assert "12 isolates" in text and "photo" in text
    info = json.loads(Path(str(out) + "_RUN_INFO.json").read_text())
    assert info["stages"] == 3 and len(info["photos"]) == 2
    with pytest.raises(SystemExit): m.main(["--stages", str(t), "--root", str(tmp_path), "--out", str(out)])


def test_refuses_missing_photo_and_overwide_label(tmp_path):
    with pytest.raises(SystemExit):
        m.main(["--stages", str(setup(tmp_path, photo_missing=True)), "--root", str(tmp_path), "--out", str(tmp_path / "x")])
    with pytest.raises(SystemExit):
        m.main(["--stages", str(setup(tmp_path, label2="a label far too long to fit inside one stage at eight points")),
                "--root", str(tmp_path), "--out", str(tmp_path / "y")])


GBK = """LOCUS       synthetic_contig       12000 bp    DNA     linear   UNK 01-JAN-1980
DEFINITION  synthetic.
FEATURES             Location/Qualifiers
     proto_core      5001..7000
     CDS             100..900
                     /locus_tag="g1"
     CDS             5100..6100
                     /locus_tag="g2"
                     /sec_met_domain="t2ks (E-value: 1e-100, bitscore: 300)"
     CDS             complement(6200..6900)
                     /locus_tag="g3"
     CDS             11000..11800
                     /locus_tag="g4"
ORIGIN
""" + "".join(f"{i * 60 + 1:>9} " + " ".join(["acgtacgtac"] * 6) + "\n" for i in range(200)) + "//\n"


def test_locus_frame_draws_core_genes_only(tmp_path):
    (tmp_path / "r.gbk").write_text(GBK)
    Image.new("RGB", (400, 300), (40, 120, 60)).save(tmp_path / "a.png")
    t = tmp_path / "s.tsv"
    t.write_text("stage\tlabel\tphoto\tframe\tcrop\nCollect\tSamples\ta.png\tcircle\t\nGenomes\t2 genomes|sequenced\tr.gbk\tlocus\t\n")
    out = tmp_path / "wf"
    assert m.main(["--stages", str(t), "--root", str(tmp_path), "--out", str(out)]) == 0
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    info = m.draw_locus(ax, tmp_path / "r.gbk", 0, 0, 1.0)
    assert info["core_cropped"] and info["genes_drawn"] == 2      # g2, g3 inside the core +-2 kb (3000..9000); g1 and g4 lie outside
    plt.close(fig)

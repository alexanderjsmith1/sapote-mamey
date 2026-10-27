"""figure_render_qc.py reads the smallest text size at --print-width-in from the PDF or SVG companion.

The defect: a 12.81 in figure placed at 6.5 in printed its smallest text at about 4 pt, and the QC passed it,
because it checked effective DPI only. Also the pypdf operator cases of tools/_min_text_check.py: the ' and "
operators, Form XObjects, and several text-show runs that pypdf merges into one report. Synthetic files only.
"""
import csv, hashlib, importlib.util, json
from pathlib import Path
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


qc = load("render_qc_text_size_subject", "tools/figure_render_qc.py")
mtc = load("min_text_text_size_subject", "tools/_min_text_check.py")


def make_pdf(path, content, form=None, width_pt=252, height_pt=200):
    """Minimal one-page PDF: Helvetica as /F1; optional Form XObject /Fm1 with its own content."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            None,
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    xobj = ""
    if form is not None:
        objs.append(f"<< /Type /XObject /Subtype /Form /BBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> "
                    f"/Length {len(form)} >>\nstream\n{form}\nendstream")
        xobj = f" /XObject << /Fm1 {len(objs)} 0 R >>"
    objs.append(f"<< /Length {len(content)} >>\nstream\n{content}\nendstream")
    objs[2] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width_pt} {height_pt}] /Resources << /Font << /F1 4 0 R >>{xobj} >> "
               f"/Contents {len(objs)} 0 R >>")
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out)); out += f"{i} 0 obj\n{o}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    Path(path).write_bytes(out); return str(path)


def figure(folder, stem, pdf_size_pt=None, page_in=6.5, svg=None):
    """A figure folder entry: PNG with enough pixels for 6.5 in at 300 DPI, caption, and an optional PDF or SVG."""
    folder.mkdir(parents=True, exist_ok=True)
    png = folder / f"{stem}.png"
    Image.new("RGB", (1950, 1200), "#336699").save(png, dpi=(300, 300))
    (folder / f"{stem}_CAPTION.md").write_text("Synthetic control figure. Two observations.\n")
    if pdf_size_pt is not None:
        make_pdf(folder / f"{stem}.pdf", f"BT /F1 1 Tf {pdf_size_pt} 0 0 {pdf_size_pt} 20 80 Tm (Isolate label) Tj ET",
                 width_pt=round(page_in * 72, 3), height_pt=300)
    if svg is not None:
        (folder / f"{stem}.svg").write_text(svg)
    return png


def size_flags(flags):
    return [(lv, msg) for lv, msg in flags if "text size" in msg or "smallest text" in msg]


def run_cli(folder, out, *extra):
    code = qc.main([str(folder), "--out", str(out), "--ocr", "off", *extra])
    rows = list(csv.DictReader(open(out / "RENDER_QC.tsv"), delimiter="\t"))
    return code, rows


# ---- the defect: text size at the print width ----

def test_12_81_in_figure_with_4_pt_printed_text_fails_at_6_5_in(tmp_path):
    # drawn 7.883 pt on a 12.81 in page; placed at 6.5 in that is 7.883 x 6.5 / 12.81 = 4.0 pt
    figure(tmp_path / "figs", "BLASTP_wide", pdf_size_pt=7.883, page_in=12.81)
    code, rows = run_cli(tmp_path / "figs", tmp_path / "qa", "--print-width-in", "6.5")
    hits = [r for r in rows if r["level"] == "error" and "smallest text" in r["flag"]]
    assert code == 2 and len(hits) == 1
    assert hits[0]["figure"] == "BLASTP_wide.png" and "4.00 pt at declared width 6.5in" in hits[0]["flag"]
    assert "below the 8 pt minimum" in hits[0]["flag"] and "BLASTP_wide.pdf" in hits[0]["flag"]


def test_8_5_pt_text_at_6_5_in_passes_and_is_reported(tmp_path):
    figure(tmp_path / "figs", "BLASTP_ok", pdf_size_pt=8.5, page_in=6.5)
    code, rows = run_cli(tmp_path / "figs", tmp_path / "qa", "--print-width-in", "6.5")
    hits = [r for r in rows if "smallest text" in r["flag"]]
    assert code == 0 and len(hits) == 1 and hits[0]["level"] == "info"
    assert "8.50 pt at declared width 6.5in (meets the 8 pt minimum)" in hits[0]["flag"]


def test_min_text_pt_is_an_option(tmp_path):
    figure(tmp_path / "figs", "BLASTP_ok", pdf_size_pt=8.5, page_in=6.5)
    code, rows = run_cli(tmp_path / "figs", tmp_path / "qa", "--print-width-in", "6.5", "--min-text-pt", "9")
    assert code == 2 and any(r["level"] == "error" and "below the 9 pt minimum" in r["flag"] for r in rows)


@pytest.mark.parametrize("value", ["nan", "0", "-2"])
def test_invalid_min_text_pt_refuses_before_qa_write(tmp_path, value):
    png = figure(tmp_path / "figs", "F", pdf_size_pt=8.5)
    with pytest.raises(SystemExit) as e:
        qc.main([str(png), "--out", str(tmp_path / "qa"), "--min-text-pt", value, "--print-width-in", "6.5"])
    assert e.value.code == 2 and not (tmp_path / "qa").exists()


def test_raster_only_is_a_warning_not_a_pass(tmp_path):
    png = figure(tmp_path / "figs", "RASTER")
    flags = size_flags(qc.check_text_size(png, 6.5))
    assert flags == [("warn", "text size not measurable: no PDF or SVG next to the figure (raster only)")]


def test_pdf_with_text_as_outlines_is_not_measurable(tmp_path):
    png = figure(tmp_path / "figs", "OUTLINES")
    make_pdf(png.with_suffix(".pdf"), "0 0 1 rg 10 10 50 50 re f", width_pt=468)
    [(level, msg)] = size_flags(qc.check_text_size(png, 6.5))
    assert level == "warn" and msg.startswith("text size not measurable: OUTLINES.pdf: no text runs")


def test_without_print_width_text_size_is_not_checked(tmp_path):
    png = figure(tmp_path / "figs", "F", pdf_size_pt=4)
    assert qc.check_text_size(png, None) == [("info", "text size at print width NOT_CHECKED (no declared print width)")]


SVG = ("<svg xmlns='http://www.w3.org/2000/svg' width='468pt' height='216pt' viewBox='0 0 468 216'>"
       "<defs><text style='font-size: 1px'>ignored</text></defs>"
       "<g style='font-size: {size}px'><text x='10' y='20'>Isolate <tspan>label</tspan></text></g></svg>")


@pytest.mark.parametrize("size,level,printed", [(8.5, "info", "8.50 pt"), (4, "error", "4.00 pt")])
def test_svg_companion_is_measured(tmp_path, size, level, printed):
    png = figure(tmp_path / "figs", "SVGFIG", svg=SVG.format(size=size))
    [(lv, msg)] = size_flags(qc.check_text_size(png, 6.5))
    assert lv == level and f"smallest text {printed} at declared width 6.5in" in msg and "SVGFIG.svg" in msg


def test_svg_scale_transform_and_wider_page(tmp_path):
    # 13 in wide user space (936 px at 72 user units per in), text 16 units scaled by 0.5: 8 units, printed at 6.5 in = 4 pt
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 936 400'>"
           "<g transform='translate(5 5) scale(0.5)'><text font-size='16'>small</text></g></svg>")
    png = figure(tmp_path / "figs", "WIDE", svg=svg)
    [(lv, msg)] = size_flags(qc.check_text_size(png, 6.5))
    assert lv == "error" and "smallest text 4.00 pt" in msg


def test_svg_without_resolvable_size_is_not_measurable(tmp_path):
    svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 468 216'><text class='big'>label</text></svg>"
    png = figure(tmp_path / "figs", "CSS", svg=svg)
    [(lv, msg)] = size_flags(qc.check_text_size(png, 6.5))
    assert lv == "warn" and "text size not measurable" in msg and "no font size" in msg


def test_pdf_is_preferred_over_svg(tmp_path):
    png = figure(tmp_path / "figs", "BOTH", pdf_size_pt=4, svg=SVG.format(size=8.5))
    [(lv, msg)] = size_flags(qc.check_text_size(png, 6.5))
    assert lv == "error" and "BOTH.pdf" in msg


def test_completed_packet_reads_the_bound_pdf(tmp_path):
    folder = tmp_path / "packet"
    png = figure(folder, "PAGE", pdf_size_pt=7.883, page_in=12.81)
    Image.open(png).save(folder / "PAGE_plot_only.png", dpi=(300, 300))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    payload = dict(completion_state="COMPLETE", artifact_root=str(folder),
                   outputs=[dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(folder.iterdir())])
    (folder / "render_receipt.json").write_text(json.dumps(payload))
    result = qc.run([folder], tmp_path / "qa", ocr_mode="off", print_width_in=6.5)
    [(lv, msg)] = size_flags(result[0][1])
    assert lv == "error" and "smallest text 4.00 pt" in msg


# ---- tools/_min_text_check.py: pypdf operator cases ----

def baselines(pdf):
    runs = []
    page = mtc.PdfReader(pdf).pages[0]
    mtc._visit_drawn_text(page, lambda text, cm, tm, font, size: runs.append((text.strip(), cm[3] * tm[5] + cm[5]))
                          if text.strip() else None)
    return runs


def test_plain_tj_unchanged(tmp_path):
    pdf = make_pdf(tmp_path / "plain.pdf", "BT /F1 1 Tf 8 0 0 8 20 80 Tm (Bees) Tj ET")
    assert [s for s, _ in mtc.text_sizes(pdf)] == [8.0]


def test_quote_operator_uses_next_line_position(tmp_path):
    pdf = make_pdf(tmp_path / "quote.pdf", "BT /F1 1 Tf 8 0 0 8 20 80 Tm 1.25 TL (A) ' ET")
    assert [s for s, _ in mtc.text_sizes(pdf)] == [8.0]
    assert baselines(pdf) == [("A", pytest.approx(70.0))]      # 80 - 1.25 x 8 after T*


def test_form_text_counted_once_at_outer_scale(tmp_path):
    pdf = make_pdf(tmp_path / "form.pdf", "q 2 0 0 2 0 0 cm /Fm1 Do Q",
                   form="BT /F1 1 Tf 4 0 0 4 0 0 Tm (A) Tj ET")
    assert [s for s, _ in mtc.text_sizes(pdf)] == [8.0]


def test_double_quote_operator_and_td_leading(tmp_path):
    pdf = make_pdf(tmp_path / "dq.pdf", "BT /F1 1 Tf 8 0 0 8 20 80 Tm 0 -1.5 TD (B) Tj 0 0 (C) \" ET")
    assert [s for s, _ in mtc.text_sizes(pdf)] == [8.0, 8.0]
    assert baselines(pdf) == [("B", pytest.approx(68.0)), ("C", pytest.approx(56.0))]   # TD sets TL 1.5; " moves one more line


def test_merged_runs_report_the_smallest_size(tmp_path):
    # pypdf merges both runs (one baseline, one font resource) into one report carrying the last matrix (8 pt)
    pdf = make_pdf(tmp_path / "merged.pdf", "BT /F1 1 Tf 4 0 0 4 20 80 Tm (tiny) Tj 8 0 0 8 60 80 Tm (Big) Tj ET")
    sizes = mtc.text_sizes(pdf)
    assert len(sizes) == 1 and sizes[0][0] == 4.0 and "tiny" in sizes[0][1] and "Big" in sizes[0][1]


def test_merged_runs_inside_a_form_compose_the_outer_scale(tmp_path):
    pdf = make_pdf(tmp_path / "mform.pdf", "q 2 0 0 2 0 0 cm /Fm1 Do Q",
                   form="BT /F1 1 Tf 2 0 0 2 0 0 Tm (a) Tj 5 0 0 5 30 0 Tm (B) Tj ET")
    assert [s for s, _ in mtc.text_sizes(pdf)] == [4.0]


def test_separate_lines_keep_their_own_sizes(tmp_path):
    pdf = make_pdf(tmp_path / "lines.pdf", "BT /F1 1 Tf 4 0 0 4 20 80 Tm (tiny) Tj 8 0 0 8 20 40 Tm (Big) Tj ET")
    assert sorted(mtc.text_sizes(pdf)) == [(4.0, "tiny"), (8.0, "Big")]

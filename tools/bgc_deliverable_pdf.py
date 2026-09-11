#!/usr/bin/env python3
"""bgc_deliverable_pdf.py -- assemble a per-BGC deliverable PDF (cover + facts + figures + Mode B).

Bundles a strain/BGC's outputs into one reviewer-ready PDF:
  cover title + plain-language synopsis + a key-facts table, then any figures (with captions),
  then the full Mode B card rendered from its markdown.

Everything is RGB-safe and reportlab-based (no headless browser). Figures are passed as
PNG:caption pairs; captions are optional. The Mode B markdown is rendered with headings,
tables (monospace), bullets, and inline **bold**/*italic*/`code` -> reportlab markup, with
nested-emphasis guarded (a frequent crash source).

Usage:
  python bgc_deliverable_pdf.py --card AS-XXX_BGC008_ModeB.md --out AS-XXX_BGC008_Deliverable.pdf \
      --title "AS-XXX * BGC008 * NODE_162 region001" \
      --subtitle "Peptidyl-nucleoside antifungal candidate" \
      --synopsis synopsis.txt \
      --fact "Locator=NODE_162 region001 (14.25 kb)" --fact "GCF=family 88560 NOVEL, singleton" \
      --figure fig1_locus.png:"Gene organization" --figure fig4_synteny.png:"Alignment to polyoxin+nikkomycin"

Deps: reportlab, pypdf (validation), Pillow (RGB flatten). Stdlib elsewhere.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, re, sys
from xml.sax.saxutils import escape as _xml_escape  # v9.7.409 export-injection

def _clean(t):
    # v9.7.409 (DEEP_AUDIT2 export-injection): neutralise < > & BEFORE the text reaches
    # reportlab's Paragraph mini-XML markup. Card text (product names, gene functions,
    # organism) is attacker-influenced; a stray "<" crashed the PDF build (paraparser) and
    # a crafted <a href>/<font> injected live hyperlinks/formatting. The intended **bold**/
    # `code` markup is added AFTER _clean at the call sites and in _inline(), so escaping the
    # raw text here is safe. Only < > & change; every other character is untouched.
    t = _xml_escape(t)
    for a, b in [("·", "-"), ("×", "x"), ("–", "-"), ("—", "-"), ("’", "'"), ("“", '"'),
                 ("”", '"'), ("≥", ">="), ("≤", "<="), ("§", "S"), ("\xa0", " ")]:
        t = t.replace(a, b)
    return t

def _inline(t):
    t = _clean(t)
    t = re.sub(r"\*\*(.+?)\*\*", lambda m: "<b>" + m.group(1).replace("*", "") + "</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r"<font face='Courier' size=8>\1</font>", t)
    return t

def _flatten_rgb(png):
    try:
        from PIL import Image
        im = Image.open(png)
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
            out = png + ".rgb.png"; bg.save(out); return out
    except Exception:
        pass
    return png

def build(args):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
                                    Table, TableStyle, HRFlowable)
    from PIL import Image as PILImage
    ss = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=16, spaceAfter=6, textColor=colors.HexColor("#1a2a3a"))
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#2c5070"))
    BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontSize=9.5, leading=13, spaceAfter=5, alignment=4)
    SMALL = ParagraphStyle("SMALL", parent=ss["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#555"))
    CAP = ParagraphStyle("CAP", parent=ss["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#444"), spaceAfter=10, alignment=1)
    BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=12)
    story = [Paragraph(_clean(args.title or "BGC Deliverable"), H1)]
    if args.subtitle:
        story.append(Paragraph(_clean(args.subtitle), H2))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#ccc"), spaceBefore=4, spaceAfter=8))
    if args.fact:
        rows = []
        for f in args.fact:
            k, _, v = f.partition("=")
            rows.append([Paragraph("<b>" + _clean(k) + "</b>", SMALL), Paragraph(_clean(v), SMALL)])
        t = Table(rows, colWidths=[1.6 * inch, 4.9 * inch])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ddd")),
                               ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f7fa")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story += [t, Spacer(1, 10)]
    if args.synopsis and os.path.exists(args.synopsis):
        story.append(Paragraph("In plain language", H2))
        with open(args.synopsis) as _fh:
            _synopsis = _fh.read()
        for para in _synopsis.split("\n\n"):
            if para.strip():
                story.append(Paragraph(_inline(para.strip()), BODY))
        story.append(HRFlowable(width="100%", color=colors.HexColor("#eee"), spaceBefore=2, spaceAfter=8))
    for i, spec in enumerate(args.figure or [], 1):
        path, _, cap = spec.partition(":")
        if not os.path.exists(path):
            continue
        png = _flatten_rgb(path)
        w, h = PILImage.open(png).size
        iw = 6.6 * inch; ih = iw * h / w
        story.append(Paragraph(f"Figure {i}&nbsp;|&nbsp; {_clean(cap)}" if cap else f"Figure {i}", H2))
        story.append(Image(png, width=iw, height=min(ih, 3.4 * inch)))
        if cap:
            story.append(Paragraph(_clean(cap), CAP))
    story.append(PageBreak())
    if args.card and os.path.exists(args.card):
        story.append(Paragraph("Technical analysis - Mode B (S1-S30)", H1))
        story.append(HRFlowable(width="100%", color=colors.HexColor("#ccc"), spaceBefore=4, spaceAfter=6))
        with open(args.card) as _fh:
            _card_raw = _fh.read()
        card = re.sub(r"<!--.*?-->", "", _card_raw, flags=re.S)
        for line in card.splitlines():
            l = line.rstrip()
            if not l.strip():
                continue
            if l.startswith("# "):
                continue
            if l.startswith("## "):
                story.append(Paragraph("<b>" + _clean(l[3:]) + "</b>", H2)); continue
            if l.startswith("### "):
                story.append(Paragraph("<b>" + _clean(l[4:]) + "</b>", BODY)); continue
            if l.startswith("|"):
                story.append(Paragraph("<font face='Courier' size=7>" + _clean(l) + "</font>", SMALL)); continue
            if l.startswith("- "):
                story.append(Paragraph("&bull; " + _inline(l[2:]), BULLET)); continue
            if l.startswith("*") and l.endswith("*") and l.count("*") == 2:
                story.append(Paragraph("<i>" + _clean(l.strip("*")) + "</i>", SMALL)); continue
            story.append(Paragraph(_inline(l), BODY))
    doc = SimpleDocTemplate(args.out, pagesize=letter, topMargin=0.7 * inch, bottomMargin=0.6 * inch,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch, title=_clean(args.title or "Deliverable"))
    doc.build(story)
    try:
        from pypdf import PdfReader
    except ImportError:
        # v9.7.409 (CLAUDE_409_optional_deps_guard): pypdf is OPTIONAL and used only to report the
        # page count -- the PDF itself is already written by reportlab above. Degrade gracefully
        # with an actionable hint; never fail the write.
        emit(f"[bgc_deliverable_pdf] wrote {args.out} "
             "(page-count check skipped: install 'pypdf' -- pip install pypdf "
             "or pip install '.[documents]' -- to report page count)")
    else:
        try:
            n = len(PdfReader(args.out).pages)
            emit(f"[bgc_deliverable_pdf] wrote {args.out} ({n} pages)")
        except Exception:
            emit(f"[bgc_deliverable_pdf] wrote {args.out}")

def main():
    ap = argparse.ArgumentParser(description="Assemble a per-BGC deliverable PDF.")
    ap.add_argument("--card"); ap.add_argument("--out", required=True)
    ap.add_argument("--title"); ap.add_argument("--subtitle"); ap.add_argument("--synopsis")
    ap.add_argument("--fact", action="append"); ap.add_argument("--figure", action="append")
    build(ap.parse_args())

if __name__ == "__main__":
    main()

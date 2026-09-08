"""Package-scoped ReportLab renderer for Sapote-Mamey Markdown deliverables.

This is the canonical implementation used by :mod:`mamey.modeb_export`.  The
legacy ``tools/render_deliverable_pdf.py`` entry point is a thin compatibility
wrapper so a distributed bundle does not require a sibling source-tree tool to
export a Mode B card.

Supported Markdown is deliberately small and deterministic: headings,
paragraphs, bullet/numbered lists, tables, callouts, fenced code blocks, rules,
images, and conservative inline emphasis.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import html
import os
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    Image,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INDIGO = colors.HexColor("#2d398b")
TEAL = colors.HexColor("#00585c")
PERI = colors.HexColor("#e8eaf4")
TEALTINT = colors.HexColor("#e0efef")
CODEBG = colors.HexColor("#f2f3f8")
INK = colors.HexColor("#1a1a2e")
GREY = colors.HexColor("#556")


def _footer_line() -> str:
    """Return an unbranded product/version footer when a build stamp is present."""
    ver = ""
    probes = (
        Path.cwd() / "BUILD_STAMP.txt",
        Path(__file__).resolve().parents[1] / "BUILD_STAMP.txt",
    )
    for probe in probes:
        try:
            match = re.search(r"version=([0-9.]+)", probe.read_text(encoding="utf-8"))
            if match:
                ver = " · v" + match.group(1)
                break
        except OSError:
            continue
    return "Sapote-Mamey" + ver


def inline(text: str) -> str:
    """Convert the supported Markdown-inline subset to ReportLab markup."""
    spans: list[str] = []

    def stash(match):
        spans.append(html.escape(match.group(1)))
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    return re.sub(
        r"\x00(\d+)\x00",
        lambda match: f'<font face="Courier" size=9>{spans[int(match.group(1))]}</font>',
        text,
    )


def P(text: str, style, **kwargs):
    """Build a paragraph, falling back to escaped text on malformed inline markup."""
    try:
        return Paragraph(inline(text), style, **kwargs)
    except Exception:  # noqa: BLE001 - one malformed line must not abort a card export
        return Paragraph(html.escape(text), style, **kwargs)


styles = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5,
                      leading=15, textColor=INK, spaceAfter=6)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=INDIGO,
                    spaceBefore=16, spaceAfter=2, leftIndent=10)
H3 = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=TEAL,
                    spaceBefore=10, spaceAfter=2, leftIndent=10)
H4 = ParagraphStyle("h4", fontName="Helvetica-BoldOblique", fontSize=10.5, leading=13,
                    textColor=INDIGO, spaceBefore=8, spaceAfter=2, leftIndent=10)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=22, bulletIndent=10, spaceAfter=3)
CODE = ParagraphStyle("code", parent=styles["Code"], fontName="Courier", fontSize=8.5,
                     leading=11, textColor=INK)
CALLOUT = ParagraphStyle("callout", parent=BODY, textColor=INK, spaceAfter=0, leading=14)


class AccentBar(Flowable):
    """A colored left bar and header text used by the sanctioned report style."""

    def __init__(self, text, style, color=INDIGO):
        super().__init__()
        self.p = Paragraph(inline(text), style)
        self.color = color

    def wrap(self, width, height):
        self.w = width
        self.ph = self.p.wrap(width - 14, 400)[1]
        return width, self.ph + 6

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, 4, self.ph + 2, fill=1, stroke=0)
        self.p.drawOn(self.canv, 0, 2)


def callout(text_lines, tint=PERI, bar=INDIGO):
    """Build a splittable callout box without a single unsplittable tall cell."""
    import textwrap

    def paragraph(line):
        try:
            return Paragraph(inline(line), CALLOUT)
        except Exception:  # noqa: BLE001
            return Paragraph(html.escape(line), CALLOUT)

    rows = []
    for line in text_lines or [" "]:
        chunks = textwrap.wrap(line, 1100, break_long_words=False) or [line] if len(line) > 1100 else [line]
        rows.extend([[paragraph(chunk)] for chunk in chunks])
    table = Table(rows, colWidths=[6.6 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), tint),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
    ]))
    return table


def code_block(code_lines):
    pre = Preformatted("\n".join(code_lines) or " ", CODE, maxLineLength=95)
    table = Table([[pre]], colWidths=[6.7 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODEBG),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBEFORE", (0, 0), (0, -1), 3, TEAL),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#d5d8e6")),
    ]))
    return table


def md_table(rows):
    if not rows:
        return Spacer(1, 1)
    header, body = rows[0], rows[1:]
    n = len(header)
    th = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.white)
    td = ParagraphStyle("td", fontName="Helvetica", fontSize=9, leading=11, textColor=INK)
    data = [[P(cell, th) for cell in header]]
    for row in body:
        row = (row + [""] * n)[:n]
        data.append([P((cell[:300] + "…") if len(cell) > 300 else cell, td) for cell in row])
    width = 6.9 * inch
    table = Table(data, colWidths=[width / n] * n, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8cbe0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for index in range(1, len(data)):
        if index % 2 == 0:
            style.append(("BACKGROUND", (0, index), (-1, index), PERI))
    table.setStyle(TableStyle(style))
    return table


MAXW = 6.9 * inch


def _image(path, alt, base_dir):
    source = path if os.path.isabs(path) else os.path.join(base_dir, path)
    try:
        image_width, image_height = ImageReader(source).getSize()
        width = min(MAXW, image_width)
        height = width * image_height / image_width
        max_height = 8.2 * inch
        if height > max_height:
            height = max_height
            width = height * image_width / image_height
        return Image(source, width=width, height=height)
    except Exception:  # noqa: BLE001
        return Paragraph(f"<i>[image: {html.escape(alt or os.path.basename(path))}]</i>", BODY)


def parse(md, base_dir="."):
    """Parse the supported Markdown subset into ReportLab flowables."""
    lines = md.split("\n")
    flow = []
    buffer, table, callouts, bullets, code = [], [], [], [], []
    in_code = False

    def flush_paragraph():
        if buffer:
            flow.append(P(" ".join(buffer), BODY))
            buffer.clear()

    def flush_table():
        if table:
            rows = [[cell.strip() for cell in row.strip().strip("|").split("|")]
                    for row in table if not re.match(r"^\s*\|?[\s:|-]+\|?\s*$", row)]
            flow.extend([md_table(rows), Spacer(1, 8)])
            table.clear()

    def flush_callouts():
        if callouts:
            tint = TEALTINT if callouts[0].lower().startswith(("tip", "note")) else PERI
            flow.extend([callout(callouts, tint), Spacer(1, 8)])
            callouts.clear()

    def flush_bullets():
        for kind, value in bullets:
            marker = "•" if kind == "ul" else value.split(".", 1)[0] + "."
            body = value if kind == "ul" else value.split(".", 1)[1].strip()
            flow.append(P(body, BULLET, bulletText=marker))
        if bullets:
            flow.append(Spacer(1, 4))
            bullets.clear()

    def flush_code():
        if code:
            flow.extend([code_block(code), Spacer(1, 8)])
            code.clear()

    for line in lines:
        if line.lstrip().startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph(); flush_table(); flush_callouts(); flush_bullets()
                in_code = True
            continue
        if in_code:
            code.append(line)
            continue
        image_match = re.match(r"^\s*!\[([^\]]*)\]\(([^)\s]+)[^)]*\)\s*$", line)
        if image_match:
            flush_paragraph(); flush_table(); flush_callouts(); flush_bullets()
            flow.extend([_image(image_match.group(2), image_match.group(1), base_dir), Spacer(1, 6)])
            continue
        if line.startswith("|"):
            flush_paragraph(); flush_callouts(); flush_bullets(); table.append(line); continue
        flush_table()
        if line.startswith(">"):
            flush_paragraph(); flush_bullets(); callouts.append(line.lstrip(">").strip()); continue
        flush_callouts()
        if re.match(r"^\s*[-*+]\s+", line):
            flush_paragraph(); bullets.append(("ul", re.sub(r"^\s*[-*+]\s+", "", line))); continue
        if re.match(r"^\s*\d+\.\s+", line):
            flush_paragraph(); bullets.append(("ol", line.strip())); continue
        flush_bullets()
        if re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", line):
            flush_paragraph(); flow.append(Spacer(1, 6))
        elif line.startswith("#### "):
            flush_paragraph(); flow.append(AccentBar(line[5:], H4, INDIGO))
        elif line.startswith("### "):
            flush_paragraph(); flow.append(AccentBar(line[4:], H3, TEAL))
        elif line.startswith("## "):
            flush_paragraph(); flow.append(AccentBar(line[3:], H2, INDIGO))
        elif line.startswith("# "):
            continue
        elif not line.strip():
            flush_paragraph()
        else:
            buffer.append(line.strip())
    if in_code:
        flush_code()
    flush_paragraph(); flush_table(); flush_callouts(); flush_bullets()
    return flow


def _wrap(text, size, max_width=6.4):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words, output, current = text.split(), [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if stringWidth(trial, "Helvetica-Bold", size) < max_width * inch:
            current = trial
        else:
            output.append(current)
            current = word
    if current:
        output.append(current)
    return output or [text]


def cover(canvas, title, subtitle):
    width, height = letter
    canvas.setFillColor(INDIGO); canvas.rect(0, height - 3.1 * inch, width, 3.1 * inch, fill=1, stroke=0)
    canvas.setFillColor(TEAL); canvas.rect(0, height - 3.25 * inch, width, 0.15 * inch, fill=1, stroke=0)
    canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 26)
    title_box = canvas.beginText(0.9 * inch, height - 1.6 * inch)
    for line in _wrap(title, 26):
        title_box.textLine(line)
    canvas.drawText(title_box)
    canvas.setFont("Helvetica", 13); canvas.setFillColor(colors.HexColor("#c8cbe0"))
    canvas.drawString(0.9 * inch, height - 2.7 * inch, subtitle[:110])
    canvas.setFillColor(GREY); canvas.setFont("Helvetica", 9)
    canvas.drawString(0.9 * inch, 0.7 * inch, _footer_line())


def render(md_path, out_path, title=None, subtitle=""):
    """Render a Markdown file to a PDF; retained for the legacy CLI wrapper."""
    markdown_path = Path(md_path)
    md = markdown_path.read_text(encoding="utf-8")
    if title is None:
        match = re.search(r"^#\s+(.+)$", md, re.M)
        title = match.group(1).strip() if match else markdown_path.stem
    flow = [Spacer(1, 3.2 * inch)] + parse(md, str(markdown_path.resolve().parent))
    doc = SimpleDocTemplate(str(out_path), pagesize=letter, topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.9 * inch, rightMargin=0.8 * inch, title=title)
    first, footer = [True], _footer_line()

    def on_page(canvas, document):
        if first[0]:
            cover(canvas, title, subtitle)
            first[0] = False
        else:
            canvas.setFillColor(GREY); canvas.setFont("Helvetica", 8)
            canvas.drawRightString(letter[0] - 0.8 * inch, 0.5 * inch, str(document.page))
            canvas.drawString(0.9 * inch, 0.5 * inch, footer)
            canvas.setStrokeColor(INDIGO); canvas.setLineWidth(0.5)
            canvas.line(0.9 * inch, 0.68 * inch, letter[0] - 0.8 * inch, 0.68 * inch)

    doc.build(flow, onFirstPage=on_page, onLaterPages=on_page)


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        raise SystemExit("usage: python -m mamey.markdown_pdf INPUT.md OUTPUT.pdf [title] [subtitle]")
    render(args[0], args[1], args[2] if len(args) > 2 else None, args[3] if len(args) > 3 else "")
    emit(f"wrote {args[1]}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - legacy-compatible renderer exit behavior
        sys.stderr.write(f"render_deliverable_pdf failed: {exc}\n")
        raise SystemExit(3)

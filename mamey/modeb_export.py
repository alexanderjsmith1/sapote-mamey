#!/usr/bin/env python3
"""modeb_export.py — export an authored Mode B card (§1-§48 markdown) to Word (.docx)
and PDF, for hand-off outside the terminal (FA6, prototype / FEATURE).

Input  : a single Mode B card `.md` (e.g. `<pkg>/mode_b/<STRAIN>_Mode_B_Top_Leads.md`
         or an authored `<BGC>_ModeB.md`), OR a package's `mode_b/` directory
         (every `*.md` in it is exported → batch).
Output : `<card>.docx` and `<card>.pdf` next to the source (or under --outdir).
         - DOCX: headings, the §-structure, bullets, blockquotes and every markdown
           table (the §4 evidence grid included) rendered as a REAL Word table.
         - PDF : reportlab — readable typography, a page number on every page, and
           the mandatory claim-safety footer on every page. It reuses the packaged
           ``mamey.markdown_pdf`` renderer (its ``parse``, styles, cover, and footer)
           rather than hand-rolling a second renderer.

Claim-safety: the card's own claim-safety language is preserved VERBATIM (it is
ordinary markdown text/blockquote and is never rewritten). On top of it, every page
carries the footer::

    Class-level capacity hypothesis · judgment deferred · similarity not identity

Deterministic; no network; never mutates the source markdown.

python-docx is optional. If it is not importable the DOCX path degrades gracefully
with a clear message (the PDF path is unaffected). Offline install lives in the
bundle wheelhouse; see docs/MODEB_EXPORT_HOOK.md.

Standalone:  python -m mamey.modeb_export CARD.md [--outdir DIR] [--format both|docx|pdf]
             [--theme evidence_dossier|field_notebook|dark_lab|minimal_clinical]
The `modeb-export` subcommand is wired in `mamey.cli`.
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
import importlib.util
import os
import re
import sys
from pathlib import Path

try:
    from .report_theme import theme_variant
except ImportError:  # standalone legacy use; the default remains unchanged
    theme_variant = None

THEME_CHOICES = ("evidence_dossier", "field_notebook", "dark_lab", "minimal_clinical")


def _resolve_theme(name: str) -> str:
    """Normalize and validate a theme before any renderer writes output."""
    key = str(name or "").strip().lower().replace("-", "_")
    if theme_variant is not None:
        return str(theme_variant(key)["name"])
    if key not in THEME_CHOICES:
        raise ValueError(f"unknown Sapote-Mamey report theme variant: {name}")
    return key

# The footer stamped on EVERY page of both outputs (verbatim, do not edit the wording).
CLAIM_SAFETY_FOOTER = (
    "Class-level capacity hypothesis · judgment deferred · similarity not identity"
)

def core_render_dependency_status() -> dict:
    """NC-009: report `reportlab` as a CORE dependency (Mode-B PDF/DOCX export), DISTINCT from the
    optional figure extras (numpy/matplotlib).

    PDF/DOCX export silently skips when reportlab is absent, so a 'PDF-ready' state must not be claimed
    until this reports OK. The graceful skip stays for ordinary post-seal use; a release-QA/cut check
    should treat CORE_DEPENDENCY_MISSING as a hard fail, not an optional-extra warning.
    """
    present = importlib.util.find_spec("reportlab") is not None
    return {
        "dependency": "reportlab",
        "purpose": "Mode-B PDF/DOCX export (mamey modeb-export)",
        "tier": "CORE",
        "present": present,
        "state": "OK" if present else "CORE_DEPENDENCY_MISSING",
        "detail": ("reportlab available; PDF/DOCX export ready" if present
                   else "reportlab absent — Mode-B PDF/DOCX export unavailable; 'PDF-ready' state cannot "
                        "be claimed until installed (pip install reportlab)"),
    }


# --------------------------------------------------------------------------- #
#  Shared: split a markdown card into a light block model (used by both paths).
# --------------------------------------------------------------------------- #
def _iter_blocks(md: str):
    """Yield (kind, payload) blocks from Mode B markdown. Deterministic, line-driven.

    kinds: 'h1'/'h2'/'h3'/'h4' (payload=text), 'table' (payload=list[list[str]]),
           'quote'/'code' (payload=list[str]), 'bullet' (payload=(marker, text)),
           'rule' (payload=None), 'p' (payload=text).
    """
    lines = md.split("\n")
    i = 0
    n = len(lines)
    in_code = False
    code_buf: list[str] = []
    tbl_buf: list[str] = []
    quote_buf: list[str] = []
    para_buf: list[str] = []

    # We collect into a list (line-driven state machine; simpler than a nested generator).
    out: list[tuple] = []

    def flush_para():
        if para_buf:
            out.append(("p", " ".join(s.strip() for s in para_buf).strip()))
            para_buf.clear()

    def flush_table():
        if tbl_buf:
            rows = [
                [c.strip() for c in r.strip().strip("|").split("|")]
                for r in tbl_buf
                if not re.match(r"^\s*\|?[\s:|-]+\|?\s*$", r)  # drop the --- separator row
            ]
            if rows:
                out.append(("table", rows))
            tbl_buf.clear()

    def flush_quote():
        if quote_buf:
            out.append(("quote", quote_buf.copy()))
            quote_buf.clear()

    while i < n:
        ln = lines[i]
        stripped = ln.lstrip()

        if stripped.startswith("```"):
            if in_code:
                out.append(("code", code_buf.copy()))
                code_buf.clear()
                in_code = False
            else:
                flush_para()
                flush_table()
                flush_quote()
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(ln)
            i += 1
            continue

        if ln.startswith("|"):
            flush_para()
            flush_quote()
            tbl_buf.append(ln)
            i += 1
            continue
        else:
            flush_table()

        if ln.startswith(">"):
            flush_para()
            quote_buf.append(ln.lstrip(">").strip())
            i += 1
            continue
        else:
            flush_quote()

        if re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", ln):
            flush_para()
            out.append(("rule", None))
        elif ln.startswith("#### "):
            flush_para()
            out.append(("h4", ln[5:].strip()))
        elif ln.startswith("### "):
            flush_para()
            out.append(("h3", ln[4:].strip()))
        elif ln.startswith("## "):
            flush_para()
            out.append(("h2", ln[3:].strip()))
        elif ln.startswith("# "):
            flush_para()
            out.append(("h1", ln[2:].strip()))
        elif re.match(r"^\s*[-*+]\s+", ln):
            flush_para()
            out.append(("bullet", ("•", re.sub(r"^\s*[-*+]\s+", "", ln).strip())))
        elif re.match(r"^\s*\d+\.\s+", ln):
            flush_para()
            m = re.match(r"^\s*(\d+)\.\s+(.*)$", ln)
            out.append(("bullet", (m.group(1) + ".", m.group(2).strip())))
        elif ln.strip() == "":
            flush_para()
        else:
            para_buf.append(ln)
        i += 1

    if in_code and code_buf:
        out.append(("code", code_buf.copy()))
    flush_para()
    flush_table()
    flush_quote()
    return out


def _card_title(md: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", md, re.M)
    return m.group(1).strip() if m else fallback


# --------------------------------------------------------------------------- #
#  DOCX path (python-docx, optional).
# --------------------------------------------------------------------------- #
def docx_available() -> bool:
    return importlib.util.find_spec("docx") is not None


def _add_inline_runs(paragraph, text: str) -> None:
    """Add **bold** / *italic* / `code` inline runs to a python-docx paragraph."""
    # Tokenise on the three inline markers, keeping the delimiters.
    token_re = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|(?<![\w*])\*(?!\s)[^*\n]+?(?<!\s)\*(?![\w*]))")
    pos = 0
    for m in token_re.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos:m.start()])
        tok = m.group(0)
        if tok.startswith("**"):
            paragraph.add_run(tok[2:-2]).bold = True
        elif tok.startswith("`"):
            r = paragraph.add_run(tok[1:-1])
            r.font.name = "Courier New"
        else:  # *italic*
            paragraph.add_run(tok[1:-1]).italic = True
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def export_card_docx(md_path: Path, out_docx: Path, theme: str = "evidence_dossier") -> dict:
    """Render a Mode B card markdown to .docx. Returns a status dict; never raises
    for the 'python-docx absent' case (returns status SKIPPED_NO_DOCX)."""
    md_path = Path(md_path)
    out_docx = Path(out_docx)
    theme = _resolve_theme(theme)
    if not docx_available():
        return {
            "status": "SKIPPED_NO_DOCX",
            "path": None,
            "theme": theme,
            "detail": (
                "python-docx is not installed — .docx not written (PDF is unaffected). "
                "Install offline from the bundle wheelhouse: "
                "pip install --no-index --find-links Tools/wheelhouse python-docx"
            ),
        }
    import docx  # type: ignore
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    md = md_path.read_text(encoding="utf-8")
    title = _card_title(md, md_path.stem)
    theme_data = theme_variant(theme) if theme_variant else {"tokens": {"colors": {"navy": "2D398B", "muted": "556666"}}}
    palette = theme_data["tokens"]["colors"]
    doc = Document()

    # Footer on every page (docx footers repeat on all pages of the section).
    for section in doc.sections:
        fp = section.footer.paragraphs[0]
        fp.text = ""
        fr = fp.add_run(CLAIM_SAFETY_FOOTER)
        fr.font.size = Pt(7.5)
        fr.font.color.rgb = RGBColor.from_string(palette.get("muted", "556666"))
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    INDIGO = RGBColor.from_string(palette["navy"])
    doc.add_heading(title, level=0)

    for kind, payload in _iter_blocks(md):
        if kind == "h1":
            # '# ' after the title line — treat as a top section heading.
            doc.add_heading(payload, level=1)
        elif kind == "h2":
            doc.add_heading(payload, level=1)
        elif kind == "h3":
            doc.add_heading(payload, level=2)
        elif kind == "h4":
            doc.add_heading(payload, level=3)
        elif kind == "rule":
            doc.add_paragraph().add_run("─" * 24).font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
        elif kind == "quote":
            for line in payload:
                p = doc.add_paragraph(style="Intense Quote" if "Intense Quote" in [s.name for s in doc.styles] else None)
                _add_inline_runs(p, line)
        elif kind == "code":
            p = doc.add_paragraph()
            r = p.add_run("\n".join(payload))
            r.font.name = "Courier New"
            r.font.size = Pt(8)
        elif kind == "bullet":
            marker, text = payload
            style = "List Bullet" if marker == "•" else "List Number"
            try:
                p = doc.add_paragraph(style=style)
            except KeyError:
                p = doc.add_paragraph()
                p.add_run(marker + " ")
            _add_inline_runs(p, text)
        elif kind == "table":
            rows = payload
            ncol = max(len(r) for r in rows)
            table = doc.add_table(rows=0, cols=ncol)
            try:
                table.style = "Light Grid Accent 1"
            except KeyError:
                pass
            for ridx, row in enumerate(rows):
                cells = table.add_row().cells
                padded = (row + [""] * ncol)[:ncol]
                for cidx, val in enumerate(padded):
                    cell = cells[cidx]
                    cell.paragraphs[0].text = ""
                    _add_inline_runs(cell.paragraphs[0], val)
                    if ridx == 0:  # header row bold
                        for run in cell.paragraphs[0].runs:
                            run.bold = True
                            run.font.color.rgb = INDIGO
            doc.add_paragraph()
        elif kind == "p":
            if payload:
                p = doc.add_paragraph()
                _add_inline_runs(p, payload)

    out_docx.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write (.tmp sibling + Path.replace): python-docx's save() opens the target with
    # zipfile.ZipFile(path, "w"), which truncates it immediately — a process killed mid-save
    # (SIGKILL/OOM/power loss) would otherwise destroy a previously-exported, still-valid .docx
    # at this same path (e.g. a re-run after editing the source card).
    _tmp_docx = out_docx.with_name(out_docx.name + ".tmp")
    doc.save(str(_tmp_docx))
    _tmp_docx.replace(out_docx)
    return {
        "status": "WRITTEN",
        "path": str(out_docx),
        "bytes": out_docx.stat().st_size,
        "theme": theme,
        "engine": f"python-docx {getattr(docx, '__version__', '?')}",
    }


# --------------------------------------------------------------------------- #
#  PDF path (reportlab, reusing packaged mamey.markdown_pdf).
# --------------------------------------------------------------------------- #
def _load_pdf_renderer():
    """Load the package-scoped PDF renderer, never a source-tree tools path."""
    if importlib.util.find_spec("reportlab") is None:
        return None
    try:
        from . import markdown_pdf
        return markdown_pdf
    except Exception:  # noqa: BLE001
        return None


def export_card_pdf(md_path: Path, out_pdf: Path, theme: str = "evidence_dossier") -> dict:
    """Render a Mode B card markdown to a styled PDF with a page number AND the
    claim-safety footer on every page. Reuses the sanctioned reportlab renderer's
    parse()/styles/cover; adds only the mandatory footer line. Returns a status dict."""
    md_path = Path(md_path)
    out_pdf = Path(out_pdf)
    theme = _resolve_theme(theme)
    r = _load_pdf_renderer()
    if r is None:
        return {
            "status": "SKIPPED_NO_REPORTLAB",
            "path": None,
            "theme": theme,
            "detail": "reportlab not importable or packaged mamey.markdown_pdf unavailable",
        }
    theme_data = theme_variant(theme) if theme_variant else {"tokens": {"colors": {"navy": "2D398B", "teal": "00585C", "cream": "E8EAF4", "pale_teal": "E0EFEF", "ink": "1A1A2E", "muted": "555555"}}}
    palette = theme_data["tokens"]["colors"]
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Spacer

    md = md_path.read_text(encoding="utf-8")
    title = _card_title(md, md_path.stem)
    subtitle = "Mode B card · Sapote-Mamey"

    # Recolor the sanctioned renderer's shared styles; do not create a second renderer.
    for style_name, key in (("BODY", "ink"), ("H2", "navy"), ("H3", "teal"), ("H4", "navy"), ("BULLET", "ink"), ("CODE", "ink"), ("CALLOUT", "ink")):
        style = getattr(r, style_name, None)
        if style is not None and key in palette:
            style.textColor = colors.HexColor("#" + palette[key])
    for attr, key in (("INDIGO", "navy"), ("TEAL", "teal"), ("PERI", "cream"), ("TEALTINT", "pale_teal"), ("INK", "ink"), ("GREY", "muted")):
        if key in palette:
            setattr(r, attr, colors.HexColor("#" + palette[key]))
    flow = [Spacer(1, 3.2 * inch)] + r.parse(md, str(md_path.resolve().parent))
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write (.tmp sibling + Path.replace): SimpleDocTemplate opens its target file for
    # writing immediately, truncating it — a process killed mid-build (SIGKILL/OOM/power loss)
    # would otherwise destroy a previously-exported, still-valid .pdf at this same path.
    _tmp_pdf = out_pdf.with_name(out_pdf.name + ".tmp")
    doc = SimpleDocTemplate(
        str(_tmp_pdf), pagesize=letter, topMargin=0.7 * inch, bottomMargin=0.85 * inch,
        leftMargin=0.9 * inch, rightMargin=0.8 * inch, title=title,
    )
    first = [True]
    proj_foot = r._footer_line()

    def on_page(canv, d):
        if first[0]:
            r.cover(canv, title, subtitle)
            first[0] = False
        # Claim-safety footer + page number + project line on EVERY page (cover included).
        canv.setFillColor(r.GREY)
        canv.setFont("Helvetica-Oblique", 7.5)
        canv.drawCentredString(letter[0] / 2.0, 0.38 * inch, CLAIM_SAFETY_FOOTER)
        if not (d.page == 1):
            canv.setFont("Helvetica", 8)
            canv.drawRightString(letter[0] - 0.8 * inch, 0.6 * inch, str(d.page))
            canv.drawString(0.9 * inch, 0.6 * inch, proj_foot)
            canv.setStrokeColor(r.INDIGO)
            canv.setLineWidth(0.5)
            canv.line(0.9 * inch, 0.78 * inch, letter[0] - 0.8 * inch, 0.78 * inch)

    doc.build(flow, onFirstPage=on_page, onLaterPages=on_page)
    _tmp_pdf.replace(out_pdf)
    return {
        "status": "WRITTEN",
        "path": str(out_pdf),
        "bytes": out_pdf.stat().st_size,
        "theme": theme,
        "engine": "reportlab (via mamey.markdown_pdf)",
    }


# --------------------------------------------------------------------------- #
#  Orchestration: single card + batch directory.
# --------------------------------------------------------------------------- #
def claim_safety_findings_for_export(md_text: str) -> list[dict]:
    """v9.7.409 B2: the card-body claim-safety findings that block a DOCX/PDF export."""
    try:
        from .modeb_structure_gate import lint_card
    except ImportError:  # loaded by path without a parent package (tests do this)
        from mamey.modeb_structure_gate import lint_card
    return [f for f in lint_card(md_text, check_claim_safety=True) if f.get("code") == "CLAIM_SAFETY"]


def export_card(md_path, outdir=None, formats=("docx", "pdf"), theme: str = "evidence_dossier", force: bool = False) -> dict:
    """Export one Mode B card to the requested formats. Returns
    {'md': ..., 'docx': <status>, 'pdf': <status>} (only requested keys present).

    v9.7.409 B2 (owner ruling 2026-09-04): fail-closed claim-safety content lint BEFORE render,
    mirroring compile_report's write-narrative door. A card body carrying product-identity
    overclaims is REFUSED (status REFUSED_CLAIM_SAFETY) unless force=True after human review.
    Before this the body shipped verbatim under a blanket footer with no content lint at all."""
    md_path = Path(md_path)
    theme = _resolve_theme(theme)
    if not force:
        _cs = claim_safety_findings_for_export(md_path.read_text(encoding="utf-8", errors="replace"))
        if _cs:
            _refused = {"status": "REFUSED_CLAIM_SAFETY", "path": None,
                        "detail": (f"{len(_cs)} claim-safety overclaim(s) in the card body -- "
                                   + "; ".join(str(f.get("message", f))[:120] for f in _cs[:3])
                                   + "; fix the phrasing or re-run with --force after review")}
            res = {"md": str(md_path), "theme": theme, "status": "REFUSED_CLAIM_SAFETY", "findings": _cs}
            for fmt in formats:
                res[fmt] = dict(_refused)  # _print_result's existing non-WRITTEN branch reports it and returns 1
            return res
    base_dir = Path(outdir) if outdir else md_path.parent
    stem = md_path.stem
    result: dict = {"md": str(md_path), "theme": theme}
    if "docx" in formats:
        result["docx"] = export_card_docx(md_path, base_dir / f"{stem}.docx", theme=theme)
    if "pdf" in formats:
        result["pdf"] = export_card_pdf(md_path, base_dir / f"{stem}.pdf", theme=theme)
    return result


def export_dir(mode_b_dir, outdir=None, formats=("docx", "pdf"), theme: str = "evidence_dossier", force: bool = False) -> list[dict]:
    """Batch-export every `*.md` under a package's mode_b/ directory (sorted, deterministic)."""
    mode_b_dir = Path(mode_b_dir)
    cards = sorted(p for p in mode_b_dir.glob("*.md") if p.name != "PROVENANCE.md")
    return [export_card(c, outdir=outdir, formats=formats, theme=theme, force=force) for c in cards]


def _print_result(res: dict, require_both: bool = False) -> int:
    rc = 0
    emit(f"card: {res['md']}")
    for fmt in ("docx", "pdf"):
        st = res.get(fmt)
        if not st:
            continue
        if st["status"] == "WRITTEN":
            emit(f"  {fmt}: {st['path']}  ({st.get('bytes', 0)} bytes; {st.get('engine', '')})")
        elif st["status"].startswith("SKIPPED"):
            emit(f"  {fmt}: SKIPPED — {st.get('detail', '')}", file=sys.stderr)
            # A skipped DOCX (no python-docx) is graceful, not a failure; a skipped PDF is.
            if fmt == "pdf":
                rc = 1
        else:
            emit(f"  {fmt}: {st['status']} — {st.get('detail', '')}", file=sys.stderr)
            rc = 1
    if require_both and any(res.get(fmt, {}).get("status") != "WRITTEN" for fmt in ("docx", "pdf")):
        emit("ERROR: --format both requires both DOCX and PDF outputs to be written; use --format pdf or --format docx for a single-output export.", file=sys.stderr)
        rc = 1
    return rc


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="mamey modeb-export",
        description="Export authored Mode B card markdown → Word (.docx) and PDF.",
    )
    ap.add_argument("input", help="A Mode B card .md OR a package mode_b/ directory (batch)")
    ap.add_argument("--outdir", default=None, help="Output dir (default: alongside the source .md)")
    ap.add_argument("--format", choices=["docx", "pdf", "both"], default="both")
    ap.add_argument("--theme", choices=THEME_CHOICES, default="evidence_dossier")
    ap.add_argument("--force", action="store_true", default=False,
                    help="v9.7.409: export despite claim-safety findings in the card body (after human review)")
    args = ap.parse_args(argv)

    formats = ("docx", "pdf") if args.format == "both" else (args.format,)
    inp = Path(args.input)
    if inp.is_dir():
        results = export_dir(inp, outdir=args.outdir, formats=formats, theme=args.theme, force=args.force)
        if not results:
            emit(f"no Mode B card *.md found under {inp}", file=sys.stderr)
            return 1
        return max(_print_result(r, require_both=args.format == "both") for r in results)
    if not inp.exists():
        emit(f"ERROR: no such file: {inp}", file=sys.stderr)
        return 2
    return _print_result(export_card(inp, outdir=args.outdir, formats=formats, theme=args.theme, force=args.force), require_both=args.format == "both")


if __name__ == "__main__":
    raise SystemExit(main())

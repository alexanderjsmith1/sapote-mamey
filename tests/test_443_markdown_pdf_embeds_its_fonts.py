"""v9.7.443: the shared ReportLab renderer embeds its fonts or refuses.

Base-14 Helvetica/Courier are never embedded, and compile_report's font QA correctly refuses such a
PDF. mamey.markdown_pdf now registers one TrueType family; when none is found, render() refuses so
tools/md_to_pdf.sh falls back to pandoc+xelatex. It must never write an unembedded PDF.
"""
import pytest

pytest.importorskip("reportlab")
pypdf = pytest.importorskip("pypdf")

from mamey import markdown_pdf as M  # noqa: E402

# The 14 standard PDF fonts: never embedded, so never acceptable in a rendered deliverable.
BASE14 = {
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
    "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
    "Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique", "Symbol", "ZapfDingbats",
}

MD = "# Title\n\nBody with **bold**, *italic* and `code`.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```\nblock\n```\n"


def _fonts(pdf_path):
    reader = pypdf.PdfReader(str(pdf_path))
    found = {}
    for page in reader.pages:
        res = page.get("/Resources") or {}
        for font in (res.get("/Font") or {}).values():
            font = font.get_object()
            desc = font.get("/FontDescriptor")
            if desc is None and font.get("/DescendantFonts"):
                desc = font["/DescendantFonts"][0].get_object().get("/FontDescriptor")
            desc = desc.get_object() if desc is not None else {}
            embedded = any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3"))
            found[str(font.get("/BaseFont"))] = embedded
    return found


def test_render_embeds_every_font(tmp_path):
    if not M.FONTS_EMBEDDED:
        pytest.skip(M.FONT_UNAVAILABLE_REASON)
    src = tmp_path / "doc.md"; src.write_text(MD, encoding="utf-8")
    out = tmp_path / "doc.pdf"
    M.render(src, out)
    fonts = _fonts(out)
    assert fonts, "no fonts found in the rendered PDF"
    assert all(fonts.values()), fonts
    # Base-14 fonts by exact name, subset tag ("ABCDEF+") removed. A substring test would also refuse
    # embedded TrueType faces whose names contain "Courier", such as macOS Courier New (CourierNewPSMT).
    base14 = [n for n in fonts if n.lstrip("/").split("+")[-1] in BASE14]
    assert not base14, fonts


def test_render_refuses_without_an_embeddable_font(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "FONTS_EMBEDDED", False)
    monkeypatch.setattr(M, "FONT_UNAVAILABLE_REASON", "no embeddable TrueType sans family found")
    src = tmp_path / "doc.md"; src.write_text(MD, encoding="utf-8")
    out = tmp_path / "doc.pdf"
    with pytest.raises(M.EmbeddedFontUnavailable):
        M.render(src, out)
    assert not out.exists()

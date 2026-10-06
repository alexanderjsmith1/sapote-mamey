"""Report complete local PDF routes without installing or contacting services."""
import importlib.util
import shutil


def status():
    primary = importlib.util.find_spec('reportlab') is not None
    embedded = False
    primary_error = None
    if primary:
        try:
            from .markdown_pdf import FONTS_EMBEDDED
            embedded = FONTS_EMBEDDED
        except ImportError as exc:
            primary_error = f"PDF primary import unavailable: {type(exc).__name__}: {exc}"
    fallback = {name:shutil.which(name) is not None for name in ('pandoc','xelatex')}
    svg = importlib.util.find_spec('cairosvg') is not None or any(shutil.which(n) for n in ('rsvg-convert','inkscape'))
    publication_qa = {name:shutil.which(name) is not None for name in ('pdffonts','pdftotext','pdfimages')}
    return {'primary_reportlab_embedded_fonts':primary and embedded, 'primary_error':primary_error,
            'fallback':fallback, 'fallback_ready':all(fallback.values()),
            'svg_conversion_ready':bool(svg), 'publication_qa':publication_qa,
            'publication_qa_ready':all(publication_qa.values())}

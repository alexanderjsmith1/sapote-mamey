"""Synthetic regression checks for SVG external use and CSS import guards."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import builtins
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location('guarded_prepare_new', ROOT / 'tools/prepare_pdf_resources.py')
prepare = module_from_spec(spec)
spec.loader.exec_module(prepare)


def svg(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink">' + body + '</svg>').encode()


@pytest.mark.parametrize('body', [
    '<use href="other.svg#shape"/>',
    '<use xlink:href="https://example.invalid/x.svg#shape"/>',
    '<use href="data:image/svg+xml;base64,PHN2Zy8+"/>',
    '<use href="#"/>',
    '<use/>',
    '<use href="#a" xlink:href="#b"/>',
])
def test_external_or_ambiguous_use_rejected(body):
    with pytest.raises(ValueError, match='PDF_SVG_EXTERNAL_USE_REFUSED'):
        prepare.reject_svg_external_image_refs(svg(body))


@pytest.mark.parametrize('body', [
    '<use href="#shape"/>',
    '<use xlink:href="#shape"/>',
    '<style>rect {fill: red}</style><rect/>',
    '<style>/* @import is text in a comment */ rect {fill: red}</style><rect/>',
    '<style>text::before {content: "@import"}</style><text/>',
])
def test_internal_use_and_ordinary_style_allowed(body):
    prepare.reject_svg_external_image_refs(svg(body))


@pytest.mark.parametrize('css', [
    '@import url("colors.css"); rect {fill: red}',
    '@IMPORT "colors.css";',
    r'@im\70ort "colors.css";',
    '@media screen {@import "colors.css";}',
])
def test_css_import_including_escapes_rejected(css):
    with pytest.raises(ValueError, match='PDF_SVG_CSS_IMPORT_REFUSED'):
        prepare.reject_svg_external_image_refs(svg('<style>' + css + '</style>'))


def test_missing_css_parser_fails_closed(monkeypatch):
    original = builtins.__import__
    def no_tinycss(name, *args, **kwargs):
        if name == 'tinycss2':
            raise ImportError('synthetic missing parser')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', no_tinycss)
    with pytest.raises(ValueError, match='PDF_SVG_CSS_PARSER_UNAVAILABLE'):
        prepare.reject_svg_external_image_refs(svg('<style>rect {fill: red}</style>'))

@pytest.mark.parametrize('body, error', [
    ('<use href="external.svg#shape"/>', 'PDF_SVG_EXTERNAL_USE_REFUSED'),
    ('<style>@import "styles.css";</style><rect/>', 'PDF_SVG_CSS_IMPORT_REFUSED'),
])
def test_prepare_fails_before_converter_and_output(tmp_path, monkeypatch, body, error):
    import os
    import sys
    import types
    pandoc = os.environ.get('PANDOC')
    if not pandoc:
        pytest.skip('PANDOC environment path is required')
    (tmp_path / 'panel.svg').write_bytes(svg(body))
    (tmp_path / 'input.md').write_text('![caption](panel.svg)\n')
    out = tmp_path / 'out'
    out.mkdir()
    calls = []
    monkeypatch.setitem(sys.modules, 'cairosvg', types.SimpleNamespace(svg2pdf=lambda **k: calls.append(k)))
    with pytest.raises(ValueError, match=error):
        prepare.prepare(tmp_path / 'input.md', out / 'safe.md', pandoc=pandoc)
    assert not calls and not list(out.iterdir())

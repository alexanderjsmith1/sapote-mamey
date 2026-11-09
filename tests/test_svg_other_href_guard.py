"""Synthetic regression tests for external non-image SVG href resources."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location('guarded_prepare_other_href', ROOT / 'tools/prepare_pdf_resources.py')
prepare = module_from_spec(spec)
spec.loader.exec_module(prepare)


def svg(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink">' + body + '</svg>').encode()


@pytest.mark.parametrize('body', [
    '<linearGradient id="g" href="defs.svg#g"/>',
    '<radialGradient id="g" xlink:href="https://example.invalid/defs.svg#g"/>',
    '<pattern id="p" href="data:image/svg+xml;base64,PHN2Zy8+"/>',
    '<textPath href="//example.invalid/path.svg#p"/>',
    '<filter id="f" href="#"/>',
    '<linearGradient href="#a" xlink:href="#b"/>',
])
def test_external_or_ambiguous_reference_is_refused(body):
    with pytest.raises(ValueError, match='PDF_SVG_EXTERNAL_HREF_REFUSED'):
        prepare.reject_svg_external_image_refs(svg(body))


@pytest.mark.parametrize('body', [
    '<linearGradient id="g" href="#base"/>',
    '<radialGradient id="g" xlink:href="#base"/>',
    '<pattern id="p" href="#base"/>',
    '<textPath href="#path"/>',
    '<a href="https://example.invalid/page"><text>link</text></a>',
    '<a xlink:href="https://example.invalid/page"><text>link</text></a>',
    '<rect fill="url(#g)"/>',
])
def test_local_resource_and_hyperlink_allowed(body):
    prepare.reject_svg_external_image_refs(svg(body))


def test_prepare_refuses_before_conversion_and_publication(tmp_path, monkeypatch):
    import os
    import sys
    import types
    pandoc = os.environ.get('PANDOC')
    if not pandoc:
        pytest.skip('PANDOC path required')
    (tmp_path / 'panel.svg').write_bytes(svg('<linearGradient id="g" href="defs.svg#g"/>'))
    (tmp_path / 'input.md').write_text('![caption](panel.svg)\n')
    out = tmp_path / 'out'
    out.mkdir()
    calls = []
    monkeypatch.setitem(sys.modules, 'cairosvg', types.SimpleNamespace(svg2pdf=lambda **k: calls.append(k)))
    with pytest.raises(ValueError, match='PDF_SVG_EXTERNAL_HREF_REFUSED'):
        prepare.prepare(tmp_path / 'input.md', out / 'safe.md', pandoc=pandoc)
    assert not calls and not list(out.iterdir())

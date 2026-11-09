"""Synthetic CSS URL guard checks; these do not prove a complete SVG policy."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

spec = spec_from_file_location('css_guard', Path(__file__).resolve().parents[1] / 'tools/prepare_pdf_resources.py')
module = module_from_spec(spec)
spec.loader.exec_module(module)

def svg(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg">' + body + '</svg>').encode()

@pytest.mark.parametrize('body', [
    '<rect fill="url(external.svg#gradient)"/>',
    '<rect style="fill:url(\'external.svg#gradient\')"/>',
    '<style>rect {fill:url(external.svg#gradient)}</style><rect/>',
    '<style>rect {fill:url("https://example.invalid/g.svg#g")}</style><rect/>',
    r'<rect style="fill:u\72l(external.svg#g)"/>',
    '<rect filter="url(file:///tmp/example.svg#f)"/>',
    '<rect mask="url(data:image/png;base64,AAAA)"/>',
    '<style>rect {fill:url(#)}</style><rect/>',
    '<rect style="fill:url(garbage value)"/>',
])
def test_unsafe_or_invalid_css_url_refused(body):
    with pytest.raises(ValueError, match='PDF_SVG_CSS_(URL_REFUSED|INVALID)'):
        module.reject_svg_external_image_refs(svg(body))

@pytest.mark.parametrize('body', [
    '<rect fill="url(#gradient)"/>',
    '<rect style="fill:url(\'#gradient\');stroke:blue"/>',
    '<style>rect {fill:url("#gradient")}</style><rect/>',
    r'<rect style="fill:u\72l(#gradient)"/>',
    '<rect style="fill:red;stroke:#abcdef"/>',
    '<style>/* url(external) is a comment */ rect {fill:red}</style>',
    '<style>text {content:"url(external)"}</style><text/>',
])
def test_local_fragment_and_inert_text_allowed(body):
    module.reject_svg_external_image_refs(svg(body))

@pytest.mark.parametrize('body', [
    '<rect fill="url(external.svg#g)"/>',
    '<style>rect {fill:url("external.svg#g")}</style><rect/>',
])
def test_prepare_refuses_before_converter_and_outputs(tmp_path, monkeypatch, body):
    import os, sys, types
    pandoc = os.environ.get('PANDOC')
    if not pandoc:
        pytest.skip('PANDOC environment path required')
    (tmp_path / 'panel.svg').write_bytes(svg(body))
    (tmp_path / 'input.md').write_text('![caption](panel.svg)\n')
    out = tmp_path / 'out'; out.mkdir()
    calls = []
    monkeypatch.setitem(sys.modules, 'cairosvg', types.SimpleNamespace(svg2pdf=lambda **k: calls.append(k)))
    with pytest.raises(ValueError, match='PDF_SVG_CSS_URL_REFUSED'):
        module.prepare(tmp_path / 'input.md', out / 'safe.md', pandoc=pandoc)
    assert not calls and not list(out.iterdir())

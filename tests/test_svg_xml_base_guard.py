"""Synthetic SVG xml:base resource-scope contract."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location('xml_base_guarded_prepare', ROOT / 'tools/prepare_pdf_resources.py')
prepare = module_from_spec(spec)
spec.loader.exec_module(prepare)

@pytest.mark.parametrize('data', [
    b'<svg xml:base="external.svg"><use href="#box"/></svg>',
    b'<svg><g xml:base="https://example.invalid/"><use href="#box"/></g></svg>',
    b'<svg xml:base="."><use href="#box"/></svg>',
    b'<svg xml:base=" "><use href="#box"/></svg>',
    '<svg xml:base="external.svg"><use href="#box"/></svg>'.encode('utf-16'),
])
def test_nonempty_xml_base_is_refused(data):
    with pytest.raises(ValueError, match='PDF_SVG_XML_BASE_REFUSED'):
        prepare.reject_svg_external_image_refs(data)

@pytest.mark.parametrize('data', [
    b'<svg><defs><rect id="box"/></defs><use href="#box"/></svg>',
    b'<svg xml:base=""><use href="#box"/></svg>',
    b'<svg><!-- xml:base="external.svg" --><text>xml:base</text></svg>',
    b'<svg xmlns:x="urn:example" x:base="value"/>',
])
def test_empty_or_unrelated_base_remains_supported(data):
    prepare.reject_svg_external_image_refs(data)

def test_prepare_refuses_before_conversion_and_publication(tmp_path, monkeypatch):
    import os, sys, types
    pandoc = os.environ.get('PANDOC')
    if not pandoc:
        pytest.skip('PANDOC path required')
    (tmp_path / 'panel.svg').write_bytes(b'<svg xml:base="other.svg"><use href="#box"/></svg>')
    (tmp_path / 'input.md').write_text('![caption](panel.svg)\n')
    out = tmp_path / 'out'; out.mkdir(); calls = []
    monkeypatch.setitem(sys.modules, 'cairosvg', types.SimpleNamespace(svg2pdf=lambda **k: calls.append(k)))
    with pytest.raises(ValueError, match='PDF_SVG_XML_BASE_REFUSED'):
        prepare.prepare(tmp_path / 'input.md', out / 'safe.md', pandoc=pandoc)
    assert not calls and not list(out.iterdir())

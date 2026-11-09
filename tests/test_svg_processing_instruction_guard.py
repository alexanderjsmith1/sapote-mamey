"""Synthetic tests for SVG XML processing-instruction resource policy."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location('pi_guarded_prepare', ROOT / 'tools/prepare_pdf_resources.py')
prepare = module_from_spec(spec)
spec.loader.exec_module(prepare)


@pytest.mark.parametrize('data', [
    b'<?xml-stylesheet type="text/css" href="styles.css"?><svg/>',
    b'<?xml-stylesheet href="https://example.invalid/style.css"?><svg/>',
    b'<svg><?example other?></svg>',
    '<?xml version="1.0" encoding="UTF-16"?><?xml-stylesheet href="styles.css"?><svg/>'.encode('utf-16'),
])
def test_processing_instructions_refused(data):
    with pytest.raises(ValueError, match='PDF_SVG_PROCESSING_INSTRUCTION_REFUSED'):
        prepare.reject_svg_external_image_refs(data)


@pytest.mark.parametrize('data', [
    b'<?xml version="1.0" encoding="UTF-8"?><svg/>',
    '<?xml version="1.0" encoding="UTF-16"?><svg/>'.encode('utf-16'),
    b'<svg><!-- <?xml-stylesheet href="not-real"?> --></svg>',
    b'<svg><text>xml-stylesheet</text></svg>',
])
def test_xml_declaration_and_comments_remain_supported(data):
    prepare.reject_svg_external_image_refs(data)


def test_malformed_xml_reports_existing_error():
    with pytest.raises(ValueError, match='PDF_SVG_XML_INVALID'):
        prepare.reject_svg_external_image_refs(b'<?xml-stylesheet href="x"?><svg')


def test_prepare_refuses_before_conversion_and_publication(tmp_path, monkeypatch):
    import os
    import sys
    import types
    pandoc = os.environ.get('PANDOC')
    if not pandoc:
        pytest.skip('PANDOC path required')
    (tmp_path / 'panel.svg').write_bytes(b'<?xml-stylesheet href="styles.css"?><svg/>')
    (tmp_path / 'input.md').write_text('![caption](panel.svg)\n')
    out = tmp_path / 'out'
    out.mkdir()
    calls = []
    monkeypatch.setitem(sys.modules, 'cairosvg', types.SimpleNamespace(svg2pdf=lambda **k: calls.append(k)))
    with pytest.raises(ValueError, match='PDF_SVG_PROCESSING_INSTRUCTION_REFUSED'):
        prepare.prepare(tmp_path / 'input.md', out / 'safe.md', pandoc=pandoc)
    assert not calls and not list(out.iterdir())

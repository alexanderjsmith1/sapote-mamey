"""Synthetic regression tests for direct nested SVG image references."""
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location
import os
import sys
import shutil
import types
import pytest

ROOT = Path(__file__).resolve().parents[1]
PANDOC = os.environ.get('PANDOC') or shutil.which('pandoc')
pytestmark = pytest.mark.skipif(not PANDOC, reason='Pandoc required')
spec = spec_from_file_location('guarded_prepare', ROOT / 'tools/prepare_pdf_resources.py')
prepare = module_from_spec(spec)
spec.loader.exec_module(prepare)

@pytest.mark.parametrize('href', ['art.png', 'https://example.invalid/art.png', 'file:///tmp/art.png', '#art', 'data:image/svg+xml;base64,PHN2Zy8+'])
def test_external_or_unresolved_svg_image_fails_before_conversion(tmp_path, monkeypatch, href):
    (tmp_path / 'art.png').write_bytes(b'local synthetic placeholder')
    svg = tmp_path / 'panel.svg'
    svg.write_text(f'<svg xmlns="http://www.w3.org/2000/svg"><image href="{href}"/></svg>')
    md = tmp_path / 'input.md'
    md.write_text('![panel][ref]\n\n[ref]: panel.svg\n')
    out = tmp_path / 'work'
    out.mkdir()
    calls = []
    monkeypatch.setitem(sys.modules, 'cairosvg', types.SimpleNamespace(svg2pdf=lambda **kw: calls.append(kw)))
    with pytest.raises(ValueError, match='PDF_SVG_EXTERNAL_IMAGE_REFUSED'):
        prepare.prepare(md, out / 'safe.md', pandoc=PANDOC)
    assert not calls and not list(out.iterdir())

@pytest.mark.parametrize('body', [
    '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h1"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/png;base64,AAAA"/></svg>',
])
def test_vector_and_data_image_pass_narrow_guard(tmp_path, monkeypatch, body):
    (tmp_path / 'panel.svg').write_text(body)
    md = tmp_path / 'input.md'
    md.write_text('![panel](panel.svg)\n')
    out = tmp_path / 'work'
    out.mkdir()
    def fake_convert(url, write_to):
        Path(write_to).write_bytes(b'%PDF synthetic')
    monkeypatch.setitem(sys.modules, 'cairosvg', types.SimpleNamespace(svg2pdf=fake_convert))
    prepare.prepare(md, out / 'safe.md', pandoc=PANDOC)
    assert (out / 'safe.md').exists()
    assert len(list(out.glob('*.pdf.conversion.json'))) == 1

def test_invalid_xml_fails_before_conversion(tmp_path):
    (tmp_path / 'panel.svg').write_text('<svg>')
    md = tmp_path / 'input.md'
    md.write_text('![panel](panel.svg)\n')
    out = tmp_path / 'work'
    out.mkdir()
    with pytest.raises(ValueError, match='PDF_SVG_XML_INVALID'):
        prepare.prepare(md, out / 'safe.md', pandoc=PANDOC)
    assert not list(out.iterdir())

def test_real_cairo_embedded_image_survives_and_external_is_refused(tmp_path):
    try:
        import cairosvg  # noqa: F401
    except (ImportError, OSError):
        pytest.skip('CairoSVG and its native Cairo library are required')
    Image = pytest.importorskip('PIL.Image')
    rasterizer = shutil.which('pdftoppm')
    if not rasterizer:
        pytest.skip('pdftoppm is required for synthetic raster verification')
    import base64
    import json
    import subprocess
    image = tmp_path / 'art.png'
    Image.new('RGB', (40, 40), 'red').save(image)
    payload = base64.b64encode(image.read_bytes()).decode('ascii')
    header = '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
    (tmp_path / 'external.svg').write_text(header + '<image width="40" height="40" href="art.png"/></svg>')
    (tmp_path / 'embedded.svg').write_text(header + '<image width="40" height="40" href="data:image/png;base64,' + payload + '"/></svg>')
    for name in ('external', 'embedded'):
        (tmp_path / (name + '.md')).write_text('![panel](' + name + '.svg)\n')
    bad = tmp_path / 'bad'
    good = tmp_path / 'good'
    bad.mkdir()
    good.mkdir()
    with pytest.raises(ValueError, match='PDF_SVG_EXTERNAL_IMAGE_REFUSED'):
        prepare.prepare(tmp_path / 'external.md', bad / 'safe.md', pandoc=PANDOC)
    assert not list(bad.iterdir())
    prepare.prepare(tmp_path / 'embedded.md', good / 'safe.md', pandoc=PANDOC)
    receipt = json.loads(next(good.glob('*.pdf.conversion.json')).read_text())
    assert receipt['converter'] == 'cairosvg'
    rendered = tmp_path / 'rendered'
    subprocess.run([rasterizer, '-png', '-singlefile', '-r', '72', receipt['converted_pdf'], str(rendered)], check=True)
    with Image.open(rendered.with_suffix('.png')) as raster:
        assert raster.convert('RGB').getpixel((10, 10)) == (255, 0, 0)

"""Synthetic integration checks for map binding, fallback and changing inputs."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import builtins
import hashlib
import json
import os
import subprocess
import sys
import types
import pytest

ROOT = Path(__file__).resolve().parents[1]
PANDOC = os.environ.get('PANDOC')
pytestmark = pytest.mark.skipif(not PANDOC, reason='PANDOC path required')
spec = spec_from_file_location('pdf_composed_guard', ROOT / 'tools/prepare_pdf_resources.py')
module = module_from_spec(spec); spec.loader.exec_module(module)

def paths(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    work = tmp_path / 'work'; work.mkdir()
    svg = source / 'panel.svg'; svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    md = source / 'input.md'; md.write_text('![A](panel.svg)\n\n![B](panel.svg)\n')
    return svg, md, work

@pytest.mark.parametrize('replacement', [b'<svg>', b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'])
def test_repeated_svg_change_reported_before_xml_validation(tmp_path, monkeypatch, replacement):
    svg, md, work = paths(tmp_path); real_read = Path.read_bytes; reads = []
    def read(path):
        if path == svg:
            reads.append(1)
            if len(reads) == 3:
                return replacement
        return real_read(path)
    monkeypatch.setattr(Path, 'read_bytes', read)
    monkeypatch.setitem(sys.modules, 'cairosvg', types.SimpleNamespace(svg2pdf=lambda url,write_to: Path(write_to).write_bytes(b'%PDF synthetic')))
    with pytest.raises(ValueError, match='PDF_SVG_SOURCE_CHANGED_DURING_PREPARATION'):
        module.prepare(md, work / 'safe.md', pandoc=PANDOC)
    assert not (work / 'safe.md').exists()
    assert not (work / 'safe.resource_map.json').exists()


def test_fallback_converter_recorded_with_real_pandoc_parse(tmp_path, monkeypatch):
    svg, md, work = paths(tmp_path)
    original_import = builtins.__import__
    def import_without_cairo(name, *args, **kwargs):
        if name == 'cairosvg':
            raise ImportError('synthetic unavailable converter')
        return original_import(name, *args, **kwargs)
    real_run = subprocess.run
    def selective_run(args, *a, **kw):
        if args[0] == 'rsvg-convert':
            Path(args[args.index('-o')+1]).write_bytes(b'%PDF synthetic fallback')
            return subprocess.CompletedProcess(args, 0)
        return real_run(args, *a, **kw)
    monkeypatch.setattr(builtins, '__import__', import_without_cairo)
    monkeypatch.setattr(module.subprocess, 'run', selective_run)
    monkeypatch.setattr(module.shutil, 'which', lambda name: '/test/rsvg-convert' if name == 'rsvg-convert' else None)
    module.prepare(md, work / 'safe.md', pandoc=PANDOC)
    receipt = json.loads(next(work.glob('*.pdf.conversion.json')).read_text())
    mapping = json.loads((work / 'safe.resource_map.json').read_text())
    assert receipt['converter'] == 'rsvg-convert'
    assert receipt['source_svg_sha256'] == hashlib.sha256(svg.read_bytes()).hexdigest()
    assert mapping['targets']['panel.svg'] == receipt['converted_pdf']
    assert (work / 'safe.md').read_text() == md.read_text()

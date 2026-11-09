"""Synthetic checks for output-relative local SVG companion links."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import unquote

import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PANDOC = os.environ.get('PANDOC') or shutil.which('pandoc')
PYTHON = sys.executable
pytestmark = pytest.mark.skipif(not PANDOC, reason='pandoc not installed')


def run(args, env):
    subprocess.run(args, check=True, capture_output=True, text=True, env=env)


@pytest.mark.parametrize('same_directory', [False, True])
def test_actual_pandoc_companion_rebased_and_other_links_unchanged(tmp_path, same_directory):
    assert PANDOC
    report = tmp_path / 'bundle' / 'report'
    assets = report / 'figure folder'
    assets.mkdir(parents=True)
    svg = assets / 'paired & one.svg'
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    output = report if same_directory else tmp_path / 'bundle' / 'output'
    output.mkdir(exist_ok=True)
    md = report / 'report.md'
    md.write_text('# Test\n\n[SVG version](<figure folder/paired & one.svg>)\n\n'
                  '[Other](<figure folder/paired & one.svg>)\n\n'
                  '[SVG version](<missing.svg>)\n\n'
                  '[SVG version](https://example.org/remote.svg)\n')
    work = tmp_path / 'work'
    work.mkdir()
    env = dict(os.environ, PANDOC=PANDOC, MAMEY_PDF_LINK_OUTPUT_DIR=str(output))
    prepared, safe = work / 'resources.md', work / 'safe.md'
    run([PYTHON, str(ROOT / 'tools/prepare_pdf_resources.py'), str(md), str(prepared)], env)
    resource_map = work / 'resources.resource_map.json'
    mapping = json.loads(resource_map.read_text())
    assert len(mapping['svg_companions']) == 1
    target = next(iter(mapping['svg_companions'].values()))
    assert (output / unquote(target)).resolve() == svg.resolve()
    assert '%20' in target and '%26' in target
    run([PYTHON, str(ROOT / 'tools/sapote_md_preflight.py'), str(prepared), str(safe),
         '--profile', 'boss', '--appendix-md', str(work / 'appendix.md'),
         '--qa-json', str(work / 'qa.json')], env)
    tex = work / 'report.tex'
    env['SAPOTE_PDF_RESOURCE_MAP'] = str(resource_map)
    run([PANDOC, str(safe), '-f', 'markdown', '-t', 'latex', '-s',
         '--lua-filter=' + str(ROOT / 'tools/pdf_resource_filter.lua'), '-o', str(tex)], env)
    latex = tex.read_text()
    assert target.replace('%', r'\%') in latex
    assert r'\href{missing.svg}{SVG version}' in latex
    assert r'\href{https://example.org/remote.svg}{SVG version}' in latex
    assert r'\href{figure\%20folder/paired\%20&\%20one.svg}{Other}' in latex
    moved = tmp_path / 'moved'
    shutil.copytree(tmp_path / 'bundle', moved)
    moved_output = moved / ('report' if same_directory else 'output')
    assert (moved_output / unquote(target)).resolve() == (moved / 'report' / 'figure folder' / svg.name).resolve()
    assert (moved_output / unquote(target)).is_file()


def test_preparer_without_output_location_leaves_companions_unchanged(tmp_path):
    assert PANDOC
    (tmp_path / 'figure.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    md = tmp_path / 'source.md'
    md.write_text('[SVG version](figure.svg)\n')
    env = dict(os.environ, PANDOC=PANDOC)
    env.pop('MAMEY_PDF_LINK_OUTPUT_DIR', None)
    prepared = tmp_path / 'prepared.md'
    run([PYTHON, str(ROOT / 'tools/prepare_pdf_resources.py'), str(md), str(prepared)], env)
    assert json.loads((tmp_path / 'prepared.resource_map.json').read_text())['svg_companions'] == {}
    assert prepared.read_text() == md.read_text()

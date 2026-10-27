"""Render generic matrices and inspect numeric-label contrast in the saved SVG.

SAPOTE_MATRIX_TOOLS selects an isolated tools/ tree; no real genomes are needed.
"""
from pathlib import Path
import csv
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest

pytestmark = pytest.mark.slow

SVG = '{http://www.w3.org/2000/svg}'


def _fill(node):
    match = re.search(r'(?:^|;)\s*fill:\s*(#[A-Fa-f0-9]{6})', node.attrib.get('style', ''))
    # SVG text defaults to black when svglite omits the fill declaration.
    if match:
        return match.group(1)
    if node.tag == SVG + 'text' and 'fill:' not in node.attrib.get('style', ''):
        return '#000000'
    return None


def _luminance(colour):
    channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [x / 12.92 if x <= 0.04045 else ((x + .055) / 1.055) ** 2.4 for x in channels]
    return sum(w * c for w, c in zip((.2126, .7152, .0722), linear))


def _contrast(a, b):
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + .05) / (low + .05)


@pytest.mark.parametrize('profile', ['SINGLE_COLUMN', 'DOUBLE_COLUMN'])
@pytest.mark.parametrize('figure_id, values', [
    ('F02_megasynthase_heatmap', [[0, 1, 10], [37, 47, 60], [101, 3, 20]]),
    ('F01_census_zscore_heatmap', [[-2, -1, -.25], [0, .25, 1], [2, -.5, .5]]),
])
def test_saved_cell_labels_have_readable_contrast(tmp_path, profile, figure_id, values):
    if not shutil.which('Rscript'):
        pytest.skip('Rscript is required for the native output test')
    tools = Path(os.environ.get('SAPOTE_MATRIX_TOOLS', Path(__file__).resolve().parents[1] / 'tools')).resolve()
    source = tmp_path / 'generic_matrix.csv'
    with source.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['row', 'Example alpha', 'Example beta', 'Example gamma'])
        writer.writerows([[f'Feature {i + 1}'] + row for i, row in enumerate(values)])
    out = tmp_path / 'native_matrix'
    result = subprocess.run(
        ['Rscript', str(tools / 'sapote_matrix_figure.R'), str(source), str(out),
         figure_id, profile, 'Generic matrix'], capture_output=True, text=True,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    root = ET.parse(out.with_suffix('.svg')).getroot()
    assert not list(root.iter(SVG + 'image')), 'Artwork must remain vector'
    cells = []
    for rect in root.iter(SVG + 'rect'):
        if _fill(rect) and all(k in rect.attrib for k in ['x', 'y', 'width', 'height']):
            cells.append(rect)
    labels = []
    for text in root.iter(SVG + 'text'):
        shown = ''.join(text.itertext()).strip()
        if not re.fullmatch(r'-?\d+(?:\.\d+)?', shown):
            continue
        x, y = float(text.attrib['x']), float(text.attrib['y'])
        containing = [r for r in cells
                      if float(r.attrib['x']) <= x <= float(r.attrib['x']) + float(r.attrib['width'])
                      and float(r.attrib['y']) <= y <= float(r.attrib['y']) + float(r.attrib['height'])]
        assert containing, f'Numeric label {shown} is not inside a cell'
        cell = min(containing, key=lambda r: float(r.attrib['width']) * float(r.attrib['height']))
        ink, background = _fill(text), _fill(cell)
        assert ink and background
        ratio = _contrast(ink, background)
        labels.append(shown)
        assert ratio >= 4.5, f'{shown}: {ink} on {background}, contrast={ratio:.3f}'
        size = re.search(r'font-size:\s*([\d.]+)', text.attrib['style'])
        assert size and float(size[1]) >= 8
    assert len(labels) == 9, 'Every generic matrix cell must retain its numeric label'
    # Native display rounds values to integers; the fix must not alter that contract.
    assert sorted(float(x) for x in labels) == sorted(float(round(x)) for row in values for x in row)

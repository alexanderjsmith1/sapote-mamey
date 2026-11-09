"""A failed locus-comparison write leaves no partial output set, so a retry can succeed.

The renderer used to write the three images, the coordinate sidecar and the receipt one by
one into the output directory. A failure after the first file left an incomplete set without
its receipt, and the next attempt refused because an output already existed.
"""
import json
import shutil
from pathlib import Path

import pytest

from mamey.figures import locus_comparison as m

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ('comparison.svg', 'comparison.png', 'comparison.pdf', 'display_coordinates.json', 'receipt.json')


def _manifest(tmp_path, slide):
    spec = json.loads((ROOT / 'examples/locus_comparison_synthetic.json').read_text())
    if slide:
        spec.setdefault('display', {})['view'] = 'slide'
    path = tmp_path / 'input.json'
    path.write_text(json.dumps(spec))
    return path


@pytest.mark.parametrize('slide', [False, True])
def test_pdf_failure_leaves_nothing_and_retry_succeeds(tmp_path, monkeypatch, slide):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.figure import Figure
    manifest = _manifest(tmp_path, slide)
    out = tmp_path / 'render'
    real = Figure.savefig

    def failing(self, fname, *args, **kwargs):
        if str(fname).endswith('.pdf'):
            raise OSError('simulated PDF write failure')
        return real(self, fname, *args, **kwargs)

    monkeypatch.setattr(Figure, 'savefig', failing)
    with pytest.raises(OSError, match='simulated PDF write failure'):
        m.render(manifest, out)
    assert not any((out / name).exists() for name in OUTPUTS)
    assert not [p.name for p in tmp_path.iterdir() if p.name.startswith('.mamey-output-')]

    monkeypatch.setattr(Figure, 'savefig', real)
    receipt = m.render(manifest, out)
    assert all((out / name).is_file() for name in OUTPUTS)
    saved = json.loads((out / 'receipt.json').read_text())
    assert saved['files'] == receipt['files']
    import hashlib
    for name, digest in saved['files'].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest


def test_existing_output_is_still_refused(tmp_path):
    manifest = _manifest(tmp_path, False)
    out = tmp_path / 'render'
    out.mkdir()
    (out / 'comparison.png').write_bytes(b'prior')
    with pytest.raises(FileExistsError):
        m.render(manifest, out)
    assert (out / 'comparison.png').read_bytes() == b'prior'

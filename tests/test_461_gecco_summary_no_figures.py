"""Summary mode must honor the requested no-figure output boundary."""
import csv
import json
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ is a package; sibling test modules import by bare name
from test_457_gecco_report_summary_per_mb import gcr, rows, summary


def test_no_figures_writes_summary_and_receipt_without_rendering(tmp_path, monkeypatch):
    source = summary(tmp_path, rows())
    def forbidden(*args, **kwargs):
        pytest.fail('the no-figures route must not invoke a figure renderer')
    monkeypatch.setattr(gcr, 'fig_calls_vs_references', forbidden)
    output = tmp_path / 'out'
    assert gcr.main(['--summary', str(source), '--out', str(output), '--no-figures']) == 0
    with (output / 'summary_by_genome.tsv').open(newline='') as handle:
        saved = list(csv.DictReader(handle, delimiter='\t'))
    assert len(saved) == len(rows())
    assert saved[0]['strain'] == 'I-1'
    receipt = json.loads((output / 'receipt.json').read_text())
    assert receipt['mode'] == 'summary' and receipt['figures_requested'] is False
    assert 'summary_by_genome.tsv' in receipt['outputs_sha256']
    assert not (output / 'calls_vs_references').exists()


def test_default_summary_still_invokes_renderer(tmp_path, monkeypatch):
    source = summary(tmp_path, rows())
    seen = []
    monkeypatch.setattr(gcr, 'fig_calls_vs_references', lambda *args, **kwargs: seen.append((args, kwargs)) or [])
    assert gcr.main(['--summary', str(source), '--out', str(tmp_path / 'out')]) == 0
    assert len(seen) == 1

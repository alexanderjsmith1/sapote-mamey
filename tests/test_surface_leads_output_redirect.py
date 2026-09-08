"""Actual command paths must honor --out without touching canonical outputs."""
from pathlib import Path
import os
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('via_cli', [False, True])
def test_redirect_preserves_canonical_deliverable(tmp_path, via_cli):
    data = tmp_path / 'data'
    source = data / 'strain_data/whole_bgc_majority_read_2026-08-05'
    source.mkdir(parents=True)
    (source / 'whole_bgc_majority_read_cohort.csv').write_text('flags\n')
    canonical = data / 'strain_data/flagged_lead_surfacing_2026-08-05'
    canonical.mkdir()
    (canonical / 'FLAGGED_LEAD_SURFACING.md').write_text('keep owner deliverable')
    out = tmp_path / 'redirect with spaces'
    cmd = [sys.executable, str(ROOT / 'mamey_run.py'), 'surface-leads'] if via_cli else [sys.executable, str(ROOT / 'deliverable_tools/surface_flagged_leads.py')]
    result = subprocess.run(cmd + ['--out', str(out)], cwd=tmp_path,
                            env=dict(os.environ, MAMEY_DATA_ROOT=str(data), PYTHONDONTWRITEBYTECODE='1'),
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert {p.name for p in out.iterdir()} == {'FLAGGED_LEAD_SURFACING.md', 'flagged_lead_surfacing.csv'}
    assert (canonical / 'FLAGGED_LEAD_SURFACING.md').read_text() == 'keep owner deliverable'
    assert len(list(canonical.iterdir())) == 1

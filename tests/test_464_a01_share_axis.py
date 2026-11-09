"""Card 464_a01_share_axis: A01 can draw each row as a share of the isolates tested.

The share axis adds an All isolates row, prints strong / tested at the end of each bar and folds genus rows with fewer
than a01_share_min_isolates isolates into one Other genera row. The count axis is unchanged. Synthetic IDs only."""
import csv
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from mamey.bioassay_paper import cli, write

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / 'tools/bioassay_a01.R'


def inputs(tmp_path, layout_extra=None):
    roster = tmp_path / 'roster.tsv'; table = tmp_path / 'table.tsv'; aliases = tmp_path / 'aliases.json'; lock = tmp_path / 'lock.md'
    genera = ['Streptomyces'] * 4 + ['Nocardia'] * 3 + ['Kribbella', 'Dietzia'] + ['Unassigned']
    write(roster, [dict(strain=f'SYN-{900 + i}', genus=g, group='Honeybees') for i, g in enumerate(genera)])
    vals = [95, 10, 60, 30, 85, 5, 20, 90, 0, 81]
    write(table, [dict(strain=f'SYN-{900 + i}', organism=o, material='Crude extract', best_pct=v)
                  for i, v in enumerate(vals) for o in ('Candida albicans', 'MRSA')])
    aliases.write_text('{}'); lock.write_text('lock\n')
    layouts = json.loads((ROOT / 'mamey/data/bioassay_layouts.json').read_text())
    layouts['bee'].update(layout_extra or {})
    cfg = tmp_path / 'layouts.json'; cfg.write_text(json.dumps(layouts))
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    return ['--table', str(table), '--table-sha256', h(table), '--roster', str(roster), '--aliases', str(aliases),
            '--lock', str(lock), '--lock-sha256', h(lock), '--layout', 'bee', '--layout-config', str(cfg)]


def test_x_axis_is_a01_only(tmp_path):
    with pytest.raises(ValueError, match='A01 only'):
        cli('A02', ROOT / 'tools/bioassay_a02.R', inputs(tmp_path) + ['--x-axis', 'share', '--out', str(tmp_path / 'o'), '--prepare-only'])


def test_bad_profile_value_refused(tmp_path):
    with pytest.raises(ValueError, match='count or share'):
        cli('A01', R, inputs(tmp_path, {'a01_x_axis': 'log'}) + ['--out', str(tmp_path / 'o'), '--prepare-only'])


def test_profile_key_reaches_config_and_caption(tmp_path):
    out = tmp_path / 'o'
    cli('A01', R, inputs(tmp_path, {'a01_x_axis': 'share'}) + ['--out', str(out), '--prepare-only'])
    assert json.loads((out / 'render_config.json').read_text())['x_axis'] == 'share'
    assert json.loads((out / 'RUN_INFO.json').read_text())['x_axis'] == 'share'
    assert 'strong / tested' in (out / 'CAPTION.md').read_text()


def test_count_is_the_default(tmp_path):
    out = tmp_path / 'o'
    cli('A01', R, inputs(tmp_path) + ['--out', str(out), '--prepare-only'])
    assert json.loads((out / 'render_config.json').read_text())['x_axis'] == 'count'
    assert 'strong / tested' not in (out / 'CAPTION.md').read_text()


@pytest.mark.skipif(shutil.which('Rscript') is None, reason='needs R: Rscript not on PATH')
def test_share_rows_fold_and_pool(tmp_path):
    out = tmp_path / 'o'
    cli('A01', R, inputs(tmp_path) + ['--x-axis', 'share', '--out', str(out)])
    with (out / 'A01_bee_crude_share_rows.tsv').open() as f:
        rows = {(r['target'], r['row']): r for r in csv.DictReader(f, delimiter='\t')}
    # Kribbella and Dietzia have one isolate each: one Other genera row of 2 genera; Unassigned is never folded
    assert rows['Candida sp.', 'Other genera']['row_label'] == 'Other genera (2)'
    assert rows['Candida sp.', 'Other genera']['lab'] == '1 / 2'
    assert ('Candida sp.', 'Kribbella') not in rows and ('Candida sp.', 'Unassigned') in rows
    assert rows['Candida sp.', 'All isolates']['lab'] == '4 / 10'
    assert rows['Candida sp.', 'Streptomyces']['lab'] == '1 / 4' and rows['Candida sp.', 'Nocardia']['lab'] == '1 / 3'
    for ext in ('.png', '.pdf', '.svg'):
        assert (out / f'A01_bee_crude{ext}').exists()

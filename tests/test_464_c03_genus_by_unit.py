"""Card 464_c03_genus_by_unit: C02's roster draws a matrix of isolates by sampling unit and genus.

The group of each unit is drawn exactly as the input gives it. A unit under two groups is refused, not resolved, and the
caption counts the stated basis of each group. Synthetic IDs only."""
import csv
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/genus_composition_figures.py'
spec = importlib.util.spec_from_file_location('composition_c03', TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
FIELDS = ['strain', 'group', 'genus', 'colony', 'row_block', 'group_basis']


def roster(tmp_path, rows):
    p = tmp_path / 'isolates.tsv'
    module.write_tsv(p, FIELDS, [dict(zip(FIELDS, r)) for r in rows])
    return p


ROWS = [('SYN-901', 'Atta', 'Streptomyces', 'C1', 'Actinomycetota', 'own deposit'),
        ('SYN-902', 'Atta', 'Streptomyces', 'C1', 'Actinomycetota', 'another isolate of the colony'),
        ('SYN-903', 'Atta', 'Unassigned', '', 'No genus\\non record', 'own deposit'),
        ('SYN-904', 'Acromyrmex', 'Pseudonocardia', 'C2', 'Actinomycetota', 'own deposit'),
        ('SYN-905', 'Not recorded', 'Citrobacter', 'C3', 'Other\\nphyla', '')]
ARGS = ['--layout', 'attine', '--groups', 'Atta', 'Acromyrmex', 'Not recorded', '--unit-column', 'colony',
        '--group-title', 'Host ant genus of the colony']


def test_unit_under_two_groups_is_refused(tmp_path):
    rows = ROWS + [('SYN-906', 'Acromyrmex', 'Nocardia', 'C1', 'Actinomycetota', 'own deposit')]
    with pytest.raises(ValueError, match='more than one group'):
        module.main(['--isolates', str(roster(tmp_path, rows)), '--out', str(tmp_path / 'o')] + ARGS)


def test_missing_unit_column_is_refused(tmp_path):
    with pytest.raises(ValueError, match='needs column'):
        module.main(['--isolates', str(roster(tmp_path, ROWS)), '--out', str(tmp_path / 'o'), '--layout', 'attine',
                     '--groups', 'Atta', 'Acromyrmex', 'Not recorded', '--unit-column', 'nest'])


@pytest.mark.skipif(shutil.which('Rscript') is None, reason='needs R: Rscript not on PATH')
def test_matrix_counts_caption_and_stamp(tmp_path):
    out = tmp_path / 'o'
    assert module.main(['--isolates', str(roster(tmp_path, ROWS)), '--out', str(out)] + ARGS) == 0
    with (out / 'C03_genus_by_unit_numbers.tsv').open() as f:
        cells = {(r['group'], r['unit'], r['genus']): int(r['n']) for r in csv.DictReader(f, delimiter='\t')}
    assert cells[('Atta', 'C1', 'Streptomyces')] == 2
    assert cells[('Atta', 'No colony on record', 'Unassigned')] == 1      # a blank unit is drawn, not dropped
    assert sum(cells.values()) == len(ROWS)
    cap = (out / 'CAPTION.md').read_text()
    assert 'own deposit, 3' in cap and 'another isolate of the colony, 1' in cap and 'not stated in the input, 1' in cap
    info = json.loads((out / 'RUN_INFO.json').read_text())
    assert info['figure'] == 'C03' and info['n_units'] == 4
    for ext in ('.png', '.pdf'):
        assert b'Sapote-Mamey genus_composition_figures' in (out / f'C03_genus_by_unit{ext}').read_bytes()

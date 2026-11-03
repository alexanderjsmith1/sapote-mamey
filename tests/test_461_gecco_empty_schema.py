"""An empty GECCO table is zero calls only if its required header is present."""
import csv
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ is a package; sibling test modules import by bare name
from test_457_gecco_cohort_report import kit, run

VALID = ['sequence_id', 'cluster_id', 'start', 'end', 'type', 'max_p', 'average_p', 'proteins', 'domains']

@pytest.mark.parametrize('header', ['', 'unrelated\tcolumns\n', 'sequence_id\tcluster_id\n'])
def test_missing_header_fields_refused_before_output(tmp_path, header):
    kit(tmp_path)
    (tmp_path / 'S-1.clusters.tsv').write_text(header)
    assert run(tmp_path, '--no-figures') == 2
    assert not (tmp_path / 'out').exists()

def test_valid_header_without_rows_is_a_valid_zero(tmp_path):
    kit(tmp_path)
    (tmp_path / 'S-1.clusters.tsv').write_text('\t'.join(VALID) + '\n')
    assert run(tmp_path, '--no-figures') == 0
    with (tmp_path / 'out' / 'summary_by_genome.tsv').open(newline='') as handle:
        row = next(csv.DictReader(handle, delimiter='\t'))
    assert row['gecco_calls'] == '0'
    assert row['calls_in_regions'] == '0'

@pytest.mark.parametrize('kind', ['duplicate_header', 'short_row', 'extra_cell'])
def test_malformed_cluster_table_refused_before_output(tmp_path, kind):
    kit(tmp_path)
    path = tmp_path / 'S-1.clusters.tsv'
    with path.open(newline='') as handle:
        rows = list(csv.reader(handle, delimiter='\t'))
    if kind == 'duplicate_header':
        rows[0].append(rows[0][0])
        for row in rows[1:]:
            row.append(row[0])
    elif kind == 'short_row':
        rows[1].pop()
    else:
        rows[1].append('unexpected extra cell')
    with path.open('w', newline='') as handle:
        csv.writer(handle, delimiter='\t').writerows(rows)
    assert run(tmp_path, '--no-figures') == 2
    assert not (tmp_path / 'out').exists()

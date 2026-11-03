"""Malformed retained alignments must not become negative rescue calls."""
from pathlib import Path
import importlib.util
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import gap_directed_rescue as rescue


@pytest.mark.parametrize('text', [
    'q1\ts1\t99\t50\n', 'q1\ts1\t99\t50\t100\t1\n',
    'q1\ts1\t99\t50\t100\t1\t\n', '\ts1\t99\t50\t100\n',
    'q1\ts1\tnan\t50\t100\n', 'q1\ts1\t101\t50\t100\n',
    'q1\ts1\t99\t-1\t100\n', 'q1\ts1\t99\t50\tinf\n',
    'q1\ts1\t99\t50\t100\t0\t2\n', 'q1\ts1\t99\t50\t100\t1\t2\tnan\n',
])
def test_invalid_rows_refuse_with_line_number(tmp_path, text):
    path = tmp_path / 'hits.tsv'; path.write_text('\n' + text)
    with pytest.raises(ValueError, match='GAP_RESCUE_HIT_ROW_INVALID: .*:2:'):
        rescue.read_hits(path)


def test_valid_five_seven_and_eight_column_rows(tmp_path):
    path = tmp_path / 'hits.tsv'
    path.write_text('q1\ts1\t50\t70\t20\nq2\ts2\t0\t100\t0\t1\t90\n'
                    'q3\ts3\t90\t80\t40\t1\t90\t1e-12\n')
    rows = rescue.read_hits(path)
    assert len(rows) == 3 and rows[0]['pident'] == 50
    assert rows[1]['qstart'] == 1 and rows[1]['qend'] == 90
    assert rows[2]['evalue'] == 1e-12


def test_empty_file_is_not_a_parse_error(tmp_path):
    path = tmp_path / 'hits.tsv'; path.write_text('')
    assert rescue.read_hits(path) == []


def test_incomplete_row_after_valid_row_refuses_entire_input(tmp_path):
    path = tmp_path / 'hits.tsv'; path.write_text('q1\ts1\t50\t70\t20\nq2\ts2\t90\n')
    with pytest.raises(ValueError, match='GAP_RESCUE_HIT_ROW_INVALID'):
        rescue.read_hits(path)


def test_command_line_refuses_malformed_input_before_output(tmp_path):
    fixture_path = Path(__file__).with_name('test_444_gap_directed_rescue.py')
    spec = importlib.util.spec_from_file_location('gap_rescue_fixture_444', fixture_path)
    fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
    genome, reference, hits = fixture._setup(tmp_path)
    with hits.open('a') as handle:
        handle.write('g006\tq000006\t60\n')
    output = tmp_path / 'rescue-output'
    result = subprocess.run([sys.executable, rescue.__file__, '--zip', str(genome), '--label', 'T',
                             '--core', 'ctgA.region001', '--reference', str(reference), '--out', str(output),
                             '--hits', str(hits), '--no-figure', '--no-gene-table'], capture_output=True, text=True)
    assert result.returncode != 0 and 'GAP_RESCUE_HIT_ROW_INVALID' in result.stderr
    assert not output.exists()

"""The 16S admission guard catches an identical pair within one sample, even beside a third sequence.

It refused only when every query sequence in the sample was identical, so a sample with two
identical reads and one different read passed with a duplicate tip in the tree.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_admission_fixture_458", ROOT / "tests" / "test_phylo_sequence_admission_v97429.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


def _q(tip, seq, sample, acc):
    return _fx.row(tip, seq, role='query', type_status='not_applicable', organism='Streptomyces sp.',
                   expected_genus='Streptomyces', biological_sample_id=sample, accession=acc)


def test_identical_pair_beside_a_different_read_fails():
    a, b = 'A' * 1400, 'C' * 1400
    rows = [_q('Q1', a, 'EXP55-S2', 'P1'), _q('Q2', a, 'EXP55-S2', 'P2'), _q('Q3', b, 'EXP55-S2', 'P3')]
    with pytest.raises(ValueError, match='DUPLICATE_QUERY_SAME_SAMPLE_SEQUENCE') as e:
        _fx.validate(rows, {'Q1': a, 'Q2': a, 'Q3': b})
    assert 'Q1' in str(e.value) and 'Q2' in str(e.value) and 'Q3' not in str(e.value)


def test_distinct_reads_in_one_sample_pass():
    a, b = 'A' * 1400, 'C' * 1400
    rows = [_q('Q1', a, 'EXP55-S2', 'P1'), _q('Q2', b, 'EXP55-S2', 'P2')]
    assert _fx.validate(rows, {'Q1': a, 'Q2': b})['status'] == 'ADMISSION_PASS'

"""Missing evidence must not become a negative reference-gene result."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import gap_rescue_gene_table as gt

CORE = 'TEST / NODE_1_length_900_cov_1 / region001 / BGC001'


def row(status=None, best_locus=''):
    result = {'reference_gene': '1', 'name': 'ref1', 'best_locus': best_locus,
              'reference_len_aa': '200', 'reference_product': 'reference annotation'}
    if status is not None:
        result['status'] = status
    return result


@pytest.mark.parametrize('status', [None, '', ' ', '\t'])
@pytest.mark.parametrize('best_locus', ['', 'stale_gene'])
def test_missing_status_refuses_even_with_a_stale_hit(status, best_locus):
    with pytest.raises(ValueError, match='GAP_RESCUE_STATUS_MISSING'):
        gt.table_rows([row(status, best_locus)], [], CORE, {}, {})


def test_recorded_negative_remains_a_negative():
    result = gt.table_rows([row('MISSING_NOT_FOUND')], [], CORE, {}, {})[0]
    assert result['CDS'] == 'not found' and result['Location'] == 'not found'


def test_generator_input_is_not_consumed_by_validation():
    result = gt.table_rows((r for r in [row('MISSING_NOT_FOUND')]), [], CORE, {}, {})
    assert len(result) == 1 and result[0]['CDS'] == 'not found'


def test_unrecognized_nonblank_outcome_is_named_not_recast_as_negative():
    result = gt.table_rows([row('FUTURE_REVIEW')], [], CORE, {}, {})[0]
    assert result['CDS'] == '-' and result['Location'] == 'status future review'


def test_write_refuses_before_replacing_existing_output(tmp_path, monkeypatch):
    table = tmp_path / 'gene_table.tsv'
    table.write_text('previous evidence\n')
    monkeypatch.setattr(gt, 'reference_annotations', lambda _: {})
    with pytest.raises(ValueError, match='GAP_RESCUE_STATUS_MISSING'):
        gt.write_gene_table(tmp_path, [row()], [], CORE, 'test', Path('reference.gbk'), {}, pair_map=False)
    assert table.read_text() == 'previous evidence\n'

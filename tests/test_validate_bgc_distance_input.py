import csv
import hashlib
import json

import pytest

from tools.validate_bgc_distance_input import validate


IDS = ['A / contigA / region001 / BGC001', 'B / contigB / region002 / BGC002']


def inputs(tmp_path, rows=None, ids=None, **receipt_changes):
    matrix = tmp_path / 'matrix.csv'
    ids = ids or IDS
    rows = rows or [[ids[0], '0', '0.4'], [ids[1], '0.4', '0']]
    with matrix.open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['locus_identity', *ids]); w.writerows(rows)
    receipt = tmp_path / 'receipt.json'
    data = {'output_sha256': hashlib.sha256(matrix.read_bytes()).hexdigest(),
            'records': 2, 'unordered_pairs': 1, 'no_hsp_regions': []}
    data.update(receipt_changes)
    receipt.write_text(json.dumps(data))
    return matrix, receipt


def test_valid_synthetic_pair(tmp_path):
    m, r = inputs(tmp_path)
    assert validate(m, r, 32)['status'] == 'STRUCTURAL_CHECK_ONLY'


@pytest.mark.parametrize('rows, error', [
    ([[IDS[0], '0', '0.4'], [IDS[1], '0.5', '0']], 'ASYMMETRIC_DISTANCE'),
    ([[IDS[0], '0.1', '0.4'], [IDS[1], '0.4', '0']], 'NONZERO_DIAGONAL'),
    ([[IDS[0], '0', 'nan'], [IDS[1], 'nan', '0']], 'INVALID_DISTANCE'),
    ([[IDS[1], '0', '0.4'], [IDS[0], '0.4', '0']], 'ROW_IDENTITY_OR_WIDTH_MISMATCH'),
    ([[IDS[0], '0', '0.4']], 'MATRIX_ROW_COUNT_MISMATCH'),
])
def test_bad_matrices_refuse(tmp_path, rows, error):
    m, r = inputs(tmp_path, rows=rows)
    with pytest.raises(ValueError, match=error): validate(m, r, 32)


def test_hash_hsp_and_budget_refuse(tmp_path):
    m, r = inputs(tmp_path, no_hsp_regions=[{'locus_identity': IDS[0]}])
    with pytest.raises(ValueError, match='NO_HSP_REQUIRES_REVIEW'): validate(m, r, 32)
    m, r = inputs(tmp_path)
    with pytest.raises(ValueError, match='MATRIX_MEMORY_LIMIT'): validate(m, r, 31)
    m.write_text(m.read_text() + '\n')
    with pytest.raises(ValueError, match='MATRIX_HASH_MISMATCH'): validate(m, r, 32)


def test_full_identity_required(tmp_path):
    m, r = inputs(tmp_path, ids=['A / contigA / region001', IDS[1]])
    with pytest.raises(ValueError, match='INCOMPLETE_LOCUS_IDENTITY'): validate(m, r, 32)

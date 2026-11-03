"""Split display must expose the base-hit assessment without assigning it to split pieces."""
import importlib
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
table = importlib.import_module('gap_rescue_gene_table')

@pytest.mark.parametrize('status,verdict,expected,absent', [
    ('MISSING_FOUND_AMBIGUOUS', 'PARALOG_FAMILY', ['base hit ambiguous', 'base-hit partner verdict: paralog family'], []),
    ('MISSING_FOUND_CLEAR', 'SINGLE_GENE', ['base-hit partner verdict: single gene'], ['base hit ambiguous']),
    ('MISSING_FOUND_CLEAR', 'SUPPORTED', [], ['base hit ambiguous', 'base-hit partner verdict']),
    ('MISSING_NOT_FOUND', '', [], ['base hit ambiguous', 'base-hit partner verdict']),
    ('MISSING_FOUND_AMBIGUOUS', 'NEW_FLAG', ['base hit ambiguous', 'base-hit partner verdict: new flag'], []),
])
def test_split_row_preserves_base_hit_status_and_verdict(status, verdict, expected, absent):
    core = 'SYNTHETIC / NODE_1_length_900_cov_1 / region001 / BGC001'
    partner = 'SYNTHETIC / NODE_2_length_900_cov_1 / region001 / BGC002'
    rows = [{'reference_gene': '1', 'name': 'reference_1', 'status': status,
             'partner_verdict': verdict, 'reference_len_aa': '500', 'best_locus': 'whole_candidate'}]
    splits = [{'reference_gene': '1', 'name': 'reference_1', 'status': 'SPLIT_ACROSS_CONTIG_ENDS',
               'split_call': 'CLEAR', 'piece1_locus': 'piece_a', 'piece2_locus': 'piece_b',
               'piece1_region_identity': core, 'piece2_region_identity': partner,
               'piece1_identity_pct': '70', 'piece2_identity_pct': '65'}]
    output = table.table_rows(rows, splits, core, {}, {})
    assert len(output) == 1
    location = output[0]['Location']
    assert location.startswith('split across ')
    assert all(x in location for x in expected)
    assert all(x not in location for x in absent)
    assert output[0]['CDS'] == 'piece_a + piece_b'

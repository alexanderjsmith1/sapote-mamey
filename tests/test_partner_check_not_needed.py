"""Do not report a missing database when reciprocal search has no candidates."""
import pytest

from mamey.ref_completion import partner_checks


@pytest.mark.parametrize('database', [None, 'database-is-supplied.dmnd'])
def test_all_matches_in_core_do_not_need_reciprocal_search(database):
    core = {'contig': 'ctg1', 'start': 0, 'end': 1000}
    proteins = {'p1': {'contig': 'ctg1', 'start': 10, 'end': 900, 'aa': 'M' * 100}}
    rows = [{'reference_gene': 1, 'status': 'PRESENT_IN_CORE', 'best_protein': 'p1'}]

    def unexpected_search(*args, **kwargs):
        pytest.fail('No outside-core candidate exists to search')

    result = partner_checks(rows, proteins, [], core, 'BGC0000001', mibig_db=database,
                            search=unexpected_search)
    assert result['reciprocal_mibig'] == 'not needed: no outside-core finds'
    assert result['neighbour_pfam'] == 'not needed'
    assert result['verdicts'] == {}

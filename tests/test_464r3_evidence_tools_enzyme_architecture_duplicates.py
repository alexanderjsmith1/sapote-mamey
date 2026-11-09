"""Two architecture rows for one gene key are a hold, never a silent last-row-wins projection."""
import pytest
from mamey.cohort_enzyme_neighborhoods import project
from tests.test_cohort_enzyme_neighborhoods import fixture


def test_duplicate_architecture_rows_are_held():
    args = list(fixture())
    agenes = args[4]
    exact = [g for g in agenes if g['membership'] == 'EXACT_REGION']
    dup = dict(exact[0], product='a conflicting annotation')
    args[4] = list(agenes) + [dup]
    with pytest.raises(ValueError, match='DUPLICATE_ARCHITECTURE_GENE_HOLD'):
        project(*args)


def test_unique_architecture_rows_still_project():
    assert project(*fixture())['genes']

"""An unrelated clause cannot provide an identity claim's hedge or denial."""
import pytest
from tools.claim_safety_linter import lint_claim_safety, lint_claim_safety_report

@pytest.mark.parametrize('lint', [lint_claim_safety, lint_claim_safety_report])
@pytest.mark.parametrize('prefix', [
    'The adjacent domain looks Streptomyces-like, and ',
    'This is a comparator region; ',
    'The neighboring domain is a class anchor; ',
    'We do not claim activity for the neighbor; ',
    'The neighbor is consistent with a terpene, but ',
])
def test_unrelated_clause_does_not_exempt_production(lint, prefix):
    assert lint(prefix + 'This strain produces bafilomycin.', compound_names={'bafilomycin'})

@pytest.mark.parametrize('lint', [lint_claim_safety, lint_claim_safety_report])
@pytest.mark.parametrize('text', [
    'The evidence does not support that this strain produces bafilomycin.',
    'The comparator is bafilomycin.',
    'The class anchor retained from the similarity ranking is bafilomycin.',
    'The capacity is consistent with a bafilomycin-like scaffold.',
])
def test_local_hedge_and_denial_still_pass(lint, text):
    assert not lint(text, compound_names={'bafilomycin'})


@pytest.mark.parametrize('lint', [lint_claim_safety, lint_claim_safety_report])
def test_compound_later_in_clause_is_not_copula_object(lint):
    assert not lint('This is precisely the historical issue with bafilomycin.', compound_names={'bafilomycin'})
    assert lint('This compound is phosphonoacetic acid.', compound_names={'phosphonoacetic acid'})

@pytest.mark.parametrize('lint', [lint_claim_safety, lint_claim_safety_report])
def test_local_explicit_production_denial(lint):
    assert not lint('The similarity does not mean identity, not that this strain makes bafilomycin.', compound_names={'bafilomycin'})
    assert not lint('No production is claimed.')

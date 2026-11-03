"""Text-only safety tests; no figures, taxonomy or product identity adjudication."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
TARGET=Path(__file__).resolve().parents[1]/'mamey/render_safe.py'
spec=importlib.util.spec_from_file_location('kcb_under_test',TARGET)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
CASES=[({'closest_product_provenance':'MIBIG_REFERENCE_LINE','kcb_top':'X'*200},'', ' (similarity)'),({'closest_candidate_kcb_product':'X'*200,'kcb_top':'ignored'},'~',' (similarity anchor only)'),({'closest_product_provenance':'KCB_TOP_FIELD','kcb_top':'X'*200},'~',' (source-derived similarity anchor only; not product identity)'),({'closest_product_provenance':'OTHER','kcb_top':'X'*200},'',' (similarity)')]


@pytest.mark.parametrize('record,prefix,qualifier',CASES)
@pytest.mark.parametrize('limit',[80,120])
def test_long_text_retains_exact_qualifier_and_bound(record,prefix,qualifier,limit):
    output=mod.safe_kcb_display(record,max_chars=limit)
    assert output.endswith(qualifier)
    assert output.startswith(prefix+'X')
    assert len(output)<=limit
    assert output.endswith('…'+qualifier)


@pytest.mark.parametrize('record,prefix,qualifier',CASES)
def test_limit_that_cannot_fit_claim_refuses(record,prefix,qualifier):
    with pytest.raises(ValueError,match='KCB_DISPLAY_LIMIT_TOO_SMALL'):
        mod.safe_kcb_display(record,max_chars=len(prefix)+len(qualifier)+1)


@pytest.mark.parametrize('record,prefix,qualifier',CASES)
def test_minimum_shortening_budget_preserves_real_anchor_character(record,prefix,qualifier):
    limit=len(prefix)+len(qualifier)+2
    assert mod.safe_kcb_display(record,max_chars=limit)==prefix+'X…'+qualifier


@pytest.mark.parametrize('record,expected',[({'closest_product_provenance':'MIBIG_REFERENCE_LINE','kcb_top':'short'},'short (similarity)'),({'closest_candidate_kcb_product':'short'},'~short (similarity anchor only)'),({'kcb_top':'short'},'~short (source-derived similarity anchor only; not product identity)'),({},'unresolved')])
def test_short_text_unchanged(record,expected):
    assert mod.safe_kcb_display(record)==expected
    assert mod.safe_kcb_display(SimpleNamespace(**record))==expected


def test_exact_fit_keeps_anchor_unshortened():
    record={'closest_candidate_kcb_product':'anchor'}
    full='~anchor (similarity anchor only)'
    assert mod.safe_kcb_display(record,max_chars=len(full))==full

"""The receipt explains current gates without upgrading a search result."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('precomputed', [True, False])
def test_thresholds_record_current_policy_and_search_state(tmp_path, monkeypatch, precomputed):
    spec = importlib.util.spec_from_file_location('gap_threshold_test', ROOT/'tools/gap_directed_rescue.py')
    tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
    monkeypatch.setattr(tool, 'load_reference', lambda _: ([], 'fixture'))
    monkeypatch.setattr(tool, 'run_diamond', lambda *a: tool._AlignmentHits([], {'capture_state': 'CAPTURED'}))
    monkeypatch.setattr(tool, 'search', lambda *a: ([], []))
    monkeypatch.setattr(tool, 'split_genes', lambda *a: ([], 'not run: fixture'))
    monkeypatch.setattr(tool, 'partner_checks', lambda *a, **k: {})
    result = tool.analyse_region('test', {}, [], {'identity': 'T / contig / region001 / BGC001'},
                                 'ref.gbk', '', 'fixture', tmp_path/'out',
                                 hits=[] if precomputed else None, figure=False,
                                 gene_table=False, write_proteins=False)
    saved = json.loads((tmp_path/'out/gap_rescue_receipt.json').read_text())
    policy = saved['reference_match_policy']
    assert policy['minimum_reference_coverage_percent'] == tool._rc.MIN_COV == 50.0
    assert policy['minimum_identity_percent'] == tool._rc.MIN_ID == 30.0
    assert policy['core_alternate_minimum_identity_percent'] == tool._rc.MIN_ID_CORE == 25.0
    assert policy['core_alternate_maximum_evalue'] == tool._rc.MAX_EVALUE_CORE
    assert policy['outside_clear_minimum_identity_percent'] == tool._rc.CLEAR_ID
    assert policy['outside_clear_minimum_bitscore_ratio_if_rival'] == tool._rc.CLEAR_RATIO
    assert 'partial alignments may exist' in policy['not_found_interpretation']
    assert 'Not established' in policy['search_completeness']
    assert saved['forward_alignment']['capture_state'] == ('PRECOMPUTED_UNVERIFIED' if precomputed else 'CAPTURED')
    assert saved['reference_match_policy'] == result['reference_match_policy']

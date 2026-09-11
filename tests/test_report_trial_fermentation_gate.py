"""Generated planning text and historical diagnostic summaries must compose with report gates."""
import csv
import json
from mamey import compile_report as report
from mamey.claim_safety_gate import lint_text


def test_siderophore_plan_passes_existing_claim_gate(tmp_path):
    (tmp_path/'TEST_4_triage_board.csv').write_text('Products\nsiderophore\n')
    text = report._fermentation_draft(tmp_path)
    assert 'CAS assay' in text
    assert not lint_text(text)


def test_prior_refusal_is_reported_without_republishing_rejected_text(tmp_path):
    rejected = 'This cluster shows antibacterial activity against Staphylococcus aureus.'
    issue = '[CLAIM-SAFETY REFUSAL] auto-emitted compiled report WITHHELD: '+rejected
    (tmp_path/'manifest.json').write_text(json.dumps({'strain_id':'TEST','issues':[issue]}))
    text = report._assembly_table(report._read_manifests(tmp_path))
    assert 'withheld' in text.lower()
    assert 'manifest.json' in text
    assert rejected not in text
    assert not lint_text(text)


def test_current_overclaim_still_fails_and_ordinary_issues_remain(tmp_path):
    rejected = 'This cluster shows antibacterial activity against Staphylococcus aureus.'
    assert lint_text(rejected)
    (tmp_path/'manifest.json').write_text(json.dumps({'strain_id':'TEST','issues':['Assembly is fragmented.',rejected]}))
    text = report._assembly_table(report._read_manifests(tmp_path))
    assert 'Assembly is fragmented.' in text
    assert rejected in text
    assert lint_text(text)

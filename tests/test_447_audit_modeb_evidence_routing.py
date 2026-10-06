"""Audit R05/R08/R09: profile routing, bound roster and honest limitations."""
import json
from types import SimpleNamespace

import pytest
from mamey import authored_verify, modeb_template_emitter
from mamey.modeb_current50_v2 import load_contract, v2_findings
from mamey.modeb_structure_gate import lint_card

ROSTER = ['ctg1_1', 'ctg1_2']
HEADER = '''#### Complete named-match, channel-separated table
| Gene | NCBI nr accession + matched protein | nr id/pos/qcov | NCBI ClusteredNR accession + matched protein | ClusteredNR id/pos/qcov | local Swiss-Prot accession + matched protein | Swiss-Prot id/pos/qcov |
|---|---|---|---|---|---|---|
'''
ROWS = [f'| {gene} | WP_000001 — synthase [Streptomyces examplei] | 90% id / 95% positives / qcov 100% | no bound hit | no bound hit | no bound hit | no bound hit |\n' for gene in ROSTER]


def card(table=HEADER + ''.join(ROWS), profile='FINISHED_FULL50_CURRENT50_V2'):
    return f'**Document state:** {profile}\n## §4 Gene-by-gene interpretation\nSee §50.\n## §50 Data evidence table\n{table}'


def evidence_findings(md, ctx=None, contract='current50_v2'):
    return [f for f in lint_card(md, contract=load_contract(contract),
                                bgc_context=ctx, check_evidence_presence=True)
            if f['code'].startswith('BLASTP_MATRIX') or f['code'] == 'EVIDENCE_GAP']


def test_v2_roster_is_required_independently_of_authored_table():
    got = evidence_findings(card())
    assert [f['code'] for f in got] == ['BLASTP_MATRIX_ROSTER_UNBOUND']
    assert got[0]['section'] == 50


def test_v2_complete_channels_and_independent_roster_pass():
    assert evidence_findings(card(), {'known_locus_tags': ROSTER, 'has_blastp_panel': True}) == []


@pytest.mark.parametrize('table, code', [
    ('| gene | GECCO p |\n|---|---|\n| ctg1_1 | 0.91 |', 'BLASTP_MATRIX_MISSING'),
    (HEADER + ROWS[0], 'BLASTP_MATRIX_ROSTER'),
    (HEADER + ''.join(ROWS) + ROWS[0], 'BLASTP_MATRIX_ROSTER'),
    ((HEADER + ''.join(ROWS)).replace('nr id/pos/qcov', 'merged numbers'), 'BLASTP_MATRIX_CHANNELS'),
    ((HEADER + ''.join(ROWS)).replace('90% id / 95% positives / qcov 100%', '90% id'), 'BLASTP_MATRIX_METRICS'),
    ((HEADER + ''.join(ROWS)).replace('WP_000001 — synthase [Streptomyces examplei]', 'WP_000001'), 'BLASTP_MATRIX_SUBJECTS'),
])
def test_v2_refuses_incomplete_gene_or_channel_evidence(table, code):
    got = evidence_findings(card(table), {'known_locus_tags': ROSTER})
    assert code in {f['code'] for f in got}
    assert all(f['section'] == 50 for f in got)


def test_v2_cannot_use_complete_table_in_section4_instead():
    wrong = card().replace('See §50.', HEADER + ''.join(ROWS)).replace(
        '## §50 Data evidence table\n' + HEADER + ''.join(ROWS), '## §50 Data evidence table\nMissing.')
    assert 'BLASTP_MATRIX_MISSING' in {f['code'] for f in evidence_findings(wrong, {'known_locus_tags': ROSTER})}


def test_full48_evidence_stays_in_section4():
    md = card(profile='FINISHED_FULL48_CURRENT_EVIDENCE').replace('## §4 Gene-by-gene interpretation\nSee §50.\n', '')
    assert evidence_findings(md, {'known_locus_tags': ROSTER}, 'full48')[0]['code'] == 'BLASTP_MATRIX_MISSING'
    proper = md.replace('## §50 Data evidence table', '## §4 Gene-by-gene interpretation')
    assert evidence_findings(proper, {'known_locus_tags': ROSTER}, 'full48') == []


def test_draft_v2_is_not_forced_into_finished_matrix():
    assert evidence_findings(card('| gene | GECCO p |\n|---|---|\n| ctg1_1 | 0.91 |', 'DRAFT')) == []


def test_precise_not_run_limitation_is_not_a_deferral():
    md = '## §22 GECCO\nNOT_RUN: GECCO was not evaluated because its source file is unavailable; no prediction is inferred.'
    assert 'V2_DEFERRAL' not in {f['code'] for f in v2_findings(md)}


@pytest.mark.parametrize('text', [
    'NOT_RUN: GECCO was not evaluated.',
    'NOT_RUN: GECCO was not evaluated because its source file is unavailable.',
    'GECCO was not evaluated because its source file is unavailable; no prediction is inferred.',
    'NOT_RUN: GECCO was not evaluated because its source file is unavailable; no prediction is inferred. TODO add results.',
    'NOT_RUN: GECCO was not evaluated because its source file is unavailable; no prediction is inferred.\nRegulators were not evaluated.',
    'NOT_RUN: GECCO was not evaluated because its source file is unavailable; no prediction is inferred. Regulators were not evaluated.',
])
def test_typed_token_cannot_hide_generic_deferral_or_todo(text):
    assert 'V2_DEFERRAL' in {f['code'] for f in v2_findings('## §22 GECCO\n' + text)}


def test_cli_v2_receipt_names_contract_and_reports_unbound_roster(tmp_path):
    path = tmp_path / 'modeb.md'
    path.write_text(modeb_template_emitter.emit_card_template(tmp_path, 'BGC001', contract=load_contract('current50_v2')) + '\nFINISHED_FULL50_CURRENT50_V2\n')
    receipt = tmp_path / 'verify.json'
    args = SimpleNamespace(file=str(path), contract='current50_v2', report_json=str(receipt), summary_only=True)
    assert authored_verify.verify_modeb_command(args) == 1
    got = json.loads(receipt.read_text())
    assert got['contract'] == 'current50_v2'
    assert got['contract_schema_version'] == 'modeb_current50_v2'
    assert '§1–§50' in got['profile'] and '§1–§48' not in got['profile']
    assert got['independent_roster_bound'] is False
    assert any(f['code'] == 'BLASTP_MATRIX_ROSTER_UNBOUND' and f['section'] == 50 for f in got['findings'])


def test_v2_receipt_reports_real_roster_binding_and_coverage_section(tmp_path, monkeypatch):
    monkeypatch.setattr(authored_verify, '_bgc_context_from_package', lambda *args: {'known_locus_tags': ROSTER})
    path = tmp_path / 'modeb.md'
    path.write_text(card().replace('90% id', 'CONFIRM 90% id'))
    receipt = tmp_path / 'verify.json'
    authored_verify.verify_modeb_command(SimpleNamespace(file=str(path), contract='current50_v2', report_json=str(receipt), summary_only=True))
    got = json.loads(receipt.read_text())
    assert got['independent_roster_bound'] is True
    gaps = [f for f in got['findings'] if f['code'] == 'COVERAGE_UNVERIFIED']
    assert len(gaps) == 1 and gaps[0]['section'] == 50 and '§50' in gaps[0]['message']


def test_missing_file_receipt_preserves_selected_contract(tmp_path):
    receipt = tmp_path / 'verify.json'
    args = SimpleNamespace(file=str(tmp_path / 'missing.md'), contract='current50_v2', report_json=str(receipt))
    assert authored_verify.verify_modeb_command(args) == 1
    got = json.loads(receipt.read_text())
    assert got['contract'] == 'current50_v2'
    assert got['contract_schema_version'] == 'modeb_current50_v2'
    assert got['profile'] == 'unresolved'


@pytest.mark.parametrize("contract, limit", [("full48", 48), ("current50_v2", 50)])
def test_failure_summary_uses_selected_contract_range(tmp_path, capsys, contract, limit):
    from types import SimpleNamespace
    from mamey.authored_verify import verify_modeb_command
    card = tmp_path / "plain.md"
    card.write_text("Plain text without section headings.\n", encoding="utf-8")
    assert verify_modeb_command(SimpleNamespace(file=str(card), contract=contract, summary_only=True)) == 1
    assert f"A hand-built doc without §1–§{limit} headings" in capsys.readouterr().out


@pytest.mark.parametrize("reason", [
    "the source file, e.g. the configured output, is unavailable",
    "the source file, i.e. the configured output, is unavailable",
    "Dr. Example did not provide the configured output",
    "Prof. Example did not provide the configured output",
])
def test_reasoned_limitation_abbreviations_do_not_end_the_sentence(reason):
    text = f"NOT_RUN: GECCO was not evaluated because {reason}; no prediction is inferred."
    assert "V2_DEFERRAL" not in {f["code"] for f in v2_findings("## §22 GECCO\n" + text)}


@pytest.mark.parametrize("suffix", [
    " Regulators were not evaluated.",
    " TODO add the configured results.",
    "\nRegulators were not evaluated.",
])
def test_abbreviations_cannot_exempt_adjacent_deferrals(suffix):
    text = ("NOT_RUN: GECCO was not evaluated because the source file, e.g. the configured "
            "output, is unavailable; no prediction is inferred." + suffix)
    assert "V2_DEFERRAL" in {f["code"] for f in v2_findings("## §22 GECCO\n" + text)}


def test_abbreviation_cannot_join_a_separate_line_to_borrow_its_ceiling():
    text = ("NOT_RUN: GECCO was not evaluated because its source file was withheld by Dr.\n"
            "Example; no prediction is inferred.")
    assert "V2_DEFERRAL" in {f["code"] for f in v2_findings("## §22 GECCO\n" + text)}

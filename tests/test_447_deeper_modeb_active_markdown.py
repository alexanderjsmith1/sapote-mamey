"""Synthetic parser controls for active Markdown, independent matrix cells and honest receipts."""
import json
from types import SimpleNamespace

import pytest

from mamey import authored_verify
from mamey.modeb_current50_v2 import load_contract, v2_findings
from mamey.modeb_markdown import active_markdown
from mamey.modeb_structure_gate import extract_section_titles, lint_card

ROSTER = ['ctg1_1', 'ctg1_2']
HEADER = ('#### Complete named-match, channel-separated table\n'
          '| Gene | NCBI nr accession matched protein | nr identity qcov | '
          'NCBI ClusteredNR accession matched protein | ClusteredNR identity qcov | '
          'local Swiss-Prot accession matched protein | Swiss-Prot identity qcov |\n'
          '|---|---|---|---|---|---|---|\n')
ROWS = [f'| {tag} | WP_000001 — synthetic fixture [Synthetic fixture] | CONFIRM 90% id / 95% positives / qcov 100% | no bound hit | no bound hit | no bound hit | no bound hit |\n'
        for tag in ROSTER]
TABLE = HEADER + ''.join(ROWS)


def full_card(table=TABLE, profile='FINISHED_FULL50_CURRENT50_V2'):
    # Parser-only text and DOI token: this supplies no real source or biological conclusion.
    prose = 'Synthetic parser fixture; independent content review is required and no biological conclusion is stated. ' * 12
    text = f'**Document state:** {profile}\n'
    for section in load_contract('current50_v2')['sections']:
        number = section['number']
        text += f'## §{number} {section["title"]}\n{prose}\n'
        if number in (48, 49):
            text += 'Synthetic citation parser token doi:10.1000/fixture; relevance is parser-only.\n'
        if number == 50:
            text += table + '\n'
    return text


def verify(tmp_path, monkeypatch, text, ctx=None):
    monkeypatch.setattr(authored_verify, '_bgc_context_from_package', lambda *args: {'known_locus_tags': ROSTER} if ctx is None else ctx)
    path, receipt = tmp_path / 'fixture.md', tmp_path / 'receipt.json'
    path.write_text(text)
    result = authored_verify.verify_modeb_command(SimpleNamespace(file=str(path), contract='current50_v2',
                                                                  report_json=str(receipt), summary_only=True))
    return result, json.loads(receipt.read_text())


@pytest.mark.parametrize('wrap', [lambda text: '<!--\n' + text + '-->',
                                  lambda text: '```markdown\n' + text + '```',
                                  lambda text: '~~~~markdown\n' + text + '~~~~',
                                  lambda text: '\n'.join('    ' + line for line in text.splitlines())])
def test_inactive_whole_card_cannot_supply_headings(tmp_path, monkeypatch, wrap):
    result, receipt = verify(tmp_path, monkeypatch, wrap(full_card()))
    assert result == 1 and receipt['status'] == 'FAIL'
    assert not receipt['coverage_verified']
    assert not extract_section_titles(wrap(full_card()), load_contract('current50_v2'))


@pytest.mark.parametrize('wrap', [lambda text: '<!--\n' + text + '-->',
                                  lambda text: '```text\n' + text + '```',
                                  lambda text: '~~~text\n' + text + '~~~'])
def test_inactive_matrix_cannot_satisfy_finished_evidence(tmp_path, monkeypatch, wrap):
    result, receipt = verify(tmp_path, monkeypatch, full_card(wrap(TABLE)))
    assert result == 1
    codes = {f['code'] for f in receipt['findings']}
    assert {'BLASTP_MATRIX_MISSING', 'V2_EVIDENCE_TABLE_MISSING'} <= codes


@pytest.mark.parametrize('hidden', ['<!-- historical FINISHED_FULL50_CURRENT50_V2 -->',
                                     '```text\nFINISHED_FULL50_CURRENT50_V2\n```'])
def test_hidden_profile_does_not_upgrade_active_draft(tmp_path, monkeypatch, hidden):
    table = '| Gene | state |\n|---|---|\n| ctg1_1 | unavailable |'
    result, receipt = verify(tmp_path, monkeypatch, full_card(table, 'DRAFT') + '\n' + hidden)
    assert result == 0
    assert not any(f['code'].startswith('BLASTP_MATRIX') for f in receipt['findings'])


def matrix_codes(table, contract='current50_v2'):
    section = 50 if contract == 'current50_v2' else 4
    token = 'FINISHED_FULL50_CURRENT50_V2' if section == 50 else 'FINISHED_FULL48_CURRENT_EVIDENCE'
    text = f'{token}\n## §{section} Data evidence table\n{table}'
    return {f['code'] for f in lint_card(text, contract=load_contract(contract),
                                        bgc_context={'known_locus_tags': ROSTER}, check_evidence_presence=True)
            if f['code'].startswith('BLASTP_MATRIX')}


@pytest.mark.parametrize('contract', ['full48', 'current50_v2'])
def test_visible_complete_matrix_still_passes_both_profiles(contract):
    assert not matrix_codes(TABLE, contract)


@pytest.mark.parametrize('contract', ['full48', 'current50_v2'])
def test_match_and_metric_columns_cannot_collapse(contract):
    table = ('#### Complete named-match, channel-separated table\n'
             '| Gene | NCBI nr accession matched protein identity qcov | '
             'NCBI ClusteredNR accession matched protein identity qcov | '
             'local Swiss-Prot accession matched protein identity qcov |\n|---|---|---|---|\n')
    table += ''.join(f'| {tag} | WP_000001 — synthetic fixture [Synthetic fixture] 90% id / 95% positives / qcov 100% | no bound hit | no bound hit |\n'
                     for tag in ROSTER)
    assert 'BLASTP_MATRIX_CHANNELS' in matrix_codes(table, contract)


def test_nr_and_swiss_prot_cannot_share_channel_columns():
    table = ('#### Complete named-match, channel-separated table\n'
             '| Gene | NCBI nr local Swiss-Prot accession matched protein | '
             'NCBI nr local Swiss-Prot identity qcov | NCBI ClusteredNR accession matched protein | '
             'NCBI ClusteredNR identity qcov |\n|---|---|---|---|---|\n')
    table += ''.join(f'| {tag} | WP_000001 — synthetic fixture [Synthetic fixture] | 90% id / 95% positives / qcov 100% | no bound hit | no bound hit |\n'
                     for tag in ROSTER)
    assert 'BLASTP_MATRIX_CHANNELS' in matrix_codes(table)


def test_missing_roster_row_never_claims_coverage_verified(tmp_path, monkeypatch):
    result, receipt = verify(tmp_path, monkeypatch, full_card(HEADER + ROWS[0]),
                              {'known_locus_tags': ROSTER, 'n_core_genes': 2})
    assert result == 1
    assert receipt['package_core_denominator_bound']
    assert not receipt['coverage_verified']
    assert any(f['code'] == 'BLASTP_MATRIX_ROSTER' for f in receipt['findings'])


def test_successful_bound_actual_coverage_check_reports_true(tmp_path, monkeypatch):
    result, receipt = verify(tmp_path, monkeypatch, full_card(),
                              {'known_locus_tags': ROSTER, 'n_core_genes': 2})
    assert result == 0 and receipt['coverage_verified']


def test_denominator_presence_without_a_checked_grid_is_not_coverage(tmp_path, monkeypatch):
    table = '| source | state |\n|---|---|\n| fixture | unavailable |'
    result, receipt = verify(tmp_path, monkeypatch, full_card(table, 'DRAFT'),
                              {'known_locus_tags': ROSTER, 'n_core_genes': 2})
    assert result == 0
    assert receipt['package_core_denominator_bound'] and not receipt['coverage_verified']


def test_active_view_preserves_offsets_and_ignores_comment_syntax_inside_code():
    text = '```text\n<!-- literal code\n```\n## §1 Identity and node/region\nVisible.\n'
    view = active_markdown(text)
    assert len(view) == len(text) and view.count('\n') == text.count('\n')
    assert '## §1' in view and '<!--' not in view
    assert extract_section_titles(text)[0][0] == 1


def test_fence_inside_comment_does_not_consume_following_active_content():
    text = '<!--\n```markdown\n-->\n## §1 Identity and node/region\nVisible.\n'
    assert extract_section_titles(text)[0][0] == 1


def test_commented_citation_and_relevance_do_not_satisfy_v2_literature():
    text = '## §48 Literature\n<!-- doi:10.1000/fixture relevance -->\n'
    assert {'V2_LITERATURE_NO_CITATION', 'V2_LITERATURE_NO_RELEVANCE'} <= {f['code'] for f in v2_findings(text)}


@pytest.mark.parametrize("profile", ["FINISHED_FULL50_CURRENT50_V2", "FINISHED_FULL48_CURRENT_EVIDENCE"])
def test_first_line_canonical_metadata_preserves_the_strict_profile(profile):
    from mamey.modeb_markdown import verification_markdown
    header = ("<!-- MODE B | canonical_identity: synthetic fixture | contract: current50_v2 | "
              "contract_sha256: " + "0" * 64 + " | profile: " + profile + " -->\n")
    view = verification_markdown(header + "## §1 Identity and node/region\n")
    assert profile in view
    assert len(view) == len(header + "## §1 Identity and node/region\n")


def test_canonical_header_only_profile_requires_independent_roster(tmp_path, monkeypatch):
    header = ("<!-- MODE B | canonical_identity: synthetic fixture | contract: current50_v2 | "
              "contract_sha256: " + "0" * 64 + " | profile: FINISHED_FULL50_CURRENT50_V2 -->\n")
    text = full_card().split("\n", 1)[1]  # remove the visible state declaration
    result, receipt = verify(tmp_path, monkeypatch, header + text, {})
    assert result == 1
    assert any(f["code"] == "BLASTP_MATRIX_ROSTER_UNBOUND" for f in receipt["findings"])


def test_later_canonical_looking_comment_does_not_upgrade_draft(tmp_path, monkeypatch):
    header = ("<!-- MODE B | canonical_identity: historical fixture | contract: current50_v2 | "
              "contract_sha256: " + "0" * 64 + " | profile: FINISHED_FULL50_CURRENT50_V2 -->\n")
    table = "| Gene | state |\n|---|---|\n| ctg1_1 | unavailable |"
    result, receipt = verify(tmp_path, monkeypatch, full_card(table, "DRAFT") + "\n" + header)
    assert result == 0
    assert not any(f["code"].startswith("BLASTP_MATRIX") for f in receipt["findings"])


def test_explicit_placeholder_view_retains_comments_but_excludes_code_examples():
    text = ("<!-- Author: active placeholder -->\n"
            "```text\n<!-- Author: code example -->\n```\n"
            "    <!-- Author: indented code example -->\n")
    view = active_markdown(text, preserve_comments=True)
    assert "Author: active placeholder" in view
    assert "Author: code example" not in view
    assert "Author: indented code example" not in view
    assert "Author:" not in active_markdown(text)

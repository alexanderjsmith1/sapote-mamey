"""Synthetic controls for the selective r5/reader + newer-audit composition.

No real card, package, biological sequence or BLAST result is consumed.
"""
import json
from types import SimpleNamespace

import pytest

from mamey import authored_verify
from mamey.modeb_current50_v2 import header_line, load_contract

ROSTER = ['ctg1_1', 'ctg1_2']
IDENTITY = ('AS-999', 'NODE_1_length_10000_cov_1', 'region001', 'BGC001')
HEADER = ('#### Complete named-match, channel-separated table\n'
          '| Gene | NCBI nr accession matched protein | nr identity qcov | '
          'NCBI ClusteredNR accession matched protein | ClusteredNR identity qcov | '
          'local Swiss-Prot accession matched protein | Swiss-Prot identity qcov |\n'
          '|---|---|---|---|---|---|---|\n')
ROWS = [f'| {tag} | WP_000001 — synthetic fixture [Synthetic fixture] | CONFIRM 90% id / 95% positives / qcov 100% | no bound hit | no bound hit | no bound hit | no bound hit |\n'
        for tag in ROSTER]


def card(table):
    text = header_line(*IDENTITY) + '\n# Mode B — ' + ' / '.join(IDENTITY) + '\n'
    prose = 'Synthetic parser fixture; independent review is required and no biological conclusion is stated. ' * 12
    for section in load_contract('current50_v2')['sections']:
        number = section['number']
        text += f'## §{number} {section["title"]}\n{prose}\n'
        if number in (48, 49):
            text += 'Synthetic citation parser token doi:10.1000/fixture; relevance is parser-only.\n'
        if number == 26:
            text += 'ctg9_6 is an existence-only context identifier; focal membership remains unassigned.\n'
        if number == 50:
            text += table
    return text


def verify(tmp_path, monkeypatch, table, roster_bound=True):
    ctx = {'known_loci': set(ROSTER), 'n_core_genes': 2}
    if roster_bound:
        ctx['known_locus_tags'] = list(ROSTER)
    monkeypatch.setattr(authored_verify, '_bgc_context_from_package', lambda *args: ctx)
    path, receipt, rescue = tmp_path/'synthetic.md', tmp_path/'receipt.json', tmp_path/'gap_rescue.tsv'
    path.write_text(card(table))
    rescue.write_text('best_locus\tbest_region_identity\nctg9_6\tAS-999 / NODE_9_length_8000_cov_1 (no antiSMASH region)\n')
    result = authored_verify.verify_modeb_command(SimpleNamespace(
        file=str(path), contract='current50_v2', rescue_tsv=[str(rescue)],
        report_json=str(receipt), summary_only=True))
    return result, json.loads(receipt.read_text()), ctx


def test_native_header_and_rescue_existence_do_not_expand_focal_roster(tmp_path, monkeypatch):
    result, receipt, ctx = verify(tmp_path, monkeypatch, HEADER+''.join(ROWS))
    assert result == 0 and receipt['coverage_verified']
    assert 'admitted for existence only (ctg9_6)' in receipt['profile']
    assert ctx['known_locus_tags'] == ROSTER and ctx['n_core_genes'] == 2
    assert ctx['known_loci'] == set(ROSTER+['ctg9_6'])


@pytest.mark.parametrize('table', [HEADER+ROWS[0], '<!--\n'+HEADER+''.join(ROWS)+'-->\n'])
def test_rescue_admission_cannot_hide_missing_or_inactive_focal_evidence(tmp_path, monkeypatch, table):
    result, receipt, ctx = verify(tmp_path, monkeypatch, table)
    assert result == 1 and receipt['package_core_denominator_bound']
    assert not receipt['coverage_verified']
    assert any(f['code'] in ('BLASTP_MATRIX_ROSTER','BLASTP_MATRIX_MISSING') for f in receipt['findings'])
    assert ctx['known_locus_tags'] == ROSTER


def test_native_first_line_profile_with_rescue_requires_independent_roster(tmp_path, monkeypatch):
    result, receipt, _ = verify(tmp_path, monkeypatch, HEADER+''.join(ROWS), roster_bound=False)
    assert result == 1 and not receipt['independent_roster_bound']
    assert not receipt['coverage_verified']
    assert any(f['code'] == 'BLASTP_MATRIX_ROSTER_UNBOUND' for f in receipt['findings'])

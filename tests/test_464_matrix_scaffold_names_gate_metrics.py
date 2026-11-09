"""Card 464_matrix_scaffold_names_gate_metrics: the emitted §50 matrix scaffold asked for
"identity / aligned length / qcov", while the gate requires % identity, % positives and query coverage in
every bound cell. An author who followed the template exactly got BLASTP_MATRIX_METRICS. The scaffold now
names the gate's metrics, accepts the gate's typed "qcov not reported", and carries the reconciliation
verdict on the same row. Synthetic fixtures only.
"""
import re

from mamey.modeb_template_emitter import _render_blastp_matrix_scaffold
from .test_447_audit_modeb_evidence_routing import card, evidence_findings

ROSTER = ['ctg1_1', 'ctg1_2']
HEADING = '#### Complete named-match, channel-separated table\n'


def _scaffold():
    return _render_blastp_matrix_scaffold([{'locus_tag': t} for t in ROSTER])


def test_scaffold_names_the_gate_metrics_and_a_verdict_column():
    text = _scaffold()
    assert text.count('% positives') == 3 * len(ROSTER)
    assert 'qcov not reported' in text and 'aligned length' not in text
    assert 'antiSMASH call and reconciliation' in text.splitlines()[0]


def test_unfilled_scaffold_reads_as_neither_reconciled_nor_measured():
    rows = _scaffold().splitlines()[2:]
    assert not any(re.search(r'\b(CONFIRM|REFINE|OVERTURN)\b', r) for r in rows)
    assert not any(re.search(r'\d+(?:\.\d+)?\s*%', r) for r in rows)


def test_row_filled_in_the_scaffold_shape_passes_the_matrix_gate():
    filled = _scaffold()
    filled = filled.replace('<accession · matched protein · organism · state>',
                            'WP_000001 — synthase [Streptomyces examplei]')
    filled = filled.replace('<% identity / % positives / qcov %, or qcov not reported>',
                            '90.0% id / 95.0% positives / qcov not reported')
    filled = filled.replace('<antiSMASH call; reconciliation verdict and its reason>',
                            'PKS_KS — CONFIRM: both channels name the same activity')
    found = evidence_findings(card(HEADING + filled + '\n'), {'known_locus_tags': ROSTER})
    assert not [f for f in found if f['code'].startswith('BLASTP_MATRIX')], found


def test_emitted_header_passes_the_channel_column_check():
    found = evidence_findings(card(HEADING + _scaffold() + '\n'), {'known_locus_tags': ROSTER})
    assert 'BLASTP_MATRIX_CHANNELS' not in {f['code'] for f in found}

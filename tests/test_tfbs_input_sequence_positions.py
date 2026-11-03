"""TFBS hits carry explicit 1-based inclusive bounds on the input sequence; legacy hit fields are unchanged.

Adapted from Codex Patch Series patch 33's test. Legacy hits are pinned to the pre-patch output."""
from types import SimpleNamespace
from mamey import source_scans as new

NEW_KEYS = ('input_sequence_start_1based', 'input_sequence_end_1based', 'motif_orientation_on_input')

def gene(strand, start, end):
    return SimpleNamespace(contig='chr', start=start, end=end, strand=strand, locus_tag='synthetic', product='synthetic')

def legacy(approx, strand):
    return {'motif': 'test', 'pattern': 'ACG', 'contig': 'chr', 'approx_position': approx,
            'target_locus': 'synthetic', 'target_product': 'synthetic', 'strand': strand}

def check(seq, g, expected, old_hits, monkeypatch, upstream=10):
    monkeypatch.setattr(new, 'TFBS_MOTIFS', {'test': ['ACG']})
    a = new.scan_tfbs({'chr': seq}, [g], upstream_bp=upstream)
    assert [{k: v for k, v in x.items() if k not in NEW_KEYS} for x in a['hits']] == old_hits
    assert [tuple(x[k] for k in NEW_KEYS) for x in a['hits']] == expected
    for x in a['hits']:
        fragment = seq[x['input_sequence_start_1based'] - 1:x['input_sequence_end_1based']]
        if x['motif_orientation_on_input'] == 'reverse_complement':
            fragment = new.reverse_complement(fragment)
        assert fragment == 'ACG'

def test_forward_and_multiple_hits(monkeypatch):
    check('AACGAAAACG' + 'TTTTT', gene(1, 11, 15), [(2, 4, 'forward'), (8, 10, 'forward')], [legacy(2, 1), legacy(8, 1)], monkeypatch)

def test_reverse_and_multiple_hits(monkeypatch):
    check('TTTTT' + 'CGTTTTTCGT', gene(-1, 1, 5), [(13, 15, 'reverse_complement'), (6, 8, 'reverse_complement')], [legacy(6, -1), legacy(13, -1)], monkeypatch)

def test_clipped_forward(monkeypatch):
    check('ACGTTTTTTT', gene(1, 5, 10), [(1, 3, 'forward')], [legacy(1, 1)], monkeypatch)

def test_clipped_reverse(monkeypatch):
    check('TTTTTACGT', gene(-1, 1, 5), [(7, 9, 'reverse_complement')], [legacy(6, -1)], monkeypatch)

def test_unknown_strand_is_explicit(monkeypatch):
    check('AACGTTTTTT', gene(0, 6, 10), [(2, 4, 'forward_assumed_unknown_target_strand')], [legacy(2, 0)], monkeypatch)

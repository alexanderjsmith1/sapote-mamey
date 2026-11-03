"""TFBS upstream scan discloses shortened windows and missing contigs without changing motif calls.

Adapted from Codex Patch Series patch 17's test. The legacy fields are pinned to the pre-patch output."""
from types import SimpleNamespace
from mamey import source_scans as candidate

LEGACY = {'status': 'MOTIF_SCAN_PRELIMINARY', 'upstream_bp': 300, 'counts': {}, 'hits': [], 'total_hits': 0,
          'claim_safety': 'Simple motif scan; replace with calibrated TFBS models/background scoring before manuscript use.'}

def gene(tag, start, end, strand=1, contig='chr'):
    return SimpleNamespace(contig=contig, start=start, end=end, strand=strand, locus_tag=tag, product='synthetic')

def test_clipped_both_strands_and_unknown_sequence_are_disclosed():
    genes = [gene('origin', 1, 20), gene('reverse', 490, 500, -1), gene('interior', 301, 330), gene('missing', 10, 20, contig='missing')]
    got = candidate.scan_tfbs({'chr': 'A' * 500}, genes)
    for key, value in LEGACY.items():
        assert got[key] == value
    assert got['upstream_window_short_count'] == 2 and got['missing_contig_count'] == 1
    assert [(x['target_locus'], x['available_bp']) for x in got['upstream_window_short_examples']] == [('origin', 0), ('reverse', 0)]

def test_custom_window_and_example_cap():
    got = candidate.scan_tfbs({'chr': 'A' * 20}, [gene(str(i), 1, 5) for i in range(1001)], upstream_bp=5)
    assert got['upstream_window_short_count'] == 1001 and len(got['upstream_window_short_examples']) == 1000
    assert got['missing_contig_count'] == 0

def test_existing_workbook_dict_writer_keeps_coverage_summary_and_marks_examples_cap():
    import json
    from openpyxl import Workbook
    from mamey.workbook import _write_dict_sheet
    result = candidate.scan_tfbs({'chr': 'A' * 20}, [gene(str(i), 1, 5) for i in range(1001)], upstream_bp=5)
    restored = json.loads(json.dumps(result))
    wb = Workbook(); _write_dict_sheet(wb, 'TFBS_Motif_Scan', restored); rows = list(wb['TFBS_Motif_Scan'].values)
    assert ('', 'upstream_window_short_count', '1001') in rows
    assert ('upstream_window_short_examples', 'list_count', 1000) in rows
    assert any(r[0] == 'upstream_window_short_examples' and r[1] == 'list_truncated' for r in rows)
    assert any(r[1] == 'coverage_note' and 'not resolved' in r[2] for r in rows)

def test_source_scan_bundle_retains_coverage_in_serialized_result():
    from dataclasses import asdict
    from mamey.models import CDSFeature
    c = CDSFeature('test_contig', 1, 30, 1, 'test_locus', 'synthetic')
    obj = asdict(candidate.run_source_scans([], [c], {'test_contig': 'A' * 1000}, domains=[], organism=''))
    assert obj['tfbs']['upstream_window_short_count'] == 1
    assert obj['tfbs']['upstream_window_short_examples'][0]['available_bp'] == 0
    assert obj['tfbs']['missing_contig_count'] == 0

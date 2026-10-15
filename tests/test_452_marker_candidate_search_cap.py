"""The local 16S plan has no small subject cap and uses alignment-aware identity."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import marker_candidate_search as marker


def test_local_plan_counts_database(monkeypatch, capsys):
    monkeypatch.setattr(marker._p16, 'blastdb_sequence_count', lambda db: 1234)
    marker.main(['plan-blast', '--assembly', 'assembly.fna', '--query', 'Q1', '--markers', '16S', '--db', 'db'])
    text = capsys.readouterr().out
    assert '-max_target_seqs 1234' in text and 'qseq sseq' in text
    assert '-max_target_seqs 25' not in text


def test_unavailable_count_requires_verified_input(monkeypatch, capsys):
    monkeypatch.setattr(marker._p16, 'blastdb_sequence_count', lambda db: None)
    marker.main(['plan-blast', '--assembly', 'assembly.fna', '--query', 'Q1', '--markers', '16S', '--db', 'db'])
    assert '${DB_RECORD_COUNT:?' in capsys.readouterr().out


def test_16s_ranking_and_threshold_use_unambiguous_identity(tmp_path):
    path = tmp_path / 'hits.tsv'
    rows = [['Q1', 'NR_1.1', 99, 100, 1, 0, 1, 100, 1, 100, 0, 200, 'A' * 100, 'C' + 'A' * 99],
            ['Q1', 'NR_2.1', 98, 100, 2, 0, 1, 100, 1, 100, 0, 180, 'NN' + 'A' * 98, 'A' * 100]]
    path.write_text('\n'.join('\t'.join(map(str, row)) for row in rows) + '\n')
    parsed = marker.parse_outfmt6(path)
    got = marker.hits_to_candidates(parsed, 'Q1', '16S', max_hits=1, min_pident=99.5)
    assert got[0]['candidate_id'] == 'NR_2.1'
    assert marker.hits_to_candidates(parsed, 'Q1', 'rpoB', max_hits=1)[0]['candidate_id'] == 'NR_1.1'


def test_short_perfect_hit_cannot_displace_long_16s():
    rows = [dict(qseqid='Q1', sseqid='NR_1.1', pident=98, length=1000, bitscore=1900),
            dict(qseqid='Q1', sseqid='NR_2.1', pident=100, length=30, bitscore=60)]
    assert marker.hits_to_candidates(rows, 'Q1', '16S', max_hits=1)[0]['candidate_id'] == 'NR_1.1'

"""Imported 16S hits retain an explicit identity basis without inventing aligned bases."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import neighbour_panel_candidates as panel


def test_extended_identity_changes_nearest_with_basis(tmp_path):
    p = tmp_path / 'hits.tsv'
    p.write_text('Q1\tNR_1.1\t98\t100\t2\t0\t1\t100\t1\t100\t0\t180\t' +
                 'NN' + 'A' * 98 + '\t' + 'A' * 100 + '\n' +
                 'Q1\tNR_2.1\t99\t100\t1\t0\t1\t100\t1\t100\t0\t200\n')
    basis = {}
    got = panel.read_blast(p, 50, basis)
    assert max(got, key=got.get) == 'NR_1.1'
    assert got['NR_1.1'][0] == 100
    assert basis == {'NR_1.1': 'unambiguous_alignment_columns', 'NR_2.1': 'raw_blast_pident'}

"""Panel ranking must see every candidate, including an ambiguous nearest record beyond 2000."""
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import phylo_16s_panel as panel


def test_panel_sees_last_record_and_corrects_ambiguity(monkeypatch, tmp_path):
    con = sqlite3.connect(':memory:')
    con.executescript('CREATE TABLE record(acc_base, definition, seq, binomial, source, uncultured, designation, genus);'
                      'CREATE TABLE record_strain(acc_base, strain_uid);')
    con.executemany('INSERT INTO record VALUES (?,?,?,?,?,?,?,?)',
                    [(f'NR_{i:06d}', 'Genusa species strain T', 'A' * 1400,
                      'Genusa species', 'refseq_type', 0, str(i), 'Genusa') for i in range(100000, 102001)])
    stage = tmp_path / 'stage'
    stage.mkdir()
    monkeypatch.setattr(panel._p16, 'space_free_workdir', lambda *a: str(stage))
    monkeypatch.setattr(panel._p16, 'blast_bin', lambda name: name)
    calls = []

    def fake(cmd, label):
        calls.append(cmd)
        if cmd[0] == 'makeblastdb':
            return SimpleNamespace(stdout='')
        cap = int(cmd[cmd.index('-max_target_seqs') + 1])
        text = 'Q1\tNR_100000\t99\t600\t' + 'A' * 600 + '\t' + 'C' * 6 + 'A' * 594 + '\n'
        if cap >= 2001:
            text += 'Q1\tNR_102000\t98\t600\t' + 'N' * 12 + 'A' * 588 + '\t' + 'A' * 600 + '\n'
        return SimpleNamespace(stdout=text)

    monkeypatch.setattr(panel._p16, 'run_checked', fake)
    got = panel.rank_references(con, [('Q1', '', 'A' * 600, '')], ('refseq_type',), set(), None)
    assert got[0][0] == 'NR_102000' and got[0][5] == 100
    assert calls[-1][calls[-1].index('-max_target_seqs') + 1] == '2001'

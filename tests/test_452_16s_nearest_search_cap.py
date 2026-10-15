"""All-record genus routing and named reference selection, using fake BLAST executables."""
import json
import os
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import phylo_autopilot as ap
import phylo_refset as refs

CLEAN = 'ACGT' * 25
AMBIG = 'ACNT' + 'ACGT' * 23 + 'ACGN'
TWO_OFF = 'AAGA' + 'ACGT' * 24


@pytest.fixture
def fake(tmp_path, monkeypatch):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    log = tmp_path / 'calls.jsonl'
    config = tmp_path / 'rows.json'
    monkeypatch.setenv('FAKE_LOG', str(log))
    monkeypatch.setenv('FAKE_ROWS', str(config))
    body = '''import json, os, sys
from pathlib import Path
a = sys.argv[1:]
with open(os.environ['FAKE_LOG'], 'a') as f: f.write(json.dumps([Path(sys.argv[0]).name] + a) + '\\n')
if Path(sys.argv[0]).name == 'blastdbcmd':
    if '-info' in a:
        print('Database: synthetic\\n1,234 sequences; 123400 total bases')
    else:
        print('>reference\\nACGT')
else:
    cfg = json.loads(Path(os.environ['FAKE_ROWS']).read_text())
    if cfg.get('fail'): sys.exit(2)
    rows = cfg['rows']
    if '-perc_identity' in a:
        rows = [r for r in rows if r[0] not in cfg.get('missing_with_floor', [])]
    cap = int(a[a.index('-max_target_seqs') + 1])
    fmt = a[a.index('-outfmt') + 1]
    for q in dict.fromkeys(r[0] for r in rows):
        for r in [r for r in rows if r[0] == q][:cap]:
            qid, acc, title, pid, length, qs, ss = r
            vals = [qid, title, pid, length] if 'stitle pident' in fmt else [qid, acc, pid, length, title]
            if 'qseq sseq' in fmt: vals += [qs, ss]
            print('\\t'.join(map(str, vals)))
'''
    for name in ['blastn', 'blastdbcmd']:
        p = bin_dir / name
        p.write_text('#!' + sys.executable + '\n' + body)
        p.chmod(0o755)
    monkeypatch.setattr(refs, 'BLAST_BIN', str(bin_dir))
    query = tmp_path / 'q.fasta'
    query.write_text('>Q1\n' + CLEAN + '\n>Q2\n' + CLEAN + '\n')

    def run(rows, which='assign', **cfg):
        config.write_text(json.dumps(dict(rows=rows, **cfg)))
        if which == 'assign':
            return ap.assign_genus(str(query), 'synthetic_db', blastn=str(bin_dir / 'blastn'))
        return refs.marker_blast(str(query), top=1, db='synthetic_db', verbose=False)

    def calls():
        return [r for r in map(json.loads, log.read_text().splitlines()) if r[0] == 'blastn']
    return run, calls


def row(acc, genus='Genusa', pid=98, qs=CLEAN, ss=TWO_OFF, qid='Q1'):
    return [qid, acc, genus + ' species strain T 16S', pid, 100, qs, ss]


def test_all_records_reveal_closer_second_genus_beyond_old_cap(fake):
    run, calls = fake
    rows = [row('NR_' + str(i)) for i in range(5)] + [row('NR_6', 'Genusb', 100, ss=CLEAN)]
    got = run(rows)
    assert got['Q1']['genus'] == 'Genusb'
    assert all(c[c.index('-max_target_seqs') + 1] == '1234' for c in calls())


def test_different_genus_near_tie_beyond_old_cap_is_held(fake):
    run, _ = fake
    rows = [row('NR_' + str(i), pid=100, ss=CLEAN) for i in range(5)]
    rows += [row('NR_6', 'Genusb', 100, ss=CLEAN)]
    assert run(rows)['Q1']['routing_state'] == 'GENUS_CONFLICT'


def test_ambiguous_calls_do_not_create_false_conflict(fake):
    run, _ = fake
    got = run([row('NR_1', qs=AMBIG, ss=CLEAN), row('NR_2', 'Genusb')])['Q1']
    assert got['pident'] == 100
    assert got['pident_raw'] == 98
    assert got['routing_state'] == 'TOP_HIT_ONLY'


def test_refset_ranks_unambiguous_identity_over_all_records(fake):
    run, calls = fake
    rows = [row('NR_' + str(i)) for i in range(5)] + [row('NR_6', 'Genusb', 98, AMBIG, CLEAN)]
    got = run(rows, which='refs')
    assert len(got) == 1 and got[0][0].endswith('_NR_6')
    assert all(c[c.index('-max_target_seqs') + 1] == '1234' for c in calls())


@pytest.mark.parametrize('which', ['assign', 'refs'])
def test_floor_fallback_is_per_query(fake, which):
    run, calls = fake
    got = run([row('NR_1'), row('NR_2', qid='Q2')], which=which, missing_with_floor=['Q2'])
    assert len(got) == 2
    assert len(calls()) == 2
    assert '-perc_identity' in calls()[0] and '-perc_identity' not in calls()[1]


@pytest.mark.parametrize('which', ['assign', 'refs'])
def test_blast_failure_is_not_no_hit(fake, which):
    run, _ = fake
    with pytest.raises((RuntimeError, SystemExit)):
        run([], which=which, fail=True)


def test_record_count_failure_uses_shared_fallback(fake, monkeypatch):
    run, calls = fake
    monkeypatch.setattr(ap._p16, 'blastdb_sequence_count', lambda *a: None)
    run([row('NR_1')])
    assert calls()[0][calls()[0].index('-max_target_seqs') + 1] == str(ap._p16.ALL_RECORDS_FALLBACK)


@pytest.mark.parametrize('which', ['assign', 'refs'])
def test_short_perfect_fragment_cannot_displace_long_alignment(fake, which):
    run, _ = fake
    fragment = row('NR_2', 'Genusb', 100, 'A' * 30, 'A' * 30)
    fragment[4] = 30
    got = run([row('NR_1'), fragment], which=which)
    if which == 'assign':
        assert got['Q1']['genus'] == 'Genusa'
    else:
        assert got[0][0].endswith('_NR_1')

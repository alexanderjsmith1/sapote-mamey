"""Failing-baseline/passing-candidate reference readiness admission regression."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys

import pytest

SRC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SRC), str(SRC / 'tools')]
TOOL = Path(os.environ.get('W3_FETCH_TOOL', SRC / 'tools/fetch_reference_cluster.py'))


@pytest.fixture
def fetch():
    spec = importlib.util.spec_from_file_location('w3_test_fetch', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def database(path, seqs):
    with sqlite3.connect(path) as c:
        c.executescript('CREATE TABLE gbk(id INT, path TEXT);'
                       'CREATE TABLE cds(id INT, gbk_id INT, nt_start INT, nt_stop INT, '
                       'strand INT, aa_seq TEXT, orf_num INT);'
                       'CREATE TABLE hsp(cds_id INT, accession TEXT, bit_score REAL);')
        # Synthetic full identity: XS-001 / NODE_1_length_120_cov_1 / region001 / BGC001.
        c.execute('INSERT INTO gbk VALUES(1,?)', ('/fixture/XS-001_NODE_1_length_120_cov_1.region001.gbk',))
        for i, aa in enumerate(seqs, 1):
            c.execute('INSERT INTO cds VALUES(?,?,?,?,?,?,?)', (i, 1, 30*i, 30*(i+1), 1, aa, i))


@pytest.mark.parametrize('seqs', [[None], [''], [' '], ['MMMMMMMMMM', None], ['MMMMMMMMMM', '']])
def test_main_refuses_empty_translation_without_publishing(fetch, tmp_path, capsys, seqs):
    db, out = tmp_path / 'fixture.db', tmp_path / 'out'
    database(db, seqs)
    before = db.read_bytes()
    assert fetch.main(['--db', str(db), '--acc', 'region001:ref', '--outdir', str(out)]) == 2
    assert not out.exists() or not list(out.iterdir())
    assert db.read_bytes() == before
    message = capsys.readouterr()
    assert 'no translated protein' in message.err
    assert 'ready for' not in message.out


def test_ordinary_output_is_usable_by_documented_downstream(fetch, tmp_path):
    db, out = tmp_path / 'fixture.db', tmp_path / 'out'
    database(db, ['MMMMMMMMMM', 'MTMTMTMTMT'])
    assert fetch.main(['--db', str(db), '--acc', 'region001:ref', '--outdir', str(out)]) == 0
    from cluster_gene_compare import compare
    compare(['first', 'second'], [out / 'ref.gbk', out / 'ref.gbk'])
    receipt = json.loads((out / 'ref.reference_selection.json').read_text())
    assert receipt['references'][0]['cds_count'] == 2


def test_valid_prior_output_set_is_preserved_after_changed_source_is_unready(fetch, tmp_path):
    db, out = tmp_path / 'fixture.db', tmp_path / 'out'
    database(db, ['MMMMMMMMMM'])
    args = ['--db', str(db), '--acc', 'region001:ref', '--outdir', str(out)]
    assert fetch.main(args) == 0
    prior = {p.name: p.read_bytes() for p in out.iterdir()}
    with sqlite3.connect(db) as c:
        c.execute('UPDATE cds SET aa_seq=NULL')
    assert fetch.main(args) == 2
    assert {p.name: p.read_bytes() for p in out.iterdir()} == prior


@pytest.mark.parametrize('protein', ['M?M', 'MUM', 'MOM', 'MJM', 'mMm'])
def test_symbols_unsupported_by_actual_downstream_matrix_refused(fetch, tmp_path, capsys, protein):
    db, out = tmp_path / 'fixture.db', tmp_path / 'out'
    database(db, [protein])
    assert fetch.main(['--db', str(db), '--acc', 'region001:ref', '--outdir', str(out)]) == 2
    assert not out.exists() or not list(out.iterdir())
    assert 'BLOSUM62 comparison matrix' in capsys.readouterr().err


@pytest.mark.parametrize('protein', ['MBZM', 'MXXM', 'M*M', 'M M M'])
def test_matrix_supported_and_transport_whitespace_sequences_still_work(fetch, tmp_path, protein):
    db, out = tmp_path / 'fixture.db', tmp_path / 'out'
    database(db, [protein])
    assert fetch.main(['--db', str(db), '--acc', 'region001:ref', '--outdir', str(out)]) == 0
    from cluster_gene_compare import compare
    compare(['first', 'second'], [out / 'ref.gbk', out / 'ref.gbk'])


def test_late_invalid_reference_preserves_prior_unrelated_output(fetch, tmp_path, capsys):
    db, out = tmp_path / 'fixture.db', tmp_path / 'out'
    database(db, ['MMMMMMMMMM'])
    with sqlite3.connect(db) as c:
        c.execute('INSERT INTO gbk VALUES(2,?)', ('/fixture/XS-001_NODE_2_length_120_cov_1.region001.gbk',))
        c.execute('INSERT INTO cds VALUES(2,2,1,30,1,?,1)', ('M?M',))
    out.mkdir()
    (out / 'unrelated.txt').write_text('preserve existing evidence')
    assert fetch.main(['--db', str(db), '--acc', 'NODE_1:valid', '--acc', 'NODE_2:bad', '--outdir', str(out)]) == 2
    assert sorted(p.name for p in out.iterdir()) == ['unrelated.txt']
    assert (out / 'unrelated.txt').read_text() == 'preserve existing evidence'
    assert 'ready for' not in capsys.readouterr().out


def test_malformed_translation_transport_refused_before_publication(fetch, tmp_path):
    db, out = tmp_path / 'fixture.db', tmp_path / 'out'
    database(db, ['M M\nM'])
    assert fetch.main(['--db', str(db), '--acc', 'region001:ref', '--outdir', str(out)]) == 2
    assert not out.exists() or not list(out.iterdir())

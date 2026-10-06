"""Synthetic reference-selection/publication regressions; no live NCBI calls."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(os.environ.get('SAPOTE_REFERENCE_TEST_ROOT', Path(__file__).resolve().parents[1]))


def load(name):
    sys.path.insert(0, str(ROOT / 'tools'))
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tools():
    fetch = load('fetch_reference_cluster')
    return fetch, load('bgc_reference_align')


def record(i):
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    # XS-001 / NODE_i_length_120_cov_1 / region001 / BGC00i (synthetic identities only).
    r = SeqRecord(Seq('N' * 120), id=f'XS-001_NODE_{i}_length_120_cov_1.region001')
    r.annotations['molecule_type'] = 'DNA'
    r.features = [SeqFeature(FeatureLocation(1, 90, strand=1), type='CDS',
                            qualifiers={'locus_tag': [f'ctg{i}_1'],
                                        'translation': ['MKTAYIAKQRQISFVKSHFSRQ']})]
    return r


def gbk(path, count=1):
    from Bio import SeqIO
    SeqIO.write([record(i + 1) for i in range(count)], path, 'genbank')


def db(path):
    with sqlite3.connect(path) as c:
        c.executescript('CREATE TABLE gbk(id INT, path TEXT);'
                       'CREATE TABLE cds(id INT, gbk_id INT, nt_start INT, nt_stop INT,'
                       'strand INT, aa_seq TEXT, orf_num INT);'
                       'CREATE TABLE hsp(cds_id INT, accession TEXT, bit_score REAL);')
        for i in (1, 2):
            c.execute('INSERT INTO gbk VALUES(?,?)',
                      (i, f'/fixture/XS-001_NODE_{i}_length_120_cov_1.region001.gbk'))
            c.execute('INSERT INTO cds VALUES(?,?,?,?,?,?,?)',
                      (i, i, 1, 90, 1, 'MKTAYIAKQRQISFVKSHFSRQ', 1))


def args(dbpath, out):
    return ['--db', str(dbpath), '--acc', 'NODE_1:first', '--acc', 'NODE_2:second',
            '--outdir', str(out)]


@pytest.mark.parametrize('field,value', [('--bgc', '../escape'), ('--strain', '../escape')])
def test_align_refuses_unsafe_output_tags(tmp_path, tools, monkeypatch, field, value):
    _, align = tools
    query, ref, out = tmp_path / 'q.gbk', tmp_path / 'r.gbk', tmp_path / 'out'
    gbk(query); gbk(ref)
    monkeypatch.setattr(sys, 'argv', ['align', '--gbk', str(query), '--ref-gbk', f'{ref}:ref',
                                    field, value, '--outdir', str(out)])
    with pytest.raises(SystemExit):
        align.main()
    assert not out.exists()


@pytest.mark.parametrize('multi_query', [False, True])
def test_align_refuses_local_multiple_records(tmp_path, tools, monkeypatch, multi_query):
    _, align = tools
    query, ref, out = tmp_path / 'q.gbk', tmp_path / 'r.gbk', tmp_path / 'out'
    gbk(query, count=2 if multi_query else 1)
    gbk(ref, count=1 if multi_query else 2)
    monkeypatch.setattr(sys, 'argv', ['align', '--gbk', str(query), '--ref-gbk', f'{ref}:ref',
                                    '--outdir', str(out)])
    with pytest.raises(SystemExit, match='exactly one GenBank record'):
        align.main()
    assert not out.exists()


def test_fetch_refuses_multiple_fetched_records(tmp_path, tools, monkeypatch, capsys):
    fetch, _ = tools
    source, out = tmp_path / 'multi.gbk', tmp_path / 'out'
    gbk(source, count=2)
    monkeypatch.setattr(fetch.urllib.request, 'urlopen', lambda *a, **k: io.BytesIO(source.read_bytes()))
    assert fetch.main(['--ncbi', 'AA123456.1:ref', '--outdir', str(out)]) == 2
    assert not out.exists()
    assert 'exactly one fetched GenBank record, got 2' in capsys.readouterr().err


@pytest.mark.parametrize('blocked', ['first.gbk', 'second.reference_selection.json'])
def test_fetch_preflights_every_destination_before_writing(tmp_path, tools, blocked):
    fetch, _ = tools
    database, out = tmp_path / 'fixture.db', tmp_path / 'out'
    db(database); out.mkdir(); (out / blocked).mkdir()
    assert fetch.main(args(database, out)) == 2
    assert sorted(p.name for p in out.iterdir()) == [blocked]


def test_fetch_failed_staging_keeps_prior_set_intact(tmp_path, tools, monkeypatch):
    fetch, _ = tools
    database, out = tmp_path / 'fixture.db', tmp_path / 'out'
    db(database)
    original = fetch.write_selection_receipt
    count = 0
    def fail_second(*a, **k):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError('synthetic receipt failure')
        return original(*a, **k)
    monkeypatch.setattr(fetch, 'write_selection_receipt', fail_second)
    assert fetch.main(args(database, out)) == 2
    assert not out.exists() or not list(out.iterdir())


def test_fetch_refuses_overwrite_of_existing_output_and_receipt(tmp_path, tools):
    fetch, _ = tools
    database, out = tmp_path / 'fixture.db', tmp_path / 'out'
    db(database)
    assert fetch.main(args(database, out)) == 0
    original = {p.name: p.read_bytes() for p in out.iterdir()}
    with sqlite3.connect(database) as c:
        c.execute("UPDATE cds SET aa_seq='MMMMMMMMMMMMMMMMMMMM' WHERE gbk_id=1")
    assert fetch.main(args(database, out)) == 2
    assert {p.name: p.read_bytes() for p in out.iterdir()} == original


def test_fetch_rejects_symlink_destination(tmp_path, tools):
    fetch, _ = tools
    database, out, external = tmp_path / 'fixture.db', tmp_path / 'out', tmp_path / 'precious.gbk'
    db(database); out.mkdir(); external.write_text('preserve')
    (out / 'first.gbk').symlink_to(external)
    assert fetch.main(args(database, out)) == 2
    assert external.read_text() == 'preserve'
    assert not (out / 'second.gbk').exists()


def test_fetch_publish_failure_rolls_back_links(tmp_path, tools, monkeypatch):
    fetch, _ = tools
    database, out = tmp_path / 'fixture.db', tmp_path / 'out'
    db(database)
    original = fetch.os.link
    count = 0
    def fail_second(*a, **k):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError('synthetic publication failure')
        return original(*a, **k)
    monkeypatch.setattr(fetch.os, 'link', fail_second)
    assert fetch.main(args(database, out)) == 2
    assert not out.exists() or not list(out.iterdir())


def test_success_receipts_bind_published_not_staging_paths(tmp_path, tools):
    fetch, _ = tools
    database, out = tmp_path / 'fixture.db', tmp_path / 'out'
    db(database)
    assert fetch.main(args(database, out)) == 0
    for label in ('first', 'second'):
        receipt = json.loads((out / f'{label}.reference_selection.json').read_text())
        binding = receipt['outputs'][0]
        artifact = out / f'{label}.gbk'
        assert binding['path'] == str(artifact.resolve())
        assert binding['sha256'] == hashlib.sha256(artifact.read_bytes()).hexdigest()


def test_align_receipt_failure_leaves_no_published_outputs(tmp_path, tools, monkeypatch, capsys):
    _, align = tools
    query, ref, out = tmp_path / 'q.gbk', tmp_path / 'r.gbk', tmp_path / 'out'
    gbk(query); gbk(ref)
    def fail(*a, **k):
        raise OSError('synthetic receipt failure')
    monkeypatch.setattr(align, 'write_selection_receipt', fail)
    monkeypatch.setattr(sys, 'argv', ['align', '--gbk', str(query), '--ref-gbk', f'{ref}:ref',
                                    '--outdir', str(out)])
    with pytest.raises(SystemExit):
        align.main()
    assert not out.exists() or not list(out.iterdir())
    assert 'CONFIDENT orthologs' not in capsys.readouterr().out


def test_align_existing_receipt_is_never_overwritten(tmp_path, tools, monkeypatch):
    _, align = tools
    query, ref, out = tmp_path / 'q.gbk', tmp_path / 'r.gbk', tmp_path / 'out'
    gbk(query); gbk(ref); out.mkdir()
    receipt = out / 'BGC_reference_selection.json'
    receipt.write_text('original receipt')
    monkeypatch.setattr(sys, 'argv', ['align', '--gbk', str(query), '--ref-gbk', f'{ref}:ref',
                                    '--outdir', str(out)])
    with pytest.raises(SystemExit):
        align.main()
    assert receipt.read_text() == 'original receipt'
    assert list(out.iterdir()) == [receipt]

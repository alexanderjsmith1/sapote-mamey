"""Actual DB/CLI regression for canonical SQLite source and WAL receipt binding."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

import pytest

SRC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SRC), str(SRC / 'tools')]


def load(name, variable):
    path = Path(os.environ.get(variable, SRC / 'tools' / f'{name}.py'))
    spec = importlib.util.spec_from_file_location(name + '_wal_audit', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('alias_kind', ['absolute_symlink', 'relative_symlink', 'canonical'])
@pytest.mark.parametrize('tool', ['fetch_reference_cluster', 'bgc_reference_align'])
def test_receipt_binds_wal_used_by_resolved_database(tmp_path, alias_kind, tool):
    module = load(tool, 'W3_FETCH_TOOL' if tool == 'fetch_reference_cluster' else 'W3_ALIGN_TOOL')
    actual = tmp_path / 'real.db'
    writer = sqlite3.connect(actual)
    try:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.executescript('CREATE TABLE gbk(id INT, path TEXT);'
                            'CREATE TABLE cds(id INT, gbk_id INT, nt_start INT, nt_stop INT, '
                            'strand INT, aa_seq TEXT, orf_num INT);'
                            'CREATE TABLE hsp(cds_id INT, accession TEXT, bit_score REAL);')
        writer.execute('INSERT INTO gbk VALUES(1,?)', ('/fixture/XS-001_NODE_1_length_120_cov_1.region001.gbk',))
        writer.execute('INSERT INTO cds VALUES(1,1,1,30,1,?,1)', ('MMMMMMMMMM',))
        writer.commit()
        wal = Path(str(actual) + '-wal')
        assert wal.exists()
        baseline_db, baseline_wal = actual.read_bytes(), wal.read_bytes()
        selected = actual
        if alias_kind != 'canonical':
            selected = tmp_path / 'alias.db'
            selected.symlink_to(actual if alias_kind == 'absolute_symlink' else actual.name)
        bound = {}
        if tool == 'fetch_reference_cluster':
            out = tmp_path / 'out'
            assert module.main(['--db', str(selected), '--acc', 'region001:ref', '--outdir', str(out)]) == 0
            bound = json.loads((out / 'ref.reference_selection.json').read_text())['references'][0]
        else:
            assert module.ref_from_db(str(selected), 'region001', provenance=bound)
        assert bound['database']['path'] == str(actual.resolve())
        assert bound['database_wal']['path'] == str(wal.resolve())
        assert bound['database_wal']['sha256'] == hashlib.sha256(baseline_wal).hexdigest()
        assert actual.read_bytes() == baseline_db and wal.read_bytes() == baseline_wal
        # A base-only replay lacks the selected committed state; the WAL is material.
        replay = tmp_path / 'base_only.db'
        replay.write_bytes(baseline_db)
        with sqlite3.connect(replay) as c:
            with pytest.raises(sqlite3.OperationalError, match='no such table'):
                c.execute('SELECT path FROM gbk').fetchall()
    finally:
        writer.close()

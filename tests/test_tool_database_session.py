import hashlib
import json
import sqlite3
import pytest
from mamey.tool_database_session import FrozenDatabaseSession
from tests.test_tool_database_reader import fixture_db,blastp_fixture,ID

def session(root,**kw):
    return FrozenDatabaseSession(root,'RELEASE_MANIFEST.json',expected_manifest_sha256=hashlib.sha256((root/'RELEASE_MANIFEST.json').read_bytes()).hexdigest(),**kw)

def test_pages_readonly_exception_close(tmp_path):
    fixture_db(tmp_path,rows=1002)
    s=session(tmp_path,adapter='gene-census-v1')
    with pytest.raises(RuntimeError):
        with s:
            assert len(list(s.iter_rows('SELECT * FROM gene ORDER BY gene_order')))==1002
            with pytest.raises(ValueError,match='BUDGET'):s.rows('SELECT * FROM gene')
            for sql in ['DELETE FROM gene','SELECT 1; DELETE FROM gene']:
                with pytest.raises(ValueError,match='SELECT'):s.rows(sql)
            raise RuntimeError('caller failure')
    assert s._c is None

@pytest.mark.parametrize('adapter',['blastp-nr-v1','blastp-clustered-nr-v1','blastp-swissprot-v2'])
def test_bound_history_and_counterevidence(tmp_path,adapter):
    evidence=blastp_fixture(tmp_path,adapter)
    with session(tmp_path,adapter=adapter) as s:
        r=s.inspect(ID,gene_order=0,view='searches')
        assert len(r['records'])==(1 if 'swiss' in adapter else 2)
        raw,total=s.hit_evidence(ID,0,1)
        assert total==1 and raw==[evidence]
        with pytest.raises(ValueError):s.hit_evidence((*ID[:1],'wrong_contig',*ID[2:]),0,1)
        if 'swiss' in adapter:assert s.hit_evidence(ID,1,1)==([],0)
        else:
            with pytest.raises(ValueError):s.hit_evidence(ID,1,1)
        assert s.inspect(ID,gene_order=2)['records'][0]['availability_state']=='NO_VERIFIED_SEARCH'
        assert s.inspect(ID,gene_order=3)['records'][0]['availability_state']=='MISSING_OR_UNBOUND_PROTEIN_HOLD'

def test_changed_dependency_and_manifest(tmp_path):
    fixture_db(tmp_path);dep=tmp_path/'dependency.txt';dep.write_text('original')
    s=session(tmp_path,dependencies=[{'root':str(tmp_path),'path':dep.name,'sha256':hashlib.sha256(dep.read_bytes()).hexdigest()}])
    with pytest.raises(ValueError,match='CHANGED'):
        with s:
            dep.write_text('changed');s.rows('SELECT * FROM gene')
    assert s._c is None
    s=session(tmp_path);(tmp_path/'RELEASE_MANIFEST.json').write_text('{}')
    with pytest.raises(ValueError,match='MANIFEST_HASH'):s.__enter__()
    assert s._c is None

def test_tamper_sidecars_and_fk(tmp_path):
    fixture_db(tmp_path);s=session(tmp_path)
    with (tmp_path/'evidence.sqlite').open('ab') as f:f.write(b'x')
    with pytest.raises(ValueError,match='SIZE'):s.__enter__()

def test_live_sidecar_refused(tmp_path):
    fixture_db(tmp_path);(tmp_path/'evidence.sqlite-wal').write_bytes(b'')
    with pytest.raises(ValueError,match='LIVE'):session(tmp_path).__enter__()

def test_foreign_key_failure(tmp_path):
    fixture_db(tmp_path);db=tmp_path/'evidence.sqlite';c=sqlite3.connect(db)
    c.executescript('CREATE TABLE parent(id INTEGER PRIMARY KEY); CREATE TABLE child(p INTEGER REFERENCES parent); INSERT INTO child VALUES(7);');c.close()
    from tests.test_tool_database_reader import update_manifest
    update_manifest(tmp_path)
    with pytest.raises(ValueError,match='FOREIGN_KEY'):session(tmp_path).__enter__()

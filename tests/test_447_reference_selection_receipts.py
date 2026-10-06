"""Synthetic R06/D15 regressions: no partial selection and durable source/output bindings."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def database(path):
    with sqlite3.connect(path) as c:
        c.executescript('CREATE TABLE gbk(id INTEGER PRIMARY KEY, path TEXT);'
                       'CREATE TABLE cds(id INTEGER PRIMARY KEY, gbk_id INT, nt_start INT, nt_stop INT,'
                       'strand INT, aa_seq TEXT, orf_num INT);'
                       'CREATE TABLE hsp(cds_id INT, accession TEXT, bit_score REAL);')
        # Full synthetic locus identity: XS-001 / NODE_1_length_120_cov_1 / region001 / BGC001.
        c.execute('INSERT INTO gbk VALUES(7,?)', ('/fixture/XS-001_NODE_1_length_120_cov_1.region001.gbk',))
        c.execute("INSERT INTO cds VALUES(1,7,1,90,1,'MKTAYIAKQRQISFVKSHFSRQ',1)")


def gbk(path, translated=True, record_id='XS-001_NODE_1_length_120_cov_1.region001'):
    pytest.importorskip('Bio')
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    rec = SeqRecord(Seq('N' * 120), id=record_id)
    rec.annotations['molecule_type'] = 'DNA'
    if translated:
        rec.features = [SeqFeature(FeatureLocation(1, 90, strand=1), type='CDS',
                                  qualifiers={'locus_tag': ['ctg1_1'], 'translation': ['MKTAYIAKQRQISFVKSHFSRQ']})]
    SeqIO.write(rec, path, 'genbank')


@pytest.mark.parametrize('tool', ['fetch_reference_cluster', 'bgc_reference_align'])
def test_missing_selection_raises(tmp_path, tool):
    db = tmp_path / 'd.db'
    database(db)
    m = load(tool)
    args = (str(db), 'missing', 'none') if tool == 'fetch_reference_cluster' else (str(db), 'missing')
    with pytest.raises(KeyError, match='not found'):
        m.ref_from_db(*args)


def test_fetch_resolves_all_before_writing(tmp_path, capsys):
    db, out = tmp_path / 'd.db', tmp_path / 'out'
    database(db)
    m = load('fetch_reference_cluster')
    assert m.main(['--db', str(db), '--acc', 'region001:present', '--acc', 'missing:absent',
                   '--outdir', str(out)]) == 2
    assert 'not found' in capsys.readouterr().err
    assert not list(out.glob('*'))


def assert_binding(binding, path):
    assert binding['path'] == str(path.resolve())
    assert binding['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_fetch_receipt_binds_db_selected_row_and_output(tmp_path):
    pytest.importorskip('Bio')
    db, out = tmp_path / 'd.db', tmp_path / 'out'
    database(db)
    assert load('fetch_reference_cluster').main(['--db', str(db), '--acc', 'region001:present',
                                                '--outdir', str(out)]) == 0
    receipt = json.loads((out / 'present.reference_selection.json').read_text())
    ref = receipt['references'][0]
    assert ref['selected_id'] == 7
    assert ref['selected_source_path'].endswith('region001.gbk')
    assert_binding(ref['database'], db)
    assert_binding(receipt['outputs'][0], out / 'present.gbk')


@pytest.mark.parametrize('empty_local', [False, True])
def test_align_refuses_missing_or_empty_member_without_outputs(tmp_path, monkeypatch, empty_local):
    db, query, out = tmp_path / 'd.db', tmp_path / 'query.gbk', tmp_path / 'out'
    database(db)
    gbk(query)
    args = ['bgc_reference_align', '--gbk', str(query), '--db', str(db), '--ref-db', 'region001:present',
            '--outdir', str(out)]
    if empty_local:
        empty = tmp_path / 'empty.gbk'
        gbk(empty, translated=False)
        args.extend(['--ref-gbk', f'{empty}:empty'])
    else:
        args.extend(['--ref-db', 'missing:absent'])
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(SystemExit, match='reference selection failed'):
        load('bgc_reference_align').main()
    assert not out.exists()


def test_align_receipt_binds_query_db_and_all_outputs(tmp_path, monkeypatch):
    pytest.importorskip('matplotlib')
    pytest.importorskip('PIL')
    db, query, out = tmp_path / 'd.db', tmp_path / 'query.gbk', tmp_path / 'out'
    database(db)
    gbk(query)
    monkeypatch.setattr(sys, 'argv', ['bgc_reference_align', '--gbk', str(query), '--strain', 'XS-001',
                                     '--bgc', 'BGC001', '--db', str(db), '--ref-db', 'region001:present',
                                     '--outdir', str(out)])
    load('bgc_reference_align').main()
    receipt = json.loads((out / 'XS-001_BGC001_reference_selection.json').read_text())
    assert_binding(receipt['query'], query)
    assert_binding(receipt['references'][0]['database'], db)
    assert receipt['references'][0]['selected_id'] == 7
    assert len(receipt['outputs']) == 2
    for binding in receipt['outputs']:
        assert_binding(binding, Path(binding['path']))


@pytest.mark.parametrize('tool', ['fetch_reference_cluster', 'bgc_reference_align'])
def test_mocked_ncbi_response_is_bound_without_network(tmp_path, monkeypatch, tool):
    from io import BytesIO
    source = tmp_path / 'fixture.gbk'
    gbk(source, record_id='AA123456.1')
    payload = source.read_bytes()
    module = load(tool)
    monkeypatch.setattr(module.urllib.request, 'urlopen', lambda *args, **kwargs: BytesIO(payload))
    provenance = {}
    if tool == 'fetch_reference_cluster':
        genes = module.ref_from_ncbi('AA123456.1', 'fixture', provenance=provenance)
    else:
        genes = module.ref_from_ncbi('AA123456.1', provenance=provenance)
        assert genes[0]['tag'] == 'ctg1_1'  # preserve local/source locus tags in the aligner
    assert genes
    assert provenance['requested_selector'] == 'AA123456.1'
    assert provenance['response_sha256'] == hashlib.sha256(payload).hexdigest()
    assert provenance['selected_record_ids'] == ['AA123456.1']


@pytest.mark.parametrize('tool', ['fetch_reference_cluster', 'bgc_reference_align'])
def test_selected_db_row_without_cds_is_refused(tmp_path, tool):
    db = tmp_path / 'd.db'
    database(db)
    with sqlite3.connect(db) as c:
        c.execute('DELETE FROM cds')
    module = load(tool)
    args = (str(db), 'region001', 'fixture') if tool == 'fetch_reference_cluster' else (str(db), 'region001')
    with pytest.raises(ValueError, match='no CDS'):
        module.ref_from_db(*args)


def test_missing_db_is_not_created(tmp_path):
    db = tmp_path / 'missing.db'
    assert load('fetch_reference_cluster').main(['--db', str(db), '--acc', 'region001:fixture',
                                                '--outdir', str(tmp_path / 'out')]) == 2
    assert not db.exists()


def test_duplicate_output_labels_are_refused_before_writes(tmp_path):
    db, out = tmp_path / 'd.db', tmp_path / 'out'
    database(db)
    assert load('fetch_reference_cluster').main(['--db', str(db), '--acc', 'region001:fixture',
                                                '--acc', 'region001:fixture', '--outdir', str(out)]) == 2
    assert not list(out.glob('*'))


def test_align_refuses_multi_record_ncbi_response_before_outputs(tmp_path, monkeypatch):
    """A receipt must not claim selection of records whose proteins were not consumed."""
    from io import BytesIO, StringIO
    from Bio import SeqIO
    query, first, out = tmp_path / 'query.gbk', tmp_path / 'first.gbk', tmp_path / 'out'
    gbk(query)
    gbk(first)
    records = list(SeqIO.parse(first, 'genbank'))
    second = records[0][:]
    # Full synthetic identity: XS-001 / NODE_2_length_120_cov_1 / region001 / BGC002.
    second.id = 'XS-001_NODE_2_length_120_cov_1.region001'
    second.name = 'SYNTHETIC_SECOND'
    records.append(second)
    response = StringIO()
    SeqIO.write(records, response, 'genbank')
    payload = response.getvalue().encode()
    module = load('bgc_reference_align')
    monkeypatch.setattr(module.urllib.request, 'urlopen', lambda *args, **kwargs: BytesIO(payload))
    monkeypatch.setattr(sys, 'argv', ['bgc_reference_align', '--gbk', str(query),
                                     '--ref-ncbi', 'AA123456.1:fixture', '--outdir', str(out)])
    with pytest.raises(SystemExit, match='exactly one fetched GenBank record, got 2'):
        module.main()
    assert not out.exists()

"""Exact versioned accession compatibility, using synthetic records and no network."""
import hashlib
import importlib.util
import io
from pathlib import Path
import sqlite3
import sys
import urllib.parse

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def retrieval_tools():
    sys.path.insert(0, str(ROOT / 'tools'))
    modules = []
    for name in ('fetch_reference_cluster', 'bgc_reference_align'):
        spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    assert modules[1].validate_ncbi_accession is modules[0].validate_ncbi_accession
    return modules


def payload(accession):
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation, SeqFeature
    from Bio.SeqRecord import SeqRecord
    record = SeqRecord(Seq('N' * 90), id=accession)
    record.annotations['molecule_type'] = 'DNA'
    record.features = [SeqFeature(FeatureLocation(0, 60, strand=1), type='CDS',
                                   qualifiers={'locus_tag': ['synthetic_1'],
                                               'translation': ['MMMMMMMMMMMMMMMMMMMM']})]
    text = io.StringIO()
    SeqIO.write(record, text, 'genbank')
    return text.getvalue().encode()


def retrieve(module, accession, provenance=None):
    if module.__name__ == 'fetch_reference_cluster':
        return module.ref_from_ncbi(accession, 'synthetic', provenance=provenance)
    return module.ref_from_ncbi(accession, provenance=provenance)


@pytest.mark.parametrize('accession', ['AA123456.1', 'NC_123456.2', 'NZ_CP123456.1',
                                      'NZ_AAAA01000001.2'])
@pytest.mark.parametrize('tool', [0, 1])
def test_exact_versioned_records_admitted_and_bound(retrieval_tools, monkeypatch, accession, tool):
    module = retrieval_tools[tool]
    source = payload(accession)
    calls = []
    def mock_fetch(url, **kwargs):
        calls.append(urllib.parse.parse_qs(urllib.parse.urlparse(url).query))
        return io.BytesIO(source)
    monkeypatch.setattr(module.urllib.request, 'urlopen', mock_fetch)
    provenance = {}
    assert retrieve(module, accession, provenance)
    assert calls == [{'db': ['nucleotide'], 'id': [accession], 'rettype': ['gb'], 'retmode': ['text']}]
    assert provenance['requested_selector'] == accession
    assert provenance['selected_record_ids'] == [accession]
    assert provenance['response_sha256'] == hashlib.sha256(source).hexdigest()


@pytest.mark.parametrize('accession', [None, '', 'NZ_CP123456', 'AA123456', 'NZ_CP123456.',
                                      'NZ_CP123456.1.2', 'NZ_CP123456.1 ', ' nz_CP123456.1',
                                      'NZ_CP123456.1/region', '../NZ_CP123456.1',
                                      'NZ_CP123456.1%', 'NZ_CP123456.1?x=2',
                                      'NZ__CP123456.1', 'NZ_CP1234.1'])
@pytest.mark.parametrize('tool', [0, 1])
def test_invalid_selectors_refuse_before_fetch(retrieval_tools, monkeypatch, accession, tool):
    def forbidden(*args, **kwargs):
        pytest.fail('Invalid accession reached external retrieval')
    monkeypatch.setattr(retrieval_tools[tool].urllib.request, 'urlopen', forbidden)
    with pytest.raises(ValueError, match='complete versioned accession'):
        retrieve(retrieval_tools[tool], accession)


@pytest.mark.parametrize('response_id', ['NZ_CP123456.2', 'NZ_CP1234567.1', 'AA123456.1'])
@pytest.mark.parametrize('tool', [0, 1])
def test_accepted_syntax_does_not_relax_fetched_identity(retrieval_tools, monkeypatch, response_id, tool):
    module = retrieval_tools[tool]
    monkeypatch.setattr(module.urllib.request, 'urlopen', lambda *a, **k: io.BytesIO(payload(response_id)))
    provenance = {}
    with pytest.raises(ValueError, match='identity mismatch'):
        retrieve(module, 'NZ_CP123456.1', provenance)
    assert provenance == {}


def test_nz_database_selector_retains_exact_version_boundaries(retrieval_tools):
    with sqlite3.connect(':memory:') as connection:
        connection.execute('CREATE TABLE gbk(id INTEGER, path TEXT)')
        for i, name in enumerate(['NZ_CP123456.1', 'NZ_CP123456.10', 'NZ_CP1234567.1',
                                  'NZxCP123456.1', 'ANZ_CP123456.1'], 1):
            connection.execute('INSERT INTO gbk VALUES(?, ?)', (i, f'/synthetic/{name}.gbk'))
        assert retrieval_tools[0].select_gbk(connection, 'NZ_CP123456.1') == (1, '/synthetic/NZ_CP123456.1.gbk')
        with pytest.raises(ValueError, match='explicit version'):
            retrieval_tools[0].select_gbk(connection, 'NZ_CP123456')
        with pytest.raises(KeyError, match='not found'):
            retrieval_tools[0].select_gbk(connection, 'NZ_CP123456.2')

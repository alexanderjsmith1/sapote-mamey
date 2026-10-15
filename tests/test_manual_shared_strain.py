"""Actual manual CLI source-only strain assertions, sharing the sibling collector."""
import importlib.util
import os
from pathlib import Path
import sys

import pytest

SRC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))
FIXTURE = Path(__file__).with_name('test_451_audit_manual_identity_and_publication.py')
spec = importlib.util.spec_from_file_location('w2_prior_fixtures', FIXTURE)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


@pytest.fixture
def candidate(monkeypatch):
    path = os.environ.get('TROVE_STRAIN_TOOL')
    if path:
        import mamey
        name = 'mamey.blastp_ingest'
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        monkeypatch.setattr(mamey, 'blastp_ingest', module)


@pytest.mark.parametrize('with_package', [True, False])
@pytest.mark.parametrize('origin', ['CSV', 'XML', 'CSV_and_XML'])
def test_foreign_space_claim_refuses_whole_manual_input(candidate, tmp_path, with_package, origin):
    query = 'SYN-B BGC001 gene=ctg1_1 aa=300' if origin != 'XML' else 'BGC001_ctg1_1'
    master, raw, pkg, args = prior.fixture(tmp_path, query, package=with_package)
    if origin != 'CSV':
        xml = tmp_path / 'alignment.xml'
        xml.write_text('<BlastOutput2><Report><Results><Search>'
                       f'<query-id>{query}</query-id><query-len>300</query-len>'
                       '<query-title>SYN-B BGC001 gene=ctg1_1 aa=300</query-title>'
                       '<hits></hits></Search></Results></Report></BlastOutput2>')
        args += ['--xml', str(xml)]
    before, raw_before = master.read_bytes(), raw.read_bytes()
    package_before = {p.relative_to(pkg): p.read_bytes() for p in pkg.rglob('*') if p.is_file()} if with_package else {}
    with pytest.raises(ValueError, match='QUERY_STRAIN_CONFLICT'):
        prior.main(args)
    assert master.read_bytes() == before and raw.read_bytes() == raw_before
    assert prior.b5_rows(master) == []
    if with_package:
        assert {p.relative_to(pkg): p.read_bytes() for p in pkg.rglob('*') if p.is_file()} == package_before


@pytest.mark.parametrize('query', ['SYN-A BGC001 gene=ctg1_1 aa=300',
                                 'ctg1_1 BGC001 gene=ctg1_1 aa=300',
                                 'BGC001_ctg1_1 BGC001 gene=ctg1_1 aa=300'])
def test_matching_space_and_no_assertion_legacy_still_work(candidate, tmp_path, query):
    master, raw, pkg, args = prior.fixture(tmp_path, query)
    assert prior.main(args) == 0
    rows = prior.b5_rows(master)
    assert len(rows) == 1 and rows[0]['strain'] == 'SYN-A'

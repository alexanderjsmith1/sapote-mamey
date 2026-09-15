"""Guard boundaries use declared uncompressed size without allocating an 80 MB fixture."""
from types import SimpleNamespace

import pytest
from mamey import antismash_evidence as evidence_module


class SizedArchive:
    def __init__(self, size):
        self.size = size

    def getinfo(self, name):
        return SimpleNamespace(file_size=self.size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.mark.parametrize('size,admitted', [(20_000_001, True), (80_000_000, True), (80_000_001, False)])
def test_full_json_guard_boundary_before_read(monkeypatch, size, admitted):
    reads = []

    def read_text(archive, name):
        reads.append(name)
        return '{"knownclusterblast": "BGC0000001"}'

    monkeypatch.setattr(evidence_module, '_read_text', read_text)
    evidence = {'loose_hits': []}
    evidence_module._parse_json_full(SizedArchive(size), 'fixture.json', evidence)
    assert bool(reads) is admitted
    assert bool(evidence['loose_hits']) is admitted
    assert bool(evidence.get('json_skipped')) is not admitted
    if not admitted:
        assert '80,000,000' in evidence['json_skipped'][0]


@pytest.mark.parametrize('size,admitted', [(80_000_000, True), (80_000_001, False)])
def test_nonstreaming_record_extractors_share_cap(monkeypatch, size, admitted):
    archive = SizedArchive(size)
    consumed = []

    def records(zf, name):
        consumed.append(name)
        yield {'id': 'record1'}

    monkeypatch.setattr(evidence_module.zipfile, 'ZipFile', lambda path: archive)
    monkeypatch.setattr(evidence_module, 'regular_file_names', lambda zf: ['fixture.json'])
    monkeypatch.setattr(evidence_module, '_should_stream', lambda zf, name: False)
    monkeypatch.setattr(evidence_module, '_iter_records', records)
    out = []
    evidence_module._run_record_extractors('fixture.zip', [(lambda rec, name, target: target.append(rec), out)])
    assert bool(consumed) is admitted
    assert bool(out) is admitted


def test_bounded_limits_unchanged():
    assert evidence_module.FULL_MAX_JSON_BYTES == 80_000_000
    assert evidence_module.BOUNDED_MAX_JSON_BYTES == 25_000_000
    assert evidence_module.BOUNDED_MAX_JSON_BYTES_STREAMING == 250_000_000
    assert evidence_module.BOUNDED_MAX_RECORDS_STREAMING == 200_000

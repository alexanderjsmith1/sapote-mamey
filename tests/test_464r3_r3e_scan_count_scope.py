"""FLBR KS counts and UMED hits carry the record set they were counted over.

The parser keeps antiSMASH region records when an archive has no whole-record GenBank. The
FLBR scan still wrote ``genome_wide_ks_like_count``, so a region-only count read as a genome-wide
one. The scan output now names its record scope, and stays NOT_BOUND when the caller gives none.
"""
import zipfile

from mamey.parsers import genbank_record_scope
from mamey.source_scans import run_source_scans


RECORD = ('LOCUS       c1   60 bp    DNA     linear   BCT 01-JAN-2000\n'
          'FEATURES             Location/Qualifiers\n'
          '     CDS             1..60\n'
          '                     /locus_tag="c1_1"\n'
          'ORIGIN\n'
          '        1 atggcggcgg cggcggcggc ggcggcggcg gcggcggcgg cggcggcggc ggcggcgtaa\n'
          '//\n')


def _zip(path, names):
    # The scope is derived from the records actually read, so each member is a parseable record.
    with zipfile.ZipFile(path, 'w') as zf:
        for name in names:
            zf.writestr(name, RECORD)
    return path


def test_region_only_archive_is_region_scoped(tmp_path):
    scope = genbank_record_scope(_zip(tmp_path / 'r.zip', ['out/c1.region001.gbk', 'out/c2.region001.gbk']))
    assert scope['state'] == 'REGION_RECORDS_ONLY'
    assert 'not the genome' in scope['note']


def test_whole_record_archive(tmp_path):
    scope = genbank_record_scope(_zip(tmp_path / 'w.zip', ['out/genome.gbk', 'out/c1.region001.gbk']))
    assert scope['state'] == 'WHOLE_RECORD_GENBANK'


def test_no_genbank_and_unreadable(tmp_path):
    assert genbank_record_scope(_zip(tmp_path / 'n.zip', ['out/index.html']))['state'] == 'NO_GENBANK'
    bad = tmp_path / 'bad.zip'
    bad.write_bytes(b'not a zip')
    assert genbank_record_scope(bad)['state'] == 'ARCHIVE_UNREADABLE'


def test_scans_stamp_bound_scope_and_default_to_not_bound():
    region = {'state': 'REGION_RECORDS_ONLY', 'note': 'region records only'}
    bound = run_source_scans([], [], {}, [], record_scope=region)
    assert bound.flbr['count_scope'] == region
    assert bound.umed['count_scope'] == region
    unbound = run_source_scans([], [], {}, [])
    assert unbound.flbr['count_scope']['state'] == 'NOT_BOUND'
    assert unbound.umed['count_scope']['state'] == 'NOT_BOUND'
    # Compatibility: the historical key stays, its scope now travels beside it.
    assert 'genome_wide_ks_like_count' in unbound.flbr

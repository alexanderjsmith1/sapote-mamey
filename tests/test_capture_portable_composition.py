"""Small stdlib-built fixtures for parent capture composition; no helper/test imports."""
from dataclasses import replace
import hashlib
import io
import struct
import warnings
import zipfile
import zlib
import pytest
from mamey import parsers
from mamey.archive_snapshot import ArchiveSnapshot,ArchiveSnapshotPolicy,ArchiveSnapshotRefused,parse_captured,captured_zip
POLICY=ArchiveSnapshotPolicy(32_000,10,64_000)
GBK='''LOCUS       SYNTHETIC_A               12 bp    DNA              UNK 01-JAN-1980
DEFINITION  Self-authored twelve-base composition fixture.
ACCESSION   SYNTHETIC_A
VERSION     SYNTHETIC_A.1
KEYWORDS    .
SOURCE      synthetic construct
  ORGANISM  synthetic construct
            other sequences; artificial sequences.
FEATURES             Location/Qualifiers
     region          1..12
                     /region_number="1"
                     /product="NRPS"
ORIGIN
        1 acgtacgtacgt
//
'''.encode()
def raw_zip(extra=(),compression=zipfile.ZIP_STORED):
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=compression) as z:
        z.writestr('fixture.region001.gbk',GBK)
        for name,data in extra:z.writestr(name,data)
    return buffer.getvalue()
def capture(tmp_path,extra=(),pin=False):
    path=tmp_path/'fixture.zip';raw=raw_zip(extra);path.write_bytes(raw)
    return path,raw,ArchiveSnapshot.capture(path,policy=POLICY,expected_sha256=hashlib.sha256(raw).hexdigest() if pin else None)

@pytest.mark.parametrize('pin',[False,True])
@pytest.mark.parametrize('fallback',[False,True])
def test_same_capture_source_pin_and_no_reopen(tmp_path,monkeypatch,pin,fallback):
    path,raw,snapshot=capture(tmp_path,pin=pin);path.unlink()
    if fallback:monkeypatch.setattr(parsers,'_require_seqio',lambda:None)
    def forbidden(*args,**kwargs):pytest.fail('attempted recapture or original-path read')
    monkeypatch.setattr(ArchiveSnapshot,'capture',forbidden)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');bgcs,receipt=parse_captured(snapshot,policy=POLICY)
    assert bgcs[0].contig=='SYNTHETIC_A.1'
    assert receipt['input_sha256']==hashlib.sha256(raw).hexdigest()
    assert receipt['original_version']==('EXPECTED_DIGEST_MATCHED' if pin else 'ORIGINAL_VERSION_UNASSERTED')

def test_independent_reader_cursors(tmp_path):
    _,_,snapshot=capture(tmp_path)
    with captured_zip(snapshot,policy=POLICY) as a,captured_zip(snapshot,policy=POLICY) as b:
        with a.open('fixture.region001.gbk') as x,b.open('fixture.region001.gbk') as y:
            assert x.read(7)==GBK[:7] and y.read()==GBK and x.read()==GBK[7:]

@pytest.mark.parametrize('name',['records.json','knownclusterblast/fixture.txt','fixture.region001.gbk'])
def test_duplicate_namespace_refuses_even_partial(tmp_path,name):
    extra=[] if name.endswith('.gbk') else [(name,b'first fabricated entry')]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');path,_,_=capture(tmp_path,extra=extra)
        with zipfile.ZipFile(path,'a') as z:z.writestr(name,b'contradictory duplicate')
        snapshot=ArchiveSnapshot.capture(path,policy=POLICY);out={'sentinel':'unchanged'}
        with pytest.raises(ArchiveSnapshotRefused):parse_captured(snapshot,policy=POLICY,require_complete_genbank=False,core_snapshot_out=out)
    assert out=={'sentinel':'unchanged'}

def test_malformed_member_completeness_does_not_claim_absence(tmp_path):
    _,_,snapshot=capture(tmp_path,extra=[('empty.gbk',b'')]);out={'sentinel':'unchanged'}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        with pytest.raises(ArchiveSnapshotRefused):parse_captured(snapshot,policy=POLICY,core_snapshot_out=out)
        assert out=={'sentinel':'unchanged'}
        bgcs,receipt=parse_captured(snapshot,policy=POLICY,require_complete_genbank=False)
    assert len(bgcs)==1 and receipt['state']=='PARSED_INCOMPLETE_EXPLICITLY_ADMITTED'
    assert receipt['biological_absence']==receipt['upstream_search_completion']=='NOT_ESTABLISHED'

def test_forged_prefix_expansion_refuses(tmp_path):
    buffer=io.BytesIO();data=GBK+GBK.replace(b'SYNTHETIC_A',b'SYNTHETIC_B')
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('fixture.region001.gbk',data)
    raw=bytearray(buffer.getvalue());central=raw.index(b'PK\x01\x02');crc=zlib.crc32(GBK)
    for offset,value in [(14,crc),(22,len(GBK)),(central+16,crc),(central+24,len(GBK))]:struct.pack_into('<I',raw,offset,value)
    path=tmp_path/'forged.zip';path.write_bytes(raw)
    with pytest.raises(ArchiveSnapshotRefused,match='EXPANSION_MISMATCH'):ArchiveSnapshot.capture(path,policy=POLICY)

def test_adapter_interrupt_preserves_caller_mapping(tmp_path):
    _,_,snapshot=capture(tmp_path);out={'sentinel':'unchanged'}
    def interrupted(source,**kwargs):raise KeyboardInterrupt('fabricated parse interruption')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        with pytest.raises(KeyboardInterrupt):parse_captured(snapshot,policy=POLICY,parse_operation=interrupted,core_snapshot_out=out)
    assert out=={'sentinel':'unchanged'}

def test_expected_digest_and_factory_identity_refuse(tmp_path):
    _,_,snapshot=capture(tmp_path)
    with pytest.raises(ArchiveSnapshotRefused,match='HASH_MISMATCH'):parse_captured(snapshot,policy=POLICY,expected_sha256='0'*64)
    with pytest.raises(ArchiveSnapshotRefused,match='NOT_CAPTURED_IN_PROCESS'):parse_captured(replace(snapshot),policy=POLICY)

@pytest.mark.parametrize('limit',['archive','members'])
def test_explicit_resource_limit_does_not_expand_to_fit(tmp_path,limit):
    path,raw,_=capture(tmp_path,extra=[('extra.txt',b'fixture')])
    policy=ArchiveSnapshotPolicy(len(raw)-1,10,64_000) if limit=='archive' else ArchiveSnapshotPolicy(32_000,1,64_000)
    with pytest.raises(ArchiveSnapshotRefused):ArchiveSnapshot.capture(path,policy=policy)

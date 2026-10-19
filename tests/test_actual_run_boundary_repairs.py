"""Completed03 wrapper fault boundaries; no pipeline/renderer/upstream execution."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
from unittest.mock import patch
import pytest
import io, zipfile
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
from mamey import captured_run as run,source_context,cli
from mamey.archive_snapshot import ArchiveSnapshotPolicy
from mamey.intake_session import CapturedIntakeSession,CapturedIntakeHold
POLICY=ArchiveSnapshotPolicy(32_000,10,64_000)
def setup(tmp_path,master=False):
    source=tmp_path/'input.zip';source.write_bytes(raw_zip())
    policy=tmp_path/'policy.json';policy.write_text(json.dumps(dict(max_archive_bytes=32_000,max_members=10,max_total_uncompressed_bytes=64_000,max_publish_bytes=128_000)))
    master_path=tmp_path/'master.xlsx' if master else None
    if master_path:master_path.write_bytes(b'SELF_AUTHORED_OLD_MASTER_BYTES')
    args=SimpleNamespace(strains=None,brief='none',locus_maps='off',metadata_csv=None,hmm_scan=False,capture_policy=str(policy),input_zip=str(source),capture_expected_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),outdir=str(tmp_path/'final'),master=str(master_path) if master else None)
    return source,policy,master_path,args

def frame(tmp_path):
    source=tmp_path/'input.zip';source.write_bytes(raw_zip());session=CapturedIntakeSession.capture(source,policy=POLICY)
    return run.RunFrame(session,source,tmp_path/'s',tmp_path/('long_final_locator_'*6),None,None),source


def test_original_path_symlink_change_cannot_fall_back_to_live_archive(tmp_path,record_property):
    bound,source=frame(tmp_path);other=tmp_path/'replacement.zip';other.write_bytes(raw_zip().replace(b'SYNTHETIC_A',b'SYNTHETIC_B'))
    # Use a valid new ZIP with recomputed CRC rather than corrupting bytes.
    import io,zipfile
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:z.writestr('fixture.region001.gbk',GBK.replace(b'SYNTHETIC_A',b'SYNTHETIC_B'))
    other.write_bytes(data.getvalue());source.unlink();source.symlink_to(other)
    with source_context.binding(bound):
        selected=source_context.bound_source(source)
        with source_context.source_zipfile(source) as z:observed=z.read('fixture.region001.gbk')
    record_property('observed_source',json.dumps({'selected_capture':selected is bound.session.snapshot,'expected_gbk_sha256':hashlib.sha256(GBK).hexdigest(),'observed_gbk_sha256':hashlib.sha256(observed).hexdigest()}))
    assert selected is bound.session.snapshot and observed==GBK


def test_replaced_bytes_at_same_locator_remain_bound_control(tmp_path):
    bound,source=frame(tmp_path);source.write_bytes(b'original bytes replaced')
    with source_context.binding(bound):
        assert source_context.bound_source(source) is bound.session.snapshot
        with source_context.source_zipfile(source) as z:assert z.read('fixture.region001.gbk')==GBK


def test_publication_budget_counts_actual_read_bytes(tmp_path,monkeypatch):
    bound,_=frame(tmp_path);folder=bound.stage/'runs';folder.mkdir(parents=True);output=folder/'result.bin';output.write_bytes(b'A')
    original=Path.open;grown=False
    def reading(path,mode="r",*args,**kwargs):
        nonlocal grown
        if path==output and mode=="rb" and not grown:grown=True;output.write_bytes(b'A'*65)
        return original(path,mode,*args,**kwargs)
    monkeypatch.setattr(Path,'open',reading)
    with pytest.raises(CapturedIntakeHold,match='PUBLICATION_BUDGET'):run.finalize_payloads(bound,8,[])


def test_publication_budget_includes_handback_relocation(tmp_path):
    bound,_=frame(tmp_path);folder=bound.stage/'runs';folder.mkdir(parents=True);output=folder/'HANDBACK.json'
    data=json.dumps({'locator':str(folder/'result')}).encode();output.write_bytes(data)
    assert len(bound.display(data.decode()).encode())>len(data)
    with pytest.raises(CapturedIntakeHold,match='PUBLICATION_BUDGET'):run.finalize_payloads(bound,len(data),[])


def test_small_stable_publication_budget_control(tmp_path):
    bound,_=frame(tmp_path);folder=bound.stage/'runs';folder.mkdir(parents=True);(folder/'result.bin').write_bytes(b'AB')
    payloads,replacement=run.finalize_payloads(bound,2,[])
    assert replacement is None and list(payloads.values())==[b'AB']


def test_failed_private_run_retains_phase_diagnostic(tmp_path,monkeypatch,record_property):
    _,_,_,args=setup(tmp_path);monkeypatch.setattr(cli,'_completion_mode',lambda args:'off');observed=[]
    def legacy(private):
        diagnostic=Path(private.outdir)/'run_phase_receipts.jsonl';diagnostic.parent.mkdir(parents=True);diagnostic.write_text('{"phase":"SELF_AUTHORED_FAILURE","status":"ERROR"}\n');observed.append(str(diagnostic));return 2
    code=run.run(args,legacy)
    retained=list(tmp_path.rglob('run_phase_receipts.jsonl'))
    record_property('phase_diagnostic',json.dumps({'code':code,'private_path':observed[0],'retained_paths':[str(p) for p in retained]}))
    assert code==2 and not Path(args.outdir).exists()
    assert retained,'failed run phase diagnostics were removed with temporary staging'


def test_precommit_publication_failure_preserves_master_control(tmp_path,monkeypatch):
    _,_,master,args=setup(tmp_path,master=True);before=master.read_bytes();monkeypatch.setattr(cli,'_completion_mode',lambda args:'off')
    def legacy(private):
        root=Path(private.outdir);root.mkdir(parents=True);(root/'result.json').write_text('{"synthetic":true}')
        Path(private.master).write_bytes(b'SELF_AUTHORED_NEW_MASTER_BYTES');return 0
    monkeypatch.setattr(run,'publish_payloads',lambda *a,**k:(_ for _ in ()).throw(OSError('fabricated precommit refusal')))
    assert run.run(args,legacy)==2 and master.read_bytes()==before and not Path(args.outdir).exists()


def test_publisher_committed_failure_is_not_reported_as_uncommitted_hold(tmp_path,monkeypatch,record_property):
    # Explicit publisher/legacy stand-ins use literal non-workbook master bytes.
    monkeypatch.setattr(run,"normalize_staged_metadata",lambda frame: None)
    _,_,master,args=setup(tmp_path,master=True);monkeypatch.setattr(cli,'_completion_mode',lambda args:'off')
    def legacy(private):
        root=Path(private.outdir);root.mkdir(parents=True);(root/'result.json').write_text('{"synthetic":true}')
        Path(private.master).write_bytes(b'SELF_AUTHORED_NEW_MASTER_BYTES');return 0
    def committed(payloads,*,replacement=None):
        # Explicit publisher-interface stand-in,not an actual workbook/OS commit claim.
        for path,data in payloads.items():path.write_bytes(data)
        if replacement:replacement[0].write_bytes(replacement[1])
        error=OSError('fabricated publisher after-commit failure');error.output_transaction_commit_status='COMMITTED';raise error
    monkeypatch.setattr(run,'publish_payloads',committed)
    result=None;error=None
    try:result=run.run(args,legacy)
    except RuntimeError as exc:error=exc
    record_property('commit_outcome',json.dumps({'returned':result,'error':str(error) if error else None,'master_is_new':master.read_bytes()==b'SELF_AUTHORED_NEW_MASTER_BYTES','fresh_output_exists':(Path(args.outdir)/'result.json').exists()}))
    assert error is not None and 'COMMITTED_POSTCOMMIT_FAILURE' in str(error)


def test_final_master_bytes_share_publication_budget(tmp_path):
    bound,_=frame(tmp_path);folder=bound.stage/'runs';folder.mkdir(parents=True)
    (folder/'result.bin').write_bytes(b'ABC')
    bound.master_stage=bound.stage/'master.xlsx';bound.master_stage.write_bytes(b'DEF')
    bound.master_final=tmp_path/'master.xlsx'
    with pytest.raises(CapturedIntakeHold,match='PUBLICATION_BUDGET'):run.finalize_payloads(bound,5,[])
    outputs,replacement=run.finalize_payloads(bound,6,[])
    assert sum(map(len,outputs.values()))+len(replacement[1])==6


def test_diagnostic_retention_is_bounded_and_unadmitted(tmp_path):
    bound,_=frame(tmp_path);folder=bound.stage/'runs';folder.mkdir(parents=True)
    (folder/'run_phase_receipts.jsonl').write_bytes(b'X'*25)
    destination=run.retain_failure_diagnostics(bound,8,ValueError('synthetic failure'))
    receipt=json.loads((destination/'FAILURE.json').read_bytes())
    assert receipt['diagnostic_bytes']==8 and receipt['files'][0]['truncated']
    assert receipt['package_or_master_admitted'] is False
    assert (destination/'runs/run_phase_receipts.jsonl').read_bytes()==b'X'*8


def test_parent_directory_alias_change_stays_bound(tmp_path):
    folder=tmp_path/'original';folder.mkdir();source=folder/'input.zip';source.write_bytes(raw_zip())
    session=CapturedIntakeSession.capture(source,policy=POLICY)
    bound=run.RunFrame(session,source,tmp_path/'s',tmp_path/'final',None,None)
    moved=tmp_path/'captured_original';folder.rename(moved)
    other=tmp_path/'other';other.mkdir();(other/'input.zip').write_bytes(b'unadmitted')
    folder.symlink_to(other,target_is_directory=True)
    with source_context.binding(bound):
        assert source_context.source_exists(source)
        assert source_context.captured_digest(source)==session.snapshot.input_sha256
        with source_context.source_zipfile(source) as archive:assert archive.read('fixture.region001.gbk')==GBK

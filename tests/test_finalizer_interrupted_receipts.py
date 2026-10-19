"""Mock publication state only: opaque bytes, no ZIP construction or native commit primitive."""
import hashlib,importlib.util,json,os,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,os.environ.get('FINALIZER_DEPENDENCY_TOOLS',str(ROOT/'tools')))
s=importlib.util.spec_from_file_location('interrupted_finalizer_owner',ROOT/'tools/finalize_public_archive.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
OPAQUE=b'SELF_AUTHORED_OPAQUE_MOCK_NOT_A_ZIP_OR_RELEASE\n'

def configure(module,tmp_path,monkeypatch,phase,exception):
 stage=tmp_path/'empty-stage';stage.mkdir();out=tmp_path/'out';out.mkdir();final=out/'opaque-fixture.bin';temporary=[];calls=[]
 monkeypatch.setattr(module,'capability_probe',lambda p:None)
 monkeypatch.setattr(module,'_inventory_bound_stage',lambda binding:[])
 def writer(binding,handle,members):
  handle.write(OPAQUE);temporary.append(Path(handle.name));calls.append('opaque-write')
  if phase=='precommit_write':raise exception
 monkeypatch.setattr(module,'_write_archive',writer)
 monkeypatch.setattr(module,'audit_archive',lambda p,members:(len(OPAQUE),hashlib.sha256(OPAQUE).hexdigest()))
 def commit(srcfd,source,dstfd,target):
  calls.append('mock-commit-attempt')
  if phase=='commit_before':raise exception
  if phase=='foreign_commit_uncertain':final.write_bytes(b'FOREIGN_CLAIMANT_PRESERVE');raise exception
  os.rename(temporary[0],final)  # Only moves owned opaque fixture; not actual archive publication.
  if phase=='commit_after':raise exception
 monkeypatch.setattr(module,'commit_noreplace',commit)
 original_sha=module._sha_path
 def sha(path):
  if path==final and phase=='postcommit_hash':raise exception
  return original_sha(path)
 monkeypatch.setattr(module,'_sha_path',sha)
 original_fsync=module.os.fsync
 def sync(fd):
  # First fsync is owned-file flush, second is postcommit directory durability.
  calls.append('fsync')
  if phase=='postcommit_fsync' and final.exists():raise exception
  return original_fsync(fd)
 monkeypatch.setattr(module.os,'fsync',sync)
 return stage,out,final,calls

@pytest.mark.parametrize('phase',['precommit_write','commit_before','commit_after','postcommit_hash','postcommit_fsync'])
@pytest.mark.parametrize('kind',['keyboard','system_zero'])
def test_interruption_always_nonzero_and_preserves_typed_state(tmp_path,monkeypatch,capsys,phase,kind):
 exc=KeyboardInterrupt() if kind=='keyboard' else SystemExit(0)
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,phase,exc)
 code=m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name]);captured=capsys.readouterr();record=json.loads(captured.out or captured.err)
 assert code==(130 if kind=='keyboard' else 1) and record['interrupted'] is True
 if phase=='precommit_write':assert record['status']=='REFUSED' and record['committed'] is False and not final.exists() and not captured.out
 elif phase=='commit_before':assert record['status']=='COMMIT_STATE_HOLD' and record['committed'] is None and not final.exists() and captured.out
 else:
  assert record['status']=='COMMITTED_HOLD' and record['committed'] is True and final.read_bytes()==OPAQUE
  assert record['expected_sha256']==hashlib.sha256(OPAQUE).hexdigest() and record['expected_size_bytes']==len(OPAQUE)
 assert not list(out.glob('.archtxn-*'))
 (tmp_path/'typed-receipt.json').write_text(json.dumps({'returncode':code,'record':record,'scope':'OPAQUE_MOCK_ONLY_NO_ARCHIVE'},indent=2)+'\n')

@pytest.mark.parametrize('exception,expected',[(SystemExit(7),7),(SystemExit('PRIVATE_EXCEPTION_TEXT_NOT_FOR_OUTPUT'),1)])
def test_foreign_or_unverified_commit_is_hold_without_ownership_claim(tmp_path,monkeypatch,capsys,exception,expected):
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,'foreign_commit_uncertain',exception)
 code=m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name]);captured=capsys.readouterr();record=json.loads(captured.out)
 assert code==expected and record['status']=='COMMIT_STATE_HOLD' and record['committed'] is None
 assert final.read_bytes()==b'FOREIGN_CLAIMANT_PRESERVE' and 'PRIVATE_EXCEPTION_TEXT_NOT_FOR_OUTPUT' not in captured.out+captured.err
 assert not list(out.glob('.archtxn-*'))


def test_normal_mock_receipt_is_unchanged(tmp_path,monkeypatch,capsys):
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,'normal',RuntimeError('unused'))
 assert m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name])==0
 record=json.loads(capsys.readouterr().out);assert record['status']=='COMMITTED' and record['archive_sha256']==hashlib.sha256(OPAQUE).hexdigest()


def test_typed_error_cannot_override_failure_to_exit_zero(tmp_path,monkeypatch,capsys):
 error=m.ArchiveTransactionError('ARCHTXN-TXN-004','synthetic_callback_failure');error.exit_code=0
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,'precommit_write',error)
 code=m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name]);captured=capsys.readouterr();record=json.loads(captured.err)
 assert code==1 and record['status']=='REFUSED' and not final.exists() and not record.get('interrupted',False)


@pytest.mark.parametrize('phase',['capability','inventory','finally_exists'])
@pytest.mark.parametrize('kind',['keyboard','system_zero'])
def test_peer_first_preflight_or_final_cleanup_interruption(tmp_path,monkeypatch,capsys,phase,kind):
 exception=KeyboardInterrupt() if kind=='keyboard' else SystemExit(0)
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,'normal',RuntimeError('unused'))
 original_exists=Path.exists
 if phase=='capability':monkeypatch.setattr(m,'capability_probe',lambda p:(_ for _ in ()).throw(exception))
 elif phase=='inventory':monkeypatch.setattr(m,'_inventory_bound_stage',lambda binding:(_ for _ in ()).throw(exception))
 else:
  fired=[]
  def exists(path):
   if not fired and path.name.startswith('.archtxn-') and original_exists(final) and not original_exists(path):fired.append(True);raise exception
   return original_exists(path)
  monkeypatch.setattr(Path,'exists',exists)
 code=m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name]);cap=capsys.readouterr();r=json.loads(cap.out or cap.err)
 assert code==(130 if kind=='keyboard' else 1) and r['interrupted'] is True
 if phase=='finally_exists':assert r['status']=='COMMITTED_HOLD' and r['committed'] is True and final.read_bytes()==OPAQUE
 else:assert r['status']=='REFUSED' and not final.exists()


@pytest.mark.parametrize('phase',['commit_before','commit_after','foreign_commit_uncertain'])
def test_peer_ordinary_attempt_error_has_conservative_commit_state(tmp_path,monkeypatch,capsys,phase):
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,phase,OSError('synthetic ordinary commit error'))
 code=m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name]);cap=capsys.readouterr();r=json.loads(cap.out)
 assert code==1 and not r.get('interrupted',False)
 if phase=='commit_after':assert r['status']=='COMMITTED_HOLD' and r['committed'] is True and final.read_bytes()==OPAQUE
 else:
  assert r['status']=='COMMIT_STATE_HOLD' and r['committed'] is None
  if phase=='foreign_commit_uncertain':assert final.read_bytes()==b'FOREIGN_CLAIMANT_PRESERVE'


def test_known_fileexists_is_refusal_and_foreign_bytes_survive(tmp_path,monkeypatch,capsys):
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,'foreign_commit_uncertain',FileExistsError('synthetic claimant'))
 code=m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name]);r=json.loads(capsys.readouterr().err)
 assert code==1 and r['status']=='REFUSED' and r['committed'] is False and r['error_code']=='ARCHTXN-TXN-001'
 assert final.read_bytes()==b'FOREIGN_CLAIMANT_PRESERVE'


def test_replaced_cleanup_directory_is_never_deleted(tmp_path,monkeypatch,capsys):
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,'normal',RuntimeError('unused'));original_commit=m.commit_noreplace;foreign=[]
 def replace_directory(*args):
  original_commit(*args);owned=next(out.glob('.archtxn-*'));owned.rename(out/'retained_original_owned');owned.mkdir();(owned/'foreign-sentinel').write_bytes(b'FOREIGN');foreign.append(owned)
 monkeypatch.setattr(m,'commit_noreplace',replace_directory)
 assert m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name])==1
 r=json.loads(capsys.readouterr().out);assert r['status']=='COMMITTED_HOLD' and r['cleanup_state']=='CLEANUP_UNVERIFIED'
 assert (foreign[0]/'foreign-sentinel').read_bytes()==b'FOREIGN' and final.read_bytes()==OPAQUE


class ReceiptStream:
 def __init__(self,mode):self.mode=mode;self.text='';self.calls=0
 def write(self,text):
  self.calls+=1
  if self.mode=='zero':return 0
  if self.mode=='none':return None
  if self.mode=='broken':raise BrokenPipeError('PRIVATE_EXCEPTION_NOT_EMITTED')
  if self.mode=='keyboard':raise KeyboardInterrupt()
  if self.mode=='system_zero':raise SystemExit(0)
  n=min(7,len(text)) if self.mode=='partial' else len(text);self.text+=text[:n];return n
 def flush(self):
  if self.mode=='flush':raise OSError('PRIVATE_FLUSH_ERROR_NOT_EMITTED')


@pytest.mark.parametrize('mode',['zero','none','broken','flush','keyboard','system_zero'])
def test_receipt_failure_cannot_be_green_and_falls_back_to_stderr(monkeypatch,mode):
 out=ReceiptStream(mode);err=ReceiptStream('ok');monkeypatch.setattr(m.sys,'stdout',out);monkeypatch.setattr(m.sys,'stderr',err)
 record={'status':'COMMITTED','final_name':'opaque.bin','archive_sha256':'0'*64,'archive_bytes':1,'cleanup_state':'MOCK_ONLY'}
 code=m._publish_receipt(record,0);held=json.loads(err.text)
 assert code==(130 if mode=='keyboard' else 1) and held['status']=='COMMITTED_HOLD' and held['committed'] is True
 assert held['receipt_error_code']=='ARCHTXN-RECEIPT-001' and 'PRIVATE_' not in err.text


def test_partial_stream_writes_complete_one_json_record(monkeypatch):
 out=ReceiptStream('partial');err=ReceiptStream('ok');monkeypatch.setattr(m.sys,'stdout',out);monkeypatch.setattr(m.sys,'stderr',err)
 record={'status':'COMMITTED','final_name':'opaque.bin'}
 assert m._publish_receipt(record,0)==0 and json.loads(out.text)==record and out.calls>1 and not err.text


def test_both_unavailable_streams_remain_failure(monkeypatch):
 out=ReceiptStream('broken');err=ReceiptStream('broken');monkeypatch.setattr(m.sys,'stdout',out);monkeypatch.setattr(m.sys,'stderr',err)
 with pytest.raises(m.ArchiveReceiptPublicationError) as observed:
  m._publish_receipt({'status':'COMMITTED'},0)
 assert observed.value.exit_code==1 and observed.value.receipt_record['receipt_delivery']=='BOTH_CHANNELS_UNAVAILABLE'
 assert observed.value.receipt_record['status']=='COMMITTED_HOLD' and 'PRIVATE_' not in str(observed.value)


def test_precommit_stderr_failure_never_uses_stdout(monkeypatch):
 out=ReceiptStream('ok');err=ReceiptStream('broken');monkeypatch.setattr(m.sys,'stdout',out);monkeypatch.setattr(m.sys,'stderr',err)
 assert m._publish_receipt({'status':'REFUSED','committed':False},1)==1 and not out.text


def test_direct_api_error_string_agrees_with_recovered_commit_state(tmp_path,monkeypatch):
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,'commit_after',OSError('synthetic callback'))
 with pytest.raises(m.ArchiveTransactionError) as observed:m.finalize_archive(stage,out,final.name)
 assert observed.value.committed is True and str(observed.value).startswith('ARCHTXN-TXN-006: postcommit_operation_failed')


def test_held_receipt_cannot_request_exit_zero(monkeypatch):
 out=ReceiptStream('ok');err=ReceiptStream('ok');monkeypatch.setattr(m.sys,'stdout',out);monkeypatch.setattr(m.sys,'stderr',err)
 assert m._publish_receipt({'status':'COMMIT_STATE_HOLD','committed':None},0)==1


@pytest.mark.parametrize('fallback,expected,kind',[('broken',1,'WRITE_OR_FLUSH_FAILED'),('zero',1,'WRITE_OR_FLUSH_FAILED'),('none',1,'WRITE_OR_FLUSH_FAILED'),('system_zero',1,'EXIT_REQUEST'),('keyboard',130,'INTERRUPTED')])
def test_unrecoverable_publication_is_typed_and_cli_handles_nonzero(monkeypatch,fallback,expected,kind):
 out=ReceiptStream('broken');err=ReceiptStream(fallback);monkeypatch.setattr(m.sys,'stdout',out);monkeypatch.setattr(m.sys,'stderr',err)
 with pytest.raises(m.ArchiveReceiptPublicationError) as observed:m._publish_receipt({'status':'COMMITTED'},0)
 error=observed.value;assert error.exit_code==expected and error.committed is True
 assert error.receipt_record['fallback_failure_kind']==kind and error.receipt_record['receipt_delivery']=='BOTH_CHANNELS_UNAVAILABLE'
 assert 'PRIVATE_' not in str(error)+json.dumps(error.receipt_record)
 monkeypatch.setattr(m,'finalize_archive',lambda *a,**k:m.ArchiveReceipt('COMMITTED',None,None,'opaque.bin',1,'0'*64,1,'TEMP_REMOVED_BY_COMMIT'))
 assert m._main(['--stage-root','unopened','--output-dir','unopened','--archive-name','opaque.bin'])==expected
 assert not out.text and not err.text


@pytest.mark.parametrize('phase,exception,expected,observations',[('commit_before',OSError('PRIVATE_COMMIT_PROBE'),1,1),('commit_before',SystemExit(0),1,2),('commit_before',KeyboardInterrupt(),130,2),('foreign_commit_uncertain',SystemExit(0),1,2)])
def test_unavailable_ownership_probe_is_recorded_and_keeps_unknown_hold(tmp_path,monkeypatch,capsys,phase,exception,expected,observations):
 import errno
 stage,out,final,calls=configure(m,tmp_path,monkeypatch,phase,exception);original=Path.lstat
 def lstat(path,*a,**k):
  if path==final and 'mock-commit-attempt' in calls:raise PermissionError(errno.EACCES,'PRIVATE_PROBE_TEXT')
  return original(path,*a,**k)
 monkeypatch.setattr(Path,'lstat',lstat)
 code=m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name]);cap=capsys.readouterr();r=json.loads(cap.out)
 assert code==expected and r['status']=='COMMIT_STATE_HOLD' and r['committed'] is None
 assert len(r['ownership_probe_failures'])==observations
 assert all(v['outcome']=='IO_UNVERIFIED' and v['errno']==errno.EACCES for v in r['ownership_probe_failures'])
 assert r['ownership_probe_failures'][-1]['phase']=='outer_commit_recovery' and 'PRIVATE_' not in cap.out+cap.err
 if phase=='foreign_commit_uncertain':assert final.read_bytes()==b'FOREIGN_CLAIMANT_PRESERVE'
 else:assert not final.exists()


def test_missing_ownership_binding_is_explicit_hold_not_false_refusal(tmp_path,monkeypatch,capsys):
 stage=tmp_path/'stage';stage.mkdir();out=tmp_path/'out';out.mkdir();final=out/'opaque.bin';final.write_bytes(OPAQUE)
 def transaction(stage,out,name,state,**kw):
  state.update(attempted=True,final_path=final,final_name=final.name)
  raise OSError('PRIVATE_MISSING_BINDING')
 monkeypatch.setattr(m,'_finalize_archive_transaction',transaction)
 assert m._main(['--stage-root',str(stage),'--output-dir',str(out),'--archive-name',final.name])==1
 cap=capsys.readouterr();r=json.loads(cap.out);assert r['status']=='COMMIT_STATE_HOLD' and r['committed'] is None
 assert r['ownership_probe_failures']==[{'phase':'outer_commit_recovery','outcome':'BINDING_UNAVAILABLE'}]
 assert final.read_bytes()==OPAQUE and 'PRIVATE_' not in cap.out+cap.err

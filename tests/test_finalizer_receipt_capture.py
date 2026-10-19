"""Caller tail and leaf-capture races only; opaque mock object, no archive/export."""
import json,os,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];CURRENT=ROOT/'tools/make_public_tier.sh'

def run(tmp_path,source,mode,attack=None,inside=False,descriptor_race=None):
 harness=tmp_path/'harness';harness.mkdir();out=tmp_path/'out';out.mkdir();stage=tmp_path/'stage';stage.mkdir();temp=stage if inside else tmp_path/'tmp';temp.mkdir(exist_ok=True);sentinel=tmp_path/'foreign-sentinel';sentinel.write_bytes(b'KEEP_FOREIGN_BYTES');marker=tmp_path/'child-launched'
 child='''import hashlib,json,sys
from pathlib import Path
a=sys.argv;out=Path(a[a.index('--output-dir')+1]);name=a[a.index('--archive-name')+1];target=out/name
Path(MARKER).write_text('fakechild')
mode=MODE;data=b'OPAQUE_MOCK_NOT_ARCHIVE_OR_RELEASE'
if mode not in ['fallback_unknown','claimed']:target.write_bytes(data)
record={'status':'COMMITTED','error_code':None,'reason_code':None,'final_name':name,'member_count':1,'archive_sha256':hashlib.sha256(data).hexdigest(),'archive_bytes':len(data),'cleanup_state':'TEMP_REMOVED_BY_COMMIT'}
if mode=='empty':sys.exit(0)
if mode=='partial':sys.stdout.write('{"status":"COMMITTED"');sys.exit(0)
if mode=='wrong_digest':record['archive_sha256']='0'*64
if mode=='empty_digest':record['archive_sha256']=hashlib.sha256(b'').hexdigest()
if mode=='extra':record['unadmitted_field']=True
if mode=='wrong_name':record['final_name']='different.bin'
if mode=='wrong_type':record['archive_bytes']=True
if mode=='symlink_object':
 target.rename(out/'foreign-opaque');target.symlink_to(out/'foreign-opaque')
if mode.startswith('fallback_'):
 r={'status':'COMMIT_STATE_HOLD' if mode=='fallback_unknown' else 'COMMITTED_HOLD','committed':None if mode=='fallback_unknown' else True,'error_code':'ARCHTXN-TXN-006'}
 sys.stderr.write(json.dumps(r)+'\\n');sys.exit(1)
if mode=='claimed':
 target.write_bytes(b'CLAIMANT_KEEP');sys.stderr.write(json.dumps({'status':'REFUSED','committed':False,'error_code':'ARCHTXN-TXN-001'})+'\\n');sys.exit(1)
text=json.dumps(record)
if mode=='duplicate':text=text[:-1]+',"status":"COMMITTED"}'
sys.stdout.write(text+'\\n')
'''.replace('MODE',repr(mode)).replace('MARKER',repr(str(marker)))
 (harness/'finalize_public_archive.py').write_text(child)
 env=dict(os.environ,PYTHON=sys.executable,TMPDIR=str(temp),STAGE=str(stage),OUT=str(out),NAME='opaque.bin',ARCHIVE=str(out/'opaque.bin'),TIER='merged',VERSION='MOCK_NOT_RELEASE')
 if attack:
  real=shutil.which('mktemp');bin=tmp_path/'bin';bin.mkdir();wrapper=bin/'mktemp'
  wrapper.write_text('#!'+sys.executable+'\n'+'''import subprocess,sys
from pathlib import Path
p=Path(subprocess.check_output([REAL,*sys.argv[1:]],text=True).strip())
if '-d' in sys.argv:
 (p/LEAF).symlink_to(FOREIGN)
else:
 p.rename(str(p)+'.owned-empty-retained');p.symlink_to(FOREIGN)
print(str(p))
'''.replace('REAL',repr(real)).replace('LEAF',repr('receipt.'+attack)).replace('FOREIGN',repr(str(sentinel))))
  wrapper.chmod(0o755);env['PATH']=str(bin)+':'+env['PATH']
 if descriptor_race:
  env['PYTHON']=validator_race_wrapper(tmp_path,sentinel,descriptor_race)
 text=source.read_text();code='set -eu\n'+text[text.index('ARCHTXN_TOOL='):]
 result=subprocess.run(['bash','-c',code,str(harness/'locator-only.sh')],env=env,capture_output=True,text=True,timeout=10)
 (tmp_path/'receipt.json').write_text(json.dumps({'code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'foreign_bytes_hex':sentinel.read_bytes().hex(),'child_launched':marker.exists(),'scope':'FAKE_CHILD_OPAQUE_OBJECT_ONLY_NO_ARCHIVE'},indent=2)+'\n')
 return result,sentinel,marker,out

@pytest.mark.parametrize('mode',['empty','partial','wrong_digest','wrong_name','wrong_type','duplicate','symlink_object','empty_digest','extra'])
def test_success_status_without_complete_bound_receipt_is_hold(tmp_path,mode):
 r,sentinel,marker,out=run(tmp_path,CURRENT,mode)
 assert r.returncode==11 and 'OK  ' not in r.stdout and (out/'opaque.bin').exists()
 assert sentinel.read_bytes()==b'KEEP_FOREIGN_BYTES'

def test_valid_opaque_receipt_protocol_only_control(tmp_path):
 r,sentinel,marker,out=run(tmp_path,CURRENT,'valid')
 assert r.returncode==0 and 'OK  ' in r.stdout and marker.exists()
 # Models stream/object receipt validation only; opaque bytes are NOT a release archive.
 assert (out/'opaque.bin').read_bytes()==b'OPAQUE_MOCK_NOT_ARCHIVE_OR_RELEASE'

@pytest.mark.parametrize('mode',['fallback_unknown','fallback_committed'])
def test_failure_hold_receipt_on_stderr_remains_hold(tmp_path,mode):
 r,sentinel,marker,out=run(tmp_path,CURRENT,mode)
 assert r.returncode==11 and 'HOLD:' in r.stderr and 'OK  ' not in r.stdout

def test_known_claimant_is_still_exit_nine(tmp_path):
 r,sentinel,marker,out=run(tmp_path,CURRENT,'claimed');assert r.returncode==9 and (out/'opaque.bin').read_bytes()==b'CLAIMANT_KEEP'

@pytest.mark.parametrize('attack',['stdout','stderr'])
def test_leaf_capture_symlink_race_never_overwrites_or_launches(tmp_path,attack):
 r,sentinel,marker,out=run(tmp_path,CURRENT,'fallback_unknown',attack=attack)
 assert r.returncode!=0 and sentinel.read_bytes()==b'KEEP_FOREIGN_BYTES' and not marker.exists()
 captures=list((tmp_path/'tmp').glob('archtxn-capture.*'));assert len(captures)==1 and (captures[0]/('receipt.'+attack)).is_symlink()

def test_capture_inside_stage_refuses_before_child(tmp_path):
 r,sentinel,marker,out=run(tmp_path,CURRENT,'valid',inside=True);assert r.returncode==10 and not marker.exists() and 'outside the final stage' in r.stderr



def validator_race_wrapper(home,sentinel,mutation):
 wrapper=home/'validator-wrapper'
 script=r'''import os,pathlib,subprocess,sys
if len(sys.argv)>3 and sys.argv[1]=='-' and sys.argv[2].endswith('receipt.stdout'):
 code=sys.stdin.read();target=pathlib.Path(sys.argv[3]);foreign=pathlib.Path(FOREIGN);marker=pathlib.Path(MARKER);mode=MUTATION
 real_open=pathlib.Path.open;real_lstat=pathlib.Path.lstat;real_os_open=os.open;real_read=os.read
 data=target.read_bytes();fired=False;stat_count=0
 def fire(action):
  global fired
  if fired:return
  fired=True;marker.write_text(action)
  if action=='truncate':
   with real_open(target,'wb') as handle:handle.write(b'')
  elif action=='rewrite':
   with real_open(target,'wb') as handle:handle.write(b'X'*len(data))
  elif action in ['replace','symlink']:
   target.rename(target.with_name('retained-opened-generation.bin'))
   if action=='replace':
    with real_open(target,'wb') as handle:handle.write(data)
   else:target.symlink_to(foreign)
 def opening(self,*args,**kw):
  if self==target and args and args[0]=='rb' and mode=='path_open_truncate':fire('truncate')
  return real_open(self,*args,**kw)
 def os_open(path,flags,*args,**kw):
  if pathlib.Path(path)==target and (flags & getattr(os,'O_ACCMODE',3))==os.O_RDONLY:
   if mode=='open_truncate':fire('truncate')
   elif mode=='open_symlink':fire('symlink')
  return real_os_open(path,flags,*args,**kw)
 def read(fd,count):
  if mode=='read_truncate':fire('truncate')
  if mode=='read_short':fire('short');return b''
  if mode=='validator_system_zero':fire('system_zero');raise SystemExit(0)
  if mode=='validator_keyboard':fire('keyboard');raise KeyboardInterrupt()
  block=real_read(fd,count)
  if not block:
   if mode=='after_read_truncate':fire('truncate')
   elif mode=='after_read_same_size_rewrite':fire('rewrite')
   elif mode=='after_read_replace':fire('replace')
   elif mode=='after_read_symlink':fire('symlink')
  return block
 def lstat(self,*args,**kw):
  global stat_count
  if self==target:
   stat_count+=1
   if mode=='initial_stat_replace' and stat_count==1:
    original=real_lstat(self,*args,**kw);fire('replace');return original
   if stat_count==2:
    if mode=='final_lstat_replace':fire('replace')
    elif mode=='final_lstat_symlink':fire('symlink')
  return real_lstat(self,*args,**kw)
 pathlib.Path.open=opening;pathlib.Path.lstat=lstat;os.open=os_open;os.read=read
 sys.argv=sys.argv[1:];exec(compile(code,'<exact-validator-stdin-own-fixture-mutations>','exec'))
else:raise SystemExit(subprocess.call([REAL,*sys.argv[1:]]))
'''.replace('FOREIGN',repr(str(sentinel))).replace('MARKER',repr(str(home/'mutation-observed'))).replace('MUTATION',repr(mutation)).replace('REAL',repr(sys.executable))
 wrapper.write_text('#!'+sys.executable+'\n'+script);wrapper.chmod(0o755);return str(wrapper)


@pytest.mark.parametrize('mutation',[
 'path_open_truncate','open_truncate','read_truncate','read_short',
 'after_read_truncate','after_read_same_size_rewrite','after_read_replace',
 'after_read_symlink','final_lstat_replace','final_lstat_symlink',
 'initial_stat_replace','open_symlink','validator_system_zero','validator_keyboard'])
def test_descriptor_bound_count_hash_and_generation_races_hold(tmp_path,mutation):
 mode='empty_digest' if mutation in ['path_open_truncate','open_truncate','read_truncate','read_short'] else 'valid'
 r,sentinel,marker,out=run(tmp_path,CURRENT,mode,descriptor_race=mutation)
 assert r.returncode==11 and 'OK  ' not in r.stdout and marker.exists()
 assert sentinel.read_bytes()==b'KEEP_FOREIGN_BYTES'
 if mutation=='path_open_truncate':
  # Original peer Path.open hook is no longer reached by descriptor-based admission.
  assert not (tmp_path/'mutation-observed').exists()
 else:assert (tmp_path/'mutation-observed').is_file()
 assert (out/'opaque.bin').exists() or (out/'opaque.bin').is_symlink()

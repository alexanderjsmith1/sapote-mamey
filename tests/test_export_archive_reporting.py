"""Tiny source-bound finalizer probes; never run the whole builder."""
import importlib.util,json,os,subprocess,sys,zipfile
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]; BASE_TOOLS=Path(os.environ.get('EXPORT_ARCHIVE_BASE_TOOLS',str(ROOT/'tools'))); SOURCE=BASE_TOOLS/'finalize_public_archive.py'
spec=importlib.util.spec_from_file_location('q4_finalizer',SOURCE); m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

def block(path):
 text=path.read_text(); return text[text.index('ARCHTXN_TOOL='):text.index('\necho "OK  $TIER')]

def run(tmp_path,source,mode='hold'):
 stage=tmp_path/'stage'; stage.mkdir();(stage/'record.txt').write_bytes(b'SYNTHETIC archive test\n')
 out=tmp_path/'out';out.mkdir();h=tmp_path/'harness';h.mkdir();(h/'make_public_tier.sh').write_text('# shell locator only\n')
 wrapper='''import importlib.util,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('bound_finalizer',SOURCE)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
original=m.finalize_archive
def fail_fsync(fd): raise OSError('injected tiny-fixture durability failure')
def hold(*a,**k): return original(*a,postcommit_fsync=fail_fsync,**k)
if MODE=='hold': m.finalize_archive=hold
if MODE=='silent':
 args=sys.argv; o=Path(args[args.index('--output-dir')+1])/args[args.index('--archive-name')+1];o.write_bytes(b'uncertain synthetic partial');sys.exit(1)
if MODE=='badstage': (Path(sys.argv[sys.argv.index('--stage-root')+1])/'Rplots.pdf').write_bytes(b'synthetic default device')
sys.exit(m._main())
'''.replace('SOURCE',repr(str(SOURCE))).replace('MODE',repr(mode))
 (h/'finalize_public_archive.py').write_text(wrapper)
 final=out/'SYNTHETIC-fixture.zip'
 if mode=='existing':final.write_bytes(b'prior claimant')
 if mode=='dangling':final.symlink_to(out/'absent-target')
 env=os.environ.copy();env.update(STAGE=str(stage),OUT=str(out),NAME=final.name,ARCHIVE=str(final),PYTHON=sys.executable,TMPDIR=str(tmp_path),PYTHONDONTWRITEBYTECODE='1')
 result=subprocess.run(['bash','-c',block(source),str(h/'make_public_tier.sh')],env=env,text=True,capture_output=True)
 (tmp_path/'shell_receipt.json').write_text(json.dumps({'code':result.returncode,'stdout':result.stdout,'stderr':result.stderr},indent=2)+'\n')
 return result,stage,final

def test_fixed_committed_hold(tmp_path):
 result,stage,final=run(tmp_path,ROOT/'tools/make_public_tier.sh')
 assert result.returncode==11 and 'COMMITTED_HOLD' in result.stderr and 'no object created' not in result.stderr
 assert final.is_file() and result.stdout==''
 record=next(json.loads(line) for line in result.stderr.splitlines() if line.startswith('{'))
 assert record['committed'] is True and record['expected_size_bytes']==final.stat().st_size
 with zipfile.ZipFile(final) as z:assert z.read('record.txt')==(stage/'record.txt').read_bytes()

@pytest.mark.parametrize('mode',['existing','dangling'])
def test_claimant_preserved(tmp_path,mode):
 result,stage,final=run(tmp_path,ROOT/'tools/make_public_tier.sh',mode)
 assert result.returncode==9
 assert final.is_symlink() if mode=='dangling' else final.read_bytes()==b'prior claimant'

def test_unknown_partial_hold(tmp_path):
 result,stage,final=run(tmp_path,ROOT/'tools/make_public_tier.sh','silent')
 assert result.returncode==11 and 'commitment is unverified' in result.stderr
 assert final.read_bytes()==b'uncertain synthetic partial'

def test_precommit_refusal(tmp_path):
 result,stage,final=run(tmp_path,ROOT/'tools/make_public_tier.sh','badstage')
 assert result.returncode==10 and not final.exists() and 'no final archive path observed' in result.stderr

def test_success_bytes(tmp_path):
 result,stage,final=run(tmp_path,ROOT/'tools/make_public_tier.sh','success')
 assert result.returncode==0
 with zipfile.ZipFile(final) as z:assert z.namelist()==['record.txt'] and z.read('record.txt')==(stage/'record.txt').read_bytes()

def test_duplicate_zip_refused(tmp_path):
 stage=tmp_path/'stage';stage.mkdir();(stage/'x').write_bytes(b'x'); rows=m.inventory_stage(stage); zpath=tmp_path/'duplicate.zip'
 binding=m._bind_stage_root(stage);m._write_archive(binding,zpath,rows)
 with zipfile.ZipFile(zpath,'a') as z:z.writestr('x',b'x')
 with pytest.raises(m.ArchiveTransactionError) as err:m.audit_archive(zpath,rows)
 assert err.value.code=='ARCHTXN-ZIP-003'

def test_mutation_before_commit(tmp_path,monkeypatch):
 stage=tmp_path/'stage';stage.mkdir();(stage/'x').write_bytes(b'x');out=tmp_path/'out';out.mkdir();prior=m.audit_archive
 def mutate(*a,**k):
  result=prior(*a,**k);(stage/'x').write_bytes(b'changed');return result
 monkeypatch.setattr(m,'audit_archive',mutate)
 with pytest.raises(m.ArchiveTransactionError) as err:m.finalize_archive(stage,out,'SYNTHETIC.zip')
 assert err.value.reason=='stage_changed_after_audit' and not (out/'SYNTHETIC.zip').exists()

def test_foreign_replacement_directory_preserved(tmp_path,monkeypatch):
 stage=tmp_path/'stage';stage.mkdir();(stage/'x').write_bytes(b'x');out=tmp_path/'out';out.mkdir();prior=m.audit_archive;replaced=[]
 def replace_owned(*a,**k):
  result=prior(*a,**k); owned=Path(a[0]).parent; retained=out/'retained-owned-original';owned.rename(retained);owned.mkdir();(owned/'foreign.txt').write_bytes(b'foreign ownership');replaced.append(owned);return result
 monkeypatch.setattr(m,'audit_archive',replace_owned)
 with pytest.raises(m.ArchiveTransactionError):m.finalize_archive(stage,out,'SYNTHETIC.zip')
 assert (replaced[0]/'foreign.txt').read_bytes()==b'foreign ownership'
 assert not (out/'SYNTHETIC.zip').exists()

"""Negative controls for source-bound public roles; no registry or biology input."""
import copy,hashlib,importlib.util,json,sys
from pathlib import Path
import pytest
I=Path(__file__).resolve().parents[1]
POLICY=Path(__file__).with_name('reviewed_public_reference_sites.json')
sys.path.insert(0,str(Path(__file__).resolve().parent))
from _identifier_role_policy import reviewed_public_sites
spec=importlib.util.spec_from_file_location('source_public_code_policy',Path(__file__).with_name('test_452_bundle_code_has_no_cohort_ids.py'))
code=importlib.util.module_from_spec(spec);spec.loader.exec_module(code)
manifest=json.loads(POLICY.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
@pytest.fixture
def selected(tmp_path):
 entry=copy.deepcopy(next(e for e in manifest['files'] if e['path']=='tools/redact_public_tier.py'))
 raw=(I/entry['path']).read_bytes();path=tmp_path/entry['path'];path.parent.mkdir();path.write_bytes(raw)
 policy=tmp_path/'policy.json';j={'schema':manifest['schema'],'files':[entry]};policy.write_text(json.dumps(j))
 return tmp_path,path,raw,policy,j

def test_historical14_tool_sites_and_exact_fixture_diagnostic(selected):
 # Preserve the original fourteen-site metadata proof without claiming every live tool binds.
 public_roles={'public_product_reference','public_organism_reference'}
 historical=[{'path':e['path'],'source_sha256':e['source_sha256'],
              'sites':[s for s in e['sites'] if s['role'] in public_roles]}
             for e in manifest['files'] if e['path'].startswith('tools/')
             and any(s['role'] in public_roles for s in e['sites'])]
 assert sum(len(e['sites']) for e in historical)==14
 assert sha(json.dumps(historical,sort_keys=True,separators=(',',':')).encode())=='faee87fe1d242b9b387cdd9238765861575d4222b16effc74b8fe1f1807585b6'
 # Exercise the unchanged exact redactor fixture as an optional positive diagnostic.
 root,path,raw,policy,j=selected
 assert len(reviewed_public_sites(root,path,raw,policy))==11
 assert code._unreviewed_code_ids(root,code.SYNTHETIC,policy)=={}

@pytest.mark.parametrize('mode',['changed','duplicated','moved','prefix','identity','keyword','subject','dict'])
def test_new_private_or_changed_site_cannot_borrow_public_role(selected,mode):
 root,path,raw,policy,j=selected;entry=j['files'][0];site=entry['sites'][0];token=raw[site['start']:site['end']].decode()
 if mode=='changed':raw+=b'\n# unrelated edit\n'
 elif mode=='duplicated':raw+=('\n# public reference '+token+'\n').encode()
 elif mode=='moved':path=path.with_name('copied.py')
 elif mode=='prefix':raw+=('\n# '+token+'0\n').encode()
 elif mode=='identity':raw=('strain_id = '+repr(token)+'\n').encode()
 elif mode=='keyword':raw=('f(strain='+repr(token)+')\n').encode()
 elif mode=='subject':raw=('subject: str = '+repr(token)+'\n').encode()
 else:raw=('x = {"isolate_id": '+repr(token)+'}\n').encode()
 path.write_bytes(raw)
 # Rebinding identity fields still cannot turn a specimen identity into a product role.
 if mode in ['identity','keyword','subject','dict']:
  a=raw.index(token.encode());entry.update(path=path.relative_to(root).as_posix(),source_sha256=sha(raw),sites=[{'start':a,'end':a+len(token),'token_sha256':sha(token.encode()),'context_start':0,'context_end':len(raw),'context_sha256':sha(raw),'role':'public_product_reference','owner':'<module>','lexical_kind':'string','provenance':copy.deepcopy(site['provenance'])}]);policy.write_text(json.dumps(j))
 assert not reviewed_public_sites(root,path,raw,policy)
 assert code._unreviewed_code_ids(root,set(),policy)

@pytest.mark.parametrize('mode',['sourcehash','contexthash','tokenhash','offset','duplicate','schema','duplicatekey','path','symlink','source_symlink','unknownrole'])
def test_invalid_or_unbound_role_table_grants_nothing(selected,mode):
 root,path,raw,policy,j=selected;entry=j['files'][0];site=entry['sites'][0]
 if mode=='sourcehash':entry['source_sha256']='0'*64
 elif mode=='contexthash':site['context_sha256']='0'*64
 elif mode=='tokenhash':site['token_sha256']='0'*64
 elif mode=='offset':site['start']=True
 elif mode=='duplicate':entry['sites'].append(copy.deepcopy(site))
 elif mode=='schema':j['schema']='unknown'
 elif mode=='path':entry['path']='../tools/redact_public_tier.py'
 elif mode=='unknownrole':site['role']='synthetic_strain'
 elif mode=='source_symlink':
  other=path.with_name('original.py');other.write_bytes(raw);path.unlink();path.symlink_to(other)
 if mode=='duplicatekey':policy.write_text('{"schema":"x","schema":"x","files":[]}')
 elif mode=='symlink':
  other=policy.with_name('original.json');other.write_text(json.dumps(j));policy.unlink();policy.symlink_to(other)
 else:policy.write_text(json.dumps(j))
 assert not reviewed_public_sites(root,path,raw,policy)

@pytest.mark.parametrize('suffix',['0','N','_alias','é'])
def test_nonexact_reference_continuation_refused_even_with_rebound_hash(selected,suffix):
 root,path,raw,policy,j=selected;entry=j['files'][0];site=entry['sites'][0];token=raw[site['start']:site['end']].decode();raw=('product = '+repr(token+suffix)+'\n').encode();a=raw.index(token.encode());entry.update(source_sha256=sha(raw),sites=[{'start':a,'end':a+len(token),'token_sha256':sha(token.encode()),'context_start':0,'context_end':len(raw),'context_sha256':sha(raw),'role':'public_product_reference','owner':'<module>','lexical_kind':'string','provenance':copy.deepcopy(site['provenance'])}]);path.write_bytes(raw);policy.write_text(json.dumps(j));assert not reviewed_public_sites(root,path,raw,policy)

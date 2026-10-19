"""Exact miniature role entries exercise assignment semantics, not export authority."""
import importlib.util,json,os,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
selected=Path(os.environ.get('IDENTIFIER_ROLE_ENGINE',ROOT/'tools/identifier_source_roles.py'))
spec=importlib.util.spec_from_file_location('identifier_source_roles',selected)
roles=importlib.util.module_from_spec(spec);sys.modules[spec.name]=roles;spec.loader.exec_module(roles)
catalog,public,public_keys=roles.reference_hashes(ROOT)
TOKEN=next(e['token'] for e in json.loads(catalog)['tokens'] if e['kind']=='public_natural_product_name')
_,allowed=roles.declarations(ROOT,public_keys)

def entry(source):
 raw=source.format(p=TOKEN).encode();match=next(roles.ID.finditer(raw.decode()));a,b=match.span();owner,kind,_=roles.semantics(raw,a,b)
 site={'start':a,'end':b,'context_start':0,'context_end':len(raw),'token_sha256':roles.digest(raw[a:b]),
       'context_sha256':roles.digest(raw),'role':'public_product_reference','owner':owner,'lexical_kind':kind,
       'provenance':{'kind':'ADOPTED_PUBLIC_SOURCE_SITE','reviewed_patch_sha256':'0'*64}}
 return raw,{'path':'tests/case.py','source_sha256':roles.digest(raw),'sites':[site]}

PEER=["record.strain_id = '{p}'\n","record['strain_id'] = '{p}'\n","strain_id, label = '{p}', 'fixture'\n"]
@pytest.mark.parametrize('source',PEER)
def test_peer_assignment_identity_values_refuse(source):
 raw,record=entry(source)
 with pytest.raises(ValueError,match='public role context'):roles.bound_sites(raw,record,public,allowed)

@pytest.mark.parametrize('source',[
 "record.STRAIN_ID: str = '{p}'\n","record['STRAIN_ID']: str = '{p}'\n",
 "[strain_id, label] = ['{p}', 'fixture']\n","label, (sample_id, product) = 'fixture', ('{p}', 'other')\n",
 "strain_id, label = pair('{p}')\n","*strain_id, product = ['{p}', 'other']\n",
 "record[selected_key] = '{p}'\n","record[0] = '{p}'\n",
 "strain_id = product = '{p}'\n","strain_id += '{p}'\n","(strain_id := '{p}')\n",
 "strain_id = '{p}'\n","f(strain_id='{p}')\n","record = dict(strain_id='{p}')\n",
 "record = {{'strain_id': '{p}'}}\n",
])
def test_other_identity_or_ambiguous_destinations_refuse(source):
 raw,record=entry(source)
 with pytest.raises(ValueError,match='public role context'):roles.bound_sites(raw,record,public,allowed)

POSITIVE=["product = '{p}'\n","record.product = '{p}'\n","record['product'] = '{p}'\n",
          "strain_id, product = 'SELF_AUTHORED_FIXTURE', '{p}'\n",
          "label, (strain_id, product) = 'fixture', ('SELF_AUTHORED_FIXTURE', '{p}')\n",
          "[strain_id, product] = ['SELF_AUTHORED_FIXTURE', '{p}']\n"]
@pytest.mark.parametrize('source',POSITIVE)
def test_genuine_product_and_separate_position_remain_public(source):
 raw,record=entry(source);assert roles.bound_sites(raw,record,public,allowed)

def miniature(tmp_path,source):
 raw,record=entry(source);root=tmp_path/'source';(root/'tests').mkdir(parents=True);(root/'tools').mkdir()
 (root/'tests/case.py').write_bytes(raw)
 for rel in ['tools/synthetic_id_registry_guard.py','tools/test_public_reference_tokens.json','tools/test_synthetic_ids.txt']:
  shutil.copyfile(ROOT/rel,root/rel)
 manifest={'schema':roles.SCHEMA,'public_reference_catalog_sha256':roles.digest(catalog),
           'canonical_declarations_sha256':roles.digest((ROOT/'tools/test_synthetic_ids.txt').read_bytes()),
           'identity_normalizer_sha256':roles.digest((ROOT/'tools/synthetic_id_registry_guard.py').read_bytes()),'files':[record]}
 (root/roles.POLICY).write_text(json.dumps(manifest));return root,raw

@pytest.mark.parametrize('source',PEER+POSITIVE[-3:])
def test_source_compatibility_production_library_and_CLI_agree(tmp_path,source):
 root,raw=miniature(tmp_path,source);expected=source in POSITIVE
 shim=importlib.util.spec_from_file_location('selected_source_shim',ROOT/'tests/_identifier_role_policy.py')
 consumer=importlib.util.module_from_spec(shim);shim.loader.exec_module(consumer)
 assert bool(consumer.reviewed_public_sites(root,root/'tests/case.py',raw,root/roles.POLICY)) is expected
 record=roles.audit_test_identifiers(root,root,roles.digest((root/roles.POLICY).read_bytes()))
 result=subprocess.run([sys.executable,'-B',str(ROOT/'tools/identifier_source_roles.py'),'--source-root',str(root),
                        '--stage-root',str(root),'--policy-sha256',roles.digest((root/roles.POLICY).read_bytes()),
                        '--receipt-stdout'],capture_output=True,text=True,timeout=10)
 assert (record['state']=='PASS_SOURCE_ROLE_SCOPE') is expected
 assert (result.returncode==0) is expected and json.loads(result.stdout)==record and not result.stderr
 assert record['artifact_export_permission'] is False

"""Invented portable controls for configured-check scope; no real vocabulary or registry."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
TOOL=Path(os.environ.get('PRIVATE_VOCAB_AUDIT_TOOL',str(ROOT/'tools/public_release_audit.py')))

def tree(tmp_path):
    root=tmp_path/'tree';(root/'mamey').mkdir(parents=True)
    (root/'mamey/__init__.py').write_text('__version__="1.0.0"\n')
    (root/'BUILD_STAMP.txt').write_text('build=invented\n')
    (root/'docs').mkdir()
    return root

def profile(tmp_path, marker=None):
    p=tmp_path/'operator_policy.json'
    p.write_text(json.dumps({'schema_version':'sapote_privacy_profile_v1',
        'profile_id':'invented-coverage','default_tier':'INTERNAL',
        'tiers':[{'tier_id':'INTERNAL','public_export':False}],'strain_assignments':[],
        'public_export_policy':{'private_identifiers':([] if marker is None else
            [{'identifier_id':'invented-private-marker','literal':marker}])}}))
    return p

def run(root, selected=None):
    args=[sys.executable,'-B',str(TOOL),str(root),'--report-json']
    if selected is not None:args+=['--privacy-profile',str(selected)]
    return subprocess.run(args,capture_output=True,text=True,timeout=15)

def coverage(result):
    return json.loads(next(line for line in result.stdout.splitlines() if line.startswith('{')))['private_vocabulary_coverage']

@pytest.mark.parametrize('empty_profile',[False,True])
def test_absent_or_empty_custom_vocabulary_is_explicitly_not_evaluated(tmp_path,empty_profile):
    root=tree(tmp_path);(root/'docs/labels.txt').write_text('AS-705\tNRPS\n')
    result=run(root,profile(tmp_path) if empty_profile else None)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'GENERIC PUBLIC CHECKS: PASS' in result.stdout
    assert 'CUSTOM PRIVATE VOCABULARY: NOT_EVALUATED' in result.stdout
    assert 'whole-tree scan clean' not in result.stdout
    assert coverage(result)=={'status':'NOT_EVALUATED','configured_literal_count':0}
    assert (root/'docs/labels.txt').read_text()=='AS-705\tNRPS\n'

def test_selected_clean_vocabulary_reports_its_bounded_pass(tmp_path):
    root=tree(tmp_path);result=run(root,profile(tmp_path,'INVENTED_PRIVATE_LITERAL'))
    assert result.returncode==0,result.stdout+result.stderr
    assert 'GENERIC PUBLIC CHECKS: PASS' in result.stdout
    assert 'CUSTOM PRIVATE VOCABULARY: PASS (configured literals checked)' in result.stdout
    assert coverage(result)=={'status':'PASS','configured_literal_count':1}

@pytest.mark.parametrize('relative',['docs/note.txt','tests/test_fixture.py','tools/public_release_audit.py'])
def test_selected_profile_detects_invented_literal_without_self_exemptions(tmp_path,relative):
    root=tree(tmp_path);marker='INVENTED_PRIVATE_LITERAL';p=root/relative
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(marker+'\n')
    result=run(root,profile(tmp_path,marker))
    assert result.returncode==1
    assert 'PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_CONTENT: invented-private-marker:' in result.stdout
    assert marker not in result.stdout+result.stderr
    assert 'GENERIC PUBLIC CHECKS: PASS' not in result.stdout

@pytest.mark.parametrize('relative,text,expected',[
    ('docs/note.txt','/Users/invented_owner/private.tsv\n','personal path'),
    ('mamey/data/strain_genus.csv','invented,Unassigned\n','cohort roster ships'),
    ('OFFICIAL_DATA/exclusions.json','{}\n','cohort exclusions payload ships'),
])
def test_unrequested_vocabulary_does_not_disable_generic_refusals(tmp_path,relative,text,expected):
    root=tree(tmp_path);p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    result=run(root)
    assert result.returncode==1 and expected in result.stdout

def test_invalid_selected_profile_still_refuses(tmp_path):
    root=tree(tmp_path);p=tmp_path/'invalid.json';p.write_text('{}')
    result=run(root,p)
    assert result.returncode==2 and 'invalid privacy profile' in result.stdout

def test_current_container_scope_and_adjacent_path_guards_survive():
    spec=importlib.util.spec_from_file_location('coverage_container_audit',TOOL)
    api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
    path='/home/mnt/gbk/*.gbk';relative='docs/history/retired_458/RIPPER_ARCHIVED_LOCAL_CONTRACT.md'
    assert not api._personal_path_in_line('container `'+path+'`',relative)
    for text,rel in [('container `'+path+'`','docs/OTHER.md'),
                     ('container `'+path+'.backup`',relative),
                     ('container `'+path+'/../private`',relative),
                     ('container `'+path+'`; personal /Users/invented_owner/work',relative)]:
        assert api._personal_path_in_line(text,rel)

"""Synthetic regression cases for derivation and complete archive enumeration.

Direct import overlay tests; baseline imports are read-only under -B. No full bundle copy.
"""
import importlib.util
import os
from pathlib import Path
import sys
import zipfile

import pytest

ROOT=Path(__file__).resolve().parents[1]
BASE=Path(os.environ.get('LANE10_BASE',str(ROOT)))
TOOLS=Path(os.environ.get('LANE10_TOOLS',str(ROOT/'tools')))
sys.path[:0]=[str(TOOLS),str(BASE/'tools'),str(BASE)]

def load(name):
    spec=importlib.util.spec_from_file_location('lane10_'+name,TOOLS/(name+'.py'))
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

@pytest.fixture
def pair(tmp_path):
    private=tmp_path/'private'; public=tmp_path/'public'
    private.mkdir(); public.mkdir()
    return private,public

def derive(pair,monkeypatch):
    mod=load('verify_tier_derivation')
    monkeypatch.setattr(sys,'argv',['verify_tier_derivation.py',*map(str,pair)])
    return mod.main()

@pytest.mark.parametrize('name',['README.md','mamey/code.py','tests/fixture.txt'])
def test_invalid_utf8_cannot_be_discarded(pair,monkeypatch,name):
    for root,data in zip(pair,[b'public text\n',b'public text\xff\n']):
        p=root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)
    assert derive(pair,monkeypatch)!=0

@pytest.mark.parametrize('contents',[(b'a\r\nb\r\n',b'a\nb\n'),(b'a\rb\r',b'a\nb\n')])
def test_identity_files_keep_newline_bytes(pair,monkeypatch,contents):
    for root,data in zip(pair,contents):
        (root/'tests').mkdir(); (root/'tests/fixture.txt').write_bytes(data)
    assert derive(pair,monkeypatch)!=0

def test_nested_metadata_basename_is_governed(pair,monkeypatch):
    for root,data in zip(pair,['source\n','changed\n']):
        (root/'docs').mkdir(); (root/'docs/BUILD_STAMP.txt').write_text(data)
    assert derive(pair,monkeypatch)!=0

def test_exact_metadata_path_is_exempt(pair,monkeypatch):
    for root,data in zip(pair,['source\n','regenerated\n']):
        (root/'docs').mkdir(); (root/'docs/BUNDLE_CAPABILITIES.md').write_text(data)
    assert derive(pair,monkeypatch)==0

def test_clean_text_still_passes(pair,monkeypatch):
    for root in pair: (root/'README.md').write_text('public text\n')
    assert derive(pair,monkeypatch)==0

@pytest.mark.parametrize('root_kind',['missing','file','symlink'])
def test_archive_scan_invalid_root_is_incomplete(tmp_path,root_kind):
    root=tmp_path/'root'
    if root_kind=='file': root.write_text('not directory')
    if root_kind=='symlink':
        target=tmp_path/'target'; target.mkdir(); root.symlink_to(target,target_is_directory=True)
    findings,count=load('archive_leak_scan').scan_tree(root,denylist=[])
    assert count==0
    assert findings and any(f['kind'] not in load('archive_leak_scan').LEAK_KINDS for f in findings)

def test_archive_scan_symlink_directory_is_incomplete(tmp_path):
    root=tmp_path/'root'; root.mkdir(); outside=tmp_path/'outside'; outside.mkdir()
    (root/'hidden').symlink_to(outside,target_is_directory=True)
    findings,count=load('archive_leak_scan').scan_tree(root,denylist=[])
    assert count==0
    assert any(f['kind']=='directory_symlink' for f in findings)

def test_archive_scan_walk_error_is_incomplete(tmp_path,monkeypatch):
    mod=load('archive_leak_scan')
    def broken_walk(root,**kwargs):
        callback=kwargs.get('onerror')
        if callback: callback(PermissionError(13,'denied',str(root/'blocked')))
        return iter([])
    monkeypatch.setattr(mod.os,'walk',broken_walk)
    findings,count=mod.scan_tree(tmp_path,denylist=[])
    assert count==0
    assert any(f['kind']=='tree_walk_error' for f in findings)

def test_archive_scan_clean_archive_and_cache_exclusion(tmp_path):
    with zipfile.ZipFile(tmp_path/'clean.ZIP','w') as z: z.writestr('notes.txt','public text')
    cache=tmp_path/'__pycache__'; cache.mkdir(); (cache/'bad.zip').write_bytes(b'not zip')
    findings,count=load('archive_leak_scan').scan_tree(tmp_path,denylist=[])
    assert count==1 and findings==[]

def test_archive_scan_archive_symlink_still_incomplete(tmp_path):
    (tmp_path/'bad.zip').symlink_to(tmp_path/'missing.zip')
    findings,count=load('archive_leak_scan').scan_tree(tmp_path,denylist=[])
    assert count==1 and findings[0]['kind']=='archive_symlink'


@pytest.mark.parametrize('source_ending',[b'\r\n',b'\r'])
def test_documentation_comparison_keeps_existing_newline_semantics(pair,monkeypatch,source_ending):
    # Names/classes are preserved; only documentation line endings are normalized for comparison.
    source=b'cohort AS-999\tNRPS'+source_ending
    staged=b'cohort AS-999\tNRPS\n'
    (pair[0]/'README.md').write_bytes(source)
    (pair[1]/'README.md').write_bytes(staged)
    assert derive(pair,monkeypatch)==0
    assert (pair[0]/'README.md').read_bytes()==source
    assert (pair[1]/'README.md').read_bytes()==staged


@pytest.mark.parametrize('staged',[b'cohort AS-XXX\tNRPS\n',b'cohort AS-999\tPKS\n',None])
def test_documentation_name_class_or_missing_file_remains_drift(pair,monkeypatch,staged):
    source=b'cohort AS-999\tNRPS\r\n'
    (pair[0]/'README.md').write_bytes(source)
    if staged is not None:(pair[1]/'README.md').write_bytes(staged)
    assert derive(pair,monkeypatch)!=0
    assert (pair[0]/'README.md').read_bytes()==source
    if staged is not None:assert (pair[1]/'README.md').read_bytes()==staged


def test_clean_unicode_documentation_still_passes(pair,monkeypatch):
    for root in pair: (root/'README.md').write_text('Sapote–Mamey public text\n',encoding='utf-8')
    assert derive(pair,monkeypatch)==0


@pytest.mark.parametrize('duplicate',['./a.txt','a.txt','././a.txt'])
def test_tier_manifest_duplicate_normalized_rows_fail(tmp_path,duplicate):
    import hashlib
    (tmp_path/'a.txt').write_text('public fixture\n')
    (tmp_path/'BUILD_STAMP.txt').write_text('build=fixture\n')
    (tmp_path/'TIER_MANIFEST.txt').write_text('# TIER_MANIFEST tier=code version=fixture stamp=fixture\n./a.txt\n./BUILD_STAMP.txt\n'+duplicate+'\n')
    (tmp_path/'SOURCE_CHECKSUMS_SHA256.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  ./'+p.name+'\n' for p in sorted(tmp_path.iterdir())))
    mod=load('check_release_manifest')
    assert mod.check(tmp_path)!=0
    assert any('duplicate normalized' in p for p in mod.membership_problems(tmp_path))

"""Run only shared preflight functions on temporary generic roots.
Never execute release_cut.sh, make_public_tier.sh or a build.
"""
from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT/'tools/cut_preflight.sh'

def run(function, root):
    return subprocess.run(['bash','-c','source "$1"; "$2" "$3"', 'fixture',str(HELPER),function,str(root)],capture_output=True,text=True)

@pytest.mark.parametrize('name',['REVIEW_CANDIDATE_README.md','REVIEW_CANDIDATE_TEST_RESULT.txt','PROPOSED_FIXES.md','PROPOSED_FIXES_extra.md'])
def test_review_root_is_refused_without_changing_it(tmp_path,name):
    p=tmp_path/name;p.write_text('preserved evidence')
    result=run('sapote_assert_no_review_root',tmp_path)
    assert result.returncode!=0 and name in result.stderr
    assert p.read_text()=='preserved evidence'

def test_nested_review_archive_and_regular_source_are_allowed(tmp_path):
    (tmp_path/'archive').mkdir();(tmp_path/'archive/PROPOSED_FIXES.md').write_text('historical')
    (tmp_path/'README.md').write_text('source')
    assert run('sapote_assert_no_review_root',tmp_path).returncode==0

def test_dangling_review_symlink_is_refused(tmp_path):
    (tmp_path/'REVIEW_CANDIDATE_link').symlink_to(tmp_path/'absent')
    assert run('sapote_assert_no_review_root',tmp_path).returncode!=0

def test_bytecode_purge_is_bounded_to_working_root(tmp_path):
    root=tmp_path/'candidate';root.mkdir();external=tmp_path/'retained';external.mkdir()
    (external/'kept.pyc').write_bytes(b'outside')
    (root/'nested/__pycache__').mkdir(parents=True)
    (root/'nested/__pycache__/old.pyc').write_bytes(b'cache')
    (root/'loose.pyo').write_bytes(b'cache');(root/'engine.py').write_text('source')
    assert run('sapote_purge_cut_bytecode',root).returncode==0
    assert not (root/'nested/__pycache__').exists() and not (root/'loose.pyo').exists()
    assert (root/'engine.py').read_text()=='source' and (external/'kept.pyc').read_bytes()==b'outside'
    assert run('sapote_purge_cut_bytecode',root).returncode==0

def test_cache_symlink_is_held_and_external_content_preserved(tmp_path):
    root=tmp_path/'candidate';root.mkdir();external=tmp_path/'retained';external.mkdir()
    (external/'kept.pyc').write_bytes(b'outside');(root/'__pycache__').symlink_to(external,target_is_directory=True)
    result=run('sapote_purge_cut_bytecode',root)
    assert result.returncode!=0 and 'symlink' in result.stderr
    assert (external/'kept.pyc').read_bytes()==b'outside' and (root/'__pycache__').is_symlink()

def test_source_only_helper_and_script_syntax():
    for rel in ['tools/cut_preflight.sh','tools/release_cut.sh','tools/make_public_tier.sh']:
        assert subprocess.run(['bash','-n',str(ROOT/rel)],capture_output=True).returncode==0
    release=(ROOT/'tools/release_cut.sh').read_text()
    assert release.index('sapote_purge_cut_bytecode "$SRC"') < release.index('python3 tools/rewrite_release_identity.py')
    tier=(ROOT/'tools/make_public_tier.sh').read_text()
    assert tier.index('sapote_assert_no_review_root "$SRC"') < tier.index('WORK="$(mktemp -d)"')

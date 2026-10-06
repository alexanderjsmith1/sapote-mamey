"""Only the common staging block is executed; never cut/seal/archive a candidate."""
from pathlib import Path
import importlib.util
import os
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path(os.environ.get('SAPOTE_NOTE_CLEANUP_BASELINE', ROOT))
NOTE = 'tools/upstream_gtotree2/NOTE_TO_GTOTREE_AUTHOR.md'
PATCH = 'tools/upstream_gtotree2/gtotree2-input-sanity-and-env-compat.patch'
NEUTRAL = 'tools/upstream_gtotree2/COMPATIBILITY_PATCH_NOTES.md'


@pytest.mark.parametrize('tier', ['code', 'clean', 'cohort', 'merged', 'public', 'sid'])
def test_common_staging_excludes_exact_note_and_preserves_source_patch_and_other_notes(tmp_path, tier):
    source = tmp_path / 'source'
    source.mkdir()
    keep = [PATCH, NEUTRAL, 'tools/upstream_gtotree2/OTHER_AUTHOR_NOTE.md', 'docs/NOTE_TO_GTOTREE_AUTHOR.md']
    for path in [NOTE, *keep]:
        p = source / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('synthetic fixture: ' + path)
    stage = tmp_path / 'stage'
    shutil.copytree(source, stage)
    script = (ROOT / 'tools/make_public_tier.sh').read_text()
    begin = '# BEGIN COMMON CORRESPONDENCE EXCLUSION'
    end = '# END COMMON CORRESPONDENCE EXCLUSION'
    assert script.index(begin) > script.index('cp -a "$SRC/." "$STAGE/"')
    assert script.index(end) < script.index('# --- 1. strip files by tier')
    block = script.split(begin, 1)[1].split(end, 1)[0]
    result = subprocess.run(['bash', '-eu', '-c', block],
                            env={**os.environ, 'STAGE': str(stage), 'TIER': tier},
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert not (stage / NOTE).exists()
    assert (source / NOTE).read_text() == 'synthetic fixture: ' + NOTE
    for path in keep:
        assert (stage / path).read_bytes() == (source / path).read_bytes()


def test_derivation_omission_is_exact_and_preserves_real_patch_and_other_notes():
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(BASELINE))
    sys.path.insert(0, str(BASELINE / 'tools'))
    spec = importlib.util.spec_from_file_location('cleanup_derivation', ROOT / 'tools/verify_tier_derivation.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module._is_stripped(NOTE)
    assert module._is_stripped('./' + NOTE)
    assert not module._is_stripped(PATCH)
    assert not module._is_stripped(NEUTRAL)
    assert not module._is_stripped('tools/upstream_gtotree2/NOTE_TO_GTOTREE_AUTHOR.md.extra')
    assert not module._is_stripped('docs/NOTE_TO_GTOTREE_AUTHOR.md')


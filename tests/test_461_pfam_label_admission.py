"""Software-only input admission controls for the Pfam description map."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

TOOL = Path(__file__).resolve().parents[1] / 'tools' / 'build_pfam_desc_map.py'
HMM = 'NAME  Alpha\nACC   PF0001\nDESC  first\n//\nNAME  Beta\nACC   PF0002\nDESC  second\n//\n'


def run(*args):
    return subprocess.run([sys.executable, '-B', str(TOOL), *map(str, args)], text=True, capture_output=True)


@pytest.mark.parametrize('kind', ['missing', 'directory', 'invalid_utf8'])
def test_unusable_supplied_labels_refused_without_touching_output(tmp_path, kind):
    hmm = tmp_path / 'test.hmm'
    hmm.write_text(HMM)
    labels = tmp_path / 'labels'
    if kind == 'directory':
        labels.mkdir()
    elif kind == 'invalid_utf8':
        labels.write_bytes(b'\xff')
    outdir = tmp_path / 'out'
    outdir.mkdir()
    output = outdir / 'pfam_desc_map.json'
    output.write_bytes(b'original output\n')
    result = run('--hmm', hmm, '--out', outdir, '--labels', labels)
    assert result.returncode != 0
    assert output.read_bytes() == b'original output\n'


def test_selection_empty_and_unrestricted_are_distinct(tmp_path):
    hmm = tmp_path / 'test.hmm'
    hmm.write_text(HMM)
    labels = tmp_path / 'labels'
    outdir = tmp_path / 'out'
    labels.write_text('Beta\n')
    result = run('--hmm', hmm, '--out', outdir, '--labels', labels)
    assert result.returncode == 0, result.stderr
    output = outdir / 'pfam_desc_map.json'
    assert json.loads(output.read_text()) == {'Beta': {'acc': 'PF0002', 'desc': 'second'}}
    labels.write_text('')
    assert run('--hmm', hmm, '--out', outdir, '--labels', labels).returncode == 0
    assert json.loads(output.read_text()) == {}
    assert run('--hmm', hmm, '--out', outdir).returncode == 0
    assert set(json.loads(output.read_text())) == {'Alpha', 'Beta'}


@pytest.mark.parametrize('source_kind', ['hmm', 'labels'])
@pytest.mark.parametrize('alias_kind', ['direct', 'symlink', 'hardlink'])
def test_output_alias_refused_without_changing_input(tmp_path, source_kind, alias_kind):
    outdir = tmp_path / 'out'
    outdir.mkdir()
    output = outdir / 'pfam_desc_map.json'
    hmm, labels = tmp_path / 'test.hmm', tmp_path / 'labels'
    source = output if alias_kind == 'direct' else tmp_path / 'input'
    if source_kind == 'hmm':
        hmm = source
    else:
        labels = source
    hmm.write_text(HMM)
    labels.write_text('Alpha\n')
    original = source.read_bytes()
    if alias_kind == 'symlink':
        output.symlink_to(source)
    elif alias_kind == 'hardlink':
        os.link(source, output)
    result = run('--hmm', hmm, '--out', outdir, '--labels', labels)
    assert result.returncode != 0
    assert source.read_bytes() == original

@pytest.mark.parametrize('kind', ['missing', 'directory'])
def test_unusable_hmm_refused_before_output_creation(tmp_path, kind):
    hmm = tmp_path / 'input.hmm'
    if kind == 'directory':
        hmm.mkdir()
    outdir = tmp_path / 'out'
    result = run('--hmm', hmm, '--out', outdir)
    assert result.returncode != 0
    assert not outdir.exists()

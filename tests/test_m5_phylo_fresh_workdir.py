"""Fresh genome execution admission; all inputs are tiny synthetic files."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest
from tools import run_planned_tree as runner
from ._trees_432_fakes import native_tree_tmp_path  # scoped lifecycle-inventoried /private/tmp fixture

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root):
    return {str(p.relative_to(root)): (p.stat().st_mode, hashlib.sha256(p.read_bytes()).hexdigest())
            for p in root.rglob('*') if p.is_file() and not p.is_symlink()}


def inputs(root):
    genome = root / 'synthetic.fna'; genome.write_text('>synthetic\nACGT\n')
    listing = root / 'genomes.txt'; listing.write_text(str(genome) + '\n')
    return genome, listing


def test_occupied_workdir_refuses_before_binary_probe_and_preserves_bytes(tmp_path, monkeypatch, capsys):
    _, listing = inputs(tmp_path)
    out = tmp_path / 'work'; (out / 'gtotree').mkdir(parents=True)
    (out / 'gtotree' / 'aligned-SCGs.faa').write_text('prior alignment')
    (out / 'run_planned_tree.log').write_text('prior log')
    (out / 'unrelated.txt').write_text('unrelated evidence')
    before = snapshot(tmp_path)
    monkeypatch.setattr(runner, '_resolve', lambda *a: pytest.fail('probe must not run'))
    rc = runner.main(['--genome-list', str(listing), '--workdir', str(out), '--outgroup', 'OG', '--approved'])
    assert rc == 2 and 'WORKDIR_OCCUPIED' in capsys.readouterr().err
    assert snapshot(tmp_path) == before


def test_actual_cli_occupied_output_refuses_without_deleting_prior_evidence(tmp_path):
    _, listing = inputs(tmp_path)
    out = tmp_path / 'work'; (out / 'gtotree').mkdir(parents=True)
    (out / 'gtotree' / 'old.txt').write_text('keep')
    before = snapshot(tmp_path)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, str(ROOT / 'mamey_run.py'), 'phylo-run',
        '--genome-list', str(listing), '--workdir', str(out), '--outgroup', 'OG', '--approved'],
        cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 2, result.stdout + result.stderr
    assert 'WORKDIR_OCCUPIED' in result.stderr
    assert snapshot(tmp_path) == before


def test_symlink_output_or_ancestor_refuses_without_touching_target(tmp_path):
    genome, _ = inputs(tmp_path)
    target = tmp_path / 'retained'; target.mkdir(); (target / 'keep.txt').write_text('keep')
    link = tmp_path / 'linked'; link.symlink_to(target, target_is_directory=True)
    before = snapshot(tmp_path)
    for out in (link, link / 'new'):
        with pytest.raises(ValueError, match='WORKDIR_SYMLINK'):
            runner.preflight_fresh_workdir(str(out), [genome])
    assert snapshot(tmp_path) == before and not (target / 'new').exists()


def test_late_missing_selected_input_refuses_before_any_output(tmp_path, monkeypatch, capsys):
    _, listing = inputs(tmp_path); out = tmp_path / 'new'
    monkeypatch.setattr(runner, '_resolve', lambda *a: pytest.fail('probe must not run'))
    rc = runner.main(['--genome-list', str(listing), '--workdir', str(out), '--outgroup', 'OG',
                      '--tree-spec', str(tmp_path / 'missing.json'), '--approved'])
    assert rc == 2 and not out.exists()
    assert 'REFUSED' in capsys.readouterr().err


def test_invalid_tree_spec_refuses_before_probe_or_output(tmp_path, monkeypatch, capsys):
    _, listing = inputs(tmp_path); out = tmp_path / 'new'
    spec = tmp_path / 'spec.json'; spec.write_text('[]')
    monkeypatch.setattr(runner, '_resolve', lambda *a: pytest.fail('probe must not run'))
    rc = runner.main(['--genome-list', str(listing), '--workdir', str(out), '--outgroup', 'OG',
                      '--tree-spec', str(spec), '--approved'])
    assert rc == 2 and 'TREE_SPEC_INVALID' in capsys.readouterr().err and not out.exists()


def test_fresh_admission_creates_nothing_and_refuses_input_as_parent(tmp_path):
    genome, listing = inputs(tmp_path); out = tmp_path / 'new'
    assert runner.preflight_fresh_workdir(str(out), [genome, listing]) == str(out)
    assert not out.exists()
    with pytest.raises(ValueError, match='WORKDIR_PARENT_NOT_DIRECTORY'):
        runner.preflight_fresh_workdir(str(genome / 'new'), [listing])


def test_fresh_main_preserves_current_failure_and_never_deletes(tmp_path, monkeypatch):
    _, listing = inputs(tmp_path); hmm = tmp_path / 'markers.hmm'; hmm.write_text('HMMER3/f\n')
    out = tmp_path / 'new'
    monkeypatch.delenv('Pfam_data_dir', raising=False)
    monkeypatch.setattr(runner, '_resolve', lambda names: '/fake/' + names[0])
    monkeypatch.setattr(runner, 'gtotree_probe', lambda path: {
        'status': 'PRESENT', 'version': 'GToTree v1.8.19', 'normalized_version': '1.8.19',
        'major': 1, 'profile': '1.8.19', 'version_exit': 0, 'help_exit': 0,
        'help_contract': 'PASS', 'verified_interface': 'PASS', 'missing_help_tokens': []})
    def failed_command(cmd, log, env):
        assert not (out / 'gtotree').exists()
        assert Path(env['Pfam_data_dir']).is_dir()
        return 9
    monkeypatch.setattr(runner, 'run', failed_command)
    rc = runner.main(['--genome-list', str(listing), '--workdir', str(out), '--hmm', str(hmm),
                      '--outgroup', 'OG', '--approved'])
    assert rc == 4
    import json
    status = json.loads((out / 'run_status.json').read_text())
    assert status['status'] == 'GTOTREE_FAILED' and status['gtotree_rc'] == 9
    assert (out / 'run_planned_tree.log').is_file()


def test_existing_empty_workdir_is_not_an_implicit_resume(tmp_path, monkeypatch, capsys):
    _, listing = inputs(tmp_path); out = tmp_path / 'empty'; out.mkdir()
    monkeypatch.setattr(runner, '_resolve', lambda *a: pytest.fail('probe must not run'))
    before = snapshot(tmp_path)
    assert runner.main(['--genome-list', str(listing), '--workdir', str(out), '--outgroup', 'OG', '--approved']) == 2
    assert 'WORKDIR_OCCUPIED' in capsys.readouterr().err
    assert snapshot(tmp_path) == before and list(out.iterdir()) == []


def test_late_ani_input_failure_creates_no_parents(tmp_path, monkeypatch, capsys):
    _, listing = inputs(tmp_path); out = tmp_path / 'parent_not_created' / 'new'
    ani = tmp_path / 'ani.txt'; ani.write_text(str(tmp_path / 'missing.fna') + '\n')
    monkeypatch.setattr(runner, '_resolve', lambda *a: pytest.fail('probe must not run'))
    before = snapshot(tmp_path)
    assert runner.main(['--genome-list', str(listing), '--workdir', str(out), '--outgroup', 'OG',
                        '--ani-refs', str(ani), '--approved']) == 2
    assert 'ANI_INPUT_GENOME_FILE_MISSING' in capsys.readouterr().err
    assert snapshot(tmp_path) == before and not out.parent.exists()


def test_inherited_missing_pfam_directory_is_not_created(tmp_path, monkeypatch, capsys):
    _, listing = inputs(tmp_path); hmm = tmp_path / 'markers.hmm'; hmm.write_text('HMMER3/f\n')
    out = tmp_path / 'new'; pfam = tmp_path / 'external_missing'
    monkeypatch.setenv('Pfam_data_dir', str(pfam))
    monkeypatch.setattr(runner, '_resolve', lambda names: '/fake/' + names[0])
    monkeypatch.setattr(runner, 'gtotree_probe', lambda path: {
        'status': 'PRESENT', 'version': 'GToTree v1.8.19', 'normalized_version': '1.8.19',
        'major': 1, 'profile': '1.8.19', 'version_exit': 0, 'help_exit': 0,
        'help_contract': 'PASS', 'verified_interface': 'PASS', 'missing_help_tokens': []})
    monkeypatch.setattr(runner, 'run', lambda *a: pytest.fail('command must not run'))
    before = snapshot(tmp_path)
    assert runner.main(['--genome-list', str(listing), '--workdir', str(out), '--hmm', str(hmm),
                        '--outgroup', 'OG', '--approved']) == 2
    assert 'PFAM_INPUT_DIRECTORY_MISSING' in capsys.readouterr().err
    assert snapshot(tmp_path) == before and not out.exists() and not pfam.exists()

"""Adversarial controls for candidate transaction recovery and release profiles."""
import importlib.util
import json
from pathlib import Path

import pytest
from mamey import blastp_ingest as bi

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('level', ['root', 'transaction'])
def test_recovery_never_follows_transaction_symlinks(tmp_path, level):
    package = tmp_path / 'package'
    package.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    victim = outside / 'keep.txt'
    victim.write_text('preserve')
    (outside / 'journal.json').write_text(json.dumps({'state': 'COMMITTED'}))
    root = package / bi._FILESET_TXN_DIR
    if level == 'root':
        outer = tmp_path / 'outer'
        outer.mkdir()
        (outer / 'one').symlink_to(outside, target_is_directory=True)
        root.symlink_to(outer, target_is_directory=True)
    else:
        root.mkdir()
        (root / 'one').symlink_to(outside, target_is_directory=True)
    with pytest.raises(bi.BlastpFileSetCommitError, match='RECOVERY_HOLD'):
        bi._recover_fileset_transactions(package)
    assert victim.read_text() == 'preserve'


@pytest.mark.parametrize('value', [[], None, 'bad', {'state': 'PREPARED', 'targets': [{}]}])
def test_malformed_recovery_journal_is_a_typed_hold(tmp_path, value):
    package = tmp_path / 'package'
    txn = package / bi._FILESET_TXN_DIR / 'one'
    txn.mkdir(parents=True)
    (txn / 'journal.json').write_text(json.dumps(value))
    with pytest.raises(bi.BlastpFileSetCommitError, match='RECOVERY_HOLD'):
        bi._recover_fileset_transactions(package)


def test_recovery_preflights_every_backup_before_modifying_targets(tmp_path):
    package = tmp_path / 'package'
    txn = package / bi._FILESET_TXN_DIR / 'one'
    txn.mkdir(parents=True)
    first = package / 'first.csv'
    first.write_text('current')
    outside = tmp_path / 'outside.bin'
    outside.write_text('external')
    (txn / 'backup_0.bin').write_text('old')
    (txn / 'backup_1.bin').symlink_to(outside)
    entries = [dict(index=i, relative_path=f'{name}.csv', existed=True,
                    backup=f'backup_{i}.bin', staged='')
               for i, name in enumerate(['first', 'second'])]
    (txn / 'journal.json').write_text(json.dumps({'state':'PREPARED','targets':entries}))
    with pytest.raises(bi.BlastpFileSetCommitError, match='RECOVERY_HOLD'):
        bi._recover_fileset_transactions(package)
    assert first.read_text() == 'current'
    assert not (package / 'second.csv').exists()


def test_release_receipt_and_runner_require_all_configured_test_groups():
    spec = importlib.util.spec_from_file_location('receipt_profile', ROOT / 'tools/verify_external_validation_receipt.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    assert '--run-slow' in helper.COMMAND_TAIL
    assert '--run-network' in helper.COMMAND_TAIL
    command = next(line for line in (ROOT / 'tools/release_cut.sh').read_text().splitlines()
                   if 'if ! PYTHONPATH=. python3 -m pytest' in line)
    assert '--run-slow' in command and '--run-network' in command

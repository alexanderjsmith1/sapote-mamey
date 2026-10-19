"""Archive-shaped directories must retain lexical candidate classification."""
import importlib.util
import os
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get('LANE10_BASE', str(ROOT)))
sys.path[:0] = [str(ROOT/'tools'), str(BASE/'tools'), str(BASE)]


def scanner():
    path = Path(os.environ.get('LANE10_FOLLOWUP_SCANNER', str(ROOT/'tools/archive_leak_scan.py')))
    spec = importlib.util.spec_from_file_location('lane10_followup_scanner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_original_sol09_archive_candidate_case(tmp_path, monkeypatch):
    # Execute the original existing case unchanged, selecting only the isolated scanner.
    path = BASE/'tests/test_archive_policy_profile_sol09.py'
    spec = importlib.util.spec_from_file_location('lane10_sol09_compat', path)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    monkeypatch.setattr(original, '_load', lambda name: scanner())
    original.test_scan_tree_lexically_enumerates_every_archive_shaped_candidate(tmp_path)


@pytest.mark.parametrize('name', ['directory.zip', 'directory.ZIP', 'directory.docx'])
def test_archive_shaped_directory_is_counted_and_cli_incomplete(tmp_path, name, capsys):
    (tmp_path/name).mkdir()
    module = scanner()
    findings, count = module.scan_tree(tmp_path, denylist=[])
    assert count == 1
    assert [f['kind'] for f in findings] == ['archive_not_regular_file']
    assert module.main([str(tmp_path)]) == 2
    assert 'INCOMPLETE' in capsys.readouterr().out


def test_archive_named_directory_symlink_is_classified_without_following(tmp_path, monkeypatch):
    root = tmp_path/'root'; root.mkdir()
    target = tmp_path/'target'; target.mkdir()
    with zipfile.ZipFile(target/'nested.zip', 'w') as z:
        z.writestr('notes.txt', 'public fixture')
    (root/'directory.zip').symlink_to(target, target_is_directory=True)
    def forbidden_read(path):
        pytest.fail('directory symlink must not be read or followed')
    monkeypatch.setattr(Path, 'read_bytes', forbidden_read)
    findings, count = scanner().scan_tree(root, denylist=[])
    assert count == 1
    assert [f['kind'] for f in findings] == ['archive_symlink']


def test_regular_archive_named_directory_still_enumerates_child_candidates(tmp_path):
    container = tmp_path/'directory.zip'; container.mkdir()
    with zipfile.ZipFile(container/'child.zip', 'w') as z:
        z.writestr('notes.txt', 'public fixture')
    findings, count = scanner().scan_tree(tmp_path, denylist=[])
    assert count == 2
    assert [f['kind'] for f in findings] == ['archive_not_regular_file']

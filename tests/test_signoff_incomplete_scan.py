"""Advisory exit zero must not hide an incomplete inspection."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('signoff_incomplete', Path(__file__).resolve().parents[1] / 'tools/signoff_check.py')
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


def test_missing_root_is_visible_even_when_quiet(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sc.sys, 'argv', ['signoff_check', '--quiet-if-clean', '--root', str(tmp_path / 'missing')])
    assert sc.main() == 0
    assert 'incomplete' in capsys.readouterr().out.lower()


def test_walk_error_is_not_empty_success(tmp_path, monkeypatch):
    def broken_walk(root, **kwargs):
        callback = kwargs.get('onerror')
        if callback:
            callback(PermissionError('synthetic unreadable subtree'))
        return iter(())
    monkeypatch.setattr(sc.os, 'walk', broken_walk)
    with pytest.raises(OSError):
        sc.find_recent_trees(str(tmp_path), 90)


def test_explicit_unreadable_tree_is_visible_when_quiet(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sc.sys, 'argv', ['signoff_check', '--quiet-if-clean', str(tmp_path / 'missing.treefile')])
    assert sc.main() == 0
    assert 'could not parse' in capsys.readouterr().out


def test_tree_stat_error_is_not_empty_success(tmp_path, monkeypatch):
    (tmp_path / 'tree.treefile').write_text('(a:1,b:1);')
    def bad_stat(path):
        raise PermissionError('synthetic stat failure')
    monkeypatch.setattr(sc.os.path, 'getmtime', bad_stat)
    with pytest.raises(OSError):
        sc.find_recent_trees(str(tmp_path), 90)


def test_empty_readable_root_remains_quiet(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sc.sys, 'argv', ['signoff_check', '--quiet-if-clean', '--root', str(tmp_path)])
    assert sc.main() == 0
    assert capsys.readouterr().out == ''

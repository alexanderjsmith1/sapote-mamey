"""Scan exclusions refer to in-root metadata, never the user's parent folders."""
import importlib.util
from pathlib import Path
import pytest


@pytest.mark.parametrize('parent', ['parent.egg-info', '.git', '__pycache__', '.pytest_cache'])
def test_parent_name_cannot_hide_release_content(tmp_path, parent, monkeypatch):
    tools = Path(__file__).resolve().parents[1] / 'tools'
    monkeypatch.syspath_prepend(str(tools))
    spec = importlib.util.spec_from_file_location('public_audit_scope_test', tools/'public_release_audit.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    root = tmp_path / parent / 'release'
    (root/'mamey/data').mkdir(parents=True)
    (root/'mamey/__init__.py').write_text('__version__ = "1.0.0"\n')
    (root/'BUILD_STAMP.txt').write_text('build=20260907v97413a\n')
    (root/'docs').mkdir()
    (root/'docs/notes.md').write_bytes(b'\xff\xfe')
    assert any('undecodable' in h and 'notes.md' in h for h in audit.audit(root))

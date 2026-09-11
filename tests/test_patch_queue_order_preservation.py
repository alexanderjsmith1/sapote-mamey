from tests.test_patch_queue_composition_audit_v97412 import _load
import pytest


@pytest.mark.parametrize('before,after', [
    ('check()\nexecute()\n', 'execute()\ncheck()\n'),
    ('check()\ncheck()\nexecute()\n', 'check()\nexecute()\n'),
    ('text = """a\n\nb"""\n', 'text = """a\nb"""\n'),
])
def test_removed_or_reordered_occurrences_are_not_additions(tmp_path, before, after):
    sealed, dropped = tmp_path / 'before.py', tmp_path / 'after.py'
    sealed.write_text(before)
    dropped.write_text(after)
    mod = _load()
    assert mod.classify_drop(sealed, dropped)[0] == mod.CODE_REVERT


def test_identical_means_identical_bytes(tmp_path):
    sealed, dropped = tmp_path / 'before.py', tmp_path / 'after.py'
    sealed.write_bytes(b'x = 1\r\n')
    dropped.write_bytes(b'x = 1\n')
    mod = _load()
    assert mod.classify_drop(sealed, dropped)[0] != mod.CODE_SAME

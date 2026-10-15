import hashlib
import os
from pathlib import Path
import pytest
from mamey.postseal_output import package_binding
from mamey import packaging

@pytest.mark.parametrize("kind", ["missing", "file", "fifo", "root_symlink", "walk_error", "disappearing"])
def test_incomplete_or_nonregular_snapshot_is_not_a_binding(tmp_path, monkeypatch, kind):
    root = tmp_path / "package"
    if kind == "file":root.write_text("not a directory")
    elif kind != "missing":root.mkdir()
    if kind == "fifo": os.mkfifo(root / "special")
    if kind == "root_symlink":
        root.rmdir()
        other = tmp_path / "other"
        other.mkdir()
        (other / "evidence.txt").write_text("outside evidence")
        root.symlink_to(other, target_is_directory=True)
    if kind in ("walk_error", "disappearing"):
        def walk(path, onerror=None, **kwargs):
            if kind == "walk_error":onerror(PermissionError("synthetic unavailable subtree"))
            else:root.rmdir()
            return iter(())
        monkeypatch.setattr(packaging.os, "walk", walk)
    with pytest.raises((ValueError, OSError, packaging.PackageContainmentError)):
        package_binding(root)

def test_complete_nested_snapshot_keeps_exact_roster_and_digest(tmp_path):
    root = tmp_path / "package"
    (root / "nested").mkdir(parents=True)
    (root / "a.txt").write_bytes(b"a")
    (root / "nested/b.txt").write_bytes(b"b")
    result = package_binding(root)
    expected = {"a.txt": hashlib.sha256(b"a").hexdigest(), "nested/b.txt": hashlib.sha256(b"b").hexdigest()}
    assert result["files_sha256"] == expected
    assert result["package_tree_sha256"] == hashlib.sha256(''.join(f'{rel}\t{value}\n' for rel, value in expected.items()).encode()).hexdigest()

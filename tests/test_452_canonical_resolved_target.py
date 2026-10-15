from pathlib import Path
import pytest
from mamey.canonical_write_guard import guard_canonical_write, CanonicalOverwriteRefused

@pytest.mark.parametrize("kind", ["directory", "file"])
def test_existing_canonical_alias_is_refused(tmp_path, monkeypatch, kind):
    monkeypatch.delenv("MAMEY_ALLOW_CANONICAL_OVERWRITE", raising=False)
    canonical = tmp_path / "results_2026-01-01"
    canonical.mkdir()
    source = canonical / "data.txt"
    source.write_text("evidence")
    alias = tmp_path / "alias"
    alias.symlink_to(canonical if kind == "directory" else source)
    target = alias / source.name if kind == "directory" else alias
    with pytest.raises(CanonicalOverwriteRefused):
        guard_canonical_write(target)
    assert source.read_text() == "evidence"
    guard_canonical_write(target, force=True)
    guard_canonical_write(canonical / "new.txt")

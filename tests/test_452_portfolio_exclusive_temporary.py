import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from mamey.portfolio_config import write_portfolio_binding, PortfolioConfigError

@pytest.mark.parametrize("kind", ["hardlink", "symlink", "regular"])
def test_existing_temporary_evidence_is_never_truncated(tmp_path, kind):
    root = tmp_path / "project"
    output = root / "project_outputs"
    output.mkdir(parents=True)
    source = root / "source.tsv"
    outside = tmp_path / "outside.tsv"
    source.write_text("source evidence")
    outside.write_text("outside evidence")
    temporary = output / "portfolio_binding.tmp"
    if kind == "hardlink": os.link(outside, temporary)
    elif kind == "symlink": temporary.symlink_to(source)
    else: temporary.write_text("existing temporary evidence")
    before = {p: p.read_bytes() for p in (source, outside, temporary)}
    inode = temporary.stat().st_ino
    with pytest.raises(PortfolioConfigError, match="already exists"):
        write_portfolio_binding(root, SimpleNamespace(as_dict=lambda: {"schema": "synthetic"}))
    assert all(p.read_bytes() == value for p, value in before.items())
    assert temporary.stat().st_ino == inode
    assert not (output / "portfolio_binding.json").exists()

def test_fresh_binding_is_still_published(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    payload = {"schema": "synthetic"}
    result = write_portfolio_binding(root, SimpleNamespace(as_dict=lambda: payload))
    assert json.loads(result.read_text()) == payload
    assert not result.with_suffix(".tmp").exists()

def test_exclusive_create_refuses_an_alias_inserted_after_admission(tmp_path, monkeypatch):
    root = tmp_path / "project"
    (root / "project_outputs").mkdir(parents=True)
    outside = tmp_path / "outside.tsv"
    outside.write_text("outside evidence")
    original = Path.open
    def open_path(self, mode="r", *args, **kwargs):
        if self.name == "portfolio_binding.tmp" and mode == "x":
            os.link(outside, self)
        return original(self, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", open_path)
    with pytest.raises(FileExistsError):
        write_portfolio_binding(root, SimpleNamespace(as_dict=lambda: {"schema": "synthetic"}))
    assert outside.read_text() == "outside evidence"
    assert not (root / "project_outputs/portfolio_binding.json").exists()

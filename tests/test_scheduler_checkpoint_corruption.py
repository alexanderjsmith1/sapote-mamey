"""A damaged checkpoint is a hold, never permission to rebuild pending work."""
from pathlib import Path

import pytest

from mamey import blastp_autoharness as scheduler


@pytest.mark.parametrize("damage", ["truncated", "unreadable", "symlink", "nonobject", "invalid_utf8"])
def test_resume_checkpoint_damage_never_rebuilds_worklist(tmp_path, monkeypatch, damage):
    package = tmp_path / "package"
    path = scheduler.state_path(package)
    path.parent.mkdir(parents=True)
    if damage == "symlink":
        path.symlink_to(tmp_path / "missing-checkpoint")
    else:
        path.write_bytes({"nonobject": b"[]", "invalid_utf8": b"\xff"}.get(damage, b'{"strain":'))
    before = path.read_bytes() if damage != "symlink" else None
    if damage == "unreadable":
        original = Path.read_text
        def refusing(p, *args, **kwargs):
            if p == path:
                raise PermissionError("synthetic read refusal")
            return original(p, *args, **kwargs)
        monkeypatch.setattr(Path, "read_text", refusing)
    calls = []
    monkeypatch.setattr(scheduler, "build_worklist", lambda *a, **kw: calls.append("rebuilt") or [])
    with pytest.raises(ValueError, match="checkpoint"):
        scheduler.init_state(package, "SYNTHETIC", resume=True)
    assert calls == []
    if damage == "symlink":
        assert path.is_symlink()
    else:
        assert path.read_bytes() == before


def test_absent_checkpoint_can_initialize_new_queue(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler, "build_worklist", lambda *a, **kw: [])
    state = scheduler.init_state(tmp_path / "package", "SYNTHETIC", resume=True)
    assert state["strain"] == "SYNTHETIC" and state["n_submits"] == 0

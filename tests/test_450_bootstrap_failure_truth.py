"""Delegated bootstrap failure retains evidence without claiming zero writes."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_450_build_stamp_patch_admission import (
    _load_owner, _snapshot, _write_fixture,
)


@pytest.mark.parametrize("partial_output", [False, True])
def test_bootstrap_failure_reports_scope_and_keeps_anchors_unwritten(
    monkeypatch, tmp_path, capsys, partial_output
):
    owner = _load_owner(monkeypatch)
    _write_fixture(tmp_path)
    bootstrap_output = tmp_path / "docs" / "BOOTSTRAP_FILE_AUDIT.md"
    bootstrap_output.parent.mkdir()
    bootstrap_output.write_text("original bootstrap output\n", encoding="utf-8")
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner, "RULES", [
        ("BUILD_STAMP.txt", re.compile(r"(?m)^engine=0\.0\.0$"), "engine=9.9.9"),
        ("restated.txt", re.compile(r"version=old"), "version=new"),
    ])
    writes = []
    bootstrap_calls = []

    def anchored_write(path, text):
        writes.append(str(Path(path).relative_to(tmp_path)))
        Path(path).write_text(text, encoding="utf-8")

    def bootstrap(check):
        bootstrap_calls.append(check)
        assert check is False
        if partial_output:
            bootstrap_output.write_text("partial bootstrap output retained\n", encoding="utf-8")
        return False, ["synthetic delegated apply failed"]

    monkeypatch.setattr(owner, "atomic_write_text", anchored_write)
    monkeypatch.setattr(owner, "sync_bootstrap_contract", bootstrap)
    before = _snapshot(tmp_path)

    with pytest.raises(SystemExit) as exc:
        owner.main([])

    assert exc.value.code == 1
    output = capsys.readouterr()
    assert "version sync REFUSED (no anchored write applied; bootstrap outputs may be partial):" in output.err
    assert "synthetic delegated apply failed" in output.err
    assert "no file written" not in output.err
    assert "done —" not in output.out
    assert "nothing to patch" not in output.out
    assert "patched " not in output.out
    assert bootstrap_calls == [False]
    assert writes == []
    after = _snapshot(tmp_path)
    assert after["BUILD_STAMP.txt"] == before["BUILD_STAMP.txt"]
    assert after["restated.txt"] == before["restated.txt"]
    rel = "docs/BOOTSTRAP_FILE_AUDIT.md"
    assert after[rel] == (
        b"partial bootstrap output retained\n" if partial_output else before[rel]
    )
    assert {key: value for key, value in after.items() if key != rel} == {
        key: value for key, value in before.items() if key != rel
    }

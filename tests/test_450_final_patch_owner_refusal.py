"""Final patch-owner refusal must not become a successful main result."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_450_build_stamp_patch_admission import (
    HEADLINE, INVALID_CASES, _load_owner, _make_invalid, _snapshot, _write_fixture,
)


def _configure_main(monkeypatch, tmp_path):
    owner = _load_owner(monkeypatch)
    _write_fixture(tmp_path)
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner, "RULES", [
        ("restated.txt", re.compile(r"version=old"), "version=new"),
    ])
    writes = []

    def write(path, text):
        writes.append(str(Path(path).relative_to(tmp_path)))
        Path(path).write_text(text, encoding="utf-8")

    monkeypatch.setattr(owner, "atomic_write_text", write)
    return owner, writes


@pytest.mark.parametrize("case,diagnostic", INVALID_CASES)
def test_metadata_drift_after_admission_refuses_success_and_retains_partial_state(
    monkeypatch, tmp_path, capsys, case, diagnostic
):
    owner, writes = _configure_main(monkeypatch, tmp_path)
    before = _snapshot(tmp_path)
    bootstrap_calls = []
    post_bootstrap = {}

    def bootstrap(check):
        bootstrap_calls.append(check)
        assert check is False
        _make_invalid(tmp_path, case)
        (tmp_path / "BOOTSTRAP_PARTIAL.txt").write_text("retained diagnostic state\n", encoding="utf-8")
        post_bootstrap.update(_snapshot(tmp_path))
        return True, ["synthetic bootstrap completed"]

    monkeypatch.setattr(owner, "sync_bootstrap_contract", bootstrap)
    with pytest.raises(SystemExit) as exc:
        owner.main([])

    assert exc.value.code == 1
    output = capsys.readouterr()
    assert diagnostic in output.out
    assert "done —" not in output.out
    assert "nothing to patch" not in output.out
    assert "patched " not in output.out
    assert bootstrap_calls == [False]
    assert writes == ["restated.txt"]
    after = _snapshot(tmp_path)
    assert after["restated.txt"] == b"version=new\n"
    assert after["BOOTSTRAP_PARTIAL.txt"] == b"retained diagnostic state\n"
    for rel, data in post_bootstrap.items():
        if rel != "restated.txt":
            assert after[rel] == data
    if case == "missing_stamp":
        assert "BUILD_STAMP.txt" not in after
    else:
        assert after["BUILD_STAMP.txt"] == post_bootstrap["BUILD_STAMP.txt"]
    for rel, data in before.items():
        if rel not in {"BUILD_STAMP.txt", "CHANGELOG.md", "restated.txt"}:
            assert after[rel] == data


@pytest.mark.parametrize("write_result,check_result,diagnostic", [
    (["MISSING FILE: BUILD_STAMP.txt"], [], "MISSING FILE: BUILD_STAMP.txt"),
    (["unexpected typed owner refusal"], [], "unexpected typed owner refusal"),
    (["patched BUILD_STAMP.txt (patch= line)"], ["OUT OF SYNC: final metadata drift"], "OUT OF SYNC: final metadata drift"),
])
def test_refusal_or_failed_final_check_cannot_be_laundered_into_success(
    monkeypatch, tmp_path, capsys, write_result, check_result, diagnostic
):
    owner, writes = _configure_main(monkeypatch, tmp_path)
    monkeypatch.setattr(owner, "sync_bootstrap_contract", lambda check: (True, []))
    patch_calls = []

    def patch_owner(check):
        patch_calls.append(check)
        return check_result if check else write_result

    monkeypatch.setattr(owner, "sync_build_stamp_patch", patch_owner)
    with pytest.raises(SystemExit) as exc:
        owner.main([])

    assert exc.value.code == 1
    output = capsys.readouterr()
    assert diagnostic in output.out
    assert "done —" not in output.out
    assert "patched " not in output.out
    assert patch_calls == [False, True]
    assert writes == ["restated.txt"]
    assert (tmp_path / "restated.txt").read_bytes() == b"version=new\n"


def test_valid_headline_change_after_admission_is_refreshed_and_verified(
    monkeypatch, tmp_path, capsys
):
    owner, writes = _configure_main(monkeypatch, tmp_path)
    bootstrap_calls = []

    def bootstrap(check):
        bootstrap_calls.append(check)
        path = tmp_path / "CHANGELOG.md"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "First headline.", "Updated headline."
        ), encoding="utf-8")
        return True, []

    monkeypatch.setattr(owner, "sync_bootstrap_contract", bootstrap)
    owner.main([])

    output = capsys.readouterr()
    assert "done —" in output.out
    assert bootstrap_calls == [False]
    assert writes == ["restated.txt", "BUILD_STAMP.txt"]
    assert "patch=" + HEADLINE.replace("First headline.", "Updated headline.") in (
        tmp_path / "BUILD_STAMP.txt"
    ).read_text(encoding="utf-8").splitlines()
    assert owner.sync_build_stamp_patch(check=True) == []

"""Synthetic patch-metadata admission and all-or-nothing owner contracts."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
STALE_STAMP = (
    "version=9.9.9\n"
    "build=20260101v9999a\n"
    "engine=0.0.0\n"
    "patch=Old summary.\n"
    "tier=code\n"
)
HEADLINE = "First headline.; Second headline"
EXPECTED_PATCH = "patch=" + HEADLINE
INVALID_CASES = [
    ("missing_line", "expected exactly one line, observed 0"),
    ("duplicate_identical", "expected exactly one line, observed 2"),
    ("duplicate_conflicting", "expected exactly one line, observed 2"),
    ("no_headline", "could not derive patch line from CHANGELOG.md"),
    ("missing_stamp", "MISSING FILE: BUILD_STAMP.txt"),
]


def _load_owner(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location(
        "build_stamp_patch_admission_sync_version", ROOT / "tools" / "sync_version.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_fixture(root):
    (root / "BUILD_STAMP.txt").write_text(STALE_STAMP, encoding="utf-8")
    (root / "CHANGELOG.md").write_text(
        "# v9.9.9 — synthetic fixture\n"
        "Build 20260101v9999a; engine 0.0.0.\n"
        "- **First headline.** synthetic detail.\n"
        "- **Second headline:** synthetic detail.\n"
        "# v9.9.8\n- **Old release headline.** excluded.\n",
        encoding="utf-8",
    )
    identity = {
        "pyproject.toml": '[project]\nversion="0.0.0"\n[tool.mamey]\nbundle_version="9.9.9"\n',
        "TAG.txt": "sapote-mamey-v9.9.9 / engine 0.0.0 / build 20260101v9999a\n",
        "CITATION.cff": "version: 9.9.9\ndate-released: 2026-01-01\n",
        "mamey/__init__.py": '__version__ = "0.0.0"\n__bundle_version__ = "9.9.9"\n',
    }
    for rel, text in identity.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "restated.txt").write_text("version=old\n", encoding="utf-8")


def _make_invalid(root, case):
    stamp = root / "BUILD_STAMP.txt"
    if case == "missing_line":
        stamp.write_text(STALE_STAMP.replace("patch=Old summary.\n", ""), encoding="utf-8")
    elif case == "duplicate_identical":
        stamp.write_text(STALE_STAMP + "patch=Old summary.\n", encoding="utf-8")
    elif case == "duplicate_conflicting":
        stamp.write_text(STALE_STAMP + "patch=Conflicting summary.\n", encoding="utf-8")
    elif case == "no_headline":
        (root / "CHANGELOG.md").write_text("# v9.9.9\nNo bold bullet headline.\n", encoding="utf-8")
    elif case == "missing_stamp":
        stamp.unlink()
    else:
        raise AssertionError(case)


def _snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    }


def _without_patch(data):
    return b"".join(line for line in data.splitlines(keepends=True) if not line.startswith(b"patch="))


@pytest.mark.parametrize("case,diagnostic", INVALID_CASES)
@pytest.mark.parametrize("check", [True, False])
def test_direct_patch_owner_refuses_invalid_input_without_writes(monkeypatch, tmp_path, case, diagnostic, check):
    owner = _load_owner(monkeypatch)
    _write_fixture(tmp_path)
    _make_invalid(tmp_path, case)
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    writes = []
    monkeypatch.setattr(owner, "atomic_write_text", lambda *args: writes.append(args))
    before = _snapshot(tmp_path)

    messages = owner.sync_build_stamp_patch(check=check)

    assert messages and diagnostic in "; ".join(messages)
    assert writes == []
    assert _snapshot(tmp_path) == before


def test_stale_check_is_read_only_and_reports_expected_mismatch(monkeypatch, tmp_path):
    owner = _load_owner(monkeypatch)
    _write_fixture(tmp_path)
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    writes = []
    monkeypatch.setattr(owner, "atomic_write_text", lambda *args: writes.append(args))
    before = _snapshot(tmp_path)

    assert owner.sync_build_stamp_patch(check=True) == [
        "OUT OF SYNC: BUILD_STAMP.txt patch= line does not match CHANGELOG head"
    ]
    assert writes == []
    assert _snapshot(tmp_path) == before


def test_valid_patch_write_changes_only_patch_and_is_then_idempotent(monkeypatch, tmp_path):
    owner = _load_owner(monkeypatch)
    _write_fixture(tmp_path)
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    writes = []

    def record_write(path, text):
        writes.append((Path(path), text))
        Path(path).write_text(text, encoding="utf-8")

    monkeypatch.setattr(owner, "atomic_write_text", record_write)
    before = _snapshot(tmp_path)
    assert owner.sync_build_stamp_patch(check=False) == ["patched BUILD_STAMP.txt (patch= line)"]
    after = _snapshot(tmp_path)
    assert len(writes) == 1 and writes[0][0] == tmp_path / "BUILD_STAMP.txt"
    assert after["BUILD_STAMP.txt"] == STALE_STAMP.replace("patch=Old summary.", EXPECTED_PATCH).encode()
    assert _without_patch(after["BUILD_STAMP.txt"]) == _without_patch(before["BUILD_STAMP.txt"])
    assert {key: value for key, value in after.items() if key != "BUILD_STAMP.txt"} == {
        key: value for key, value in before.items() if key != "BUILD_STAMP.txt"
    }
    assert owner.sync_build_stamp_patch(check=True) == []
    assert owner.sync_build_stamp_patch(check=False) == []
    assert len(writes) == 1
    assert _snapshot(tmp_path) == after


@pytest.mark.parametrize("case,diagnostic", INVALID_CASES)
def test_main_refuses_patch_input_before_bootstrap_and_anchor_writes(monkeypatch, tmp_path, capsys, case, diagnostic):
    owner = _load_owner(monkeypatch)
    _write_fixture(tmp_path)
    _make_invalid(tmp_path, case)
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner, "RULES", [
        ("restated.txt", re.compile(r"version=old"), "version=new"),
    ])
    writes = []
    bootstrap_calls = []
    monkeypatch.setattr(owner, "atomic_write_text", lambda *args: writes.append(args))
    monkeypatch.setattr(owner, "sync_bootstrap_contract", lambda check: bootstrap_calls.append(check) or (True, []))
    before = _snapshot(tmp_path)

    with pytest.raises(SystemExit) as exc:
        owner.main([])

    assert exc.value.code == 1
    assert diagnostic in capsys.readouterr().err
    assert writes == []
    assert bootstrap_calls == []
    assert _snapshot(tmp_path) == before


def test_main_preflight_is_read_only_and_final_patch_keeps_new_anchor(monkeypatch, tmp_path):
    owner = _load_owner(monkeypatch)
    _write_fixture(tmp_path)
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner, "RULES", [
        ("BUILD_STAMP.txt", re.compile(r"(?m)^engine=0\.0\.0$"), "engine=9.9.9"),
        ("restated.txt", re.compile(r"version=old"), "version=new"),
    ])
    before = _snapshot(tmp_path)
    events = []
    original_plan = owner._build_stamp_patch_plan

    def record_plan():
        result = original_plan()
        events.append(("plan", result[1]))
        return result

    def record_bootstrap(check):
        events.append(("bootstrap", check))
        return True, []

    def record_write(path, text):
        events.append(("write", str(Path(path).relative_to(tmp_path))))
        Path(path).write_text(text, encoding="utf-8")

    monkeypatch.setattr(owner, "_build_stamp_patch_plan", record_plan)
    monkeypatch.setattr(owner, "sync_bootstrap_contract", record_bootstrap)
    monkeypatch.setattr(owner, "atomic_write_text", record_write)

    owner.main([])

    after = _snapshot(tmp_path)
    assert events[0] == ("plan", STALE_STAMP)
    assert events[1] == ("bootstrap", False)
    plans = [(index, value) for index, (kind, value) in enumerate(events) if kind == "plan"]
    assert len(plans) == 3
    second_index, second_stamp = plans[1]
    assert "engine=9.9.9\n" in second_stamp and "patch=Old summary.\n" in second_stamp
    final_index, final_stamp = plans[2]
    assert final_index > second_index
    assert "engine=9.9.9\n" in final_stamp and EXPECTED_PATCH + "\n" in final_stamp
    assert any(kind == "write" and value == "BUILD_STAMP.txt" for kind, value in events[:second_index])
    assert after["BUILD_STAMP.txt"] == STALE_STAMP.replace(
        "engine=0.0.0", "engine=9.9.9"
    ).replace("patch=Old summary.", EXPECTED_PATCH).encode()
    assert after["restated.txt"] == b"version=new\n"
    assert {key: value for key, value in after.items() if key not in {"BUILD_STAMP.txt", "restated.txt"}} == {
        key: value for key, value in before.items() if key not in {"BUILD_STAMP.txt", "restated.txt"}
    }
    assert _without_patch(after["BUILD_STAMP.txt"]).replace(b"engine=9.9.9", b"engine=0.0.0") == _without_patch(before["BUILD_STAMP.txt"])

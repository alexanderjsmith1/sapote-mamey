"""Generic source-only identity controls; no release, archives or child processes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest


TOOLS = Path(__file__).resolve().parents[1] / "tools"
FIELDS = ("engine", "bundle", "build", "init_engine", "init_bundle", "stamp_bundle")
ENGINE = "3.2.1"
BUNDLE = "7.6.5"
BUILD = "SYNTHETIC_BUILD"


@pytest.fixture(autouse=True)
def forbid_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("identity token control attempted child execution")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)


@pytest.fixture
def identity(monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    name = "c2_required_identity_tokens"
    path = TOOLS / "verify_release_identity.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    assert Path(module.__file__).resolve() == path.resolve()
    for helper in ("check_release_manifest", "_console"):
        assert Path(sys.modules[helper].__file__).resolve() == (TOOLS / (helper + ".py")).resolve()
    return module


def snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        result[path.relative_to(root).as_posix()] = (
            mode, hashlib.sha256(path.read_bytes()).hexdigest() if stat.S_ISREG(mode) else None
        )
    return result


def synthetic_tree(root, identity, mode):
    root.mkdir()
    (root / "mamey").mkdir()
    if mode == "missing_all":
        project = "# synthetic marker exists; identity assignments absent\n"
        init = "# synthetic marker exists; identity assignments absent\n"
        stamp = "# synthetic marker exists; identity assignments absent\n"
        probe = identity.READ_PROOF + "\n"
    else:
        project = f'[project]\nversion = "{ENGINE}"\n\n[tool.sapote]\nbundle_version = "{BUNDLE}"\n'
        init = f'__version__ = "{ENGINE}"\nBUNDLE_VERSION = "{BUNDLE}"\n'
        stamp = f"version={BUNDLE}\nengine={ENGINE}\n"
        if mode == "valid":
            stamp += f"build={BUILD}\n"
        probe = f"{identity.READ_PROOF}\nv{BUNDLE} / {ENGINE} / {BUILD}\n"
    files = {
        "pyproject.toml": project, "mamey/__init__.py": init, "BUILD_STAMP.txt": stamp,
        "AGENTS.md": probe, "CLAUDE.md": probe, "README.md": probe, "TAG": probe,
    }
    for relative, text in files.items():
        (root / relative).write_text(text, encoding="utf-8")
    tier = root / "TIER_MANIFEST.txt"
    tier.write_text("# synthetic membership only\n" + "".join("./" + name + "\n" for name in sorted(files)))
    checksummed = sorted([*files, "TIER_MANIFEST.txt"])
    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_text("".join(
        hashlib.sha256((root / name).read_bytes()).hexdigest() + "  ./" + name + "\n"
        for name in checksummed
    ))
    return root


def check(root, identity, capsys):
    # Establish content/membership premises independently before asking about identity.
    assert identity._root_marker_errors(root) == []
    assert identity.check_content(root, strict_coverage=True) == []
    assert identity.check_membership(root) == []
    before = snapshot(root)
    rc = identity.main(["--root", str(root), "--json", "--strict-membership"])
    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["tier_zips_checked"] == 0
    assert payload["membership_advisories"] == []
    assert snapshot(root) == before, "read-only identity check changed synthetic evidence"
    return rc, payload


def test_missing_all_identity_tokens_refuse(tmp_path, identity, capsys):
    root = synthetic_tree(tmp_path / "synthetic-root", identity, "missing_all")
    rc, payload = check(root, identity, capsys)
    assert rc == 1, "present marker files with no identity tokens must refuse"
    assert payload["status"] == "FAIL"
    assert set(payload["errors"]) == {"missing required identity token: " + field for field in FIELDS}


def test_missing_build_token_refuses(tmp_path, identity, capsys):
    root = synthetic_tree(tmp_path / "synthetic-root", identity, "missing_build")
    rc, payload = check(root, identity, capsys)
    assert rc == 1, "absent build token must not disable build probes"
    assert payload["status"] == "FAIL"
    assert payload["errors"] == ["missing required identity token: build"]


def test_complete_identity_tokens_stay_valid(tmp_path, identity, capsys):
    root = synthetic_tree(tmp_path / "synthetic-root", identity, "valid")
    rc, payload = check(root, identity, capsys)
    assert rc == 0 and payload["status"] == "PASS"
    assert payload["errors"] == []
    assert {field: payload["truth"][field] for field in FIELDS} == {
        "engine": ENGINE, "init_engine": ENGINE, "bundle": BUNDLE,
        "init_bundle": BUNDLE, "stamp_bundle": BUNDLE, "build": BUILD,
    }

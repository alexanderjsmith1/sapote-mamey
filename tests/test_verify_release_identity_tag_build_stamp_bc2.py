"""BC2-VRI-01 (v9.7.395): tools/verify_release_identity.py's build-stamp freshness check must
cover TAG, not just BUILD_STAMP.txt/README.md/the handshake docs.

verify_release_identity.py's own module docstring says it exists to catch "the v9.7.139
wrapper/stale-internal failure class before a cut is published" — a doc/probe file that still
names the current bundle+engine version but has a stale build stamp behind it. TAG genuinely
carries a build stamp line ("build: <stamp>"), but the build-check membership set in
_probe_text() omitted "TAG", so a stale build stamp inside TAG specifically (bundle and engine
version both still current everywhere) was invisible to this fail-closed gate — it reported PASS.

Reproduced live against the unpatched tools/verify_release_identity.py before this fix.
"""
from __future__ import annotations
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import verify_release_identity as vri  # noqa: E402

BUNDLE = "9.7.999"
ENGINE = "1.9.999"
BUILD_CURRENT = "20260901v97999a"
BUILD_STALE = "20260101v97000a"


def _make_tree(root: pathlib.Path, tag_build: str) -> None:
    (root / "mamey").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nversion = "{ENGINE}"\n\n[tool.sapote]\nbundle_version = "{BUNDLE}"\n'
    )
    (root / "mamey" / "__init__.py").write_text(
        f'__version__ = "{ENGINE}"\nBUNDLE_VERSION = "{BUNDLE}"\n'
    )
    (root / "BUILD_STAMP.txt").write_text(
        f"version={BUNDLE}\nbuild={BUILD_CURRENT}\nengine={ENGINE}\n"
    )
    (root / "TAG").write_text(
        f"sapote-mamey v{BUNDLE}\nengine: mamey v{ENGINE}\nbuild: {tag_build}\n"
    )
    handshake_text = (
        f"{vri.READ_PROOF}\nv{BUNDLE} / {ENGINE} / {BUILD_CURRENT}\n"
    )
    for name in ("000_READ_ME_FIRST_CHATGPT_CLAUDE.md", "CHATGPT_START_HERE.md",
                 "CHATGPT_READ_ME_FIRST.md", "CLAUDE_START_HERE.md", "README.md"):
        (root / name).write_text(handshake_text)


def test_stale_tag_build_stamp_is_caught(tmp_path):
    _make_tree(tmp_path, tag_build=BUILD_STALE)  # TAG's build is stale; everything else current
    truth = vri.truth_from_root(tmp_path)
    assert not truth["truth_errors"], f"fixture itself is inconsistent: {truth['truth_errors']}"
    errors = vri.check_tree(tmp_path, truth)
    assert any("TAG" in e and "current build" in e for e in errors), (
        f"a stale build stamp inside TAG must be caught by the fail-closed gate; got: {errors}"
    )


def test_current_tag_build_stamp_stays_clean(tmp_path):
    _make_tree(tmp_path, tag_build=BUILD_CURRENT)  # everything current, including TAG
    truth = vri.truth_from_root(tmp_path)
    errors = vri.check_tree(tmp_path, truth)
    assert errors == [], f"a fully-current tree must report zero errors; got: {errors}"


def test_cli_end_to_end_stale_tag_exits_nonzero(tmp_path):
    _make_tree(tmp_path, tag_build=BUILD_STALE)
    rc = vri.main(["--root", str(tmp_path)])
    assert rc == 1

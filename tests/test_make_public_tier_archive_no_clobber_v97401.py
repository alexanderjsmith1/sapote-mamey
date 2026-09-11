"""v9.7.401: the canonical tier builder must never update or overwrite an archive.

`zip` updates an existing destination in place. A rerun to the same version/stamp pathname can
therefore retain members that no longer exist in the staged tree and emit a mixed-generation
archive. These tests use a tiny generic MERGED fixture only; they do not create a real public
export or depend on cohort data.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "make_public_tier.sh"
STAMP = "20260902v00000a"
ARCHIVE_NAME = f"sapote-mamey-v0.0.0-MERGED-PRIVATE-scaffold-{STAMP}.zip"


def _source(tmp_path: Path) -> Path:
    src = tmp_path / "generic source"
    (src / "mamey").mkdir(parents=True)
    (src / "tools").mkdir()
    (src / "mamey" / "__init__.py").write_text('__version__ = "0.0.0"\n', encoding="utf-8")
    (src / "BUILD_STAMP.txt").write_text(
        f"version=0.0.0\nbuild={STAMP}\nengine=0.0.0\ntier=merged\n",
        encoding="utf-8",
    )
    (src / "CITATION.cff").write_text("version: 0.0.0\n", encoding="utf-8")
    (src / "generic_payload.txt").write_text("fresh generic payload\n", encoding="utf-8")
    for name in ("tracked_file_policy.py", "check_release_manifest.py"):
        shutil.copy2(ROOT / "tools" / name, src / "tools" / name)
    return src


def _run(src: Path, out: Path, *, env_extra: dict[str, str] | None = None):
    env = {
        **os.environ,
        "BUILD_STAMP": STAMP,
        "SKIP_INTIER_PYTEST": "1",
        **(env_extra or {}),
    }
    return subprocess.run(
        ["bash", str(BUILDER), "merged", str(src), str(out)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.skipif(not shutil.which("bash") or not shutil.which("zip"), reason="bash/zip unavailable")
def test_existing_archive_is_refused_and_preserved_byte_for_byte(tmp_path: Path):
    src = _source(tmp_path)
    out = tmp_path / "release output"
    out.mkdir()
    archive = out / ARCHIVE_NAME
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("STALE_SENTINEL.txt", "must not survive by archive update\n")
    before = archive.read_bytes()

    result = _run(src, out)

    assert result.returncode == 9, result.stdout + result.stderr
    assert "no-clobber policy" in result.stderr
    assert archive.read_bytes() == before, "refusal must preserve the prior archive byte-for-byte"


@pytest.mark.skipif(not shutil.which("bash") or not shutil.which("zip"), reason="bash/zip unavailable")
def test_fresh_archive_is_created_from_only_the_current_stage(tmp_path: Path):
    src = _source(tmp_path)
    out = tmp_path / "release output"

    result = _run(src, out)

    assert result.returncode == 0, result.stdout + result.stderr
    archive = out / ARCHIVE_NAME
    assert archive.is_file()
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert "generic_payload.txt" in names
    assert "STALE_SENTINEL.txt" not in names


@pytest.mark.skipif(not shutil.which("bash") or not shutil.which("zip"), reason="bash/zip unavailable")
def test_concurrent_final_path_claim_is_refused_without_overwrite(tmp_path: Path):
    """A claim on the final path AFTER the preflight and BEFORE the commit must be refused.

    THE SEAM MOVED AT v9.7.405, THE CLAIM DID NOT. This test used to inject the race by shimming
    the `zip` binary: the shim claimed the path, then exec'd the real `zip`. At v9.7.405 the
    CODEX_392 transaction finalizer replaced the shell's zip-then-hard-link commit, so `zip` is
    no longer invoked, the shim could never fire, and the test passed vacuously against a run
    that had no race in it at all. The race is now driven where it actually happens rather than
    at any implementation seam: a watcher claims the destination the instant the finalizer's
    temporary archive appears, which is inside the write/audit/hash window between the preflight
    and `commit_noreplace`. That injection depends on no hook and no binary, so it survives the
    next change of committer too.

    Re-pointing this test found a real defect, which is the argument for re-pointing rather than
    retiring it: the finalizer had no typed refusal on the lost-race path, so `FileExistsError`
    escaped `_main` and the tool exited with a traceback instead of its refusal receipt. The
    safety properties were already sound; the contract was not. The three assertions below are
    unchanged from the v9.7.401 original.
    """
    src = _source(tmp_path)
    out = tmp_path / "release output"
    out.mkdir()
    archive = out / ARCHIVE_NAME
    claimed = threading.Event()

    def claim_when_transaction_opens() -> None:
        # The finalizer's temporary is ".<final name>.archtxn.tmp" beside the destination. Its
        # existence is the deterministic marker that the transaction is past its preflight and
        # has not yet committed; poll for it rather than sleeping a guessed interval.
        temporary = out / f".{ARCHIVE_NAME}.archtxn.tmp"
        deadline = time.monotonic() + 110
        while time.monotonic() < deadline:
            if temporary.exists():
                archive.write_bytes(b"concurrent claimant\n")
                claimed.set()
                return
            time.sleep(0.0005)

    watcher = threading.Thread(target=claim_when_transaction_opens, daemon=True)
    watcher.start()
    result = _run(src, out)
    watcher.join(timeout=5)

    # Fail loudly rather than passing vacuously if the window was never observed — a green result
    # from an uninjected race is exactly the failure mode that hid here between .405 and this fix.
    assert claimed.is_set(), (
        "the watcher never saw the finalizer's temporary archive, so no race was injected; "
        "this assertion exists so a missed window can never be mistaken for a passing test\n"
        + result.stdout + result.stderr
    )
    assert result.returncode == 9, result.stdout + result.stderr
    assert "claimed before commit" in result.stderr
    assert archive.read_bytes() == b"concurrent claimant\n"

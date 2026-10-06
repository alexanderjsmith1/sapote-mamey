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
    for name in ("tracked_file_policy.py", "check_release_manifest.py", "cut_preflight.sh"):
        shutil.copy2(ROOT / "tools" / name, src / "tools" / name)
    return src


def _run(src: Path, out: Path, *, env_extra: dict[str, str] | None = None, builder: Path = BUILDER):
    env = {
        **os.environ,
        "SAPOTE_ENABLE_DISABLED_TIERS": "1",  # v9.7.444: the merged tier is disabled by default
        "BUILD_STAMP": STAMP,
        "SKIP_INTIER_PYTEST": "1",
        **(env_extra or {}),
    }
    return subprocess.run(
        ["bash", str(builder), "merged", str(src), str(out)],
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
    """Claim the destination at its actual precommit boundary, with an injection witness.

    The builder and native committer run on the same tiny generic fixture. A local
    wrapper injects an exclusive competing claim immediately before the final
    native no-replace call. Capability-probe names are excluded. This avoids both
    obsolete temporary filenames and guessed scheduling windows.
    """
    src = _source(tmp_path)
    out = tmp_path / "release output"
    out.mkdir()
    archive = out / ARCHIVE_NAME
    witness = tmp_path / "claim.witness"
    harness = tmp_path / "builder harness"
    harness.mkdir()
    owned_builder = harness / "make_public_tier.sh"
    shutil.copy2(BUILDER, owned_builder)
    finalizer = ROOT / "tools/finalize_public_archive.py"
    wrapper = harness / "finalize_public_archive.py"
    wrapper.write_text(
        "from pathlib import Path\nimport importlib.util, os, sys\n"
        + "spec=importlib.util.spec_from_file_location('fixture_finalizer', " + repr(str(finalizer)) + ")\n"
        + "module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)\n"
        + "original=module.commit_noreplace\n"
        + "def competing_claim(source_dirfd,source_name,destination_dirfd,destination_name):\n"
        + "    if destination_name == " + repr(ARCHIVE_NAME) + ":\n"
        + "        fd=os.open(destination_name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=destination_dirfd)\n"
        + "        with os.fdopen(fd,'wb') as handle:handle.write(b'concurrent claimant\\n');handle.flush();os.fsync(handle.fileno())\n"
        + "        Path(" + repr(str(witness)) + ").write_text('actual precommit claim')\n"
        + "    return original(source_dirfd,source_name,destination_dirfd,destination_name)\n"
        + "module.commit_noreplace=competing_claim\nraise SystemExit(module._main())\n"
    )
    result = _run(src, out, builder=owned_builder)
    assert witness.read_text() == 'actual precommit claim', result.stdout + result.stderr
    assert result.returncode == 9, result.stdout + result.stderr
    assert "claimed before commit" in result.stderr
    assert archive.read_bytes() == b"concurrent claimant\n"

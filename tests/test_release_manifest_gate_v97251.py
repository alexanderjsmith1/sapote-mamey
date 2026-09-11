"""v9.7.251 — nothing verified the bundle's integrity artifacts against the bundle.

The v9.7.250 release check found all five governance gates and `release-qa` passing on an artifact whose
checksum manifest failed on 128 files, whose TIER_MANIFEST contradicted its own BUILD_STAMP, and which
listed two files it did not contain. `verify_release_identity.py` checks version/engine/build agree with
*each other* — it never recomputes a checksum or walks the manifest.

Root cause of that artifact: it was hand-zipped from the working tree instead of cut through
`tools/release.sh` + `make_public_tier.sh`, which regenerate both files as the LAST step, post-redaction.
The proper .250 CODE tier verified clean (1262 entries, 0 mismatched, 0 missing). The gate exists so the
next hand-zip cannot ship.
"""
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_release_manifest.py"


def _run(root=None):
    args = [sys.executable, str(GATE)]
    if root:
        args += ["--root", str(root)]
    return subprocess.run(args, capture_output=True, text=True, cwd=str(ROOT))


def test_gate_exists():
    assert GATE.is_file()


def test_stamp_and_build_agree_in_the_working_tree():
    """The stamp check is edit-stable and belongs here. The CHECKSUM check is not: every source edit
    invalidates the manifest until it is regenerated, so asserting it in pytest would fail on every
    commit. It runs in the CUT PATH instead (tools/release.sh, after post-redaction regeneration) —
    which is exactly where the v9.7.250 hand-zip bypassed it."""
    import re
    tier = (ROOT / "TIER_MANIFEST.txt").read_text(encoding="utf-8")
    build = (ROOT / "BUILD_STAMP.txt").read_text(encoding="utf-8")
    ts = re.search(r"stamp=(\S+)", tier).group(1)
    bs = re.search(r"^build=(\S+)", build, re.M).group(1)
    assert ts == bs, f"TIER_MANIFEST stamp={ts} but BUILD_STAMP build={bs}"


def test_gate_catches_a_checksum_mismatch(tmp_path):
    (tmp_path / "a.txt").write_text("real content", encoding="utf-8")
    (tmp_path / "SOURCE_CHECKSUMS_SHA256.txt").write_text(
        f"{'0'*64}  ./a.txt\n", encoding="utf-8")
    r = _run(tmp_path)
    assert r.returncode == 1 and "mismatch" in r.stdout


def test_gate_catches_a_manifest_entry_for_a_file_that_does_not_exist(tmp_path):
    (tmp_path / "SOURCE_CHECKSUMS_SHA256.txt").write_text(
        f"{'0'*64}  ./BGC002_corrected.md\n", encoding="utf-8")
    r = _run(tmp_path)
    assert r.returncode == 1 and "does not exist" in r.stdout


def test_gate_catches_a_stamp_that_contradicts_the_build(tmp_path):
    (tmp_path / "SOURCE_CHECKSUMS_SHA256.txt").write_text("", encoding="utf-8")
    (tmp_path / "TIER_MANIFEST.txt").write_text(
        "# TIER_MANIFEST tier=code version=9.7.250 stamp=20260705v97233a\n", encoding="utf-8")
    (tmp_path / "BUILD_STAMP.txt").write_text("version=9.7.250\nbuild=20260709v97250a\n", encoding="utf-8")
    r = _run(tmp_path)
    assert r.returncode == 1 and "two different builds" in r.stdout

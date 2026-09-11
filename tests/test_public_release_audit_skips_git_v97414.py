"""Regression: the leak audit must skip .git/ so GitHub Actions checkouts don't false-fail (v9.7.414).

A release tree checked out by GitHub Actions carries a `.git/` directory whose index and pack
objects are undecodable binary. `_policy_hits()` (called first by `audit()`) skipped
`__pycache__`/`.DS_Store` but NOT `.git/`, while `audit()`'s own whole-tree scan DID skip `.git/`
and `*.egg-info/` — the skip drifted across sibling loops. So `public_release_audit.py .` (the CI
"Public-release audit" gate) FAILED on `.git/index` and the pack files even though none of them
ship in any release. This pins that every scan loop shares ONE exclusion predicate.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import public_release_audit as pra  # noqa: E402


def _valid_root(tmp_path: Path) -> Path:
    (tmp_path / "mamey" / "data").mkdir(parents=True)
    (tmp_path / "mamey" / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (tmp_path / "BUILD_STAMP.txt").write_text("build=20260907v97413a\n")
    return tmp_path


def test_git_checkout_dir_is_skipped(tmp_path):
    root = _valid_root(tmp_path)
    pack = root / ".git" / "objects" / "pack"
    pack.mkdir(parents=True)
    (root / ".git" / "index").write_bytes(b"DIRC\x00\x00\x00\x02\xff\xfe\x00")
    (pack / "pack-deadbeef.pack").write_bytes(b"PACK\x00\x00\x00\x02\xff\x00")
    (pack / "pack-deadbeef.idx").write_bytes(b"\xff\x74\x4f\x63\x00\x00\x00\x02")
    (pack / "pack-deadbeef.rev").write_bytes(b"RIDX\x00\x00\x00\x01\xff")
    git_hits = [h for h in pra.audit(root) if ".git" in h]
    assert not git_hits, f".git/ must be skipped (GitHub Actions checkout); got: {git_hits}"


def test_editable_install_egg_info_is_skipped(tmp_path):
    root = _valid_root(tmp_path)
    egg = root / "sapote_mamey.egg-info"
    egg.mkdir()
    (egg / "PKG-INFO").write_bytes(b"\x00\x01\xff undecodable binary\x00")
    assert not [h for h in pra.audit(root) if "egg-info" in h], "pip install -e egg-info must be skipped"


def test_real_leak_still_caught(tmp_path):
    """The skip must not become a hole: a genuine undecodable file OUTSIDE .git still fails."""
    root = _valid_root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_bytes(b"\x00\xff\xfe undecodable, and NOT under .git\x00")
    assert [h for h in pra.audit(root) if "undecodable" in h and "notes.md" in h], \
        "an undecodable non-.git file must still be flagged"


def test_one_shared_exclusion_predicate():
    """Anti-drift (worst-list W13): one predicate, not three copies that can diverge again."""
    assert "_is_excluded_from_scan" in Path(pra.__file__).read_text()

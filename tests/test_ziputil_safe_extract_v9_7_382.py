"""test_ziputil_safe_extract_v9_7_382.py — P2-1: every release/ingest ZIP consumer must use the
one fail-closed extraction path (mamey.ziputil.safe_extract_all), which rejects absolute and
../-traversal members instead of writing outside the destination.
"""
import io
import zipfile
from pathlib import Path

import pytest

from mamey.ziputil import safe_extract_all


def _zip_with(members: dict[str, bytes]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    buf.seek(0)
    return buf


def test_benign_members_extract(tmp_path):
    with zipfile.ZipFile(_zip_with({"a/b.txt": b"hi", "c.gbk": b"LOCUS"})) as z:
        safe_extract_all(z, tmp_path)
    assert (tmp_path / "a" / "b.txt").read_bytes() == b"hi"
    assert (tmp_path / "c.gbk").exists()


def test_parent_traversal_rejected(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    with zipfile.ZipFile(_zip_with({"../escape.txt": b"pwn"})) as z:
        with pytest.raises(ValueError):
            safe_extract_all(z, dest)
    assert not (tmp_path / "escape.txt").exists()


def test_absolute_member_rejected(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    # a member whose path resolves outside dest must raise, not write to an absolute location
    with zipfile.ZipFile(_zip_with({"deep/../../../../../../tmp/x.txt": b"pwn"})) as z:
        with pytest.raises(ValueError):
            safe_extract_all(z, dest)


def test_release_consumers_route_through_guard():
    # the three former direct-extractall call sites must reference the shared guard, not extractall
    root = Path(__file__).resolve().parent.parent
    for rel in ("mamey/comparators/antismash_ingest.py",
                "tools/comparator_discovery.py",
                "tools/check_tier_parity.py"):
        src = (root / rel).read_text()
        assert "safe_extract_all" in src, f"{rel} must use safe_extract_all"
        assert ".extractall(" not in src, f"{rel} must not call .extractall directly"

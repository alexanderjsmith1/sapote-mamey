"""v9.7.361 (R1): preflight_zip_hygiene must CONSULT the path-bound allowlist file.

Regression cover for the .355-.360 gap: `tools/zip_hygiene_allowlist.{py,tsv}` shipped as the
sanctioned mechanism for intentionally-large files, but `preflight_zip_hygiene.py` used only its own
hardcoded suffix tuple and never read the file -- so the gate stayed RED on a file that had already
been reviewed, declared, and given a ceiling. Two tools, one gate, not connected.

The point of these tests is that wiring the allowlist did NOT defang the gate. A guard that cannot
fail is worthless, so the negative cases matter more than the positive one.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

pzh = pytest.importorskip("preflight_zip_hygiene")

LIMIT = pzh.LARGE_LIMIT
ALLOWED_PATH = "mamey/data/literature/_corpus/literature_corpus.jsonl"


def _zip_with(tmp_path: Path, name: str, size: int) -> Path:
    zp = tmp_path / "t.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr(name, b"x" * size)
    return zp


def test_allowlist_tsv_is_loadable_and_declares_the_corpus():
    allow = pzh._load_path_allowlist()
    assert allow, "allowlist TSV did not load -- the gate would silently fall back to strict-only"
    key = next((k for k in allow if k.lstrip("./") == ALLOWED_PATH), None)
    assert key, f"{ALLOWED_PATH} not declared in the allowlist"
    ceiling, reason = allow[key]
    assert ceiling > LIMIT, "a declared ceiling below the gate limit is meaningless"
    assert reason.strip(), "allowlist entries must carry a written reason"


def test_allowlisted_file_under_its_ceiling_passes(tmp_path):
    zp = _zip_with(tmp_path, ALLOWED_PATH, LIMIT + 1024)
    assert pzh.scan(zp)["large"] == []


def test_unlisted_oversized_file_still_fails(tmp_path):
    """The gate must keep its teeth: an undeclared large file is still a violation."""
    zp = _zip_with(tmp_path, "mamey/data/huge_unlisted.bin", LIMIT + (2 * 1024 * 1024))
    large = pzh.scan(zp)["large"]
    assert len(large) == 1 and "huge_unlisted.bin" in large[0]


def test_allowlisted_file_over_its_own_ceiling_fails(tmp_path):
    """Allowlisting binds a file to a DECLARED ceiling -- it is not a blanket exemption."""
    allow = pzh._load_path_allowlist()
    key = next(k for k in allow if k.lstrip("./") == ALLOWED_PATH)
    ceiling = allow[key][0]
    zp = _zip_with(tmp_path, ALLOWED_PATH, ceiling + 1024)
    large = pzh.scan(zp)["large"]
    assert len(large) == 1 and "literature_corpus.jsonl" in large[0]


def test_small_files_are_never_flagged(tmp_path):
    zp = _zip_with(tmp_path, "mamey/data/small.txt", 1024)
    assert pzh.scan(zp)["large"] == []


def test_missing_allowlist_degrades_to_strict_not_permissive(tmp_path):
    """If the TSV is absent the gate must get STRICTER, never more permissive."""
    allow = pzh._load_path_allowlist(tmp_path / "does_not_exist.tsv")
    assert allow == {}
    assert pzh._oversized(ALLOWED_PATH, LIMIT + 1024, allow) is True

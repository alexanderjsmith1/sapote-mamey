"""test_determinism_smoke.py — CANDIDATE (Indigo2 JOB-D, 2026-08-15) → tests/ in the next cut.

Package-vs-itself determinism smoke: exercises the engine's OWN repro_fingerprint() on a
synthesized minimal package (no on-disk package fixture exists in the sealed tree — verified:
no `*_2_inventory.csv` under examples/ or tests/). Deliberately NOT the run-the-engine-twice
mode — that is CPU-gated and the Developer or User-owned (see candidate_files/tools/check_determinism.py, the
sibling harness this builds on). CPU cost here: milliseconds.

Covers, using only mamey.packaging's public surface:
  1. fingerprint(pkg) == fingerprint(pkg)                      (pure function, same tree)
  2. rewrite same bytes -> fingerprint unchanged                (mtime/inode independence)
  3. CRLF variant of a whitelisted CSV -> fingerprint unchanged (documented normalization)
  4. one changed byte in a whitelisted artifact -> DIVERGES, and the changed component is named
  5. missing whitelisted artifact -> component == "MISSING", no crash (partial-package contract)
  6. every DETERMINISM_WHITELIST suffix participates            (whitelist coverage, audit I2-213)

Claim-safety: build-reproducibility only; no scientific meaning is read from any hashed value.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mamey.packaging import DETERMINISM_WHITELIST, repro_fingerprint


def _make_pkg(root: Path, stem: str = "SMOKE") -> Path:
    pkg = root / "package"
    pkg.mkdir(parents=True, exist_ok=True)
    for i, suffix in enumerate(DETERMINISM_WHITELIST):
        (pkg / f"{stem}{suffix}").write_bytes(
            f"col_a,col_b\nrow{i},value{i}\n".encode()
        )
    return pkg


def test_fingerprint_is_stable_for_same_tree(tmp_path):
    pkg = _make_pkg(tmp_path)
    a = repro_fingerprint(pkg)
    b = repro_fingerprint(pkg)
    assert a["fingerprint"] == b["fingerprint"]
    assert a["components"] == b["components"]


def test_fingerprint_ignores_rewrite_metadata(tmp_path):
    pkg = _make_pkg(tmp_path)
    before = repro_fingerprint(pkg)["fingerprint"]
    for p in pkg.iterdir():
        p.write_bytes(p.read_bytes())  # same content, new mtime
    assert repro_fingerprint(pkg)["fingerprint"] == before


def test_fingerprint_normalizes_crlf(tmp_path):
    pkg = _make_pkg(tmp_path)
    before = repro_fingerprint(pkg)["fingerprint"]
    target = next(pkg.glob(f"*{DETERMINISM_WHITELIST[0]}"))
    target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    assert repro_fingerprint(pkg)["fingerprint"] == before


def test_fingerprint_detects_single_byte_change(tmp_path):
    pkg = _make_pkg(tmp_path)
    before = repro_fingerprint(pkg)
    suffix = DETERMINISM_WHITELIST[3]  # _4_triage_board.csv — a score-bearing artifact
    target = next(pkg.glob(f"*{suffix}"))
    target.write_bytes(target.read_bytes().replace(b"value3", b"valueX"))
    after = repro_fingerprint(pkg)
    assert after["fingerprint"] != before["fingerprint"]
    changed = [s for s in before["components"] if before["components"][s] != after["components"][s]]
    assert changed == [suffix]


def test_partial_package_reports_missing_not_crash(tmp_path):
    pkg = _make_pkg(tmp_path)
    suffix = DETERMINISM_WHITELIST[-1]
    next(pkg.glob(f"*{suffix}")).unlink()
    fp = repro_fingerprint(pkg)
    assert fp["components"][suffix] == "MISSING"


def test_whitelist_fully_participates(tmp_path):
    pkg = _make_pkg(tmp_path)
    fp = repro_fingerprint(pkg)
    assert set(fp["components"]) == set(DETERMINISM_WHITELIST)
    assert set(fp["whitelist"]) == set(DETERMINISM_WHITELIST)
    assert all(v != "MISSING" for v in fp["components"].values())

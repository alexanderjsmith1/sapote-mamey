"""TESTS — CLAUDE_410_seal_locus_maps_coverage (SEAL_INTEGRITY_REATTACK A9 / A10).

Two v9.7.409 seal gaps, both execution-confirmed against a sealed package
(development/round6_v409/SEAL_INTEGRITY_REATTACK.md):

  A9  locus_maps/ injection. packaging.is_post_seal_covered() covered only *_data.csv / *.json
      under locus_maps/, while validate._checksum_reciprocal_exempt() exempted the WHOLE
      locus_maps/ prefix from the SEAL-03 untracked scan. A fabricated locus_maps/*.md, *.txt or
      *.pdf therefore sat in the gap between the two predicates — neither hash-pinned (SEAL-05)
      nor flagged as untracked (SEAL-03) — and validated MAMEY_COMPLETE.
  A10 An unreadable subtree fails closed (the .409 rglob -> os.walk(onerror=re-raise) fix), but
      validate_package() / verify_checksums() caught only PackageContainmentError, so the
      PermissionError escaped `mamey validate` as an uncaught traceback instead of a typed FAIL.

Every test here asserts the PATCHED contract. Run against pristine v9.7.409 the A9 and A10 cases
FAIL (that is the fail-before evidence: A9 -> no error recorded for the injected file; A10 ->
PermissionError propagates out of validate_package); with the lane applied they PASS. The
regression cases pass on both, pinning what must NOT change (legit locus-map output stays clean,
image re-renders stay exempt, the symlink refusal keeps its own label).

All checks run on synthetic sealed fixtures under tmp_path — no bundle, package or gold run is
touched. The fixture is sealed the sanctioned way: core checksums_sha256.txt, then
packaging.write_post_seal_checksums() (which also anchors the post-seal manifest).
"""
import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from mamey import packaging as pk
from mamey import validate as vd


# ── fixture: a minimal sealed package with a legitimate locus_maps/ set ───────
def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _sealed_with_locus_maps(root: Path) -> Path:
    root.mkdir()
    inv = root / "AS-1_2_inventory.csv"
    inv.write_text("BGC_ID,Depth_floor\nBGC001,full_mode_b\n", encoding="utf-8")
    (root / "checksums_sha256.txt").write_text(f"{_sha(inv)}  AS-1_2_inventory.csv\n", encoding="utf-8")
    lm = root / "locus_maps"
    lm.mkdir()
    # exactly what the locus-map renderers emit: image + numbers companion + v8 receipt
    (lm / "BGC001_locus_map.svg").write_text("<svg/>", encoding="utf-8")
    (lm / "BGC001_locus_map.png").write_bytes(b"\x89PNG")
    (lm / "BGC001_locus_map_data.csv").write_text("gene,start,end\ng1,1,100\n", encoding="utf-8")
    (lm / "BGC001_locus_map_v8_receipt.json").write_text("{}", encoding="utf-8")
    pk.write_post_seal_checksums(root)
    return root


def _unreadable_subtree_or_skip(pkg: Path):
    """Add pkg/locked/hidden.txt with locked chmod 000; skip where the OS cannot enforce it."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("running as root: directory-mode 000 does not block enumeration")
    locked = pkg / "locked"
    locked.mkdir()
    (locked / "hidden.txt").write_text("must-not-vanish\n", encoding="utf-8")
    os.chmod(locked, 0o000)

    def _restore():
        os.chmod(locked, stat.S_IRWXU)

    try:
        os.listdir(locked)
    except PermissionError:
        return _restore
    _restore()
    pytest.skip("filesystem does not enforce directory-mode 000")


# ── A9: injected non-image file under locus_maps/ is caught ──────────────────
@pytest.mark.parametrize("name", ["fabricated.md", "notes.txt", "evil.pdf", "EVIL_cnbu.json"])
def test_a9_locus_maps_injection_flips_checksum_integrity(tmp_path, name):
    """FAIL-BEFORE on .409 (errors == [] for .md/.txt/.pdf); PASS-AFTER: the drop is an error."""
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    assert vd.verify_checksums(pkg) == [], "fixture must be clean before the attack"
    (pkg / "locus_maps" / name).write_bytes(b"fabricated")
    errors = vd.verify_checksums(pkg)
    assert any(f"locus_maps/{name}" in e for e in errors), errors
    res = vd.validate_package(pkg, write_status_receipt=False)
    assert res["checksum_integrity"] == "FAIL"
    assert res["status"] == "FAIL"


def test_a9_coverage_and_exemption_are_aligned():
    """The two predicates must agree: anything reciprocal-exempt under locus_maps/ is either
    post-seal-covered (SEAL-05 owns it) or an image re-render. Nothing falls in between."""
    for rel in ("locus_maps/x.md", "locus_maps/x.txt", "locus_maps/x.pdf", "locus_maps/x.csv",
                "locus_maps/x_data.csv", "locus_maps/x.json", "locus_maps/deep/x.md",
                "locus_maps/x.png", "locus_maps/x.svg"):
        exempt = vd._checksum_reciprocal_exempt(rel)
        covered = pk.is_post_seal_covered(rel)
        image = pk.is_checksum_excluded(rel)
        assert exempt == (covered or image), rel
        if not image:
            assert covered, f"non-image file under locus_maps/ must be covered: {rel}"


def test_a9_without_post_seal_manifest_untracked_scan_still_flags_it(tmp_path):
    """A package sealed before post_seal_checksums.txt existed: the SEAL-03 untracked scan alone
    must now see a non-image, non-covered drop... every non-image file is covered, so the drop is
    exempt from SEAL-03 by design (SEAL-05 owns it) — pin that the covered/exempt contract holds
    for the manifest-less case exactly as it does for judgment/ and the other covered subtrees."""
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    (pkg / "post_seal_checksums.txt").unlink()
    # strip the anchor comment line the writer folded into the core manifest
    core = pkg / "checksums_sha256.txt"
    core.write_text("".join(l for l in core.read_text(encoding="utf-8").splitlines(True)
                            if not l.startswith("#")), encoding="utf-8")
    assert vd.verify_checksums(pkg) == []
    (pkg / "locus_maps" / "fabricated.md").write_bytes(b"fabricated")
    # backward-compatible: absent manifest == pre-.409 behaviour for every covered subtree
    assert vd.verify_checksums(pkg) == []


# ── A9 regressions: legit output stays clean; images stay the documented exception ────
def test_a9_regression_legit_locus_map_output_is_clean(tmp_path):
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    res = vd.validate_package(pkg, write_status_receipt=False)
    assert res["checksum_integrity"] == "PASS"
    assert vd.verify_checksums(pkg) == []


def test_a9_regression_image_rerender_still_exempt(tmp_path):
    """png/svg under locus_maps/ are non-deterministic matplotlib re-renders (seal-first design):
    a re-render (byte change) or a new image must not trip the seal. Unchanged from .409."""
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    (pkg / "locus_maps" / "BGC001_locus_map.svg").write_text("<svg>re-rendered</svg>", encoding="utf-8")
    (pkg / "locus_maps" / "BGC002_locus_map.png").write_bytes(b"\x89PNG new")
    assert vd.verify_checksums(pkg) == []
    assert pk.is_post_seal_covered("locus_maps/BGC001_locus_map.svg") is False
    assert pk.is_post_seal_covered("locus_maps/BGC001_locus_map.png") is False


def test_a9_regression_sanctioned_refresh_folds_new_locus_output(tmp_path):
    """A sanctioned authoring command (render-figures) writes new locus_maps/ data then calls
    refresh_post_seal_checksums(): its legit output must be folded in, not flagged."""
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    (pkg / "locus_maps" / "BGC002_locus_map_data.csv").write_text("gene,start,end\n", encoding="utf-8")
    (pkg / "locus_maps" / "BGC002_locus_map_v8_receipt.json").write_text("{}", encoding="utf-8")
    pk.refresh_post_seal_checksums(pkg)
    assert vd.verify_checksums(pkg) == []
    assert pk.verify_post_seal_anchor(pkg) == []


def test_a9_regression_covered_json_and_csv_still_caught(tmp_path):
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    (pkg / "locus_maps" / "x.json").write_bytes(b"{}")
    (pkg / "locus_maps" / "x_locus_map_data.csv").write_bytes(b"a\n")
    errors = vd.verify_checksums(pkg)
    assert any("locus_maps/x.json" in e for e in errors)
    assert any("locus_maps/x_locus_map_data.csv" in e for e in errors)


# ── A10: unreadable subtree -> typed clean FAIL, no traceback ─────────────────
def test_a10_validate_package_unreadable_subtree_is_typed_fail(tmp_path):
    """FAIL-BEFORE on .409: validate_package RAISES PermissionError. PASS-AFTER: returns a
    structured FAIL verdict with the SEAL_UNREADABLE_SUBTREE label; nothing is raised."""
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    restore = _unreadable_subtree_or_skip(pkg)
    try:
        res = vd.validate_package(pkg, write_status_receipt=False)
    finally:
        restore()
    assert res["status"] == "FAIL"
    assert res["package_containment"] == "FAIL"
    assert res["checksum_integrity"] == "FAIL"
    assert res["seal_enumeration"] == "SEAL_UNREADABLE_SUBTREE"
    assert any("SEAL_UNREADABLE_SUBTREE" in e for e in res["containment_errors"])
    assert any("UNVERIFIED" in e for e in res["checksum_errors"])


def test_a10_verify_checksums_unreadable_subtree_is_typed_error(tmp_path):
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    restore = _unreadable_subtree_or_skip(pkg)
    try:
        errors = vd.verify_checksums(pkg)
    finally:
        restore()
    assert len(errors) == 1
    assert errors[0].startswith("SEAL_UNREADABLE_SUBTREE")


def test_a10_still_fails_closed_no_pass_obtainable(tmp_path):
    """Fail-closed semantics preserved: the unreadable subtree can never yield PASS/MAMEY_COMPLETE,
    and the seal itself is not mutated (no receipt written into the package on the FAIL path)."""
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    before = {p.relative_to(pkg).as_posix(): _sha(p) for p in pkg.rglob("*") if p.is_file()}
    restore = _unreadable_subtree_or_skip(pkg)
    try:
        res = vd.validate_package(pkg, write_status_receipt=False)
    finally:
        restore()
    assert res["status"] not in ("PASS", "MAMEY_COMPLETE")
    after = {p.relative_to(pkg).as_posix(): _sha(p) for p in pkg.rglob("*") if p.is_file()}
    after.pop("locked/hidden.txt", None)
    assert after == before, "validate must not mutate the sealed package on the FAIL path"


def test_a10_cli_validate_exit_1_without_traceback(tmp_path):
    """`mamey validate` on the unreadable package: exit 1, JSON verdict on stdout, and no Python
    traceback on stderr (FAIL-BEFORE on .409: traceback + PermissionError on stderr)."""
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    restore = _unreadable_subtree_or_skip(pkg)
    try:
        proc = subprocess.run([sys.executable, "-m", "mamey", "validate", str(pkg)],
                              capture_output=True, text=True, timeout=300)
    finally:
        restore()
    assert proc.returncode == 1, (proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr, proc.stderr
    assert "PermissionError" not in proc.stderr, proc.stderr
    assert "SEAL_UNREADABLE_SUBTREE" in proc.stdout
    assert '"status": "FAIL"' in proc.stdout


def test_a10_regression_symlink_refusal_keeps_its_own_label(tmp_path):
    """The containment (symlink) branch is untouched: same message, distinct enumeration label."""
    pkg = _sealed_with_locus_maps(tmp_path / "pkg")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    try:
        (pkg / "locus_maps" / "link.svg").symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    res = vd.validate_package(pkg, write_status_receipt=False)
    assert res["status"] == "FAIL"
    assert res["seal_enumeration"] == "PACKAGE_CONTAINMENT"
    assert any("package symlink is prohibited" in e for e in res["containment_errors"])

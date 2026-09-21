"""Pytest-compatible companion for test_409_post_seal_checksums.py.

The standalone script exercises the same three attack vectors (injection, swap, delete) plus
boundary checks, but behind `if __name__ == "__main__"` — pytest never collects it.  This file
wraps the same patterns into proper `def test_*()` functions so they appear in the CI suite.

v9.7.436 patch: claude-alex-2026-40.
"""
import hashlib
import shutil
from pathlib import Path

import pytest

from mamey.packaging import is_post_seal_covered, write_post_seal_checksums
from mamey.validate import verify_checksums


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _make_sealed_package(root: Path):
    """Minimal synthetic sealed package matching the standalone script's layout."""
    root.mkdir(parents=True, exist_ok=True)
    core = root / "STR_2_inventory.csv"
    core.write_text("bgc_id,product\nBGC001,unknown\n", encoding="utf-8")
    (root / "domain_level").mkdir()
    (root / "domain_level" / "domain_safe_unsafe_claims.csv").write_text(
        "bgc_id,claim,safe\nBGC001,none asserted,TRUE\n", encoding="utf-8")
    (root / "blastp_online").mkdir()
    (root / "blastp_online" / "BGC001_online_blastp.csv").write_text(
        "gene,hit\nctg1_1,none\n", encoding="utf-8")
    (root / "STR_8a_fig_landscape.png").write_bytes(b"\x89PNG\r\n\x1a\n-real-figure-bytes-")
    (root / "STR_8d_fig_ab_ranked_data.csv").write_text("rank,score\n1,0.5\n", encoding="utf-8")
    (root / "checksums_sha256.txt").write_text(
        f"{_sha(core)}  STR_2_inventory.csv\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# FAIL-BEFORE: no post_seal_checksums.txt => attacks are NOT caught (the leak
# the patch closes).  These pass ONLY when the pre-patch backward-compat
# posture is preserved — `verify_checksums` returns [] on a package that has
# no post-seal manifest.
# ---------------------------------------------------------------------------

class TestFailBeforeNoManifest:
    """Without post_seal_checksums.txt, the three attacks are invisible."""

    def test_injection_not_flagged_without_manifest(self, tmp_path):
        pkg = tmp_path / "fb_inject"
        _make_sealed_package(pkg)
        (pkg / "mode_b").mkdir()
        (pkg / "mode_b" / "BGC999_mode_b.md").write_text(
            "fabricated: produces penicillin\n", encoding="utf-8")
        errs = verify_checksums(pkg)
        assert not any("post_seal" in e for e in errs)
        assert not any("injected" in e for e in errs)

    def test_swap_not_flagged_without_manifest(self, tmp_path):
        pkg = tmp_path / "fb_swap"
        _make_sealed_package(pkg)
        (pkg / "domain_level" / "domain_safe_unsafe_claims.csv").write_text(
            "bgc_id,claim,safe\nBGC001,makes vancomycin,TRUE\n", encoding="utf-8")
        assert verify_checksums(pkg) == []

    def test_delete_not_flagged_without_manifest(self, tmp_path):
        pkg = tmp_path / "fb_delete"
        _make_sealed_package(pkg)
        (pkg / "STR_8a_fig_landscape.png").unlink()
        assert verify_checksums(pkg) == []


# ---------------------------------------------------------------------------
# PASS-AFTER: sealed by write_post_seal_checksums => each attack caught.
# ---------------------------------------------------------------------------

class TestPassAfterWithManifest:
    """With the post-seal manifest present, every attack is caught."""

    @pytest.fixture()
    def sealed_pkg(self, tmp_path):
        pkg = tmp_path / "pa_base"
        _make_sealed_package(pkg)
        write_post_seal_checksums(pkg)
        return pkg

    def test_sealer_emits_manifest(self, sealed_pkg):
        assert (sealed_pkg / "post_seal_checksums.txt").exists()

    def test_covered_set_excludes_core(self, sealed_pkg):
        res = write_post_seal_checksums(sealed_pkg)
        assert res["n_files"] >= 4
        assert "STR_2_inventory.csv" not in res["files"]

    def test_clean_sealed_package_verifies_clean(self, sealed_pkg):
        assert verify_checksums(sealed_pkg) == []

    def test_injection_caught(self, tmp_path, sealed_pkg):
        pkg = tmp_path / "pa_inject"
        shutil.copytree(sealed_pkg, pkg)
        (pkg / "mode_b").mkdir()
        (pkg / "mode_b" / "BGC999_mode_b.md").write_text("fabricated\n", encoding="utf-8")
        errs = verify_checksums(pkg)
        assert any("injected file present" in e for e in errs)

    def test_swap_caught(self, tmp_path, sealed_pkg):
        pkg = tmp_path / "pa_swap"
        shutil.copytree(sealed_pkg, pkg)
        (pkg / "domain_level" / "domain_safe_unsafe_claims.csv").write_text(
            "bgc_id,claim,safe\nBGC001,makes vancomycin,TRUE\n", encoding="utf-8")
        errs = verify_checksums(pkg)
        assert any("post-seal checksum mismatch" in e for e in errs)

    def test_delete_caught(self, tmp_path, sealed_pkg):
        pkg = tmp_path / "pa_delete"
        shutil.copytree(sealed_pkg, pkg)
        (pkg / "STR_8a_fig_landscape.png").unlink()
        errs = verify_checksums(pkg)
        assert any("post-seal file deleted" in e for e in errs)


# ---------------------------------------------------------------------------
# BOUNDARY: mutable receipts stay changeable; post-seal deliverables covered.
# ---------------------------------------------------------------------------

class TestBoundaryCoverage:
    """is_post_seal_covered correctly separates mutable from covered paths."""

    @pytest.mark.parametrize("rel", [
        "manifest.json",
        "package_status.json",
        "gate_validation.json",
        "STR_compiled_report.md",
        "STR_SAPOTE_WORKFLOW_LEDGER.md",
        "STR_cnbu.json",
        "STR_judgment_register.json",
        "post_seal_checksums.txt",
        "locus_maps/M_locus_map.png",
    ])
    def test_mutable_not_covered(self, rel):
        assert is_post_seal_covered(rel) is False

    @pytest.mark.parametrize("rel", [
        "mode_b/c.md",
        "domain_level/t.csv",
        "blastp_online/b.csv",
        "guide/g.md",
        "figures/f.png",
        "STR_8a_fig_landscape.png",
        "STR_8d_fig_ab_ranked_data.csv",
        "locus_maps/M_locus_map_data.csv",
        "locus_maps/M_v8_receipt.json",
    ])
    def test_deliverable_covered(self, rel):
        assert is_post_seal_covered(rel) is True

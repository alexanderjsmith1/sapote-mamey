"""v9.7.338 SEAL-03 — reciprocal checksum coverage in verify_checksums().

Before SEAL-03, ``verify_checksums`` only re-hashed files LISTED in checksums_sha256.txt (the
forward direction). A file INJECTED into a sealed package after the seal — one that is simply
not listed — slipped past integrity entirely: the forward pass never looks for files it does
not already know about, and the gate returned PASS. SEAL-03 adds the reciprocal scan: any file
present in the tree but absent from the manifest is an integrity error, UNLESS it is a
legitimate post-seal artifact (figures re-rendered after the seal, mutable receipts, the
manifest/checksums themselves, the per-strain judgment register, etc. — see
validate._checksum_reciprocal_exempt).

Because verify_checksums is wired into validate_package (a non-empty error list -> status FAIL),
this is a VERDICT-CHANGING tightening: a sealed package with a stray/injected untracked file now
FAILs `mamey validate`. These tests assert the reciprocal scan FIRES on the known-bad artifact
(an injected file) and does NOT false-positive on the legitimate post-seal artifact classes —
the project's "verify the gate bites on a known-bad input" discipline.

The exemption set was validated against a REAL sealed AS-168 gold package (json-evidence off):
0 untracked-file errors on a clean seal, and the scan fires the instant a stray file is dropped in.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from mamey.validate import verify_checksums


def _sealed_package(tmp_path: Path, extra: dict[str, bytes] | None = None) -> Path:
    """A package with a POPULATED checksums_sha256.txt (a real seal always lists 100+ files, so
    the reciprocal scan is active). `extra` files are written but NOT added to checksums."""
    pkg = tmp_path / "AS-TEST"
    pkg.mkdir()
    tracked = {
        "AS-TEST_2_inventory.csv": b"bgc_id,Depth_floor\nBGC001,full_mode_b\n",
        "AS-TEST_4_triage_board.csv": b"col\n",
        "manifest_short.json": b"{}",
    }
    lines = []
    for rel, content in tracked.items():
        (pkg / rel).write_bytes(content)
        lines.append(f"{hashlib.sha256(content).hexdigest()}  {rel}")
    (pkg / "checksums_sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for rel, content in (extra or {}).items():
        p = pkg / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    return pkg


def _untracked_errors(pkg: Path) -> list[str]:
    return [e for e in verify_checksums(pkg) if "untracked" in e]


# --------------------------------------------------------------------------------------
# Control + the core known-bad: an injected untracked file must be caught.
# --------------------------------------------------------------------------------------

def test_control_clean_sealed_package_has_no_untracked_errors(tmp_path):
    pkg = _sealed_package(tmp_path)
    assert verify_checksums(pkg) == []


def test_injected_untracked_file_is_flagged(tmp_path):
    """KNOWN-BAD: a file present in the tree but absent from checksums_sha256.txt (the shape of a
    post-seal injection) must be reported — the whole point of the reciprocal scan."""
    pkg = _sealed_package(tmp_path, extra={"INJECTED_EVIL.txt": b"malware"})
    errs = _untracked_errors(pkg)
    assert any("INJECTED_EVIL.txt" in e for e in errs), verify_checksums(pkg)


def test_injected_untracked_file_in_subdir_is_flagged(tmp_path):
    pkg = _sealed_package(tmp_path, extra={"bgc_blastp_panel/sneaky.json": b"{}"})
    errs = _untracked_errors(pkg)
    assert any("bgc_blastp_panel/sneaky.json" in e for e in errs), verify_checksums(pkg)


# --------------------------------------------------------------------------------------
# The legitimate post-seal artifact classes must NOT be flagged (else every clean seal FAILs).
# Each of these is written AFTER packaging.write_manifest captures the file list.
# --------------------------------------------------------------------------------------

def test_legitimate_post_seal_artifacts_are_exempt(tmp_path):
    exempt = {
        # writer-excluded singletons + mutable receipts
        "manifest.json": b"{}",
        "repro_fingerprint.json": b"{}",
        "package_status.json": b"{}",
        "claim_safety_status.json": b"{}",
        "run_phase_receipts.jsonl": b'{"phase":"end"}\n',
        # per-strain judgment register (rewritten by ingest-receipts)
        "AS-TEST_judgment_register.json": b"{}",
        # whole post-seal figure subtrees (re-rendered by the figure phase / render-figures)
        "smoke_figures/fig_assembly_tier.png": b"\x89PNG",
        "smoke_figures/fig_assembly_tier_data.csv": b"a,b\n1,2\n",
        "gold_figures/D01_bubble.png": b"\x89PNG",
        "locus_maps/BGC004_locus_map.svg": b"<svg/>",
        # render-all-figures and domain-level governed post-seal trees
        "figures/FIGURE_INDEX.csv": b"source,path\n",
        "figures_rendered/FIGURE_QA.md": b"# QA\n",
        "domain_level/domain_rows_long.csv": b"Strain,BGC_ID\n",
        # channel-preserving BLASTP overlay + its immutable guard receipts
        "blastp_online/BGC001_online_blastp.csv": b"locus_tag,channel\nctg1_1,nr\n",
        "blastp_online/_ingest_ledger.json": b"{}",
        "blastp_quarantine/nr_overlay_token_quarantine.csv": b"reason,channel\n",
        "blastp_ingest_receipts/nr_overlay_token_receipt.json": b"{}",
        # canonical Sapote judgment/workflow outputs
        "mode_b_templates/BGC001_template.md": b"# template\n",
        "mode_b_templates/_INDEX.md": b"# index\n",
        "judgment/AS-TEST_BGC001_mode_b.md": b"# authored card\n",
        "guide/AS-TEST_BGC001_Guide.md": b"# guide\n",
        "AS-TEST_compiled_report.md": b"# report\n",
        "AS-TEST_SAPOTE_WORKFLOW_LEDGER.md": b"# ledger\n",
        "render_all_figures_summary.json": b"{}",
        # package-ROOT figure images + their data companions
        "AS-TEST_overview.png": b"\x89PNG",
        "AS-TEST_fig_ranking_data.csv": b"a\n1\n",
        # supplementary presentation docs + cnbu
        "PRINT_FIGURE_PACK.md": b"# print pack\n",
        "FIGURES_SUPPLEMENTARY.md": b"# supp\n",
        "figure_manifest_print.csv": b"figure_stem,png_path\n",
        "package_PRINT_FIGURE_PACK.pdf": b"%PDF-1.4",
        "AS-TEST_strain_brief.pdf": b"%PDF-1.4",
        "AS-TEST_cnbu.json": b"{}",
    }
    pkg = _sealed_package(tmp_path, extra=exempt)
    errs = _untracked_errors(pkg)
    assert errs == [], f"legitimate post-seal artifacts must not be flagged as untracked: {errs}"


# --------------------------------------------------------------------------------------
# The empty-manifest guard: an empty checksums_sha256.txt tracks nothing, so the reciprocal
# scan does not fire (a real seal never has an empty manifest; test fixtures do).
# --------------------------------------------------------------------------------------

def test_empty_checksums_manifest_does_not_trigger_reciprocal(tmp_path):
    pkg = tmp_path / "AS-EMPTY"
    pkg.mkdir()
    (pkg / "AS-EMPTY_2_inventory.csv").write_text("x\n", encoding="utf-8")
    (pkg / "checksums_sha256.txt").write_text("", encoding="utf-8")
    assert _untracked_errors(pkg) == []


# --------------------------------------------------------------------------------------
# Guard against over-broadening: a stray file that merely resembles an exempt name (but isn't)
# is still caught. e.g. a root .txt is not a figure, not mutable, not a receipt.
# --------------------------------------------------------------------------------------

def test_non_exempt_stray_csv_at_root_is_flagged(tmp_path):
    """A stray *.csv at root that is NOT a *_fig_*_data.csv companion must still be flagged."""
    pkg = _sealed_package(tmp_path, extra={"AS-TEST_secret_export.csv": b"a\n1\n"})
    errs = _untracked_errors(pkg)
    assert any("AS-TEST_secret_export.csv" in e for e in errs), verify_checksums(pkg)


def test_non_exempt_neighbor_tree_is_still_flagged(tmp_path):
    """Only the governed post-seal prefixes are exempt; a lookalike directory is not."""
    pkg = _sealed_package(tmp_path, extra={"domain_level_injected/sneaky.csv": b"a\n1\n"})
    errs = _untracked_errors(pkg)
    assert any("domain_level_injected/sneaky.csv" in e for e in errs), verify_checksums(pkg)


def test_blastp_lookalike_neighbor_tree_is_still_flagged(tmp_path):
    """Only exact governed BLASTP post-seal prefixes are exempt."""
    pkg = _sealed_package(tmp_path, extra={"blastp_online_injected/sneaky.csv": b"a\n1\n"})
    errs = _untracked_errors(pkg)
    assert any("blastp_online_injected/sneaky.csv" in e for e in errs), verify_checksums(pkg)


def test_workflow_lookalike_neighbor_tree_and_root_file_are_still_flagged(tmp_path):
    pkg = _sealed_package(tmp_path, extra={
        "mode_b_templates_injected/sneaky.md": b"bad\n",
        "AS-TEST_compiled_report_backup.md": b"bad\n",
    })
    errs = _untracked_errors(pkg)
    assert any("mode_b_templates_injected/sneaky.md" in e for e in errs), errs
    assert any("AS-TEST_compiled_report_backup.md" in e for e in errs), errs

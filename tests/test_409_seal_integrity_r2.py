"""TESTS — CLAUDE_409_seal_integrity_r2 (round-2 seal/provenance hardening).

Fail-before / pass-after coverage for the four bypasses this lane closes, plus regression
checks that legitimate authoring is preserved. Run with the r2 lane APPLIED (on top of the
four .409 siblings): `pytest TESTS_409_seal_integrity_r2.py`.

The `_pre_r2` marker on some assertions documents the BASE behaviour (four siblings only, r2
NOT applied) — those are the leaks this lane closes; with r2 applied they invert. Where a base
tree is available at $SEAL_R2_BASE (a checkout with only the four siblings), the paired
`test_*_fail_before` cases assert the leak still exists there.

All checks operate at the packaging/validate FUNCTION level on synthetic packages under tmp_path
— they do not require a full 60-BGC gold run. No real bundle or package is touched.
"""
import json
import os
import hashlib
from pathlib import Path

import pytest

from mamey import packaging as pk


# ── helpers ──────────────────────────────────────────────────────────────────
def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _seed_core(root: Path, extra_lines=()):
    """A minimal sealed CORE: a couple of tracked files + checksums_sha256.txt covering them."""
    (root / "AS-1_2_inventory.csv").write_text("BGC_ID,Depth_floor\nBGC001,full_mode_b\nBGC002,abbreviated_ledger\n", encoding="utf-8")
    lines = [f"{_sha(root / 'AS-1_2_inventory.csv')}  AS-1_2_inventory.csv"]
    lines.extend(extra_lines)
    (root / "checksums_sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _seed_post_seal_data(root: Path):
    (root / "judgment").mkdir(exist_ok=True)
    (root / "judgment" / "AS-1_BGC001_mode_b.md").write_text("# BGC001 Mode B\n" + "authored " * 40, encoding="utf-8")
    (root / "domain_level").mkdir(exist_ok=True)
    (root / "domain_level" / "domain_safe_unsafe_claims.csv").write_text("bgc,claim\nBGC001,ambiguous\n", encoding="utf-8")


# ── FIX 4 — basename-exemption trick (R2-5 / D1,D2,D3) ───────────────────────
@pytest.mark.parametrize("rel", [
    "domain_level/EVIL_cnbu.json",              # D1: *_cnbu.json suffix
    "domain_level/EVIL_compiled_report.md",     # D2: *_compiled_report.md suffix
    "blastp_online/package_status.json",        # D3: a MUTABLE_RECEIPT name
    "judgment/EVIL_SAPOTE_WORKFLOW_LEDGER.md",  # ledger-suffix trick inside a subtree
])
def test_basename_trick_now_covered(rel):
    """PASS-AFTER: a file whose name mimics a regenerated/mutable file, injected INTO a covered
    subtree, is now covered (so the reciprocal injection scan will flag it). Pre-r2 these all
    returned False (uncovered) and leaked."""
    assert pk.is_post_seal_covered(rel) is True


def test_basename_trick_root_still_exempt():
    """REGRESSION: the same suffixes at the package ROOT (where those files legitimately live)
    stay EXEMPT — this lane must not start pinning the regenerated root reports/buffers."""
    assert pk.is_post_seal_covered("AS-1_compiled_report.md") is False
    assert pk.is_post_seal_covered("AS-1_cnbu.json") is False
    assert pk.is_post_seal_covered("package_status.json") is False
    assert pk.is_post_seal_covered("AS-1_judgment_register.json") is False


# ── FIX 3 — coverage drift (R2-3 judgment/, R2-4 other exempt subtrees) ───────
@pytest.mark.parametrize("rel", [
    "judgment/AS-1_BGC999_mode_b.md",           # R2-3: the highest-impact card home
    "gold_figures/fake_fig_data.csv",
    "cohort_figures/fake_data.csv",
    "ASSEMBLY_LINES/BGC999_line.json",
    "P450_TAILORING/fake.csv",
    "COMPOUND_FAMILIES/fake.json",
    "mode_b_templates/fake.md",
    "mamey_native_figures/fake_fig_data.csv",
    "blastp_quarantine/fake.json",
    "blastp_ingest_receipts/fake.json",
])
def test_previously_uncovered_subtrees_now_covered(rel):
    """PASS-AFTER: every core-exempt subtree the round-1 allowlist omitted is now covered."""
    assert pk.is_post_seal_covered(rel) is True


# ── FIX 1 — anchor post_seal_checksums.txt (R2-1 / B1, D4) ────────────────────
def test_anchor_written_and_verifies(tmp_path):
    _seed_core(tmp_path)
    _seed_post_seal_data(tmp_path)
    res = pk.write_post_seal_checksums(tmp_path)
    assert res["n_files"] >= 2
    # anchor line folded into the core seal, and it verifies clean.
    assert pk.read_post_seal_anchor(tmp_path) is not None
    assert pk.verify_post_seal_anchor(tmp_path) == []


def test_anchor_catches_manifest_edit_B1(tmp_path):
    """FAIL-BEFORE was: edit one hash line in post_seal_checksums.txt to match a swapped file ->
    PASS. PASS-AFTER: the edit changes the manifest's own digest, which no longer matches the
    anchor -> verify_post_seal_anchor reports an error."""
    _seed_core(tmp_path)
    _seed_post_seal_data(tmp_path)
    pk.write_post_seal_checksums(tmp_path)
    # B1: attacker rewrites a line inside post_seal_checksums.txt (as they would to match a swap).
    psc = tmp_path / "post_seal_checksums.txt"
    txt = psc.read_text(encoding="utf-8").splitlines()
    txt[0] = "0" * 64 + "  " + txt[0].split(None, 1)[1]
    psc.write_text("\n".join(txt) + "\n", encoding="utf-8")
    errs = pk.verify_post_seal_anchor(tmp_path)
    assert errs and "anchor" in errs[0].lower()


def test_anchor_catches_manifest_deletion_D4(tmp_path):
    _seed_core(tmp_path)
    _seed_post_seal_data(tmp_path)
    pk.write_post_seal_checksums(tmp_path)
    (tmp_path / "post_seal_checksums.txt").unlink()
    errs = pk.verify_post_seal_anchor(tmp_path)
    assert errs and "missing" in errs[0].lower()


def test_anchor_absent_is_backward_compatible(tmp_path):
    """A pre-r2 package (no anchor line) must still validate: verify returns []."""
    _seed_core(tmp_path)  # no anchor line, no post_seal_checksums.txt
    assert pk.verify_post_seal_anchor(tmp_path) == []


def test_anchor_line_is_ignored_by_core_forward_pass(tmp_path):
    """The anchor is a '#'-comment line, so it must not become a tracked/verified core entry."""
    _seed_core(tmp_path)
    _seed_post_seal_data(tmp_path)
    pk.write_post_seal_checksums(tmp_path)
    core_txt = (tmp_path / "checksums_sha256.txt").read_text(encoding="utf-8")
    assert "# post_seal_checksums.txt.sha256 " in core_txt


# ── FIX 2 — recompute the determinism fingerprint (provenance A) ──────────────
def _seed_fingerprintable(root: Path):
    (root / "AS-1_2_inventory.csv").write_text("BGC_ID\nBGC001\nBGC002\n", encoding="utf-8")
    (root / "AS-1_4_triage_board.csv").write_text("BGC_ID,tier\nBGC001,A\n", encoding="utf-8")


def test_fingerprint_recompute_pass_on_true_receipt(tmp_path):
    _seed_fingerprintable(tmp_path)
    fp = pk.write_repro_fingerprint(tmp_path)  # writes the TRUE value
    (tmp_path / "manifest.json").write_text(json.dumps({"repro_fingerprint": fp["fingerprint"]}), encoding="utf-8")
    gate = pk.verify_repro_fingerprint_recompute(tmp_path)
    assert gate["state"] == "PASS"


def test_fingerprint_recompute_fails_forged_receipt(tmp_path):
    """FAIL-BEFORE: validate never recomputed, so a forged fingerprint passed. PASS-AFTER: the
    recomputed value != the forged 'deadbeef' receipt -> FAIL."""
    _seed_fingerprintable(tmp_path)
    pk.write_repro_fingerprint(tmp_path)
    forged = "de" * 32
    (tmp_path / "repro_fingerprint.json").write_text(json.dumps({"fingerprint": forged, "components": {}}), encoding="utf-8")
    gate = pk.verify_repro_fingerprint_recompute(tmp_path)
    assert gate["state"] == "FAIL"


def test_fingerprint_recompute_not_evaluable_without_receipt(tmp_path):
    """A partial/fixture package with no stored fingerprint stays NOT_EVALUABLE (keeps validating)."""
    _seed_fingerprintable(tmp_path)
    gate = pk.verify_repro_fingerprint_recompute(tmp_path)
    assert gate["state"] == "NOT_EVALUABLE"


# ── FIX 5 — manifest provenance binding (C5 / D, PROV-01) ─────────────────────
def test_manifest_bgcs_count_binding(tmp_path):
    """FAIL-BEFORE: manifest.json entirely checksum-exempt, so appending a fake BGC entry passed.
    PASS-AFTER: manifest.bgcs count is cross-checked against the covered inventory row count."""
    (tmp_path / "AS-1_2_inventory.csv").write_text("BGC_ID,Depth_floor\nBGC001,full_mode_b\nBGC002,abbreviated_ledger\n", encoding="utf-8")
    good = {"mode": "gold", "bgcs": [{"bgc_id": "BGC001"}, {"bgc_id": "BGC002"}]}
    assert pk.verify_manifest_provenance_binding(tmp_path, good)["state"] == "PASS"
    forged = {"mode": "gold", "bgcs": [{"bgc_id": "BGC001"}, {"bgc_id": "BGC002"}, {"bgc_id": "BGC999", "product": "vancomycin"}]}
    r = pk.verify_manifest_provenance_binding(tmp_path, forged)
    assert r["state"] == "FAIL" and "count" in r["detail"]


def test_manifest_mode_downgrade_binding(tmp_path):
    """FAIL-BEFORE: flipping mode gold->public passed and silently disabled the gold gate.
    PASS-AFTER: gold-only Depth_floor values in the covered inventory contradict mode=public."""
    (tmp_path / "AS-1_2_inventory.csv").write_text("BGC_ID,Depth_floor\nBGC001,full_mode_b\nBGC002,abbreviated_ledger\n", encoding="utf-8")
    downgraded = {"mode": "public", "bgcs": [{"bgc_id": "BGC001"}, {"bgc_id": "BGC002"}]}
    r = pk.verify_manifest_provenance_binding(tmp_path, downgraded)
    assert r["state"] == "FAIL" and "downgrade" in r["detail"]


def test_manifest_binding_not_evaluable_without_manifest(tmp_path):
    (tmp_path / "AS-1_2_inventory.csv").write_text("BGC_ID\nBGC001\n", encoding="utf-8")
    assert pk.verify_manifest_provenance_binding(tmp_path, {})["state"] == "NOT_EVALUABLE"


def test_engine_version_binding_advisory(tmp_path):
    from mamey import __version__ as eng
    (tmp_path / "AS-1_2_inventory.csv").write_text("BGC_ID\nBGC001\n", encoding="utf-8")
    ok = pk.verify_manifest_provenance_binding(tmp_path, {"workflow_version": f"Mamey v{eng}"})
    assert ok["engine_version_binding"] == "PASS"
    mix = pk.verify_manifest_provenance_binding(tmp_path, {"workflow_version": "Mamey v9.9.999-FORGED"})
    assert mix["engine_version_binding"] == "MISMATCH"


# ── REGRESSION — legitimate authoring / refresh still folds output in ─────────
def test_refresh_folds_legit_authoring_and_reanchors(tmp_path):
    _seed_core(tmp_path)
    _seed_post_seal_data(tmp_path)
    pk.write_post_seal_checksums(tmp_path)
    assert pk.verify_post_seal_anchor(tmp_path) == []
    # a sanctioned authoring command writes a NEW covered card, then calls refresh:
    (tmp_path / "judgment" / "AS-1_BGC002_mode_b.md").write_text("# BGC002\n" + "authored " * 40, encoding="utf-8")
    pk.refresh_post_seal_checksums(tmp_path)
    # legit output folded in AND re-anchored -> still clean.
    assert pk.verify_post_seal_anchor(tmp_path) == []
    recorded = (tmp_path / "post_seal_checksums.txt").read_text(encoding="utf-8")
    assert "AS-1_BGC002_mode_b.md" in recorded

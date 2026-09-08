"""v9.7.412 round 5 — findings from an end-to-end gold run on the shipped smoke fixture plus
tamper probes against the resulting sealed package. Synthetic inputs only; no scientific claims.

R1  a fresh gold run's own package failed `validate` (rc 1) because figure_receipts.jsonl is
    appended post-seal by mamey/figure_save.py and was never registered as a mutable receipt.
R2  gold_completeness credited cards of pure filler ("x x x") that clear the heading/char floors.
R3  claim_safety_status was trusted as stored, so a card added to judgment/ AFTER the seal was
    never re-scanned and an overclaim kept the package at PASS.
R4  three identity shapes evaded the detector: a verb split by an HTML comment or hyphen-linebreak,
    a label/table product assertion, and a subject-bound "-producing" compound.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from mamey.claim_safety_gate import lint_text  # noqa: E402
from mamey.packaging import MUTABLE_RECEIPT_NAMES  # noqa: E402
from mamey.validate import claim_safety_status_blocks  # noqa: E402


# ── R1 ──────────────────────────────────────────────────────────────────────────────────
def test_r1_figure_receipts_is_a_registered_mutable_receipt():
    """figure_save.py appends this after the seal; unregistered it made every figure-bearing
    package fail its own SEAL-03 reciprocal scan."""
    assert "figure_receipts.jsonl" in MUTABLE_RECEIPT_NAMES


def test_r1_reciprocal_scan_exempts_the_post_seal_figure_receipt():
    from mamey.validate import _checksum_reciprocal_exempt as exempt
    assert exempt("figure_receipts.jsonl") is True


# ── R2 ──────────────────────────────────────────────────────────────────────────────────
def _filler_card(sections: int = 4, filler: str = "x ") -> str:
    return "".join(f"## §{i} Section {i}\n\n" + filler * 120 + "\n\n" for i in range(1, sections + 1))


def _authored_card(sections: int = 4) -> str:
    bodies = [
        "The region carries a modular assembly line with condensation and adenylation domains.",
        "Boundary status is interior; the contig extends well beyond both flanks of this locus.",
        "Comparator similarity stays class level and no product identity is asserted anywhere here.",
        "Missing evidence is recorded explicitly: no measured metabolite data exists for this strain.",
    ]
    return "".join(f"## §{i} Section {i}\n\n{bodies[(i - 1) % len(bodies)]}\n\n" for i in range(1, sections + 1))


def _minimal_but_genuine_card() -> str:
    """Just clears the .409 floors (3 headings, >200 non-whitespace chars): must stay credited."""
    return ("## §1 Identity\n\nExact locus bound to node and region; class-level read only.\n\n"
            "## §2 Boundary\n\nInterior placement, both flanks present on this contig.\n\n"
            "## §3 Evidence\n\nDomain census recorded; comparator similarity is not identity.\n\n")


@pytest.mark.parametrize("text,expected_credit", [(_filler_card(), False), (_authored_card(), True), (_minimal_but_genuine_card(), True)])
def test_r2_filler_cards_are_not_credited_toward_gold_completeness(tmp_path, text, expected_credit):
    """Reproduces the probe: filler clears the .409 heading/char floors, so a lexical-variety floor
    is what separates it from a real card. Thresholds are far inside the real corpus (measured
    minimum 653 distinct tokens, maximum 0.131 single-token share over 1,559 finished cards)."""
    import re
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text)
    distinct = len({w.lower() for w in words})
    counts: dict[str, int] = {}
    for w in words:
        counts[w.lower()] = counts.get(w.lower(), 0) + 1
    top_share = (max(counts.values()) / len(words)) if words else 1.0
    credited = distinct >= 20 and top_share <= 0.5
    assert credited is expected_credit


def test_r2_validate_carries_the_lexical_floors():
    src = (ROOT / "mamey" / "validate.py").read_text(encoding="utf-8")
    assert "_MIN_MODEB_DISTINCT_TOKENS = 20" in src
    assert "_MAX_MODEB_TOP_TOKEN_SHARE = 0.5" in src


# ── R3 ──────────────────────────────────────────────────────────────────────────────────
def _package(tmp_path, stored_status="PASS"):
    pkg = tmp_path / "package"
    (pkg / "judgment").mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "TEST-01", "claim_safety_status": stored_status}), encoding="utf-8")
    return pkg


def test_r3_post_seal_overclaim_card_flips_the_status(tmp_path):
    pkg = _package(tmp_path)
    blocks, status = claim_safety_status_blocks(pkg)
    assert blocks is False and status.startswith("PASS"), status
    (pkg / "judgment" / "TEST-01_BGC001_mode_b.md").write_text(
        "## §1 Identity\n\nBGC001 produces **venezuelin**; this is the confirmed product.\n", encoding="utf-8")
    blocks, status = claim_safety_status_blocks(pkg)
    assert blocks is True and "RECHECK_FAIL" in status, status


def test_r3_waiver_file_still_releases_the_hold(tmp_path):
    pkg = _package(tmp_path)
    (pkg / "judgment" / "TEST-01_BGC001_mode_b.md").write_text("BGC001 produces venezuelin.\n", encoding="utf-8")
    from mamey.validate import CLAIM_SAFETY_WAIVER_NAME
    (pkg / CLAIM_SAFETY_WAIVER_NAME).write_text("{}", encoding="utf-8")
    blocks, status = claim_safety_status_blocks(pkg)
    assert blocks is False and status.endswith("_WAIVED"), status


def test_r3_clean_package_is_not_blocked(tmp_path):
    pkg = _package(tmp_path)
    (pkg / "judgment" / "TEST-01_BGC001_mode_b.md").write_text(
        "## §1 Identity\n\nBGC001 encodes a polyketide synthase with capacity consistent with a macrolide class; judgment deferred.\n",
        encoding="utf-8")
    blocks, _status = claim_safety_status_blocks(pkg)
    assert blocks is False


# ── R4 ──────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text", [
    "BGC001 produ<!-- -->ces venezuelin.",
    "BGC001 synthesi<!--x-->ses venezuelin.",
    "BGC001 pro-\nduces venezuelin.",
    "Product: venezuelin.",
    "| product | venezuelin |",
    "BGC001 is venezuelin-producing.",
])
def test_r4_evaded_identity_shapes_are_now_flagged(text):
    assert lint_text(text), text


@pytest.mark.parametrize("text", [
    # measured on the 1,559-card corpus: these forms must stay clean
    "ectoine-producing bacteria carry dedicated transporters.",
    "a biliverdin-producing heme oxygenase [Streptomyces]",
    "The region encodes a pro-\nduct of unknown class.",
    "Cannot be claimed: that this strain produ<!-- -->ces mycofactocin.",
    "BGC001 encodes a polyketide synthase with capacity consistent with a macrolide class.",
    "The product is unpredicted.",
])
def test_r4_legitimate_prose_stays_clean(text):
    assert lint_text(text) == [], (text, lint_text(text))

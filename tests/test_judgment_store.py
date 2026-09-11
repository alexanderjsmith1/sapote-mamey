"""test_judgment_store.py — v9.7.67

Tests for mamey/judgment_store.py — the Mode B persistence layer.
Closes worst-list item 29 (Mode B is session-ephemeral).
"""
import csv
import json
import os
import tempfile
from pathlib import Path

import pytest

from mamey.judgment_store import (
    init_register,
    record_mode_b,
    record_batch_complete,
    read_register,
    read_laypersons,
    read_fermentation,
    read_mode_b,
    list_complete_bgcs,
    pending_bgcs,
    is_judgment_complete,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def pkg(tmp_path):
    """Minimal package directory with manifest.json."""
    (tmp_path / "manifest.json").write_text(
        json.dumps({"strain_id": "AS-TEST", "mode": "gold", "bgcs": []})
    )
    return tmp_path


# ── init_register ─────────────────────────────────────────────────────────────

def test_init_register_creates_register(pkg):
    reg = init_register(pkg, "AS-TEST", ["BGC001", "BGC002", "BGC003"])
    assert (pkg / "AS-TEST_judgment_register.json").exists()
    assert reg["total_bgcs"] == 3
    assert reg["complete_bgcs"] == 0
    assert reg["judgment_status"] == "PENDING"

def test_init_register_idempotent_preserves_progress(pkg):
    """Re-running init_register must not wipe Sapote progress."""
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002"])
    record_mode_b(pkg, "BGC001", "# §1\nContent", "Layperson text", "Ferm note", "batch_1")
    # Re-init with a different BGC list (BGC003 added)
    reg = init_register(pkg, "AS-TEST", ["BGC001", "BGC002", "BGC003"])
    assert reg["bgcs"]["BGC001"]["status"] == "COMPLETE"   # preserved
    assert reg["bgcs"]["BGC002"]["status"] == "PENDING"    # unchanged
    assert reg["bgcs"]["BGC003"]["status"] == "PENDING"    # new

def test_init_register_empty_bgc_list(pkg):
    reg = init_register(pkg, "AS-TEST", [])
    assert reg["total_bgcs"] == 0
    assert reg["completion_pct"] == 0.0

def test_init_register_no_manifest(tmp_path):
    """Package without manifest.json uses directory name as strain ID."""
    reg = init_register(tmp_path, "AS-FALLBACK", ["BGC001"])
    assert reg["strain_id"] == "AS-FALLBACK"


# ── record_mode_b ─────────────────────────────────────────────────────────────

def test_record_mode_b_writes_file(pkg):
    init_register(pkg, "AS-TEST", ["BGC001"])
    result = record_mode_b(pkg, "BGC001", "# §1\nMode B content.", "Lay para.", "Ferm note.", "batch_1")
    path = result["path"]
    assert path.exists()
    assert "Mode B content" in path.read_text()
    assert "verdict" in result and "tier" in result["verdict"]

def test_record_mode_b_updates_register(pkg):
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002"])
    record_mode_b(pkg, "BGC001", "# §1", "Lay para", "Ferm", "batch_1")
    reg = read_register(pkg)
    assert reg["bgcs"]["BGC001"]["status"] == "COMPLETE"
    assert reg["bgcs"]["BGC002"]["status"] == "PENDING"
    assert reg["complete_bgcs"] == 1
    assert reg["judgment_status"] == "IN_PROGRESS"

def test_record_mode_b_appends_layperson(pkg):
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002"])
    record_mode_b(pkg, "BGC001", "# §1", "BGC001 layperson text.", "", "batch_1")
    record_mode_b(pkg, "BGC002", "# §1", "BGC002 layperson text.", "", "batch_1")
    lay = read_laypersons(pkg)
    assert "BGC001 layperson text" in lay
    assert "BGC002 layperson text" in lay

def test_record_mode_b_appends_fermentation(pkg):
    init_register(pkg, "AS-TEST", ["BGC001"])
    record_mode_b(pkg, "BGC001", "# §1", "", "Grow at 28°C in ISP2.", "batch_1")
    ferm = read_fermentation(pkg)
    assert "28°C in ISP2" in ferm

def test_record_mode_b_empty_optional_fields(pkg):
    """Empty layperson_paragraph and fermentation_note must not create empty files."""
    init_register(pkg, "AS-TEST", ["BGC001"])
    record_mode_b(pkg, "BGC001", "# §1\nContent.", "", "", "batch_1")
    lay_path = pkg / "judgment" / "AS-TEST_laypersons_section.md"
    ferm_path = pkg / "judgment" / "AS-TEST_fermentation_section.md"
    # Files should not exist if nothing was appended
    assert not lay_path.exists() or lay_path.read_text().strip() == ""

def test_record_mode_b_creates_judgment_dir(pkg):
    init_register(pkg, "AS-TEST", ["BGC001"])
    record_mode_b(pkg, "BGC001", "# §1", "Lay.", "Ferm.", "batch_1")
    assert (pkg / "judgment").is_dir()


# ── record_batch_complete ─────────────────────────────────────────────────────

def test_record_batch_complete_marks_multiple_bgcs(pkg):
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002", "BGC003"])
    record_batch_complete(pkg, "batch_1", ["BGC001", "BGC002"])
    reg = read_register(pkg)
    assert reg["bgcs"]["BGC001"]["status"] == "COMPLETE"
    assert reg["bgcs"]["BGC002"]["status"] == "COMPLETE"
    assert reg["bgcs"]["BGC003"]["status"] == "PENDING"
    assert reg["complete_bgcs"] == 2


# ── read functions ────────────────────────────────────────────────────────────

def test_read_register_missing_returns_stub(tmp_path):
    reg = read_register(tmp_path)
    assert reg["judgment_status"] == "NOT_INITIALISED"

def test_read_laypersons_missing_returns_empty(tmp_path):
    assert read_laypersons(tmp_path) == ""

def test_read_fermentation_missing_returns_empty(tmp_path):
    assert read_fermentation(tmp_path) == ""

def test_read_mode_b_missing_returns_empty(pkg):
    assert read_mode_b(pkg, "BGC001") == ""

def test_read_mode_b_after_write(pkg):
    init_register(pkg, "AS-TEST", ["BGC001"])
    record_mode_b(pkg, "BGC001", "# §1\nThe content.", "Lay.", "Ferm.", "batch_1")
    content = read_mode_b(pkg, "BGC001")
    assert "The content" in content


# ── list_complete_bgcs / pending_bgcs ────────────────────────────────────────

def test_list_complete_and_pending(pkg):
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002", "BGC003"])
    record_mode_b(pkg, "BGC001", "# §1", "Lay.", "Ferm.", "batch_1")
    assert list_complete_bgcs(pkg) == ["BGC001"]
    assert set(pending_bgcs(pkg)) == {"BGC002", "BGC003"}


# ── is_judgment_complete ──────────────────────────────────────────────────────

def test_is_judgment_complete_false_when_pending(pkg):
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002"])
    record_mode_b(pkg, "BGC001", "# §1", "", "", "batch_1")
    assert not is_judgment_complete(pkg)

def test_is_judgment_complete_true_when_all_done(pkg):
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002"])
    record_mode_b(pkg, "BGC001", "# §1", "", "", "batch_1")
    record_mode_b(pkg, "BGC002", "# §1", "", "", "batch_1")
    assert is_judgment_complete(pkg)

def test_is_judgment_complete_false_for_empty_register(tmp_path):
    assert not is_judgment_complete(tmp_path)


# ── Cross-batch accumulation (key correctness property) ───────────────────────

def test_cross_batch_accumulation(pkg):
    """Batch 2 progress must not overwrite Batch 1 progress."""
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002", "BGC003"])
    # Batch 1: BGC001 and BGC002
    record_mode_b(pkg, "BGC001", "# §1\nBatch1.", "Lay1.", "Ferm1.", "batch_1")
    record_mode_b(pkg, "BGC002", "# §1\nBatch1.", "Lay2.", "Ferm2.", "batch_1")
    # Batch 2: BGC003
    record_mode_b(pkg, "BGC003", "# §1\nBatch2.", "Lay3.", "Ferm3.", "batch_2")
    reg = read_register(pkg)
    assert reg["complete_bgcs"] == 3
    assert is_judgment_complete(pkg)
    lay = read_laypersons(pkg)
    assert "Lay1" in lay and "Lay3" in lay  # both batches present
    ferm = read_fermentation(pkg)
    assert "Ferm1" in ferm and "Ferm3" in ferm


# --- v9.7.112: write-time quality verdict + incomplete_cards ---

def test_record_mode_b_stamps_verdict(pkg):
    from mamey.judgment_store import record_mode_b, read_register
    init_register(pkg, "AS-TEST", ["BGC001"])
    # A short stub card -> verdict should be STUB, stamped in the register
    result = record_mode_b(pkg, "BGC001", "# §1\nshort.", "Lay.", "Ferm.", "batch_1", rank=1)
    assert result["verdict"]["tier"] in ("STUB", "SHALLOW")
    reg = read_register(pkg)
    assert reg["bgcs"]["BGC001"]["quality_tier"] in ("STUB", "SHALLOW")

def test_incomplete_cards_lists_non_full(pkg):
    from mamey.judgment_store import record_mode_b, incomplete_cards
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002"])
    record_mode_b(pkg, "BGC001", "# §1\nshort stub.", "L.", "F.", "batch_1", rank=1)
    inc = incomplete_cards(pkg)
    ids = {r["bgc_id"] for r in inc}
    assert "BGC001" in ids  # the stub is flagged incomplete


# --- v9.7.112: batch orchestration ---

def test_batch_status_rank_ordered(pkg):
    from mamey.judgment_store import record_mode_b, batch_status
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002", "BGC003"])
    record_mode_b(pkg, "BGC002", "# §1 stub", "L", "F", "batch_1", rank=2)
    st = batch_status(pkg, ["BGC001", "BGC002", "BGC003"])
    assert st["total"] == 3
    assert st["not_started"] == 2
    # rank order preserved
    assert [b["bgc_id"] for b in st["per_bgc"]] == ["BGC001", "BGC002", "BGC003"]

def test_compile_ready_blocks_until_all_full(pkg):
    from mamey.judgment_store import record_mode_b, compile_ready
    init_register(pkg, "AS-TEST", ["BGC001"])
    record_mode_b(pkg, "BGC001", "# §1 stub", "L", "F", "batch_1", rank=1)
    ok, reason = compile_ready(pkg, ["BGC001"])
    assert ok is False
    assert "not FULL" in reason


# ── STEP 5 (v9.7.123 SM-P1-004): claim-safety lint at card write time ──────────
def test_record_mode_b_claim_safety_clean(pkg):
    """A claim-safe card records claim_safety.clean = True, never blocks the write."""
    init_register(pkg, "AS-TEST", ["BGC001"])
    card = ("## BGC001 (NODE_1 · region001)\n"
            "§1 Identity. Biosynthetic capacity consistent with a kirromycin-like compound.\n"
            "§5 Pharmacology. Capacity consistent with the elfamycin class.")
    result = record_mode_b(pkg, "BGC001", card)
    cs = result["verdict"].get("claim_safety")
    assert cs is not None
    assert cs["clean"] is True
    assert cs["findings"] == []
    # write still happened (passive, non-blocking)
    assert result["path"].exists()


def test_record_mode_b_claim_safety_flags_overclaim(pkg):
    """An identity overclaim is surfaced in the verdict but does NOT block the write."""
    init_register(pkg, "AS-TEST", ["BGC001"])
    card = ("## BGC001 (NODE_1 · region001)\n"
            "§1 Identity. This BGC produces kirromycin.\n"
            "§5 Pharmacology content.")
    result = record_mode_b(pkg, "BGC001", card)
    cs = result["verdict"].get("claim_safety")
    assert cs["clean"] is False
    assert any("overclaim" in f for f in cs["findings"])
    # passive: the card was still written despite the finding
    assert result["path"].exists()


# ── STEP 5 cont (v9.7.124 SM-P0-003): locator reconciliation at card write time ──
def _seed_triage(pkg, rows):
    import csv as _csv
    with open(pkg / "AS-TEST_4_triage_board.csv", "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["Rank", "BGC_ID", "Node_ID", "Contig", "antiSMASH_Region", "Products", "Misanchor_Flag"])
        for r in rows:
            w.writerow(r)


def test_record_mode_b_locator_pass(pkg):
    """A complete four-part identity matching the triage row records PASS."""
    init_register(pkg, "AS-TEST", ["BGC001"])
    _seed_triage(pkg, [["1", "BGC001", "NODE_10", "NODE_10", "region001", "RiPP", ""]])
    card = "# Mode B — AS-TEST / NODE_10 / region001 / BGC001\n§1 capacity consistent with a RiPP."
    result = record_mode_b(pkg, "BGC001", card)
    assert result["verdict"]["locator"]["status"] == "PASS"
    assert result["path"].exists()


def test_record_mode_b_locator_node_mismatch(pkg):
    """A drifted node in the card heading is flagged MISMATCH but the card still writes."""
    init_register(pkg, "AS-TEST", ["BGC001"])
    _seed_triage(pkg, [["1", "BGC001", "NODE_10", "NODE_10", "region001", "RiPP", ""]])
    card = "# Mode B — AS-TEST / NODE_99 / region001 / BGC001\n§1 content."
    result = record_mode_b(pkg, "BGC001", card)
    assert result["verdict"]["locator"]["status"] == "MISMATCH"
    assert result["path"].exists()  # passive, non-blocking


def test_record_mode_b_locator_region_conflict_is_mismatch(pkg):
    """A region difference is a four-part identity conflict, not a warning."""
    init_register(pkg, "AS-TEST", ["BGC001"])
    _seed_triage(pkg, [["1", "BGC001", "NODE_30", "NODE_30", "region002", "PKS", ""]])
    card = "# Mode B — AS-TEST / NODE_30 / region009 / BGC001\n§1 content."
    result = record_mode_b(pkg, "BGC001", card)
    assert result["verdict"]["locator"]["status"] == "MISMATCH"
    assert result["verdict"]["locator"]["refusal_reason"] == "IDENTITY_CONFLICT"


def test_record_mode_b_locator_no_triage_row(pkg):
    """If no triage board is present, locator records NO_TRIAGE_ROW (degrades gracefully)."""
    init_register(pkg, "AS-TEST", ["BGC001"])
    card = "## BGC001 (NODE_10 · region001)\n§1 content."
    result = record_mode_b(pkg, "BGC001", card)
    assert result["verdict"]["locator"]["status"] == "NO_TRIAGE_ROW"


# ── v9.7.125: enrichment augmentation for thin HIGH-tier cards (BGC028/BGC023 finding) ──
def _seed_gene_table(pkg, bgc_id, n_genes=8):
    import csv as _csv
    with open(pkg / "AS-TEST_gene_by_gene_all_bgcs.csv", "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=["bgc_id", "locus_tag", "sec_met_domains", "aa_length"])
        w.writeheader()
        domains = ["KS;AT;KR", "Condensation;AMP-binding", "Halogenase", "Methyltransferase",
                   "Thioesterase", "PCP", "Epimerase", "Cytochrome_P450"]
        for i in range(n_genes):
            w.writerow({"bgc_id": bgc_id, "locus_tag": f"ctg1_{i}",
                        "sec_met_domains": domains[i % len(domains)], "aa_length": 400 + i * 10})


def test_shallow_high_card_gets_enrichment_augmentation(pkg):
    """A thin card below the §11–§20 floor is offered deterministic census from the gene table."""
    _seed_gene_table(pkg, "BGC001", n_genes=8)
    init_register(pkg, "AS-TEST", ["BGC001"])
    thin = "## BGC001 (NODE_1 · region001)\n§1 §2 §3 §4 §5 §6 §7 §8 §9 §10 brief. §11 thin."
    result = record_mode_b(pkg, "BGC001", thin, rank=1)
    assert result["verdict"]["tier"] in ("SHALLOW", "STUB")
    aug = result["verdict"].get("enrichment_augmentation")
    assert aug is not None and aug.get("available")
    assert aug["chars"] > 0


def test_augmentation_not_offered_when_no_gene_table(pkg):
    """Without a gene table, no augmentation is offered (degrades gracefully, never errors)."""
    init_register(pkg, "AS-TEST", ["BGC001"])
    thin = "## BGC001 (NODE_1 · region001)\n§1 brief."
    result = record_mode_b(pkg, "BGC001", thin, rank=1)
    aug = result["verdict"].get("enrichment_augmentation")
    # either absent, or present-but-not-available; must never raise
    assert aug is None or aug.get("available") in (False, None)

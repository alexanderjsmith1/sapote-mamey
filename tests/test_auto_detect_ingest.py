"""test_auto_detect_ingest.py — tests for W4 (v9.7.149c).

W4 item 2: `mamey ingest-receipts --auto-detect <pkg>` scans
`<pkg>/judgment/` for `*_mode_b.md` cards not yet in the register and
ingests them.

W4 item 3: `judgment_status` surfaced in `mamey resume` markdown
(alongside `last_sapote_session` which W1 already wired).

Fixtures use AS-XXX only.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from tests._modeb_card_fixtures import valid_modeb_card_stub


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pkg_with_register(tmp_path: pathlib.Path,
                            strain_id: str = "AS-XXX",
                            *,
                            bgc_states: dict[str, str] | None = None,
                            ) -> pathlib.Path:
    """Build a synthetic package with a valid judgment register.

    `bgc_states` maps BGC ID → status ("PENDING" or "COMPLETE"). Defaults to
    BGC001 PENDING, BGC002 PENDING, BGC003 PENDING.
    """
    if bgc_states is None:
        bgc_states = {"BGC001": "PENDING", "BGC002": "PENDING",
                      "BGC003": "PENDING"}

    pkg = tmp_path / strain_id / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain_id}))
    (pkg / "manifest_short.json").write_text(json.dumps(
        {"strain_id": strain_id}))

    total = len(bgc_states)
    done = sum(1 for s in bgc_states.values() if s == "COMPLETE")
    status = ("COMPLETE" if done == total and total > 0
              else "IN_PROGRESS" if done > 0 else "PENDING")
    reg = {
        "schema_version": "1.0",
        "strain_id": strain_id,
        "total_bgcs": total,
        "complete_bgcs": done,
        "completion_pct": round(100.0 * done / total, 1) if total else 0.0,
        "judgment_status": status,
        "last_sapote_session": None,
        "bgcs": {bid: {"status": s, "mode_b_file": None,
                       "session_id": None, "timestamp": None}
                 for bid, s in bgc_states.items()},
    }
    (pkg / f"{strain_id}_judgment_register.json").write_text(json.dumps(reg))

    # Also create the triage board (needed by session_resume in some tests)
    triage_rows = ["BGC_ID,Products,Corrected_rank,Standing_rule"]
    for i, bid in enumerate(bgc_states.keys(), 1):
        triage_rows.append(f"{bid},NRPS,{i},")
    (pkg / f"{strain_id}_4_triage_board.csv").write_text(
        "\n".join(triage_rows) + "\n")

    return pkg


def _write_card(pkg: pathlib.Path, strain_id: str, bgc_id: str,
                content: str | None = None
                ) -> pathlib.Path:
    """Write a Mode B card file at the canonical path.

    content=None (default, v9.7.151): writes a structurally-valid §1-30
    stub via valid_modeb_card_stub() so the card actually clears the
    structure gate — needed since W9 (v9.7.150) lints every card before
    persisting. Pass an explicit content string (e.g. "" or whitespace)
    to test the empty/invalid-card rejection paths specifically.
    """
    jd = pkg / "judgment"
    jd.mkdir(exist_ok=True)
    path = jd / f"{strain_id}_{bgc_id}_mode_b.md"
    if content is None:
        content = valid_modeb_card_stub(bgc_id, strain_id=strain_id)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# auto_detect_ingest()
# ---------------------------------------------------------------------------

def test_auto_detect_finds_and_records_orphan_cards(tmp_path):
    """Headline: cards written to judgment/ but not in the register get
    ingested."""
    from mamey.mode_b_receipt import auto_detect_ingest
    from mamey.judgment_store import read_register

    pkg = _make_pkg_with_register(tmp_path)
    _write_card(pkg, "AS-XXX", "BGC001")
    _write_card(pkg, "AS-XXX", "BGC002")

    summary = auto_detect_ingest(pkg)
    assert set(summary["recorded"]) == {"BGC001", "BGC002"}
    assert summary["scanned_count"] == 2

    reg = read_register(pkg)
    assert reg["bgcs"]["BGC001"]["status"] == "COMPLETE"
    assert reg["bgcs"]["BGC002"]["status"] == "COMPLETE"
    assert reg["bgcs"]["BGC003"]["status"] == "PENDING"  # no card → untouched


def test_auto_detect_skips_already_complete_bgcs(tmp_path):
    """Idempotent: a BGC already marked COMPLETE in the register is not
    re-ingested."""
    from mamey.mode_b_receipt import auto_detect_ingest

    pkg = _make_pkg_with_register(
        tmp_path,
        bgc_states={"BGC001": "COMPLETE", "BGC002": "PENDING"},
    )
    _write_card(pkg, "AS-XXX", "BGC001")
    _write_card(pkg, "AS-XXX", "BGC002")

    summary = auto_detect_ingest(pkg)
    assert summary["recorded"] == ["BGC002"]
    assert summary["skipped_already_complete"] == ["BGC001"]


def test_auto_detect_skips_unknown_bgcs_never_invents(tmp_path):
    """A card for a BGC not in the register is SKIPPED, never invented.

    Mirrors the receipt-ingest contract — the register is the source of
    truth for which BGCs exist; the card files are content.
    """
    from mamey.mode_b_receipt import auto_detect_ingest
    from mamey.judgment_store import read_register

    pkg = _make_pkg_with_register(
        tmp_path,
        bgc_states={"BGC001": "PENDING"},
    )
    _write_card(pkg, "AS-XXX", "BGC001")
    _write_card(pkg, "AS-XXX", "BGC999")  # not in register

    summary = auto_detect_ingest(pkg)
    assert summary["recorded"] == ["BGC001"]
    assert summary["skipped_unknown"] == ["BGC999"]
    reg = read_register(pkg)
    assert "BGC999" not in reg["bgcs"], "must not invent BGCs"


def test_auto_detect_updates_judgment_status_after_ingest(tmp_path):
    """When all PENDING BGCs get cards ingested, the register's
    judgment_status rolls up to COMPLETE."""
    from mamey.mode_b_receipt import auto_detect_ingest

    pkg = _make_pkg_with_register(
        tmp_path,
        bgc_states={"BGC001": "PENDING", "BGC002": "PENDING"},
    )
    _write_card(pkg, "AS-XXX", "BGC001")
    _write_card(pkg, "AS-XXX", "BGC002")

    summary = auto_detect_ingest(pkg)
    assert summary["judgment_status"] == "COMPLETE"


def test_auto_detect_handles_no_judgment_dir(tmp_path):
    """No judgment/ directory at all — degrades silently. Shouldn't create
    one as a side effect either (F2 contract)."""
    from mamey.mode_b_receipt import auto_detect_ingest

    pkg = _make_pkg_with_register(tmp_path)
    summary = auto_detect_ingest(pkg)
    assert summary["recorded"] == []
    assert summary["scanned_count"] == 0
    assert not (pkg / "judgment").exists(), (
        "auto_detect_ingest must not create judgment/ as a side effect"
    )


def test_auto_detect_ignores_empty_card_files(tmp_path):
    """An empty Mode B file shouldn't be recorded as a completed card."""
    from mamey.mode_b_receipt import auto_detect_ingest

    pkg = _make_pkg_with_register(tmp_path)
    _write_card(pkg, "AS-XXX", "BGC001", content="")
    _write_card(pkg, "AS-XXX", "BGC002", content="   \n   \n")
    _write_card(pkg, "AS-XXX", "BGC003", content=valid_modeb_card_stub("BGC003", strain_id="AS-XXX"))

    summary = auto_detect_ingest(pkg)
    assert summary["recorded"] == ["BGC003"]


def test_auto_detect_ignores_non_canonical_filenames(tmp_path):
    """Files in judgment/ that don't match `<strain>_<BGC>_mode_b.md` are
    skipped — defensive against e.g. backup files or `.tmp` files."""
    from mamey.mode_b_receipt import auto_detect_ingest

    pkg = _make_pkg_with_register(tmp_path)
    jd = pkg / "judgment"
    jd.mkdir()
    # Canonical
    (jd / "AS-XXX_BGC001_mode_b.md").write_text(
        valid_modeb_card_stub("BGC001", strain_id="AS-XXX"))
    # Non-canonical — wrong strain prefix
    (jd / "WRONG_BGC002_mode_b.md").write_text("## ignored")
    # Non-canonical — no suffix
    (jd / "AS-XXX_BGC003.md").write_text("## ignored")

    summary = auto_detect_ingest(pkg)
    assert summary["recorded"] == ["BGC001"]


# ---------------------------------------------------------------------------
# W4 item 3 — session_resume surfaces judgment_status
# ---------------------------------------------------------------------------

def test_session_resume_surfaces_judgment_status_in_markdown(tmp_path):
    from mamey.session_resume import build_resume

    pkg = _make_pkg_with_register(
        tmp_path,
        bgc_states={"BGC001": "COMPLETE", "BGC002": "PENDING"},
    )
    result = build_resume(pkg)
    assert result["judgment_status"] == "IN_PROGRESS"
    assert "**Judgment status:** IN_PROGRESS" in result["markdown"]


def test_session_resume_judgment_status_complete(tmp_path):
    from mamey.session_resume import build_resume

    pkg = _make_pkg_with_register(
        tmp_path,
        bgc_states={"BGC001": "COMPLETE"},
    )
    result = build_resume(pkg)
    assert result["judgment_status"] == "COMPLETE"


# ---------------------------------------------------------------------------
# End-to-end: auto-detect → resume shows the bump
# ---------------------------------------------------------------------------

def test_end_to_end_auto_detect_then_resume_shows_completion(tmp_path):
    """After auto_detect_ingest runs, `mamey resume` should reflect the new
    judgment_status without any other action."""
    from mamey.mode_b_receipt import auto_detect_ingest
    from mamey.session_resume import build_resume

    pkg = _make_pkg_with_register(
        tmp_path,
        bgc_states={"BGC001": "PENDING", "BGC002": "PENDING"},
    )
    # Pre-state: pending
    pre = build_resume(pkg)
    assert pre["judgment_status"] == "PENDING"
    assert pre["done"] == []

    # Drop cards into judgment/ as if a chat had written them
    _write_card(pkg, "AS-XXX", "BGC001")
    _write_card(pkg, "AS-XXX", "BGC002")

    # Run auto-detect
    auto_detect_ingest(pkg)

    # Post-state: resume reflects completion without any further action
    post = build_resume(pkg)
    assert post["judgment_status"] == "COMPLETE"
    assert set(post["done"]) == {"BGC001", "BGC002"}

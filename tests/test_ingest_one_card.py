"""test_ingest_one_card.py — tests for N4 + N5 (v9.7.149c).

N4: `mamey ingest-receipts --card <file.md>` — synchronous one-card persistence
    alongside the receipt and auto-detect flows.

N5: `auto_detect_ingest` and `ingest_one_card` both parse the session ID
    from the card's `<!-- MODE B: <BGC> | strain: <S> | session: <id> | <ts> -->`
    header (written by record_mode_b in judgment_store.py:356) so re-ingested
    cards preserve the original session ID rather than overwriting it.

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
    """Build a synthetic package with a valid judgment register."""
    if bgc_states is None:
        bgc_states = {"BGC001": "PENDING", "BGC002": "PENDING"}

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
    return pkg


def _card_with_header(bgc_id: str, strain: str, session_id: str,
                      body: str | None = None
                      ) -> str:
    """Build a Mode B card string with the canonical header that record_mode_b
    writes (mirrors judgment_store.py:356-358).

    body=None (default, v9.7.151): uses valid_modeb_card_stub() content so the
    resulting card actually clears the structure gate — needed since W9
    (v9.7.150) lints every card before persisting. Pass an explicit body
    (e.g. for the "bare body, no header" tests) to exercise BGC-ID-resolution
    edge cases specifically — those tests aren't exercising card validity.
    """
    if body is None:
        # Strip the leading title line — _card_with_header supplies its own header
        full = valid_modeb_card_stub(bgc_id, strain_id=strain)
        body = full.split("\n", 2)[2]  # drop "# Mode B — ..." title + blank line
    return (
        f"<!-- MODE B: {bgc_id} | strain: {strain} | "
        f"session: {session_id} | 2026-06-29T12:00:00Z -->\n\n"
        + body
    )


# ---------------------------------------------------------------------------
# _parse_card_session_id + _parse_card_bgc_id (N5)
# ---------------------------------------------------------------------------

def test_parse_session_id_extracts_from_canonical_header(tmp_path):
    from mamey.mode_b_receipt import _parse_card_session_id
    content = _card_with_header("BGC001", "AS-XXX", "S-2026-06-29-batch3")
    assert _parse_card_session_id(content) == "S-2026-06-29-batch3"


def test_parse_session_id_empty_when_no_header(tmp_path):
    from mamey.mode_b_receipt import _parse_card_session_id
    assert _parse_card_session_id("no header here") == ""
    assert _parse_card_session_id("") == ""


def test_parse_bgc_id_extracts_from_canonical_header(tmp_path):
    from mamey.mode_b_receipt import _parse_card_bgc_id
    content = _card_with_header("BGC042", "AS-XXX", "S-9")
    assert _parse_card_bgc_id(content) == "BGC042"


# ---------------------------------------------------------------------------
# N5 — auto_detect preserves original session ID
# ---------------------------------------------------------------------------

def test_auto_detect_preserves_session_id_from_card_header(tmp_path):
    """When a card carries a `session:` header, auto_detect should record
    that session ID — not the generic 'auto-detect' placeholder."""
    from mamey.mode_b_receipt import auto_detect_ingest
    from mamey.judgment_store import read_register

    pkg = _make_pkg_with_register(tmp_path)
    jd = pkg / "judgment"
    jd.mkdir()
    (jd / "AS-XXX_BGC001_mode_b.md").write_text(
        _card_with_header("BGC001", "AS-XXX", "S-2026-06-29-batch3"))

    auto_detect_ingest(pkg)

    reg = read_register(pkg)
    assert reg["bgcs"]["BGC001"]["session_id"] == "S-2026-06-29-batch3", (
        "auto-detect should have preserved the card's original session ID"
    )
    # last_sapote_session is set at register-level too
    assert reg.get("last_sapote_session") == "S-2026-06-29-batch3"


def test_auto_detect_falls_back_when_no_session_header(tmp_path):
    """Card with no header → falls back to 'auto-detect' as session ID."""
    from mamey.mode_b_receipt import auto_detect_ingest
    from mamey.judgment_store import read_register

    pkg = _make_pkg_with_register(tmp_path)
    jd = pkg / "judgment"
    jd.mkdir()
    # v9.7.151: needs to be structurally valid (no MODE B header by design —
    # that's what this test is about — but the §1-30 contract still applies).
    full_card = valid_modeb_card_stub("BGC001", strain_id="AS-XXX")
    body_only = full_card.split("\n", 2)[2]  # drop the "# Mode B — ..." title line
    (jd / "AS-XXX_BGC001_mode_b.md").write_text(body_only)

    auto_detect_ingest(pkg)

    reg = read_register(pkg)
    assert reg["bgcs"]["BGC001"]["session_id"] == "auto-detect"


# ---------------------------------------------------------------------------
# N4 — ingest_one_card
# ---------------------------------------------------------------------------

def test_ingest_one_card_records_canonical_filename(tmp_path):
    """Headline: a single card file gets persisted via ingest_one_card."""
    from mamey.mode_b_receipt import ingest_one_card
    from mamey.judgment_store import read_register

    pkg = _make_pkg_with_register(tmp_path)
    card = tmp_path / "AS-XXX_BGC001_mode_b.md"
    card.write_text(_card_with_header("BGC001", "AS-XXX", "S-9"))

    summary = ingest_one_card(pkg, card)
    assert summary["status"] == "RECORDED"
    assert summary["bgc_id"] == "BGC001"
    assert summary["session_id"] == "S-9"

    reg = read_register(pkg)
    assert reg["bgcs"]["BGC001"]["status"] == "COMPLETE"
    assert reg["bgcs"]["BGC001"]["session_id"] == "S-9"


def test_ingest_one_card_resolves_bgc_from_header_when_filename_doesnt_match(tmp_path):
    """Card filename doesn't match `<strain>_<BGC>_mode_b.md` — but the
    card's header carries `MODE B: BGC001`. Header wins."""
    from mamey.mode_b_receipt import ingest_one_card
    from mamey.judgment_store import read_register

    pkg = _make_pkg_with_register(tmp_path)
    # Filename has no BGC ID at all
    card = tmp_path / "random_name.md"
    card.write_text(_card_with_header("BGC001", "AS-XXX", "S-9"))

    summary = ingest_one_card(pkg, card)
    assert summary["status"] == "RECORDED"
    assert summary["bgc_id"] == "BGC001"
    reg = read_register(pkg)
    assert reg["bgcs"]["BGC001"]["status"] == "COMPLETE"


def test_ingest_one_card_resolves_bgc_from_filename_when_no_header(tmp_path):
    """Card has no header but canonical filename — filename pattern parses
    the BGC ID. Session ID defaults to 'card-ingest'."""
    from mamey.mode_b_receipt import ingest_one_card
    from mamey.judgment_store import read_register

    pkg = _make_pkg_with_register(tmp_path)
    card = tmp_path / "AS-XXX_BGC002_mode_b.md"
    # v9.7.151: needs to be structurally valid; no MODE B header by design.
    full_card = valid_modeb_card_stub("BGC002", strain_id="AS-XXX")
    body_only = full_card.split("\n", 2)[2]  # drop the "# Mode B — ..." title line
    card.write_text(body_only)

    summary = ingest_one_card(pkg, card)
    assert summary["status"] == "RECORDED"
    assert summary["bgc_id"] == "BGC002"
    assert summary["session_id"] == "card-ingest"


def test_ingest_one_card_skips_unknown_bgc(tmp_path):
    """BGC in card header not in the register → SKIPPED_UNKNOWN, no record."""
    from mamey.mode_b_receipt import ingest_one_card
    from mamey.judgment_store import read_register

    pkg = _make_pkg_with_register(tmp_path)
    card = tmp_path / "card.md"
    card.write_text(_card_with_header("BGC999", "AS-XXX", "S-9"))

    summary = ingest_one_card(pkg, card)
    assert summary["status"] == "SKIPPED_UNKNOWN"
    reg = read_register(pkg)
    assert "BGC999" not in reg["bgcs"]


def test_ingest_one_card_idempotent_on_already_complete(tmp_path):
    """BGC already COMPLETE → SKIPPED_ALREADY_COMPLETE; no re-record."""
    from mamey.mode_b_receipt import ingest_one_card

    pkg = _make_pkg_with_register(
        tmp_path,
        bgc_states={"BGC001": "COMPLETE"},
    )
    card = tmp_path / "card.md"
    card.write_text(_card_with_header("BGC001", "AS-XXX", "S-9"))

    summary = ingest_one_card(pkg, card)
    assert summary["status"] == "SKIPPED_ALREADY_COMPLETE"


def test_ingest_one_card_handles_missing_file(tmp_path):
    """Nonexistent path → BAD_PATH, no raise."""
    from mamey.mode_b_receipt import ingest_one_card
    pkg = _make_pkg_with_register(tmp_path)
    summary = ingest_one_card(pkg, tmp_path / "does_not_exist.md")
    assert summary["status"] == "BAD_PATH"


def test_ingest_one_card_handles_unresolved_bgc(tmp_path):
    """A file with no resolvable BGC (no header, non-canonical filename)
    returns UNRESOLVED_BGC, not a wild guess."""
    from mamey.mode_b_receipt import ingest_one_card
    pkg = _make_pkg_with_register(tmp_path)
    card = tmp_path / "untitled.md"
    card.write_text("## §1\n\nNo BGC ID anywhere.\n")
    summary = ingest_one_card(pkg, card)
    assert summary["status"] == "UNRESOLVED_BGC"

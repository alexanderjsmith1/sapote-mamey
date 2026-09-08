"""mode_b_receipt.py — ingest Sapote Mode B judgment back into the durable store.

THE PROBLEM THIS SOLVES (P-D)
-----------------------------
The judgment layer (Sapote / Claude) produces the real §1-§48 Mode B cards. The
write path to persist them — ``judgment_store.record_mode_b`` — already exists,
and the read-back into the master workbook — ``master_workbook.update_e1_from_judgment``
— already exists. What was MISSING was the front door: a documented contract a
Sapote session emits at the end of a Mode B batch, plus a one-shot command that
consumes it and drives both halves. Without it, finished cards were saved as loose
files in chat outputs and never reached the register or the workbook's E1 sheet —
the data fell on the floor.

THE RECEIPT CONTRACT (``mode_b_receipt.json``)
----------------------------------------------
A Sapote session writes ONE json file describing the cards it produced. Minimal
shape (only ``bgc_id`` + ``mode_b_md`` are required per entry)::

    {
      "schema_version": "mode-b-receipt-1.0",
      "strain_id": "AS-XXX",                 # optional; resolved from package if absent
      "session_id": "sapote_2026-06-19_AF",  # optional; defaults to "sapote"
      "cards": [
        {
          "bgc_id": "BGC018",
          "mode_b_md": "# §1 Identity ...\n...full §1-§48 markdown...",
          "layperson_paragraph": "In plain terms, ...",   # optional
          "fermentation_note": "Aqueous/SAX fractionation ..."  # optional
        },
        ...
      ]
    }

INGEST (``mamey ingest-receipts``)
----------------------------------
For each card: calls ``record_mode_b`` (writes the per-BGC .md, appends the
layperson/fermentation sections, flips the register row to COMPLETE). Then, if a
``--master`` workbook is given, calls ``update_e1_from_judgment`` so E1_Mode_B_Index
and A4_Completeness_Audit reconcile from the now-updated register.

Fail-closed and idempotent: an unknown ``bgc_id`` (not in the register) is reported
and skipped rather than silently invented; re-ingesting the same receipt is a no-op
beyond refreshing timestamps (record_mode_b overwrites the card, register dedups).
"""

from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import json
import hashlib
import csv
import re
import sys
from pathlib import Path
from typing import Any

RECEIPT_SCHEMA_VERSION = "mode-b-receipt-1.0"
NATIVE_MODE_B_RECEIPT_SCHEMAS = {"mode_b_coverage_receipt_v1", "mode_b_coverage_receipt_v2"}


def _load_receipt(receipt_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"Receipt not found: {receipt_path}")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as e:  # v9.7.410: a 200k-deep `[[[[…` partial write raises RecursionError (a RuntimeError subclass, not ValueError) — route it to the same fail-closed ValueError the CLI boundary catches instead of crashing
        raise ValueError(f"Receipt is not valid JSON ({receipt_path}): {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Receipt root must be a JSON object")
    if "cards" not in data or not isinstance(data["cards"], list):
        # v9.7.141: native mode-b coverage receipts from older v9.7.140 runs are
        # coverage-only, not authored Sapote receipts. Accept them as a no-card
        # coverage receipt instead of failing the handoff. New mode-b emits v2
        # receipts with a real `cards` array and will ingest normally.
        if data.get("schema_version") in NATIVE_MODE_B_RECEIPT_SCHEMAS:
            data = dict(data)
            data["cards"] = []
            data["coverage_only"] = True
        else:
            raise ValueError("Receipt must contain a 'cards' array")
    return data


def ingest_receipt(
    package_dir: str | Path,
    receipt_path: str | Path,
    master_workbook_path: str | Path | None = None,
    *,
    force_structure: bool = False,
) -> dict[str, Any]:
    """Ingest one mode_b_receipt.json into the judgment store (and optionally the workbook).

    Returns a summary dict::

        {"strain_id", "recorded": [bgc_ids],
         "recorded_with_structure_override": [bgc_ids],
         "skipped_unknown": [bgc_ids],
         "skipped_no_content": [bgc_ids],
         "skipped_identity_mismatch": [{receipt_bgc_id, card_bgc_id, ...}],
         "skipped_structure_invalid": [(bgc_id, n_errors), ...],
         "register_status", "e1_updated": bool, "e1_summary"}

    Idempotent and fail-closed: receipt/package strain conflicts raise before any
    card write; card-header/package identity conflicts and unknown BGCs are
    skipped and reported. Structure-invalid cards (W9, v9.7.150+) are skipped
    unless force_structure=True. Identity conflicts are never overridable.
    """
    from .judgment_store import read_register, record_mode_b
    try:
        from .modeb_structure_gate import lint_card as _lint_card
        _gate_available = True
    except Exception:
        _gate_available = False

    pkg = Path(package_dir)
    receipt = _load_receipt(Path(receipt_path))

    sv = receipt.get("schema_version", "")
    if sv and sv != RECEIPT_SCHEMA_VERSION:
        # Forward-compatible: warn but proceed on a different minor; the card shape is stable.
        # Native mode-b coverage receipts are explicitly accepted: v2 carries ingest-compatible
        # cards; v1 is coverage-only and records no judgment cards.
        if sv in NATIVE_MODE_B_RECEIPT_SCHEMAS:
            emit(
                f"INFO: consuming native mode-b coverage receipt '{sv}'.",
                file=sys.stderr,
            )
        else:
            emit(
                f"WARNING: receipt schema_version '{sv}' != expected '{RECEIPT_SCHEMA_VERSION}'; "
                "proceeding (card shape is stable).",
                file=sys.stderr,
            )

    reg = read_register(pkg)
    if reg.get("judgment_status") in ("NOT_INITIALISED", "CORRUPT"):
        raise ValueError(
            f"Judgment register at {pkg} is {reg.get('judgment_status')} — "
            "run a Mamey extraction first so the register exists."
        )
    package_strain = str(reg.get("strain_id") or "").strip()
    receipt_strain = str(receipt.get("strain_id") or "").strip()
    if receipt_strain and receipt_strain != package_strain:
        raise ValueError(
            "Receipt strain_id conflicts with the package judgment register: "
            f"{receipt_strain!r} != {package_strain!r}"
        )
    known_bgcs = set(reg.get("bgcs", {}).keys())

    session_id = receipt.get("session_id", "sapote")
    recorded: list[str] = []
    recorded_with_override: list[str] = []
    skipped_unknown: list[str] = []
    skipped_no_content: list[str] = []
    skipped_identity_mismatch: list[dict[str, str]] = []
    skipped_structure_invalid: list[tuple[str, int]] = []

    for card in receipt["cards"]:
        bgc_id = (card.get("bgc_id") or "").strip()
        if not bgc_id:
            continue
        mode_b_md = card.get("mode_b_md", "") or ""
        if not mode_b_md.strip():
            skipped_no_content.append(bgc_id)
            continue
        card_bgc_id = _parse_card_bgc_id(mode_b_md)
        card_strain = _parse_card_strain_id(mode_b_md)
        mismatch_reasons: list[str] = []
        if card_bgc_id and card_bgc_id != bgc_id:
            mismatch_reasons.append("CARD_BGC_MISMATCH")
        if card_strain and card_strain != package_strain:
            mismatch_reasons.append("CARD_STRAIN_MISMATCH")
        package_locus_mismatch = None
        if not mismatch_reasons:
            package_locus_mismatch = _card_identity_mismatch(
                mode_b_md, pkg, package_strain, bgc_id
            )
            if package_locus_mismatch:
                mismatch_reasons.append("CARD_PACKAGE_LOCUS_MISMATCH")
        if mismatch_reasons:
            mismatch = {
                "receipt_bgc_id": bgc_id,
                "card_bgc_id": card_bgc_id,
                "card_strain_id": card_strain,
                "package_strain_id": package_strain,
                "reason": ";".join(mismatch_reasons),
            }
            if package_locus_mismatch:
                mismatch["expected_locus"] = package_locus_mismatch[0]
                mismatch["card_locus"] = package_locus_mismatch[1]
            skipped_identity_mismatch.append(mismatch)
            emit(
                f"  IDENTITY: {bgc_id} — {';'.join(mismatch_reasons)}; "
                "card not recorded",
                file=sys.stderr,
            )
            continue
        # Fail-closed: never invent a register row for an unknown BGC.
        if bgc_id not in known_bgcs:
            skipped_unknown.append(bgc_id)
            continue

        # ----- W9 structure gate -----
        n_errors = 0
        if True:  # v9.7.409 A7 (G3): the gate block now ALWAYS runs; an unavailable gate raises into the
            # existing UNAVAILABLE handler below instead of skipping it (which recorded the card clean).
            try:
                if not _gate_available:
                    raise ImportError("modeb_structure_gate import failed")
                ctx = _bgc_context_from_triage(pkg, bgc_id)
                findings = _lint_card(mode_b_md, bgc_context=ctx, check_evidence_presence=True)  # item 4: §4 coverage/named-subject enforced at receipt
                n_errors = sum(1 for f in findings
                               if f.get("severity") == "ERROR")
                if n_errors:
                    emit(f"  STRUCTURE: {bgc_id} — {n_errors} ERROR(s) vs "
                          "§1–§48 contract", file=sys.stderr)
            except Exception as _gate_exc:
                # v9.7.335 (extension): this was `n_errors = 0  # gate fail-open`, the same
                # defect .335 closed in ingest_one_card — and this is the PRIMARY documented
                # Sapote->durable-store path, so the fail-open mattered more here. A gate that
                # crashed is an UNVERIFIED card, not a clean one; route it to the existing
                # structure-invalid skip instead of recording it.
                n_errors = 1
                emit(f"  STRUCTURE: {bgc_id} — gate UNAVAILABLE "
                      f"({type(_gate_exc).__name__}); card treated as UNVERIFIED, not clean",
                      file=sys.stderr)
        if n_errors and not force_structure:
            skipped_structure_invalid.append((bgc_id, n_errors))
            continue

        # Quality gate: evaluate depth but do NOT block ingest.
        # v9.7.371 fix: rank/edge_status were never threaded through -- every card was always
        # scored at the most lenient LOW floor with no fragment exemption. Recompute ctx here
        # (cheap, idempotent) rather than reusing the gate-branch-scoped `ctx` above, since that
        # variable is only bound when _gate_available is True.
        _q_ctx = _bgc_context_from_triage(pkg, bgc_id)
        _q_rank, _q_edge, _q_cds = _rank_and_edge_from_ctx(_q_ctx)
        from .mode_b_quality_gate import evaluate_card
        verdict = evaluate_card(bgc_id, mode_b_md, rank=_q_rank, edge_status=_q_edge, cds_count=_q_cds)
        if verdict.tier == "SHALLOW":
            emit(f"  WARNING: {bgc_id} — {verdict.message}", file=sys.stderr)
        elif verdict.tier == "STUB":
            emit(f"  CRITICAL: {bgc_id} — {verdict.message}", file=sys.stderr)
        record_mode_b(
            pkg,
            bgc_id,
            mode_b_md=mode_b_md,
            layperson_paragraph=card.get("layperson_paragraph", "") or "",
            fermentation_note=card.get("fermentation_note", "") or "",
            session_id=session_id,
            rank=_q_rank,
            edge_status=_q_edge,
            cds_count=_q_cds,
        )
        if n_errors:
            recorded_with_override.append(bgc_id)
        else:
            recorded.append(bgc_id)

    # Quality summary across all ingested cards.
    from .mode_b_quality_gate import evaluate_batch, summary_line
    all_cards = [c for c in receipt["cards"]
                 if (c.get("bgc_id", "").strip() in known_bgcs
                     and (c.get("mode_b_md") or "").strip()
                     and (_parse_card_bgc_id(c.get("mode_b_md") or "")
                          in ("", c.get("bgc_id", "").strip()))
                     and (_parse_card_strain_id(c.get("mode_b_md") or "")
                          in ("", package_strain)))]
    verdicts = evaluate_batch(all_cards)
    quality_summary = summary_line(verdicts)

    reg_after = read_register(pkg)
    summary: dict[str, Any] = {
        "strain_id": reg_after.get("strain_id"),
        "recorded": recorded,
        "recorded_with_structure_override": recorded_with_override,
        "skipped_unknown": skipped_unknown,
        "skipped_no_content": skipped_no_content,
        "skipped_identity_mismatch": skipped_identity_mismatch,
        "skipped_structure_invalid": skipped_structure_invalid,
        "register_status": reg_after.get("judgment_status"),
        "complete_bgcs": reg_after.get("complete_bgcs"),
        "total_bgcs": reg_after.get("total_bgcs"),
        "quality": quality_summary,
        "quality_verdicts": [{"bgc_id": v.bgc_id, "tier": v.tier, "chars": v.char_count,
                              "gene_mentions": v.gene_mentions} for v in verdicts],
        "e1_updated": False,
        "e1_summary": None,
        "coverage_receipt": {
            "schema_version": sv,
            "coverage_only": bool(receipt.get("coverage_only", False)),
            "coverage_status": receipt.get("coverage_status"),
            "inventory_bgc_count": receipt.get("inventory_bgc_count"),
            "emitted_card_count": receipt.get("emitted_card_count"),
            "missing_bgc_ids": receipt.get("missing_bgc_ids", []),
        } if sv in NATIVE_MODE_B_RECEIPT_SCHEMAS else None,
    }

    if master_workbook_path:
        from .master_workbook import update_e1_from_judgment

        e1_summary = update_e1_from_judgment(pkg, master_workbook_path)
        summary["e1_updated"] = True
        summary["e1_summary"] = e1_summary

    return summary


def auto_detect_ingest(package_dir: str | Path,
                       *,
                       force_structure: bool = False) -> dict[str, Any]:
    """Scan `<pkg>/judgment/` for `*_mode_b.md` cards not yet in the register
    and ingest them.

    Use case: an analysis chat wrote Mode B card files into `judgment/`
    directly (via record_mode_b's atomic write) but never emitted a
    `mode_b_receipt.json` — or a chat session ended before the receipt
    flow ran. `--auto-detect` recovers by reading the card files directly.

    Filename convention (set by `judgment_store._mode_b_path()`):
        `<strain>_<BGC_ID>_mode_b.md`

    For each card whose BGC is in the register AND not already COMPLETE,
    the card content is recorded via `record_mode_b()`. BGCs already
    COMPLETE are skipped (idempotent). BGCs not in the register are
    skipped (never invented).

    Session ID is parsed from the card's `<!-- MODE B: ... session: <id> ... -->`
    header (N5, v9.7.149c) when present, so re-ingested cards preserve the
    original session ID rather than overwriting with "auto-detect". Falls
    back to "auto-detect" only when no header is parseable.

    Structure gate (W9, v9.7.150+):
        Each candidate card is linted against the §1–§48 contract before
        write. Cards with ERROR-severity findings are skipped (listed in
        `skipped_structure_invalid`) unless force_structure=True, in which
        case they are recorded and listed in `recorded_with_structure_override`.
        This is the firebreak for the BGC033 wrong-scaffold recurrence.

    Returns:
        {"strain_id": <str>,
         "recorded": [bgc_id, ...],
         "recorded_with_structure_override": [bgc_id, ...],
         "skipped_already_complete": [bgc_id, ...],
         "skipped_unknown": [bgc_id, ...],
         "skipped_structure_invalid": [(bgc_id, n_errors), ...],
         "judgment_status": <register status after ingest>,
         "scanned_count": <int>}

    Never raises on a missing/empty judgment dir — returns recorded=[].

    W4 item 2 (v9.7.149c) + W9 structure-gate (v9.7.150+).
    """
    from .judgment_store import (
        _judgment_dir_read, _strain_from_pkg,
        read_register, record_mode_b,
    )
    try:
        from .modeb_structure_gate import lint_card as _lint_card
        _gate_available = True
    except Exception:
        _gate_available = False

    pkg = Path(package_dir)
    strain = _strain_from_pkg(pkg)
    judgment = _judgment_dir_read(pkg)

    summary: dict[str, Any] = {
        "strain_id": strain,
        "recorded": [],
        "recorded_with_structure_override": [],
        "skipped_already_complete": [],
        "skipped_unknown": [],
        "skipped_structure_invalid": [],
        # v9.7.152 (AS-XXX Bug 1): recognizable near-miss filenames (e.g.
        # 'BGC006_mode_b.md' missing the '<strain>_' prefix) that would
        # otherwise be silently skipped — surfaced loudly so a card author
        # isn't left with 'scanned: N, recorded: 0' and no diagnostic.
        "skipped_misnamed": [],
        "judgment_status": None,
        "scanned_count": 0,
    }

    if not judgment.is_dir():
        # No judgment dir — nothing to ingest. Surface register status.
        reg = read_register(pkg)
        summary["judgment_status"] = reg.get("judgment_status")
        return summary

    reg = read_register(pkg)
    if reg.get("judgment_status") in ("NOT_INITIALISED", "CORRUPT"):
        summary["judgment_status"] = reg.get("judgment_status")
        return summary

    known_bgcs = reg.get("bgcs", {})
    cards = sorted(judgment.glob("*_mode_b.md"))
    summary["scanned_count"] = len(cards)

    # Parse `<strain>_<BGC_ID>_mode_b.md` → BGC_ID
    suffix = "_mode_b.md"
    prefix = f"{strain}_"
    for card_path in cards:
        name = card_path.name
        if not (name.startswith(prefix) and name.endswith(suffix)):
            # Filename doesn't match the canonical '<strain>_<BGC>_mode_b.md'.
            # v9.7.152 (AS-XXX Bug 1): if the stem still carries a recognizable
            # BGC id that IS in the register, this is a near-miss (e.g. the
            # '<strain>_' prefix was dropped by the card writer) — surface it
            # loudly instead of dropping it silently. Junk names (no BGC id, or
            # an id not in the register) are skipped without noise.
            _m = re.search(r"(BGC\d+)", name)
            if _m and _m.group(1) in known_bgcs:
                summary["skipped_misnamed"].append((_m.group(1), name))
            continue
        bgc_id = name[len(prefix): -len(suffix)]
        if not bgc_id:
            continue
        if bgc_id not in known_bgcs:
            summary["skipped_unknown"].append(bgc_id)
            continue
        if known_bgcs[bgc_id].get("status") == "COMPLETE":
            summary["skipped_already_complete"].append(bgc_id)
            continue
        try:
            content = card_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not content.strip():
            continue

        # ----- W9 structure gate -----
        n_errors = 0
        if True:  # v9.7.409 A7 (G3): same fail-closed routing as ingest_receipt above.
            try:
                if not _gate_available:
                    raise ImportError("modeb_structure_gate import failed")
                ctx = _bgc_context_from_triage(pkg, bgc_id)
                findings = _lint_card(content, bgc_context=ctx, check_evidence_presence=True)  # item 4: §4 coverage enforced at receipt
                n_errors = sum(1 for f in findings
                               if f.get("severity") == "ERROR")
            except Exception as _gate_exc:
                # v9.7.335 (extension): same fail-open as ingest_receipt above. A crashed gate
                # is an unverified card; the session-start recovery sweep must not silently
                # promote orphan cards it could not lint.
                n_errors = 1
                emit(f"  STRUCTURE: {bgc_id} — gate UNAVAILABLE "
                      f"({type(_gate_exc).__name__}); card treated as UNVERIFIED, not clean",
                      file=sys.stderr)
        if n_errors and not force_structure:
            summary["skipped_structure_invalid"].append((bgc_id, n_errors))
            continue

        session_id = _parse_card_session_id(content) or "auto-detect"
        # v9.7.371 fix: same rank/edge_status gap as ingest_receipt above.
        # v9.7.374 fix: same cds_count gap (see _rank_and_edge_from_ctx docstring).
        _q_ctx = _bgc_context_from_triage(pkg, bgc_id)
        _q_rank, _q_edge, _q_cds = _rank_and_edge_from_ctx(_q_ctx)
        try:
            record_mode_b(pkg, bgc_id, mode_b_md=content,
                          session_id=session_id,
                          rank=_q_rank, edge_status=_q_edge, cds_count=_q_cds)
            if n_errors:
                summary["recorded_with_structure_override"].append(bgc_id)
            else:
                summary["recorded"].append(bgc_id)
        except Exception:
            # Non-blocking — failing on one card must not poison the rest
            continue

    # Refresh status post-ingest
    reg = read_register(pkg)
    summary["judgment_status"] = reg.get("judgment_status")
    return summary


# N5 (v9.7.149c): card session-ID parser. The `<!-- MODE B: <BGC> | strain: <S>
# | session: <session_id> | <ts> -->` header is written by record_mode_b in
# judgment_store.py at the top of every card file. Parsing it back lets the
# auto-detect and per-card ingest flows preserve the original session ID
# rather than overwriting with a generic placeholder.
_CARD_SESSION_RE = re.compile(r"<!--\s*MODE\s*B:.*?\bsession:\s*([^|>\s]+)",
                              re.DOTALL | re.IGNORECASE)


def _parse_card_session_id(content: str) -> str:
    """Return the session ID from a Mode B card's header comment, or '' if
    no header is present or parseable. Never raises.
    """
    if not content:
        return ""
    m = _CARD_SESSION_RE.search(content)
    return m.group(1).strip() if m else ""


def ingest_one_card(package_dir: str | Path,
                    card_path: str | Path,
                    *,
                    force_structure: bool = False) -> dict[str, Any]:
    """Ingest a single Mode B card file directly (one card = one CLI call).

    Use case: an analysis chat writes a card to disk and wants to persist it
    immediately, without bundling into a receipt JSON. Complements the
    receipt-batch flow and the session-start `--auto-detect` recovery sweep.

    BGC ID is resolved in priority order:
      1. The card's `<!-- MODE B: <BGC_ID> | ... -->` header
      2. The filename pattern `<strain>_<BGC_ID>_mode_b.md`

    Session ID is parsed from the same header; falls back to "card-ingest".

    Structure gate (v9.7.150+):
        Before write, the card is linted against the §1–§48 contract via
        `mamey.modeb_structure_gate.lint_card()` with the BGC's triage row
        as context. ERROR-severity findings refuse the write — the firebreak
        for the BGC033 wrong-scaffold pattern. Override with
        force_structure=True (or CLI --force-structure), which records the
        card anyway and surfaces the findings in the return dict.

    Returns:
        {"strain_id": <str>,
         "status": "RECORDED" | "RECORDED_WITH_STRUCTURE_OVERRIDE"
                  | "SKIPPED_ALREADY_COMPLETE" | "SKIPPED_UNKNOWN"
                  | "SKIPPED_STRUCTURE_INVALID"
                  | "BAD_PATH" | "NO_CONTENT" | "UNRESOLVED_BGC"
                  | "RECORD_FAILED",
         "bgc_id": <str|None>,
         "session_id": <str|None>,
         "judgment_status": <register status after ingest>,
         "structure_findings": [Finding, ...]}

    Never raises. The caller decides exit behaviour from the `status` field.

    N4 (v9.7.149c) + W9 structure-gate wiring (v9.7.150+).
    """
    from .judgment_store import (
        _strain_from_pkg, read_register, record_mode_b,
    )

    pkg = Path(package_dir)
    strain = _strain_from_pkg(pkg)
    card = Path(card_path)

    summary: dict[str, Any] = {
        "strain_id": strain,
        "status": "BAD_PATH",
        "bgc_id": None,
        "session_id": None,
        "judgment_status": None,
        "structure_findings": [],
    }

    # v9.7.409 (BC hostile audit H5): every early return below used to leave `structure_findings`
    # as [] — byte-identical to a clean lint — so the CLI printed "structure: PASS (§1–§48 contract
    # satisfied)" for an EMPTY file and for a Mode B Top-Leads summary with zero § headings. A file
    # the gate never evaluated is not a passing card; say so with a typed ERROR finding.
    def _not_evaluated(code: str, message: str) -> None:
        summary["structure_findings"] = [{
            "severity": "ERROR", "code": code, "section": None,
            "expected": "a Mode B card the structure gate could evaluate", "found": message,
            "message": f"structure NOT evaluated: {message}",
        }]

    if not card.is_file():
        _not_evaluated("STRUCTURE_NOT_EVALUATED", "card path is not a file")
        return summary

    try:
        content = card.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as _exc:
        _not_evaluated("STRUCTURE_NOT_EVALUATED", f"card unreadable ({type(_exc).__name__})")
        return summary
    if not content.strip():
        summary["status"] = "NO_CONTENT"
        _not_evaluated("EMPTY_CARD", "card file is empty")
        return summary

    # Resolve BGC ID — header first, filename second
    bgc_id = _parse_card_bgc_id(content)
    if not bgc_id:
        # Fall back to filename pattern <strain>_<BGC_ID>_mode_b.md
        name = card.name
        prefix = f"{strain}_"
        suffix = "_mode_b.md"
        if name.startswith(prefix) and name.endswith(suffix):
            bgc_id = name[len(prefix): -len(suffix)]
    if not bgc_id:
        summary["status"] = "UNRESOLVED_BGC"
        _not_evaluated("UNRESOLVED_BGC", "no BGC id in the card header or filename — not a Mode B card, or not this package's")
        return summary
    summary["bgc_id"] = bgc_id

    session_id = _parse_card_session_id(content) or "card-ingest"
    summary["session_id"] = session_id

    # v9.7.409 (BC hostile audit H9): a template whose node name was rewritten to a locus the package
    # does not contain was RECORDED and marked COMPLETE. The exact-locus doctrine — strain / full node /
    # region / alias from ONE bound record — is enforced here: the card header's strain and node must
    # match the package's own inventory row for this BGC. Mismatch → typed ERROR, nothing recorded.
    _mismatch = _card_identity_mismatch(content, pkg, strain, bgc_id)
    if _mismatch:
        summary["status"] = "SKIPPED_IDENTITY_MISMATCH"
        summary["structure_findings"] = [{
            "severity": "ERROR", "code": "CARD_IDENTITY_MISMATCH", "section": None,
            "expected": _mismatch[0], "found": _mismatch[1],
            "message": f"card identity does not match the package: expected {_mismatch[0]}, card says {_mismatch[1]}",
        }]
        return summary

    reg = read_register(pkg)
    known_bgcs = reg.get("bgcs", {})
    if bgc_id not in known_bgcs:
        summary["status"] = "SKIPPED_UNKNOWN"
        summary["judgment_status"] = reg.get("judgment_status")
        return summary
    if known_bgcs[bgc_id].get("status") == "COMPLETE":
        summary["status"] = "SKIPPED_ALREADY_COMPLETE"
        summary["judgment_status"] = reg.get("judgment_status")
        return summary

    # ----- W9 structure gate -----
    structure_findings: list[dict] = []
    try:
        from .modeb_structure_gate import lint_card
        bgc_ctx = _bgc_context_from_triage(pkg, bgc_id)
        structure_findings = lint_card(content, bgc_context=bgc_ctx, check_evidence_presence=True)  # item 4: §4 coverage enforced at receipt
    except Exception as _gate_exc:
        # v9.7.335: this used to set structure_findings = [], which is BYTE-IDENTICAL to a clean
        # lint — a crashed gate was recorded as a valid card and printed as "structure: PASS".
        # Emit an explicit ERROR sentinel instead so absence of a check is never rendered as a pass.
        structure_findings = [{
            "severity": "ERROR", "code": "GATE_UNAVAILABLE", "section": 0,
            "expected": "structure gate executes",
            "found": f"gate raised {type(_gate_exc).__name__}",
            "detail": ("the §1–§48 structure gate could not run, so this card is UNVERIFIED — "
                       "not clean. Fix the bundle-integrity fault and re-run verify-modeb."),
        }]
    summary["structure_findings"] = structure_findings

    n_errors = sum(1 for f in structure_findings if f.get("severity") == "ERROR")
    if n_errors and not force_structure:
        summary["status"] = "SKIPPED_STRUCTURE_INVALID"
        summary["judgment_status"] = reg.get("judgment_status")
        return summary

    # v9.7.371 fix: same rank/edge_status gap as ingest_receipt/auto_detect_ingest above --
    # bgc_ctx was already computed for the structure gate but never threaded into the quality
    # gate's priority-tier floor / fragment exemption.
    # v9.7.374 fix: same cds_count gap (see _rank_and_edge_from_ctx docstring).
    _q_rank, _q_edge, _q_cds = _rank_and_edge_from_ctx(bgc_ctx if isinstance(bgc_ctx, dict) else {})
    try:
        record_mode_b(pkg, bgc_id, mode_b_md=content, session_id=session_id,
                      rank=_q_rank, edge_status=_q_edge, cds_count=_q_cds)
        summary["status"] = ("RECORDED_WITH_STRUCTURE_OVERRIDE" if n_errors
                             else "RECORDED")
    except Exception as _exc:
        # Non-blocking. Distinct from the early BAD_PATH (card file itself
        # unreadable) — this is a write-time failure inside record_mode_b
        # (e.g. disk error, register write failure). Reusing BAD_PATH here
        # would mislead a caller into thinking the --card argument was wrong.
        # (bug hunt finding 15.3, v9.7.150c)
        summary["status"] = "RECORD_FAILED"
        summary["error"] = f"{type(_exc).__name__}: {_exc}"
        summary["judgment_status"] = reg.get("judgment_status")
        return summary

    reg = read_register(pkg)
    summary["judgment_status"] = reg.get("judgment_status")
    return summary


def _rank_and_edge_from_ctx(ctx: dict) -> tuple:
    """v9.7.371 fix: extract (rank, edge_status) from a triage-row context dict for
    mode_b_quality_gate.evaluate_card()/judgment_store.record_mode_b()'s rank/edge_status
    params. Every production ingest path in this file computed `ctx` via
    _bgc_context_from_triage() (for the structure gate) but never threaded it into the quality
    gate, so every card was always evaluated at rank=None -> the most lenient LOW floor, and
    edge_status=None -> the fragment-floor exemption never fired. Returns (None, None, None) on
    any missing/malformed value (fail-safe: never invents a rank/edge_status/cds_count).

    v9.7.374 fix: also extract cds_count (populated by _bgc_context_from_triage from the sealed
    gene_context.jsonl). The .371 fix above covered rank/edge_status but left cds_count out, so
    evaluate_card()'s fragment-floor exemption — which requires edge_status AND cds_count
    together — stayed disabled even after .371: cds_count was always None here, so
    evaluate_card's `cds_count is not None` half of its is_fragment check was always False,
    and the exemption never fired even for a genuine boundary fragment with edge_status set."""
    rank_raw = str(ctx.get("Corrected_rank") or "").strip()
    rank = int(rank_raw) if rank_raw.isdigit() else None
    edge_status = (ctx.get("Boundary") or "").strip() or None
    cds_count = ctx.get("cds_count")
    cds_count = int(cds_count) if isinstance(cds_count, int) else None
    return rank, edge_status, cds_count


def _bgc_context_from_triage(pkg: Path, bgc_id: str, _cross: bool = True) -> dict:
    """Build the BGC context dict that modeb_structure_gate predicates expect,
    by reading the relevant triage row. Returns {} on any failure — the
    linter will then treat conditional sections as optional (WARN, not ERROR).

    `_cross` guards the sibling merge with `_bgc_context_from_package`. That sibling
    ALSO merges this builder's output, so an unguarded cross-call is an unbounded
    mutual recursion (A-03, WAC-01375/DSM46095 audit): each door recursed to Python's
    limit, swallowed the RecursionError via the merge's `except`, and — on a real
    package — blew the 5-min wall re-reading the sealed CSVs ~250× (exit 124). A
    top-level call (`_cross=True`) merges once and calls the sibling with `_cross=False`
    so it does NOT cross back; the top-level door still gets both contexts, one hop.
    """
    import csv as _csv
    candidates = sorted(pkg.glob("*_4_triage_board.csv"))
    if not candidates:
        return {}
    try:
        with open(candidates[0], newline="", encoding="utf-8") as f:
            rows = list(_csv.DictReader(f))
    except (OSError, _csv.Error):
        return {}
    matching = next((r for r in rows
                     if (r.get("BGC_ID") or r.get("bgc_id") or "").strip()
                     == bgc_id), None)
    if not matching:
        return {}
    ctx: dict = dict(matching)
    # Roll up strain-level high-priority count for the §29 predicate
    hp = sum(1 for r in rows
             if (r.get("Lead_tier_auto") or "").upper()
             in ("HIGH", "PRIORITY ISO", "PRIORITY_ISO",
                 "HIGH SEQ", "HIGH_SEQ"))
    ctx["strain_high_priority_count"] = hp
    # v9.7.369 — bind the §31-§48 predicate inputs from the package's own sealed
    # tables, so the typed predicates in modeb_structure_gate can evaluate them.
    # Without these keys the extension predicates always fall to the fail-safe
    # False and the gate is structurally silent on extension-depth (measured
    # 2026-08-17: 81 of 82 authored extension instances cohort-wide were §43,
    # emitted by generator repertoire, with the gate unable to notice). Every
    # count below is deterministic and read-only; any failure leaves the key
    # absent, which the predicates already treat as NOT applicable.
    import re as _re
    _bgc_pat = _re.compile(r"BGC\d+")

    def _read(glob_pat):
        cands = sorted(pkg.glob(glob_pat))
        if not cands:
            return []
        try:
            with open(cands[0], newline="", encoding="utf-8",
                      errors="replace") as fh:
                return list(_csv.DictReader(fh))
        except (OSError, _csv.Error):
            return []

    # module_count: aSModule features ONLY — counting aSDomain rows would fire
    # §32-§34 on domains without a programmed assembly line.
    n_mod = sum(1 for r in _read("*_3_antismash_modules.csv")
                if (r.get("feature_type") or "") == "aSModule"
                and (r.get("bgc_id") or "").strip() == bgc_id)
    if n_mod:
        ctx["module_count"] = n_mod
    # protocluster_count: crosswalk rows for this BGC.
    n_prot = sum(1 for r in _read("*_2b_bgc_crosswalk.csv")
                 if (r.get("bgc_id") or "").strip() == bgc_id)
    if n_prot:
        ctx["protocluster_count"] = n_prot
    # n_4a_rows: ABOVE-BAR RG-GMCI ranked pairs only. LOW_SHARED_REFERENCE_SIGNAL
    # rows are shared-genus reference noise, not split-pathway evidence; counting
    # them would make §43 applicable on 19 of AS-XXX's 28 pair members that the
    # authoring bar correctly refuses.
    n_4a = 0
    for r in _read("*_4A_RGGMCI_ranked_pairs.csv"):
        if (r.get("rggmci_confidence") or "") == "LOW_SHARED_REFERENCE_SIGNAL":
            continue
        if bgc_id in (str(r.get("bgc_a") or "").strip(),
                      str(r.get("bgc_b") or "").strip()):
            n_4a += 1
    if n_4a:
        ctx["n_4a_rows"] = n_4a
    # n_4d_rows: two-proof rescue rows naming this BGC on either side.
    n_4d = 0
    for r in _read("*_4D_two_proof_rescue.csv"):
        vals = (str(r.get("bgc_a") or ""), str(r.get("bgc_b") or ""),
                str(r.get("bgc_id") or ""))
        if any(bgc_id == _v.strip() for _v in vals):
            n_4d += 1
    if n_4d:
        ctx["n_4d_rows"] = n_4d
    # v9.7.374 fix: this triage-row context never carried known_loci/locus_home/known_locus_tags/
    # panels_present -- the three keys modeb_structure_gate's PHANTOM_LOCUS, LOCUS_BGC_MISMATCH, and
    # PANEL_ABSENT_CLAIM fabrication-detection ERROR checks require (each is fail-open "silent
    # without it" BY DESIGN -- "cannot judge what it cannot see"). This function feeds lint_card()
    # at every ingest-receipts entry point (ingest_receipt, auto_detect_ingest, ingest_one_card,
    # lint_card_in_package) -- the documented canonical front door (mamey/cli.py's pipeline order:
    # ...render-figures -> ingest-receipts) -- so those three ERROR-level fabrication guards have
    # been running fully fail-open on every card that reaches the pipeline through ingest-receipts,
    # even though the SAME fabrication classes (a phantom locus, a locus misattributed to the wrong
    # BGC, a per-gene result claimed for an unrun panel) are exactly what authored_verify.py's
    # sibling context builder (_bgc_context_from_package) already reads from the sealed package and
    # supplies correctly for the separate `verify-modeb` CLI path. Merge that package-derived
    # context in here too, mirroring the W7 door-symmetry fix (v9.7.370) philosophy of "one ctx
    # source, both doors" -- but for the gap that fix left open in the opposite direction (package-
    # derived keys flowing INTO the ingest door, not just triage keys flowing into the verify door).
    # Package-derived values take precedence on any key collision, matching authored_verify.py's own
    # merge convention (ctx already-set beats a later-merged value).
    if _cross:
        try:
            from .authored_verify import _bgc_context_from_package
            # _cross=False: the sibling must not merge triage back in, or the two
            # doors recurse without bound (A-03).
            pctx = _bgc_context_from_package(str(pkg), bgc_id, _cross=False) or {}
            for k, v in pctx.items():
                ctx[k] = v
        except Exception:
            pass
    # cds_count: total CDS in this BGC's gene table, from the sealed gene_context.jsonl.
    # v9.7.374 fix: mode_b_quality_gate.evaluate_card()'s fragment-floor exemption is keyed on
    # edge_status AND cds_count together (its own docstring: "keys on edge_status AND cds — NOT
    # cds alone"), but this function never populated cds_count. Unlike Corrected_rank/Boundary,
    # no triage-board or inventory column carries a per-BGC CDS count, so the v9.7.371 fix that
    # threaded rank/edge_status through record_mode_b()/evaluate_card() left this half of the same
    # exemption permanently disabled (evaluate_card's is_fragment requires `cds_count is not
    # None`, which was always False since cds_count was always None -> is_fragment always False).
    # gene_context.jsonl is a sealed, package-local
    # artifact already read the same way elsewhere (modeb_template_emitter._gene_rows_for_bgc):
    # one JSON object per line, "current engine shape" {"bgc_id": X, "cds": [...]}. Read
    # defensively; absent/malformed -> cds_count stays unset -> no exemption granted (conservative,
    # matches the existing "missing edge_status/cds_count -> no exemption" contract). Runs AFTER
    # the package-context merge above (order-dependent resolution of the two .374 cards touching
    # this function's tail -- see the stacking note in this card's PATCH_CARD.md).
    if "cds_count" not in ctx:
        for _gc_path in sorted(pkg.glob("*gene_context.jsonl")):
            try:
                for _line in _gc_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    _line = _line.strip()
                    if not _line:
                        continue
                    _obj = json.loads(_line)
                    if (_obj.get("bgc_id") or _obj.get("BGC_ID")) != bgc_id:
                        continue
                    if isinstance(_obj.get("cds"), list):
                        ctx["cds_count"] = len(_obj["cds"])
                    break
            except (OSError, json.JSONDecodeError, AttributeError):
                pass
            if "cds_count" in ctx:
                break
    return ctx


_CARD_BGC_RE = re.compile(r"<!--\s*MODE\s*B:\s*([A-Za-z0-9_-]+)\s*\|",
                          re.IGNORECASE)

# v9.7.198: also resolve the `emit-modeb-template` header form
# `<!-- MODE B TEMPLATE | bgc: <ID> | ... -->` (keyed). The canonical regex
# above matches only `<!-- MODE B: <ID> | -->` (written by judgment_store),
# so a card authored directly from the emitter — before judgment_store
# rewrites its header — failed header resolution and returned UNRESOLVED_BGC.
_CARD_BGC_KEYED_RE = re.compile(r"<!--\s*MODE\s*B\b[^>]*?\bbgc:\s*([A-Za-z0-9_-]+)",
                                re.IGNORECASE)
_CARD_STRAIN_RE = re.compile(
    r"<!--\s*MODE\s*B\b[^>]*?\bstrain:\s*([^|>\s]+)",
    re.IGNORECASE,
)


def lint_card_in_package(package_dir: str | Path, bgc_id: str,
                         card_md: str | None = None) -> list:
    """Lint a Mode B card with the SAME triage context the ingest gate uses,
    so 'passes here' == 'ingests cleanly'.

    v9.7.152 (AS-XXX Bug 2): the standalone ``modeb_structure_gate.lint_card``,
    called without ``bgc_context``, cannot evaluate conditional-section
    predicates (§21–§27, §29) and so treats those *required* sections as
    optional (WARN). The ingest path supplies context via
    ``_bgc_context_from_triage`` and enforces them as ERROR. A context-free
    authoring loop therefore green-lights cards that ingest then rejects. This
    wrapper closes that gap.

    - Resolves ``_bgc_context_from_triage(pkg, bgc_id)`` exactly as ingest does.
    - If ``card_md`` is None, reads the card from its canonical path (supports
      linting on-disk cards); if that path is missing, returns a single
      BAD_PATH finding rather than raising.
    - Fails open: any gate/triage error degrades to a context-free lint (or
      ``[]``), never raises — an authoring helper must not crash the loop.
    """
    pkg = Path(package_dir)
    try:
        from .modeb_structure_gate import lint_card as _lint_card
    except Exception:
        return []  # gate unavailable — fail open

    if card_md is None:
        from .judgment_store import _mode_b_path, _strain_from_pkg
        path = _mode_b_path(pkg, bgc_id)
        if not path.exists():
            return [{
                "severity": "ERROR", "code": "BAD_PATH", "section": None,
                "message": (f"no card at canonical path {path.name}; "
                            f"expected '{_strain_from_pkg(pkg)}_{bgc_id}_mode_b.md' "
                            "in the judgment dir."),
            }]
        try:
            card_md = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return [{"severity": "ERROR", "code": "BAD_PATH",
                     "section": None, "message": f"could not read card: {e}"}]

    try:
        ctx = _bgc_context_from_triage(pkg, bgc_id)
    except Exception:
        ctx = {}
    try:
        return _lint_card(card_md, bgc_context=ctx)
    except Exception:
        # last-resort: context-free lint so the author still gets structure info
        try:
            return _lint_card(card_md)
        except Exception:
            return []


def emit_modeb_template_command(args) -> int:
    """CLI: mamey emit-modeb-template --package <pkg> --bgc <BGC_ID>
                              | --package <pkg> --batch [--scope all|top|leads|pending] [--top-n N]

    Emit canonical §1–§48 Mode B card templates pre-filled with the
    BGC-specific facts from the triage board + manifests. Single-BGC mode
    prints the template; batch mode writes one card per BGC to
    `<pkg>/mode_b_templates/` plus an index file.

    Pairs with `modeb_structure_gate`: a card built on the emitted template
    is structurally valid by construction. (W9 firebreak, v9.7.150+.)
    """
    import argparse  # noqa: F401 — for type clarity at call sites
    from pathlib import Path as _P
    pkg = _P(args.package).resolve()
    if not pkg.is_dir():
        emit(f"ERROR: not a directory: {pkg}", file=sys.stderr)
        return 1

    bgc = getattr(args, "bgc", None)
    batch = bool(getattr(args, "batch", False))
    if not bgc and not batch:
        emit("ERROR: either --bgc <BGC_ID> or --batch is required",
              file=sys.stderr)
        return 2
    if bgc and batch:
        emit("ERROR: --bgc and --batch are mutually exclusive",
              file=sys.stderr)
        return 2

    # v9.7.344 BLASTp-completeness HARD gate: BLASTp ingestion is a MANDATORY step before Mode B
    # authoring. Refuse (exit 3) if ingestable BLASTp is available on disk but not ingested, unless
    # --blastp-waiver "<reason>" is given (recorded to manifest provenance).
    from . import blastp_gate as _bpg
    _strain = ""
    for _f in pkg.glob("*_4_triage_board.csv"):
        _strain = _f.name.split("_4_triage_board.csv")[0]
        break
    _bp = _bpg.gate(pkg, _strain, waiver=getattr(args, "blastp_waiver", None))
    if _bp["blocked"]:
        emit(_bp["message"], file=sys.stderr)
        return 3
    if _bp["waived"]:
        emit(f"  {_bp['message']}", file=sys.stderr)

    if bgc:
        try:
            from . import modeb_template_emitter as _emit
            card = _emit.emit_card_template(pkg, bgc)
        except FileNotFoundError as e:
            emit(f"ERROR: {e}", file=sys.stderr)
            return 1
        out = getattr(args, "out", None)
        if out:
            _P(out).write_text(card, encoding="utf-8")
            emit(f"template -> {out}")
        else:
            emit(card)
        return 0

    # batch
    scope = getattr(args, "scope", "all") or "all"
    top_n = getattr(args, "top_n", None)
    try:
        from . import modeb_template_emitter as _emit
        res = _emit.emit_batch(pkg, scope=scope, top_n=top_n)
    except FileNotFoundError as e:
        emit(f"ERROR: {e}", file=sys.stderr)
        return 1
    if res.get("skipped_reason"):
        emit(f"ERROR: {res['skipped_reason']}", file=sys.stderr)
        return 1
    # P-emit-01 (docs lineage v9.7.243, merged at v9.7.250): --scope leads exited 0 when no BGC
    # carried Lead_tier_auto in {HIGH, PRIORITY_ISO, HIGH_SEQ} — e.g. every VERY_POOR assembly whose
    # BGCs are all Medium or below. W3 reads mode_b_templates/; an exit-0 with an empty directory
    # reads as PASS and silently blocks W4. Exit 3 names the condition instead.
    fail_on_empty = getattr(args, "fail_on_empty", False)
    if not res["emitted"] and (scope == "leads" or fail_on_empty):
        emit(
            f"emit-modeb-template: 0 BGCs in scope '{scope}' — nothing to emit. "
            f"If this is unexpected, check Lead_tier_auto in the triage board. "
            f"(exit 3; use --scope all or --scope pending to emit all BGCs)",
            file=sys.stderr,
        )
        return 3
    emit(f"Mode B template batch for {pkg.parent.name}:", f"  scope:    {scope}" + (f" (top {top_n})" if top_n else ""), f"  emitted:  {len(res['emitted'])} template(s) -> {res['out']}/", f"  index:    {res['out']}/_INDEX.md", sep="\n")
    if res["skipped"]:
        emit(f"  skipped:  {len(res['skipped'])}")
        for bid, reason in res["skipped"].items():
            emit(f"    {bid}: {reason}", file=sys.stderr)
    return 0



_CARD_NODE_RE = re.compile(r"<!--\s*MODE\s*B\b[^>]*?\bnode:\s*([^|>\s]+)", re.IGNORECASE)
_CARD_REGION_RE = re.compile(r"<!--\s*MODE\s*B\b[^>]*?\bregion:\s*([^|>\s]+)", re.IGNORECASE)


def _package_node_for_bgc(pkg: Path, bgc_id: str) -> str:
    """Return the package's full node/contig for ``bgc_id``, or ``""``.

    ``Contig`` is the full physical identifier in current packages.  ``Node_ID``
    can be a display-shortened derivative (for example, it may omit the decimal
    coverage suffix), so it is only a fallback.  Exact-locus comparison must not
    prefer that lossy field over the full source identifier.
    """
    import csv as _csv
    for inv in sorted(Path(pkg).glob("*_2_inventory.csv")):
        try:
            with open(inv, newline="", encoding="utf-8") as f:
                for r in _csv.DictReader(f):
                    if (r.get("BGC_ID") or r.get("bgc_id") or "").strip() == bgc_id:
                        return (r.get("Contig") or r.get("contig") or r.get("Node_ID") or "").strip()
        except (OSError, UnicodeDecodeError, _csv.Error):
            continue
    return ""


def _package_region_for_bgc(pkg: Path, bgc_id: str) -> str:
    """Return the package's normalized antiSMASH region token, or ``""``."""
    import csv as _csv
    for inv in sorted(Path(pkg).glob("*_2_inventory.csv")):
        try:
            with open(inv, newline="", encoding="utf-8") as f:
                for r in _csv.DictReader(f):
                    if (r.get("BGC_ID") or r.get("bgc_id") or "").strip() == bgc_id:
                        value = (r.get("antiSMASH_Region") or r.get("region") or "").strip()
                        if value:
                            match = re.fullmatch(r"region[_ -]?(\d{1,4})", value, re.IGNORECASE)
                            return f"region{int(match.group(1)):03d}" if match else value
        except (OSError, UnicodeDecodeError, _csv.Error):
            continue
    return ""


def _card_identity_mismatch(content: str, pkg: Path, strain: str, bgc_id: str):
    """Return ``(expected, found)`` when a stated card identity contradicts its package.

    The comparison covers strain, full node/contig, and region; ``bgc_id`` is
    already resolved by the caller.  Unstated fields remain a separate profile
    completeness concern rather than being guessed here.
    """
    m_s = _CARD_STRAIN_RE.search(content)
    if m_s and strain and m_s.group(1).strip() != str(strain):
        return (f"strain {strain}", f"strain {m_s.group(1).strip()}")
    m_n = _CARD_NODE_RE.search(content)
    if m_n:
        pkg_node = _package_node_for_bgc(pkg, bgc_id)
        if pkg_node and m_n.group(1).strip() != pkg_node:
            return (f"{bgc_id} on node {pkg_node}", f"{bgc_id} on node {m_n.group(1).strip()}")
    m_r = _CARD_REGION_RE.search(content)
    if m_r:
        pkg_region = _package_region_for_bgc(pkg, bgc_id)
        card_region = m_r.group(1).strip()
        match = re.fullmatch(r"region[_ -]?(\d{1,4})", card_region, re.IGNORECASE)
        normalized_card_region = f"region{int(match.group(1)):03d}" if match else card_region
        if pkg_region and normalized_card_region != pkg_region:
            return (f"{bgc_id} in {pkg_region}", f"{bgc_id} in {card_region}")
    return None

def _parse_card_bgc_id(content: str) -> str:
    """Return the BGC ID from a Mode B card's header comment, or '' if no
    header is present or parseable."""
    if not content:
        return ""
    m = _CARD_BGC_RE.search(content)
    if m:
        return m.group(1).strip()
    # v9.7.198: fall back to the emitter's keyed header form.
    m = _CARD_BGC_KEYED_RE.search(content)
    return m.group(1).strip() if m else ""


def _parse_card_strain_id(content: str) -> str:
    """Return the strain ID asserted by either supported Mode B header."""
    if not content:
        return ""
    match = _CARD_STRAIN_RE.search(content)
    return match.group(1).strip() if match else ""


FINISHED_REVIEW_REQUEST_SCHEMA = "mode-b-finished-review-request-1.0"
FINISHED_REVIEW_REQUEST_SCHEMA_V3 = "mode-b-finished-review-request-1.1"
FINISHED_REVIEW_REQUEST_SCHEMA_V4 = "mode-b-finished-review-request-1.2"
FINISHED_REVIEW_REQUEST_SCHEMA_V5 = "mode-b-finished-review-request-1.3"
FINISHED_REVIEW_REQUEST_SCHEMA_V6 = "mode-b-finished-review-request-1.4"
FINISHED_REVIEW_REQUEST_SCHEMA_V7 = "mode-b-finished-review-request-1.5"
FINISHED_REVIEW_REQUEST_SCHEMA_V8 = "mode-b-finished-review-request-1.6"
FINISHED_REVIEW_REQUEST_SCHEMA_V9 = "mode-b-finished-review-request-1.7"
FINISHED_REVIEW_REQUEST_SCHEMA_V10 = "mode-b-finished-review-request-1.8"
FINISHED_REVIEW_REQUEST_SCHEMA_V11 = "mode-b-finished-review-request-1.9"
FINISHED_REVIEW_INTENT = "REQUEST_FINISHED_FULL48_REVIEW"
# Match the canonical names owned by mode_b.gene_first_stage_v2. User-facing
# documentation may spell these "NCBI nr" and "NCBI ClusteredNR", but receipt
# joins must not create a second namespace.
FINISHED_REVIEW_CHANNELS = ("nr", "clustered_nr", "local_swissprot")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _review_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _review_member(root: Path, locator: object, label: str,
                   findings: list[dict[str, str]]) -> Path | None:
    """Resolve one portable review-packet member without allowing root escape."""
    text = str(locator or "").strip()
    if not text:
        findings.append({"code": "REVIEW_MEMBER_LOCATOR_MISSING", "detail": label})
        return None
    candidate = Path(text)
    if candidate.is_absolute() or ".." in candidate.parts:
        findings.append({"code": "REVIEW_MEMBER_LOCATOR_UNSAFE", "detail": label})
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        findings.append({"code": "REVIEW_MEMBER_ROOT_ESCAPE", "detail": label})
        return None
    if not resolved.is_file():
        findings.append({"code": "REVIEW_MEMBER_MISSING", "detail": label})
        return None
    return resolved


def _review_json_member(root: Path, spec: object, label: str,
                        findings: list[dict[str, str]]) -> dict[str, Any] | None:
    if not isinstance(spec, dict):
        findings.append({"code": "REVIEW_MEMBER_SPEC_INVALID", "detail": label})
        return None
    path = _review_member(root, spec.get("locator"), label, findings)
    expected = str(spec.get("sha256") or "").strip().lower()
    if not _SHA256_RE.fullmatch(expected):
        findings.append({"code": "REVIEW_MEMBER_SHA256_INVALID", "detail": label})
        return None
    if path is None:
        return None
    if _review_sha256(path) != expected:
        findings.append({"code": "REVIEW_MEMBER_SHA256_MISMATCH", "detail": label})
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError):  # v9.7.410: a 200k-deep `[[[[…` request crashed the validator instead of routing to HOLD
        findings.append({"code": "REVIEW_MEMBER_JSON_INVALID", "detail": label})
        return None
    if not isinstance(value, dict):
        findings.append({"code": "REVIEW_MEMBER_JSON_NOT_OBJECT", "detail": label})
        return None
    return value


def validate_finished_review_request(
    package_dir: str | Path,
    request_path: str | Path,
    artifact_root: str | Path,
) -> dict[str, Any]:
    """Validate a finished-card review request without writing or promoting anything.

    The result is deliberately a coarse route: ``READY_FOR_OWNER_REVIEW`` or
    ``HOLD_FINISHED_REVIEW_REQUEST``.  READY means only that the bound request is
    internally consistent and may be shown to an owner; it is not card acceptance,
    currentness selection, scientific validation, promotion, or release.
    """
    findings: list[dict[str, str]] = []
    pkg = Path(package_dir).resolve()
    root = Path(artifact_root).resolve()
    request_file = Path(request_path).resolve()

    if not pkg.is_dir():
        findings.append({"code": "REVIEW_PACKAGE_MISSING", "detail": "package directory"})
    if not root.is_dir():
        findings.append({"code": "REVIEW_ARTIFACT_ROOT_MISSING", "detail": "artifact root"})
    try:
        request = json.loads(request_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError):  # v9.7.410: a 200k-deep `[[[[…` request crashed the validator instead of routing to HOLD
        request = {}
        findings.append({"code": "REVIEW_REQUEST_JSON_INVALID", "detail": "request"})
    if not isinstance(request, dict):
        request = {}
        findings.append({"code": "REVIEW_REQUEST_NOT_OBJECT", "detail": "request"})

    request_schema = request.get("schema_version")
    if request_schema not in (
        FINISHED_REVIEW_REQUEST_SCHEMA,
        FINISHED_REVIEW_REQUEST_SCHEMA_V3,
        FINISHED_REVIEW_REQUEST_SCHEMA_V4,
        FINISHED_REVIEW_REQUEST_SCHEMA_V5,
        FINISHED_REVIEW_REQUEST_SCHEMA_V6,
        FINISHED_REVIEW_REQUEST_SCHEMA_V7,
        FINISHED_REVIEW_REQUEST_SCHEMA_V8,
        FINISHED_REVIEW_REQUEST_SCHEMA_V9,
        FINISHED_REVIEW_REQUEST_SCHEMA_V10,
        FINISHED_REVIEW_REQUEST_SCHEMA_V11,
    ):
        findings.append({"code": "REVIEW_REQUEST_SCHEMA_MISMATCH", "detail": "schema_version"})
    requires_semantic_v3 = request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V3,
        FINISHED_REVIEW_REQUEST_SCHEMA_V4,
        FINISHED_REVIEW_REQUEST_SCHEMA_V5,
        FINISHED_REVIEW_REQUEST_SCHEMA_V6,
        FINISHED_REVIEW_REQUEST_SCHEMA_V7,
        FINISHED_REVIEW_REQUEST_SCHEMA_V8,
        FINISHED_REVIEW_REQUEST_SCHEMA_V9,
        FINISHED_REVIEW_REQUEST_SCHEMA_V10,
        FINISHED_REVIEW_REQUEST_SCHEMA_V11,
    )
    requires_semantic_v4 = request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V4,
        FINISHED_REVIEW_REQUEST_SCHEMA_V5,
        FINISHED_REVIEW_REQUEST_SCHEMA_V6,
        FINISHED_REVIEW_REQUEST_SCHEMA_V7,
        FINISHED_REVIEW_REQUEST_SCHEMA_V8,
        FINISHED_REVIEW_REQUEST_SCHEMA_V9,
        FINISHED_REVIEW_REQUEST_SCHEMA_V10,
        FINISHED_REVIEW_REQUEST_SCHEMA_V11,
    )
    requires_semantic_v5 = request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V5,
        FINISHED_REVIEW_REQUEST_SCHEMA_V6,
        FINISHED_REVIEW_REQUEST_SCHEMA_V7,
        FINISHED_REVIEW_REQUEST_SCHEMA_V8,
        FINISHED_REVIEW_REQUEST_SCHEMA_V9,
        FINISHED_REVIEW_REQUEST_SCHEMA_V10,
        FINISHED_REVIEW_REQUEST_SCHEMA_V11,
    )
    requires_semantic_v6 = request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V6, FINISHED_REVIEW_REQUEST_SCHEMA_V7,
        FINISHED_REVIEW_REQUEST_SCHEMA_V8)
    requires_semantic_v6 = requires_semantic_v6 or request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V9, FINISHED_REVIEW_REQUEST_SCHEMA_V10,
        FINISHED_REVIEW_REQUEST_SCHEMA_V11)
    requires_semantic_v7 = request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V7, FINISHED_REVIEW_REQUEST_SCHEMA_V8,
        FINISHED_REVIEW_REQUEST_SCHEMA_V9)
    requires_semantic_v7 = requires_semantic_v7 or request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V10, FINISHED_REVIEW_REQUEST_SCHEMA_V11)
    requires_inventory_v8 = request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V8, FINISHED_REVIEW_REQUEST_SCHEMA_V9,
        FINISHED_REVIEW_REQUEST_SCHEMA_V10, FINISHED_REVIEW_REQUEST_SCHEMA_V11)
    requires_selection_v9 = request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V9, FINISHED_REVIEW_REQUEST_SCHEMA_V10,
        FINISHED_REVIEW_REQUEST_SCHEMA_V11)
    requires_figure_v10 = request_schema in (
        FINISHED_REVIEW_REQUEST_SCHEMA_V10, FINISHED_REVIEW_REQUEST_SCHEMA_V11)
    requires_reconciliation_v11 = request_schema == FINISHED_REVIEW_REQUEST_SCHEMA_V11
    quality_profile = request.get("quality_profile")
    if requires_reconciliation_v11:
        if quality_profile != (
            "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
            "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5_PLUS_"
            "SEMANTIC_DECISION_CHAINS_V6_PLUS_SEMANTIC_CLAIM_MODELS_V7_PLUS_"
            "INVENTORY_RECONCILIATION_V8_PLUS_SELECTION_PROCESS_V9_PLUS_"
            "FIGURE_SPEC_V10_PLUS_RECONCILIATION_SPECIFICITY_V11"
        ):
            findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH", "detail": "quality_profile"})
    elif requires_figure_v10:
        if quality_profile != (
            "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
            "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5_PLUS_"
            "SEMANTIC_DECISION_CHAINS_V6_PLUS_SEMANTIC_CLAIM_MODELS_V7_PLUS_"
            "INVENTORY_RECONCILIATION_V8_PLUS_SELECTION_PROCESS_V9_PLUS_"
            "FIGURE_SPEC_V10"
        ):
            findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH", "detail": "quality_profile"})
    elif requires_selection_v9:
        if quality_profile != (
            "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
            "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5_PLUS_"
            "SEMANTIC_DECISION_CHAINS_V6_PLUS_SEMANTIC_CLAIM_MODELS_V7_PLUS_"
            "INVENTORY_RECONCILIATION_V8_PLUS_SELECTION_PROCESS_V9"
        ):
            findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH", "detail": "quality_profile"})
    elif requires_inventory_v8:
        if quality_profile != (
            "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
            "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5_PLUS_"
            "SEMANTIC_DECISION_CHAINS_V6_PLUS_SEMANTIC_CLAIM_MODELS_V7_PLUS_"
            "INVENTORY_RECONCILIATION_V8"
        ):
            findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH", "detail": "quality_profile"})
    elif requires_semantic_v7:
        if quality_profile != (
            "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
            "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5_PLUS_"
            "SEMANTIC_DECISION_CHAINS_V6_PLUS_SEMANTIC_CLAIM_MODELS_V7"
        ):
            findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH", "detail": "quality_profile"})
    elif requires_semantic_v6:
        if quality_profile != (
            "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
            "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5_PLUS_"
            "SEMANTIC_DECISION_CHAINS_V6"
        ):
            findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH", "detail": "quality_profile"})
    elif requires_semantic_v5:
        if quality_profile != (
            "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_"
            "SEMANTIC_COMPARATORS_V4_PLUS_SEMANTIC_SECTIONS_V5"
        ):
            findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH", "detail": "quality_profile"})
    elif requires_semantic_v4:
        if quality_profile != "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_SEMANTIC_COMPARATORS_V4":
            findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH", "detail": "quality_profile"})
    elif requires_semantic_v3:
        if quality_profile != "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3":
            findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH", "detail": "quality_profile"})
    elif quality_profile is not None:
        findings.append({"code": "REVIEW_REQUEST_QUALITY_PROFILE_NOT_ALLOWED", "detail": "quality_profile"})
    if request.get("intent") != FINISHED_REVIEW_INTENT:
        findings.append({"code": "REVIEW_REQUEST_INTENT_MISMATCH", "detail": "intent"})
    if request.get("structure_override_used") is not False:
        findings.append({"code": "REVIEW_STRUCTURE_OVERRIDE_FORBIDDEN", "detail": "structure_override_used"})

    identity = request.get("identity") if isinstance(request.get("identity"), dict) else {}
    try:
        from .exact_identity import exact_locus_display
        exact = exact_locus_display(
            identity.get("strain"), identity.get("full_node_or_contig"),
            identity.get("region"), identity.get("bgc_alias"),
        )
    except Exception:
        exact = ""
        findings.append({"code": "REVIEW_EXACT_IDENTITY_INVALID", "detail": "identity"})
    if exact and identity.get("display") != exact:
        findings.append({"code": "REVIEW_EXACT_IDENTITY_DISPLAY_MISMATCH", "detail": "identity.display"})

    package_manifest = pkg / "manifest.json"
    package_sha = str(request.get("package_manifest_sha256") or "").strip().lower()
    if not _SHA256_RE.fullmatch(package_sha):
        findings.append({"code": "REVIEW_PACKAGE_SHA256_INVALID", "detail": "package_manifest_sha256"})
    elif not package_manifest.is_file():
        findings.append({"code": "REVIEW_PACKAGE_MANIFEST_MISSING", "detail": "manifest.json"})
    elif _review_sha256(package_manifest) != package_sha:
        findings.append({"code": "REVIEW_PACKAGE_SHA256_MISMATCH", "detail": "manifest.json"})
    else:
        try:
            manifest = json.loads(package_manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError):  # v9.7.410: a 200k-deep `[[[[…` request crashed the validator instead of routing to HOLD
            manifest = {}
            findings.append({"code": "REVIEW_PACKAGE_MANIFEST_INVALID", "detail": "manifest.json"})
        if isinstance(manifest, dict) and manifest.get("strain_id") != identity.get("strain"):
            findings.append({"code": "REVIEW_PACKAGE_STRAIN_MISMATCH", "detail": "manifest.strain_id"})
        matches = []
        for row in manifest.get("bgcs", []) if isinstance(manifest, dict) else []:
            if not isinstance(row, dict):
                continue
            region = row.get("antismash_region") or row.get("region")
            if isinstance(region, int) or (isinstance(region, str) and region.isdigit()):
                region = f"region{int(region):03d}"
            if (
                row.get("bgc_id") == identity.get("bgc_alias")
                and row.get("contig") == identity.get("full_node_or_contig")
                and region == identity.get("region")
            ):
                matches.append(row)
        if len(matches) != 1:
            findings.append({"code": "REVIEW_PACKAGE_EXACT_LOCUS_NOT_UNIQUE", "detail": f"matches={len(matches)}"})

    card_spec = request.get("card") if isinstance(request.get("card"), dict) else {}
    card_path = _review_member(root, card_spec.get("locator"), "card", findings)
    card_sha = str(card_spec.get("sha256") or "").strip().lower()
    card_text = ""
    card_hash_matched = False
    if not _SHA256_RE.fullmatch(card_sha):
        findings.append({"code": "REVIEW_CARD_SHA256_INVALID", "detail": "card.sha256"})
    elif card_path is not None:
        if _review_sha256(card_path) != card_sha:
            findings.append({"code": "REVIEW_CARD_SHA256_MISMATCH", "detail": "card"})
        else:
            card_hash_matched = True
            card_text = card_path.read_text(encoding="utf-8", errors="replace")
            if "FINISHED_FULL48_CURRENT_EVIDENCE" not in card_text:
                findings.append({"code": "REVIEW_CARD_PROFILE_MISSING", "detail": "card"})
            if exact and exact not in card_text:
                findings.append({"code": "REVIEW_CARD_EXACT_IDENTITY_MISSING", "detail": "card"})

    roster_spec = request.get("roster") if isinstance(request.get("roster"), dict) else {}
    roster_path = _review_member(root, roster_spec.get("locator"), "roster", findings)
    roster_file_sha = str(roster_spec.get("sha256") or "").strip().lower()
    roster_digest = str(roster_spec.get("query_roster_sha256") or "").strip().lower()
    if not _SHA256_RE.fullmatch(roster_file_sha):
        findings.append({"code": "REVIEW_ROSTER_FILE_SHA256_INVALID", "detail": "roster.sha256"})
    elif roster_path is not None and _review_sha256(roster_path) != roster_file_sha:
        findings.append({"code": "REVIEW_ROSTER_FILE_SHA256_MISMATCH", "detail": "roster"})
    if not _SHA256_RE.fullmatch(roster_digest):
        findings.append({"code": "REVIEW_ROSTER_DIGEST_INVALID", "detail": "roster.query_roster_sha256"})

    canonical_loci: list[str] = []
    if roster_path is not None:
        try:
            from .mode_b.gene_first_stage_v2 import (
                ROSTER_FIELDS,
                StageHold,
                _validate_roster,
                query_roster_sha256,
            )
            with roster_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                header = reader.fieldnames or []
                if len(header) != len(set(header)):
                    raise ValueError("duplicate roster header")
                missing = [field for field in ROSTER_FIELDS if field not in header]
                if missing:
                    raise ValueError("missing canonical roster fields")
                roster_rows = [
                    {key: (value or "").strip() for key, value in row.items() if key is not None}
                    for row in reader
                ]
            gene_first_identity = {
                "strain": identity.get("strain"),
                "full_node": identity.get("full_node_or_contig"),
                "region": identity.get("region"),
                "bgc_alias": identity.get("bgc_alias"),
                "exact_identity": exact,
            }
            validated_roster = _validate_roster(roster_rows, gene_first_identity)
            canonical_loci = [row["locus_tag"] for row in validated_roster]
            computed_roster_digest = query_roster_sha256(
                gene_first_identity, validated_roster
            )
            if _SHA256_RE.fullmatch(roster_digest) and computed_roster_digest != roster_digest:
                findings.append({
                    "code": "REVIEW_ROSTER_DIGEST_MISMATCH",
                    "detail": "roster.query_roster_sha256",
                })
        except (OSError, UnicodeDecodeError, csv.Error, KeyError, ValueError, StageHold):
            canonical_loci = []
            findings.append({
                "code": "REVIEW_ROSTER_CONTENT_INVALID",
                "detail": "canonical gene-first roster",
            })

    common_expected = {
        "exact_identity": exact,
        "card_sha256": card_sha,
        "package_manifest_sha256": package_sha,
        "query_roster_sha256": roster_digest,
    }
    if requires_semantic_v3:
        common_expected["quality_profile"] = quality_profile

    # Candidate request v1.3 hardening: section-level receipt literals must
    # resolve to the exact independently verified artifacts in this packet.
    # Older request versions retain their documented field set and semantics.
    section_receipt_specs = request.get("section_evidence_receipts")
    if requires_semantic_v5:
        section_receipt_specs = (
            section_receipt_specs if isinstance(section_receipt_specs, dict) else {}
        )
        expected_section_receipt_names = {
            "section15_missing_evidence_state", "section43_rggmci_run",
        }
        if set(section_receipt_specs) != expected_section_receipt_names:
            findings.append({
                "code": "REVIEW_SECTION_EVIDENCE_RECEIPT_SET_MISMATCH",
                "detail": ",".join(sorted(section_receipt_specs)),
            })
        section15_specs = section_receipt_specs.get("section15_missing_evidence_state")
        if not isinstance(section15_specs, list) or not section15_specs:
            findings.append({
                "code": "REVIEW_SECTION15_RECEIPT_SET_EMPTY",
                "detail": "section_evidence_receipts.section15_missing_evidence_state",
            })
            section15_specs = []
        fingerprints = [
            (str(spec.get("locator") or ""), str(spec.get("sha256") or "").lower())
            for spec in section15_specs if isinstance(spec, dict)
        ]
        locators = [locator for locator, _ in fingerprints]
        hashes = [digest for _, digest in fingerprints]
        if (len(locators) != len(set(locators))
                or len(hashes) != len(set(hashes))):
            findings.append({
                "code": "REVIEW_SECTION15_RECEIPT_DUPLICATE",
                "detail": "section_evidence_receipts.section15_missing_evidence_state",
            })
        section15_hashes: list[str] = []
        for index, spec in enumerate(section15_specs):
            label = f"section_evidence_receipts.section15_missing_evidence_state[{index}]"
            value = _review_json_member(root, spec, label, findings)
            if isinstance(spec, dict) and _SHA256_RE.fullmatch(
                str(spec.get("sha256") or "").lower()
            ):
                section15_hashes.append(str(spec["sha256"]).lower())
            if value is not None:
                for field in ("exact_identity", "package_manifest_sha256", "query_roster_sha256"):
                    if value.get(field) != common_expected[field]:
                        findings.append({"code": "REVIEW_SECTION_EVIDENCE_BINDING_MISMATCH", "detail": f"{label}.{field}"})
                if value.get("receipt_role") != "SECTION_15_MISSING_EVIDENCE_STATE":
                    findings.append({"code": "REVIEW_SECTION_EVIDENCE_ROLE_MISMATCH", "detail": label})
                if value.get("status") != "COMPLETE":
                    findings.append({"code": "REVIEW_SECTION_EVIDENCE_NOT_COMPLETE", "detail": label})
        section43_spec = section_receipt_specs.get("section43_rggmci_run")
        section43_value = _review_json_member(
            root, section43_spec,
            "section_evidence_receipts.section43_rggmci_run", findings,
        )
        section43_hash = (
            str(section43_spec.get("sha256") or "").lower()
            if isinstance(section43_spec, dict) else ""
        )
        if section43_value is not None:
            for field in ("exact_identity", "package_manifest_sha256", "query_roster_sha256"):
                if section43_value.get(field) != common_expected[field]:
                    findings.append({"code": "REVIEW_SECTION_EVIDENCE_BINDING_MISMATCH", "detail": f"section43_rggmci_run.{field}"})
            if section43_value.get("receipt_role") != "SECTION_43_RGGMCI_RUN":
                findings.append({"code": "REVIEW_SECTION_EVIDENCE_ROLE_MISMATCH", "detail": "section43_rggmci_run"})
            if section43_value.get("status") != "COMPLETE":
                findings.append({"code": "REVIEW_SECTION_EVIDENCE_NOT_COMPLETE", "detail": "section43_rggmci_run"})
        if card_hash_matched:
            from .modeb_publication_gate import semantic_sections_v5_receipt_hashes
            card_receipts = semantic_sections_v5_receipt_hashes(card_text)
            if sorted(card_receipts["section15_missing_evidence_state"]) != sorted(section15_hashes):
                findings.append({"code": "REVIEW_SECTION15_RECEIPT_BINDING_MISMATCH", "detail": "card section 15"})
            if card_receipts["section31_canonical_roster"] != [roster_digest]:
                findings.append({"code": "REVIEW_SECTION31_ROSTER_DIGEST_MISMATCH", "detail": "card section 31"})
            if card_receipts["section43_rggmci_run"] != [section43_hash]:
                findings.append({"code": "REVIEW_SECTION43_RECEIPT_BINDING_MISMATCH", "detail": "card section 43"})
    elif section_receipt_specs is not None:
        findings.append({
            "code": "REVIEW_SECTION_EVIDENCE_RECEIPTS_NOT_ALLOWED",
            "detail": "section_evidence_receipts",
        })

    # Candidate request v1.4 binds every v6 evidence cell to one exact,
    # section-keyed receipt.  Both measured and typed terminal rows are bound:
    # an author-written unavailable claim is still an evidence-state claim.
    decision_receipt_specs = request.get(
        "semantic_decision_chain_evidence_receipts")
    decision_sections = (14, 16, 21, 22, 23, 25, 30, 41)
    if requires_semantic_v6:
        decision_receipt_specs = (
            decision_receipt_specs
            if isinstance(decision_receipt_specs, dict) else {}
        )
        expected_decision_keys = {f"section{section}" for section in decision_sections}
        if set(decision_receipt_specs) != expected_decision_keys:
            findings.append({
                "code": "REVIEW_DECISION_CHAIN_RECEIPT_SET_MISMATCH",
                "detail": ",".join(sorted(decision_receipt_specs)),
            })
        receipt_bindings: dict[str, list[tuple[str, str]]] = {}
        for section in decision_sections:
            key = f"section{section}"
            specs = decision_receipt_specs.get(key)
            if not isinstance(specs, list) or not specs:
                findings.append({
                    "code": "REVIEW_DECISION_CHAIN_RECEIPT_SET_EMPTY",
                    "detail": key,
                })
                specs = []
            fingerprints = [
                (str(spec.get("locator") or ""),
                 str(spec.get("sha256") or "").strip().lower())
                for spec in specs if isinstance(spec, dict)
            ]
            locators = [locator for locator, _ in fingerprints]
            hashes = [digest for _, digest in fingerprints]
            if (len(locators) != len(set(locators))
                    or len(hashes) != len(set(hashes))):
                findings.append({
                    "code": "REVIEW_DECISION_CHAIN_RECEIPT_DUPLICATE",
                    "detail": key,
                })
            receipt_bindings[key] = []
            for index, spec in enumerate(specs):
                label = (
                    "semantic_decision_chain_evidence_receipts."
                    f"{key}[{index}]"
                )
                value = _review_json_member(root, spec, label, findings)
                digest = (
                    str(spec.get("sha256") or "").strip().lower()
                    if isinstance(spec, dict) else ""
                )
                if value is None:
                    continue
                for field in (
                    "exact_identity", "package_manifest_sha256",
                    "query_roster_sha256",
                ):
                    if value.get(field) != common_expected[field]:
                        findings.append({
                            "code": "REVIEW_DECISION_CHAIN_EVIDENCE_BINDING_MISMATCH",
                            "detail": f"{label}.{field}",
                        })
                if value.get("receipt_role") != "MODEB_SEMANTIC_DECISION_CHAIN_EVIDENCE":
                    findings.append({
                        "code": "REVIEW_DECISION_CHAIN_EVIDENCE_ROLE_MISMATCH",
                        "detail": label,
                    })
                if value.get("section_number") != section:
                    findings.append({
                        "code": "REVIEW_DECISION_CHAIN_EVIDENCE_SECTION_MISMATCH",
                        "detail": label,
                    })
                state = str(value.get("typed_state") or "").strip()
                if not state or state != state.upper():
                    findings.append({
                        "code": "REVIEW_DECISION_CHAIN_EVIDENCE_STATE_INVALID",
                        "detail": label,
                    })
                if value.get("status") != "COMPLETE":
                    findings.append({
                        "code": "REVIEW_DECISION_CHAIN_EVIDENCE_NOT_COMPLETE",
                        "detail": label,
                    })
                receipt_bindings[key].append((state, digest))
        if card_hash_matched:
            from .modeb_publication_gate import semantic_decision_chain_v6_bindings
            card_bindings = semantic_decision_chain_v6_bindings(card_text)
            for section in decision_sections:
                key = f"section{section}"
                card_pairs: list[tuple[str, str]] = []
                for row in card_bindings.get(key, []):
                    hashes = row.get("evidence_hashes")
                    if not isinstance(hashes, list) or len(hashes) != 1:
                        findings.append({
                            "code": "REVIEW_DECISION_CHAIN_CARD_EVIDENCE_HASH_COUNT_MISMATCH",
                            "detail": key,
                        })
                        continue
                    card_pairs.append((
                        str(row.get("typed_state") or "").strip(),
                        str(hashes[0]).strip().lower(),
                    ))
                if sorted(card_pairs) != sorted(receipt_bindings.get(key, [])):
                    findings.append({
                        "code": "REVIEW_DECISION_CHAIN_CARD_RECEIPT_BINDING_MISMATCH",
                        "detail": key,
                    })
    elif decision_receipt_specs is not None:
        findings.append({
            "code": "REVIEW_DECISION_CHAIN_EVIDENCE_RECEIPTS_NOT_ALLOWED",
            "detail": "semantic_decision_chain_evidence_receipts",
        })

    claim_receipt_specs = request.get("semantic_claim_model_evidence_receipts")
    claim_sections = (8, 11, 13, 44)
    if requires_semantic_v7:
        claim_receipt_specs = claim_receipt_specs if isinstance(claim_receipt_specs, dict) else {}
        expected_claim_keys = {f"section{section}" for section in claim_sections}
        if set(claim_receipt_specs) != expected_claim_keys:
            findings.append({"code": "REVIEW_CLAIM_MODEL_RECEIPT_SET_MISMATCH",
                             "detail": ",".join(sorted(claim_receipt_specs))})
        claim_bindings: dict[str, list[tuple[str, str]]] = {}
        for section in claim_sections:
            key = f"section{section}"
            specs = claim_receipt_specs.get(key)
            if not isinstance(specs, list) or not specs:
                findings.append({"code": "REVIEW_CLAIM_MODEL_RECEIPT_SET_EMPTY", "detail": key})
                specs = []
            fingerprints = [(str(spec.get("locator") or ""), str(spec.get("sha256") or "").strip().lower())
                            for spec in specs if isinstance(spec, dict)]
            if (len([x[0] for x in fingerprints]) != len({x[0] for x in fingerprints})
                    or len([x[1] for x in fingerprints]) != len({x[1] for x in fingerprints})):
                findings.append({"code": "REVIEW_CLAIM_MODEL_RECEIPT_DUPLICATE", "detail": key})
            claim_bindings[key] = []
            for index, spec in enumerate(specs):
                label = f"semantic_claim_model_evidence_receipts.{key}[{index}]"
                value = _review_json_member(root, spec, label, findings)
                digest = str(spec.get("sha256") or "").strip().lower() if isinstance(spec, dict) else ""
                if value is None:
                    continue
                for field in ("exact_identity", "package_manifest_sha256", "query_roster_sha256"):
                    if value.get(field) != common_expected[field]:
                        findings.append({"code": "REVIEW_CLAIM_MODEL_EVIDENCE_BINDING_MISMATCH",
                                         "detail": f"{label}.{field}"})
                if value.get("receipt_role") != "MODEB_SEMANTIC_CLAIM_MODEL_EVIDENCE":
                    findings.append({"code": "REVIEW_CLAIM_MODEL_EVIDENCE_ROLE_MISMATCH", "detail": label})
                if value.get("section_number") != section:
                    findings.append({"code": "REVIEW_CLAIM_MODEL_EVIDENCE_SECTION_MISMATCH", "detail": label})
                state = str(value.get("typed_state") or "").strip()
                if not state or state != state.upper():
                    findings.append({"code": "REVIEW_CLAIM_MODEL_EVIDENCE_STATE_INVALID", "detail": label})
                if value.get("status") != "COMPLETE":
                    findings.append({"code": "REVIEW_CLAIM_MODEL_EVIDENCE_NOT_COMPLETE", "detail": label})
                claim_bindings[key].append((state, digest))
        if card_hash_matched:
            from .modeb_publication_gate import semantic_claim_model_v7_bindings
            card_bindings = semantic_claim_model_v7_bindings(card_text)
            for section in claim_sections:
                key = f"section{section}"
                card_pairs: list[tuple[str, str]] = []
                for row in card_bindings.get(key, []):
                    hashes = row.get("evidence_hashes")
                    if not isinstance(hashes, list) or len(hashes) != 1:
                        findings.append({"code": "REVIEW_CLAIM_MODEL_CARD_EVIDENCE_HASH_COUNT_MISMATCH", "detail": key})
                        continue
                    card_pairs.append((str(row.get("typed_state") or "").strip(), str(hashes[0]).lower()))
                if sorted(card_pairs) != sorted(claim_bindings.get(key, [])):
                    findings.append({"code": "REVIEW_CLAIM_MODEL_CARD_RECEIPT_BINDING_MISMATCH", "detail": key})
    elif claim_receipt_specs is not None:
        findings.append({"code": "REVIEW_CLAIM_MODEL_EVIDENCE_RECEIPTS_NOT_ALLOWED",
                         "detail": "semantic_claim_model_evidence_receipts"})

    inventory_receipt_specs = request.get("inventory_reconciliation_evidence_receipts")
    inventory_sections = (32, 33, 34, 35, 37, 38)
    if requires_inventory_v8:
        inventory_receipt_specs = (
            inventory_receipt_specs if isinstance(inventory_receipt_specs, dict) else {})
        expected_inventory_keys = {f"section{section}" for section in inventory_sections}
        if set(inventory_receipt_specs) != expected_inventory_keys:
            findings.append({"code": "REVIEW_INVENTORY_RECEIPT_SET_MISMATCH",
                             "detail": ",".join(sorted(inventory_receipt_specs))})
        inventory_bindings: dict[str, list[tuple[str, str, str, str, str, str]]] = {}
        for section in inventory_sections:
            key = f"section{section}"
            specs = inventory_receipt_specs.get(key)
            if not isinstance(specs, list) or not specs:
                findings.append({"code": "REVIEW_INVENTORY_RECEIPT_SET_EMPTY", "detail": key})
                specs = []
            fingerprints = [(str(spec.get("locator") or ""),
                             str(spec.get("sha256") or "").strip().lower())
                            for spec in specs if isinstance(spec, dict)]
            if (len([x[0] for x in fingerprints]) != len({x[0] for x in fingerprints})
                    or len([x[1] for x in fingerprints]) != len({x[1] for x in fingerprints})):
                findings.append({"code": "REVIEW_INVENTORY_RECEIPT_DUPLICATE", "detail": key})
            inventory_bindings[key] = []
            for index, spec in enumerate(specs):
                label = f"inventory_reconciliation_evidence_receipts.{key}[{index}]"
                value = _review_json_member(root, spec, label, findings)
                digest = str(spec.get("sha256") or "").strip().lower() if isinstance(spec, dict) else ""
                if value is None:
                    continue
                for field in ("exact_identity", "package_manifest_sha256", "query_roster_sha256"):
                    if value.get(field) != common_expected[field]:
                        findings.append({"code": "REVIEW_INVENTORY_EVIDENCE_BINDING_MISMATCH",
                                         "detail": f"{label}.{field}"})
                if value.get("receipt_role") != "MODEB_INVENTORY_RECONCILIATION_EVIDENCE":
                    findings.append({"code": "REVIEW_INVENTORY_EVIDENCE_ROLE_MISMATCH", "detail": label})
                if value.get("section_number") != section:
                    findings.append({"code": "REVIEW_INVENTORY_EVIDENCE_SECTION_MISMATCH", "detail": label})
                state = str(value.get("typed_state") or "").strip()
                member = str(value.get("exact_member_or_typed_zero") or "").strip()
                role = str(value.get("section_specific_role") or "").strip()
                denominator = str(value.get("declared_denominator") if value.get("declared_denominator") is not None else "").strip()
                evidence_state = str(value.get("evidence_state") or "").strip()
                if not state or state != state.upper():
                    findings.append({"code": "REVIEW_INVENTORY_EVIDENCE_STATE_INVALID", "detail": label})
                if value.get("status") != "COMPLETE":
                    findings.append({"code": "REVIEW_INVENTORY_EVIDENCE_NOT_COMPLETE", "detail": label})
                inventory_bindings[key].append(
                    (state, member, role, digest, denominator, evidence_state))
        if card_hash_matched:
            from .modeb_publication_gate import inventory_reconciliation_v8_bindings
            card_bindings = inventory_reconciliation_v8_bindings(card_text)
            for section in inventory_sections:
                key = f"section{section}"
                card_rows: list[tuple[str, str, str, str, str, str]] = []
                for row in card_bindings.get(key, []):
                    hashes = row.get("evidence_hashes")
                    if not isinstance(hashes, list) or len(hashes) != 1:
                        findings.append({"code": "REVIEW_INVENTORY_CARD_EVIDENCE_HASH_COUNT_MISMATCH",
                                         "detail": key})
                        continue
                    card_rows.append((
                        str(row.get("typed_state") or "").strip(),
                        str(row.get("exact_member_or_typed_zero") or "").strip(),
                        str(row.get("section_specific_role") or "").strip(),
                        str(hashes[0]).strip().lower(),
                        str(row.get("declared_denominator") or "").strip(),
                        str(row.get("evidence_state") or "").strip(),
                    ))
                if sorted(card_rows) != sorted(inventory_bindings.get(key, [])):
                    findings.append({"code": "REVIEW_INVENTORY_CARD_RECEIPT_BINDING_MISMATCH",
                                     "detail": key})
    elif inventory_receipt_specs is not None:
        findings.append({"code": "REVIEW_INVENTORY_EVIDENCE_RECEIPTS_NOT_ALLOWED",
                         "detail": "inventory_reconciliation_evidence_receipts"})

    selection_spec = request.get("selection_process_evidence_receipt")
    if requires_selection_v9:
        label = "selection_process_evidence_receipt"
        selection_value = _review_json_member(root, selection_spec, label, findings)
        selection_digest = (
            str(selection_spec.get("sha256") or "").strip().lower()
            if isinstance(selection_spec, dict) else "")
        external_tuple: tuple[str, ...] | None = None
        if selection_value is not None:
            for field in ("exact_identity", "package_manifest_sha256", "query_roster_sha256"):
                if selection_value.get(field) != common_expected[field]:
                    findings.append({"code": "REVIEW_SELECTION_EVIDENCE_BINDING_MISMATCH",
                                     "detail": f"{label}.{field}"})
            if selection_value.get("receipt_role") != "MODEB_SELECTION_PROCESS_EVIDENCE":
                findings.append({"code": "REVIEW_SELECTION_EVIDENCE_ROLE_MISMATCH", "detail": label})
            if selection_value.get("section_number") != 2:
                findings.append({"code": "REVIEW_SELECTION_EVIDENCE_SECTION_MISMATCH", "detail": label})
            if selection_value.get("selected_exact_identity") != exact:
                findings.append({"code": "REVIEW_SELECTION_SELECTED_IDENTITY_MISMATCH", "detail": label})
            state = str(selection_value.get("selection_state") or "").strip()
            if not state or state != state.upper():
                findings.append({"code": "REVIEW_SELECTION_EVIDENCE_STATE_INVALID", "detail": label})
            if selection_value.get("status") != "COMPLETE":
                findings.append({"code": "REVIEW_SELECTION_EVIDENCE_NOT_COMPLETE", "detail": label})
            external_tuple = (
                state,
                str(selection_value.get("selected_exact_identity") or "").strip(),
                str(selection_value.get("comparator_exact_identity_or_terminal_state") or "").strip(),
                str(selection_value.get("candidate_set_denominator") if selection_value.get("candidate_set_denominator") is not None else "").strip(),
                selection_digest,
                str(selection_value.get("selected_observed_metrics") or "").strip(),
                str(selection_value.get("comparator_metrics_or_terminal_basis") or "").strip(),
                str(selection_value.get("predeclared_selection_rule") or "").strip(),
                str(selection_value.get("rule_evaluation") or "").strip(),
            )
        if card_hash_matched:
            from .modeb_publication_gate import selection_process_v9_bindings
            card_rows = selection_process_v9_bindings(card_text)
            if len(card_rows) != 1:
                findings.append({"code": "REVIEW_SELECTION_CARD_ROW_COUNT_MISMATCH",
                                 "detail": str(len(card_rows))})
            else:
                row = card_rows[0]
                hashes = row.get("candidate_set_hashes")
                if not isinstance(hashes, list) or len(hashes) != 1:
                    findings.append({"code": "REVIEW_SELECTION_CARD_RECEIPT_HASH_COUNT_MISMATCH",
                                     "detail": "section2"})
                else:
                    card_tuple = (
                        str(row.get("selection_state") or "").strip(),
                        str(row.get("selected_exact_identity") or "").strip(),
                        str(row.get("comparator_exact_identity_or_terminal_state") or "").strip(),
                        str(row.get("candidate_set_denominator") or "").strip(),
                        str(hashes[0]).strip().lower(),
                        str(row.get("selected_observed_metrics") or "").strip(),
                        str(row.get("comparator_metrics_or_terminal_basis") or "").strip(),
                        str(row.get("predeclared_selection_rule") or "").strip(),
                        str(row.get("rule_evaluation") or "").strip(),
                    )
                    if external_tuple is None or card_tuple != external_tuple:
                        findings.append({"code": "REVIEW_SELECTION_CARD_RECEIPT_BINDING_MISMATCH",
                                         "detail": "section2"})
    elif selection_spec is not None:
        findings.append({"code": "REVIEW_SELECTION_EVIDENCE_RECEIPT_NOT_ALLOWED",
                         "detail": "selection_process_evidence_receipt"})

    figure_spec = request.get("locus_map_v8_receipt")
    visual_spec = request.get("locus_map_visual_review_receipt")
    if requires_figure_v10:
        figure_label = "locus_map_v8_receipt"
        figure_payload = _review_json_member(root, figure_spec, figure_label, findings)
        figure_digest = (
            str(figure_spec.get("sha256") or "").strip().lower()
            if isinstance(figure_spec, dict) else "")
        validated_figure: dict[str, Any] | None = None
        receipt_path: Path | None = None
        if figure_payload is not None and isinstance(figure_spec, dict):
            receipt_path = (root / str(figure_spec["locator"])).resolve()
            try:
                from .locus_map_v8 import validate_locus_map_v8_receipt
                validated_figure = validate_locus_map_v8_receipt(
                    receipt_path, expected_bgc_id=str(identity.get("bgc_alias") or ""))
            except Exception as exc:
                detail = getattr(exc, "details", (type(exc).__name__,))
                findings.append({"code": "REVIEW_LOCUS_MAP_V8_INVALID",
                                 "detail": ",".join(map(str, detail))})
        interval_literal = ""
        if validated_figure is not None and receipt_path is not None:
            locus_identity = validated_figure.get("exact_locus_identity")
            locus_identity = locus_identity if isinstance(locus_identity, dict) else {}
            component_pairs = (
                ("strain", "strain"), ("full_node_or_contig", "full_node_or_contig"),
                ("region", "region"), ("bgc_alias", "bgc_alias"),
            )
            for receipt_key, request_key in component_pairs:
                if locus_identity.get(receipt_key) != identity.get(request_key):
                    findings.append({"code": "REVIEW_LOCUS_MAP_IDENTITY_MISMATCH",
                                     "detail": receipt_key})
            sources = validated_figure.get("sources")
            if not isinstance(sources, list) or not sources:
                findings.append({"code": "REVIEW_LOCUS_MAP_SOURCES_MISSING",
                                 "detail": "sources"})
            else:
                for index, source in enumerate(sources):
                    label = f"locus_map_v8_receipt.sources[{index}]"
                    if not isinstance(source, dict):
                        findings.append({"code": "REVIEW_LOCUS_MAP_SOURCE_INVALID", "detail": label})
                        continue
                    locator = str(source.get("path") or "")
                    source_path = Path(locator)
                    if source_path.is_absolute() or ".." in source_path.parts:
                        findings.append({"code": "REVIEW_LOCUS_MAP_SOURCE_UNSAFE", "detail": label})
                        continue
                    resolved_source = (pkg / source_path).resolve()
                    try:
                        resolved_source.relative_to(pkg)
                    except ValueError:
                        findings.append({"code": "REVIEW_LOCUS_MAP_SOURCE_UNSAFE", "detail": label})
                        continue
                    if not resolved_source.is_file():
                        findings.append({"code": "REVIEW_LOCUS_MAP_SOURCE_MISSING", "detail": label})
                    elif (_review_sha256(resolved_source) != source.get("sha256")
                          or resolved_source.stat().st_size != source.get("bytes")):
                        findings.append({"code": "REVIEW_LOCUS_MAP_SOURCE_INTEGRITY_MISMATCH",
                                         "detail": label})
            outputs = validated_figure.get("outputs")
            csv_name = outputs.get("csv") if isinstance(outputs, dict) else None
            csv_path = receipt_path.parent / str(csv_name or "")
            try:
                with csv_path.open(encoding="utf-8", newline="") as handle:
                    figure_rows = list(csv.DictReader(handle))
                figure_loci = [str(row.get("locus_tag") or "").strip() for row in figure_rows]
                if figure_loci != list(canonical_loci):
                    findings.append({"code": "REVIEW_LOCUS_MAP_CANONICAL_ROSTER_MISMATCH",
                                     "detail": ",".join(figure_loci)})
                starts = [int(row["start"]) for row in figure_rows]
                ends = [int(row["end"]) for row in figure_rows]
                if not starts or not ends:
                    raise ValueError
                interval_literal = f"{min(starts)}-{max(ends)} bp"
            except (OSError, csv.Error, KeyError, TypeError, ValueError):
                findings.append({"code": "REVIEW_LOCUS_MAP_INTERVAL_UNAVAILABLE",
                                 "detail": "csv start/end"})
        visual = _review_json_member(root, visual_spec, "locus_map_visual_review_receipt", findings)
        visual_digest = (
            str(visual_spec.get("sha256") or "").strip().lower()
            if isinstance(visual_spec, dict) else "")
        visual_state = ""
        if visual is not None:
            if visual.get("receipt_role") != "MODEB_LOCUS_MAP_VISUAL_REVIEW":
                findings.append({"code": "REVIEW_LOCUS_MAP_VISUAL_ROLE_MISMATCH",
                                 "detail": "locus_map_visual_review_receipt"})
            for field, expected_value in (
                ("exact_identity", exact),
                ("locus_map_v8_receipt_sha256", figure_digest),
            ):
                if visual.get(field) != expected_value:
                    findings.append({"code": "REVIEW_LOCUS_MAP_VISUAL_BINDING_MISMATCH",
                                     "detail": field})
            visual_state = str(visual.get("visual_review_state") or "").strip().upper()
            if visual_state != "PASS_OWNER_REVIEWED":
                findings.append({"code": "REVIEW_LOCUS_MAP_VISUAL_NOT_PASS",
                                 "detail": visual_state})
            checks = visual.get("checks")
            expected_checks = {
                "clipped_arrows", "overlapping_labels", "unreadable_type",
                "missing_legend", "hidden_suppression", "ambiguous_identity",
                "absent_companion_data",
            }
            if not isinstance(checks, dict) or set(checks) != expected_checks:
                findings.append({"code": "REVIEW_LOCUS_MAP_VISUAL_CHECK_SET_MISMATCH",
                                 "detail": "checks"})
            elif any(checks.values()):
                findings.append({"code": "REVIEW_LOCUS_MAP_VISUAL_DEFECT_PRESENT",
                                 "detail": ",".join(sorted(k for k, v in checks.items() if v))})
            integrity = (
                validated_figure.get("output_integrity")
                if isinstance(validated_figure, dict) else {})
            for kind in ("png", "svg"):
                expected_hash = (
                    integrity.get(kind, {}).get("sha256")
                    if isinstance(integrity, dict) and isinstance(integrity.get(kind), dict)
                    else None)
                if visual.get(f"{kind}_sha256") != expected_hash:
                    findings.append({"code": "REVIEW_LOCUS_MAP_VISUAL_RENDER_MISMATCH",
                                     "detail": kind})
        if card_hash_matched:
            from .modeb_publication_gate import figure_spec_v10_bindings
            card_rows = figure_spec_v10_bindings(card_text)
            if len(card_rows) != 1:
                findings.append({"code": "REVIEW_FIGURE_SPEC_CARD_ROW_COUNT_MISMATCH",
                                 "detail": str(len(card_rows))})
            else:
                row = card_rows[0]
                map_hashes = row.get("locus_map_hashes")
                visual_hashes = row.get("visual_review_hashes")
                if not isinstance(map_hashes, list) or len(map_hashes) != 1:
                    findings.append({"code": "REVIEW_FIGURE_SPEC_CARD_MAP_HASH_COUNT_MISMATCH",
                                     "detail": "section18"})
                if not isinstance(visual_hashes, list) or len(visual_hashes) != 1:
                    findings.append({"code": "REVIEW_FIGURE_SPEC_CARD_VISUAL_HASH_COUNT_MISMATCH",
                                     "detail": "section18"})
                if (isinstance(map_hashes, list) and len(map_hashes) == 1
                        and isinstance(visual_hashes, list) and len(visual_hashes) == 1):
                    expected_tuple = (
                        "FIGURE_RENDERED_REVIEWED", exact, interval_literal,
                        figure_digest, "PNG+SVG+CSV", "ENCODED_WITH_EXPLICIT_MISSING",
                        "PRESENT_PACKAGE_RELATIVE_SOURCES", "VERIFIED_ALL_GENES",
                        visual_digest, visual_state,
                    )
                    card_tuple = (
                        str(row.get("figure_state") or "").strip(),
                        str(row.get("exact_plotted_identity") or "").strip(),
                        str(row.get("plotted_interval") or "").strip(),
                        str(map_hashes[0]).strip().lower(),
                        str(row.get("rendered_formats") or "").strip(),
                        str(row.get("evidence_state_encoding") or "").strip(),
                        str(row.get("provenance_footer") or "").strip(),
                        str(row.get("lossless_sidecar") or "").strip(),
                        str(visual_hashes[0]).strip().lower(),
                        str(row.get("visual_review_state") or "").strip(),
                    )
                    if card_tuple != expected_tuple:
                        findings.append({"code": "REVIEW_FIGURE_SPEC_CARD_BINDING_MISMATCH",
                                         "detail": "section18"})
    elif figure_spec is not None or visual_spec is not None:
        findings.append({"code": "REVIEW_FIGURE_SPEC_RECEIPTS_NOT_ALLOWED",
                         "detail": "locus_map_v8_receipt,locus_map_visual_review_receipt"})
    verification_specs = request.get("verification_receipts")
    verification_specs = verification_specs if isinstance(verification_specs, dict) else {}
    verification_names = ["structure", "substantive_quality_v2", "blinded_score"]
    if requires_semantic_v3:
        verification_names.append("semantic_sections_v3")
    if requires_semantic_v4:
        verification_names.append("semantic_comparators_v4")
    if requires_semantic_v5:
        verification_names.append("semantic_sections_v5")
    if requires_semantic_v6:
        verification_names.append("semantic_decision_chains_v6")
    if requires_semantic_v7:
        verification_names.append("semantic_claim_models_v7")
    if requires_inventory_v8:
        verification_names.append("inventory_reconciliation_v8")
    if requires_selection_v9:
        verification_names.append("selection_process_v9")
    if requires_figure_v10:
        verification_names.append("figure_spec_v10")
    if requires_reconciliation_v11:
        verification_names.append("reconciliation_specificity_v11")
    if set(verification_specs) != set(verification_names):
        findings.append({
            "code": "REVIEW_VERIFICATION_RECEIPT_SET_MISMATCH",
            "detail": ",".join(sorted(verification_specs)),
        })
    receipts: dict[str, dict[str, Any] | None] = {}
    for name in verification_names:
        receipts[name] = _review_json_member(
            root, verification_specs.get(name), f"verification_receipts.{name}", findings
        )
        value = receipts[name]
        if value is not None:
            for field, expected in common_expected.items():
                if value.get(field) != expected:
                    findings.append({"code": "REVIEW_RECEIPT_BINDING_MISMATCH", "detail": f"{name}.{field}"})

    structure = receipts.get("structure") or {}
    if structure and (
        structure.get("status") != "PASS"
        or structure.get("profile") != "FINISHED_FULL48_CURRENT_EVIDENCE"
    ):
        findings.append({"code": "REVIEW_STRUCTURE_RECEIPT_NOT_PASS", "detail": "structure"})
    quality = receipts.get("substantive_quality_v2") or {}
    if quality and (
        quality.get("status") != "PASS"
        or quality.get("substantive_quality_v2") is not True
    ):
        findings.append({"code": "REVIEW_QUALITY_V2_RECEIPT_NOT_PASS", "detail": "substantive_quality_v2"})
    semantic_v3 = receipts.get("semantic_sections_v3") or {}
    if requires_semantic_v3 and semantic_v3 and (
        semantic_v3.get("status") != "PASS"
        or semantic_v3.get("semantic_sections_v3") is not True
    ):
        findings.append({"code": "REVIEW_SEMANTIC_V3_RECEIPT_NOT_PASS", "detail": "semantic_sections_v3"})
    semantic_v4 = receipts.get("semantic_comparators_v4") or {}
    if requires_semantic_v4 and semantic_v4 and (
        semantic_v4.get("status") != "PASS"
        or semantic_v4.get("semantic_comparators_v4") is not True
    ):
        findings.append({"code": "REVIEW_SEMANTIC_V4_RECEIPT_NOT_PASS", "detail": "semantic_comparators_v4"})
    semantic_v5 = receipts.get("semantic_sections_v5") or {}
    if requires_semantic_v5 and semantic_v5 and (
        semantic_v5.get("status") != "PASS"
        or semantic_v5.get("semantic_sections_v5") is not True
    ):
        findings.append({"code": "REVIEW_SEMANTIC_V5_RECEIPT_NOT_PASS", "detail": "semantic_sections_v5"})
    semantic_v6 = receipts.get("semantic_decision_chains_v6") or {}
    if requires_semantic_v6 and semantic_v6 and (
        semantic_v6.get("status") != "PASS"
        or semantic_v6.get("semantic_decision_chains_v6") is not True
    ):
        findings.append({"code": "REVIEW_SEMANTIC_V6_RECEIPT_NOT_PASS", "detail": "semantic_decision_chains_v6"})
    semantic_v7 = receipts.get("semantic_claim_models_v7") or {}
    if requires_semantic_v7 and semantic_v7 and (
        semantic_v7.get("status") != "PASS"
        or semantic_v7.get("semantic_claim_models_v7") is not True
    ):
        findings.append({"code": "REVIEW_SEMANTIC_V7_RECEIPT_NOT_PASS", "detail": "semantic_claim_models_v7"})
    inventory_v8 = receipts.get("inventory_reconciliation_v8") or {}
    if requires_inventory_v8 and inventory_v8 and (
        inventory_v8.get("status") != "PASS"
        or inventory_v8.get("inventory_reconciliation_v8") is not True
    ):
        findings.append({"code": "REVIEW_INVENTORY_V8_RECEIPT_NOT_PASS",
                         "detail": "inventory_reconciliation_v8"})
    selection_v9 = receipts.get("selection_process_v9") or {}
    if requires_selection_v9 and selection_v9 and (
        selection_v9.get("status") != "PASS"
        or selection_v9.get("selection_process_v9") is not True
    ):
        findings.append({"code": "REVIEW_SELECTION_V9_RECEIPT_NOT_PASS",
                         "detail": "selection_process_v9"})
    figure_v10 = receipts.get("figure_spec_v10") or {}
    if requires_figure_v10 and figure_v10 and (
        figure_v10.get("status") != "PASS"
        or figure_v10.get("figure_spec_v10") is not True
    ):
        findings.append({"code": "REVIEW_FIGURE_V10_RECEIPT_NOT_PASS",
                         "detail": "figure_spec_v10"})
    reconciliation_v11 = receipts.get("reconciliation_specificity_v11") or {}
    if requires_reconciliation_v11 and reconciliation_v11 and (
        reconciliation_v11.get("status") != "PASS"
        or reconciliation_v11.get("reconciliation_specificity_v11") is not True
    ):
        findings.append({"code": "REVIEW_RECONCILIATION_V11_RECEIPT_NOT_PASS",
                         "detail": "reconciliation_specificity_v11"})
    score = receipts.get("blinded_score") or {}
    if score:
        if score.get("route") != "PASS_TO_HUMAN_REVIEW":
            findings.append({"code": "REVIEW_BLINDED_SCORE_ROUTE_HOLD", "detail": "blinded_score.route"})
        for field in ("rubric_sha256", "scorer_sha256"):
            if not _SHA256_RE.fullmatch(str(score.get(field) or "")):
                findings.append({"code": "REVIEW_BLINDED_SCORE_BINDING_INVALID", "detail": f"blinded_score.{field}"})

    channel_specs = request.get("channel_producer_receipts")
    channel_specs = channel_specs if isinstance(channel_specs, dict) else {}
    if set(channel_specs) != set(FINISHED_REVIEW_CHANNELS):
        findings.append({"code": "REVIEW_CHANNEL_SET_MISMATCH", "detail": ",".join(sorted(channel_specs))})
    for channel in FINISHED_REVIEW_CHANNELS:
        producer = _review_json_member(
            root, channel_specs.get(channel), f"channel_producer_receipts.{channel}", findings
        )
        if producer is None:
            continue
        for field in ("exact_identity", "package_manifest_sha256", "query_roster_sha256"):
            if producer.get(field) != common_expected[field]:
                findings.append({"code": "REVIEW_CHANNEL_BINDING_MISMATCH", "detail": f"{channel}.{field}"})
        if producer.get("channel") != channel:
            findings.append({"code": "REVIEW_CHANNEL_NAME_MISMATCH", "detail": channel})
        if producer.get("producer_state") not in ("COMPLETE", "NO_HIT_COMPLETE"):
            findings.append({"code": "REVIEW_CHANNEL_NOT_COMPLETE", "detail": channel})
        for field in ("database_sha256", "output_sha256"):
            if not _SHA256_RE.fullmatch(str(producer.get(field) or "")):
                findings.append({"code": "REVIEW_CHANNEL_PROVENANCE_INVALID", "detail": f"{channel}.{field}"})

    # Do not trust a self-consistent set of author-written PASS receipts as the only
    # proof. Re-run the bundled deterministic gate against the actual bytes, package
    # context, and independent roster. This does not reproduce the owner-held score;
    # that remains a separately bound receipt and process boundary.
    if card_hash_matched and canonical_loci and identity.get("bgc_alias"):
        try:
            from .modeb_structure_gate import lint_card
            context = _bgc_context_from_triage(pkg, str(identity["bgc_alias"]))
            # The request's independently hash-bound roster is authoritative for
            # this exact review packet.  Thread it into both gate APIs: the
            # publication gate consumes ``canonical_loci`` directly, while the
            # finished BLASTp matrix check reads ``known_locus_tags`` from context.
            context["known_locus_tags"] = list(canonical_loci)
            live_findings = lint_card(
                card_text,
                bgc_context=context,
                check_depth=True,
                strict_depth=True,
                check_class_content=True,
                check_claim_safety=True,
                check_evidence_presence=True,
                check_publication_quality=True,
                check_substantive_quality_v2=True,
                check_semantic_sections_v3=requires_semantic_v3,
                check_semantic_comparators_v4=requires_semantic_v4,
                check_semantic_sections_v5=requires_semantic_v5,
                check_semantic_decision_chains_v6=requires_semantic_v6,
                check_semantic_claim_models_v7=requires_semantic_v7,
                check_inventory_reconciliation_v8=requires_inventory_v8,
                check_selection_process_v9=requires_selection_v9,
                check_figure_spec_v10=requires_figure_v10,
                check_reconciliation_specificity_v11=requires_reconciliation_v11,
                canonical_loci=canonical_loci,
            )
        except Exception as exc:
            live_findings = []
            findings.append({"code": "REVIEW_LIVE_GATE_UNAVAILABLE", "detail": type(exc).__name__})
        live_errors = sorted({str(row.get("code") or "UNKNOWN") for row in live_findings
                              if row.get("severity") == "ERROR"})
        if live_errors:
            findings.append({
                "code": "REVIEW_LIVE_FINISHED_GATE_NOT_PASS",
                "detail": ",".join(live_errors),
            })

    status = "READY_FOR_OWNER_REVIEW" if not findings else "HOLD_FINISHED_REVIEW_REQUEST"
    return {
        "schema_version": request_schema,
        "status": status,
        "exact_identity": exact,
        "finding_codes": sorted({row["code"] for row in findings}),
        "findings": findings,
        "mutation_performed": False,
        "authenticity_ceiling": (
            "Hashes prove byte consistency, not who produced a receipt. The blinded-score "
            "receipt must come from an owner-controlled root or a later authenticated signer."
        ),
        "authority_ceiling": (
            "Internal-consistency routing only; READY does not mean card acceptance, "
            "currentness selection, scientific validation, promotion, integration, release, "
            "or publication readiness."
        ),
    }


def validate_finished_review_request_command(args) -> int:
    result = validate_finished_review_request(
        args.package, args.request, args.artifact_root
    )
    emit(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "READY_FOR_OWNER_REVIEW" else 3


def ingest_receipts_command(args) -> int:
    """CLI: mamey ingest-receipts --package <dir> [--receipt <file.json>]
                                  [--auto-detect | --card <file.md>] [--master <wb.xlsx>]

    Persists Sapote Mode B cards into the judgment store and (optionally) reconciles
    the master workbook's E1_Mode_B_Index from the updated register.

    Three flows, mutually exclusive:

      --receipt <f.json>  — canonical: one receipt may carry many cards
      --auto-detect       — recovery: scan judgment/ for orphan cards (W4)
      --card <f.md>       — synchronous: persist one card directly (N4, v9.7.149c)
    """
    pkg = Path(args.package).resolve()
    if not pkg.exists():
        emit(f"ERROR: package directory not found: {pkg}", file=sys.stderr)
        return 1

    auto = getattr(args, "auto_detect", False)
    receipt = getattr(args, "receipt", None)
    card = getattr(args, "card", None)

    flows = [bool(auto), bool(receipt), bool(card)]
    if sum(flows) > 1:
        emit("ERROR: --auto-detect, --receipt, and --card are mutually exclusive",
              file=sys.stderr)
        return 2
    if sum(flows) == 0:
        emit("ERROR: one of --receipt <file>, --auto-detect, or --card <file> is required",
              file=sys.stderr)
        return 2

    if card:
        force_structure = bool(getattr(args, "force_structure", False))
        card_summary = ingest_one_card(pkg, Path(card).resolve(),
                                        force_structure=force_structure)
        emit(f"Card ingest for {card_summary['strain_id']}:", f"  card:              {card}", f"  BGC:               {card_summary['bgc_id'] or '(unresolved)'}", f"  session:           {card_summary['session_id'] or '(none)'}", f"  status:            {card_summary['status']}", sep="\n")
        # W9: surface structure findings (errors first, then warnings)
        findings = card_summary.get("structure_findings") or []
        n_err = sum(1 for f in findings if f.get("severity") == "ERROR")
        n_warn = sum(1 for f in findings if f.get("severity") == "WARN")
        if findings:
            emit(f"  structure:         {n_err} ERROR(S), {n_warn} WARN(S) "
                  "vs §1–§48 contract")
            for f in findings:
                sec = f"§{f['section']}" if f.get("section") else "—"
                emit(f"    [{f['severity']}] [{f.get('code','?')}] "
                      f"{sec}: {f.get('message','')}", file=sys.stderr)
            if card_summary["status"] == "SKIPPED_STRUCTURE_INVALID":
                emit("\n  Card was NOT recorded. Either fix the structure "
                      "issues above (recommended) or re-run with "
                      "--force-structure to record anyway.", file=sys.stderr)
        else:
            emit("  structure:         PASS (§1–§48 contract satisfied)")
        emit(f"  register status:   {card_summary['judgment_status'] or '(unknown)'}")
        # Exit codes:
        #   0 — RECORDED
        #   3 — SKIPPED_STRUCTURE_INVALID (recoverable: re-run with --force-structure)
        #   4 — RECORDED_WITH_STRUCTURE_OVERRIDE (recorded but flagged)
        #   1 — all other non-recorded outcomes
        st = card_summary["status"]
        if st == "RECORDED":
            return 0
        if st == "RECORDED_WITH_STRUCTURE_OVERRIDE":
            return 4
        if st == "SKIPPED_STRUCTURE_INVALID":
            return 3
        return 1

    if auto:
        force_structure = bool(getattr(args, "force_structure", False))
        summary = auto_detect_ingest(pkg, force_structure=force_structure)
        emit(f"Auto-detect ingest for {summary['strain_id']}:", f"  scanned:           {summary['scanned_count']} *_mode_b.md card(s) in judgment/", sep="\n")
        emit(f"  recorded:          {len(summary['recorded'])} -> "
              f"{', '.join(summary['recorded']) or '(none)'}")
        if summary.get("recorded_with_structure_override"):
            emit(f"  recorded w/ override: "
                  f"{', '.join(summary['recorded_with_structure_override'])}  "
                  "(structure ERRORS present; --force-structure used)")
        if summary["skipped_already_complete"]:
            emit(f"  skipped (done):    "
                  f"{', '.join(summary['skipped_already_complete'])}")
        if summary["skipped_unknown"]:
            emit(f"  SKIPPED (unknown): "
                  f"{', '.join(summary['skipped_unknown'])}  "
                  "(not in register — not invented)")
        if summary.get("skipped_structure_invalid"):
            bad = [f"{bid} ({n} err)"
                   for bid, n in summary["skipped_structure_invalid"]]
            emit(f"  SKIPPED (structure): {', '.join(bad)}  "
                  "(§1–§48 contract violations; rebuild from template or "
                  "re-run with --force-structure)")
        # v9.7.152 (AS-XXX Bug 1): loud, actionable warning for recognizable
        # near-miss filenames that were skipped — prevents silent
        # 'scanned: N, recorded: 0' with no diagnostic.
        if summary.get("skipped_misnamed"):
            emit(f"  WARNING (misnamed): {', '.join((f'{bid} ({fn})' for bid, fn in summary['skipped_misnamed']))}", f"    -> cards must be named '{summary['strain_id']}_<BGC>_mode_b.md'; rename and re-run, or these will not be ingested.", sep="\n", file=sys.stderr)
        emit(f"  register status:   {summary['judgment_status'] or '(unknown)'}")
        # Exit codes: 0 normal; 3 if any cards were rejected for structure
        # (so a CI run can detect that and fail)
        return 3 if summary.get("skipped_structure_invalid") else 0

    master = getattr(args, "master", None)
    force_structure = bool(getattr(args, "force_structure", False))
    try:
        summary = ingest_receipt(pkg, Path(receipt).resolve(), master,
                                  force_structure=force_structure)
    except (FileNotFoundError, ValueError) as e:
        emit(f"ERROR: {e}", file=sys.stderr)
        return 1

    emit(f"Ingested Mode B receipt for {summary['strain_id']}:", f"  recorded:          {len(summary['recorded'])} BGC(s) -> {', '.join(summary['recorded']) or '(none)'}", sep="\n")
    if summary.get("recorded_with_structure_override"):
        emit(f"  recorded w/ override: "
              f"{', '.join(summary['recorded_with_structure_override'])}  "
              "(structure ERRORS present; --force-structure used)")
    if summary["skipped_unknown"]:
        emit(f"  SKIPPED (unknown): {', '.join(summary['skipped_unknown'])}  "
              "(not in register — not invented)")
    if summary["skipped_no_content"]:
        emit(f"  SKIPPED (empty):   {', '.join(summary['skipped_no_content'])}")
    if summary.get("skipped_identity_mismatch"):
        bad = [
            f"{row['receipt_bgc_id']} ({row['reason']})"
            for row in summary["skipped_identity_mismatch"]
        ]
        emit(
            f"  SKIPPED (identity): {', '.join(bad)}  "
            "(receipt/card/package identity conflict; not overridable)"
        )
    if summary.get("skipped_structure_invalid"):
        bad = [f"{bid} ({n} err)"
               for bid, n in summary["skipped_structure_invalid"]]
        emit(f"  SKIPPED (structure): {', '.join(bad)}  "
              "(§1–§48 contract violations; rebuild from template or "
              "re-run with --force-structure)")
    cov = summary.get("coverage_receipt")
    if cov:
        emit(f"  native coverage:   {cov.get('coverage_status') or '(not supplied)'} "
              f"({cov.get('emitted_card_count')}/{cov.get('inventory_bgc_count')} emitted)")
        if cov.get("coverage_only"):
            emit("  native coverage:   coverage-only receipt accepted; no cards recorded")
    emit(f"  register:          {summary['complete_bgcs']}/{summary['total_bgcs']} complete "
          f"({summary['register_status']})")
    if summary["e1_updated"]:
        es = summary["e1_summary"] or {}
        emit(f"  workbook E1:       updated "
              f"({es.get('bgcs_complete', '?')} complete / {es.get('bgcs_written', '?')} rows)")
    else:
        emit("  workbook E1:       not updated (no --master given)")
    if summary.get("skipped_identity_mismatch"):
        return 5
    return 3 if summary.get("skipped_structure_invalid") else 0

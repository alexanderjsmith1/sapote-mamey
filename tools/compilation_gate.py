#!/usr/bin/env python3
"""
compilation_gate.py — gate a strain compendium markdown/PDF before it can be called
a "compendium" deliverable (PDF_COMPILATION_GATE_20260624).

A PDF for a full actinomycete genome must carry the full deliverable contract, a Mode B
card for every scorable BGC, enough depth to clear a genome-size-scaled page floor, and
must not have padded its way there. This gate runs the checks; the renderer
(tools/md_to_pdf.sh) is unchanged and runs only after G1/G2/G4/G5 pass.

GATES
  G1  Deliverable presence  — all 13 FULL_RUN_PROFILE §A items present (or SKIPPED/N/A
                              with a reason). Reuses check_deliverable_suite.check().
  G2  Mode B coverage       — a §1–§30 contract-valid card for EVERY scorable BGC
                              (modeb_structure_gate.lint_card, ERROR-severity findings
                              fail). Denominator is the full scorable count, never the
                              carded count. Cards on the legacy §1–§20 scaffold do not
                              count as carded (v9.7.150e+).
  G3  Page-count floor      — rendered PDF meets a minimum page count scaled to BGC count.
                              (post-render; needs the actual PDF via pdfinfo.)
  G4  Per-card depth        — each Mode B card clears mode_b_quality_gate.evaluate_card().
  G5  Anti-padding          — page count comes from analysis, not whitespace/repetition.

A failing gate does NOT delete the PDF — it relabels it _PARTIAL_ and records the
shortfall in a receipt JSON. The _COMPENDIUM_ filename token is reserved for PASS.

USAGE
  # pre-render (G1/G2/G4/G5) on the source markdown:
  python tools/compilation_gate.py --md AS-XXX_COMPENDIUM_v1.md --manifest DELIVERABLE_MANIFEST_AS-XXX.md \
        --scorable-bgcs 48 [--mode gold] [--json] [--receipt out.json]

  # post-render (adds G3) once the PDF exists:
  python tools/compilation_gate.py --md ... --manifest ... --scorable-bgcs 48 --pdf AS-XXX_COMPENDIUM_v1.pdf

Exit 0 = PASS (may be named _COMPENDIUM_), 1 = FAIL (must be _PARTIAL_).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# ── tree-local imports (gate lives in tools/, engine in mamey/) ────────────────
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
from _wbio import atomic_write_text

try:
    from mamey.mode_b_quality_gate import evaluate_card  # G4
except Exception:  # pragma: no cover - import guard
    evaluate_card = None

try:
    import check_deliverable_suite as cds  # G1 (reuse the existing contract parser)
except Exception:  # pragma: no cover - import guard
    cds = None


# ── G3 page-count floor, scaled to genome size ─────────────────────────────────
# Lower bound, NOT a target. A thin PDF below the floor signals missing Mode B depth or
# deliverables — never an instruction to pad (see G5).
def page_floor(scorable_bgcs: int) -> int:
    if scorable_bgcs < 15:
        return 30      # small genome or heavy fragmentation
    if scorable_bgcs <= 35:
        return 60      # typical small Streptomyces / Micromonospora
    if scorable_bgcs <= 70:
        return 100     # full mid-size actinomycete genome
    if scorable_bgcs <= 110:
        return 140     # large genome
    return 180         # very large / highly fragmented


# A Mode B card heading. Cards are written as "### BGCxxx ..." or "## BGCxxx ...".
# A Mode B card heading. The v9.7.150 W9 template emitter writes the card
# title as `# Mode B — BGCxxx (NODE_y) — AS-XXX` (single `#`). Pre-W9
# cards used `## BGCxxx ...` or `### BGCxxx ...` style headings. Both
# forms are accepted; the regex below also matches the persisted W9
# header comment `<!-- MODE B: BGCxxx ... -->`. Counting de-dupes by BGC
# ID downstream in `_carded_bgc_ids`. (bunny-hop fix, v9.7.151)
_CARD_HEAD = re.compile(
    r'^#{1,4}\s+.*\bBGC\d{2,4}\b'                      # ## or ### heading
    r'|<!--\s*MODE\s*B:\s*BGC\d{2,4}\b'                # W9 persisted header
    r'|^#\s*Mode\s*B\s*[\u2014\-]\s*BGC\d{2,4}\b',     # W9 template title
    re.M | re.I,
)
# §-section headers inside a card (e.g. "§1", "§ 1", "Section 1"). Used for G5 density.
# §-section headers inside a card. Current contract is §1–§30 (W9,
# v9.7.150). Pre-W9 cards used §1–§8 (then §1–§10). The regex captures
# §1 through §99 defensively so it never silently drops a real section.
# (bunny-hop fix, v9.7.151)
_SECTION = re.compile(r'§\s*(\d{1,2})(?!\d)')
# Gene/locus table rows (a markdown table row mentioning a locus tag like ctgN_MM).
_GENE_ROW = re.compile(r'^\|.*\bctg\d+_\d+\b', re.M)


def _carded_bgc_ids(md: str) -> set[str]:
    """BGC IDs that have a Mode B card heading in the markdown."""
    ids = set()
    for m in _CARD_HEAD.finditer(md):
        mm = re.search(r'\bBGC(\d{2,4})\b', m.group(0))
        if mm:
            ids.add(f"BGC{mm.group(1)}")
    return ids


def _split_cards(md: str) -> list[tuple[str, str]]:
    """Split markdown into (bgc_id, card_text) chunks at each card heading."""
    heads = list(_CARD_HEAD.finditer(md))
    out = []
    for i, h in enumerate(heads):
        start = h.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(md)
        mm = re.search(r'\bBGC(\d{2,4})\b', h.group(0))
        if mm:
            out.append((f"BGC{mm.group(1)}", md[start:end]))
    return out


# ── G1: deliverable presence ───────────────────────────────────────────────────
def g1_deliverables(manifest_path: str | None, mode: str) -> tuple[bool, list[str]]:
    if not manifest_path:
        return False, ["G1: no --manifest given; cannot verify the 13-item contract"]
    if cds is None:
        return False, ["G1: check_deliverable_suite not importable"]
    text = Path(manifest_path).read_text(encoding="utf-8")
    findings, stats = cds.check(text, mode)
    msgs = [f"G1: {f}" for f in findings]
    return (not findings), msgs


# ── G2: Mode B coverage (every scorable BGC carded) ────────────────────────────
def g2_modeb_coverage(md: str, scorable_bgcs: int) -> tuple[bool, list[str], int]:
    """G2: every scorable BGC has a card, AND each card passes the §1–§30 structure
    gate (v9.7.150e+). A card present-but-legacy-scaffold no longer counts as carded —
    closes the gap where this gate and modeb_structure_gate.py could disagree about
    whether a card is complete (Bunny Hop finding #9/#51, v9.7.150f)."""
    carded = _carded_bgc_ids(md)
    n = len(carded)
    msgs: list[str] = []

    try:
        # Absolute import: this is a standalone tools/ script, not part of the
        # mamey package, so a relative import (`from .modeb_structure_gate`)
        # has no parent package context and silently fails — that was the bug
        # this fix closes (caught during functional verification, v9.7.150f).
        from mamey.modeb_structure_gate import lint_card as _lint_card
        _gate_available = True
        _import_error = None
    except Exception as exc:
        _gate_available = False
        _import_error = exc

    structurally_invalid = []
    if _gate_available:
        for bgc_id, card_text in _split_cards(md):
            try:
                findings = _lint_card(card_text, bgc_context=None)
                n_errors = sum(1 for f in findings if f.get("severity") == "ERROR")
                if n_errors:
                    structurally_invalid.append((bgc_id, n_errors))
            except Exception as exc:
                # v9.7.409 A8 (SF-1/G2): fail CLOSED -- a card whose lint crashed was NOT certified valid.
                structurally_invalid.append((bgc_id, f"lint-crash: {type(exc).__name__}"))
    else:
        # v9.7.374: this branch used to fall through silently -- structural linting
        # simply never ran, and G2 still reported PASS on coverage-count alone with no
        # finding at all (unlike G1/G4, which correctly fail closed and report when
        # their own imports fail). A structurally broken card sailed through G2 as long
        # as the BGC count matched. Fail closed and say so, matching G1/G4.
        msgs.append(
            f"G2: mamey.modeb_structure_gate not importable ({_import_error}) -- "
            f"structural section-contract linting could not run; card structure not certified"
        )

    if n < scorable_bgcs:
        msgs.append(
            f"G2: Mode B coverage {n}/{scorable_bgcs} — every scorable BGC owes a §1–§30 "
            f"contract-valid card (FULL ANALYSIS MODE). {scorable_bgcs - n} uncarded."
        )
    if structurally_invalid:
        bad = ", ".join(f"{b}({e} err)" if isinstance(e, int) else f"{b}({e})" for b, e in structurally_invalid)
        msgs.append(
            f"G2: {len(structurally_invalid)} card(s) present but structurally invalid "
            f"per the §1–§30 contract — likely legacy §1–§20 scaffold: {bad}"
        )

    ok = (n >= scorable_bgcs) and not structurally_invalid and _gate_available
    return ok, msgs, n


# ── G4: per-card depth ─────────────────────────────────────────────────────────
def g4_card_depth(md: str) -> tuple[bool, list[str]]:
    if evaluate_card is None:
        return False, ["G4: mode_b_quality_gate not importable"]
    msgs = []
    for bgc_id, card in _split_cards(md):
        v = evaluate_card(bgc_id, card)
        tier = getattr(v, "tier", None) or getattr(v, "depth_tier", "")
        if str(tier).upper() == "STUB":
            msgs.append(f"G4: {bgc_id} card is STUB depth (fails §1–§30 / char floor)")
    return (not msgs), msgs


# ── G5: anti-padding ───────────────────────────────────────────────────────────
# Page count must come from analysis. Heuristic: section-headers-per-card and
# gene-table-rows-per-card must clear a minimum so a high page count can't be hit with
# whitespace or repeated boilerplate.
_MIN_SECTIONS_PER_CARD = 18     # was 6 (pre-W9 §1–§8 contract); W9 contract requires
                                 # §1–§20 always + §28 + §30 always = 22 mandatory
                                 # sections, 18 tolerates conditional §21–§27/§29 omission
                                 # (bunny-hop fix, v9.7.151)
_MIN_GENE_ROWS_TOTAL = 8        # a real compendium carries gene tables, not just prose


def g5_anti_padding(md: str, n_cards: int) -> tuple[bool, list[str]]:
    msgs = []
    if n_cards <= 0:
        return True, []  # G2 already failed; nothing to check
    n_sections = len(_SECTION.findall(md))
    n_gene_rows = len(_GENE_ROW.findall(md))
    sect_per_card = n_sections / n_cards
    if sect_per_card < _MIN_SECTIONS_PER_CARD:
        msgs.append(
            f"G5: {sect_per_card:.1f} §-sections per card (< {_MIN_SECTIONS_PER_CARD}) — "
            f"pages may be padded; cards lack §-section depth"
        )
    if n_gene_rows < _MIN_GENE_ROWS_TOTAL:
        msgs.append(
            f"G5: {n_gene_rows} gene-table rows total (< {_MIN_GENE_ROWS_TOTAL}) — "
            f"compendium lacks gene-level tables, likely prose-padded"
        )
    return (not msgs), msgs


# ── G3: page-count floor (post-render) ─────────────────────────────────────────
def _pdf_page_count(pdf_path: str) -> int | None:
    """Page count via pdfinfo; None if unavailable."""
    try:
        out = subprocess.run(
            ["pdfinfo", pdf_path], capture_output=True, text=True, timeout=30
        )
        m = re.search(r'^Pages:\s*(\d+)', out.stdout, re.M)
        if m:
            return int(m.group(1))
    except Exception:
        return None
    return None


def g3_page_floor(pdf_path: str | None, scorable_bgcs: int) -> tuple[bool, list[str], int | None, int]:
    floor = page_floor(scorable_bgcs)
    if not pdf_path:
        return True, [], None, floor  # pre-render: G3 deferred, not failed
    pages = _pdf_page_count(pdf_path)
    if pages is None:
        return False, [f"G3: could not read page count from {pdf_path} (pdfinfo missing?)"], None, floor
    if pages < floor:
        return False, [
            f"G3: {pages} pages < floor {floor} for {scorable_bgcs} BGCs — "
            f"compendium too thin; Mode B depth or deliverables missing"
        ], pages, floor
    return True, [], pages, floor


# ── orchestration ──────────────────────────────────────────────────────────────
def _locator_pre_g2(md: str, triage_csv_path: str | None) -> tuple[bool, list[str]]:
    """Pre-G2 locator-reconciliation check (SM-P0-003 / STEP 5a). WARN mode — non-blocking."""
    if not triage_csv_path:
        return True, []
    try:
        import csv as _csv
        import sys as _sys
        _tools = str(Path(__file__).resolve().parent)
        if _tools not in _sys.path:
            _sys.path.insert(0, _tools)
        from locator_reconciliation import reconcile_batch
    except Exception as exc:
        return True, [f"LOCATOR-WARN: could not import locator_reconciliation: {exc}"]

    triage_path = Path(triage_csv_path)
    if not triage_path.exists():
        return True, [f"LOCATOR-WARN: triage CSV not found: {triage_csv_path}"]

    try:
        import csv as _csv
        with open(triage_path, newline="", encoding="utf-8") as f:
            triage_rows = {row["BGC_ID"]: row for row in _csv.DictReader(f)}
    except Exception as exc:
        return True, [f"LOCATOR-WARN: could not read triage CSV: {exc}"]

    cards = _split_cards(md)
    entries = [{"card_text": ct, "triage_row": triage_rows.get(bid, {})}
               for bid, ct in cards]
    rows = reconcile_batch(entries)
    warn_msgs = [
        f"LOCATOR-WARN [{r['status']}] {r['BGC_ID']}: fields={r['mismatched_fields'] or r['status']}"
        for r in rows if r["exit_code"] != 0
    ]
    return True, warn_msgs  # always True — WARN mode


def run_gate(md_path: str, manifest: str | None, scorable_bgcs: int,
             pdf: str | None, mode: str, triage_csv: str | None = None) -> dict:
    md = Path(md_path).read_text(encoding="utf-8")

    g1_ok, g1_msgs = g1_deliverables(manifest, mode)
    _loc_ok, loc_msgs = _locator_pre_g2(md, triage_csv)
    g2_ok, g2_msgs, n_cards = g2_modeb_coverage(md, scorable_bgcs)
    g4_ok, g4_msgs = g4_card_depth(md)
    g5_ok, g5_msgs = g5_anti_padding(md, n_cards)
    g3_ok, g3_msgs, pages, floor = g3_page_floor(pdf, scorable_bgcs)

    findings = g1_msgs + loc_msgs + g2_msgs + g3_msgs + g4_msgs + g5_msgs
    gate_pass = g1_ok and g2_ok and g3_ok and g4_ok and g5_ok

    return {
        "gate": "PASS" if gate_pass else "FAIL",
        "scorable_bgcs": scorable_bgcs,
        "mode_b_cards": n_cards,
        "page_count": pages,
        "page_floor": floor,
        "post_render": pdf is not None,
        "checks": {"G1": g1_ok, "G2": g2_ok, "G3": g3_ok, "G4": g4_ok, "G5": g5_ok,
                   "LOCATOR": "WARN" if loc_msgs else "OK"},
        "findings": findings,
    }


def main():
    ap = argparse.ArgumentParser(description="Compendium PDF compilation gate (G1–G5).")
    ap.add_argument("--md", required=True, help="source compendium markdown")
    ap.add_argument("--manifest", help="filled DELIVERABLE_MANIFEST_<strain>.md (G1)")
    ap.add_argument("--scorable-bgcs", type=int, required=True,
                    help="full scorable BGC count (the G2 denominator)")
    ap.add_argument("--pdf", help="rendered PDF for the post-render G3 page-floor check")
    ap.add_argument("--mode", default="standard", choices=["smoke", "standard", "gold"])
    ap.add_argument("--receipt", help="write the gate receipt JSON here")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--triage-csv",
                    help="(SM-P0-003) triage board CSV for pre-G2 locator reconciliation (WARN mode)")
    a = ap.parse_args()

    receipt = run_gate(a.md, a.manifest, a.scorable_bgcs, a.pdf, a.mode,
                       triage_csv=getattr(a, "triage_csv", None))
    receipt["filename"] = a.pdf or a.md

    if a.receipt:
        atomic_write_text(a.receipt, json.dumps(receipt, indent=2))

    if a.json:
        emit(json.dumps(receipt, indent=2))
    else:
        emit(f"Compilation gate — {receipt['gate']}", f"  Mode B: {receipt['mode_b_cards']}/{receipt['scorable_bgcs']} cards", sep="\n")
        if receipt["page_count"] is not None:
            emit(f"  Pages: {receipt['page_count']} (floor {receipt['page_floor']})")
        else:
            emit(f"  Page floor: {receipt['page_floor']} (pre-render; G3 deferred)")
        for k, ok in receipt["checks"].items():
            emit(f"  {k}: {'✓' if ok else '✗'}")
        for f in receipt["findings"]:
            emit(f"  ✗ {f}")
        if receipt["gate"] == "PASS":
            emit("  ✓ may be named _COMPENDIUM_")
        else:
            emit("  ✗ must be labelled _PARTIAL_ — not a compendium")

    sys.exit(0 if receipt["gate"] == "PASS" else 1)


if __name__ == "__main__":
    main()

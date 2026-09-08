"""modeb_round.py — v9.7.194 contractual Mode B round orchestrator.

WHAT THIS IS. The `emit-modeb-template → author → verify` sequence, made contractual and stateful.
A CLI cannot author prose (that is the Sapote/LLM step), so this orchestrator owns the two
DETERMINISTIC halves and tracks the state in between:

  1. EMIT   — emit N triage skeletons (top-N by Corrected_rank) via the existing emit_batch.
  2. VERIFY — for each emitted skeleton, run the structure gate to confirm it is a VALID SCAFFOLD
              (all §1–§48 headings present). NOTE: a freshly emitted skeleton is deliberately
              unauthored, so it is NOT expected to pass the DEPTH gate — depth is checked later by
              `verify-modeb` once a card is authored. Here we only assert the scaffold is sound.
  3. WORKLIST — write modeb_round_worklist.json: the N BGCs, evidence pointers, gate status, and a
              per-BGC `authoring_state`. This is the contract surface the Sapote layer reads.

TERMINOLOGY (important — avoids a collision). The engine's `THIN_CARD` is a depth-gate FAILURE
(a structurally-complete card with too little authored prose). The user-facing "thin card" in the
round contract is a TRIAGE card: an emitted skeleton + evidence, deliberately unauthored, awaiting
a fill request. To avoid overloading `thin`, the states are named TRIAGE_EMITTED / AUTHORING /
AUTHORED_VERIFIED / VERIFY_FAILED. A TRIAGE card is not a failed card — it is a not-yet-authored one.

THE CONTRACT (what the Sapote layer honors around this):
  - Minimum before contacting the user: >= 1 BGC fully authored + verify-modeb PASS (+ its guide).
  - Preferred: N (default 10) TRIAGE cards emitted + scaffold-verified, THEN surface to the user,
    who chooses: fill all N / fill a subset / emit the next N.
This module produces the worklist and states; the Sapote layer does the authoring and advances
states by re-running verify on the authored file.
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
from pathlib import Path
from typing import Any, Optional

from .modeb_evidence_state import EVIDENCE_STATES

# authoring states (the contract surface)
S_TRIAGE = "TRIAGE_EMITTED"        # skeleton emitted + scaffold-verified, awaiting fill request
S_AUTHORING = "AUTHORING"           # Sapote is filling it now
S_AUTHORED = "AUTHORED_VERIFIED"    # authored + verify-modeb PASS (receipts recorded)
S_SCAFFOLD_BAD = "SCAFFOLD_INVALID"  # the emitted skeleton failed the structure gate (a real bug)
S_VERIFY_FAILED = "VERIFY_FAILED"   # authored but verify-modeb failed (thin/structural)


def _scaffold_ok(card_md: str) -> tuple[bool, list[str]]:
    """Assert an emitted skeleton is a valid §1–§48 SCAFFOLD (headings present). Depth is NOT
    checked here — an unauthored skeleton is expected to be thin. Returns (ok, structural_errors)."""
    from .modeb_structure_gate import lint_card
    # structure only: check_depth=False so THIN findings do not fire on the unauthored skeleton
    findings = lint_card(card_md, check_depth=False, strict_depth=False)
    # v9.7.371 fix: this filter named codes lint_card() never emits ("MISSING_SECTION",
    # "SECTION_OUT_OF_ORDER") -- the real codes are MISSING_REQUIRED_SECTION and OUT_OF_ORDER /
    # SECTION_ORDER (confirmed by grepping modeb_structure_gate.py). The two most important
    # structural checks -- a missing required section, or sections out of numeric order -- could
    # never appear in structural_errs, so a genuinely invalid scaffold silently passed _scaffold_ok
    # as if sound.
    structural_errs = [f for f in findings
                       if f.get("severity") == "ERROR"
                       and f.get("code") in ("NO_HEADINGS_DETECTED", "EMPTY_CARD",
                                             "MISSING_REQUIRED_SECTION", "OUT_OF_ORDER",
                                             "SECTION_ORDER", "TITLE_MISMATCH")]
    return (len(structural_errs) == 0, [f"{f.get('code')}: {f.get('message')}" for f in structural_errs])


def run_round(package_dir: str | Path, top_n: int = 10,
              scope: str = "top", precompute_dir: str | Path | None = None) -> dict[str, Any]:
    """Emit + scaffold-verify a round of N triage Mode B cards. Returns the worklist dict and
    writes it to <pkg>/modeb_round_worklist.json. Does NOT author (that is the Sapote step)."""
    pkg = Path(package_dir).resolve()
    from . import modeb_template_emitter as _emit

    res = _emit.emit_batch(pkg, scope=scope, top_n=top_n, precompute_dir=precompute_dir)
    if res.get("skipped_reason"):
        return {"ok": False, "error": res["skipped_reason"], "package": str(pkg)}

    out_dir = Path(res["out"])
    entries = []
    for bgc_id in res["emitted"]:
        # emit_batch writes <BGC>_template.md
        tmpl = out_dir / f"{bgc_id}_template.md"
        state = S_TRIAGE
        scaffold_errs: list[str] = []
        if tmpl.exists():
            ok, scaffold_errs = _scaffold_ok(tmpl.read_text(encoding="utf-8", errors="replace"))
            if not ok:
                state = S_SCAFFOLD_BAD
        else:
            state = S_SCAFFOLD_BAD
            scaffold_errs = [f"template file not found: {tmpl.name}"]
        entries.append({
            "bgc_id": bgc_id,
            "template": str(tmpl),
            "authoring_state": state,
            "scaffold_errors": scaffold_errs,
            "authored_card": None,      # set by the Sapote layer when it authors
            "verify_receipts": None,    # set on verify-modeb PASS (error count, char count)
            "escalation_evidence_state": "UNBOUND",
            "escalation_evidence_note": (
                "Template emission does not admit external escalation evidence; "
                "use the Mode B evidence transition contract."
            ),
        })

    worklist = {
        "schema_version": "modeb-round-worklist-1.0",
        "package": str(pkg),
        "strain": pkg.parent.name,
        "scope": scope,
        "requested_n": top_n,
        "emitted_n": len(res["emitted"]),
        "scaffold_invalid_n": sum(1 for e in entries if e["authoring_state"] == S_SCAFFOLD_BAD),
        "templates_dir": str(out_dir),
        "entries": entries,
        "contract": {
            "minimum_before_contact": "at least 1 BGC AUTHORED_VERIFIED (+ its guide)",
            "preferred_before_contact": f"{top_n} TRIAGE_EMITTED cards, then user chooses fill scope",
            "user_choices": ["fill all", "fill subset [bgc_ids]", "emit next round"],
            "evidence_states": sorted(EVIDENCE_STATES),
        },
    }
    worklist_path = pkg / "modeb_round_worklist.json"
    tmp_path = Path(str(worklist_path) + ".tmp")
    tmp_path.write_text(json.dumps(worklist, indent=2), encoding="utf-8")
    tmp_path.replace(worklist_path)  # os.replace is atomic on the same filesystem
    return {"ok": True, **worklist}


def modeb_round_command(args) -> int:
    pkg = Path(args.package).resolve()
    if not (pkg / "manifest.json").exists():
        emit(f"ERROR: no sealed package at {pkg} (manifest.json missing)", file=__import__("sys").stderr)
        return 1
    r = run_round(pkg, top_n=getattr(args, "top_n", 10), scope=getattr(args, "scope", "top"),
                  precompute_dir=getattr(args, "from_precompute", None))
    if not r.get("ok"):
        emit(f"[modeb-round] ERROR: {r.get('error')}", file=__import__("sys").stderr)
        return 1
    emit(f"[modeb-round] {r['strain']}: emitted {r['emitted_n']} triage card(s) "
          f"(scope={r['scope']}, requested {r['requested_n']})")
    if r["scaffold_invalid_n"]:
        emit(f"[modeb-round] WARNING: {r['scaffold_invalid_n']} emitted skeleton(s) FAILED the "
              f"structure gate — these are real scaffold bugs, not just unauthored:")
        for e in r["entries"]:
            if e["authoring_state"] == S_SCAFFOLD_BAD:
                emit(f"    {e['bgc_id']}: {'; '.join(e['scaffold_errors'][:2])}")
    emit(f"[modeb-round] worklist -> {pkg / 'modeb_round_worklist.json'}", f"[modeb-round] contract: minimum {r['contract']['minimum_before_contact']}; preferred {r['contract']['preferred_before_contact']}", f'[modeb-round] NOTE: authoring is the Sapote/LLM step — this command emits + scaffold-verifies only. Author each card, then `mamey verify-modeb <file>` to advance its state to {S_AUTHORED}.', sep="\n")
    return 0

"""deliverable_queue.py — resumable, autonomous strain-deliverable queue (.345).

Runs each strain through the gate-clear DETERMINISTIC pipeline and records a status ledger. The
JUDGMENT layer (the 4 Sapote narratives + §4 prose) is deliberately NOT auto-written — it is flagged
PENDING_JUDGMENT per strain, because a claim-safe narrative is a judgment task, not a template fill.

Per strain: (1) BLASTp gate — auto-ingest available channels, then verify clear (or record BLOCKED);
(2) emit Mode B cards (all subsections); (3) lead-pages, af-dossier, reference-dark, good-guesses;
(4) compile-report (deterministic sections + auto-filled blastp_evidence/fermentation). Idempotent:
a strain marked DONE in the ledger is skipped on re-run.

CLAIM CEILING: deterministic capacity/evidence layers only; narratives await judgment; class-level.
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
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import blastp_gate as _g
from .blastp_ingest import install_channel_top10


def _run(mod_args: list[str], env=None) -> tuple[int, str]:
    """Invoke `python -m mamey <args>` in-process-safe via subprocess; returns (rc, tail)."""
    cmd = [sys.executable, "-m", "mamey", *mod_args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env=env)
        tail = (p.stdout or p.stderr or "").strip().splitlines()[-1:] or [""]
        return p.returncode, tail[0]
    except Exception as e:  # noqa: BLE001
        return 99, f"{type(e).__name__}: {e}"


def _auto_ingest(package: str, strain: str) -> dict:
    roots = _g.discover_trove_roots(package)
    got = {}
    for ch in ("nr", "clustered_nr", "swissprot", "ebi"):
        for r in roots.get(ch, []):
            try:
                res = install_channel_top10(package, r, ch, strain)
                if res.get("bgcs"):
                    got[ch] = res["bgcs"]
            except Exception:  # noqa: BLE001
                pass
    return got


def process_strain(strain: str, runs_dir: str, out_root: str, activity_csv: str | None = None) -> dict:
    pkg = os.path.join(runs_dir, strain, "package")
    rec = {"strain": strain,
           "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if not os.path.isdir(pkg):
        rec["status"] = "NO_PACKAGE"
        return rec
    out = os.path.join(out_root, strain, "sapote")
    os.makedirs(out, exist_ok=True)
    # 1. gate: auto-ingest, then verify
    rec["ingested"] = _auto_ingest(pkg, strain)
    gate = _g.gate(pkg, strain)
    if gate["blocked"]:
        rec["status"] = "BLASTP_BLOCKED"
        rec["missing"] = len(gate["missing"])
        return rec
    rec["gate"] = "CLEAR"
    env = dict(os.environ)
    # 2. deterministic deliverables
    steps = {
        "cards": ["emit-modeb-template", "--package", pkg, "--batch", "--scope", "all"],
        "lead_pages": ["lead-pages", pkg, "--out", os.path.join(out, "lead_pages")],
        "reference_dark": ["reference-dark", pkg, "--out", os.path.join(out, "reference_dark")],
        "good_guesses": ["good-guesses", pkg, "--out", os.path.join(out, "good_guesses")],
    }
    if activity_csv:
        steps["af_dossier"] = ["af-dossier", pkg, "--activity-table", activity_csv, "--out", os.path.join(out, "af_dossier")]
    else:
        steps["af_dossier"] = ["af-dossier", pkg, "--out", os.path.join(out, "af_dossier")]
    steps["report"] = ["compile-report", pkg, "--out", os.path.join(out, f"{strain}_compiled_report.md")]
    results = {}
    for name, argv in steps.items():
        rc, tail = _run(argv, env=env)
        results[name] = "ok" if rc == 0 else f"rc{rc}:{tail[:60]}"
    # copy emitted templates into the deliverable folder
    tdir = os.path.join(pkg, "mode_b_templates")
    if os.path.isdir(tdir):
        dst = os.path.join(out, "mode_b_templates"); os.makedirs(dst, exist_ok=True)
        n = 0
        for f in os.listdir(tdir):
            if f.endswith(".md"):
                Path(dst, f).write_text(Path(tdir, f).read_text(encoding="utf-8"), encoding="utf-8"); n += 1
        results["cards_copied"] = n
    rec["steps"] = results
    rec["status"] = "DETERMINISTIC_DONE"
    rec["narratives"] = "PENDING_JUDGMENT"  # the Sapote judgment layer is authored separately
    return rec


def run_queue(strains: list[str], runs_dir: str, out_root: str, activity_csv: str | None = None,
              ledger_path: str | None = None, resume: bool = True) -> dict:
    ledger_path = ledger_path or os.path.join(out_root, "DELIVERABLE_QUEUE_LEDGER.json")
    os.makedirs(out_root, exist_ok=True)
    ledger = {}
    if resume and os.path.exists(ledger_path):
        try:
            ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            ledger = {}
    done_states = {"DETERMINISTIC_DONE"}
    for s in strains:
        if resume and ledger.get(s, {}).get("status") in done_states:
            emit(f"[queue] {s}: skip (already {ledger[s]['status']})", flush=True)
            continue
        emit(f"[queue] {s}: processing…", flush=True)
        rec = process_strain(s, runs_dir, out_root, activity_csv)
        ledger[s] = rec
        # v9.7.374 fix: this file is the ONLY resumability bookkeeping this queue has (see module
        # docstring: "a strain marked DONE in the ledger is skipped on re-run"). A direct write_text()
        # here is not atomic; a crash/kill mid-write leaves a truncated ledger.json that fails
        # json.loads() on the next resume, and run_queue()'s own except-JSONDecodeError handler resets
        # ledger = {} -- discarding EVERY previously-DETERMINISTIC_DONE strain's bookkeeping, not just
        # the one being written when the crash happened. Write to a tmp sibling then atomically replace.
        _ledger_tmp = Path(str(ledger_path) + ".tmp")
        _ledger_tmp.write_text(json.dumps(ledger, indent=1), encoding="utf-8")
        _ledger_tmp.replace(ledger_path)
        emit(f"[queue] {s}: {rec['status']}"
              + (f" (missing {rec.get('missing')})" if rec['status'] == 'BLASTP_BLOCKED' else ""), flush=True)
    summary = {"total": len(strains),
               "deterministic_done": sum(1 for r in ledger.values() if r.get("status") == "DETERMINISTIC_DONE"),
               "blocked": sum(1 for r in ledger.values() if r.get("status") == "BLASTP_BLOCKED"),
               "ledger": ledger_path}
    emit(f"[queue] DONE: {summary['deterministic_done']}/{summary['total']} deterministic-complete; "
          f"{summary['blocked']} BLASTp-blocked. Ledger -> {ledger_path}", flush=True)
    return summary


def deliverable_queue_command(args) -> int:
    strains = args.strains if getattr(args, "strains", None) else []
    run_queue(strains, args.runs_dir, args.out_root,
              activity_csv=getattr(args, "activity_table", None),
              ledger_path=getattr(args, "ledger", None),
              resume=not getattr(args, "no_resume", False))
    return 0

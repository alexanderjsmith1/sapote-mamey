#!/usr/bin/env python3
"""
sapote_workflow.py — the mandatory Sapote workflow driver / gate.

WHY THIS EXISTS
---------------
Mamey (Tier 1) has a *set format*: `mamey run` executes a fixed phase order in code
and `mamey validate` is a hard seal gate. The Sapote judgment layer (Tier 2/3) has the
same steps written down — FULL_RUN_PROFILE.md Section A's 13-item delivery order,
the execution slice, the deliverable contract — plus a fleet of individually-callable
gates (`mamey validate`, `verify-modeb`, `verify-guide`, `compile-report --strict`,
tools/check_deliverable_suite.py, tools/sapote_judgment_receipt.py,
tools/session_checklist.py). What it did NOT have is a single ordered *driver* that
sequences those gates, enforces the order (a downstream step is BLOCKED until its
mandatory predecessor PASSES), reads the REAL package artifacts, and fails closed.

This tool is that driver. It is the Sapote analogue of `mamey validate`: point it at a
sealed Mamey package (+ optionally a deliverables dir) and it reports, per canonical
step, PASS / PENDING / BLOCKED / N/A with receipts (file names, row/section counts,
gate exit), writes a workflow ledger (md + json), and — under --strict — exits non-zero
if any MANDATORY step is not PASS.

It does NOT re-implement any gate. Every check either inspects a real artifact the
engine already wrote, or shells out to the real gate command. The canonical step list is
in docs/SAPOTE_WORKFLOW_CONTRACT.md; this file is its executable form.

USAGE
-----
  python tools/sapote_workflow.py --package runs_<date>/<ID>/package
  python tools/sapote_workflow.py --package <pkg> --deliverables <dir> --strict --json
  python tools/sapote_workflow.py --package <pkg> --ledger-out WORKFLOW_LEDGER.md
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
import argparse, glob, json, os, re, subprocess, sys
from datetime import datetime, timezone

PASS, PENDING, BLOCKED, NA = "PASS", "PENDING", "BLOCKED", "N/A"
SYM = {PASS: "\u2705", PENDING: "\u23f3", BLOCKED: "\u26d4", NA: "\u2796"}


def _first(pkg, pattern):
    hits = sorted(glob.glob(os.path.join(pkg, pattern)))
    return hits[0] if hits else None


def _count_lines(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return max(0, sum(1 for _ in fh) - 1)  # minus header
    except Exception:
        return 0


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _gate_verdict_ok(gate):
    """True only when gate_validation.json's top-level verdict is a PASS-family value.

    v9.7.410: the seal step must read the RECORDED VERDICT, not merely confirm the file
    parses. The PASS-family vocabulary matches the rest of the engine (seal_package.py:
    ``status.startswith("PASS") or status == "MAMEY_COMPLETE"``; discover.py /
    package_continuity_widgets.py accept PASS / PASS_WITH_ISSUES / MAMEY_COMPLETE). A
    boolean ``ok: true`` is honored too. Anything else (FAIL/WARN/absent/blank) -> False.
    """
    if not isinstance(gate, dict):
        return False
    v = gate.get("ok", gate.get("status"))
    if isinstance(v, bool):
        return v
    s = str(v).strip().upper()
    return s.startswith("PASS") or s == "MAMEY_COMPLETE"


# v9.7.412 (hostile audit of .411, W4): content-commitment floors for a Mode-B card FILE to count as
# authored — the same floors the gold-completeness block in mamey/validate.py applies (>= 3 recognised
# section headings AND >= 200 non-whitespace chars). The .410 check (>= 1 prose line) still credited a
# one-line stub. Under --strict, W4 additionally invokes the REAL `verify-modeb` on each disk card and
# credits only rc == 0; a verifier that cannot be launched fails CLOSED (never credited).
_MIN_MODEB_SECTIONS = 3
_MIN_MODEB_AUTHORED_CHARS = 200


def _modeb_is_authored(path):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return False
    try:
        try:
            from .modeb_structure_gate import extract_section_titles as _ext
        except ImportError:  # loaded by file path without a parent package (the driver tests do this)
            _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if _root not in sys.path:
                sys.path.insert(0, _root)
            from mamey.modeb_structure_gate import extract_section_titles as _ext
        sections = {n for (n, _t) in _ext(text)}
    except Exception:
        sections = set()  # fail closed: unreadable structure == not authored
    return len(sections) >= _MIN_MODEB_SECTIONS and len("".join(text.split())) >= _MIN_MODEB_AUTHORED_CHARS


def _run_verify_modeb(pkg, card):
    """Exit code of the real `verify-modeb` gate on one card (0 = passes). Launch failure -> 2 (fail closed)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        r = subprocess.run([sys.executable, os.path.join(root, "mamey_run.py"), "verify-modeb", os.path.abspath(card),
                            "--package", os.path.abspath(pkg)], capture_output=True, text=True, timeout=300, cwd=root)
        return r.returncode
    except Exception:
        return 2


def _has_content_line(path):
    """True if the file holds >=1 non-empty, non-heading (``#``) content line.

    v9.7.410: an authored Mode B card must carry real content — a file that exists but
    holds only headings / blank lines is an emitted skeleton, not a completed card.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if s and not s.startswith("#"):
                    return True
    except OSError:
        return False
    return False


def _strain(pkg):
    m = _load_json(os.path.join(pkg, "manifest.json")) or {}
    sid = m.get("strain") or m.get("strain_id")
    if sid:
        return sid
    # fall back to filename prefix
    hit = _first(pkg, "*_4_triage_board.csv")
    if hit:
        return os.path.basename(hit).split("_4_triage_board.csv")[0]
    return os.path.basename(os.path.dirname(pkg.rstrip("/")))


# ---- per-step checkers: each returns (status, receipt_str) --------------------
# They receive (pkg, deliv, ctx). ctx carries derived state (strain id, counts).

def s0_seal(pkg, deliv, ctx):
    man = os.path.join(pkg, "manifest.json")
    if not os.path.exists(man):
        return PENDING, "manifest.json absent — package not sealed"
    # v9.7.410: read the recorded verdict, not merely file presence. Pre-.410
    # `ok = bool(gate) and chk` cleared W0 on ANY parseable gate_validation.json —
    # including an overall=FAIL seal — because it never inspected the verdict. Require a
    # PASS-family top-level verdict; missing / unparseable / non-PASS -> PENDING.
    gate_path = os.path.join(pkg, "gate_validation.json")
    gate = None
    if os.path.exists(gate_path):
        try:
            with open(gate_path, encoding="utf-8") as fh:
                gate = json.load(fh)
        except (json.JSONDecodeError, OSError):
            gate = None
    verdict = gate.get("ok", gate.get("status")) if isinstance(gate, dict) else None
    gate_pass = _gate_verdict_ok(gate)
    chk = os.path.exists(os.path.join(pkg, "checksums_sha256.txt"))
    ok = gate_pass and chk
    parts = [f"manifest.json ({os.path.getsize(man)}B)"]
    if gate is None:
        parts.append("gate_validation.json absent/unparseable")
    else:
        parts.append(f"gate_validation.json verdict={verdict!r} pass={gate_pass}")
    parts.append("checksums_sha256.txt " + ("present" if chk else "MISSING"))
    ctx["n_bgc"] = len((_load_json(man) or {}).get("bgcs", []) or [])
    parts.append(f"bgcs={ctx['n_bgc']}")
    return (PASS if ok else PENDING), "; ".join(parts)


def s1_firstpass(pkg, deliv, ctx):
    tb = _first(pkg, "*_4_triage_board.csv")
    if not tb:
        return PENDING, "triage board (*_4_triage_board.csv) not found"
    rows = _count_lines(tb)
    ss = os.path.exists(os.path.join(pkg, "AS_scan_states.json")) or _first(pkg, "*_3_scan_states.json")
    return PASS, f"{os.path.basename(tb)} ({rows} BGC rows); scan_states={'yes' if ss else 'no'}"


def s2_leads(pkg, deliv, ctx):
    ab = _first(pkg, "*_4c_AB_lead_board.csv")
    af = _first(pkg, "*_4c_AF_lead_board.csv")
    if not (ab and af):
        return PENDING, f"AB={'yes' if ab else 'no'} AF={'yes' if af else 'no'} lead boards"
    return PASS, f"{os.path.basename(ab)} ({_count_lines(ab)}) + {os.path.basename(af)} ({_count_lines(af)})"


def s3_templates(pkg, deliv, ctx):
    d = os.path.join(pkg, "mode_b_templates")
    cards = glob.glob(os.path.join(d, "*BGC*.md")) if os.path.isdir(d) else []
    ctx["n_templates"] = len(cards)
    if not cards:
        return PENDING, "no mode_b_templates/ — run `mamey emit-modeb-template --batch`"
    return PASS, f"mode_b_templates/ : {len(cards)} §1–§48 skeletons emitted"


def s4_modeb(pkg, deliv, ctx):
    reg = _first(pkg, "*_judgment_register.json") or os.path.join(pkg, "judgment_register.json")
    data = _load_json(reg) if reg else None
    complete = []
    if isinstance(data, dict):
        # v9.7.371 fix: the real judgment_store.py::init_register() schema keys the per-BGC
        # entries under "bgcs" -- neither "register" nor "cards" ever exists, so this fell
        # through to `data` itself (the WHOLE top-level register dict), then iterated its
        # top-level keys as if each were a bgc_id. Concretely: when judgment_status=="COMPLETE"
        # the literal string "judgment_status" got appended as a fake completed BGC (count
        # always 1 regardless of real progress); when judgment_status is IN_PROGRESS/PENDING,
        # complete stayed permanently empty even with real COMPLETE bgcs in the register. Since
        # W4 gates every downstream mandatory step, this could either falsely block the whole
        # Sapote workflow driver or falsely clear the gate on a single fake entry.
        entries = data.get("bgcs") or data.get("register") or data.get("cards") or {}
        if isinstance(entries, dict):
            for bgc, rec in entries.items():
                st = (rec or {}).get("status") if isinstance(rec, dict) else rec
                if str(st).upper() == "COMPLETE":
                    complete.append(bgc)
        elif isinstance(entries, list):
            for rec in entries:
                if not isinstance(rec, dict):
                    return PENDING, "malformed judgment register entry"
                if str(rec.get("status", "")).upper() == "COMPLETE":
                    complete.append(rec.get("bgc_id", "?"))
    ctx["n_cards"] = len(complete)
    # also look for authored card files on disk (judgment dir)
    # v9.7.410: crediting mere existence let an emitted skeleton (headings/blank only)
    # count as an authored card. Dedupe files matched by both globs (e.g.
    # "mode_b_BGC001.md"), then require each to hold >=1 substantive content line.
    candidates = sorted(set(
        glob.glob(os.path.join(pkg, "judgment", "*mode_b*.md")) +
        glob.glob(os.path.join(pkg, "judgment", "*BGC*.md"))
    ))
    # v9.7.412: content-commitment floors (was: >= 1 prose line, which credited a one-line stub)
    disk = [m for m in candidates if _has_content_line(m) and _modeb_is_authored(m)]
    stubs = len(candidates) - len(disk)
    if not complete and not disk:
        extra = f"; {stubs} card file(s) below the content floors" if stubs else ""
        return PENDING, f"0 Mode B cards COMPLETE in judgment register (author → verify-modeb → ingest-receipts){extra}"
    if ctx.get("strict") and not disk:
        return PENDING, "strict W4 requires current authored card files; register status alone is insufficient"
    if ctx.get("strict") and disk:
        # v9.7.412: under --strict, run the real verifier; credit only rc == 0 (launch failure = not credited)
        failed = [os.path.basename(m) for m in disk if _run_verify_modeb(pkg, m) != 0]
        if failed:
            return PENDING, f"{len(failed)}/{len(disk)} authored card(s) fail verify-modeb: {', '.join(failed[:5])}"
        return PASS, f"{len(complete)} card(s) COMPLETE in register; {len(disk)} authored .md on disk, all pass verify-modeb"
    note = f"; {stubs} stub file(s) ignored" if stubs else ""
    return PASS, f"{len(complete)} card(s) COMPLETE in register; {len(disk)} authored .md on disk (confirm each with verify-modeb){note}"


def s5_guide(pkg, deliv, ctx):
    # conditional (Module 19) — search deliverables + package for authored guides
    roots = [r for r in (pkg, deliv) if r]
    guides = []
    for r in roots:
        guides += glob.glob(os.path.join(r, "*_Guide.md")) + glob.glob(os.path.join(r, "**", "*_Guide.md"), recursive=True)
    guides = sorted(set(guides))
    if not guides:
        return NA, "no *_Guide.md authored (conditional; run `mamey guide` then `verify-guide`)"
    # residual LAY slots => not authored
    unauthored = [g for g in guides if "<!-- LAY:" in open(g, encoding="utf-8", errors="replace").read()]
    if unauthored:
        return PENDING, f"{len(guides)} guide(s), {len(unauthored)} still hold <!-- LAY: --> slots (verify-guide will fail)"
    return PASS, f"{len(guides)} guide(s) authored, no residual LAY slots"


def s6_narrative(pkg, deliv, ctx):
    # Lay guide / ecology synthesis / ferm card — §A items 8–11
    roots = [r for r in (deliv, pkg) if r]
    want = {"layperson": ["*ayperson*", "*Lay_Guide*", "*lay_guide*"],
            "ecology": ["*cology*", "*Ecolog*"],
            "fermentation": ["*erment*", "*Ferm*"]}
    found = {}
    for key, pats in want.items():
        hit = None
        for r in roots:
            for p in pats:
                g = glob.glob(os.path.join(r, p)) or glob.glob(os.path.join(r, "**", p), recursive=True)
                if g:
                    hit = os.path.basename(g[0]); break
            if hit:
                break
        found[key] = hit
    have = [k for k, v in found.items() if v]
    if not have:
        return PENDING, "no narrative deliverables found (layperson guide / ecology synthesis / ferm card)"
    if len(have) < 3:
        return PENDING, "partial: have " + ", ".join(have) + "; missing " + ", ".join(k for k in want if not found[k])
    return PASS, "; ".join(f"{k}={found[k]}" for k in want)


def s7_compile(pkg, deliv, ctx):
    rep = _first(pkg, "*_compiled_report.md")
    if not rep:
        rep = _first(deliv, "*_compiled_report.md") if deliv else None
    if not rep:
        return PENDING, "no *_compiled_report.md (run `mamey compile-report --strict`)"
    txt = open(rep, encoding="utf-8", errors="replace").read()
    # v9.7.410: also count the real placeholder marker compile_report.py emits —
    # `<!-- SAPOTE:<key> -->` — which is exactly what its own open_slots() detects. The
    # closing tag is `<!-- /SAPOTE:...`, so this substring matches only OPEN slots.
    open_slots = (txt.count("<!-- OPEN")
                  + txt.count("<!-- SAPOTE:")
                  + len(re.findall(r"\bTODO\b|\bFILL[- ]IN\b", txt)))
    chars = len(txt)
    status = PASS if open_slots == 0 else PENDING
    return status, f"{os.path.basename(rep)} ({chars} chars, {open_slots} open slot(s))"


def s8_suite(pkg, deliv, ctx):
    # 13-item deliverable contract via check_deliverable_suite.py against a filled manifest
    dm = None
    for r in [deliv, pkg, os.getcwd()]:
        if not r:
            continue
        g = glob.glob(os.path.join(r, "DELIVERABLE_MANIFEST*.md"))
        if g:
            dm = g[0]; break
    if not dm:
        return PENDING, "no DELIVERABLE_MANIFEST_<strain>.md (emit + fill, then check_deliverable_suite.py)"
    # v9.7.410: the real tool is tools/check_deliverable_suite.py (one level above
    # mamey/), never mamey/check_deliverable_suite.py — the old path never existed, so the
    # subprocess raised and the gate silently degraded to PENDING with a spurious reason.
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tool = os.path.join(pkg_root, "tools", "check_deliverable_suite.py")
    man = os.path.join(pkg, "manifest.json")
    try:
        r = subprocess.run([sys.executable, tool, "--manifest", man, "--mode", "gold"],
                           capture_output=True, text=True, timeout=120)
        ok = r.returncode == 0
        tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
        return (PASS if ok else PENDING), f"check_deliverable_suite rc={r.returncode}: {tail[0][:120]}"
    except Exception as e:
        return PENDING, f"suite gate not run: {e}"


def s9_receipt(pkg, deliv, ctx):
    man = _load_json(os.path.join(pkg, "manifest.json")) or {}
    gc = json.dumps(man).find("JUDGMENT_PENDING")
    receipt = _first(pkg, "*judgment_receipt*") or (os.path.join(pkg, "commit_receipt.json") if os.path.exists(os.path.join(pkg, "commit_receipt.json")) else None)
    if gc != -1:
        return PENDING, "manifest still carries JUDGMENT_PENDING (run tools/sapote_judgment_receipt.py to flip gold_completeness)"
    return PASS, f"gold_completeness not JUDGMENT_PENDING; receipt={os.path.basename(receipt) if receipt else 'n/a'}"


def s10_close(pkg, deliv, ctx):
    # behavioral: session close checklist + exactly-8 next paths. Driver notes availability.
    return NA, "session-close is behavioral: run tools/session_checklist.py and emit exactly 8 next-paths"


# id, title, mandatory?, predecessor id, checker, verifying-gate hint
STEPS = [
    ("W0", "Sealed Mamey package (validate)",        True,  None, s0_seal,      "mamey validate <pkg>"),
    ("W1", "First-pass scans + triage board",        True,  "W0", s1_firstpass, "tools/build_first_pass_scans.py"),
    ("W2", "Lead boards / DAPR (AB + AF)",            True,  "W1", s2_leads,     "tools/lead_board.py / apply_dapr_boards.py"),
    ("W3", "Mode B §1–§48 templates emitted",        True,  "W2", s3_templates, "mamey emit-modeb-template --batch"),
    ("W4", "Mode B cards authored + verified",       True,  "W3", s4_modeb,     "mamey verify-modeb ; ingest-receipts"),
    ("W5", "BGC Guide(s) authored + verified",       False, "W3", s5_guide,     "mamey guide ; verify-guide"),
    ("W6", "Narrative set (lay/ecology/ferm)",       True,  "W4", s6_narrative, "DELIVERABLE_CONTRACT A2"),
    ("W7", "Compiled report (readiness gate)",       True,  "W6", s7_compile,   "mamey compile-report --strict"),
    ("W8", "13-item deliverable suite contract",     True,  "W7", s8_suite,     "tools/check_deliverable_suite.py"),
    ("W9", "Judgment receipt (gold_completeness)",   True,  "W8", s9_receipt,   "tools/sapote_judgment_receipt.py"),
    ("W10","Session close + exactly-8 next-paths",   True,  "W9", s10_close,    "tools/session_checklist.py"),
]


def run(pkg, deliv, strict=False):
    ctx = {"strain": _strain(pkg), "strict": bool(strict)}  # v9.7.412: checkers may tighten under --strict
    results = {}
    order = []
    for sid, title, mand, pred, checker, hint in STEPS:
        # ordering enforcement: mandatory step is BLOCKED if a mandatory predecessor is not PASS
        if pred and results.get(pred, {}).get("status") not in (PASS, NA):
            status, receipt = BLOCKED, f"blocked by {pred} (not PASS)"
        else:
            status, receipt = checker(pkg, deliv, ctx)
        results[sid] = {"title": title, "mandatory": mand, "predecessor": pred,
                        "status": status, "receipt": receipt, "gate": hint}
        order.append(sid)
    ctx["mandatory_incomplete"] = [s for s in order
                                   if results[s]["mandatory"] and results[s]["status"] != PASS]
    ctx["passed"] = [s for s in order if results[s]["status"] == PASS]
    return ctx, results, order


def render_md(ctx, results, order):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_pass = len(ctx["passed"])
    n_mand = sum(1 for s in order if results[s]["mandatory"])
    lines = [
        f"# Sapote Workflow Ledger — {ctx['strain']}",
        f"_Generated {now} · driver: tools/sapote_workflow.py · contract: docs/SAPOTE_WORKFLOW_CONTRACT.md_",
        "",
        f"**{n_pass}/{len(order)} steps PASS · {len(ctx['mandatory_incomplete'])}/{n_mand} mandatory steps incomplete**",
        "",
        "| Step | Stage | Req | Status | Receipt |",
        "|---|---|:--:|:--:|---|",
    ]
    for s in order:
        r = results[s]
        req = "M" if r["mandatory"] else "cond"
        lines.append(f"| {s} | {r['title']} | {req} | {SYM[r['status']]} {r['status']} | {r['receipt']} |")
    lines += ["", "## Gate per step (how each is verified)", ""]
    for s in order:
        lines.append(f"- **{s}** {results[s]['title']} → `{results[s]['gate']}`")
    if ctx["mandatory_incomplete"]:
        lines += ["", "## Next mandatory step", ""]
        nxt = ctx["mandatory_incomplete"][0]
        lines.append(f"→ **{nxt}: {results[nxt]['title']}** — {results[nxt]['receipt']}  ")
        lines.append(f"   run: `{results[nxt]['gate']}`")
    else:
        lines += ["", "**All mandatory steps PASS — strain is workflow-complete.**"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Mandatory Sapote workflow driver / gate.")
    ap.add_argument("--package", required=True, help="sealed Mamey package dir")
    ap.add_argument("--deliverables", default=None, help="dir holding authored Sapote deliverables")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any mandatory step is not PASS")
    ap.add_argument("--json", action="store_true", help="emit JSON ledger to stdout")
    ap.add_argument("--ledger-out", default=None, help="write the markdown ledger to this path")
    a = ap.parse_args()

    pkg = a.package
    if not os.path.isdir(pkg):
        emit(f"ERROR: package dir not found: {pkg}", file=sys.stderr)
        return 2

    ctx, results, order = run(pkg, a.deliverables, a.strict)
    md = render_md(ctx, results, order)

    if a.json:
        emit(json.dumps({"strain": ctx["strain"], "steps": results,
                          "mandatory_incomplete": ctx["mandatory_incomplete"]}, indent=2))
    else:
        emit(md)

    out = a.ledger_out or os.path.join(pkg, f"{ctx['strain']}_SAPOTE_WORKFLOW_LEDGER.md")
    try:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(md)
        if not a.json:
            emit(f"[ledger] {out}")
    except Exception as e:
        emit(f"[ledger] could not write {out}: {e}", file=sys.stderr)

    if a.strict and ctx["mandatory_incomplete"]:
        emit(f"STRICT FAIL: {len(ctx['mandatory_incomplete'])} mandatory step(s) incomplete: "
              + ", ".join(ctx["mandatory_incomplete"]), file=sys.stderr)
        return 1
    return 0


def workflow_command(args) -> int:
    """`mamey workflow` adapter. Reuses the same driver the tools/ shim calls — one
    implementation, so the CLI and the script can never disagree."""
    import os as _os
    pkg = args.package
    if not _os.path.isdir(pkg):
        emit(f"ERROR: package dir not found: {pkg}", file=sys.stderr)
        return 2
    ctx, results, order = run(pkg, getattr(args, "deliverables", None), bool(getattr(args, "strict", False)))
    md = render_md(ctx, results, order)
    if getattr(args, "as_json", False):
        emit(json.dumps({"strain": ctx["strain"], "steps": results,
                          "mandatory_incomplete": ctx["mandatory_incomplete"]}, indent=2))
    else:
        emit(md)
    out = getattr(args, "ledger_out", None) or _os.path.join(
        pkg, f"{ctx['strain']}_SAPOTE_WORKFLOW_LEDGER.md")
    try:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(md)
        if not getattr(args, "as_json", False):
            emit(f"[ledger] {out}")
    except OSError as e:
        emit(f"[ledger] could not write {out}: {e}", file=sys.stderr)
    if getattr(args, "strict", False) and ctx["mandatory_incomplete"]:
        emit("STRICT FAIL: mandatory step(s) incomplete: "
              + ", ".join(ctx["mandatory_incomplete"]), file=sys.stderr)
        return 1
    return 0

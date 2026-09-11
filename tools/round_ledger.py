#!/usr/bin/env python3
"""round_ledger.py — verify a Mode B card and append one audit row to the round ledger.

A drop-in for the multi-round authoring loop: instead of calling `verify-modeb` bare,
call this — it runs the same gate, then records the receipt (gate status, warning count,
char count, and the round/provenance context) as a CSV row. The point is a durable,
greppable trail across the 6+ rounds and across chats, built only from data already printed.

    python3 tools/round_ledger.py CARD.md --package PKG --bgc BGC025 \
        --round 1 --node "NODE_275·r001" \
        --blastp pending --precursor pending \
        --ledger runs/AS-XXX/round_ledger.csv

Columns: round, bgc, node_region, gate_status, warnings, chars, blastp_status,
precursor_status, authored_utc, card_path.
Gate status and warning counts come from the structured verify-modeb receipt, checked
against the process exit code. Unverified coverage remains a qualified, non-passing ledger state.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, datetime as dt, re, subprocess, sys, json, tempfile
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path


def run_gate(card: str, package: str, bgc: str):
    """Run mamey verify-modeb and parse (status, warnings). Returns (status, n_warn, raw).

    v9.7.374 (audit lane): invoke the canonical `mamey_run.py` entry point, not
    `python -m mamey`. `-m mamey` resolves the `mamey` package via sys.path, which for a
    `python -m X` invocation is seeded from the CALLER's current working directory — not from
    this script's location. Run this tool from anywhere other than the bundle root (e.g. from
    `tools/`, or from a per-strain `runs/<SID>/` working dir while authoring a card — both
    routine locations for this loop) and `-m mamey` silently falls through to whatever `mamey`
    package is `pip install -e`'d in the active environment, which can be a DIFFERENT, STALE
    sealed-tree cut (verified live: from `tools/` in this v9.7.373/engine-1.9.126 tree, `-m
    mamey` resolved to an editable install of the v9.7.370/engine-1.9.123 tree — three versions
    stale, and missing the current tree's v9.7.373 §1-48 publication-quality roster gate
    entirely). The ledger row would then carry a false receipt: gate_status=OK computed by code
    that cannot even run the gates the current card is supposed to be held to, contradicting this
    tool's own contract ("the row cannot claim a card passed that did not"). `mamey_run.py`
    force-inserts its own directory onto sys.path[0] before importing `mamey`, so resolving it by
    this file's own location guarantees the LOCAL bundle's engine runs regardless of caller cwd
    or whatever else is pip-installed.
    """
    repo_root = Path(__file__).resolve().parent.parent
    runner = repo_root / "mamey_run.py"
    if not runner.is_file():
        return "GATE_ERROR", -1, "local mamey_run.py unavailable"
    try:
        with tempfile.TemporaryDirectory(prefix="round_gate_") as tmp:
            report_path = Path(tmp) / "report.json"
            cmd = [sys.executable, str(runner), "verify-modeb", card, "--package", package,
                   "--bgc", bgc, "--report-json", str(report_path)]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            raw = ((out.stdout or "") + (out.stderr or "")).strip()
            if out.returncode not in (0, 1):
                return "GATE_ERROR", -1, raw
            report = json.loads(report_path.read_text(encoding="utf-8"))
            expected = "PASS" if out.returncode == 0 else "FAIL"
            if (type(report.get("exit_code")) is not int
                    or report["exit_code"] != out.returncode or report.get("status") != expected):
                return "GATE_ERROR", -1, "gate receipt and process verdict disagree\n" + raw
            warnings = report.get("warning_instances")
            if type(warnings) is not int or warnings < 0:
                return "GATE_ERROR", -1, "missing or invalid warning count\n" + raw
            if out.returncode == 1:
                return "FAIL", warnings, raw
            if report.get("coverage_verified") is not True:
                return "COVERAGE_UNVERIFIED", warnings, raw
            return "OK", warnings, raw
    except Exception as exc:
        return "GATE_ERROR", -1, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card")
    ap.add_argument("--package", required=True)
    ap.add_argument("--bgc", required=True)
    ap.add_argument("--round", required=True)
    ap.add_argument("--node", default="", help="node·region assembly locator (record-keeping)")
    ap.add_argument("--blastp", default="pending", choices=["pending", "done", "n/a"])
    ap.add_argument("--precursor", default="n/a", choices=["pending", "done", "n/a"])
    ap.add_argument("--ledger", required=True, help="CSV path (created with header if absent)")
    a = ap.parse_args()

    card = Path(a.card)
    if not card.exists():
        emit(f"card not found: {card}", file=sys.stderr); return 2
    # v9.7.233 (bunny-hop): count CHARACTERS, not bytes. Mode B cards are full of multibyte
    # \u00a7/\u2013 (\u00a71\u2026\u00a730 alone adds ~30 bytes), so st_size overcounts the char metric the
    # gate actually reports. Read as text and len() it.
    try:
        chars = len(card.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        chars = card.stat().st_size  # fallback: byte size if the card is unreadable as utf-8
    status, warns, raw = run_gate(str(card), a.package, a.bgc)

    row = {
        "round": a.round, "bgc": a.bgc, "node_region": a.node,
        "gate_status": status, "warnings": warns, "chars": chars,
        "blastp_status": a.blastp, "precursor_status": a.precursor,
        "authored_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "card_path": str(card),
    }
    led = Path(a.ledger)
    # v97395 fix: `not led.exists()` treats existence as proof of a header. A pre-existing but
    # EMPTY (0-byte) ledger -- a pre-created placeholder, or a prior invocation of this same tool
    # interrupted between opening the file in append mode and writing its row, both realistic for
    # a tool this docstring says is invoked "across the 6+ rounds and across chats" -- produced a
    # data row with no header at all, silently corrupting every downstream csv.DictReader read of
    # this ledger from then on. A file needs a header whenever it doesn't exist OR is empty.
    new = (not led.exists()) or led.stat().st_size == 0
    led.parent.mkdir(parents=True, exist_ok=True)
    with led.open("a", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)

    emit(f"[round_ledger] {a.bgc} r{a.round}: gate={status} warns={warns} chars={chars} "
          f"blastp={a.blastp} precursor={a.precursor} -> {led}")
    # non-zero exit if the gate did not cleanly pass, so the loop can catch it
    return 0 if status == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())

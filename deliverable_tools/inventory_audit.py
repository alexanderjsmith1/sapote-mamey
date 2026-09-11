#!/usr/bin/env python3
"""Inventory Audit (AQUARIUS_01) — make sure nothing important slips through the class-gated bottom tier.

the Developer or User asked for this as a safety net for the Inventory-tier reform: the reform reserves the Inventory
tier for housekeeping classes and moves specialized/antimicrobial-capable BGCs to the new 'Low' tier.
This audit reviews the split on the real cohort and FLAGS the judgment calls a human should eyeball so
nothing genuinely important is left mislabelled as background:

  WATCH_BROADENED  — the row is kept in Inventory ONLY because of a broadened housekeeping class
                     (fatty_acid / pigment / signaling / glycolipid), not one of the Developer or User's core five.
                     A pigment/fatty-acid call can occasionally sit on a real specialized cluster.
  WATCH_AMBIGUOUS  — the product string carries a token that is nominally "housekeeping-ish" but can
                     be a genuine antibiotic scaffold (2dos=aminoglycoside, glycopeptide, aminocoumarin,
                     oligosaccharide, nucleoside-sugar). These MUST be reviewed, not assumed background.

It imports the engine's OWN allow-list (`mamey.scoring.HOUSEKEEPING_INVENTORY_CLASSES` +
`is_housekeeping_only`) so the audit can never drift from the code that assigns the tier.

Read-only. Emits a Markdown report + a TSV of every flagged row. Stdlib only.

Claim-safety: tiers are auto-floor ROUTING PRIORS, not measured activity; a class token is CAPACITY,
never a product/activity claim; "WATCH" means "a human should look", not "more active". Judgment deferred.

Usage:
  python3 deliverable_tools/inventory_audit.py [--boards-glob GLOB] [--out DIR]
"""
from __future__ import annotations

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, re, sys, pathlib, collections, datetime
import os

# import the engine's own allow-list so the audit and the scorer cannot diverge
_HERE = pathlib.Path(__file__).resolve()
for up in _HERE.parents:
    if (up / "mamey" / "scoring.py").exists():
        sys.path.insert(0, str(up)); break
from mamey.scoring import (HOUSEKEEPING_INVENTORY_CLASSES,
                           CORE_HOUSEKEEPING_INVENTORY_CLASSES,
                           INVENTORY_AMBIGUOUS_REVIEW_TOKENS,
                           is_housekeeping_only, _norm_product_class)  # noqa: E402

STRICT_CORE = set(CORE_HOUSEKEEPING_INVENTORY_CLASSES)
BROADENED_ONLY = HOUSEKEEPING_INVENTORY_CLASSES - STRICT_CORE
# housekeeping-ish tokens that can nonetheless be a real antibiotic scaffold — always review
AMBIGUOUS_TOKENS = set(INVENTORY_AMBIGUOUS_REVIEW_TOKENS)
NEUTRAL = {"", "unresolved", "other"}


class _BGC:
    __slots__ = ("products",)
    def __init__(self, products): self.products = products


def _classes(prod: str) -> set[str]:
    return {_norm_product_class(t) for t in re.split(r"[;,/]", (prod or "").lower())
            if t.strip()} - NEUTRAL


def audit(boards_glob: str, outdir: pathlib.Path):
    boards = sorted(glob.glob(boards_glob))
    remains_inv = collections.Counter()
    to_low = collections.Counter()
    flagged = []
    n_inv = 0
    for b in boards:
        strain = pathlib.Path(b).parts[-3]
        for r in csv.DictReader(open(b)):
            if (r.get("Lead_tier_auto") or "").strip() != "Inventory":
                continue
            n_inv += 1
            prod = r.get("Products") or ""
            classes = _classes(prod)
            hk = is_housekeeping_only(_BGC([prod]))
            if not hk:
                to_low[strain] += 1
                continue
            # stays Inventory — is it a judgment call?
            remains_inv[strain] += 1
            flags = []
            if classes and classes <= BROADENED_ONLY:
                flags.append("WATCH_BROADENED")
            if any(tok in prod.lower() for tok in AMBIGUOUS_TOKENS):
                flags.append("WATCH_AMBIGUOUS")
            if flags:
                flagged.append((strain, r.get("BGC_ID"), prod, r.get("AB_auto"),
                                r.get("AF_auto"), r.get("Novelty_auto"), ";".join(sorted(classes)),
                                ",".join(flags)))
    outdir.mkdir(parents=True, exist_ok=True)
    tsv = outdir / "INVENTORY_AUDIT_flagged.tsv"
    with open(tsv, "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t")
        w.writerow(["strain", "bgc_id", "products", "AB_auto", "AF_auto", "Novelty_auto",
                    "classes", "flags"])
        w.writerows(flagged)
    md = outdir / "INVENTORY_AUDIT.md"
    total_low = sum(to_low.values()); total_inv = sum(remains_inv.values())
    with open(md, "w") as fh:
        fh.write(f"# Inventory Audit — AQUARIUS_01 class-gated bottom tier\n\n")
        fh.write(f"_generated {datetime.date.today()} · boards={len(boards)} · "
                 f"engine allow-list = {len(HOUSEKEEPING_INVENTORY_CLASSES)} classes_\n\n")
        fh.write(f"- current 'Inventory' rows reviewed: **{n_inv}**\n")
        fh.write(f"- would REMAIN Inventory (housekeeping-only): **{total_inv}**\n")
        fh.write(f"- would move to **Low** (specialized): **{total_low}**\n")
        fh.write(f"- **flagged for human review: {len(flagged)}** "
                 f"({sum('WATCH_AMBIGUOUS' in f[-1] for f in flagged)} AMBIGUOUS, "
                 f"{sum('WATCH_BROADENED' in f[-1] for f in flagged)} BROADENED)\n\n")
        fh.write("## Flagged rows (review these — an important cluster must not stay 'Inventory')\n\n")
        fh.write("| strain | BGC | classes | flags | AB | AF | Nov | products |\n|---|---|---|---|--:|--:|--:|---|\n")
        for s, bid, prod, ab, af, nov, cls, fl in sorted(flagged, key=lambda x: x[-1]):
            fh.write(f"| {s} | {bid} | {cls} | {fl} | {ab} | {af} | {nov} | {prod} |\n")
        fh.write("\n_Claim-safety: WATCH = a human should look, not 'more active'. Tiers are auto-floor "
                 "routing priors, not measured activity; class = capacity. Judgment deferred._\n")
    emit(f"reviewed {n_inv} Inventory rows -> REMAIN {total_inv} / to-Low {total_low}; "
          f"flagged {len(flagged)} for review")
    emit(f"wrote {md}", f"wrote {tsv}", sep="\n")
    return 0


def _default_boards_glob():
    """First package home whose ``<home>/*/package/*_4_triage_board.csv`` pattern matches.

    The old default hardcoded ``mamey_packages/`` — a home that can be absent — so a
    defaults run silently audited ZERO boards and still exited 0 (resolver-bypass audit
    finding 3, 2026-09-01). Homes tried, in order: ``mamey_packages``, ``Mamey Complete*``,
    then any ``MAMEY_PACKAGE_HOMES`` env globs (``os.pathsep``-separated). First home with
    matches wins — homes are NOT unioned, so a strain present in two homes is not
    double-counted. Returns (glob_pattern, n_matches); pattern may match zero if no home does.
    """
    root = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
    homes = ["mamey_packages", "Mamey Complete*"]
    homes += [h.strip() for h in os.environ.get("MAMEY_PACKAGE_HOMES", "").split(os.pathsep) if h.strip()]
    last = os.path.join(root, homes[0], "*", "package", "*_4_triage_board.csv")
    for home in homes:
        pat = os.path.join(root, home, "*", "package", "*_4_triage_board.csv")
        if glob.glob(pat):
            return pat, True
        last = pat
    return last, False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--boards-glob", default=None,
                    help="glob for *_4_triage_board.csv files (default: first package home with matches)")
    ap.add_argument("--out", default=".")
    a = ap.parse_args(argv)
    boards_glob = a.boards_glob
    if boards_glob is None:
        boards_glob, _found = _default_boards_glob()
    if not glob.glob(boards_glob):
        # Refuse loudly instead of writing a "reviewed 0" report: an audit over zero
        # boards is a location/estate error, never a finding.
        sys.stderr.write('{"status":"REFUSED","code":"INVENTORY_AUDIT_NO_BOARDS",'
                         '"detail":"boards glob matched no files; set --boards-glob, '
                         'SAPOTE_WORKSPACE_ROOT, or MAMEY_PACKAGE_HOMES"}\n')
        return 2
    return audit(boards_glob, pathlib.Path(a.out))


if __name__ == "__main__":
    raise SystemExit(main())

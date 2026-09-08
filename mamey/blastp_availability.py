"""blastp_availability.py — Central Command BLASTp availability declaration (.345).

Scans a runs dir (or one package) and declares, per strain per channel, how much BLASTp is
AVAILABLE on disk vs INGESTED into the package — the "activate at onset and declare availability"
step. Reader-side; non-scoring. Reuses blastp_gate discovery/compare so it agrees with the gate.

Emits: a text table, a CSV, and a JSON (the same aggregate a table/widget renders from).

CLAIM CEILING: BLASTp = similarity, not identity; counts are BGC-channel coverage, not a claim.
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
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import io
import json
import os
from pathlib import Path

from . import blastp_gate as _g

CHANNELS = ("nr", "clustered_nr", "swissprot", "ebi")


def strain_availability(package: str | Path, strain: str, trove_roots: dict | None = None) -> dict:
    """Declare available and stored BGC-channel pairs for one strain.

    ``ingested`` is the complete package-ledger/store count, even when the original trove is no
    longer discoverable from the current working directory. ``matched`` is the older
    available-and-ingested intersection. Keeping those concepts separate prevents a valid stored
    overlay from being displayed as ``0`` merely because its source trove is elsewhere.
    """
    roots = trove_roots if trove_roots is not None else _g.discover_trove_roots(package)
    avail = _g.available(strain, roots)
    have = _g.ingested(package)
    rec = {"strain": strain, "channels": {}}
    total_missing = 0
    for ch in CHANNELS:
        a = set(avail.get(ch, {}).keys())
        ing = {b for b, cs in have.items() if ch in cs}
        miss = len(a - ing)
        rec["channels"][ch] = {
            "avail": len(a),
            "ingested": len(ing),
            "matched": len(a & ing),
            "ingested_only": len(ing - a),
            "missing": miss,
        }
        total_missing += miss
    rec["total_missing"] = total_missing
    rec["gate_blocked"] = total_missing > 0
    return rec


def _strain_of(pkg: Path) -> str:
    for f in pkg.glob("*_4_triage_board.csv"):
        return f.name.split("_4_triage_board.csv")[0]
    return pkg.parent.name


def scan(runs_dir: str | Path | None = None, package: str | Path | None = None) -> dict:
    """Scan a runs dir (many packages) or a single package. Returns the availability aggregate."""
    pkgs: list[tuple[str, Path]] = []
    if package:
        p = Path(package)
        pkgs.append((_strain_of(p), p))
    else:
        runs = Path(runs_dir or ".")
        for d in sorted(runs.iterdir()):
            pk = d / "package"
            if pk.is_dir():
                pkgs.append((d.name, pk))
    roots = _g.discover_trove_roots(pkgs[0][1]) if pkgs else {}
    rows = [strain_availability(pk, s, trove_roots=roots) for s, pk in pkgs]
    tot_avail = sum(r["channels"][c]["avail"] for r in rows for c in CHANNELS)
    tot_ing = sum(r["channels"][c]["ingested"] for r in rows for c in CHANNELS)
    tot_matched = sum(r["channels"][c]["matched"] for r in rows for c in CHANNELS)
    tot_missing = sum(r["channels"][c]["missing"] for r in rows for c in CHANNELS)
    return {
        "meta": {
            "strains": len(rows),
            "blocked_strains": sum(1 for r in rows if r["gate_blocked"]),
            "available_pairs": tot_avail,
            "ingested_pairs": tot_ing,
            "matched_pairs": tot_matched,
            "missing_pairs": tot_missing,
            # v97396 fix: this defaulted to 1.0 ("100% ingested") whenever tot_avail == 0 -- but
            # that is exactly the tool's own stated primary use case ("activate at ONSET"),
            # before any BLASTp has run anywhere. Reporting a strain with zero available data as
            # fully complete contradicts this module's own "CLAIM CEILING: counts are BGC-channel
            # coverage, not a claim." None (rendered as N/A below) is honest; a numeric 0% would
            # be equally misleading in the other direction ("nothing done" when there is also
            # nothing TO do).
            "ingested_fraction": round(tot_matched / tot_avail, 3) if tot_avail else None,
            "trove_roots": {c: [Path(x).name for x in rs] for c, rs in roots.items() if rs},
        },
        "strains": rows,
    }


def render_table(agg: dict) -> str:
    m = agg["meta"]
    frac = m["ingested_fraction"]
    frac_display = f"{frac*100:.0f}%" if frac is not None else "N/A (nothing available yet)"
    L = ["BLASTP AVAILABILITY — Central Command declaration",
         f"  strains: {m['strains']}  ·  would-block (un-ingested): {m['blocked_strains']}  ·  "
         f"stored pairs: {m['ingested_pairs']}  ·  matched/available pairs: "
         f"{m['matched_pairs']}/{m['available_pairs']} "
         f"({frac_display})",
         f"  trove roots: {m['trove_roots']}",
         "",
         f"  {'strain':9} {'nr(a/s)':10} {'clus(a/s)':10} {'swiss(a/s)':11} {'ebi(a/s)':9} MISSING"]
    for r in sorted(agg["strains"], key=lambda x: -x["total_missing"]):
        def ai(ch):
            c = r["channels"][ch]
            return f"{c['avail']}/{c['ingested']}"
        L.append(f"  {r['strain']:9} {ai('nr'):10} {ai('clustered_nr'):10} "
                 f"{ai('swissprot'):11} {ai('ebi'):9} {r['total_missing']}")
    return "\n".join(L)


def _atomic_write_text(path: Path, text: str) -> None:
    """Write to a temp sibling then atomically replace (mirrors packaging.py's
    ``_atomic_write_text``), so an interrupted write never leaves a truncated
    BLASTP_AVAILABILITY.json/.csv behind."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write(agg: dict, out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_p = out / "BLASTP_AVAILABILITY.json"
    csv_p = out / "BLASTP_AVAILABILITY.csv"
    _atomic_write_text(json_p, json.dumps(agg, indent=1))
    channel_fields = ("avail", "ingested", "matched", "ingested_only", "missing")
    cols = ["strain"] + [f"{c}_{k}" for c in CHANNELS for k in channel_fields] + ["total_missing", "gate_blocked"]
    _csv_buf = io.StringIO(newline="")
    w = _SafeDictWriter(_csv_buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in agg["strains"]:
        row = {"strain": r["strain"], "total_missing": r["total_missing"], "gate_blocked": r["gate_blocked"]}
        for c in CHANNELS:
            for k in channel_fields:
                row[f"{c}_{k}"] = r["channels"][c][k]
        w.writerow(row)
    _atomic_write_text(csv_p, _csv_buf.getvalue())
    return {"json": str(json_p), "csv": str(csv_p)}


def blastp_availability_command(args) -> int:
    agg = scan(runs_dir=getattr(args, "runs_dir", None), package=getattr(args, "package", None))
    emit(render_table(agg))
    out = getattr(args, "out", None)
    if out:
        paths = write(agg, out)
        emit(f"\n-> {paths['csv']}\n-> {paths['json']}")
    return 0

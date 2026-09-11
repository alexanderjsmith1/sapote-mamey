"""cohort_leads_ledger.py — union every sealed package's triage board into ONE
ranked, cross-strain priority-leads worklist (ADD-01 shortlist).

Why: each sealed Mamey package already carries a per-strain triage board
(`*_4_triage_board.csv`) whose Exceptional/High rows are the leads a bench
scientist would act on first. Those boards exist per-strain but are never
aggregated — the cohort deliverable has a prose synthesis, not a machine-readable
cross-strain leads table. This module turns N scattered boards into one worklist.

Claim-safety: this is a pure RE-PROJECTION of already-computed, capacity-level
board rows. It re-ranks across the cohort as a routing prior ("look here first"),
never a bioactivity/structure claim, and NEVER recomputes AB/AF/tiers. It reads
the boards; it does not score. If strains span engine versions the output header
carries a MIXED-ENGINE comparability caution (rows scored by different engines are
not strictly comparable).

Design: stdlib only (csv, glob, json, os). No Mamey engine dependency — it reads
sealed packages, so it works on any runs-dir of already-sealed packages without
re-running anything.

CLI-free by design: the writer/logic lives here; argparse wiring is described in
FA1_HOOK.md so cli.py stays untouched during prototyping.

Usage (library):
    from mamey.cohort_leads_ledger import build_ledger, write_ledger
    rows, meta = build_ledger("path/to/runs_dir")
    write_ledger(rows, meta, "COHORT_PRIORITY_LEADS.csv")
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import glob
import json
import os
from typing import Any

# Lead-tier priority. Higher rank == higher priority. Only Exceptional + High are
# unioned into the ledger (Medium/Inventory are excluded by INCLUDE_TIERS).
TIER_RANK = {
    "exceptional": 4,
    "high": 3,
    "medium": 2,
    "inventory": 1,
}
INCLUDE_TIERS = {"exceptional", "high"}

# Output column order for COHORT_PRIORITY_LEADS.csv.
LEDGER_COLUMNS = [
    "Cohort_rank",
    "strain",
    "BGC_ID",
    "node_region",
    "Arch_Capacity",
    "Lead_tier_auto",
    "AB_auto",
    "AF_auto",
    "KCB_top",
    "Misanchor_Flag",
    "engine_version",
]


def _num(x: Any) -> float:
    """Parse a numeric cell; blanks/garbage sort last (as -inf-ish via 0.0 guard)."""
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return float("-inf")


def _read_manifest_engine(pkg_dir: str) -> str:
    """Return the engine/workflow version string for a sealed package, or ''.

    Prefers manifest.json's `workflow_version` (e.g. 'Mamey v1.9.x'); this is the
    authoritative per-package engine stamp.
    """
    mpath = os.path.join(pkg_dir, "manifest.json")
    if os.path.isfile(mpath):
        try:
            with open(mpath, encoding="utf-8") as fh:
                m = json.load(fh)
            v = m.get("workflow_version") or m.get("engine_version") or ""
            return str(v).strip()
        except (OSError, ValueError, json.JSONDecodeError):
            return ""
    return ""


def _strain_from_manifest(pkg_dir: str, fallback: str) -> str:
    mpath = os.path.join(pkg_dir, "manifest.json")
    if os.path.isfile(mpath):
        try:
            with open(mpath, encoding="utf-8") as fh:
                m = json.load(fh)
            s = m.get("strain_id") or m.get("display_name")
            if s:
                return str(s).strip()
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return fallback


def _node_region(row: dict) -> str:
    """Human-readable 'node·region' locator from a triage row."""
    node = (row.get("Node_ID") or "").strip()
    region = (row.get("antiSMASH_Region") or "").strip()
    if node and region:
        return f"{node} {region}"
    # Fall back to the composite Assembly_Locator if the split fields are absent.
    return (row.get("Assembly_Locator") or node or region or "").strip()


def find_triage_boards(runs_dir: str) -> list[str]:
    """Return sorted paths to every `*_4_triage_board.csv` under a runs-dir.

    Matches both `<runs>/<strain>/package/*_4_triage_board.csv` (audit_runs layout)
    and a flat `<runs>/*_4_triage_board.csv`.
    """
    patterns = [
        os.path.join(runs_dir, "*", "package", "*_4_triage_board.csv"),
        os.path.join(runs_dir, "*", "*_4_triage_board.csv"),
        os.path.join(runs_dir, "*_4_triage_board.csv"),
    ]
    seen: set[str] = set()
    out: list[str] = []
    for pat in patterns:
        for p in glob.glob(pat):
            rp = os.path.realpath(p)
            if rp not in seen:
                seen.add(rp)
                out.append(p)
    return sorted(out)


def build_ledger(runs_dir: str) -> tuple[list[dict], dict]:
    """Union all Exceptional+High triage rows across a runs-dir into ranked leads.

    Returns (rows, meta) where rows is a list of ledger dicts (already ranked and
    stamped with Cohort_rank) and meta carries {engine_versions, mixed_engine,
    n_strains, n_leads, boards}.
    """
    boards = find_triage_boards(runs_dir)
    collected: list[dict] = []
    engine_versions: set[str] = set()
    # AUDIT_374: n_strains is keyed on the CASE-NORMALIZED strain id, not the raw
    # display string. Two boards for the same physical strain whose manifest/filename casing
    # differs (e.g. "AS-XXX" vs "AS-XXX" -- a real possibility across re-run folders left in
    # the same runs-dir) previously counted as 2 distinct strains in the denominator, and their
    # rows both survived into the ranked ledger as if they were two different strains' leads.
    # `strains` still stores the case-normalized key; original casing is preserved unchanged in
    # each row's "strain" field so display output is untouched.
    strains: set[str] = set()

    for board in boards:
        pkg_dir = os.path.dirname(board)
        base = os.path.basename(board)
        # Strain prefix = filename up to the '_4_triage_board.csv' suffix.
        strain_guess = base.replace("_4_triage_board.csv", "")
        strain = _strain_from_manifest(pkg_dir, strain_guess)
        engine = _read_manifest_engine(pkg_dir)
        if engine:
            engine_versions.add(engine)
        strains.add(strain.strip().upper())

        try:
            with open(board, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    tier = (row.get("Lead_tier_auto") or "").strip()
                    if tier.lower() not in INCLUDE_TIERS:
                        continue
                    collected.append(
                        {
                            "strain": strain,
                            "BGC_ID": (row.get("BGC_ID") or "").strip(),
                            "node_region": _node_region(row),
                            "Arch_Capacity": (row.get("Arch_Capacity") or "").strip(),
                            "Lead_tier_auto": tier,
                            "AB_auto": (row.get("AB_auto") or "").strip(),
                            "AF_auto": (row.get("AF_auto") or "").strip(),
                            "KCB_top": (row.get("KCB_top") or "").strip(),
                            "Misanchor_Flag": (row.get("Misanchor_Flag") or "").strip(),
                            "engine_version": engine,
                            # private sort keys (dropped before write)
                            "_tier_rank": TIER_RANK.get(tier.lower(), 0),
                            "_af": _num(row.get("AF_auto")),
                            "_ab": _num(row.get("AB_auto")),
                        }
                    )
        except OSError:
            continue

    # Rank by (lead tier desc, then AF desc, then AB desc). Stable ties broken by
    # (strain, BGC_ID) for deterministic output.
    collected.sort(
        key=lambda r: (
            -r["_tier_rank"],
            -r["_af"] if r["_af"] != float("-inf") else float("inf"),
            -r["_ab"] if r["_ab"] != float("-inf") else float("inf"),
            r["strain"],
            r["BGC_ID"],
        )
    )
    for i, r in enumerate(collected, start=1):
        r["Cohort_rank"] = i

    meta = {
        "engine_versions": sorted(engine_versions),
        "mixed_engine": len(engine_versions) > 1,
        "n_strains": len(strains),
        "n_leads": len(collected),
        "boards": boards,
    }
    return collected, meta


def _mixed_engine_note(meta: dict) -> str:
    versions = ", ".join(meta["engine_versions"]) or "unknown"
    if meta["mixed_engine"]:
        return (
            "# CLAIM-SAFETY / COMPARABILITY: MIXED ENGINE VERSIONS in this cohort "
            f"({versions}). Rows scored by different engine versions are NOT strictly "
            "comparable; cross-strain ranking here is a routing prior only, not a "
            "confident cross-strain call. Re-run under a single engine before "
            "quoting cross-strain rank as evidence."
        )
    return (
        f"# Engine version: {versions} (single-engine cohort; rows are comparable). "
        "Ranking is a capacity-level routing prior, not a bioactivity/structure claim."
    )


def write_ledger(rows: list[dict], meta: dict, out_path: str) -> str:
    """Write COHORT_PRIORITY_LEADS.csv with a claim-safety/comparability header.

    The header lines begin with '#'; a standards-compliant CSV reader that ignores
    comment lines (or DictReader after skipping '#') can still consume the table.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    # AUDIT_374: build the CSV in memory, then write it crash-safely (tmp-sibling +
    # os.replace). This is the cohort-level worklist a bench scientist opens directly; a
    # process killed mid-write previously left a truncated COHORT_PRIORITY_LEADS.csv on disk
    # with no error surfaced anywhere.
    import io
    buf = io.StringIO()
    buf.write(_mixed_engine_note(meta) + "\n")
    buf.write(
        f"# Cohort priority leads: {meta['n_leads']} Exceptional+High leads "
        f"across {meta['n_strains']} strains. Capacity-level, non-scoring "
        "re-projection of sealed triage boards.\n"
    )
    writer = _SafeDictWriter(buf, fieldnames=LEDGER_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    tmp = str(out_path) + ".tmp"
    try:
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            fh.write(buf.getvalue())
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, out_path)
    return out_path


def run(runs_dir: str, out_path: str = "COHORT_PRIORITY_LEADS.csv") -> dict:
    """Convenience entry: build + write, returning meta (with out_path added)."""
    rows, meta = build_ledger(runs_dir)
    write_ledger(rows, meta, out_path)
    meta = dict(meta)
    meta["out_path"] = out_path
    return meta

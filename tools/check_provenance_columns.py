#!/usr/bin/env python3
"""check_provenance_columns.py — fail if a per-BGC table lacks its provenance anchor.

The failure this fixes (AS-XXX status-manifest, 2026-07-05): a hand-emitted per-BGC
status TSV led with a bare ``bgc`` column and dropped ``strain`` / ``contig`` / ``region``
entirely, so a ``BGC001`` row could not be traced to a strain or a node/region. That
violates the standing rule (cite every BGC node/region; BGC### is a non-portable internal
id, so node+region is the durable anchor) and makes the table un-mergeable across runs.

The canonical convention already exists in ``mamey/master_workbook.py`` — every per-BGC
sheet (B1_BGC_Master, B5_BLASTp_Hits, C1/C2_DAPR…) leads with
``strain, assembly_locator, contig, region, BGC_ID``. This gate enforces that any per-BGC
CSV/TSV emitted for delivery carries the same anchor, so no future cut can ship a per-BGC
table that isn't traceable.

A table is judged "per-BGC" if it has a BGC-id column (``BGC_ID`` / ``bgc_id`` / ``bgc`` /
``BGC``) or any cell matching the ``BGC\\d{3,}`` pattern in that column. For such a table the
gate requires, case-insensitively:
  - a strain column       (strain / strain_id)
  - a contig/node column  (contig / node_id / node)     OR an assembly_locator column
  - a region column       (region / antismash_region)   OR an assembly_locator column
(An ``assembly_locator`` column satisfies contig+region jointly, since it encodes
``NODE_x regionNNN (BGC###)`` — the boss-facing locus label from ``crosswalk.assembly_locator``.)

Fail-closed: exits non-zero the moment a per-BGC table is missing its anchor.

  python tools/check_provenance_columns.py path/to/table.tsv [more.csv ...]
  python tools/check_provenance_columns.py --glob 'runs_*/**/*.tsv'
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import csv
import glob
import re
import sys
from pathlib import Path

BGC_ID_COLS = {"bgc_id", "bgc", "bgcid"}
STRAIN_COLS = {"strain", "strain_id", "strainid"}
# v9.7.409 (CLAUDE_409 provenance anchors, Defect B): recognise the project's OWN canonical
# split-locus column names. The activity-lead exports (the package's gold standard) carry
# `strain, exact_locus, full_node_or_contig, region, bgc_alias`; the cohort roster carries
# `node/contig`; pairwise tables carry `contig_a/contig_b`. Without these, the gate flagged its
# own most doctrine-faithful tables. See development/round4_sweep/PROVENANCE_COLUMNS_TRIAGE.md.
CONTIG_COLS = {"contig", "node_id", "node", "nodeid",
               "full_node_or_contig", "exact_locus", "node/contig", "contig_a", "contig_b"}
REGION_COLS = {"region", "antismash_region", "region_key", "region_number"}
LOCATOR_COLS = {"assembly_locator", "locus", "locus_label", "exact_locus"}
BGC_CELL = re.compile(r"^BGC\d{3,}$", re.I)


def _norm(h: str) -> str:
    return (h or "").strip().lstrip("\ufeff").lower()


def _sniff(path: Path):
    """Return (fieldnames, rows) using the delimiter implied by the suffix.

    BC2-PC-01 (v9.7.396): the delimiter used to come SOLELY from the file suffix (.tsv/.tab ->
    tab, else comma), with no check that the file's actual content agreed. A per-BGC table
    genuinely missing its provenance anchor (bare "bgc" column, no strain/contig/region --
    exactly the AS-XXX 2026-07-05 failure this gate's own docstring cites as its origin) was
    misparsed into a single garbled header when its real delimiter didn't match its extension
    (e.g. a comma-delimited export saved with a .tsv extension). DictReader then returned one
    nonsense fieldname matching no BGC_ID_COLS and no cell matching BGC_CELL, so _is_per_bgc()
    returned False and this fail-closed gate silently reported "not a per-BGC table" — exactly
    the class of failure it exists to catch, hidden by an extension/content mismatch rather than
    a real absence of the anchor columns. Reproduced with both mismatch directions.

    Fix: if the suffix-implied delimiter produces exactly one field (the classic misparse
    signature) and the OTHER delimiter appears inside that field's text, re-parse with the other
    delimiter instead. Narrow and low-risk: it only fires on the unambiguous single-field-with-
    other-delimiter-inside signature, so a genuinely single-column file is untouched unless its
    one column's own values happen to contain the other delimiter character.
    """
    suffix_delim = "\t" if path.suffix.lower() in (".tsv", ".tab") else ","
    other_delim = "," if suffix_delim == "\t" else "\t"

    def _read(delim):
        with path.open(encoding="utf-8", newline="") as fh:
            lines = fh.readlines()
        # v9.7.409 (CLAUDE_409 provenance anchors, Defect A): skip a leading `#`-comment banner.
        # Mamey figure-data CSVs lead with a `# provenance,...` line; csv.DictReader took that
        # banner as the header row, hiding the real `contig,region` header one line below and
        # manufacturing three false "missing anchor" failures. Drop leading lines whose first
        # non-space character is `#` before parsing.
        start = 0
        while start < len(lines) and lines[start].lstrip().startswith("#"):
            start += 1
        reader = csv.DictReader(lines[start:], delimiter=delim)
        fields = reader.fieldnames or []
        rows = list(reader)
        return fields, rows

    fields, rows = _read(suffix_delim)
    if len(fields) == 1 and other_delim in fields[0]:
        fields, rows = _read(other_delim)
    return fields, rows


def _is_per_bgc(fields, rows) -> tuple[bool, str | None]:
    """A table is per-BGC if it has a BGC-id header, or a column whose cells look like BGC###."""
    norm = {_norm(f): f for f in fields}
    for key in BGC_ID_COLS:
        if key in norm:
            return True, norm[key]
    # scan cells: any column where >=1 cell matches BGC\d{3,}
    # v9.7.374: was rows[:50] -- a fail-closed provenance gate silently skipped the AS-XXX class
    # of failure it exists to catch whenever the real BGC-id cells didn't happen to fall in the
    # first 50 rows (e.g. leading blank/placeholder/summary rows before the detail section, or
    # any per-BGC deliverable table over ~50 rows with IDs later in the file). Scan every row --
    # correctness matters more than the marginal cost of scanning a per-BGC delivery table, which
    # is never large enough for a full-column scan to be a real performance concern.
    for f in fields:
        for r in rows:
            v = (r.get(f) or "").strip()
            if BGC_CELL.match(v):
                return True, f
    return False, None


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        fields, rows = _sniff(path)
    except Exception as exc:  # unreadable → report, don't crash the gate
        return [f"{path}: unreadable ({type(exc).__name__}: {exc})"]
    if not fields:
        return []  # empty / headerless: not a per-BGC delivery table
    per_bgc, _ = _is_per_bgc(fields, rows)
    if not per_bgc:
        return []  # not a per-BGC table; gate does not apply
    norm = {_norm(f) for f in fields}
    has_locator = bool(norm & LOCATOR_COLS)
    if not (norm & STRAIN_COLS):
        problems.append(f"{path}: per-BGC table missing a strain column (need one of {sorted(STRAIN_COLS)})")
    if not (norm & CONTIG_COLS or has_locator):
        problems.append(f"{path}: per-BGC table missing contig/node (need one of {sorted(CONTIG_COLS)} or an assembly_locator)")
    if not (norm & REGION_COLS or has_locator):
        problems.append(f"{path}: per-BGC table missing region (need one of {sorted(REGION_COLS)} or an assembly_locator)")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="CSV/TSV files to check")
    ap.add_argument("--glob", action="append", default=[], help="glob(s) of tables to check (recursive **)")
    ns = ap.parse_args(argv)

    targets: list[Path] = [Path(p) for p in ns.paths]
    for g in ns.glob:
        targets += [Path(p) for p in glob.glob(g, recursive=True)]
    targets = [p for p in targets if p.suffix.lower() in (".tsv", ".tab", ".csv") and p.is_file()]

    if not targets:
        emit("check_provenance_columns: no CSV/TSV targets given", file=sys.stderr)
        return 2

    all_problems: list[str] = []
    checked = 0
    for path in targets:
        checked += 1
        all_problems += check_file(path)

    if all_problems:
        emit(f"check_provenance_columns: FAIL — {len(all_problems)} per-BGC table(s) missing provenance anchor:", file=sys.stderr)
        for p in all_problems:
            emit(f"  {p}", file=sys.stderr)
        return 1
    emit(f"check_provenance_columns: OK — {checked} table(s) checked, all per-BGC tables carry strain+contig+region (or assembly_locator).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

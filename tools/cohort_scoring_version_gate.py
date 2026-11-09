#!/usr/bin/env python3
"""cohort_scoring_version_gate.py — fail-closed: a comparative build may only aggregate strains
scored under ONE engine version.

STATUS (v9.7.374 doc-fix): this module docstring previously read "DRAFT for v9.7.99 ...
intentionally NOT registered yet" — stale since v9.7.338. It has in fact been reclassified WIRED
since .338 (COH-01) and is hooked into `mamey.cohort_deliverable._check_engine_uniformity`, which
calls `assert_uniform_scoring_engine(...)` before any cross-strain aggregation in
`run_cohort_deliverable()`. `tools/gate_registry.tsv` correctly lists it WIRED, and
`tests/test_gate_wiring_invariant.py::_UNIT_TESTED_OPERATOR_GATES` already documents the .338
reclassification in a comment — only this file's own docstring had not caught up. See
`tests/test_cohort_scoring_version_gate.py` and `tests/test_cohort_deliverable.py` for the
regression coverage.

Why (docs/history/retired_458/COHORT_RESCORING_PLAN.md): scoring boundaries stacked 1.9.84→1.9.96. Cross-strain AB/AF
comparison is only valid when every aggregated strain was scored under the same engine. Before
this gate existed, the comparative builds (hub_merge, build_cross_strain_figures, lead_board,
cohort_concordance_summary, build_master*, merge_workbooks) aggregated strains with NO version
check — so a mixed-version cohort silently produced an invalid comparison. This converts "remember
to re-score" into a gate, the same fail-closed pattern as the leak audit and tier-derivation parity
gate.

Per-strain provenance already exists: the master workbook's A3_Run_Manifest sheet records
"version" = f"Mamey v{engine}" (mamey/master_workbook.py). The gate reads that field per strain.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, re, sys
from pathlib import Path


class CohortVersionError(RuntimeError):
    """Raised when a comparative cohort spans more than one scoring engine version."""


_VER = re.compile(r"(\d+\.\d+\.\d+)")


def parse_engine_version(version_field: str) -> str | None:
    """'Mamey v1.9.96' -> '1.9.96'; tolerant of surrounding text. None if no version found."""  # version-sync-ok
    m = _VER.search(version_field or "")
    return m.group(1) if m else None


def assert_uniform_scoring_engine(strain_versions: dict[str, str], current_engine: str) -> None:
    """Raise CohortVersionError unless every strain's parsed engine == current_engine.

    strain_versions: {strain_id: raw version field, e.g. 'Mamey v1.9.96'}. Missing/unparseable  # version-sync-ok
    versions are themselves a failure (a strain with no recorded provenance can't be certified).
    """
    offenders, unstamped = {}, []
    # v9.7.115: an empty cohort is a FAILURE, not a vacuous pass. A fail-closed gate that says "OK"
    # when it found zero strains to certify almost always means a bad glob/path, not a clean cohort —
    # and a comparative build on zero strains is meaningless. Refuse rather than wave it through.
    if not strain_versions:
        raise CohortVersionError(
            f"no strains found to certify at engine {current_engine} — the comparative cohort is "
            "empty (likely a wrong workbooks path). A fail-closed gate does not pass on zero input."
        )
    for strain, raw in strain_versions.items():
        v = parse_engine_version(raw)
        if v is None:
            unstamped.append(strain)
        elif v != current_engine:
            offenders[strain] = v
    if unstamped or offenders:
        parts = []
        if offenders:
            parts.append("scored under a different engine: "
                         + ", ".join(f"{s}={v}" for s, v in sorted(offenders.items())))
        if unstamped:
            parts.append("no recorded engine version: " + ", ".join(sorted(unstamped)))
        raise CohortVersionError(
            f"cohort is not uniformly scored at engine {current_engine} — " + "; ".join(parts)
            + ". Re-score these strains under the current engine before building a comparative deliverable."
        )


def _read_workbook_versions(path: Path) -> list[str]:
    """Every data row's A3_Run_Manifest 'version' from a strain master workbook (read-only).

    Fully blank rows are skipped. A workbook with no manifest sheet, no 'version' column or no
    data row gives an empty list, which the CLI treats as an unstamped workbook.
    """
    import openpyxl  # local import: comparative builds already depend on openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in ("A3_Run_Manifest", "Run_Manifest"):
            if sheet in wb.sheetnames:
                ws = wb[sheet]
                header = [c.value for c in next(ws.iter_rows(max_row=1))]
                if "version" in header:
                    col = header.index("version")
                    return [str(row[col]) if col < len(row) and row[col] is not None else ""
                            for row in ws.iter_rows(min_row=2, values_only=True)
                            if any(cell is not None and str(cell).strip() for cell in row)]
        return []
    finally:
        wb.close()


def _read_workbook_version(path: Path) -> str:
    """First manifest row's version (kept for callers of the old helper)."""
    rows = _read_workbook_versions(path)
    return rows[0] if rows else ""


def collect_versions(workbooks_dir: Path) -> dict[str, str]:
    """{workbook stem or 'stem [manifest row N]': raw version} for every top-level *.xlsx.

    Every manifest data row is read, so a later row recorded under another engine is seen.
    """
    strain_versions = {}
    for wbp in sorted(Path(workbooks_dir).glob("*.xlsx")):
        rows = _read_workbook_versions(wbp)
        if len(rows) <= 1:
            strain_versions[wbp.stem] = rows[0] if rows else ""
        else:
            for index, raw in enumerate(rows, start=2):
                strain_versions[f"{wbp.stem} [manifest row {index}]"] = raw
    return strain_versions


def check_roster(workbooks_dir: Path, roster_path: Path) -> None:
    """Raise CohortVersionError unless the top-level *.xlsx stems equal the intended roster."""
    names = [line.strip() for line in roster_path.read_text(encoding="utf-8").splitlines()]
    names = [n for n in names if n and not n.startswith("#")]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    found = {p.stem for p in Path(workbooks_dir).glob("*.xlsx")}
    missing, extra = sorted(set(names) - found), sorted(found - set(names))
    if duplicates or missing or extra or not names:
        raise CohortVersionError(
            "workbooks do not match the intended roster: "
            + "; ".join(part for part in (
                "roster is empty" if not names else "",
                ("duplicate roster entries: " + ", ".join(duplicates)) if duplicates else "",
                ("missing workbooks: " + ", ".join(missing)) if missing else "",
                ("workbooks not on the roster: " + ", ".join(extra)) if extra else "") if part))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbooks-dir", required=True, help="dir of per-strain master workbooks (*.xlsx)")
    ap.add_argument("--engine", required=True, help="current engine version, e.g. 1.9.96")
    ap.add_argument("--roster", type=Path, default=None,
                    help="text file naming the intended workbook stems, one per line; the gate "
                         "fails unless the top-level *.xlsx files match it exactly")
    a = ap.parse_args(argv)
    try:
        if a.roster is not None:
            check_roster(Path(a.workbooks_dir), a.roster)
        strain_versions = collect_versions(Path(a.workbooks_dir))
        assert_uniform_scoring_engine(strain_versions, a.engine)
    except (CohortVersionError, OSError) as e:
        emit(f"FAIL: {e}", file=sys.stderr)
        return 1
    scope = ("the files match the intended roster" if a.roster is not None else
             "no intended roster was checked, so a missing workbook would not be seen")
    emit(f"OK: all {len(strain_versions)} manifest version record(s) read from top-level *.xlsx in "
         f"{a.workbooks_dir} are at engine {a.engine}; {scope}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

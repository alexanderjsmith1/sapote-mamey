"""exclusion_gate.py — leak detector for whole-strain exclusions in GOVERNED output.

The SSOT accessor (``mamey/exclusions.py``) tells modules WHICH strains are held
out of governed conclusions; this module ENFORCES that decision at the output
boundary. It scans a governed/public output table (a CSV, an .xlsx, or an
in-memory list of rows) and FAILS if any hard-excluded strain id
(``exclusions.governed_excluded()`` == {AS-XXX}) appears in it.

Why this exists (the leak it closes): before this gate, nothing failed a run when
a hard-excluded strain reached a governed cross-strain table. ``exclusions.py`` was
wired into the RAW-data report modules (dualpass_ledger, p450_tailoring,
assembly_line, compound_family_report, widget_data), but the GOVERNED conclusion
emitters — the cross-strain master workbook (BGC_Master / class matrix / DAPR
AB+AF lead boards) and the sealed per-strain package validator — never consulted
``governed_excluded()``. A ``run --strain AS-XXX`` (or a stray AS-XXX row appended
to the master workbook) would therefore seal and validate as a governed result
with nothing to catch it. This module is that missing catch, routed through the
one SSOT so a future exclusion change stays a single edit.

Scope note — GOVERNED, not RAW: this gate uses ``governed_excluded()`` (AS-XXX
only). AS-XXX is IN governed conclusions (decontaminated strain-of-record, ratified
2026-08-05), so an AS-XXX row must NOT trip this gate. Raw-data modules that must
also skip AS-XXX use ``exclusions.raw_analysis_excluded()`` instead — pass a custom
``exclude`` set for that scope.

Engine-neutral: pure detection over already-produced tables. It changes no score
and no extracted value; it only refuses to bless an output that leaked an excluded
strain.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import exclusions

# AS-###/AJS-### style ids embedded anywhere in a cell (e.g. "AS-XXX_BGC3",
# "runs/AS-XXX/package"). Boundaried so AS-XXX does not match AS-XXX.
# AUDIT_371: case-insensitive -- a strain id is always canonically uppercase
# throughout this pipeline, but this gate exists specifically to catch a strain id
# leaking into free text (a filename, a note, a copy-pasted path), which is exactly
# the kind of text that CAN legitimately vary in case (reproduced live: "AS-XXX" in
# a cell was silently missed by the case-sensitive version, while "AS-XXX" in an
# otherwise-identical cell was correctly caught). Matching case-insensitively can
# only make this leak-prevention gate MORE strict, never less -- there is no
# legitimate governed-output text where a case-insensitive match would be a false
# positive that should be blocked from failing.
_ID_RE = re.compile(r"(?<![0-9A-Za-z])(A[JS]?S-[0-9]{2,5})(?![0-9])", re.IGNORECASE)


def _norm(value: Any) -> str:
    return "" if value is None else str(value)


def _ids_in_text(text: str) -> set[str]:
    # AUDIT_371: normalize the matched substring to canonical uppercase before
    # returning it -- _ID_RE now matches case-insensitively, but `excl` (the exclusion
    # set from exclusions.governed_excluded()/raw_analysis_excluded()) is always
    # canonical uppercase, so a case-sensitive `in excl` membership check would still
    # silently miss a lowercase match even with the regex fixed. Both sides must be
    # normalized consistently for the fix to actually close the gap.
    return {m.group(1).upper() for m in _ID_RE.finditer(text)}


def excluded_ids_in_row(row: Iterable[Any] | Mapping[str, Any],
                        exclude: set[str] | None = None) -> set[str]:
    """Return the hard-excluded strain ids present in a single row.

    ``row`` may be a sequence of cells or a mapping (dict). ``exclude`` defaults to
    the SSOT ``governed_excluded()`` set; pass ``raw_analysis_excluded()`` for the
    raw-data scope.
    """
    excl = exclusions.governed_excluded() if exclude is None else set(exclude)
    if not excl:
        return set()
    cells = row.values() if isinstance(row, Mapping) else row
    found: set[str] = set()
    for cell in cells:
        for cid in _ids_in_text(_norm(cell)):
            if cid in excl:
                found.add(cid)
    return found


def scan_rows(rows: Iterable[Iterable[Any] | Mapping[str, Any]],
              exclude: set[str] | None = None) -> set[str]:
    """Scan an iterable of rows; return every hard-excluded strain id found."""
    found: set[str] = set()
    for row in rows:
        found |= excluded_ids_in_row(row, exclude=exclude)
    return found


def scan_csv(path: str | Path, exclude: set[str] | None = None) -> set[str]:
    """Scan a CSV/TSV governed table for hard-excluded strain ids."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")
    delimiter = "\t" if (p.suffix.lower() == ".tsv" or "\t" in text.splitlines()[0:1] and "," not in text.splitlines()[0:1]) else ","
    reader = csv.reader(text.splitlines(), delimiter=delimiter)
    return scan_rows(reader, exclude=exclude)


def scan_xlsx(path: str | Path, exclude: set[str] | None = None) -> dict[str, set[str]]:
    """Scan every sheet of an .xlsx governed workbook.

    Returns ``{sheet_name: {offending ids}}`` for sheets that leaked an excluded
    strain (empty dict == clean). Requires openpyxl; raises ImportError if absent
    so the caller fails closed rather than silently skipping the check.
    """
    from openpyxl import load_workbook  # local import: optional dep, fail closed
    wb = load_workbook(Path(path), read_only=True, data_only=True)
    offenders: dict[str, set[str]] = {}
    try:
        for ws in wb.worksheets:
            hits = scan_rows(ws.iter_rows(values_only=True), exclude=exclude)
            if hits:
                offenders[ws.title] = hits
    finally:
        wb.close()
    return offenders


def gate_governed_outputs(paths: Iterable[str | Path],
                          exclude: set[str] | None = None) -> dict[str, Any]:
    """Gate a set of governed output files (.csv/.tsv/.xlsx).

    Returns a validate.py-style result dict::

        {"status": "PASS"|"FAIL",
         "exclusion_set": [...],
         "offenders": {path: {sheet_or_'*': [ids]}}}

    ``status`` is FAIL if any hard-excluded strain id appears in any table.
    """
    excl = exclusions.governed_excluded() if exclude is None else set(exclude)
    offenders: dict[str, Any] = {}
    for path in paths:
        p = Path(path)
        if not p.is_file():
            continue
        suf = p.suffix.lower()
        if suf in (".csv", ".tsv"):
            hits = scan_csv(p, exclude=excl)
            if hits:
                offenders[str(p)] = {"*": sorted(hits)}
        elif suf in (".xlsx", ".xlsm"):
            sheet_hits = scan_xlsx(p, exclude=excl)
            if sheet_hits:
                offenders[str(p)] = {s: sorted(v) for s, v in sheet_hits.items()}
    return {
        "status": "FAIL" if offenders else "PASS",
        "exclusion_set": sorted(excl),
        "offenders": offenders,
    }


def assert_strain_governable(strain_id: str, exclude: set[str] | None = None) -> None:
    """Raise ValueError if ``strain_id`` is hard-excluded from governed conclusions.

    Source-side guard for governed emitters (e.g. master_workbook.update_master_workbook)
    so an excluded strain is refused at ingest, before it ever reaches a table.
    """
    excl = exclusions.governed_excluded() if exclude is None else set(exclude)
    # AUDIT_374: this ingest-side guard was missed by the AUDIT_371 case
    # normalization pass applied to the rest of this module (_ids_in_text/scan_rows) --
    # `excl` is always canonical uppercase, so a raw `str(strain_id) in excl` check silently
    # let a differently-cased --strain value (e.g. "AS-XXX") through with zero exception,
    # exactly the leak this module's docstring says it exists to close. Reproduced live.
    if str(strain_id).strip().upper() in {s.upper() for s in excl}:
        raise ValueError(
            f"exclusion_gate: {strain_id} is hard-excluded from GOVERNED output "
            f"(SSOT: OFFICIAL_DATA/exclusions.json governed_excluded={sorted(excl)}). "
            "Refusing to append it to a governed cross-strain table."
        )

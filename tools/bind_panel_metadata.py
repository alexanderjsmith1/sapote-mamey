#!/usr/bin/env python3
"""Bind display metadata onto a GToTree panel's figure_metadata.tsv.

Inputs (all paths are arguments; nothing is hard-coded to a session folder):

  --panel-dir DIR        baseline panel holding figure_metadata.tsv
  --out-dir DIR          where the bound figure_metadata.tsv is written
  --bc3 TSV              verified source/geography table (identifier, panels,
                         isolation_source_verified/_existing, geography_*, location_*)
  --corrections TSV      owner correction table (panel, identifier, field, proposed_value,
                         unresolved_issue); a WITHDRAW / UNRESOLVABLE / DO NOT / NO TRACEABLE
                         value clears the field
  --assay-table TSV      bioassay table, columns: strain, anti_candida, anti_mrsa
                         states are exactly "+", "-" (or U+2212), "n.t." or blank
  --assembly-records TSV NCBI Assembly esummary export, columns: accession, organism,
                         strain, fromtype (extra columns such as level, biosample are kept
                         but unused)
  --omitted-tips TSV     omit receipt (tip, name, reason) written by
                         tools/omitted_tips_receipt.py; copied beside the output and checked
                         against the bound tips

Design rules, in order of importance:

1. NOTHING IS INVENTED. Free-text isolation source is mapped to a display *category* through
   the explicit table below. A value that matches no rule is reported and the run FAILS; it is
   never silently bucketed into "Other documented".
2. THE DEPOSITED TEXT IS PRESERVED. `source_display` keeps the verbatim record; the category is
   a separate column. Organism names in labels are exactly as deposited; none are corrected.
3. ABSENCE IS DISPLAYED AS ABSENCE. An assay cell has four states (+, -, n.t., blank). A blank
   is never coerced into n.t. and n.t. is never coerced into a negative.
4. OWNER CORRECTIONS WIN over the verified table where both speak.
5. `[Type]` is a claim. It is written only when the NCBI Assembly record's `fromtype` equals
   "assembly from type material". `reference_class` follows the same field.
"""
from __future__ import annotations

import argparse
import csv
import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import logging as _logging  # noqa: E402
import sys as _sys_for_log  # noqa: E402
_LOG = _logging.getLogger(__name__)
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from omitted_tips_receipt import read_receipt  # noqa: E402

ABSENT = {"", "pending", "unknown", "na", "n/a", "missing", "not recorded", "unresolved", "none"}
NOT_RECORDED = "Not recorded"

ASSAY_STATES = ("+", "-", "−", "n.t.", "")
ASSAY_TABLE_COLUMNS = ("strain", "anti_candida", "anti_mrsa")
ASSEMBLY_RECORD_COLUMNS = ("accession", "organism", "strain", "fromtype")
TYPE_MATERIAL = "assembly from type material"

# --- isolation source -> registry category ------------------------------------------------------
# Ordered: first match wins. Patterns are matched against the lower-cased deposited text.
SOURCE_RULES: list[tuple[str, str]] = [
    # FIRST, ALWAYS: a laboratory derivative inherits nothing from its parent's environment.
    (r"\bmutant\b|\bderivative\b|derived from|\bsubclone\b", "Laboratory mutant"),
    (r"\bbumble\s*bee|\bbombus\b", "Bumblebee"),
    (r"\bhoney\s*bee|\bapis\b", "Honeybee"),
    (r"\bwasp\b|vespid", "Wasp"),
    (r"\bant\b|\batta\b|acromyrmex|attine", "Ant"),
    (r"\bbee\b|apidae|andrena|halictid", "Other bee"),
    (r"termite", "Termite"),
    (r"mycetoma|lesion|clinical|sputum|homo sapiens|\bhuman\b|skin|blood|wound|abscess|"
     r"\bpatient\b|bronchial|cerebrospinal", "Animal/clinical"),
    (r"lichen", "Lichen"),
    (r"moss|bryophyte", "Bryophyte"),
    (r"biofilter", "Biofilter"),
    (r"sludge|waste|effluent|sewage", "Waste-associated"),
    (r"mangrove", "Mangrove"),
    (r"marine|ocean|sea\s|seawater|saline lake|salt lake", "Marine"),
    (r"freshwater|lake|river|pond", "Freshwater sediment"),
    # plant BEFORE soil: "chickpea rhizosphere" and "root of X" are plant-associated, not soil
    (r"rhizosphere|endophyte|\broot\b|stem|tuber|leaf|bark|plant|pollen|sugarcane|wheat-field", "Plant"),
    # "natural rubber" is a processed material, not a living-plant association
    (r"natural rubber|\brubber\b", "Other documented"),
    (r"\bsoil\b|sediment|rock|basalt|peat|desert|cave", "Soil"),
    (r"fermentation|starter", "Other documented"),
]

# --- geography -> registry vocabulary -----------------------------------------------------------
GEO_RULES: list[tuple[str, str]] = [
    (r"^us$|united states|^usa$|\bu\.s\.a?\b", "US"),
    (r"canada", "Canada"),
    (r"north america|central america|mexico|caribbean", "North America"),
    (r"south america|brazil|peru|chile|argentina|colombia", "South America"),
    (r"^asia$|china|japan|korea|thailand|india|bangladesh|vietnam", "Asia"),
    (r"^europe$|germany|france|spain|italy|uk|united kingdom|netherlands", "Europe"),
    (r"^africa$|egypt|sudan|morocco|kenya", "Africa"),
    (r"oceania|australia|new zealand", "Oceania"),
    (r"antarctic", "Antarctica"),
    (r"pacific|indian ocean|atlantic", "Marine"),
]


class BindError(SystemExit):
    pass


def _read_tsv(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


# ------------------------------------------------------------------------------------------------
# Assay cells (four states, never coerced)
# ------------------------------------------------------------------------------------------------
def strain_id_from_row(row: dict) -> str:
    """Owner strain id for a QUERY row: the identifier column, else the AS-nnn prefix of the tip."""
    ident = (row.get("identifier") or "").strip()
    if re.fullmatch(r"AS-\d+", ident):
        return ident
    m = re.match(r"^(AS-\d+)", (row.get("tip") or "").strip())
    return m.group(1) if m else ident


def load_assay_table(path: str | Path) -> dict[str, tuple[str, str]]:
    path = Path(path)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = tuple(reader.fieldnames or ())
        if not set(ASSAY_TABLE_COLUMNS) <= set(header):
            raise BindError(f"ASSAY_TABLE_HEADER: {path} has {header}, needs {ASSAY_TABLE_COLUMNS}")
        out: dict[str, tuple[str, str]] = {}
        for row in reader:
            strain = (row.get("strain") or "").strip()
            if not strain:
                continue
            cand = (row.get("anti_candida") if row.get("anti_candida") is not None else "").strip()
            mrsa = (row.get("anti_mrsa") if row.get("anti_mrsa") is not None else "").strip()
            for state in (cand, mrsa):
                if state not in ASSAY_STATES:
                    raise BindError(
                        f"ASSAY_STATE_INVALID: {strain} carries {state!r}; the four states are "
                        "'+', '-', 'n.t.' and blank. Nothing is coerced."
                    )
            if strain in out and out[strain] != (cand, mrsa):
                raise BindError(f"ASSAY_TABLE_CONFLICT: {strain} appears twice with different states")
            out[strain] = (cand, mrsa)
    return out


def bind_assay_cells(rows: list[dict], assay: dict[str, tuple[str, str]], source_label: str) -> dict[str, str]:
    """Fill Candida/MRSA on QUERY rows from the assay table; reference rows are never touched.

    Returns {strain: outcome} where outcome is BOUND or NO_ASSAY_ROW. A strain absent from the
    table keeps whatever the row already had (usually blank) and is reported, not guessed.
    """
    report: dict[str, str] = {}
    for row in rows:
        if (row.get("role") or "").strip().upper() != "QUERY":
            continue
        strain = strain_id_from_row(row)
        if strain not in assay:
            report[strain] = "NO_ASSAY_ROW"
            continue
        cand, mrsa = assay[strain]
        row["Candida"], row["MRSA"] = cand, mrsa    # exact states; blank stays blank
        status = (row.get("metadata_status") or "").strip()
        row["metadata_status"] = (status + "+" if status else "") + f"ASSAY_FROM:{source_label}"
        report[strain] = "BOUND"
    return report


# ------------------------------------------------------------------------------------------------
# Reference labels from NCBI Assembly records ([Type] only from fromtype)
# ------------------------------------------------------------------------------------------------
def is_type_material(fromtype: str) -> bool:
    return (fromtype or "").strip().casefold() == TYPE_MATERIAL


def load_assembly_records(path: str | Path) -> dict[str, dict]:
    path = Path(path)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = tuple(reader.fieldnames or ())
        if not set(ASSEMBLY_RECORD_COLUMNS) <= set(header):
            raise BindError(f"ASSEMBLY_RECORDS_HEADER: {path} has {header}, needs {ASSEMBLY_RECORD_COLUMNS}")
        out: dict[str, dict] = {}
        for row in reader:
            acc = (row.get("accession") or "").strip()
            if acc:
                out[acc] = {k: (row.get(k) or "").strip() for k in ASSEMBLY_RECORD_COLUMNS}
    return out


def build_reference_label(row: dict, record: dict) -> dict:
    """Return the label fields for a reference/outgroup row from its Assembly record.

    label = "<organism> <strain> [Type] (<accession>)"; strain is omitted when the deposited
    organism string already ends with it; [Type] only when fromtype is type material; outgroups
    carry "[Type; outgroup]" or "[outgroup]". QUERY rows are left to the owner's own labels.
    """
    organism, strain = record["organism"], record["strain"]
    if not strain:
        m = re.search(r"\bstrain ([^\s,]+)", row.get("label_concise") or "")
        strain = m.group(1) if m else ""
    name = organism if (strain and strain in organism) else f"{organism} {strain}".strip()
    typed = is_type_material(record["fromtype"])
    tag = "Type" if typed else ""
    if (row.get("role") or "").strip().upper() == "OUTGROUP":
        tag = f"{tag}; outgroup" if tag else "outgroup"
    label = f"{name}{' [' + tag + ']' if tag else ''} ({record['accession']})"
    return {"label_concise": label, "label_experiment": label,
            "reference_class": "Type" if typed else "Reference"}


def bind_reference_labels(rows: list[dict], records: dict[str, dict]) -> dict[str, str]:
    report: dict[str, str] = {}
    for row in rows:
        if (row.get("role") or "").strip().upper() == "QUERY":
            continue
        acc = (row.get("identifier") or "").strip()
        rec = records.get(acc)
        if rec is None:
            report[acc or row.get("tip", "?")] = "NO_ASSEMBLY_RECORD"
            continue
        row.update(build_reference_label(row, rec))
        report[acc] = "Type" if is_type_material(rec["fromtype"]) else "Reference"
    return report


# ------------------------------------------------------------------------------------------------
# Source / geography from the verified table plus owner corrections
# ------------------------------------------------------------------------------------------------
def _pick(row: dict, base: str) -> str:
    for key in (f"{base}_verified", f"{base}_existing"):
        val = (row.get(key) or "").strip()
        if val and val.lower() not in ABSENT:
            return val
    return ""


def classify(text: str, rules: list[tuple[str, str]], field: str, ident: str) -> str:
    if not text or text.lower() in ABSENT:
        return NOT_RECORDED
    low = text.lower()
    for pattern, category in rules:
        if re.search(pattern, low):
            return category
    raise BindError(f"UNMAPPED {field} for {ident}: {text!r}\n  Add an explicit rule rather than a default bucket.")


def load_bc3(path: Path, panel: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in _read_tsv(path):
        if panel in (row.get("panels") or ""):
            out[row["identifier"].strip()] = row
    return out


def load_corrections(path: Path, panel: str, identity_holds: set[str]) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for row in _read_tsv(path):
        row_panel = (row.get("panel") or "").strip()
        if row_panel != panel and not row_panel.startswith("LOCAL-"):
            continue
        val = (row.get("proposed_value") or "").strip()
        ident = row["identifier"].strip()
        if re.search(r"IDENTITY HOLD", row.get("unresolved_issue") or "", re.I):
            identity_holds.add(ident)
        if re.match(r"^(UNRESOLVABLE|WITHDRAW|DO NOT|NO TRACEABLE)", val, re.I):
            out[(ident, row["field"].strip())] = "__CLEARED__"
            continue
        if re.match(r"^THESE ARE", val, re.I):
            continue
        out[(ident, row["field"].strip())] = val
    return out


def apply_identity_hold(label: str) -> str:
    label = re.sub(r"^([A-Z][a-z]+) +(?!sp\.)[a-z]+", r"\1 sp.", label)
    label = re.sub(r"\[Type; *outgroup\]", "[outgroup; species identity on hold]", label)
    label = re.sub(r"\[Type\]", "[species identity on hold]", label)
    return label


def bind_source_geography(rows: list[dict], bc3: dict[str, dict], corr: dict[tuple[str, str], str],
                          identity_holds: set[str]) -> list[str]:
    missing = []
    for row in rows:
        ident = (row.get("identifier") or row.get("tip") or "").strip()
        rec = bc3.get(ident)
        if rec is None:
            missing.append(ident)
            continue

        def resolve(field: str) -> str:
            override = corr.get((ident, field))
            if override == "__CLEARED__":
                return ""
            return override or _pick(rec, field)

        source, geo_raw, location = resolve("isolation_source"), resolve("geography"), resolve("location")
        row["source_display"] = source or NOT_RECORDED
        row["location_raw"] = location or NOT_RECORDED
        row["source_category"] = classify(source, SOURCE_RULES, "source", ident)
        row["geography_display"] = classify(geo_raw, GEO_RULES, "geography", ident)
        if ident in identity_holds:
            for col in ("label_concise", "label_experiment"):
                if row.get(col):
                    row[col] = apply_identity_hold(row[col])
        for corr_field, col in (("candida_call", "Candida"), ("mrsa_call", "MRSA")):
            if corr.get((ident, corr_field)) == "__CLEARED__":
                row[col] = ""      # withdrawn record: blank, never "n.t."
        row["metadata_status"] = "BOUND_FROM_VERIFIED_TABLE" + (
            "+OWNER_CORRECTION" if any(k[0] == ident for k in corr) else "")
    return missing


# ------------------------------------------------------------------------------------------------
def write_rows(path: Path, rows: list[dict], first_cols: list[str]) -> None:
    cols = list(first_cols)
    for row in rows:
        for key in row:
            if key not in cols:
                cols.append(key)
    for extra in ("Candida", "MRSA", "source_category", "location_raw", "metadata_status"):
        if extra not in cols:
            cols.append(extra)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=cols, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> int:
    _logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys_for_log.stdout)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--bc3")
    ap.add_argument("--corrections")
    ap.add_argument("--assay-table")
    ap.add_argument("--assembly-records")
    ap.add_argument("--omitted-tips")
    args = ap.parse_args(argv)

    src_dir, out_dir = Path(args.panel_dir), Path(args.out_dir)
    panel = src_dir.name
    rows = _read_tsv(src_dir / "figure_metadata.tsv")
    if not rows:
        raise BindError(f"{panel}: figure_metadata.tsv has no rows")
    first_cols = list(rows[0].keys())
    for row in rows:
        row.setdefault("Candida", "")
        row.setdefault("MRSA", "")
    out_dir.mkdir(parents=True, exist_ok=True)
    status_lines = [f"== {panel}: {len(rows)} tips =="]

    if args.bc3:
        holds: set[str] = set()
        corr = load_corrections(Path(args.corrections), panel, holds) if args.corrections else {}
        missing = bind_source_geography(rows, load_bc3(Path(args.bc3), panel), corr, holds)
        if missing:
            raise BindError(f"{len(missing)} tip(s) absent from the verified table for {panel}: {missing}")
        status_lines.append("source/geography bound from verified table")

    if args.assay_table:
        report = bind_assay_cells(rows, load_assay_table(args.assay_table), Path(args.assay_table).name)
        for strain, outcome in sorted(report.items()):
            status_lines.append(f"assay {strain}: {outcome}")

    if args.assembly_records:
        report = bind_reference_labels(rows, load_assembly_records(args.assembly_records))
        shutil.copy(args.assembly_records, out_dir / Path(args.assembly_records).name)
        n_type = sum(v == "Type" for v in report.values())
        status_lines.append(f"labels from Assembly records: {len(report)} references, {n_type} [Type], "
                            f"{sum(v == 'NO_ASSEMBLY_RECORD' for v in report.values())} without a record")

    if args.omitted_tips:
        receipt = read_receipt(args.omitted_tips)
        bound = {(r.get("identifier") or "").strip() for r in rows} | {(r.get("tip") or "").strip() for r in rows}
        clash = sorted({r["tip"] for r in receipt} & bound)
        if clash:
            raise BindError(f"OMIT_RECEIPT_CLASH: receipted as omitted but present in the panel: {clash}")
        shutil.copy(args.omitted_tips, out_dir / "omitted_tips.tsv")
        status_lines.append(f"omit receipt: {len(receipt)} row(s) copied to omitted_tips.tsv")

    write_rows(out_dir / "figure_metadata.tsv", rows, first_cols)
    _LOG.info("\n".join(status_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

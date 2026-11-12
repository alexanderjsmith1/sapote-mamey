#!/usr/bin/env python3
"""gap_rescue_join_runs.py — join finished gap-rescue runs of one locus against different reference records.

A gap_directed_rescue run searches one core region against one reference record. A locus with two good references
(for example a second MIBiG record for the same pathway family) needs two runs, one per record, each in its own
folder. This tool reads those folders and writes one table, so a card can show where every reference gene sits:

    python tools/gap_rescue_join_runs.py --run <run folder> --run <run folder> [--run ...] --out <new folder>

It refuses (exit 2), and writes nothing, when:
  - a folder has no readable receipt (a JSON object) or no gap_rescue.tsv rows (NOT_A_RUN);
  - the receipts' `core` (the four-part identity) or `label` differ (DIFFERENT_LOCUS, DIFFERENT_GENOME);
  - two receipts record different `inputs.zip_sha256` (DIFFERENT_GENOME);
  - one reference record appears twice: the same file name, the same stem or the same `inputs.reference_sha256`
    (SAME_REFERENCE_TWICE);
  - a gene table's rows do not line up with its run's gap_rescue.tsv (TABLE_MISMATCH);
  - --out is inside the bundle, is a file, or already holds a join (OUT_NOT_EMPTY).

A run made before receipts carried `inputs` has no ZIP checksum, so its genome cannot be compared byte for byte.
Such runs are still joined on locus and label, and runs.tsv says so in `genome_check`:
  - checked: every run recorded the same ZIP checksum;
  - not checked: one or more runs recorded no ZIP checksum.

Outputs in --out:
  - runs.tsv: one row per run: folder, reference record and name, input checksums, genome_check, and the run's own
    gene_table_counts.tsv values (a column the run did not write is blank).
  - reference_genes.tsv: one row per reference gene per run, with its status, its placement (in the region; same
    contig, outside the region; another contig; not found in this assembly), the best local protein and its region
    identity, the gene table's notes for that gene (edge crossing, shared protein, split, partner flags), and
    `also_best_for`: the other runs' reference genes whose best local protein is the same one. The gene table's short
    locus label ("BGC051, NODE_8 (core)") is not copied; every locus is named by its full four-part identity.

Nothing is added across runs. Each reference keeps its own counts: a fragmented cluster's numbers are estimates, and
two references of one family share genes, so a sum would count one protein twice. The table places genes; it does
not judge which reference fits better. Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

RUN_COLS = ("run", "reference", "reference_name", "reference_sha256", "zip", "zip_sha256", "genome_check",
            "reference_genes", "core", "core_proteins", "clear", "ambiguous", "not_found", "other", "set_aside", "split",
            "core_crossing")
GENE_COLS = ("identity", "reference", "reference_name", "reference_gene", "status", "placement", "best_locus",
             "best_identity_pct", "best_region_identity", "partner_verdict", "gene_table_notes", "also_best_for", "run")
OUTPUTS = ("runs.tsv", "reference_genes.tsv")


def _tsv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter="\t")]


def _notes(location: str) -> str:
    """The gene table's notes for a gene: its location text after the first ';', without the short locus label."""
    return location.split(";", 1)[1].strip() if ";" in location else ""


def read_run(folder: Path) -> dict:
    """The receipt, the per-gene rows, each row's gene-table notes and the counts of one run folder."""
    folder = Path(folder)
    try:
        receipt = json.loads((folder / "gap_rescue_receipt.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"NOT_A_RUN: {folder}: no readable gap_rescue_receipt.json ({type(exc).__name__})") from exc
    if not isinstance(receipt, dict) or not isinstance(receipt.get("inputs") or {}, dict):
        raise ValueError(f"NOT_A_RUN: {folder}: the receipt is not a JSON object with an object `inputs`")
    rows = _tsv(folder / "gap_rescue.tsv")
    if not rows:
        raise ValueError(f"NOT_A_RUN: {folder} has no gap_rescue.tsv rows")
    table = _tsv(folder / "gene_table.tsv")
    if table:
        # write_gene_table emits one row per gap_rescue.tsv row, in the same order; match by position, never by name,
        # and refuse when the two disagree (names are blank or repeated in some references).
        names = [(t.get("Reference gene") or "", r.get("name") or "") for t, r in zip(table, rows)]
        if len(table) != len(rows) or any(a and b and a != b for a, b in names):
            raise ValueError(f"TABLE_MISMATCH: {folder}: gene_table.tsv does not line up with gap_rescue.tsv")
    notes = [_notes(t.get("Location") or "") for t in table] if table else [""] * len(rows)
    counts = (_tsv(folder / "gene_table_counts.tsv") or [{}])[0]
    return {"folder": folder, "receipt": receipt, "rows": rows, "notes": notes, "counts": counts}


def _inputs(run: dict) -> dict:
    return run["receipt"].get("inputs") or {}


def check_same_locus(runs: list[dict]) -> str:
    """Raise ValueError unless every run describes the same locus on the same genome, once per reference.
    Returns the genome_check value for runs.tsv."""
    cores = {r["receipt"].get("core", "") for r in runs}
    labels = {r["receipt"].get("label", "") for r in runs}
    if len(cores) != 1 or "" in cores:
        raise ValueError("DIFFERENT_LOCUS: the receipts name " + "; ".join(sorted(map(str, cores))))
    if len(labels) != 1:
        raise ValueError("DIFFERENT_GENOME: the receipts' labels are " + ", ".join(sorted(map(str, labels))))
    zips = [_inputs(r).get("zip_sha256") or "" for r in runs]
    if len(set(zips) - {""}) > 1:
        raise ValueError("DIFFERENT_GENOME: the receipts record different antiSMASH ZIP checksums")
    for key, values in (("file name", [str(r["receipt"].get("reference", "")) for r in runs]),
                        ("stem", [Path(str(r["receipt"].get("reference", ""))).stem for r in runs]),
                        ("SHA-256", [_inputs(r).get("reference_sha256") or "" for r in runs])):
        twice = sorted({v for v in values if v and values.count(v) > 1})
        if twice:
            raise ValueError(f"SAME_REFERENCE_TWICE: the same reference {key} in two runs: " + ", ".join(twice))
    return "checked" if all(zips) else "not checked: one or more runs recorded no ZIP checksum"


def join(runs: list[dict], genome_check: str) -> tuple[list[dict], list[dict]]:
    """(runs.tsv rows, reference_genes.tsv rows) for runs already checked by check_same_locus."""
    best_for: dict[str, list[tuple[int, str]]] = {}
    for n, run in enumerate(runs):
        ref = Path(str(run["receipt"].get("reference", ""))).stem
        for r in run["rows"]:
            if r.get("best_locus") and r.get("status") != "MISSING_NOT_FOUND":
                best_for.setdefault(r["best_locus"], []).append((n, f"{ref}:{r.get('name', '')}"))
    run_rows, gene_rows = [], []
    for n, run in enumerate(runs):
        rec, inputs = run["receipt"], _inputs(run)
        ref = Path(str(rec.get("reference", ""))).stem
        parts = str(rec.get("core", "")).split(" / ")
        core_contig = parts[1] if len(parts) == 4 else ""
        run_rows.append({"run": str(run["folder"]), "reference": ref, "reference_name": rec.get("reference_name", ""),
                         "reference_sha256": inputs.get("reference_sha256") or "not recorded",
                         "zip": inputs.get("zip") or "not recorded",
                         "zip_sha256": inputs.get("zip_sha256") or "not recorded", "genome_check": genome_check,
                         **{k: run["counts"].get(k, "") for k in RUN_COLS[7:]}})
        for r, note in zip(run["rows"], run["notes"]):
            found = r.get("status") != "MISSING_NOT_FOUND" and r.get("best_locus")
            others = [label for m, label in best_for.get(r.get("best_locus", ""), []) if m != n]
            gene_rows.append({"identity": rec.get("core", ""), "reference": ref,
                              "reference_name": rec.get("reference_name", ""), "reference_gene": r.get("name", ""),
                              "status": r.get("status", ""), "placement": placement(r, core_contig),
                              "best_locus": r.get("best_locus", "") if found else "",
                              "best_identity_pct": r.get("best_identity_pct", "") if found else "",
                              "best_region_identity": r.get("best_region_identity", "") if found else "",
                              "partner_verdict": r.get("partner_verdict", ""), "gene_table_notes": note,
                              "also_best_for": "; ".join(others) if found else "", "run": str(run["folder"])})
    return run_rows, gene_rows


def placement(row: dict, core_contig: str) -> str:
    """Where the reference gene's best local protein sits, from the run's own status and contig."""
    status = row.get("status", "")
    if status == "PRESENT_IN_CORE":
        return "in the region"
    if status.startswith("MISSING_FOUND"):
        where = ("same contig, outside the region" if core_contig and row.get("best_contig") == core_contig
                 else "another contig")
        return where + ("; ambiguous" if status == "MISSING_FOUND_AMBIGUOUS" else "")
    if status == "MISSING_NOT_FOUND":
        return "not found in this assembly"
    return f"status {status.lower().replace('_', ' ')}" if status else ""


def _check_out(out: Path) -> None:
    bundle = Path(__file__).resolve().parents[1]
    resolved = out.resolve()
    if resolved == bundle or bundle in resolved.parents:
        raise ValueError("OUT_NOT_EMPTY: --out must lie outside the bundle")
    if out.exists() and not out.is_dir():
        raise ValueError(f"OUT_NOT_EMPTY: --out {out} is a file")
    if any((out / name).exists() for name in OUTPUTS):
        raise ValueError(f"OUT_NOT_EMPTY: --out {out} already holds a join; give a new folder")


def _write(path: Path, cols, rows) -> None:
    # Reference names and gene-table notes come from antiSMASH and GenBank text, so a cell that starts with = + - @
    # is neutralized the same way as every other bundle table writer.
    try:
        from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    except ImportError:
        import os as _cs_os, sys as _cs_sys
        _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
        from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=list(cols), delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="append", required=True, type=Path, help="a finished run folder (repeat, two or more)")
    ap.add_argument("--out", required=True, type=Path, help="a new output folder, outside the bundle")
    a = ap.parse_args(argv)
    if len(a.run) < 2:
        ap.error("give at least two --run folders")
    try:
        _check_out(a.out)
        runs = [read_run(f) for f in a.run]
        genome_check = check_same_locus(runs)
    except ValueError as exc:
        sys.stderr.write(f"REFUSED {exc}\n")
        return 2
    run_rows, gene_rows = join(runs, genome_check)
    a.out.mkdir(parents=True, exist_ok=True)
    _write(a.out / "runs.tsv", RUN_COLS, run_rows)
    _write(a.out / "reference_genes.tsv", GENE_COLS, gene_rows)
    sys.stderr.write(f"[gap_rescue_join_runs] {len(run_rows)} runs, {len(gene_rows)} reference genes "
                     f"(genome {genome_check}) -> {a.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

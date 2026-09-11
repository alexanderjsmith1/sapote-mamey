#!/usr/bin/env python3
"""tools/chitin_reference_eval.py -- operator front door for the whole-genome chitin/GlcNAc
reference-capacity evaluation (mamey/chitin_reference_eval.py).

Inputs:
  - A sealed package's CGAD scan output: by default read from <package>/manifest.json at
    source_scans.chitinase.counts (the field mamey/cli.py itself derives cgad_active from); or
    pass --cgad-json to point at any JSON file/object holding a "counts" dict directly (useful
    for testing or for a package whose manifest layout has moved).
  - --registry: an operator-supplied reference registry TSV. Columns: reference_id, taxon (or
    genus), source_path, source_sha256, and OPTIONAL ani_pct / aligned_fragment_fraction /
    chitin_domains_total. This tool never reads or redistributes the reference sequence itself --
    a row with no ani_pct types NOT_SCORED rather than being silently dropped or scored zero.
  - --strain-id / --taxon: override the package manifest's own strain_id/taxonomy when needed
    (e.g. --cgad-json input with no package to read them from).

Outputs (stdout is the receipt -- this tool's deliverable is what it prints):
  - default: the evaluation receipt as JSON on stdout.
  - --format tsv: a single-row TSV (one strain per invocation) on stdout.
  - --out-json / --out-tsv: also write the same content to a file (atomic write).
A typed refusal (bad input, unreadable package, malformed registry) goes to stderr via
sys.stderr.write and a non-zero exit; refusals are never printed to stdout mixed with the
receipt.

SCOPE: whole-genome, per-strain, independent of Mode B/BGC completion (workroom CHD-001/CHD-002)
-- this tool must never be wired into triage or scoring. See mamey/chitin_reference_eval.py for
the full scope/claim-ceiling docstring.

Tools/bin/python3, PYTHONDONTWRITEBYTECODE=1 house convention.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_dump_json, atomic_write_text

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
from mamey.chitin_reference_eval import evaluate_strain, ChitinReferenceEvalError


class Refusal(Exception):
    """Typed operator-facing refusal -- caught in main() and written to stderr, never stdout."""


def _load_cgad_counts_from_package(package_dir: str) -> tuple[dict, str, str]:
    manifest_path = os.path.join(package_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise Refusal(f"MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: no manifest.json under {package_dir}")
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: unreadable manifest.json: {exc}")
    strain_id = manifest.get("strain_id") or "NR"
    taxon = manifest.get("taxonomy") or manifest.get("display_name") or ""
    source_scans = manifest.get("source_scans") or {}
    chitinase = source_scans.get("chitinase") or {}
    counts = chitinase.get("counts")
    if counts is None:
        raise Refusal(
            "MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: manifest.json has no source_scans.chitinase.counts "
            "-- this package was not run with the CGAD scan, or its manifest schema has moved")
    return counts, strain_id, taxon


def _load_cgad_counts_from_json(path: str) -> dict:
    if not os.path.isfile(path):
        raise Refusal(f"MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: --cgad-json not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: unreadable --cgad-json: {exc}")
    counts = data.get("counts", data) if isinstance(data, dict) else None
    if not isinstance(counts, dict):
        raise Refusal("MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: --cgad-json has no usable counts dict")
    return counts


def _load_registry(path: str) -> list[dict[str, str]]:
    if not os.path.isfile(path):
        raise Refusal(f"MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: --registry not found: {path}")
    try:
        with open(path, "r", newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
    except OSError as exc:
        raise Refusal(f"MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: unreadable --registry: {exc}")
    if not rows:
        raise Refusal(f"MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: --registry is empty: {path}")
    return rows


def _to_tsv_row(evaluation) -> str:
    d = evaluation.to_dict()
    p = d["profile"]
    top = d["top_reference"] or {}
    fields = [
        "strain_id", "architecture_state", "domains_total", "reference_panel_n",
        "reference_quality", "top_reference_id", "top_ani_pct",
        "top_aligned_fragment_fraction", "claim_ceiling",
    ]
    values = [
        d["strain_id"], p["architecture_state"], str(p["domains_total"]),
        str(d["reference_panel_n"]), d["reference_quality"],
        top.get("reference_id", "NR"),
        "" if top.get("ani_pct") is None else str(top["ani_pct"]),
        "" if top.get("aligned_fragment_fraction") is None else str(top["aligned_fragment_fraction"]),
        d["claim_ceiling"],
    ]
    out = [fields, values]
    buf = []
    for row in out:
        buf.append("\t".join(str(v).replace("\t", " ").replace("\n", " ") for v in row))
    return "\n".join(buf) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--package", help="sealed package directory (reads manifest.json)")
    src.add_argument("--cgad-json", help="JSON file with a CGAD counts dict (testing/override)")
    ap.add_argument("--registry", required=True, help="operator-supplied reference registry TSV")
    ap.add_argument("--strain-id", default=None, help="override the strain id")
    ap.add_argument("--taxon", default=None, help="override the taxon used for registry matching")
    ap.add_argument("--genus-alias", action="append", default=[],
                     help="additional taxon alias to match in the registry (repeatable)")
    ap.add_argument("--format", choices=["json", "tsv"], default="json")
    ap.add_argument("--out-json", default=None, help="also write the JSON receipt to this path")
    ap.add_argument("--out-tsv", default=None, help="also write the TSV row to this path")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_arg_parser()
    ns = ap.parse_args(argv)
    try:
        if ns.package:
            counts, manifest_strain_id, manifest_taxon = _load_cgad_counts_from_package(ns.package)
        else:
            counts, manifest_strain_id, manifest_taxon = _load_cgad_counts_from_json(ns.cgad_json), "NR", ""
        strain_id = ns.strain_id or manifest_strain_id
        taxon = ns.taxon if ns.taxon is not None else manifest_taxon
        if strain_id in (None, "", "NR") and ns.strain_id is None:
            raise Refusal(
                "MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: no strain_id available from the package "
                "manifest -- pass --strain-id")
        registry_rows = _load_registry(ns.registry)
        evaluation = evaluate_strain(strain_id, counts, registry_rows, taxon, ns.genus_alias)
    except Refusal as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1
    except ChitinReferenceEvalError as exc:
        sys.stderr.write(f"MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL: {exc}\n")
        return 1

    if ns.format == "tsv":
        payload = _to_tsv_row(evaluation)
    else:
        payload = json.dumps(evaluation.to_dict(), indent=2) + "\n"
    sys.stdout.write(payload)

    if ns.out_json:
        atomic_dump_json(evaluation.to_dict(), ns.out_json, indent=2)
    if ns.out_tsv:
        atomic_write_text(ns.out_tsv, _to_tsv_row(evaluation))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

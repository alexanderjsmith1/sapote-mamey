#!/usr/bin/env python3
"""tools/npatlas_provision.py -- operator front door for user-provisioned NP Atlas ingestion
(mamey/npatlas_provision.py). Implements steps 1-3 of the NP Atlas provisioning/structure-display
audit (NPA-01..NPA-04); Tanimoto similarity and ChemSpider link-out (steps 4/5) are owner-gated
and NOT in this tool.

Subcommands
-----------
  inspect   -- read-only streamed preview of a source file: hash, bytes, record count, a small
               sample of records' keys. Never writes anything.
  provision -- stream the source, apply a declarative filter, write a content-addressed filtered
               output plus a receipt (source hash, licence, filter rule, counts, output hash).
  doctor    -- report whether streaming (ijson) and structure rendering (rdkit) are available in
               this environment, plus the NP Atlas dataset's own provisioning status.

This tool never assumes a personal directory and never redistributes the source dataset --
`provision` writes only the operator-named --out file, which contains only the records the
operator's own filter selected from a file the operator supplied.

stdout is the deliverable: the receipt/report as JSON (or --format tsv for `provision`). A typed
refusal goes to stderr (prefixed NPATLAS_PROVISION_REFUSAL:) and exits non-zero; the two streams
are never mixed.

Tools/bin/python3, PYTHONDONTWRITEBYTECODE=1 house convention.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_dump_json, atomic_write_text

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
from mamey.npatlas_provision import (
    NpatlasProvisionError,
    FilterClause,
    clause_from_dict,
    doctor_report,
    inspect_source,
    load_predicate_file,
    provision,
)


class Refusal(Exception):
    """Typed operator-facing refusal -- caught in main() and written to stderr, never stdout."""


def _build_clauses(ns: argparse.Namespace) -> list[FilterClause]:
    clauses: list[FilterClause] = []
    if ns.origin_type:
        clauses.append(clause_from_dict({"field": "origin_type", "op": "in", "value": ns.origin_type}))
    if ns.taxon_contains:
        field_name = ns.taxon_field or "origin_taxon"
        for t in ns.taxon_contains:
            clauses.append(clause_from_dict({"field": field_name, "op": "icontains", "value": t}))
    if ns.genus:
        clauses.append(clause_from_dict({"field": ns.genus_field or "genus", "op": "in", "value": ns.genus}))
    if getattr(ns, "phylum", None):
        # CLAUDE_409: select on the synthetic scalar `phylum` field that --normalize derives from the
        # nested origin_organism.taxon.ancestors[]. One `in` clause over the allowlist -- so the actino
        # split is `--phylum Actinobacteria --phylum Actinomycetota` (an OR), not the impossible AND of
        # two --taxon-contains clauses the shipped recipe produced. Requires --normalize (enforced in main).
        clauses.append(clause_from_dict({"field": "phylum", "op": "in", "value": ns.phylum}))
    if ns.predicate_file:
        try:
            clauses.extend(load_predicate_file(ns.predicate_file))
        except NpatlasProvisionError as exc:
            raise Refusal(str(exc))
    return clauses


def _to_tsv_row(receipt_dict: dict) -> str:
    fields = ["source_path", "source_sha256", "source_bytes", "dataset_version", "licence_id",
              "included_count", "excluded_count", "output_path", "output_sha256", "normalized",
              "tool_version"]
    values = [str(receipt_dict.get(f, "")) for f in fields]
    rows = [fields, values]
    return "\n".join("\t".join(v.replace("\t", " ").replace("\n", " ") for v in row) for row in rows) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="read-only streamed preview of a source file")
    p_inspect.add_argument("--source", required=True, help="NP Atlas .json or .sdf file (operator-supplied)")
    p_inspect.add_argument("--json-root", default=None, help="override the ijson root prefix (default: auto-detected)")
    p_inspect.add_argument("--sample-limit", type=int, default=5)
    p_inspect.add_argument("--out-json", default=None, help="also write the inspect report to this path")

    p_prov = sub.add_parser("provision", help="stream, filter, and write a content-addressed subset + receipt")
    p_prov.add_argument("--source", required=True, help="NP Atlas .json or .sdf file (operator-supplied)")
    p_prov.add_argument("--out", required=True, help="output path for the filtered subset (JSON)")
    p_prov.add_argument("--json-root", default=None, help="override the ijson root prefix (default: auto-detected)")
    p_prov.add_argument("--dataset-version", default="unknown", help="the NP Atlas release version the operator downloaded (e.g. v2024_09)")
    p_prov.add_argument("--origin-type", action="append", default=[], help="keep only these origin_type values (repeatable)")
    p_prov.add_argument("--taxon-contains", action="append", default=[], help="keep records whose taxon field contains this substring, case-insensitive (repeatable)")
    p_prov.add_argument("--taxon-field", default=None, help="dotted field name for --taxon-contains (default: origin_taxon)")
    p_prov.add_argument("--genus", action="append", default=[], help="keep only these genus values (repeatable, allowlist)")
    p_prov.add_argument("--genus-field", default=None, help="dotted field name for --genus (default: genus)")
    p_prov.add_argument("--normalize", action="store_true", help="remap each raw NP Atlas v2024_09 record onto the schema the resolver reads (name/reference/npclassifier.class + a synthetic scalar `phylum`) BEFORE filtering and writing; required for a provision the resolver can load (verbatim output builds an EMPTY index)")
    p_prov.add_argument("--phylum", action="append", default=[], help="keep records whose derived phylum is in this allowlist, e.g. --phylum Actinobacteria --phylum Actinomycetota (repeatable, OR); implies --normalize")
    p_prov.add_argument("--predicate-file", default=None, help="a JSON file of additional declarative filter clauses (ANDed with the above)")
    p_prov.add_argument("--format", choices=["json", "tsv"], default="json")
    p_prov.add_argument("--out-receipt", default=None, help="also write the receipt to this path (same format as stdout)")

    sub.add_parser("doctor", help="report streaming/rendering readiness and dataset provisioning status")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_arg_parser()
    ns = ap.parse_args(argv)
    try:
        if ns.command == "inspect":
            report = inspect_source(ns.source, root_prefix=ns.json_root, sample_limit=ns.sample_limit)
            payload = json.dumps(report, indent=2, default=str) + "\n"
            sys.stdout.write(payload)
            if ns.out_json:
                atomic_dump_json(report, ns.out_json, indent=2)
            return 0

        if ns.command == "provision":
            clauses = _build_clauses(ns)
            # --phylum selects on the synthetic scalar field normalization derives, so it implies
            # --normalize (a --phylum filter over verbatim records would match nothing).
            normalize = bool(ns.normalize or ns.phylum)
            receipt = provision(ns.source, ns.out, clauses, root_prefix=ns.json_root,
                                 dataset_version=ns.dataset_version, normalize=normalize)
            d = receipt.to_dict()
            payload = _to_tsv_row(d) if ns.format == "tsv" else (json.dumps(d, indent=2) + "\n")
            sys.stdout.write(payload)
            if ns.out_receipt:
                if ns.format == "tsv":
                    atomic_write_text(ns.out_receipt, _to_tsv_row(d))
                else:
                    atomic_dump_json(d, ns.out_receipt, indent=2)
            return 0

        if ns.command == "doctor":
            report = doctor_report()
            sys.stdout.write(json.dumps(report, indent=2) + "\n")
            return 0

        raise Refusal(f"NPATLAS_PROVISION_REFUSAL: unknown command {ns.command!r}")
    except Refusal as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1
    except NpatlasProvisionError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

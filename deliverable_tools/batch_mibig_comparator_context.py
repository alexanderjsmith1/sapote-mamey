#!/usr/bin/env python3
"""Create additive comparator-context copies of a per-strain HTML report tree."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bigscape_network_widget import enhance_mibig_summary, sha256


def build(report_root, out_root, mibig_json_dir, curated_context=None, receipt_out=None, component_context=None):
    source_root = Path(report_root).resolve()
    destination_root = Path(out_root).resolve()
    if not source_root.is_dir():
        raise ValueError("MIBIG_BATCH_GATE: report root must be a directory")
    if destination_root == source_root or source_root in destination_root.parents:
        raise ValueError("MIBIG_BATCH_GATE: output must be outside the authoritative report root")
    sources = sorted(source_root.rglob("REPORT.html"))
    if not sources:
        raise ValueError("MIBIG_BATCH_GATE: no REPORT.html inputs found")
    staged = []
    for source in sources:
        relative = source.relative_to(source_root)
        enhanced, context_receipt = enhance_mibig_summary(
            source.read_text(encoding="utf-8"), mibig_json_dir, curated_context, component_context,
        )
        staged.append((source, relative, enhanced, context_receipt))
    records = []
    for source, relative, enhanced, context_receipt in staged:
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(enhanced, encoding="utf-8")
        records.append({
            "source_locator": relative.as_posix(),
            "source_sha256": sha256(source),
            "output_locator": relative.as_posix(),
            "output_sha256": sha256(destination),
            "rows": context_receipt["rows"],
            "unique_comparators": context_receipt["unique_comparators"],
            "activity_verified_context_rows": context_receipt["activity_verified_context_rows"],
            "mechanism_verified_context_rows": context_receipt["mechanism_verified_context_rows"],
            "no_admitted_comparator_rows": context_receipt["no_admitted_comparator_rows"],
            "comparator_context_unresolved_rows": context_receipt["comparator_context_unresolved_rows"],
            "component_bound_rows": context_receipt["component_bound_rows"],
        })
    receipt = {
        "status": "PASS", "report_count": len(records), "authoritative_inputs_mutated": False,
        "source_root_role": "authoritative per-strain report tree (read-only)",
        "output_root_role": "additive comparator-context report copies",
        "records": records,
    }
    receipt_path = Path(receipt_out) if receipt_out else destination_root / "MIBIG_COMPARATOR_CONTEXT_BATCH_RECEIPT.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--mibig-json-dir", required=True)
    parser.add_argument("--curated-comparator-context")
    parser.add_argument("--comparator-component-context")
    parser.add_argument("--receipt-out")
    args = parser.parse_args(argv)
    try:
        receipt = build(
            args.report_root, args.out_root, args.mibig_json_dir,
            args.curated_comparator_context, args.receipt_out, args.comparator_component_context,
        )
    except ValueError as error:
        raise SystemExit(str(error))
    print(json.dumps({"status": receipt["status"], "report_count": receipt["report_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

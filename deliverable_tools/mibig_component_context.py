#!/usr/bin/env python3
"""Derive a provenance-bound coherent-component view of a broad antiSMASH region.

The whole-region matched-CDS fraction is retained. A local denominator is added only
when comparator-matched genes form a coherent order block; this may support a pathway-
family interpretation, but never raises product, activity, or mechanism certainty.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

CLAIM_CEILING = (
    "Component-aware match density and core-marker presence support pathway-family context only. "
    "They do not establish exact product, pathway boundaries, completeness, expression, production, "
    "activity, mechanism, novelty, or release eligibility."
)
FIELDS = [
    "complete_identity", "mibig_accession", "whole_region_matched_cds",
    "whole_region_total_cds", "coherent_block_start_gene_order",
    "coherent_block_end_gene_order", "coherent_block_matched_cds",
    "local_component_denominator", "local_component_hit_fraction",
    "matched_cds_outside_selected_block", "gene_order_status",
    "core_completeness_status", "component_interpretation", "segmentation_hold",
    "evidence_source", "evidence_sha256", "claim_ceiling",
]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tsv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_tsv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _clusters(positions, max_unmatched_gap=2):
    clusters = []
    for position in positions:
        if not clusters or position - clusters[-1][-1] > max_unmatched_gap + 1:
            clusters.append([position])
        else:
            clusters[-1].append(position)
    return clusters


def _has_token(row, token):
    text = " ".join(str(row.get(field) or "") for field in (
        "primary_functional_role", "functional_logic_tags", "product_annotation",
        "sec_met_domains", "gene_functions",
    )).casefold()
    return re.search(token, text) is not None


def derive(rows, identity, accession, evidence_source, evidence_hash):
    selected = [row for row in rows if str(row.get("complete_identity") or "").strip() == identity]
    if not selected:
        raise ValueError("MIBIG_COMPONENT_GATE: complete identity is absent from functional evidence")
    orders = sorted(int(row["gene_order"]) for row in selected)
    if orders != list(range(1, len(selected) + 1)):
        raise ValueError("MIBIG_COMPONENT_GATE: gene_order must be unique and contiguous from 1")
    matched = sorted(
        int(row["gene_order"]) for row in selected
        if str(row.get("dominant_reference_gene_match") or "").strip() == "YES"
        and str(row.get("dominant_mibig_accession") or "").strip() == accession
    )
    if not matched:
        raise ValueError("MIBIG_COMPONENT_GATE: selected comparator has no matched CDS")
    cluster = max(_clusters(matched), key=lambda values: (len(values), -(values[-1] - values[0])))
    start, end = cluster[0], cluster[-1]
    denominator = end - start + 1
    local_fraction = len(cluster) / denominator
    core_positions = {}
    core_patterns = {
        "T2PKS_KS": r"(?:\bt2ks\b|\bks \(score)",
        "T2PKS_CLF": r"(?:\bt2clf\b|\bclf )",
        "ACP": r"t2pks\)\s+acp\s+\(",
    }
    for label, pattern in core_patterns.items():
        core_positions[label] = [int(row["gene_order"]) for row in selected if _has_token(row, pattern)]
    detected = sum(bool(values) for values in core_positions.values())
    all_outside = detected == 3 and all(
        all(position < start or position > end for position in values)
        for values in core_positions.values()
    )
    core_status = f"MINIMAL_T2PKS_CORE_{detected}_OF_3_PRESENT"
    if all_outside:
        core_status += "_OUTSIDE_SELECTED_COMPARATOR_BLOCK"
    outside = len(matched) - len(cluster)
    segmentation_hold = (
        "OVERMERGED_REGION_COMPONENT_BOUNDARIES_REQUIRE_REVIEW"
        if denominator < len(selected) or outside else "NO_SEGMENTATION_HOLD"
    )
    gene_order_status = (
        f"COHERENT_{len(cluster)}_OF_{denominator}_BLOCK"
        + (f"_PLUS_{outside}_OUTLIER" if outside else "")
    )
    return {
        "complete_identity": identity,
        "mibig_accession": accession,
        "whole_region_matched_cds": str(len(matched)),
        "whole_region_total_cds": str(len(selected)),
        "coherent_block_start_gene_order": str(start),
        "coherent_block_end_gene_order": str(end),
        "coherent_block_matched_cds": str(len(cluster)),
        "local_component_denominator": str(denominator),
        "local_component_hit_fraction": f"{local_fraction:.6f}",
        "matched_cds_outside_selected_block": str(outside),
        "gene_order_status": gene_order_status,
        "core_completeness_status": core_status,
        "component_interpretation": "COMPONENT_SUPPORTED_PATHWAY_FAMILY_CONTEXT_ONLY",
        "segmentation_hold": segmentation_hold,
        "evidence_source": evidence_source,
        "evidence_sha256": evidence_hash,
        "claim_ceiling": CLAIM_CEILING,
    }


def build(evidence_tsv, identity, accession, evidence_extract, out, evidence_locator):
    if not re.fullmatch(r"BGC\d{7}", accession):
        raise ValueError("MIBIG_COMPONENT_GATE: invalid MIBiG accession")
    rows = read_tsv(evidence_tsv)
    selected = [row for row in rows if str(row.get("complete_identity") or "").strip() == identity]
    if not selected:
        raise ValueError("MIBIG_COMPONENT_GATE: requested complete identity is absent")
    write_tsv(evidence_extract, selected, list(selected[0]))
    row = derive(selected, identity, accession, evidence_locator, sha256(evidence_extract))
    write_tsv(out, [row], FIELDS)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-tsv", required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--mibig-accession", required=True)
    parser.add_argument("--evidence-extract", required=True)
    parser.add_argument("--evidence-locator", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        row = build(args.evidence_tsv, args.identity, args.mibig_accession, args.evidence_extract, args.out, args.evidence_locator)
    except ValueError as error:
        raise SystemExit(str(error))
    sys.stdout.write(json.dumps(row, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

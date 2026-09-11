"""Normalize preliminary MiBIG/KCB and ClusterBlast per-gene evidence.

The adapter is deliberately sequence-first and fail-closed.  A locus-tag join
to a current exact-region inventory is useful routing evidence, but it is not a
submitted-query receipt and does not make a historical comparator run current.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path


COMPARATOR_FORMATS = {
    "MIBIG_PER_GENE_CSV": {
        "bgc_id", "query_gene", "subject_gene", "mibig_accession",
        "mibig_compound", "pct_identity", "pct_coverage",
    },
    "CLUSTERBLAST_PER_GENE_CSV": {
        "bgc_id", "query_gene", "subject_gene", "pct_identity", "pct_coverage",
    },
}

COMPARATOR_OUTPUT_FIELDS = [
    "comparator_channel", "source_scoped_bgc_alias", "query_gene", "subject_gene",
    "reference_accession", "reference_name", "reference_type", "pct_identity",
    "source_pct_coverage", "usable_pct_coverage", "coverage_state", "score", "evalue",
    "reference_rank", "reference_label", "exact_current_protein_sha256",
    "exact_current_aa_length", "query_join_state", "evidence_state",
]


def read_comparator_source(path: Path, source_format: str) -> list[dict[str, str]]:
    """Read and minimally validate a supported per-gene comparator table."""
    required = COMPARATOR_FORMATS.get(source_format)
    if required is None:
        raise ValueError(f"Unsupported comparator format: {source_format!r}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"Comparator source {path.name} missing columns: {missing}")
        rows = [dict(row) for row in reader]
        # `None in row` (dict keys) only catches a row with TOO MANY columns (csv.DictReader
        # collects the overflow under the restkey, which defaults to None). A row with TOO FEW
        # columns fills the missing fields with `restval` (also None by default) under their
        # normal field-name keys, so it produced no None *key* and slipped past this guard,
        # despite the module's fail-closed design intent. Check values too.
        if any(None in row or None in row.values() for row in rows):
            raise ValueError(f"Malformed comparator source: {path}")
    return rows


def coverage_state(raw: str, source_flag: str = "") -> tuple[str, str]:
    """Return usable coverage and a state without capping suspect values."""
    if raw == "":
        return "", "COVERAGE_MISSING"
    try:
        value = float(raw)
    except ValueError:
        return "", "COVERAGE_UNPARSEABLE_HOLD"
    # v97396 fix: float() accepts the string "nan" (any case), but every comparison against NaN
    # is False under IEEE 754 semantics, so it silently passed both the >100 and <0 guards below
    # and was reported as "WITHIN_EXPECTED_RANGE" -- the same failure shape as the malformed-row
    # gap already fixed in read_comparator_source() above, this module's own documented
    # fail-closed design intent notwithstanding. A NaN sentinel is not a number; hold it as
    # unparseable, same as any other non-numeric value.
    if math.isnan(value):
        return "", "COVERAGE_UNPARSEABLE_HOLD"
    if value > 100 or source_flag.startswith("SOURCE_GT100"):
        return "", "SOURCE_GT100_HOLD_DENOMINATOR_OR_HSP_AGGREGATE_UNRESOLVED"
    if value < 0:
        return "", "COVERAGE_NEGATIVE_INVALID"
    return raw, "WITHIN_EXPECTED_RANGE_SOURCE_REPORTED"


def normalize_comparator_children(
    rows: list[dict[str, str]], *, source_format: str, alias: str,
    exact_genes: dict[str, dict[str, object]],
) -> list[dict[str, str]]:
    """Return alias-filtered child rows joined only to exact-region gene labels."""
    if source_format not in COMPARATOR_FORMATS:
        raise ValueError(f"Unsupported comparator format: {source_format!r}")
    out: list[dict[str, str]] = []
    for row in rows:
        if row.get("bgc_id") != alias:
            continue
        usable, cov_state = coverage_state(
            row.get("pct_coverage", ""), row.get("coverage_qc_flag", "")
        )
        query_gene = row.get("query_gene", "")
        exact = exact_genes.get(query_gene)
        if source_format == "MIBIG_PER_GENE_CSV":
            channel = "MIBIG_KNOWNCLUSTERBLAST"
            accession = row.get("mibig_accession", "")
            name = row.get("mibig_compound", "")
            reference_type = row.get("reference_type", "")
            reference_label = row.get("reference", "")
            score = row.get("blast_score", "")
        else:
            channel = "CLUSTERBLAST"
            accession = ""
            name = row.get("reference", "")
            reference_type = row.get("reference_source", "")
            reference_label = row.get("reference", "")
            score = row.get("blast_score", "")
        out.append({
            "comparator_channel": channel,
            "source_scoped_bgc_alias": alias,
            "query_gene": query_gene,
            "subject_gene": row.get("subject_gene", ""),
            "reference_accession": accession,
            "reference_name": name,
            "reference_type": reference_type,
            "pct_identity": row.get("pct_identity", ""),
            "source_pct_coverage": row.get("pct_coverage", ""),
            "usable_pct_coverage": usable,
            "coverage_state": cov_state,
            "score": score,
            "evalue": row.get("evalue", ""),
            "reference_rank": row.get("reference_rank", ""),
            "reference_label": reference_label,
            "exact_current_protein_sha256": str(exact.get("protein_sha256", "")) if exact else "",
            "exact_current_aa_length": str(exact.get("aa_length", "")) if exact else "",
            "query_join_state": (
                "LOCUS_TAG_IN_EXACT_REGION_QUERY_BYTES_UNBOUND"
                if exact else "QUERY_LABEL_OUTSIDE_EXACT_REGION_OR_GENE_MODEL_MISMATCH"
            ),
            "evidence_state": "PRELIMINARY_SOURCE_BOUND_QUERY_AND_RUN_RECEIPTS_UNBOUND",
        })
    return out

"""Build a post-seal evidence packet for genes sparsely represented in named BGC references.

The command is deterministic and report-only.  It identifies low-reference-match genes,
keeps nr and ClusteredNR annotations separate, groups consecutive genes for human review,
and emits an additive Markdown scaffold.  It never assigns pathway membership or a gene
function automatically.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import BUNDLE_VERSION
from .csv_safety import SafeDictWriter
from .mode_b.gene_first_explore import (
    GeneFirstHold,
    _one_gene_table,
    load_gene_rows,
    resolve_identity,
)

SCHEMA = "mamey_unmatched_gene_addendum_v1"
CLAIM_CEILING = (
    "Reference sparsity and gene neighborhood are review cues only. They do not establish "
    "pathway membership, biochemical function, product identity, expression, production, "
    "bioactivity, novelty, or scientific acceptance."
)

EVIDENCE_FIELDS = (
    "exact_identity", "gene_order", "locus_tag", "aa_length", "strand",
    "product_qualifier", "gene_function_inference", "sec_met_domains",
    "selected_reference_match_count", "selected_reference_count", "reference_match_state",
    "nr_evidence_state", "nr_subject", "clustered_nr_evidence_state",
    "clustered_nr_subject", "neighborhood_id", "possible_function",
    "alternative_explanation", "pathway_relevance_tier", "discriminating_test",
)
NEIGHBORHOOD_FIELDS = (
    "exact_identity", "neighborhood_id", "first_gene_order", "last_gene_order",
    "first_locus_tag", "last_locus_tag", "gene_count", "locus_tags",
    "review_state", "claim_ceiling",
)
ADJUDICATION_FIELDS = (
    "exact_identity", "locus_tag", "possible_function", "alternative_explanation",
    "pathway_relevance_tier", "discriminating_test",
)


class UnmatchedGeneAddendumHold(ValueError):
    """Typed refusal for identity, evidence, or output-contract defects."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise


def _safe_token(identity: Mapping[str, str]) -> str:
    token = "__".join(
        re.sub(r"[^A-Za-z0-9_.-]+", "_", identity[key])
        for key in ("strain", "full_node", "region", "bgc_alias")
    )
    if len(token) > 180:
        raise UnmatchedGeneAddendumHold(
            "UNMATCHED_GENE_OUTPUT_HOLD: exact identity is too long for portable filenames"
        )
    return token


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise UnmatchedGeneAddendumHold(
            f"UNMATCHED_GENE_SOURCE_HOLD: input is not a file: {path.name}"
        )
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            fields = list(reader.fieldnames or [])
            rows = [dict(row) for row in reader]
    except (OSError, csv.Error) as exc:
        raise UnmatchedGeneAddendumHold(
            f"UNMATCHED_GENE_SOURCE_HOLD: cannot read {path.name}"
        ) from exc
    if not fields:
        raise UnmatchedGeneAddendumHold(
            f"UNMATCHED_GENE_SOURCE_HOLD: {path.name} has no header"
        )
    return fields, rows


def _one_mibig_table(package: Path, explicit: str | Path | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise UnmatchedGeneAddendumHold(
                "UNMATCHED_GENE_SOURCE_HOLD: --mibig-per-gene is not a file"
            )
        return path
    matches = sorted(package.glob("*_3_mibig_per_gene.csv"))
    if len(matches) != 1:
        raise UnmatchedGeneAddendumHold(
            "UNMATCHED_GENE_SOURCE_HOLD: expected exactly one *_3_mibig_per_gene.csv"
        )
    return matches[0]


def _ordered_gene_rows(rows: list[dict[str, str]]) -> list[tuple[dict[str, str], int]]:
    """Return genomic order; ``rank`` is deliberately ignored because it is a BGC rank."""
    explicit = []
    for row in rows:
        value = str(row.get("gene_order") or row.get("order") or "").strip()
        try:
            explicit.append(int(float(value)))
        except ValueError:
            explicit.append(None)
    if all(value is not None for value in explicit) and len(set(explicit)) == len(rows):
        sorted_rows = [row for _order, row in sorted(zip(explicit, rows), key=lambda pair: pair[0])]
    else:
        starts = []
        for index, row in enumerate(rows):
            try:
                starts.append((int(float(str(row.get("cds_start") or ""))), index, row))
            except ValueError:
                starts.append((index, index, row))
        sorted_rows = [row for _start, _index, row in sorted(starts)]
    return [(row, index) for index, row in enumerate(sorted_rows, 1)]


def _strand(row: Mapping[str, str]) -> str:
    value = str(row.get("strand") or "").strip()
    return {"1": "+", "+1": "+", "-1": "-"}.get(value, value or "UNAVAILABLE")


def _load_mibig_counts(
    path: Path, bgc_alias: str, known_genes: set[str], selected_accessions: set[str]
) -> tuple[dict[str, set[str]], set[str]]:
    fields, rows = _read_rows(path)
    required = {"bgc_id", "query_gene", "mibig_accession"}
    if not required <= set(fields):
        raise UnmatchedGeneAddendumHold(
            f"UNMATCHED_GENE_SOURCE_HOLD: MIBiG table missing {sorted(required-set(fields))}"
        )
    target = [row for row in rows if str(row.get("bgc_id") or "").strip().upper() == bgc_alias]
    all_accessions = {
        str(row.get("mibig_accession") or "").strip() for row in target
        if str(row.get("mibig_accession") or "").strip()
    }
    chosen = selected_accessions or all_accessions
    if selected_accessions and not selected_accessions <= all_accessions:
        missing = sorted(selected_accessions - all_accessions)
        raise UnmatchedGeneAddendumHold(
            f"UNMATCHED_GENE_REFERENCE_HOLD: selected accessions absent from target evidence: {missing}"
        )
    matches: dict[str, set[str]] = defaultdict(set)
    for row in target:
        gene = str(row.get("query_gene") or "").strip()
        accession = str(row.get("mibig_accession") or "").strip()
        if not gene or gene not in known_genes:
            if gene:
                raise UnmatchedGeneAddendumHold(
                    f"UNMATCHED_GENE_IDENTITY_HOLD: MIBiG query gene is outside target roster: {gene}"
                )
            continue
        if accession in chosen:
            matches[gene].add(accession)
    return matches, chosen


def _normalized_channel(path: Path | None, channel: str, identity: str, known: set[str]) -> dict[str, tuple[str, str]]:
    if path is None:
        return {}
    fields, rows = _read_rows(path)
    gene_field = next((name for name in ("gene", "locus_tag", "query_gene") if name in fields), None)
    subject_field = next((name for name in ("subject_def", "subject_name", "description", "top_hit") if name in fields), None)
    if not gene_field or not subject_field:
        raise UnmatchedGeneAddendumHold(
            f"UNMATCHED_GENE_SOURCE_HOLD: {channel} table lacks gene or subject field"
        )
    if "exact_identity" in fields:
        foreign = sorted({str(r.get("exact_identity") or "").strip() for r in rows if str(r.get("exact_identity") or "").strip() != identity})
        if foreign:
            raise UnmatchedGeneAddendumHold(
                f"UNMATCHED_GENE_IDENTITY_HOLD: {channel} exact identity conflicts"
            )
    result: dict[str, tuple[str, str]] = {}
    for row in rows:
        gene = str(row.get(gene_field) or "").strip()
        if not gene:
            continue
        if gene not in known:
            raise UnmatchedGeneAddendumHold(
                f"UNMATCHED_GENE_IDENTITY_HOLD: {channel} gene is outside target roster: {gene}"
            )
        if gene in result:
            raise UnmatchedGeneAddendumHold(
                f"UNMATCHED_GENE_SOURCE_HOLD: duplicate {channel} gene: {gene}"
            )
        subject = str(row.get(subject_field) or "").strip()
        result[gene] = ("BOUND" if subject else "BOUND_NO_DESCRIPTION", subject or "UNAVAILABLE")
    return result


def _load_adjudication(path: Path | None, identity: str, eligible: set[str]) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    fields, rows = _read_rows(path)
    if set(fields) != set(ADJUDICATION_FIELDS):
        raise UnmatchedGeneAddendumHold(
            "UNMATCHED_GENE_ADJUDICATION_HOLD: adjudication schema mismatch"
        )
    result = {}
    for row in rows:
        if str(row.get("exact_identity") or "").strip() != identity:
            raise UnmatchedGeneAddendumHold(
                "UNMATCHED_GENE_ADJUDICATION_HOLD: exact identity conflict"
            )
        gene = str(row.get("locus_tag") or "").strip()
        if gene not in eligible or gene in result:
            raise UnmatchedGeneAddendumHold(
                f"UNMATCHED_GENE_ADJUDICATION_HOLD: ineligible or duplicate locus tag: {gene}"
            )
        if any(not str(row.get(field) or "").strip() for field in ADJUDICATION_FIELDS[2:]):
            raise UnmatchedGeneAddendumHold(
                f"UNMATCHED_GENE_ADJUDICATION_HOLD: blank judgment field for {gene}"
            )
        result[gene] = dict(row)
    return result


def _group_rows(rows: list[dict[str, str]], identity: str, max_order_gap: int) -> list[dict[str, str]]:
    groups: list[list[dict[str, str]]] = []
    for row in rows:
        if not groups or int(row["gene_order"]) - int(groups[-1][-1]["gene_order"]) > max_order_gap:
            groups.append([row])
        else:
            groups[-1].append(row)
    output = []
    for index, group in enumerate(groups, 1):
        group_id = f"UGN{index:03d}"
        for row in group:
            row["neighborhood_id"] = group_id
        output.append({
            "exact_identity": identity,
            "neighborhood_id": group_id,
            "first_gene_order": group[0]["gene_order"],
            "last_gene_order": group[-1]["gene_order"],
            "first_locus_tag": group[0]["locus_tag"],
            "last_locus_tag": group[-1]["locus_tag"],
            "gene_count": str(len(group)),
            "locus_tags": ";".join(row["locus_tag"] for row in group),
            "review_state": "AUTHOR_JUDGMENT_REQUIRED",
            "claim_ceiling": CLAIM_CEILING,
        })
    return output


def _tsv(fields: Iterable[str], rows: Iterable[Mapping[str, Any]]) -> str:
    from io import StringIO
    buffer = StringIO()
    writer = SafeDictWriter(buffer, fieldnames=list(fields), delimiter="\t", lineterminator="\n", extrasaction="ignore")
    writer.writeheader(); writer.writerows(rows)
    return buffer.getvalue()


def _md_escape(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _render_markdown(
    identity: str, rows: list[dict[str, str]], neighborhoods: list[dict[str, str]],
    selected_count: int, threshold: int, adjudicated: int,
) -> str:
    lines = [
        "# Unmatched-gene function addendum scaffold", "",
        f"**Exact locus:** `{identity}`  ",
        "**Status:** deterministic evidence packet; human biological adjudication required  ",
        f"**Reference rule:** {selected_count} selected named reference(s); include genes matching <= {threshold} reference(s).  ",
        f"**Adjudication coverage:** {adjudicated}/{len(rows)} included genes.", "",
        "## Claim ceiling", "", CLAIM_CEILING, "",
        "## Candidate neighborhoods", "",
        "Consecutive low-match genes are grouped only to organize review. A group is not a pathway call.", "",
        "| Group | Gene span | Genes | Review state |", "|---|---|---:|---|",
    ]
    for group in neighborhoods:
        lines.append(
            f"| {group['neighborhood_id']} | `{group['first_locus_tag']}` to `{group['last_locus_tag']}` | "
            f"{group['gene_count']} | {group['review_state']} |"
        )
    lines.extend([
        "", "## Gene-by-gene review table", "",
        "| Gene | aa | Ref matches | Domains / current call | nr | ClusteredNR | Possible function | Alternative | Test |",
        "|---|---:|---:|---|---|---|---|---|---|",
    ])
    for row in rows:
        call = row["sec_met_domains"] or row["gene_function_inference"] or row["product_qualifier"] or "UNANNOTATED"
        lines.append(
            "| `{locus_tag}` | {aa_length} | {selected_reference_match_count}/{selected_reference_count} | "
            "{call} | {nr_subject} | {clustered_nr_subject} | {possible_function} | "
            "{alternative_explanation} | {discriminating_test} |".format(
                call=_md_escape(call), **{key: _md_escape(value) for key, value in row.items()}
            )
        )
    lines.extend([
        "", "## Authoring questions", "",
        "For each neighborhood, answer these before merging the addendum into a report:", "",
        "1. Does domain architecture support a catalytic, transport, regulatory, resistance, precursor-supply, or cell-envelope role?",
        "2. Is the neighborhood co-oriented and physically coherent, or is it better explained as an antiSMASH boundary capture?",
        "3. Do nr and ClusteredNR agree, diverge, or remain missing? Neither channel takes precedence by default.",
        "4. Which perturbation or biochemical assay would link the gene to the same product as the defining core enzyme?",
        "5. What alternative explanation remains if the pathway-linkage experiment is negative?", "",
        "## Merge instruction", "",
        "Append this addendum to the human-authored report only after the judgment fields are completed. "
        "Keep the evidence TSV and receipt beside the report; do not replace the original report in place.", "",
    ])
    return "\n".join(lines)


def build_unmatched_gene_addendum(
    *, package: str | Path, strain: str, full_node: str, region: str, bgc_alias: str,
    out: str | Path, gene_table: str | Path | None = None,
    mibig_per_gene: str | Path | None = None,
    reference_accessions: Sequence[str] = (), max_reference_fraction: float = 0.20,
    max_reference_matches: int | None = None, max_order_gap: int = 1,
    nr: str | Path | None = None, clustered_nr: str | Path | None = None,
    adjudication: str | Path | None = None,
) -> dict[str, Any]:
    package_path = Path(package).expanduser().resolve()
    if not package_path.is_dir():
        raise UnmatchedGeneAddendumHold("UNMATCHED_GENE_SOURCE_HOLD: package is not a directory")
    try:
        identity, _bgc, manifest = resolve_identity(
            package_path, strain=strain, full_node=full_node, region=region, bgc_alias=bgc_alias
        )
        gene_path = _one_gene_table(package_path, gene_table)
        genes = load_gene_rows(gene_path, identity)
    except GeneFirstHold as exc:
        raise UnmatchedGeneAddendumHold(str(exc).replace("MODEB_GENE_FIRST", "UNMATCHED_GENE")) from exc
    exact = identity["exact_identity"]
    ordered = _ordered_gene_rows(genes)
    known = {row["locus_tag"] for row, _ in ordered}
    mibig_path = _one_mibig_table(package_path, mibig_per_gene)
    selected = {str(value).strip() for value in reference_accessions if str(value).strip()}
    match_sets, selected = _load_mibig_counts(mibig_path, identity["bgc_alias"], known, selected)
    reference_count = len(selected)
    if not 0 <= max_reference_fraction <= 1:
        raise UnmatchedGeneAddendumHold("UNMATCHED_GENE_REFERENCE_HOLD: fraction must be between 0 and 1")
    threshold = max_reference_matches if max_reference_matches is not None else math.floor(reference_count * max_reference_fraction)
    if threshold < 0 or threshold > reference_count:
        raise UnmatchedGeneAddendumHold("UNMATCHED_GENE_REFERENCE_HOLD: match threshold is out of range")
    nr_path = Path(nr).expanduser().resolve() if nr else None
    cnr_path = Path(clustered_nr).expanduser().resolve() if clustered_nr else None
    nr_rows = _normalized_channel(nr_path, "nr", exact, known)
    cnr_rows = _normalized_channel(cnr_path, "clustered_nr", exact, known)

    eligible = {
        row["locus_tag"] for row, _ in ordered if len(match_sets.get(row["locus_tag"], set())) <= threshold
    }
    adj_path = Path(adjudication).expanduser().resolve() if adjudication else None
    judgments = _load_adjudication(adj_path, exact, eligible)
    evidence = []
    for row, order in ordered:
        gene = row["locus_tag"]
        count = len(match_sets.get(gene, set()))
        if gene not in eligible:
            continue
        judgment = judgments.get(gene, {})
        nr_state, nr_subject = nr_rows.get(gene, ("MISSING", "NO_ADMITTED_NR_ROW"))
        cnr_state, cnr_subject = cnr_rows.get(gene, ("MISSING", "NO_ADMITTED_CLUSTERED_NR_ROW"))
        evidence.append({
            "exact_identity": exact, "gene_order": str(order), "locus_tag": gene,
            "aa_length": str(int(float(row["aa_length"]))), "strand": _strand(row),
            "product_qualifier": str(row.get("product_qualifier") or "").strip(),
            "gene_function_inference": str(row.get("gene_function_inference") or "").strip(),
            "sec_met_domains": str(row.get("sec_met_domains") or "").strip(),
            "selected_reference_match_count": str(count),
            "selected_reference_count": str(reference_count),
            "reference_match_state": "REFERENCE_DARK" if reference_count == 0 else "LOW_MATCH",
            "nr_evidence_state": nr_state, "nr_subject": nr_subject,
            "clustered_nr_evidence_state": cnr_state, "clustered_nr_subject": cnr_subject,
            "neighborhood_id": "",
            "possible_function": judgment.get("possible_function", "AUTHOR_JUDGMENT_REQUIRED"),
            "alternative_explanation": judgment.get("alternative_explanation", "AUTHOR_JUDGMENT_REQUIRED"),
            "pathway_relevance_tier": judgment.get("pathway_relevance_tier", "UNADJUDICATED"),
            "discriminating_test": judgment.get("discriminating_test", "AUTHOR_JUDGMENT_REQUIRED"),
        })
    neighborhoods = _group_rows(evidence, exact, max_order_gap)

    out_root = Path(out).expanduser().resolve()
    if not out_root.is_dir():
        raise UnmatchedGeneAddendumHold(
            "UNMATCHED_GENE_OUTPUT_HOLD: --out must be an existing additive output root"
        )
    token = f"{_safe_token(identity)}__SapoteMamey_v{str(BUNDLE_VERSION).lstrip('v')}"
    outdir = out_root / token
    names = {
        "evidence": f"{token}__UNMATCHED_GENE_FUNCTIONS.tsv",
        "neighborhoods": f"{token}__UNMATCHED_GENE_NEIGHBORHOODS.tsv",
        "markdown": f"{token}__UNMATCHED_GENE_FUNCTIONS_ADDENDUM.md",
        "receipt": f"{token}__UNMATCHED_GENE_FUNCTIONS_RECEIPT.json",
        "adjudication_template": f"{token}__UNMATCHED_GENE_ADJUDICATION_TEMPLATE.tsv",
    }
    if outdir.exists():
        raise UnmatchedGeneAddendumHold("UNMATCHED_GENE_OUTPUT_HOLD: exact-identity output already exists")
    outdir.mkdir()
    evidence_path = outdir / names["evidence"]
    neighborhood_path = outdir / names["neighborhoods"]
    markdown_path = outdir / names["markdown"]
    template_path = outdir / names["adjudication_template"]
    _atomic_write(evidence_path, _tsv(EVIDENCE_FIELDS, evidence))
    _atomic_write(neighborhood_path, _tsv(NEIGHBORHOOD_FIELDS, neighborhoods))
    _atomic_write(markdown_path, _render_markdown(exact, evidence, neighborhoods, reference_count, threshold, len(judgments)))
    templates = [{
        "exact_identity": exact, "locus_tag": row["locus_tag"],
        "possible_function": "", "alternative_explanation": "",
        "pathway_relevance_tier": "", "discriminating_test": "",
    } for row in evidence]
    _atomic_write(template_path, _tsv(ADJUDICATION_FIELDS, templates))
    receipt_path = outdir / names["receipt"]
    inputs = {
        "manifest": {"locator": "package://manifest.json", "sha256": _sha256(package_path/"manifest.json")},
        "gene_table": {"locator": f"package://{gene_path.name}", "sha256": _sha256(gene_path)},
        "mibig_per_gene": {"locator": f"package://{mibig_path.name}", "sha256": _sha256(mibig_path)},
        "nr": ({"locator": "input://nr", "sha256": _sha256(nr_path)} if nr_path else None),
        "clustered_nr": ({"locator": "input://clustered_nr", "sha256": _sha256(cnr_path)} if cnr_path else None),
        "adjudication": ({"locator": "input://adjudication", "sha256": _sha256(adj_path)} if adj_path else None),
    }
    receipt = {
        "schema": SCHEMA, "status": "AUTHOR_JUDGMENT_REQUIRED" if len(judgments) < len(evidence) else "ADJUDICATED_SCAFFOLD",
        "sapote_mamey_bundle_version": str(BUNDLE_VERSION),
        "source_package_bundle_version": manifest.get("bundle_version"),
        "exact_identity": exact, "inputs": inputs,
        "selection": {"selected_reference_accessions": sorted(selected), "selected_reference_count": reference_count,
                      "max_reference_fraction": max_reference_fraction, "max_reference_matches": threshold,
                      "max_order_gap": max_order_gap},
        "counts": {"target_genes": len(genes), "included_low_match_genes": len(evidence),
                   "neighborhoods": len(neighborhoods), "adjudicated_genes": len(judgments),
                   "nr_bound_genes": len(nr_rows), "clustered_nr_bound_genes": len(cnr_rows)},
        "channel_contract": "nr and clustered_nr are retained separately; no precedence winner is assigned",
        "claim_ceiling": CLAIM_CEILING,
        "outputs": [],
    }
    for path in (evidence_path, neighborhood_path, markdown_path, template_path):
        receipt["outputs"].append({"path": path.name, "sha256": _sha256(path), "bytes": path.stat().st_size})
    _atomic_write(receipt_path, json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    return receipt


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--package", required=True, help="Sealed Mamey package directory")
    parser.add_argument("--strain", required=True)
    parser.add_argument("--node", required=True, dest="full_node", help="Full node-or-contig token")
    parser.add_argument("--region", required=True)
    parser.add_argument("--bgc", required=True, dest="bgc_alias")
    parser.add_argument("--out", required=True, help="Existing additive output root")
    parser.add_argument("--gene-table", default=None)
    parser.add_argument("--mibig-per-gene", default=None)
    parser.add_argument("--reference-accession", action="append", default=[], dest="reference_accessions")
    parser.add_argument("--max-reference-fraction", type=float, default=0.20)
    parser.add_argument("--max-reference-matches", type=int, default=None)
    parser.add_argument("--max-order-gap", type=int, default=1)
    parser.add_argument("--nr", default=None, help="Optional normalized nr CSV/TSV")
    parser.add_argument("--clustered-nr", default=None, dest="clustered_nr", help="Optional normalized ClusteredNR CSV/TSV")
    parser.add_argument("--adjudication", default=None, help="Optional completed adjudication TSV")


def command(args: argparse.Namespace) -> int:
    try:
        receipt = build_unmatched_gene_addendum(
            package=args.package, strain=args.strain, full_node=args.full_node,
            region=args.region, bgc_alias=args.bgc_alias, out=args.out,
            gene_table=args.gene_table, mibig_per_gene=args.mibig_per_gene,
            reference_accessions=args.reference_accessions,
            max_reference_fraction=args.max_reference_fraction,
            max_reference_matches=args.max_reference_matches,
            max_order_gap=args.max_order_gap, nr=args.nr,
            clustered_nr=args.clustered_nr, adjudication=args.adjudication,
        )
    except UnmatchedGeneAddendumHold as exc:
        raise SystemExit(str(exc)) from exc
    sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    return command(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())

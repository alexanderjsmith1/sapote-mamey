"""Rank-uncapped per-gene KnownClusterBlast/MIBiG evidence (P-MPG).

This is deliberately separate from generic ClusterBlast.  It preserves the
MIBiG channel as similarity/capacity evidence and never changes novelty scores.
"""
from __future__ import annotations

import re
import zipfile
from math import ceil
from pathlib import Path
from typing import Any

from .antismash_evidence import _region_key_from_name
from .clusterblast_genes import _gene_sort_key
from .ziputil import regular_file_names


SCHEMA_VERSION = "mibig_per_gene_v3"
REPORT_ONLY_CONTRACT = "REPORT_ONLY_NO_SCORING"
RECOGNIZABLE_MIN_IDENTITY = 30.0


def _coverage_fields(value: Any) -> dict[str, Any]:
    """Preserve antiSMASH's raw value while bounding interpretive use.

    Rare KnownClusterBlast rows exceed 100% because the source calculation is
    alignment-length based.  That provenance is useful, but values above 100
    must not add confidence or silently appear as literal query coverage.
    """
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return {
            "pct_coverage_interpretation": None,
            "coverage_qc_flag": "MISSING_OR_NONNUMERIC",
        }
    return {
        "pct_coverage_interpretation": min(100.0, max(0.0, raw)),
        "coverage_qc_flag": (
            "SOURCE_GT100_CAPPED_FOR_INTERPRETATION"
            if raw > 100.0
            else "SOURCE_LT0_CAPPED_FOR_INTERPRETATION"
            if raw < 0.0
            else "WITHIN_EXPECTED_RANGE"
        ),
    }


def _blocks(text: str) -> list[str]:
    # antiSMASH normally places the first marker after a Details header, but
    # accepting a marker at byte zero keeps the parser robust to trimmed TXT
    # exports and fixtures.
    return re.split(r"(?:^|\r?\n)>>\r?\n", text)[1:]


def _hit_rows(block: str) -> list[dict[str, Any]]:
    m = re.search(r"Table of Blast hits.*?\n(.*)", block, re.S)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        p = line.split("\t")
        if len(p) < 6:
            continue
        try:
            pid = float(p[2])
        except ValueError:
            continue
        def f(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        if p[0].strip() and p[1].strip():
            coverage = f(p[4])
            out.append({"query_gene": p[0].strip(), "subject_gene": p[1].strip(),
                        "pct_identity": pid, "blast_score": f(p[3]),
                        "pct_coverage": coverage, **_coverage_fields(coverage),
                        "evalue": p[5].strip()})
    return out


def _query_genes(text: str) -> set[str]:
    """Return every query-cluster CDS listed in the antiSMASH TXT header."""
    match = re.search(
        r"Table of genes, locations, strands and annotations of query cluster:\s*\n"
        r"(.*?)(?:\n\s*Significant hits:|\Z)",
        text,
        re.I | re.S,
    )
    if not match:
        return set()
    return {
        parts[0].strip()
        for line in match.group(1).splitlines()
        if (parts := line.split("\t")) and len(parts) >= 4 and parts[0].strip()
    }


def parse_mibig_gene_map(zip_path: str | Path, bgcs: list[Any]) -> dict[str, Any]:
    """Parse only knownclusterblast TXT blocks, across every reference rank."""
    bgc_by_key = {f"{b.contig}_c{int(b.region_number)}": b for b in bgcs
                  if getattr(b, "contig", None) and getattr(b, "region_number", None) is not None}
    # Preserve one best subject hit for every (query gene, MIBiG reference)
    # pair. A query may therefore occur more than once when it supports
    # multiple ranked MIBiG BGCs. This is what makes the table genuinely
    # rank-uncapped while avoiding duplicate subject hits within one reference.
    per_gene: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    all_query: dict[str, set[str]] = {}
    recognizable_query: dict[str, set[str]] = {}
    reference_rows = []
    parse_errors = 0
    with zipfile.ZipFile(zip_path) as zf:
        for name in regular_file_names(zf):
            low = name.lower()
            if "knownclusterblast/" not in low or not low.endswith(".txt"):
                continue
            try:
                _, _, region_key = _region_key_from_name(name)
                bgc = bgc_by_key.get(region_key)
                if bgc is None:
                    continue
                bid = bgc.bgc_id
                text = zf.read(name).decode("utf-8", "replace")
                all_query.setdefault(bid, set()).update(_query_genes(text))
                for block in _blocks(text):
                    rm = re.search(r"^\s*(\d+)\.\s+(\S+)", block, re.M)
                    if not rm:
                        continue
                    rank, ref = int(rm.group(1)), rm.group(2)
                    src = re.search(r"Source:\s*(.+)", block)
                    typ = re.search(r"Type:\s*(.+)", block)
                    hits = _hit_rows(block)
                    for h in hits:
                        q = h["query_gene"]
                        # Hit-derived fallback covers trimmed files lacking the
                        # query table; recognizable counts are always hit-based.
                        all_query.setdefault(bid, set()).add(q)
                        recognizable_query.setdefault(bid, set()).add(q)
                        cand = {**h, "bgc_id": bid, "reference": ref,
                                "mibig_accession": ref.split(".", 1)[0],
                                "mibig_compound": (src.group(1).strip() if src else ""),
                                "reference_source": (src.group(1).strip() if src else ""),
                                "reference_type": (typ.group(1).strip() if typ else ""),
                                "reference_rank": rank, "source_file": name}
                        reference_key = ref.split(".", 1)[0]
                        key = (q, reference_key)
                        cur = per_gene.setdefault(bid, {}).get(key)
                        if cur is None or (h.get("blast_score") or 0) > (cur.get("blast_score") or 0):
                            per_gene.setdefault(bid, {})[key] = cand
                    reference_rows.append({"bgc_id": bid, "reference": ref,
                                           "mibig_accession": ref.split(".", 1)[0],
                                           "reference_rank": rank, "hit_count": len(hits),
                                           "source_file": name})
            except Exception:
                parse_errors += 1
    rows = {
        bid: sorted(
            hits.values(),
            key=lambda h: (
                _gene_sort_key(h.get("query_gene", "")),
                int(h.get("reference_rank") or 999999),
                h.get("mibig_accession", ""),
            ),
        )
        for bid, hits in per_gene.items()
    }
    return {"schema_version": SCHEMA_VERSION,
            "report_only_contract": REPORT_ONLY_CONTRACT,
            "status": "PASS" if rows else "NULL_NO_MIBIG_GENE_HITS",
            "per_gene_mibig": rows, "query_gene_counts": {k: len(v) for k, v in all_query.items()},
            "recognizable_query_gene_counts": {
                k: len(v) for k, v in recognizable_query.items()
            },
            "reference_rows": reference_rows, "bgc_count": len(rows),
            "parse_error_count": parse_errors,
            "claim_safety": "MIBiG per-gene identity/coverage is protein similarity and capacity evidence, not product identity, activity, or production."}


def build_bgc_mibig_profile(per_gene: dict[str, list[dict[str, Any]]], query_gene_counts: dict[str, int],
                            bgc_by_id: dict[str, Any] | None = None,
                            convergence_rows: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    profiles = {}
    convergence_by_bgc: dict[str, list[dict[str, Any]]] = {}
    for row in convergence_rows or []:
        convergence_by_bgc.setdefault(str(row.get("bgc_id", "")), []).append(row)
    all_ids = set(per_gene) | set(query_gene_counts or {}) | set(bgc_by_id or {})
    for bid in sorted(all_ids):
        hits = per_gene.get(bid, [])
        denom = int((query_gene_counts or {}).get(bid, 0) or 0) or len({
            str(hit.get("query_gene", ""))
            for hit in hits
            if hit.get("query_gene")
        })
        informative_genes = {
            h.get("query_gene")
            for h in hits
            if h.get("query_gene")
            and (h.get("pct_identity") or 0) >= RECOGNIZABLE_MIN_IDENTITY
        }
        frac = len(informative_genes) / denom if denom else 0.0
        best_by_query: dict[str, dict[str, Any]] = {}
        for hit in hits:
            query = str(hit.get("query_gene", ""))
            current = best_by_query.get(query)
            if current is None or (hit.get("blast_score") or 0) > (current.get("blast_score") or 0):
                best_by_query[query] = hit
        bgc_context = (bgc_by_id or {}).get(bid)
        anchor = _bgc_value(bgc_context, "kcb_top", "")
        anchored = bool(re.search(r"\bBGC\d{7,}(?:\.\d+)?\b", str(anchor or "")))
        if not hits and denom:
            cls = "NO_MIBIG_PROTEIN_HITS"
        elif not hits:
            cls = "UNASSESSED_NO_QUERY_DENOMINATOR"
        # MPG-01 (v9.7.338): gate the KCB anchor on gene-level recognizability. A bare kcb_top
        # accession is a whole-cluster similarity anchor; on its own it short-circuited every
        # fraction tier, so a region with only 9.7% recognizable genes was still stamped
        # KNOWN_ANCHORED and the TRUE/PARTIAL/INTERPRETABLE dark-matter tiers were unreachable
        # for anchored regions. This inverted the novelty read. Require frac >= 0.20 to keep the
        # KNOWN_ANCHORED call; sparse-anchored regions fall through to the fraction tiers (they
        # land in TRUE_DARK_MATTER because frac < 0.20), which is the honest interpretation.
        elif anchored and frac >= 0.20:
            cls = "KNOWN_ANCHORED"
        elif frac >= 0.50:
            cls = "INTERPRETABLE_DARK_MATTER"
        elif frac > 0.20:
            cls = "PARTIAL_DARK_MATTER"
        else:
            cls = "TRUE_DARK_MATTER"
        dominant = (convergence_by_bgc.get(bid) or [{}])[0]
        profiles[bid] = {"bgc_id": bid, "query_gene_count": denom,
                         "recognizable_gene_count": len(informative_genes),
                         "recognizable_gene_fraction": round(frac, 4),
                         "mibig_gene_fraction": round(frac, 4),
                         "recognizable_min_pct_identity": RECOGNIZABLE_MIN_IDENTITY,
                         "median_pct_identity": _median([h.get("pct_identity") for h in best_by_query.values()]),
                         "distinct_mibig_refs": len({h.get("mibig_accession") for h in hits if h.get("mibig_accession")}),
                         "interpretation_class": cls,
                         "dominant_mibig_accession": dominant.get("mibig_accession", ""),
                         "dominant_mibig_compound": dominant.get("mibig_compound", ""),
                         "dominant_distinct_query_genes": dominant.get("distinct_query_genes", 0),
                         "dominant_convergence_tier": dominant.get("convergence_tier", "UNASSESSED"),
                         "report_only_contract": REPORT_ONLY_CONTRACT}
    return profiles


def build_mibig_convergence(
    per_gene: dict[str, list[dict[str, Any]]],
    query_gene_counts: dict[str, int],
    bgc_by_id: dict[str, Any] | None = None,
    recognizable_query_gene_counts: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate per-gene rows by BGC and MIBiG reference.

    The result is deterministic sequence evidence, not a product call. Broad
    class concordance is reported so class-mismatched numerical hits remain
    visible without being promoted.
    """
    rows: list[dict[str, Any]] = []
    for bid, hits in sorted((per_gene or {}).items()):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for hit in hits:
            accession = str(hit.get("mibig_accession") or hit.get("reference") or "")
            if accession:
                grouped.setdefault(accession, []).append(hit)
        total_query_genes = int((query_gene_counts or {}).get(bid, 0) or 0)
        recognizable_query_genes = int(
            (recognizable_query_gene_counts or {}).get(bid, 0) or 0
        )
        if not recognizable_query_genes:
            recognizable_query_genes = len({
                str(hit.get("query_gene", ""))
                for hit in hits
                if hit.get("query_gene")
            })
        bgc = (bgc_by_id or {}).get(bid, {})
        products = _bgc_value(bgc, "products", [])
        product_text = "; ".join(products) if isinstance(products, (list, tuple, set)) else str(products or "")
        boundary = _bgc_value(bgc, "edge_status", _bgc_value(bgc, "boundary", ""))
        for accession, ref_hits in grouped.items():
            query_genes = {str(h.get("query_gene", "")) for h in ref_hits if h.get("query_gene")}
            subject_genes = {str(h.get("subject_gene", "")) for h in ref_hits if h.get("subject_gene")}
            representative = sorted(
                ref_hits,
                key=lambda h: (
                    int(h.get("reference_rank") or 999999),
                    -(float(h.get("blast_score") or 0)),
                ),
            )[0]
            identities = [h.get("pct_identity") for h in ref_hits]
            coverages = [h.get("pct_coverage") for h in ref_hits]
            interpretive_coverages = [
                h.get("pct_coverage_interpretation")
                if h.get("pct_coverage_interpretation") is not None
                else min(100.0, max(0.0, float(h.get("pct_coverage") or 0)))
                for h in ref_hits
            ]
            ranks = [int(h.get("reference_rank") or 999999) for h in ref_hits]
            query_share = len(query_genes) / total_query_genes if total_query_genes else 0.0
            recognizable_share = (
                len(query_genes) / recognizable_query_genes
                if recognizable_query_genes else 0.0
            )
            median_identity = _median(identities)
            median_coverage = _median(coverages)
            median_coverage_interpretation = _median(interpretive_coverages)
            class_status = _class_concordance(product_text, str(representative.get("reference_type", "")))
            tier = _convergence_tier(
                len(query_genes),
                median_identity,
                median_coverage_interpretation,
                recognizable_share,
                min(ranks) if ranks else 999999,
                class_status,
            )
            rows.append({
                "bgc_id": bid,
                "products": product_text,
                "boundary": boundary,
                "mibig_accession": accession,
                "mibig_compound": representative.get("mibig_compound", ""),
                "reference_type": representative.get("reference_type", ""),
                "distinct_query_genes": len(query_genes),
                "distinct_subject_genes": len(subject_genes),
                "query_gene_count_total": total_query_genes,
                "recognizable_query_gene_count": recognizable_query_genes,
                "query_gene_share": round(query_share, 4),
                "recognizable_gene_share": round(recognizable_share, 4),
                "median_pct_identity": median_identity,
                "median_pct_coverage": median_coverage,
                "median_pct_coverage_interpretation": median_coverage_interpretation,
                "coverage_qc_flag": (
                    "SOURCE_GT100_CAPPED_FOR_INTERPRETATION"
                    if any(float(value or 0) > 100.0 for value in coverages)
                    else "WITHIN_EXPECTED_RANGE"
                ),
                "minimum_pct_identity": _minimum(identities),
                "best_reference_rank": min(ranks) if ranks else None,
                "source_row_count": len(ref_hits),
                "class_concordance": class_status,
                "convergence_tier": tier,
                "convergence_tier_basis": "recognizable_gene_share",
                "claim_safety": (
                    "Multi-gene convergence is direct sequence evidence for pathway-family "
                    "relatedness, not proof of exact product identity, expression, production, "
                    "activity, novelty, or cross-contig linkage."
                ),
            })
    tier_order = {
        "H1_HIGH_DENSITY": 0,
        "H2_STRONG_FAMILY": 1,
        "H3_MULTI_GENE": 2,
        "H4_REPEATED_SUPPORT": 3,
        "H5_SINGLE_OR_WEAK": 4,
        "CAUTION_CLASS_MISMATCH": 5,
    }
    ordered = sorted(
        rows,
        key=lambda row: (
            row.get("bgc_id", ""),
            tier_order.get(str(row.get("convergence_tier")), 99),
            -int(row.get("distinct_query_genes") or 0),
            -float(row.get("median_pct_identity") or 0),
            int(row.get("best_reference_rank") or 999999),
        ),
    )
    by_bgc: dict[str, list[dict[str, Any]]] = {}
    for row in ordered:
        by_bgc.setdefault(str(row.get("bgc_id", "")), []).append(row)
    for bgc_rows in by_bgc.values():
        for rank, row in enumerate(bgc_rows, 1):
            row["convergence_rank"] = rank
            row["dominant_reference"] = rank == 1
            row["dominance_status"] = "NOT_DOMINANT"
            row["runner_up_mibig_accession"] = ""
            row["runner_up_mibig_compound"] = ""
            row["runner_up_distinct_query_genes"] = 0
            row["dominance_gene_margin"] = ""
        dominant = bgc_rows[0]
        runner = bgc_rows[1] if len(bgc_rows) > 1 else None
        genes = int(dominant.get("distinct_query_genes") or 0)
        runner_genes = int((runner or {}).get("distinct_query_genes") or 0)
        margin = genes - runner_genes
        if runner is None:
            status = "UNIQUE_DOMINANT"
        elif margin >= max(3, ceil(genes * 0.25)):
            status = "CLEAR_DOMINANT"
        elif margin <= 0:
            status = "CO_DOMINANT_OR_DIFFUSE"
        else:
            status = "MIXED_FAMILY_SIGNAL"
        dominant.update({
            "dominance_status": status,
            "runner_up_mibig_accession": (runner or {}).get("mibig_accession", ""),
            "runner_up_mibig_compound": (runner or {}).get("mibig_compound", ""),
            "runner_up_distinct_query_genes": runner_genes,
            "dominance_gene_margin": margin if runner else genes,
        })
    return ordered


def _bgc_value(bgc: Any, key: str, default: Any = None) -> Any:
    if isinstance(bgc, dict):
        return bgc.get(key, default)
    return getattr(bgc, key, default)


def _class_tokens(text: str) -> set[str]:
    lowered = (text or "").lower()
    tokens: set[str] = set()
    if any(x in lowered for x in ("pks", "polyketide", "arylpolyene", "phenazine")):
        tokens.add("PKS")
    if any(x in lowered for x in ("nrps", "nrp-", "napaa", "nonribosomal", "thioamide-nrp")):
        tokens.add("NRPS")
    if any(x in lowered for x in ("ripp", "ribosomal", "lanthi", "lasso", "linaridin",
                                  "thiopeptide", "ranthi", "sacti", "azole-containing")):
        tokens.add("RiPP")
    if "terpene" in lowered:
        tokens.add("TERPENE")
    if any(x in lowered for x in ("saccharide", "oligosaccharide", "glycoside")):
        tokens.add("SACCHARIDE")
    if any(x in lowered for x in ("siderophore", "metallophore")):
        tokens.add("SIDEROPHORE")
    return tokens


def _class_concordance(products: str, reference_type: str) -> str:
    query = _class_tokens(products)
    reference = _class_tokens(reference_type)
    if query and reference and query.intersection(reference):
        return "CONCORDANT"
    if query and reference:
        return "DISCORDANT"
    return "UNRESOLVED"


def _convergence_tier(
    query_genes: int,
    median_identity: float | None,
    median_coverage: float | None,
    query_share: float,
    best_rank: int,
    class_status: str,
) -> str:
    identity = float(median_identity or 0)
    coverage = min(100.0, float(median_coverage or 0))
    if class_status == "DISCORDANT":
        return "CAUTION_CLASS_MISMATCH"
    if query_genes >= 12 and identity >= 70 and coverage >= 80 and query_share >= 0.65 and best_rank <= 3:
        return "H1_HIGH_DENSITY"
    if query_genes >= 8 and identity >= 55 and coverage >= 75 and query_share >= 0.40:
        return "H2_STRONG_FAMILY"
    if query_genes >= 4 and identity >= 40 and coverage >= 60:
        return "H3_MULTI_GENE"
    if query_genes >= 2 and identity >= 35:
        return "H4_REPEATED_SUPPORT"
    return "H5_SINGLE_OR_WEAK"


def _median(values):
    vals = sorted(float(v) for v in values if v is not None)
    if not vals:
        return None
    n = len(vals)
    return round(vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2, 3)


def _minimum(values):
    vals = [float(v) for v in values if v is not None]
    return round(min(vals), 3) if vals else None

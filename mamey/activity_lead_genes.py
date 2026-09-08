"""Gene-level biosynthetic foundations for activity-lead routing boards.

The input is the claim-safe CSV emitted by :mod:`mamey.activity_lead_report`.
For every complete four-part locus, this module binds the corresponding
``*_gene_by_gene_all_bgcs.csv`` rows by strain, full contig, region and the
source-local alias retained in that board.  It then selects at most five
locally encoded genes that best explain the source class labels.

The result is an authoring aid, not a biological verdict.  It never converts
sequence similarity into identity, capacity into production, or a routing
prior into measured antibacterial/antifungal activity.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
import re
from collections import defaultdict
from typing import Any, Iterable


ANCHOR_COLUMNS = [
    "strain", "exact_locus", "full_node_or_contig", "region", "bgc_alias",
    "source_local_bgc_alias", "gene_anchor_rank", "locus_tag", "start", "end",
    "strand", "aa_length", "evidence_tier", "biosynthetic_role", "key_domains",
    "class_votes", "logic", "source_gene_table", "claim_ceiling",
]

LOCUS_COLUMNS = [
    "strain", "exact_locus", "full_node_or_contig", "region", "bgc_alias",
    "source_local_bgc_alias", "source_products", "governed_gene_count",
    "anchor_count", "gene_logic_strength", "supported_classes",
    "unresolved_source_labels", "biosynthetic_logic_summary", "source_gene_table",
    "claim_ceiling",
]

HOLD_COLUMNS = [
    "strain", "exact_locus", "state", "reason", "source_triage_board",
]

CLAIM_CEILING = (
    "CLASS_LEVEL_BIOSYNTHETIC_LOGIC_ONLY_NOT_COMPOUND_IDENTITY_PRODUCTION_"
    "ANTIFUNGAL_OR_ANTIBACTERIAL_ACTIVITY"
)

TIER_SCORE = {
    "CLASS_DEFINING_CORE": 60,
    "CLASS_SIGNATURE_SUPPORT": 50,
    "PATHWAY_COMPLETION_SUPPORT": 40,
    "TRANSPORT_OR_SELF_PROTECTION_CONTEXT": 30,
    "REGULATORY_CONTEXT": 20,
    "CONTEXT_ONLY": 10,
}


def _tokens(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;,]", value or "") if part.strip()]


def _norm_class(value: str) -> str | None:
    text = value.strip().lower()
    if not text or text in {"other", "unknown"}:
        return None
    if "nrps" in text or "nonribosomal" in text:
        return "NRPS"
    if "pks" in text or "polyketide" in text:
        return "PKS"
    if any(k in text for k in ("ripp", "lanth", "lasso", "thiopeptide", "linaridin", "cyanobactin")):
        return "RiPP"
    if "terpene" in text:
        return "terpene"
    if "siderophore" in text:
        return "siderophore"
    if "saccharide" in text or "polysaccharide" in text:
        return "saccharide"
    if "betalactone" in text or "beta-lactone" in text:
        return "beta-lactone"
    if "phosphonate" in text:
        return "phosphonate"
    return value.strip()


def _source_classes(products: str) -> list[str]:
    seen: list[str] = []
    for token in _tokens(products):
        normalized = _norm_class(token)
        if normalized and normalized not in seen:
            seen.append(normalized)
    return seen


def _class_votes(row: dict[str, str]) -> set[str]:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("product_qualifier", "gene_function_inference", "sec_met_domains")
    ).lower()
    votes: set[str] = set()

    nrps_core = bool(re.search(r"\b(amp-binding|adenylation|condensation|nrps)\b", text))
    if nrps_core and not (
        "thioesterase" in text
        and not re.search(r"\b(amp-binding|adenylation|condensation)\b", text)
    ):
        votes.add("NRPS")
    if re.search(r"\b(pks[_ -]?ks|ketosynthase|ketoacyl[- ]synth|polyketide synthase|transat[- ]?pks|t[123]pks)\b", text):
        votes.add("PKS")
    if re.search(r"\b(lanm|lanb|lanc|ycao|tfua|ripp precursor|lanthipeptide|lassopeptide|linaridin)\b", text):
        votes.add("RiPP")
    if re.search(r"\b(terpene synthase|phytoene synthase|lycopene cyclase|squalene-hopene cyclase)\b", text):
        votes.add("terpene")
    if re.search(r"\b(iuca|iucb|luca|lucc|siderophore synthetase)\b", text):
        votes.add("siderophore")
    if re.search(r"\b(beta-lactone synthetase|betalactone synthetase)\b", text):
        votes.add("beta-lactone")
    if re.search(r"\b(phosphoenolpyruvate mutase|pep mutase|phosphonopyruvate)\b", text):
        votes.add("phosphonate")
    if re.search(r"\b(polysaccharide biosynthesis|saccharide biosynthesis)\b", text):
        votes.add("saccharide")
    return votes


def _tier(row: dict[str, str], votes: set[str]) -> str:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("product_qualifier", "gene_function_inference", "sec_met_domains")
    ).lower()
    if votes and re.search(
        r"amp-binding|adenylation|condensation|pks[_ -]?ks|ketosynthase|polyketide synthase|"
        r"terpene synthase|phytoene synthase|lycopene cyclase|iuca|luca|beta-lactone synthetase|"
        r"phosphoenolpyruvate mutase",
        text,
    ):
        return "CLASS_DEFINING_CORE"
    if votes:
        return "CLASS_SIGNATURE_SUPPORT"
    if re.search(r"methyltransferase|glycosyltransferase|oxygenase|dehydrogenase|thioesterase|tailor", text):
        return "PATHWAY_COMPLETION_SUPPORT"
    if re.search(r"transporter|permease|efflux|abc[- ]?type|resistance|self[- ]?protection", text):
        return "TRANSPORT_OR_SELF_PROTECTION_CONTEXT"
    if re.search(r"regulator|transcription|response regulator", text):
        return "REGULATORY_CONTEXT"
    return "CONTEXT_ONLY"


def _logic(row: dict[str, str], tier: str, votes: set[str]) -> str:
    domains = ", ".join(_tokens(row.get("sec_met_domains") or "")) or "no diagnostic domain string"
    if tier == "CLASS_DEFINING_CORE":
        return f"Core catalytic architecture supports {', '.join(sorted(votes))}; domains: {domains}."
    if tier == "CLASS_SIGNATURE_SUPPORT":
        return f"Class-signature context supports {', '.join(sorted(votes))}; domains: {domains}."
    if tier == "PATHWAY_COMPLETION_SUPPORT":
        return "Tailoring or release capacity supports pathway coherence but does not define the product class alone."
    if tier == "TRANSPORT_OR_SELF_PROTECTION_CONTEXT":
        return "Transport or possible protection context is present; substrate and direction remain unresolved."
    if tier == "REGULATORY_CONTEXT":
        return "Local regulatory context is present; expression remains unknown."
    return "Context-only annotation; it does not independently establish the source class label."


def select_gene_anchors(
    rows: Iterable[dict[str, str]],
    products: str,
    *,
    top_n: int = 5,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Choose a diverse, deterministic set of class-explanatory genes."""
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    candidates: list[dict[str, Any]] = []
    for row in rows:
        votes = _class_votes(row)
        tier = _tier(row, votes)
        item = dict(row)
        item["_votes"] = votes
        item["_tier"] = tier
        item["_score"] = TIER_SCORE[tier]
        candidates.append(item)
    candidates.sort(
        key=lambda row: (
            -int(row["_score"]),
            -len(row["_votes"]),
            int(row.get("cds_start") or row.get("start") or 0),
            str(row.get("locus_tag") or ""),
        )
    )

    wanted = _source_classes(products)
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    for source_class in wanted:
        for row in candidates:
            tag = str(row.get("locus_tag") or "")
            if tag not in used and source_class in row["_votes"]:
                selected.append(row)
                used.add(tag)
                break
        if len(selected) >= top_n:
            break
    for row in candidates:
        if len(selected) >= top_n:
            break
        tag = str(row.get("locus_tag") or "")
        if tag not in used:
            selected.append(row)
            used.add(tag)

    supported = sorted({vote for row in selected for vote in row["_votes"]})
    unresolved = [label for label in wanted if label not in supported]
    class_defining = sum(row["_tier"] == "CLASS_DEFINING_CORE" for row in selected)
    if class_defining and not unresolved:
        strength = "STRONG_GENE_LOGIC"
    elif class_defining or supported:
        strength = "MODERATE_GENE_LOGIC"
    elif selected:
        strength = "WEAK_ACCESSORY_ONLY"
    else:
        strength = "UNRESOLVED_CLASS_FOUNDATION"
    summary = (
        f"{class_defining} class-defining anchor(s); "
        f"{sum(row['_tier'] == 'PATHWAY_COMPLETION_SUPPORT' for row in selected)} "
        "pathway-completion anchor(s)."
    )
    return selected, {
        "gene_logic_strength": strength,
        "supported_classes": supported,
        "unresolved_source_labels": unresolved,
        "biosynthetic_logic_summary": summary,
    }


def _region_from_source_gbk(value: str) -> str:
    match = re.search(r"\.(region\d+)\.gbk$", value or "", re.IGNORECASE)
    return match.group(1) if match else ""


def _gene_table_for_board(board: str, strain: str) -> str | None:
    package = os.path.dirname(os.path.abspath(board))
    preferred = os.path.join(package, f"{strain}_gene_by_gene_all_bgcs.csv")
    if os.path.isfile(preferred):
        return preferred
    try:
        names = sorted(
            name for name in os.listdir(package)
            if name.endswith("_gene_by_gene_all_bgcs.csv")
        )
    except OSError:
        return None
    return os.path.join(package, names[0]) if len(names) == 1 else None


def build_gene_anchor_report(
    leads_csv: str,
    *,
    top_n: int = 5,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    with open(leads_csv, newline="", encoding="utf-8-sig") as handle:
        leads = list(csv.DictReader(handle))
    anchors: list[dict[str, Any]] = []
    loci: list[dict[str, Any]] = []
    holds: list[dict[str, str]] = []
    cache: dict[str, list[dict[str, str]]] = {}

    seen: set[str] = set()
    for lead in leads:
        exact = (lead.get("exact_locus") or "").strip()
        if exact in seen:
            continue
        seen.add(exact)
        strain = (lead.get("strain") or "").strip()
        contig = (lead.get("full_node_or_contig") or "").strip()
        region = (lead.get("region") or "").strip()
        alias = (lead.get("bgc_alias") or "").strip()
        source_alias = (lead.get("source_local_bgc_alias") or "").strip()
        board = (lead.get("source_triage_board") or "").strip()
        expected = f"{strain} / {contig} / {region} / {alias}"
        if not all((strain, contig, region, alias, source_alias, board)) or exact != expected:
            holds.append({
                "strain": strain, "exact_locus": exact,
                "state": "INCOMPLETE_OR_CONTRADICTORY_EXACT_LOCUS_NOT_ADMITTED",
                "reason": "complete four-part identity and source-local alias are mandatory",
                "source_triage_board": board,
            })
            continue
        table = _gene_table_for_board(board, strain)
        if not table:
            holds.append({
                "strain": strain, "exact_locus": exact,
                "state": "GENE_TABLE_NOT_BOUND",
                "reason": "exactly one per-package gene-by-gene table was not found",
                "source_triage_board": board,
            })
            continue
        if table not in cache:
            with open(table, newline="", encoding="utf-8-sig") as handle:
                cache[table] = list(csv.DictReader(handle))
        gene_rows = [
            row for row in cache[table]
            if (row.get("contig") or "").strip() == contig
            and _region_from_source_gbk(row.get("source_gbk") or "").lower() == region.lower()
            and (row.get("bgc_id") or "").strip() == source_alias
        ]
        if not gene_rows:
            holds.append({
                "strain": strain, "exact_locus": exact,
                "state": "PHYSICAL_GENE_ROSTER_NOT_BOUND",
                "reason": "no gene rows matched contig, region and source-local alias",
                "source_triage_board": board,
            })
            continue

        products = (lead.get("Products") or lead.get("products") or "").strip()
        selected, summary = select_gene_anchors(gene_rows, products, top_n=top_n)
        for rank, row in enumerate(selected, 1):
            votes = set(row["_votes"])
            tier = str(row["_tier"])
            anchors.append({
                "strain": strain, "exact_locus": exact,
                "full_node_or_contig": contig, "region": region, "bgc_alias": alias,
                "source_local_bgc_alias": source_alias, "gene_anchor_rank": rank,
                "locus_tag": (row.get("locus_tag") or "").strip(),
                "start": (row.get("cds_start") or "").strip(),
                "end": (row.get("cds_end") or "").strip(),
                "strand": (row.get("strand") or "").strip(),
                "aa_length": (row.get("aa_length") or "").strip(),
                "evidence_tier": tier,
                "biosynthetic_role": (row.get("gene_function_inference") or "").strip(),
                "key_domains": "; ".join(_tokens(row.get("sec_met_domains") or "")),
                "class_votes": "; ".join(sorted(votes)),
                "logic": _logic(row, tier, votes),
                "source_gene_table": table,
                "claim_ceiling": CLAIM_CEILING,
            })
        loci.append({
            "strain": strain, "exact_locus": exact,
            "full_node_or_contig": contig, "region": region, "bgc_alias": alias,
            "source_local_bgc_alias": source_alias, "source_products": products,
            "governed_gene_count": len(gene_rows), "anchor_count": len(selected),
            "gene_logic_strength": summary["gene_logic_strength"],
            "supported_classes": "; ".join(summary["supported_classes"]),
            "unresolved_source_labels": "; ".join(summary["unresolved_source_labels"]),
            "biosynthetic_logic_summary": summary["biosynthetic_logic_summary"],
            "source_gene_table": table, "claim_ceiling": CLAIM_CEILING,
        })

    strengths: dict[str, int] = defaultdict(int)
    for row in loci:
        strengths[str(row["gene_logic_strength"])] += 1
    meta = {
        "lead_rows": len(leads), "unique_exact_loci": len(seen),
        "loci_with_gene_profiles": len(loci), "gene_anchor_rows": len(anchors),
        "holds": len(holds), "top_n": top_n,
        "gene_logic_strength": dict(sorted(strengths.items())),
        "claim_safety": (
            "Class-level biosynthetic logic only. Similarity is not identity; capacity is not "
            "production; a routing prior is not measured activity."
        ),
    }
    return anchors, loci, holds, meta


def _write_csv(path: str, rows: list[dict[str, Any]], columns: list[str]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def run(leads_csv: str, out_dir: str, *, top_n: int = 5) -> dict[str, Any]:
    anchors, loci, holds, meta = build_gene_anchor_report(leads_csv, top_n=top_n)
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "anchors_csv": os.path.join(out_dir, "ACTIVITY_LEAD_GENE_ANCHORS.csv"),
        "loci_csv": os.path.join(out_dir, "ACTIVITY_LEAD_GENE_LOGIC.csv"),
        "holds_csv": os.path.join(out_dir, "ACTIVITY_LEAD_GENE_ANCHOR_HOLDS.csv"),
        "metadata_json": os.path.join(out_dir, "ACTIVITY_LEAD_GENE_ANCHOR_META.json"),
    }
    _write_csv(paths["anchors_csv"], anchors, ANCHOR_COLUMNS)
    _write_csv(paths["loci_csv"], loci, LOCUS_COLUMNS)
    _write_csv(paths["holds_csv"], holds, HOLD_COLUMNS)
    tmp = paths["metadata_json"] + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, paths["metadata_json"])
    result = dict(meta)
    result["paths"] = paths
    return result

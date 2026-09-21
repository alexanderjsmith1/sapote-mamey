"""Portable, claim-safe RG-GMCI complementary-rescue atlas.

This post-seal review layer combines an existing RG-GMCI pair table with exact
per-gene MIBiG hits, locus annotations, and a MIBiG GenBank archive.  It does
not alter RG-GMCI confidence, join contigs, or assign a product.  Its purpose is
to expose when two complete loci cover distinct parts of the same comparator.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import csv
import json
import re
import statistics
import tarfile

from .csv_safety import SafeDictWriter

CLAIM_CEILING = (
    "Homology-guided paired-locus prioritization only. A shared MIBiG comparator "
    "and complementary protein tiling do not prove physical contig adjacency, "
    "exact product, complete pathway, expression, production, activity, novelty, "
    "or scientific acceptance."
    "Scores are tool-specific: the same assembly fact is weighted differently by each ranking tool, so values are not comparable across tools."
)

TIERS = (
    "A_CONTROL_GRADE_COMPLEMENTARY_RESCUE",
    "B_STRONG_COMPLEMENTARY_RESCUE",
    "C_COMPLEMENTARY_REVIEW_CANDIDATE",
    "D_SHARED_REFERENCE_OR_GENERIC_HOLD",
)


def _read(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def _number(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def exact_identity_parts(value: str) -> tuple[str, str, str, str]:
    """Return the permanent four-part identity, failing closed on omissions."""
    parts = tuple(part.strip() for part in str(value).split(" / "))
    if len(parts) != 4 or not all(parts):
        raise ValueError(
            "RGGMCI_ATLAS_IDENTITY_HOLD: expected strain / full node-or-contig / region / BGC alias"
        )
    strain, node, region, alias = parts
    if not re.fullmatch(r"region\d+", region, re.I) or not re.fullmatch(r"BGC\d+", alias, re.I):
        raise ValueError(f"RGGMCI_ATLAS_IDENTITY_HOLD: malformed identity: {value}")
    return strain, node, region, alias


def _median(values) -> float:
    vals = [_number(v) for v in values if v not in (None, "")]
    return statistics.median(vals) if vals else 0.0


def _protein_key(value: str) -> tuple:
    numbers = re.findall(r"\d+", value or "")
    return tuple(int(x) for x in numbers) if numbers else (10**12, value or "")


def read_mibig_rosters(path: str | Path) -> dict[str, dict]:
    """Read protein order and CDS denominators from a .tar.gz of MIBiG GBKs."""
    protein_re = re.compile(r'/protein_id="([^"]+)"')
    rosters: dict[str, dict] = {}
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.lower().endswith((".gbk", ".gbff")):
                continue
            stream = archive.extractfile(member)
            if stream is None:
                continue
            accession = Path(member.name).stem.split(".")[0]
            proteins = protein_re.findall(stream.read().decode("utf-8", errors="replace"))
            rosters[accession] = {
                "protein_count": len(proteins),
                "protein_order": {protein: index + 1 for index, protein in enumerate(proteins)},
            }
    return rosters


def reference_topology(a: set[str], b: set[str], order: dict[str, int]) -> tuple[str, int | str]:
    apos = sorted(order[p] for p in a if p in order)
    bpos = sorted(order[p] for p in b if p in order)
    if not apos or not bpos:
        return "REFERENCE_ORDER_UNAVAILABLE", ""
    if a & b:
        return "OVERLAPPING_REFERENCE_PROTEINS", 0
    if max(apos) < min(bpos):
        gap = min(bpos) - max(apos) - 1
        return ("DISJOINT_ADJACENT_SEGMENTS" if gap <= 3 else "DISJOINT_SEPARATED_SEGMENTS"), gap
    if max(bpos) < min(apos):
        gap = min(apos) - max(bpos) - 1
        return ("DISJOINT_ADJACENT_SEGMENTS" if gap <= 3 else "DISJOINT_SEPARATED_SEGMENTS"), gap
    return "DISJOINT_INTERLEAVED_REFERENCE_PROTEINS", 0


def _generic_modular(locus_a: dict, locus_b: dict, row: dict) -> bool:
    def text(locus):
        return " ".join(str(locus.get(k, "")) for k in (
            "current_antismash_products", "architecture_first_pathway_type", "functional_logic_tags"
        )).lower()
    modular = lambda value: any(token in value for token in ("pks", "nrps", "polyketide", "assembly_line"))
    return modular(text(locus_a)) and modular(text(locus_b)) and (
        row["max_reference_rank"] > 3 or row["median_identity"] < 45 or row["reference_total_proteins"] > 60
    )


def evidence_tier(row: dict) -> tuple[str, str]:
    both = min(row["unique_subjects_a"], row["unique_subjects_b"])
    ordered = row["reference_tiling_topology"] in {
        "DISJOINT_ADJACENT_SEGMENTS", "DISJOINT_SEPARATED_SEGMENTS"
    }
    boundary = (row["boundary_a"] != "Interior" or row["boundary_b"] != "Interior" or
                row["subject_tiling_verdict"] == "TERMINUS_TRUNCATION_SPLIT")
    if (row["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE" and both >= 3 and
            row["shared_subjects"] == 0 and row["combined_unique_subjects"] >= 10 and
            row["reference_protein_coverage"] >= .35 and row["max_reference_rank"] <= 3 and
            row["median_identity"] >= 35 and row["median_alignment_coverage"] >= 55 and
            ordered and boundary and
            not row["generic_modular_caution"]):
        return TIERS[0], "Broad, disjoint, boundary-supported tiling by two loci in a high-ranked comparator."
    if (row["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE" and both >= 2 and
            row["shared_subjects"] == 0 and row["combined_unique_subjects"] >= 6 and
            row["reference_protein_coverage"] >= .20 and row["subject_disjointness"] >= .85 and
            row["median_identity"] >= 30 and row["median_alignment_coverage"] >= 55 and
            row["max_reference_rank"] <= 5 and ordered and boundary and
            not row["generic_modular_caution"]):
        return TIERS[1], "Substantial, disjoint two-locus contribution to a high-ranked comparator."
    if (both >= 2 and row["shared_subjects"] <= 1 and row["subject_disjointness"] >= .85 and
            row["combined_unique_subjects"] >= 5 and row["max_reference_rank"] <= 10):
        return TIERS[2], "Complementary exact-protein tiling is present; specificity or completeness needs review."
    return TIERS[3], "The shared-reference signal does not pass the two-locus breadth and specificity gate."


def evidence_score(row: dict) -> float:
    balance = min(row["unique_subjects_a"], row["unique_subjects_b"]) / max(
        row["unique_subjects_a"], row["unique_subjects_b"], 1)
    score = (
        20 * balance + 15 * row["subject_disjointness"] +
        25 * min(row["reference_protein_coverage"] / .50, 1) +
        15 * min(row["median_identity"] / 70, 1) +
        10 * min(row["median_alignment_coverage"] / 90, 1) +
        10 * max(0, 1 - (row["max_reference_rank"] - 1) / 39) +
        3 * (row["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE") +
        2 * (row["boundary_a"] != "Interior" or row["boundary_b"] != "Interior")
    )
    if row["generic_modular_caution"]:
        score -= 8
    return round(max(0, min(100, score)), 2)


def build_atlas(pair_rows: list[dict], locus_rows: list[dict], hit_rows: list[dict], rosters: dict) -> tuple[list[dict], list[dict]]:
    loci = {}
    for locus in locus_rows:
        ident = locus.get("complete_identity", "")
        exact_identity_parts(ident)
        if ident in loci:
            raise ValueError(f"RGGMCI_ATLAS_LOCUS_DUPLICATE: {ident}")
        loci[ident] = locus

    hits: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for hit in hit_rows:
        ident = hit.get("complete_identity", "")
        exact_identity_parts(ident)
        ref = hit.get("mibig_accession", "").split(".")[0]
        if ref:
            hits[(ident, ref)].append(hit)

    ranked, details = [], []
    for pair in pair_rows:
        ida, idb = pair.get("identity_a", ""), pair.get("identity_b", "")
        pa, pb = exact_identity_parts(ida), exact_identity_parts(idb)
        if pa[0] != pb[0] or pair.get("strain", pa[0]) != pa[0]:
            raise ValueError(f"RGGMCI_ATLAS_STRAIN_HOLD: {ida} + {idb}")
        if ida not in loci or idb not in loci:
            raise ValueError(f"RGGMCI_ATLAS_LOCUS_BINDING_HOLD: {ida} + {idb}")
        refs_a = {ref for ident, ref in hits if ident == ida}
        refs_b = {ref for ident, ref in hits if ident == idb}
        candidates = []
        for ref in sorted(refs_a & refs_b):
            ha, hb = hits[(ida, ref)], hits[(idb, ref)]
            sa = {h.get("subject_gene", "") for h in ha if h.get("subject_gene")}
            sb = {h.get("subject_gene", "") for h in hb if h.get("subject_gene")}
            union, overlap = sa | sb, sa & sb
            # A reference whose roster never loaded has an UNMEASURED denominator, not a zero one.
            # The numbers below stay as they are so scoring and ranking are untouched; the state
            # column is what lets a reader tell "covers none of the reference" from "never read it".
            roster_loaded = ref in rosters
            roster = rosters.get(ref, {"protein_count": 0, "protein_order": {}})
            topology, gap = reference_topology(sa, sb, roster["protein_order"])
            ranks_a = [int(_number(h.get("reference_rank"), 999)) for h in ha]
            ranks_b = [int(_number(h.get("reference_rank"), 999)) for h in hb]
            row = {
                "strain": pa[0], "pair": pair.get("pair", f"{pa[3]}+{pb[3]}"),
                "identity_a": ida, "identity_b": idb, "shared_reference": ref,
                "shared_reference_product": (ha + hb)[0].get("mibig_product", ""),
                "query_genes_a": len({h.get("query_gene") for h in ha if h.get("query_gene")}),
                "query_genes_b": len({h.get("query_gene") for h in hb if h.get("query_gene")}),
                "unique_subjects_a": len(sa - sb), "unique_subjects_b": len(sb - sa),
                "subjects_a_total": len(sa), "subjects_b_total": len(sb),
                "shared_subjects": len(overlap), "combined_unique_subjects": len(union),
                "subject_disjointness": round(1 - len(overlap) / len(union), 4) if union else 0.0,
                "reference_roster_state": "LOADED" if roster_loaded else "REFERENCE_ROSTER_NOT_LOADED",
                "reference_total_proteins": int(roster["protein_count"]),
                "reference_protein_coverage": round(len(union) / roster["protein_count"], 4) if roster["protein_count"] else 0.0,
                "median_identity_a": round(_median(h.get("pct_identity") for h in ha), 2),
                "median_identity_b": round(_median(h.get("pct_identity") for h in hb), 2),
                "median_identity": round(_median(h.get("pct_identity") for h in ha + hb), 2),
                "median_alignment_coverage": round(_median(h.get("pct_coverage_interpretation") for h in ha + hb), 2),
                "best_reference_rank_a": min(ranks_a, default=999),
                "best_reference_rank_b": min(ranks_b, default=999),
                "max_reference_rank": max(min(ranks_a, default=999), min(ranks_b, default=999)),
                "reference_tiling_topology": topology, "reference_segment_gap_proteins": gap,
                "subjects_a": "; ".join(sorted(sa, key=_protein_key)),
                "subjects_b": "; ".join(sorted(sb, key=_protein_key)),
            }
            candidates.append(row)
            details.append(dict(row, rggmci_confidence=pair.get("rggmci_confidence", ""),
                                subject_tiling_verdict=pair.get("subject_tiling_verdict", ""),
                                claim_ceiling=CLAIM_CEILING))
        if candidates:
            priority = {"DISJOINT_ADJACENT_SEGMENTS": 4, "DISJOINT_SEPARATED_SEGMENTS": 3,
                        "DISJOINT_INTERLEAVED_REFERENCE_PROTEINS": 2,
                        "OVERLAPPING_REFERENCE_PROTEINS": 1, "REFERENCE_ORDER_UNAVAILABLE": 0}
            best = max(candidates, key=lambda r: (min(r["unique_subjects_a"], r["unique_subjects_b"]),
                priority.get(r["reference_tiling_topology"], 0), r["combined_unique_subjects"],
                r["reference_protein_coverage"], r["subject_disjointness"],
                -r["max_reference_rank"], r["median_identity"]))
        else:
            best = {"strain": pa[0], "pair": pair.get("pair", f"{pa[3]}+{pb[3]}"),
                    "identity_a": ida, "identity_b": idb, "shared_reference": "",
                    "shared_reference_product": "", "query_genes_a": 0, "query_genes_b": 0,
                    "unique_subjects_a": 0, "unique_subjects_b": 0, "subjects_a_total": 0,
                    "subjects_b_total": 0, "shared_subjects": 0, "combined_unique_subjects": 0,
                    "subject_disjointness": 0.0, "reference_total_proteins": 0,
                    "reference_protein_coverage": 0.0, "median_identity_a": 0.0,
                    "median_identity_b": 0.0, "median_identity": 0.0,
                    "median_alignment_coverage": 0.0, "best_reference_rank_a": 999,
                    "best_reference_rank_b": 999, "max_reference_rank": 999,
                    "reference_tiling_topology": "NO_SHARED_EXACT_REFERENCE",
                    "reference_segment_gap_proteins": "", "subjects_a": "", "subjects_b": ""}
        la, lb = loci[ida], loci[idb]
        best.update({
            "rggmci_score": pair.get("rggmci_score", ""),
            "rggmci_confidence": pair.get("rggmci_confidence", ""),
            "subject_tiling_verdict": pair.get("subject_tiling_verdict", ""),
            "terminus_override_note": pair.get("terminus_override_note", ""),
            "boundary_a": la.get("boundary", ""), "boundary_b": lb.get("boundary", ""),
            "products_a": la.get("current_antismash_products", ""),
            "products_b": lb.get("current_antismash_products", ""),
        })
        best["generic_modular_caution"] = _generic_modular(la, lb, best)
        best["evidence_score_0_100"] = evidence_score(best)
        best["evidence_tier"], best["tier_reason"] = evidence_tier(best)
        best["claim_ceiling"] = CLAIM_CEILING
        ranked.append(best)

    tier_rank = {tier: i for i, tier in enumerate(TIERS)}
    ranked.sort(key=lambda row: (tier_rank[row["evidence_tier"]], -row["evidence_score_0_100"],
                                 row["identity_a"], row["identity_b"]))
    within = Counter()
    for index, row in enumerate(ranked, 1):
        row["rescue_rank_all_pairs"] = index
        within[row["strain"]] += 1
        row["rescue_rank_within_strain"] = within[row["strain"]]
    return ranked, details


def _write_tsv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = SafeDictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_atlas(out_dir: str | Path, ranked: list[dict], details: list[dict]) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_tsv(out / "RGGMCI_RESCUE_CANDIDATES.tsv", ranked)
    _write_tsv(out / "RGGMCI_PAIR_REFERENCE_EVIDENCE.tsv", details)
    strict = [row for row in ranked if row["evidence_tier"] in TIERS[:2]]
    _write_tsv(out / "RGGMCI_STRICT_RESCUES.tsv", strict)
    counts = Counter(row["evidence_tier"] for row in ranked)
    lines = ["# RG-GMCI complementary rescue atlas", "", CLAIM_CEILING, "",
             f"Evaluated **{len(ranked):,}** pairs; strict review set: **{len(strict):,}**.", "",
             "| Rank | Tier | First complete identity | Second complete identity | Comparator | Score |",
             "|---:|---|---|---|---|---:|"]
    for row in strict:
        lines.append(f"| {row['rescue_rank_all_pairs']} | {row['evidence_tier']} | {row['identity_a']} | "
                     f"{row['identity_b']} | {row['shared_reference']} {row['shared_reference_product']} | "
                     f"{row['evidence_score_0_100']:.2f} |")
    (out / "RGGMCI_RESCUE_ATLAS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    receipt = {"status": "PASS", "pair_count": len(ranked), "pair_reference_count": len(details),
               "strict_count": len(strict), "tier_counts": dict(counts),
               "claim_ceiling": CLAIM_CEILING}
    (out / "RGGMCI_RESCUE_ATLAS_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def run(pair_table: str | Path, locus_table: str | Path, hits_root: str | Path,
        mibig_archive: str | Path, out_dir: str | Path) -> dict:
    hit_paths = sorted(Path(hits_root).rglob("MIBIG_HITS_EXACT_IDENTITY.tsv"))
    if not hit_paths:
        raise ValueError("RGGMCI_ATLAS_HIT_HOLD: no MIBIG_HITS_EXACT_IDENTITY.tsv files found")
    hit_rows = [row for path in hit_paths for row in _read(path)]
    ranked, details = build_atlas(_read(pair_table), _read(locus_table), hit_rows,
                                  read_mibig_rosters(mibig_archive))
    return write_atlas(out_dir, ranked, details)

#!/usr/bin/env python3
"""Reciprocal, core-weighted, boundary-aware BGC evidence ranking.

This reader-side tool combines package-backed MIBiG gene hits with the complete
CDS roster of the referenced MIBiG entry.  RG-GMCI is retained as a separate
linked-fragment routing channel and never increases the standalone biological
evidence score.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import tarfile
from collections import defaultdict
from pathlib import Path
import os as _os, sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    from mamey._gbk_shim import parse_genbank_text
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    from mamey._gbk_shim import parse_genbank_text

CLAIM = ("Pathway-family prioritization under admitted sequence and annotation evidence; "
         "not proof of exact product, complete pathway, expression, production, activity, "
         "novelty, physical cross-contig linkage, or scientific acceptance.")
GENUINE_TILING = {"COMPLEMENTARY_SPLIT", "TERMINUS_TRUNCATION_SPLIT"}
CORE_WEIGHTS = {"biosynthetic": 3.0, "biosynthetic-additional": 2.0}


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def norm_accession(value):
    return re.sub(r"\.\d+$", "", (value or "").strip())


def norm_gene(value):
    return re.sub(r"\.\d+$", "", (value or "").strip())


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with Path(path).open(newline="", errors="replace") as handle:
        delimiter = "\t" if Path(path).suffix.lower() == ".tsv" else ","
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_tsv(path, rows, fields=None):
    rows = list(rows)
    if fields is None:
        fields = list(rows[0]) if rows else []
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def one_file(package, suffix, required=True):
    files = sorted(Path(package).glob(f"*{suffix}"))
    if len(files) == 1:
        return files[0]
    if required:
        raise ValueError(f"{package}: expected one *{suffix}; found {len(files)}")
    return None


def discover_packages(values, root=None):
    found = [Path(v).expanduser().resolve() for v in values or []]
    if root:
        for cds in Path(root).expanduser().resolve().rglob("*_cds_table.csv"):
            if (cds.parent / "manifest.json").is_file():
                found.append(cds.parent)
    unique, seen = [], set()
    for package in found:
        if package not in seen:
            seen.add(package)
            unique.append(package)
    if not unique:
        raise ValueError("provide --package or --packages-root")
    return unique


def package_inputs(package):
    package = Path(package).resolve()
    manifest = package / "manifest.json"
    if not manifest.is_file():
        raise ValueError(f"{package}: manifest.json is required")
    return {
        "package": package,
        "manifest": manifest,
        "cds": one_file(package, "_cds_table.csv"),
        "hits": one_file(package, "_3_mibig_per_gene.csv"),
        "inventory": one_file(package, "_2_inventory.csv"),
        "rggmci": one_file(package, "_4A_RGGMCI_ranked_pairs.csv", required=False),
    }


def read_aliases(path):
    if not path:
        return {}
    aliases = {}
    for row in read_csv(path):
        source, display = row.get("source_strain", "").strip(), row.get("display_strain", "").strip()
        if not source or not display:
            raise ValueError("alias table requires source_strain and display_strain")
        aliases[source] = display
    return aliases


def identity(strain, contig, region, bgc):
    values = [strain, contig, region, bgc]
    if not all(values):
        raise ValueError(f"incomplete BGC identity: {values}")
    return " / ".join(values)


def qfirst(qualifiers, key):
    values = qualifiers.get(key, [])
    return values[0].strip() if values else ""


def mibig_reference_rosters(archive, required_accessions):
    """Read only requested records from a MIBiG GenBank tarball."""
    required = {norm_accession(x) for x in required_accessions if x}
    rosters = {}
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf:
            if not member.isfile() or not member.name.lower().endswith(('.gbk', '.gbff')):
                continue
            accession = norm_accession(Path(member.name).stem)
            if accession not in required:
                continue
            stream = tf.extractfile(member)
            if stream is None:
                continue
            records = parse_genbank_text(stream.read().decode("utf-8", errors="replace"))
            genes = []
            for record in records:
                for feat in record.features:
                    if feat.type != "CDS":
                        continue
                    ids = {norm_gene(qfirst(feat.qualifiers, k)) for k in ("locus_tag", "protein_id", "gene")}
                    ids.discard("")
                    kind = qfirst(feat.qualifiers, "gene_kind").lower()
                    weight = CORE_WEIGHTS.get(kind, 0.0)
                    genes.append({
                        "order": len(genes) + 1,
                        "ids": ids,
                        "primary_id": qfirst(feat.qualifiers, "locus_tag") or qfirst(feat.qualifiers, "protein_id") or f"CDS_{len(genes)+1}",
                        "gene_kind": kind or "unclassified",
                        "core_weight": weight,
                        "product": qfirst(feat.qualifiers, "product"),
                    })
            id_map = {}
            for gene in genes:
                for gid in gene["ids"]:
                    id_map[gid] = gene
            rosters[accession] = {"genes": genes, "id_map": id_map}
    return rosters


def wilson_lower(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / den)


def order_concordance(pairs):
    if len(pairs) < 3:
        return None
    ordered = sorted(pairs, key=lambda p: p["query_order"])
    refs = [p["reference_order"] for p in ordered]
    concordant = discordant = 0
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            if refs[i] == refs[j]:
                continue
            if refs[i] < refs[j]:
                concordant += 1
            else:
                discordant += 1
    total = concordant + discordant
    return max(concordant, discordant) / total if total else None


def greedy_pairs(hits, roster):
    edges = []
    for hit in hits:
        ref_gene = roster["id_map"].get(norm_gene(hit.get("subject_gene")))
        if not ref_gene:
            continue
        cov = min(100.0, number(hit.get("pct_coverage_interpretation") or hit.get("pct_coverage")))
        eff = number(hit.get("pct_identity")) * cov / 100.0
        edges.append((number(hit.get("blast_score")), eff, hit.get("query_gene", ""), ref_gene["order"], hit, ref_gene))
    edges.sort(key=lambda x: (-x[0], -x[1], x[2], x[3]))
    used_q, used_r, pairs = set(), set(), []
    for _, eff, query, ref_order, hit, ref_gene in edges:
        if not query or query in used_q or ref_order in used_r:
            continue
        used_q.add(query); used_r.add(ref_order)
        pairs.append({
            "query_gene": query,
            "reference_gene": ref_gene["primary_id"],
            "reference_order": ref_order,
            "reference_kind": ref_gene["gene_kind"],
            "reference_core_weight": ref_gene["core_weight"],
            "effective_similarity": eff,
            "pct_identity": number(hit.get("pct_identity")),
            "blast_score": number(hit.get("blast_score")),
        })
    return pairs


def best_rggmci_per_locus(rows, id_by_bgc):
    verdict_order = {"COMPLEMENTARY_SPLIT": 3, "TERMINUS_TRUNCATION_SPLIT": 2,
                     "MIXED_SUBJECT_SIGNAL": 1, "INSUFFICIENT_SUBJECT_DATA": 0,
                     "OVERLAPPING_PARALOG": -1}
    confidence_order = {"HIGH_RG_GMCI_RESCUE": 2, "MODERATE_RG_GMCI_CANDIDATE": 1,
                        "LOW_SHARED_REFERENCE_SIGNAL": 0}
    best, linked = {}, []
    for row in rows:
        a, b = row.get("bgc_a", ""), row.get("bgc_b", "")
        if a not in id_by_bgc or b not in id_by_bgc:
            continue
        verdict, conf = row.get("subject_tiling_verdict", ""), row.get("rggmci_confidence", "")
        key = (verdict_order.get(verdict, -2), confidence_order.get(conf, -1), number(row.get("rggmci_score")))
        enriched = dict(row)
        enriched.update({"identity_a": id_by_bgc[a], "identity_b": id_by_bgc[b]})
        if verdict in GENUINE_TILING and conf in {"HIGH_RG_GMCI_RESCUE", "MODERATE_RG_GMCI_CANDIDATE"}:
            linked.append(enriched)
        for bgc, partner in ((a, b), (b, a)):
            if bgc not in best or key > best[bgc][0]:
                best[bgc] = (key, enriched, partner)
    return {k: v[1:] for k, v in best.items()}, linked


def evidence_tier(metrics):
    n = metrics["matched_gene_pairs"]
    rec = metrics["reciprocal_coverage_f1"]
    core = metrics["reference_core_completeness"]
    sim = metrics["median_effective_similarity"]
    syn = metrics["orientation_aware_order_concordance"]
    boundary = metrics["boundary"]
    synteny_ok = syn is None or syn >= 0.60
    if n >= 4 and rec >= .60 and core >= .70 and sim >= 60 and synteny_ok and boundary == "Interior":
        return "A_STRONG_PATHWAY_FAMILY_ARCHITECTURE"
    if n >= 3 and rec >= .35 and core >= .40 and sim >= 45 and synteny_ok:
        return "B_SUPPORTED_PARTIAL_ARCHITECTURE"
    if metrics.get("rggmci_genuine_high"):
        return "B_SUPPORTED_LINKED_FRAGMENT_CANDIDATE"
    if n >= 2 or metrics.get("clear_specific_gene_count", 0) >= 1:
        return "C_LOCALIZED_OR_INCOMPLETE_REFERENCE_MATCH"
    if n >= 1:
        return "D_WEAK_OR_DIFFUSE_SIMILARITY"
    return "U_NO_ADMITTED_MIBIG_REFERENCE_MATCH"


def analyze(packages, archive, out, clear_dir=None, aliases=None):
    out = Path(out).expanduser().resolve(); out.mkdir(parents=True, exist_ok=True)
    aliases = aliases or {}
    specificity = defaultdict(dict)
    clear_dir = Path(clear_dir).resolve() if clear_dir else None
    if clear_dir:
        for row in read_csv(clear_dir / "ALL_GENE_TOP_VS_SECOND_MIBIG.tsv"):
            specificity[row["complete_identity"]][row["query_gene"]] = row

    package_data, needed, sources = [], set(), []
    for package in packages:
        inp = package_inputs(package)
        data = {k: read_csv(inp[k]) if inp.get(k) and k in {"cds", "hits", "inventory", "rggmci"} else inp.get(k)
                for k in inp}
        package_data.append(data)
        needed.update(norm_accession(r.get("mibig_accession")) for r in data["hits"] if r.get("mibig_accession"))
        for role in ("manifest", "cds", "hits", "inventory", "rggmci"):
            path = inp.get(role)
            if path:
                sources.append({"package": str(package), "role": role, "path": str(path),
                                "sha256": sha256(path), "bytes": path.stat().st_size})
    source_strains = []
    for data in package_data:
        if not data["cds"]:
            raise ValueError(f"{data['package']}: empty CDS table")
        source_strains.append(data["cds"][0].get("strain", ""))
    duplicates = sorted({s for s in source_strains if source_strains.count(s) > 1})
    if duplicates:
        raise ValueError("multiple packages discovered for source strain(s): " + ", ".join(duplicates))
    archive = Path(archive).expanduser().resolve()
    sources.append({"package": "MIBiG", "role": "reference_archive", "path": str(archive),
                    "sha256": sha256(archive), "bytes": archive.stat().st_size})
    rosters = mibig_reference_rosters(archive, needed)

    ranking, reciprocal, core_rows, rg_rows, linked_rows = [], [], [], [], []
    for data in package_data:
        cds_by_bgc, hits_by_bgc = defaultdict(list), defaultdict(list)
        for row in data["cds"]: cds_by_bgc[row.get("bgc_id", "")].append(row)
        for row in data["hits"]: hits_by_bgc[row.get("bgc_id", "")].append(row)
        inv = {r.get("BGC_ID", ""): r for r in data["inventory"]}
        first_cds = next(iter(cds_by_bgc.values()))[0]
        source_strain = first_cds.get("strain", "")
        strain = aliases.get(source_strain, source_strain)
        id_by_bgc = {}
        for bgc, rows in cds_by_bgc.items():
            id_by_bgc[bgc] = identity(strain, rows[0].get("contig", ""), rows[0].get("region", ""), bgc)
        rg_best, linked = best_rggmci_per_locus(data.get("rggmci") or [], id_by_bgc)
        for row in linked:
            linked_rows.append({
                "strain": strain, "pair": row.get("pair", ""), "identity_a": row["identity_a"],
                "identity_b": row["identity_b"], "rggmci_score": row.get("rggmci_score", ""),
                "rggmci_confidence": row.get("rggmci_confidence", ""),
                "subject_tiling_verdict": row.get("subject_tiling_verdict", ""),
                "strong_supporting_references": row.get("strong_supporting_references", ""),
                "terminus_override_note": row.get("terminus_override_note", ""),
                "interpretation_guard": row.get("interpretation_guard", ""), "claim_ceiling": CLAIM,
            })
        for bgc, cds_rows in cds_by_bgc.items():
            ident = id_by_bgc[bgc]; total_query = len(cds_rows); qorder = {r.get("locus_tag", ""): number(r.get("order")) for r in cds_rows}
            by_ref = defaultdict(list)
            for hit in hits_by_bgc.get(bgc, []): by_ref[norm_accession(hit.get("mibig_accession"))].append(hit)
            candidates = []
            for accession, hits in by_ref.items():
                roster = rosters.get(accession)
                if not roster or not roster["genes"]:
                    continue
                pairs = greedy_pairs(hits, roster)
                for pair in pairs: pair["query_order"] = qorder.get(pair["query_gene"], 0)
                matched_core = sum(p["reference_core_weight"] for p in pairs)
                total_core = sum(g["core_weight"] for g in roster["genes"])
                candidates.append((matched_core, len(pairs), sum(p["blast_score"] for p in pairs), accession, pairs, roster))
            candidates.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3]))
            if candidates:
                _, _, _, accession, pairs, roster = candidates[0]
            else:
                accession, pairs, roster = "", [], {"genes": []}
            matched = len(pairs); total_ref = len(roster["genes"])
            qcov = matched / total_query if total_query else 0
            rcov = matched / total_ref if total_ref else 0
            reciprocal_f1 = 2 * qcov * rcov / (qcov + rcov) if qcov + rcov else 0
            total_core = sum(g["core_weight"] for g in roster["genes"])
            matched_core = sum(p["reference_core_weight"] for p in pairs)
            core_fraction = matched_core / total_core if total_core else 0
            similarities = [p["effective_similarity"] for p in pairs]
            median_sim = statistics.median(similarities) if similarities else 0
            synteny = order_concordance(pairs)
            spec_rows = [specificity[ident].get(p["query_gene"]) for p in pairs]
            gaps = [number(r.get("top_minus_second_identity_x_coverage_points")) for r in spec_rows if r and r.get("top_minus_second_identity_x_coverage_points") != ""]
            median_gap = statistics.median(gaps) if gaps else 0
            clear_count = sum(1 for r in spec_rows if r and r.get("match_band") == "CLEAR_SPECIFIC_HIGH")
            dominant_coherence = matched / max(1, len({h.get("query_gene", "") for h in hits_by_bgc.get(bgc, []) if h.get("query_gene")}))
            boundary = inv.get(bgc, {}).get("Boundary", "")
            boundary_penalty = 0 if boundary == "Interior" else 8 if boundary == "Edge" else 12 if boundary == "Full-contig" else 8
            rg = rg_best.get(bgc)
            rgrow, partner = rg if rg else ({}, "")
            genuine = rgrow.get("subject_tiling_verdict") in GENUINE_TILING
            rg_high = genuine and rgrow.get("rggmci_confidence") == "HIGH_RG_GMCI_RESCUE"
            rg_mod = genuine and rgrow.get("rggmci_confidence") == "MODERATE_RG_GMCI_CANDIDATE"
            wilson = wilson_lower(matched, total_query)
            components = {
                "reciprocal": 25 * reciprocal_f1,
                "core": 25 * core_fraction,
                "similarity": 15 * median_sim / 100,
                "specificity": 10 * min(1, max(0, median_gap) / 50),
                "coherence": 10 * min(1, dominant_coherence),
                "synteny": 10 * (synteny if synteny is not None else 0),
                "wilson": 5 * wilson,
            }
            biological = max(0, sum(components.values()) - boundary_penalty)
            rg_bonus = 4 if rg_high else 2 if rg_mod else 0
            metrics = {
                "matched_gene_pairs": matched, "reciprocal_coverage_f1": reciprocal_f1,
                "reference_core_completeness": core_fraction, "median_effective_similarity": median_sim,
                "orientation_aware_order_concordance": synteny, "boundary": boundary,
                "clear_specific_gene_count": clear_count, "rggmci_genuine_high": rg_high,
            }
            tier = evidence_tier(metrics)
            product = next((h.get("mibig_compound", "") for h in hits_by_bgc.get(bgc, []) if norm_accession(h.get("mibig_accession")) == accession), "")
            base = {
                "complete_identity": ident, "strain": strain, "bgc_alias": bgc,
                "current_antismash_products": inv.get(bgc, {}).get("Products", ""), "boundary": boundary,
                "dominant_mibig_accession": accession, "dominant_mibig_product": product,
                "evidence_tier": tier, "standalone_biological_evidence_score_0_100": round(biological, 2),
                "review_priority_score_0_100": round(min(100, biological + rg_bonus), 2),
                "total_query_cds": total_query, "total_reference_cds": total_ref,
                "matched_gene_pairs": matched, "query_coverage": round(qcov, 4),
                "reference_coverage": round(rcov, 4), "reciprocal_coverage_f1": round(reciprocal_f1, 4),
                "wilson_stabilized_query_hit_fraction": round(wilson, 4),
                "reference_core_weight_total": round(total_core, 2), "matched_reference_core_weight": round(matched_core, 2),
                "reference_core_completeness": round(core_fraction, 4),
                "median_effective_similarity": round(median_sim, 2), "median_top_vs_second_gap": round(median_gap, 2),
                "clear_specific_gene_count": clear_count, "dominant_reference_coherence": round(min(1, dominant_coherence), 4),
                "orientation_aware_order_concordance": "" if synteny is None else round(synteny, 4),
                "boundary_penalty": boundary_penalty, "rggmci_routing_bonus": rg_bonus,
                "rggmci_partner_identity": id_by_bgc.get(partner, ""),
                "rggmci_confidence": rgrow.get("rggmci_confidence", ""),
                "rggmci_subject_tiling_verdict": rgrow.get("subject_tiling_verdict", ""),
                "rggmci_score": rgrow.get("rggmci_score", ""),
                "rggmci_interpretation_guard": rgrow.get("interpretation_guard", ""),
                "claim_ceiling": CLAIM,
            }
            ranking.append(base)
            reciprocal.append({k: base[k] for k in ["complete_identity", "dominant_mibig_accession", "dominant_mibig_product", "total_query_cds", "total_reference_cds", "matched_gene_pairs", "query_coverage", "reference_coverage", "reciprocal_coverage_f1", "orientation_aware_order_concordance", "claim_ceiling"]})
            core_rows.append({k: base[k] for k in ["complete_identity", "dominant_mibig_accession", "reference_core_weight_total", "matched_reference_core_weight", "reference_core_completeness", "median_effective_similarity", "median_top_vs_second_gap", "clear_specific_gene_count", "claim_ceiling"]})
            rg_rows.append({k: base[k] for k in ["complete_identity", "boundary", "boundary_penalty", "rggmci_partner_identity", "rggmci_confidence", "rggmci_subject_tiling_verdict", "rggmci_score", "rggmci_routing_bonus", "rggmci_interpretation_guard", "claim_ceiling"]})

    tier_order = {"A": 0, "B": 1, "C": 2, "D": 3, "U": 4}
    ranking.sort(key=lambda r: (tier_order.get(r["evidence_tier"][0], 9), -number(r["standalone_biological_evidence_score_0_100"]), -number(r["review_priority_score_0_100"]), r["complete_identity"]))
    strain_counts = defaultdict(int)
    for index, row in enumerate(ranking, 1):
        row["definitive_rank_all_bgcs"] = index
        strain_counts[row["strain"]] += 1
        row["definitive_rank_within_strain"] = strain_counts[row["strain"]]
    rank_fields = ["definitive_rank_all_bgcs", "definitive_rank_within_strain"] + [k for k in ranking[0] if k not in {"definitive_rank_all_bgcs", "definitive_rank_within_strain"}]
    write_tsv(out / "ALL_BGC_DEFINITIVE_EVIDENCE_RANK.tsv", ranking, rank_fields)
    write_tsv(out / "ALL_BGC_RECIPROCAL_REFERENCE_METRICS.tsv", reciprocal)
    write_tsv(out / "ALL_BGC_CORE_GENE_EVIDENCE.tsv", core_rows)
    write_tsv(out / "ALL_BGC_RGGMCI_BOUNDARY_EVIDENCE.tsv", rg_rows)
    write_tsv(out / "RGGMCI_LINKED_UNIT_REVIEW.tsv", sorted(linked_rows, key=lambda r: (r["strain"], -number(r["rggmci_score"]), r["pair"])))
    summary = []
    for tier in sorted({r["evidence_tier"] for r in ranking}):
        rows = [r for r in ranking if r["evidence_tier"] == tier]
        summary.append({"evidence_tier": tier, "bgc_count": len(rows), "strain_count": len({r["strain"] for r in rows}),
                        "median_standalone_score": round(statistics.median(number(r["standalone_biological_evidence_score_0_100"]) for r in rows), 2),
                        "claim_ceiling": CLAIM})
    write_tsv(out / "TIER_SUMMARY.tsv", summary)
    for strain in sorted({r["strain"] for r in ranking}):
        folder = out / "PER_STRAIN" / re.sub(r"[^A-Za-z0-9._-]+", "_", strain)
        subset = [r for r in ranking if r["strain"] == strain]
        write_tsv(folder / "DEFINITIVE_EVIDENCE_RANK.tsv", subset, rank_fields)
        write_tsv(folder / "RGGMCI_BOUNDARY_EVIDENCE.tsv", [r for r in rg_rows if r["complete_identity"].startswith(strain + " / ")])
    write_tsv(out / "SOURCE_HASHES.tsv", sources)
    receipt = {
        "schema": "definitive-bgc-ranker-receipt-v1", "status": "COMPLETE",
        "packages": len(packages), "bgcs": len(ranking), "strains": len({r["strain"] for r in ranking}),
        "mibig_accessions_required": len(needed), "mibig_rosters_resolved": len(rosters),
        "rggmci_linked_units_admitted": len(linked_rows), "claim_ceiling": CLAIM,
        "outputs": {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in sorted(out.glob("*.tsv"))},
    }
    (out / "RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", action="append", default=[])
    p.add_argument("--packages-root")
    p.add_argument("--mibig-gbk-archive", required=True)
    p.add_argument("--clear-match-results")
    p.add_argument("--strain-aliases")
    p.add_argument("--out", required=True)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    receipt = analyze(discover_packages(args.package, args.packages_root), args.mibig_gbk_archive,
                      args.out, args.clear_match_results, read_aliases(args.strain_aliases))
    _sys.stdout.write(json.dumps(receipt, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

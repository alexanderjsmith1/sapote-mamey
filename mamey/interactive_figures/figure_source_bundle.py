#!/usr/bin/env python3
"""Build a provenance-rich cohort figure source bundle from sealed packages.

The bundle is additive and post-seal. It reads only named members from package
ZIPs referenced by ``AS_All_Strains_Widget_Data.json`` and emits compact tables
for BGC/class co-occurrence, machinery-role assignments, per-gene MIBiG
convergence, and antiSMASH module/substrate calls. Missing members are recorded
as missing evidence; they are never converted to biological negatives.
"""

from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from ..console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from mamey.console import emit

import argparse
import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import io
import json
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Sequence

from .figure_set_registry import GLOBAL_CLAIM_CEILING, PROFILE
from .widget_data import machinery_role


SCHEMA_VERSION = "sapote-mamey.codex-figure-source-bundle.v2"
SELECTED_CSV_SUFFIXES = (
    "_2_inventory.csv",
    "_cds_table.csv",
    "_3_mibig_per_gene.csv",
    "_3_antismash_modules.csv",
    "_4_triage_board.csv",
    "_domains.csv",
    "_4A_RGGMCI_evidence.csv",
)
SELECTED_JSON_SUFFIXES = (
    "_1_intake.json",
    "_3_scan_states.json",
    "deep_data.json",
    "gate_validation.json",
    "Project_Memory_Snapshot.json",
    "manifest.json",
)
SELECTED_SUFFIXES = SELECTED_CSV_SUFFIXES + SELECTED_JSON_SUFFIXES
REQUIRED_SUFFIXES = (
    "_2_inventory.csv", "_cds_table.csv", "_3_mibig_per_gene.csv", "_3_antismash_modules.csv",
)
TAILORING_PATTERNS = {
    "P450-like": re.compile(r"\bp450\b|cytochrome p450", re.I),
    "Methyltransferase-like": re.compile(r"methyltransferase|methyltransf", re.I),
    "Glycosyltransferase-like": re.compile(r"glycosyltransferase|glycos[_ -]?transf", re.I),
    "Oxidoreductase-like": re.compile(r"oxidoreductase|dehydrogenase|\breductase\b", re.I),
    "Acyltransferase-like": re.compile(r"acyltransferase|acyl[_ -]?transf", re.I),
    "Halogenase-like": re.compile(r"halogenase", re.I),
    "Thioesterase-like": re.compile(r"thioesterase", re.I),
    "Aminotransferase-like": re.compile(r"aminotransferase", re.I),
}
REGULATOR_PATTERNS = {
    "SARP-like": re.compile(r"\bsarp\b", re.I),
    "LuxR-like": re.compile(r"\bluxr\b", re.I),
    "TetR-like": re.compile(r"\btetr\b", re.I),
    "MarR-like": re.compile(r"\bmarr\b", re.I),
    "LysR-like": re.compile(r"\blysr\b", re.I),
    "LAL-like": re.compile(r"\blal\b|large atp-binding regulator", re.I),
    "Response-regulator-like": re.compile(r"response regulator", re.I),
    "Sigma-factor-like": re.compile(r"sigma factor", re.I),
    "Generic-regulatory": re.compile(r"regulatory|transcriptional regulator", re.I),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def _float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _natural_bgc(value: str) -> tuple[int, str]:
    digits = "".join(ch for ch in value if ch.isdigit())
    return (int(digits) if digits else 10**9, value)


def _write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str] | None = None) -> None:
    if fields is None:
        fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _member(zf: zipfile.ZipFile, suffix: str) -> str | None:
    hits = sorted(name for name in zf.namelist() if name.endswith(suffix))
    return hits[0] if hits else None


def _median(values: Iterable[float]) -> float | None:
    seq = list(values)
    return float(statistics.median(seq)) if seq else None


def build_source_bundle(widget_data: str | Path, package_dir: str | Path, outdir: str | Path) -> dict[str, Any]:
    widget_path = Path(widget_data).resolve()
    package_root = Path(package_dir).resolve()
    destination = Path(outdir).resolve()
    payload = json.loads(widget_path.read_text(encoding="utf-8"))
    strains = payload.get("strains") or {}
    if not strains:
        raise ValueError("widget data has no strains")
    for strain, record in strains.items():
        include_by_default = record.get("include_by_default", True)
        cohort_role = str(record.get("cohort_role") or "STUDY").strip().upper()
        if not isinstance(include_by_default, bool):
            raise ValueError("FIGURE_INCLUDE_BY_DEFAULT_INVALID: include_by_default must be boolean")
        if cohort_role == "EXTERNAL_BENCHMARK" and include_by_default:
            raise ValueError("FIGURE_EXTERNAL_BENCHMARK_DEFAULT_ON: external benchmarks must be default-off")
    destination.mkdir(parents=True, exist_ok=True)

    bgc_records: list[dict[str, Any]] = []
    class_memberships: list[dict[str, Any]] = []
    class_pairs: list[dict[str, Any]] = []
    gene_assignments: list[dict[str, Any]] = []
    mibig_gene_rows: list[dict[str, Any]] = []
    mibig_bgc_rows: list[dict[str, Any]] = []
    module_rows: list[dict[str, Any]] = []
    module_domain_rows: list[dict[str, Any]] = []
    module_substrate_rows: list[dict[str, Any]] = []
    gene_feature_rows: list[dict[str, Any]] = []
    cds_summary_rows: list[dict[str, Any]] = []
    extended_bgc_rows: list[dict[str, Any]] = []
    domain_family_rows: list[dict[str, Any]] = []
    rgg_pair_rows: list[dict[str, Any]] = []
    rgg_bgc_rows: list[dict[str, Any]] = []
    evidence_channel_rows: list[dict[str, Any]] = []
    strain_context_rows: list[dict[str, Any]] = []
    domain_category_rows: list[dict[str, Any]] = []
    cassette_family_rows: list[dict[str, Any]] = []
    resistance_family_rows: list[dict[str, Any]] = []
    manifest_scan_rows: list[dict[str, Any]] = []
    member_ledger: list[dict[str, Any]] = []
    package_states: list[dict[str, Any]] = []

    for strain in sorted(strains, key=lambda s: _natural_bgc(s.replace("AS-", "BGC"))):
        strain_record = strains[strain]
        package_name = str(strain_record.get("package") or "")
        package_path = package_root / package_name
        governance = str(strain_record.get("governance") or "UNRESOLVED")
        host = str((strain_record.get("hostContext") or {}).get("group") or "UNRESOLVED")
        cohort_role = str(strain_record.get("cohort_role") or "STUDY").strip().upper()
        include_by_default = strain_record.get("include_by_default", True)
        if not package_name or not package_path.is_file():
            package_states.append({"strain": strain, "package": package_name, "state": "MISSING_PACKAGE"})
            strain_context_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "cohort_role": cohort_role, "include_by_default": include_by_default,
                "taxonomy": "", "genus": "", "genome_bp": "", "corrected_bgcs": "",
                "assembly_tier": "", "snapshot_state": "MISSING_PACKAGE",
            })
            continue
        package_states.append({"strain": strain, "package": package_name, "state": "PRESENT"})
        with zipfile.ZipFile(package_path) as zf:
            selected: dict[str, Any] = {}
            for suffix in SELECTED_SUFFIXES:
                member = _member(zf, suffix)
                if member is None:
                    selected[suffix] = None
                    member_ledger.append({
                        "strain": strain, "governance": governance, "package": package_name,
                        "member_suffix": suffix, "member_path": "", "state": "MISSING",
                        "bytes": 0, "sha256": "",
                    })
                    continue
                raw = zf.read(member)
                selected[suffix] = (json.loads(raw) if suffix in SELECTED_JSON_SUFFIXES else _rows(raw))
                member_ledger.append({
                    "strain": strain, "governance": governance, "package": package_name,
                    "member_suffix": suffix, "member_path": member, "state": "PRESENT",
                    "bytes": len(raw), "sha256": _sha256_bytes(raw),
                })

        snapshot = selected["Project_Memory_Snapshot.json"] or {}
        taxonomy = str(snapshot.get("taxonomy") or "").strip() if isinstance(snapshot, dict) else ""
        genus = taxonomy.split()[0] if taxonomy else ""
        assembly = snapshot.get("assembly") or {} if isinstance(snapshot, dict) else {}
        bgc_counts = snapshot.get("bgc_counts") or {} if isinstance(snapshot, dict) else {}
        snapshot_state = "PRESENT" if snapshot else "MISSING"
        manifest = selected["manifest.json"] or {}
        intake = selected["_1_intake.json"] or {}
        antismash_version = str(
            (manifest.get("antismash_version") if isinstance(manifest, dict) else "")
            or (intake.get("antismash_version") if isinstance(intake, dict) else "") or ""
        ).strip()
        antismash_version_source = (
            "manifest.json.antismash_version"
            if isinstance(manifest, dict) and manifest.get("antismash_version")
            else ("*_1_intake.json.antismash_version" if antismash_version else "MISSING")
        )
        strain_context_rows.append({
            "strain": strain, "governance": governance, "host_group": host,
            "cohort_role": cohort_role, "include_by_default": include_by_default,
            "taxonomy": taxonomy, "genus": genus,
            "genome_bp": assembly.get("genome_bp", "") if isinstance(assembly, dict) else "",
            "corrected_bgcs": bgc_counts.get("corrected", "") if isinstance(bgc_counts, dict) else "",
            "assembly_tier": bgc_counts.get("assembly_tier", "") if isinstance(bgc_counts, dict) else "",
            "snapshot_state": snapshot_state,
            "antismash_version": antismash_version,
            "antismash_version_source": antismash_version_source,
        })
        scans = snapshot.get("source_scans") or {} if isinstance(snapshot, dict) else {}
        manifest_scans = manifest.get("source_scans") or {} if isinstance(manifest, dict) else {}
        for scan_name in ("cctt", "transporters", "regulators"):
            scan = manifest_scans.get(scan_name) or {} if isinstance(manifest_scans, dict) else {}
            hits = scan.get("hits") or {} if isinstance(scan, dict) else {}
            if not isinstance(hits, dict):
                continue
            for token, token_hits in sorted(hits.items()):
                if not isinstance(token_hits, list):
                    continue
                manifest_scan_rows.append({
                    "strain": strain, "governance": governance, "host_group": host,
                    "cohort_role": cohort_role, "include_by_default": include_by_default,
                    "scan": scan_name, "token": str(token), "hit_count": len(token_hits),
                    "value_state": "OBSERVED_ZERO" if not token_hits else "POPULATED",
                    "source_state": str(scan.get("status") or "MISSING"),
                    "source_field": f"manifest.json.source_scans.{scan_name}.hits",
                })
        domain_scan = scans.get("domain_architecture") or {} if isinstance(scans, dict) else {}
        domain_acc: Counter[str] = Counter()
        for detail in (domain_scan.get("per_bgc") or {}).values() if isinstance(domain_scan, dict) else ():
            for category, count in (detail.get("domain_counts") or {}).items() if isinstance(detail, dict) else ():
                value = _float(count)
                if value is not None:
                    domain_acc[str(category)] += int(value)
        for category, count in sorted(domain_acc.items()):
            domain_category_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "cohort_role": cohort_role, "include_by_default": include_by_default,
                "domain_category": category, "count": count,
                "source_state": str(domain_scan.get("status") or snapshot_state),
            })
        for output, scan_name, family_name in (
            (cassette_family_rows, "cassettes", "cassette_family"),
            (resistance_family_rows, "resistance", "resistance_family"),
        ):
            scan = scans.get(scan_name) or {} if isinstance(scans, dict) else {}
            counts = scan.get("counts") or {} if isinstance(scan, dict) else {}
            for family, count in sorted(counts.items()):
                value = _float(count)
                if value is None:
                    continue
                output.append({
                    "strain": strain, "governance": governance, "host_group": host,
                    "cohort_role": cohort_role, "include_by_default": include_by_default,
                    family_name: str(family), "count": int(value),
                    "source_state": str(scan.get("status") or snapshot_state),
                })

        inventory = selected["_2_inventory.csv"] or []
        inventory_map = {
            (row.get("BGC_ID") or "").strip(): row
            for row in inventory
            if (row.get("BGC_ID") or "").strip()
        }
        bgc_context: dict[str, dict[str, Any]] = {}
        for row in inventory:
            bgc_id = (row.get("BGC_ID") or "").strip()
            if not bgc_id:
                continue
            products = sorted({token.strip() for token in (row.get("Products") or "").split(";") if token.strip()})
            boundary = (row.get("Boundary") or "MISSING").strip() or "MISSING"
            node_id = (row.get("Node_ID") or "").strip()
            node_or_contig = (row.get("Contig") or node_id).strip()
            region = (row.get("antiSMASH_Region") or "").strip()
            complete_identity = f"{strain} / {node_or_contig} / {region} / {bgc_id}" if node_or_contig and region else ""
            context = {"boundary": boundary, "products": products, "node_id": node_id,
                       "node_or_contig": node_or_contig,
                       "region": region, "complete_identity": complete_identity}
            bgc_context[bgc_id] = context
            bgc_records.append({
                "strain": strain, "governance": governance, "host_group": host,
                "package": package_name, "bgc_id": bgc_id, "boundary": boundary,
                "node_id": node_id, "node_or_contig": node_or_contig,
                "region": region, "complete_identity": complete_identity,
                "length_kb": row.get("Length_kb") or "", "products": "; ".join(products),
                "class_count": len(products), "hybrid_state": "HYBRID" if len(products) > 1 else "SINGLE_CLASS",
                "kcb_state": "POPULATED" if (row.get("KCB_top") or "").strip() else "OBSERVED_ZERO",
                "kcb_top": row.get("KCB_top") or "", "kcb_score": row.get("KCB_score") or "",
                "tta_tier": row.get("TTA_tier") or "", "resistance_tier": row.get("Resistance_tier") or "",
                "claim_ceiling": row.get("claim_ceiling") or row.get("product_claim_ceiling") or "",
                "needs_manual_kcb_check": row.get("needs_manual_kcb_check") or "",
                "parse_confidence": row.get("parse_confidence") or "",
                "closest_product_provenance": row.get("closest_product_provenance") or "",
                "denominator_type": row.get("denominator_type") or "",
            })
            for product in products:
                class_memberships.append({
                    "strain": strain, "governance": governance, "host_group": host,
                    "bgc_id": bgc_id, "boundary": boundary, "product_class": product,
                })
            for class_a, class_b in combinations(products, 2):
                class_pairs.append({
                    "strain": strain, "governance": governance, "host_group": host,
                    "bgc_id": bgc_id, "boundary": boundary,
                    "class_a": class_a, "class_b": class_b,
                })

        triage_map = {
            (row.get("BGC_ID") or "").strip(): row
            for row in (selected["_4_triage_board.csv"] or [])
            if (row.get("BGC_ID") or "").strip()
        }
        deep_payload = selected["deep_data.json"] or {}
        # v9.7.408 (Codex hostile audit Q2/Q5): the modules table carries several feature_type values —
        # aSDomain (an HMM domain call), aSModule (a module marker whose `domain` cell holds the tool
        # name "antismash"), ACTIVE_SITE_PAIRING (a residue-presence call per domain, antiSMASH
        # active_site_finder), NRPS_PKS_CONSENSUS (substrate consensus), and others. Only aSDomain rows
        # are domains; counting every row's `domain` cell put 163 "antismash" tokens at the top of a
        # domain tally in one strain and reported active-site evidence as structurally unavailable while 367
        # typed active-site rows sat in that strain's file. A missing feature_type column (older packages,
        # fixtures) is treated as aSDomain so behaviour there is unchanged.
        active_site_by_bgc: Counter[str] = Counter()
        active_site_unmapped_rows = 0
        for _mrow in selected["_3_antismash_modules.csv"] or []:
            if (_mrow.get("feature_type") or "").strip().upper() == "ACTIVE_SITE_PAIRING":
                _bid = (_mrow.get("bgc_id") or "").strip()
                if _bid and _bid.upper() != "UNMAPPED" and (_mrow.get("mapping_status") or "").upper() == "MAPPED":
                    active_site_by_bgc[_bid] += 1
                else:
                    active_site_unmapped_rows += 1
        profile_map = {
            (row.get("bgc_id") or "").strip(): row
            for row in (deep_payload.get("bgc_profile") or [])
            if (row.get("bgc_id") or "").strip()
        }
        # Keep one deterministic source-row projection per physical CDS. The
        # retained BGC assignment stays explicit for class/boundary joins.
        raw_assignments: list[dict[str, Any]] = []
        seen_assignment: set[tuple[str, str, str, str, str]] = set()
        # Match the governed widget contract exactly: physical CDS are first
        # projected with first-row retention on contig+locus+start+end, and
        # only then assigned a machinery role by declared precedence.
        deduped_cds: dict[tuple[str, str, str, str], dict[str, str]] = {}
        for row in selected["_cds_table.csv"] or []:
            physical_key = (
                (row.get("contig") or "").strip(), (row.get("locus_tag") or "").strip(),
                (row.get("start") or "").strip(), (row.get("end") or "").strip(),
            )
            deduped_cds.setdefault(physical_key, row)
        cds_by_bgc: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)
        tta_gene_by_bgc: Counter[str] = Counter()
        tta_codon_by_bgc: Counter[str] = Counter()
        for key, row in deduped_cds.items():
            bgc_id = (row.get("bgc_id") or "").strip()
            if not bgc_id:
                continue
            cds_by_bgc[bgc_id].add(key)
            tta_count = int(_float(row.get("tta_codons")) or 0)
            tta_codon_by_bgc[bgc_id] += tta_count
            if tta_count > 0:
                tta_gene_by_bgc[bgc_id] += 1
        for key, row in deduped_cds.items():
            bgc_id = (row.get("bgc_id") or "").strip()
            context = bgc_context.get(bgc_id, {"boundary": "MISSING", "products": []})
            annotation_text = " ".join((row.get("product") or "", row.get("sec_met_domains") or "", row.get("gene_functions") or ""))
            for feature_group, patterns in (("TAILORING_LIKE", TAILORING_PATTERNS), ("REGULATOR_LIKE", REGULATOR_PATTERNS)):
                for feature_family, pattern in patterns.items():
                    if pattern.search(annotation_text):
                        gene_feature_rows.append({
                            "strain": strain, "governance": governance, "host_group": host,
                            "bgc_id": bgc_id, "boundary": context["boundary"],
                            "products": "; ".join(context["products"]),
                            "contig": key[0], "locus_tag": key[1], "start": key[2], "end": key[3],
                            "physical_key": "|".join((strain, *key)),
                            "feature_group": feature_group, "feature_family": feature_family,
                            "evidence_basis": "annotation token or domain-family text",
                        })
            role = machinery_role(row.get("gene_functions") or "")
            if role is None:
                continue
            assignment_key = (bgc_id, *key)
            if assignment_key in seen_assignment:
                continue
            seen_assignment.add(assignment_key)
            length_value = _float(row.get("length_aa"))
            raw_assignments.append({
                "strain": strain, "governance": governance, "host_group": host,
                "bgc_id": bgc_id, "boundary": context["boundary"],
                "products": "; ".join(context["products"]), "role": role,
                "contig": key[0], "locus_tag": key[1], "start": key[2], "end": key[3],
                "length_aa": row.get("length_aa") or "",
                "length_state": "POPULATED" if length_value is not None and length_value > 0 else "MISSING_OR_NONPOSITIVE",
                "physical_key": "|".join((strain, *key)),
            })
        grouped_assignments: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in raw_assignments:
            grouped_assignments[row["physical_key"]].append(row)
        for physical_rows in grouped_assignments.values():
            physical_rows.sort(key=lambda r: _natural_bgc(r["bgc_id"]))
            multiplicity = len(physical_rows)
            for index, row in enumerate(physical_rows):
                row["physical_assignment_multiplicity"] = multiplicity
                row["primary_physical_assignment"] = "YES" if index == 0 else "NO"
                gene_assignments.append(row)

        for bgc_id, context in sorted(bgc_context.items(), key=lambda item: _natural_bgc(item[0])):
            inventory_row = inventory_map.get(bgc_id, {})
            length_kb = _float(inventory_row.get("Length_kb"))
            cds_count = len(cds_by_bgc.get(bgc_id, set()))
            cds_summary_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "bgc_id": bgc_id, "boundary": context["boundary"],
                "products": "; ".join(context["products"]), "length_kb": length_kb if length_kb is not None else "",
                "physical_cds": cds_count,
                "cds_per_10kb": (10.0 * cds_count / length_kb) if length_kb and length_kb > 0 else "",
                "tta_bearing_cds": tta_gene_by_bgc[bgc_id], "tta_codons_cds_table": tta_codon_by_bgc[bgc_id],
                "source_state": "POPULATED" if selected["_cds_table.csv"] is not None else "MISSING",
            })

            triage = triage_map.get(bgc_id, {})
            profile = profile_map.get(bgc_id, {})
            active_sites = deep_payload.get("active_sites") or []
            resistance_tier = (
                profile.get("resistance_tier")
                or triage.get("Resistance_tier")
                or inventory_row.get("Resistance_tier")
                or ""
            ).strip()
            cctt = (profile.get("cctt_triggers") or triage.get("CCTT_triggers") or "").strip()
            rgg_support = (triage.get("RGGMCI_support") or "").strip()
            extended_bgc_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "bgc_id": bgc_id, "boundary": context["boundary"], "products": "; ".join(context["products"]),
                "node_id": context.get("node_id", ""), "region": context.get("region", ""),
                "node_or_contig": context.get("node_or_contig", ""),
                "complete_identity": context.get("complete_identity", ""),
                "arch": triage.get("Arch") or inventory_row.get("Arch") or "",
                "arch_capacity": triage.get("Arch_Capacity", ""), "class_conf": triage.get("Class_Conf", ""),
                "length_kb": length_kb if length_kb is not None else "", "physical_cds": cds_count,
                "cds_per_10kb": (10.0 * cds_count / length_kb) if length_kb and length_kb > 0 else "",
                "tta_codons": profile.get("tta_codons", tta_codon_by_bgc[bgc_id]),
                "tta_cds": profile.get("tta_cds", tta_gene_by_bgc[bgc_id]),
                "tta_tier": inventory_row.get("TTA_tier") or "",
                "resistance_tier": resistance_tier,
                "transporter_domains": profile.get("Transporter", ""), "regulator_domains": profile.get("Regulator", ""),
                "oxidoreductase_domains": profile.get("Oxidoreductase", ""), "total_domains": profile.get("total_domains", ""),
                "cctt_triggers": cctt, "cctt_trigger_count": len([x for x in re.split(r"[;,]", cctt) if x.strip()]),
                "ab_auto": triage.get("AB_auto", ""), "af_auto": triage.get("AF_auto", ""),
                "novelty_auto": triage.get("Novelty_auto", ""), "lead_tier_auto": triage.get("Lead_tier_auto", ""),
                "primary_metab_flag": triage.get("Primary_metab_flag", ""), "standing_rule": triage.get("Standing_rule", ""),
                "misanchor_flag": triage.get("Misanchor_Flag", ""), "rggmci_support": rgg_support,
                "rggmci_support_count": len([x for x in re.split(r"[;,]", rgg_support) if x.strip()]),
                "active_site_rows": (sum(1 for row in active_sites if (row.get("bgc_id") or "").strip() == bgc_id) or active_site_by_bgc.get(bgc_id, 0)),
                "active_site_state": (
                    "POPULATED" if any((row.get("bgc_id") or "").strip() == bgc_id for row in active_sites)
                    else "POPULATED" if active_site_by_bgc.get(bgc_id, 0)
                    else "MISSING" if selected["deep_data.json"] is None and selected["_3_antismash_modules.csv"] is None
                    else "STRUCTURALLY_UNAVAILABLE"),
                "active_site_source": (
                    "deep_data" if any((row.get("bgc_id") or "").strip() == bgc_id for row in active_sites)
                    else "antismash_modules:ACTIVE_SITE_PAIRING" if active_site_by_bgc.get(bgc_id, 0) else ""),
                "triage_source_state": "POPULATED" if bgc_id in triage_map else "MISSING",
                "deep_profile_state": "POPULATED" if bgc_id in profile_map else "MISSING",
                "domain_source_state": "POPULATED" if selected["_domains.csv"] is not None else "MISSING",
                "rggmci_source_state": "POPULATED" if selected["_4A_RGGMCI_evidence.csv"] is not None else "MISSING",
            })

        gene_acc: dict[tuple[str, str], dict[str, Any]] = {}
        bgc_acc: dict[str, dict[str, Any]] = {}
        for row in selected["_3_mibig_per_gene.csv"] or []:
            bgc_id = (row.get("bgc_id") or "").strip()
            query_gene = (row.get("query_gene") or "").strip()
            if not bgc_id or not query_gene:
                continue
            accession = (row.get("mibig_accession") or row.get("reference") or "").strip()
            compound = (row.get("mibig_compound") or "").strip()
            identity = _float(row.get("pct_identity"))
            coverage = _float(row.get("pct_coverage_interpretation") or row.get("pct_coverage"))
            score = _float(row.get("blast_score"))
            rank = _float(row.get("reference_rank"))
            for key, accumulator in (
                ((bgc_id, query_gene), gene_acc.setdefault((bgc_id, query_gene), {
                    "accessions": set(), "compounds": set(), "identities": [], "coverages": [],
                    "scores": [], "ranks": [], "hits": 0, "best_reference": "",
                })),
                ((bgc_id,), bgc_acc.setdefault(bgc_id, {
                    "genes": set(), "accessions": set(), "compounds": set(), "identities": [],
                    "coverages": [], "scores": [], "ranks": [], "hits": 0,
                })),
            ):
                del key
                accumulator["hits"] += 1
                if query_gene and "genes" in accumulator: accumulator["genes"].add(query_gene)
                if accession: accumulator["accessions"].add(accession)
                if compound: accumulator["compounds"].add(compound)
                if identity is not None: accumulator["identities"].append(identity)
                if coverage is not None: accumulator["coverages"].append(coverage)
                if score is not None: accumulator["scores"].append(score)
                if rank is not None: accumulator["ranks"].append(rank)
            current = gene_acc[(bgc_id, query_gene)]
            if score is not None and (not current["scores"] or score >= max(current["scores"])):
                current["best_reference"] = accession
        for (bgc_id, query_gene), acc in sorted(gene_acc.items()):
            mibig_gene_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "bgc_id": bgc_id, "boundary": bgc_context.get(bgc_id, {}).get("boundary", "MISSING"),
                "query_gene": query_gene, "hit_rows": acc["hits"],
                "distinct_mibig_accessions": len(acc["accessions"]),
                "distinct_compound_labels": len(acc["compounds"]),
                "max_pct_identity": max(acc["identities"], default=""),
                "median_pct_identity": _median(acc["identities"]) or "",
                "median_pct_coverage": _median(acc["coverages"]) or "",
                "max_blast_score": max(acc["scores"], default=""),
                "best_reference": acc["best_reference"],
                "minimum_reference_rank": min(acc["ranks"], default=""),
            })
        for bgc_id, acc in sorted(bgc_acc.items(), key=lambda item: _natural_bgc(item[0])):
            mibig_bgc_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "bgc_id": bgc_id, "boundary": bgc_context.get(bgc_id, {}).get("boundary", "MISSING"),
                "query_genes_with_hits": len(acc["genes"]), "hit_rows": acc["hits"],
                "distinct_mibig_accessions": len(acc["accessions"]),
                "distinct_compound_labels": len(acc["compounds"]),
                "median_pct_identity": _median(acc["identities"]) or "",
                "median_pct_coverage": _median(acc["coverages"]) or "",
                "max_blast_score": max(acc["scores"], default=""),
                "minimum_reference_rank": min(acc["ranks"], default=""),
            })

        module_acc: dict[str, dict[str, Any]] = {}
        module_pseudo_id_rows = 0
        for row in selected["_3_antismash_modules.csv"] or []:
            bgc_id = (row.get("bgc_id") or "").strip()
            if not bgc_id:
                continue
            if bgc_id.upper() == "UNMAPPED":
                module_pseudo_id_rows += 1   # a state, not a locus: never a 97th BGC
                continue
            acc = module_acc.setdefault(bgc_id, {"rows": 0, "domains": Counter(), "substrates": Counter(), "mapped": 0, "unmapped": 0, "feature_types": Counter()})
            acc["rows"] += 1
            if (row.get("mapping_status") or "").upper() == "MAPPED": acc["mapped"] += 1
            else: acc["unmapped"] += 1
            feature_type = (row.get("feature_type") or "aSDomain").strip()
            acc["feature_types"][feature_type] += 1
            domain = (row.get("domain") or "").strip()
            substrate = (row.get("substrate_consensus") or "").strip()
            if domain and feature_type == "aSDomain": acc["domains"][domain] += 1
            if substrate: acc["substrates"][substrate] += 1
        for bgc_id, acc in sorted(module_acc.items(), key=lambda item: _natural_bgc(item[0])):
            module_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "bgc_id": bgc_id, "boundary": bgc_context.get(bgc_id, {}).get("boundary", "MISSING"),
                "module_rows": acc["rows"], "mapped_rows": acc["mapped"], "unmapped_rows": acc["unmapped"],
                "asdomain_rows": acc["feature_types"].get("aSDomain", 0), "asmodule_rows": acc["feature_types"].get("aSModule", 0),
                "active_site_pairing_rows": acc["feature_types"].get("ACTIVE_SITE_PAIRING", 0),
                "consensus_rows": acc["feature_types"].get("NRPS_PKS_CONSENSUS", 0),
                "other_feature_rows": sum(v for k, v in acc["feature_types"].items() if k not in {"aSDomain", "aSModule", "ACTIVE_SITE_PAIRING", "NRPS_PKS_CONSENSUS"}),
                "distinct_domains": len(acc["domains"]), "distinct_substrate_calls": len(acc["substrates"]),
                "substrate_calls": "; ".join(sorted(acc["substrates"])),
            })
            for domain, count in sorted(acc["domains"].items()):
                module_domain_rows.append({
                    "strain": strain, "governance": governance, "host_group": host,
                    "bgc_id": bgc_id, "boundary": bgc_context.get(bgc_id, {}).get("boundary", "MISSING"),
                    "domain": domain, "call_rows": count,
                })
            for substrate, count in sorted(acc["substrates"].items()):
                module_substrate_rows.append({
                    "strain": strain, "governance": governance, "host_group": host,
                    "bgc_id": bgc_id, "boundary": bgc_context.get(bgc_id, {}).get("boundary", "MISSING"),
                    "substrate": substrate, "call_rows": count,
                })

        # Domain rows are aggregated only after a deterministic physical-domain
        # projection. The domain name is retained as source text; no synonym or
        # biochemical-function adjudication is introduced here.
        domain_seen: set[tuple[str, str, str, str, str, str]] = set()
        domain_counts: Counter[tuple[str, str, str]] = Counter()
        for row in selected["_domains.csv"] or []:
            bgc_id = (row.get("bgc_id") or "").strip()
            domain = (row.get("domain") or "").strip()
            if not bgc_id or not domain:
                continue
            key = (
                bgc_id, (row.get("locus_tag") or "").strip(),
                (row.get("feature_type") or "").strip(), domain,
                (row.get("start") or "").strip(), (row.get("end") or "").strip(),
            )
            if key in domain_seen:
                continue
            domain_seen.add(key)
            domain_counts[(bgc_id, domain, key[2] or "UNSPECIFIED")] += 1
        for (bgc_id, domain, feature_type), count in sorted(domain_counts.items()):
            context = bgc_context.get(bgc_id, {"boundary": "MISSING", "products": []})
            domain_family_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "bgc_id": bgc_id, "boundary": context["boundary"],
                "products": "; ".join(context["products"]), "domain": domain,
                "feature_type": feature_type, "physical_domain_rows": count,
                "evidence_basis": "deduplicated sealed *_domains.csv row",
            })

        pair_acc: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in selected["_4A_RGGMCI_evidence.csv"] or []:
            bgc_a = (row.get("bgc_a") or "").strip()
            bgc_b = (row.get("bgc_b") or "").strip()
            pair = (row.get("pair") or "+".join(sorted((bgc_a, bgc_b), key=_natural_bgc))).strip()
            if not pair or not bgc_a or not bgc_b:
                continue
            key = (pair, bgc_a, bgc_b)
            acc = pair_acc.setdefault(key, {
                "rows": 0, "references": set(), "adjacency": Counter(), "tiling": Counter(),
                "identity": [], "shared_subjects": 0, "a_only": 0, "b_only": 0,
            })
            acc["rows"] += 1
            if (row.get("ref") or "").strip(): acc["references"].add((row.get("ref") or "").strip())
            acc["adjacency"][(row.get("adjacency_class") or "UNSPECIFIED").strip()] += 1
            acc["tiling"][(row.get("subject_tiling_class") or "UNSPECIFIED").strip()] += 1
            value = _float(row.get("avg_min_identity"))
            if value is not None: acc["identity"].append(value)
            acc["shared_subjects"] += int(_float(row.get("n_shared_subjects")) or 0)
            acc["a_only"] += int(_float(row.get("n_a_only_subjects")) or 0)
            acc["b_only"] += int(_float(row.get("n_b_only_subjects")) or 0)
        bgc_rgg: dict[str, dict[str, Any]] = defaultdict(lambda: {"pairs": set(), "rows": 0, "references": set(), "max_identity": []})
        for (pair, bgc_a, bgc_b), acc in sorted(pair_acc.items()):
            top_adjacency = sorted(acc["adjacency"].items(), key=lambda item: (-item[1], item[0]))[0][0]
            top_tiling = sorted(acc["tiling"].items(), key=lambda item: (-item[1], item[0]))[0][0]
            rgg_pair_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "pair": pair, "bgc_a": bgc_a, "bgc_b": bgc_b,
                "evidence_rows": acc["rows"], "distinct_references": len(acc["references"]),
                "max_avg_min_identity": max(acc["identity"], default=""),
                "dominant_adjacency_class": top_adjacency, "dominant_tiling_class": top_tiling,
                "shared_subjects_total": acc["shared_subjects"],
                "a_only_subjects_total": acc["a_only"], "b_only_subjects_total": acc["b_only"],
                "claim_ceiling": "cross-contig linkage candidate only; not a physically validated pathway",
            })
            for bgc_id in (bgc_a, bgc_b):
                bgc_rgg[bgc_id]["pairs"].add(pair)
                bgc_rgg[bgc_id]["rows"] += acc["rows"]
                bgc_rgg[bgc_id]["references"].update(acc["references"])
                if acc["identity"]: bgc_rgg[bgc_id]["max_identity"].append(max(acc["identity"]))
        for bgc_id, acc in sorted(bgc_rgg.items(), key=lambda item: _natural_bgc(item[0])):
            context = bgc_context.get(bgc_id, {"boundary": "MISSING", "products": []})
            rgg_bgc_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "bgc_id": bgc_id, "boundary": context["boundary"],
                "products": "; ".join(context["products"]),
                "candidate_pairs": len(acc["pairs"]), "evidence_rows": acc["rows"],
                "distinct_references": len(acc["references"]),
                "max_avg_min_identity": max(acc["max_identity"], default=""),
            })

        scan_payload = selected["_3_scan_states.json"] or {}
        if selected["_3_scan_states.json"] is None:
            evidence_channel_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "channel_group": "SOURCE_MEMBER", "channel": "scan_states_member",
                "state": "MISSING", "detail": "Optional extended source member not present",
                "source_member": "*_3_scan_states.json",
            })
        for scan in scan_payload.get("scans") or []:
            if not isinstance(scan, list) or len(scan) < 2:
                continue
            evidence_channel_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "channel_group": "SOURCE_SCAN", "channel": scan[0], "state": scan[1],
                "detail": scan[2] if len(scan) > 2 else "", "source_member": "*_3_scan_states.json",
            })
        for channel, state in (scan_payload.get("evidence_channels") or {}).items():
            evidence_channel_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "channel_group": "EVIDENCE_CHANNEL", "channel": channel,
                "state": (state or {}).get("status") or "MISSING",
                "detail": (state or {}).get("reason") or "", "source_member": "*_3_scan_states.json",
            })
        validation = selected["gate_validation.json"] or {}
        for gate in ("file_presence", "manifest_parse", "reporting_v2_gate", "rggmci_gate", "citation_compact_gate", "gold_completeness", "checksum_integrity", "package_status"):
            evidence_channel_rows.append({
                "strain": strain, "governance": governance, "host_group": host,
                "channel_group": "PACKAGE_GATE", "channel": gate,
                "state": validation.get(gate) or "MISSING", "detail": "",
                "source_member": "gate_validation.json",
            })

    observed_role_counts: dict[tuple[str, str], int] = defaultdict(int)
    for row in gene_assignments:
        if row["length_state"] == "POPULATED":
            observed_role_counts[(row["strain"], row["role"])] += 1
    machinery_reconciliation: list[dict[str, Any]] = []
    for strain, record in strains.items():
        expected_roles = {role: len(values) for role, values in (record.get("machinery") or {}).items()}
        roles = sorted(set(expected_roles) | {role for sid, role in observed_role_counts if sid == strain})
        for role in roles:
            expected = expected_roles.get(role, 0)
            observed = observed_role_counts.get((strain, role), 0)
            if observed != expected:
                machinery_reconciliation.append({
                    "strain": strain, "governance": record.get("governance") or "UNRESOLVED",
                    "role": role, "widget_count": expected, "sealed_member_count": observed,
                    "delta_sealed_minus_widget": observed - expected,
                    "state": "SOURCE_SNAPSHOT_DIFFERENCE",
                })
    outputs = {
        "BGC_RECORDS.csv": bgc_records,
        "BGC_CLASS_MEMBERSHIPS.csv": class_memberships,
        "BGC_CLASS_PAIRS.csv": class_pairs,
        "BGC_MACHINERY_ASSIGNMENTS.csv": gene_assignments,
        "MIBIG_GENE_CONVERGENCE.csv": mibig_gene_rows,
        "MIBIG_BGC_CONVERGENCE.csv": mibig_bgc_rows,
        "MODULE_SUBSTRATE_BGC_SUMMARY.csv": module_rows,
        "MODULE_DOMAIN_CALLS.csv": module_domain_rows,
        "MODULE_SUBSTRATE_CALLS.csv": module_substrate_rows,
        "BGC_GENE_FEATURE_TOKENS.csv": gene_feature_rows,
        "BGC_CDS_SUMMARY.csv": cds_summary_rows,
        "BGC_EXTENDED_EVIDENCE.csv": extended_bgc_rows,
        "DOMAIN_FAMILY_CALLS.csv": domain_family_rows,
        "RGGMCI_PAIR_SUMMARY.csv": rgg_pair_rows,
        "RGGMCI_BGC_SUMMARY.csv": rgg_bgc_rows,
        "EVIDENCE_CHANNEL_STATES.csv": evidence_channel_rows,
        "STRAIN_CONTEXT.csv": strain_context_rows,
        "DOMAIN_CATEGORY_COUNTS.csv": domain_category_rows,
        "CASSETTE_FAMILY_COUNTS.csv": cassette_family_rows,
        "RESISTANCE_FAMILY_COUNTS.csv": resistance_family_rows,
        "MANIFEST_SOURCE_SCAN_COUNTS.csv": manifest_scan_rows,
        "SOURCE_MEMBER_LEDGER.csv": member_ledger,
        "PACKAGE_STATES.csv": package_states,
        "WIDGET_MACHINERY_RECONCILIATION_ISSUES.csv": machinery_reconciliation,
    }
    output_receipts = []
    for name, rows in outputs.items():
        path = destination / name
        _write_csv(path, rows)
        output_receipts.append({"path": name, "rows": len(rows), "sha256": _sha256_path(path)})
    missing_packages = [row["strain"] for row in package_states if row["state"] != "PRESENT"]
    missing_members = [row for row in member_ledger if row["state"] != "PRESENT"]
    missing_required_members = [row for row in missing_members if row["member_suffix"] in REQUIRED_SUFFIXES]
    missing_snapshots = [row["strain"] for row in strain_context_rows if row["snapshot_state"] != "PRESENT"]
    expected_bgc_rows = sum(int(record.get("bgcRows") or 0) for record in strains.values())
    expected_memberships = sum(
        int(values.get("total") or 0)
        for record in strains.values()
        for values in (record.get("classes") or {}).values()
    )
    expected_machinery_with_lengths = sum(int(record.get("machineryGenes") or 0) for record in strains.values())
    observed_machinery_with_lengths = sum(row["length_state"] == "POPULATED" for row in gene_assignments)
    checks = [
        {"check_id": "PACKAGE_RESOLUTION", "status": "PASS" if not missing_packages else "FAIL",
         "detail": f"present={len(strains)-len(missing_packages)} expected={len(strains)}"},
        {"check_id": "REQUIRED_MEMBER_RESOLUTION", "status": "PASS" if not missing_required_members else "ISSUE",
         "detail": f"present={len(strains)*len(REQUIRED_SUFFIXES)-len(missing_required_members)} expected={len(strains)*len(REQUIRED_SUFFIXES)}; optional extended members are ledgered without converting absence to a biological negative"},
        {"check_id": "BGC_ROW_RECONCILIATION", "status": "PASS" if len(bgc_records) == expected_bgc_rows else "FAIL",
         "detail": f"observed={len(bgc_records)} expected={expected_bgc_rows}"},
        {"check_id": "CLASS_MEMBERSHIP_RECONCILIATION", "status": "PASS" if len(class_memberships) == expected_memberships else "FAIL",
         "detail": f"observed={len(class_memberships)} expected={expected_memberships}"},
        {"check_id": "MACHINERY_LENGTH_RECONCILIATION", "status": "PASS" if observed_machinery_with_lengths == expected_machinery_with_lengths else "ISSUE",
         "detail": f"sealed_member_assignments={observed_machinery_with_lengths} widget_snapshot={expected_machinery_with_lengths}; differences={len(machinery_reconciliation)} role cells; direct sealed-member values retained with issue ledger"},
        {"check_id": "PROJECT_MEMORY_SNAPSHOT_AVAILABILITY", "status": "PASS",
         "detail": f"present={len(strains)-len(missing_snapshots)} expected={len(strains)}; this member is optional for the base source bundle, and missing snapshots remain typed missingness rather than zero evidence"},
    ]
    hard_failure = any(check["status"] == "FAIL" for check in checks)
    soft_issue = any(check["status"] == "ISSUE" for check in checks)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL" if hard_failure else ("PASS_WITH_ISSUES" if soft_issue else "PASS"),
        "profile": PROFILE,
        "source": {"widget_data": str(widget_path), "widget_sha256": _sha256_path(widget_path), "package_dir": str(package_root)},
        "strain_count": len(strains), "present_package_count": len(strains) - len(missing_packages),
        "missing_packages": missing_packages, "missing_member_count": len(missing_members),
        "missing_required_member_count": len(missing_required_members),
        "missing_members": [{"strain": row["strain"], "member_suffix": row["member_suffix"]} for row in missing_members],
        "outputs": output_receipts, "machine_checks": checks, "claim_ceiling": GLOBAL_CLAIM_CEILING,
        "deduplication": "Physical CDS are projected by first-row retention on strain+contig+locus_tag+start+end before role precedence, matching the widget-data contract; retained BGC assignment remains explicit.",
    }
    receipt_path = destination / "SOURCE_BUNDLE_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--widget-data", required=True)
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args(argv)
    result = build_source_bundle(args.widget_data, args.package_dir, args.outdir)
    emit(json.dumps(result, indent=2))
    return 0 if result["status"] in {"PASS", "PASS_WITH_ISSUES"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

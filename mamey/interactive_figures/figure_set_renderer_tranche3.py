#!/usr/bin/env python3
"""Render 28 sealed-evidence Codex Figure Factory sets (tranche 3)."""

from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from ..console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from mamey.console import emit

import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from .figure_set_registry import GLOBAL_CLAIM_CEILING, PROFILE, build_registry
from .figure_set_renderer import (
    Chart, HOST_ORDER, _host, _load, _median, _pct, _quantile, _sha256,
    _validate_outputs, _write_rows, render_svg,
)


SCHEMA_VERSION = "sapote-mamey.codex-figure-set-render.tranche3.v1"
IMPLEMENTED_IDS_3 = (
    "FS097", "FS098", "FS099", "FS100", "FS101", "FS102", "FS103",
    "FS105", "FS106", "FS107", "FS108", "FS109", "FS110", "FS111",
    "FS113", "FS114", "FS115", "FS116", "FS117", "FS118", "FS119",
    "FS121", "FS122", "FS123", "FS124", "FS125", "FS126", "FS127",
)
CONVERGENCE_BINS = ("1", "2–4", "5–9", "10–24", "25+")


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _n(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _top(counter: Counter[str], n: int) -> list[str]:
    return [key for key, _value in sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))[:n]]


def _conv_bin(value: Any) -> str:
    number = int(_n(value))
    if number <= 1: return "1"
    if number <= 4: return "2–4"
    if number <= 9: return "5–9"
    if number <= 24: return "10–24"
    return "25+"


def _class_map(memberships: Sequence[dict[str, str]]) -> dict[tuple[str, str], set[str]]:
    result: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in memberships:
        result[(row["strain"], row["bgc_id"])].add(row["product_class"])
    return result


def _state(value: bool, source_present: bool = True) -> tuple[str, int]:
    if not source_present: return "MISSING", -1
    return ("POPULATED", 1) if value else ("OBSERVED_ZERO", 0)


def build_charts_3(payload: dict[str, Any], all_ids: Sequence[str], governed: Sequence[str], bundle: Path) -> list[Chart]:
    strains = payload["strains"]
    governed_set, all_set = set(governed), set(all_ids)
    bgcs = _read(bundle / "BGC_RECORDS.csv")
    memberships = _read(bundle / "BGC_CLASS_MEMBERSHIPS.csv")
    mibig_genes = _read(bundle / "MIBIG_GENE_CONVERGENCE.csv")
    modules = _read(bundle / "MODULE_SUBSTRATE_BGC_SUMMARY.csv")
    domains = _read(bundle / "MODULE_DOMAIN_CALLS.csv")
    substrates = _read(bundle / "MODULE_SUBSTRATE_CALLS.csv")
    ledger = _read(bundle / "SOURCE_MEMBER_LEDGER.csv")
    classes = _class_map(memberships)
    g_bgcs = [row for row in bgcs if row["strain"] in governed_set]
    g_memberships = [row for row in memberships if row["strain"] in governed_set]
    g_mibig = [row for row in mibig_genes if row["strain"] in governed_set]
    g_modules = [row for row in modules if row["strain"] in governed_set]
    g_domains = [row for row in domains if row["strain"] in governed_set]
    g_substrates = [row for row in substrates if row["strain"] in governed_set]
    top_classes = _top(Counter(row["product_class"] for row in g_memberships), 15)
    member_present = {(row["strain"], row["member_suffix"]): row["state"] == "PRESENT" for row in ledger}
    charts: list[Chart] = []

    # Per-gene MIBiG convergence. The source-bundle ingress fulfills the
    # registry gate; the figures remain similarity-only.
    conv_counts = Counter(_conv_bin(row["distinct_mibig_accessions"]) for row in g_mibig)
    charts.append(Chart("FS097", "bar", "Per-gene MIBiG convergence — governed cohort overview",
                        "Genes are binned by distinct MIBiG accessions among source-reported per-gene hits; this is similarity, not identity", [{"reference_bin": key, "query_genes": conv_counts[key]} for key in CONVERGENCE_BINS],
                        {"category": "reference_bin", "value": "query_genes", "x_label": "Query genes with source-reported MIBiG hits"}))

    strain_mibig = []
    for sid in governed:
        rows = [row for row in g_mibig if row["strain"] == sid]
        strain_mibig.append({"strain": sid, "genes_with_hits": len(rows), "median_distinct_accessions": _median(_n(row["distinct_mibig_accessions"]) for row in rows), "host": _host(strains[sid])})
    charts.append(Chart("FS098", "scatter", "Per-gene MIBiG convergence — every governed strain",
                        "Every governed strain is labelled; strains with no reported per-gene hits remain at observed zero", strain_mibig,
                        {"x": "genes_with_hits", "y": "median_distinct_accessions", "label": "strain", "x_label": "Query genes with MIBiG hits", "y_label": "Median distinct MIBiG accessions per hit gene", "x_min": 0, "y_min": 0}))

    class_conv_counts: Counter[tuple[str, str]] = Counter()
    class_gene_counts: Counter[str] = Counter()
    for row in g_mibig:
        for cls in classes.get((row["strain"], row["bgc_id"]), set()):
            class_conv_counts[(cls, _conv_bin(row["distinct_mibig_accessions"]))] += 1
            class_gene_counts[cls] += 1
    class_conv = [{"class": cls, "reference_bin": bin_name, "gene_pct": _pct(class_conv_counts[(cls, bin_name)], class_gene_counts[cls]), "query_genes": class_conv_counts[(cls, bin_name)]} for cls in top_classes for bin_name in CONVERGENCE_BINS]
    charts.append(Chart("FS099", "heatmap", "Per-gene MIBiG convergence by BGC class",
                        "Hit-bearing genes are projected through nonexclusive physical-BGC class memberships", class_conv,
                        {"row": "class", "column": "reference_bin", "value": "gene_pct", "legend": "Within-class hit genes (%)"}))

    boundary_conv = []
    for boundary in ("Edge", "Full-contig", "Interior", "MISSING"):
        rows = [row for row in g_mibig if row["boundary"] == boundary]
        counts = Counter(_conv_bin(row["distinct_mibig_accessions"]) for row in rows)
        if rows:
            for bin_name in CONVERGENCE_BINS:
                boundary_conv.append({"boundary": boundary, "reference_bin": bin_name, "gene_pct": _pct(counts[bin_name], len(rows)), "query_genes": counts[bin_name]})
    charts.append(Chart("FS100", "heatmap", "Per-gene MIBiG convergence by boundary context",
                        "Hit-bearing genes are stratified by their retained physical-BGC boundary assignment", boundary_conv,
                        {"row": "boundary", "column": "reference_bin", "value": "gene_pct", "legend": "Within-boundary hit genes (%)"}))

    host_conv = []
    for group in HOST_ORDER:
        rows = [row for row in g_mibig if row["host_group"] == group]
        counts = Counter(_conv_bin(row["distinct_mibig_accessions"]) for row in rows)
        for bin_name in CONVERGENCE_BINS:
            host_conv.append({"host": group, "reference_bin": bin_name, "gene_pct": _pct(counts[bin_name], len(rows)), "query_genes": counts[bin_name]})
    charts.append(Chart("FS101", "heatmap", "Per-gene MIBiG convergence by host cohort",
                        "Similarity profiles are normalized within explicit host groups; no host causality is inferred", host_conv,
                        {"row": "host", "column": "reference_bin", "value": "gene_pct", "legend": "Within-host-group hit genes (%)"}))

    mpg_availability = []
    for sid in governed:
        rows = [row for row in g_mibig if row["strain"] == sid]
        member = member_present.get((sid, "_3_mibig_per_gene.csv"), False)
        fields = {
            "Per-gene member": member,
            "Genes with hits": bool(rows),
            "Identity populated": any(str(row["median_pct_identity"]).strip() for row in rows),
            "Coverage populated": any(str(row["median_pct_coverage"]).strip() for row in rows),
            "Reference populated": any(str(row["best_reference"]).strip() for row in rows),
        }
        for field, populated in fields.items():
            state, value = _state(populated, member if field != "Per-gene member" else True)
            mpg_availability.append({"strain": sid, "field": field, "state": state, "value": value})
    charts.append(Chart("FS102", "state_heatmap", "Per-gene MIBiG evidence availability",
                        "Source-member availability, observed-zero hit sets, and populated identity/coverage/reference fields remain distinct", mpg_availability,
                        {"row": "strain", "column": "field", "value": "value", "state": "state"}))

    all_conv = Counter(_conv_bin(row["distinct_mibig_accessions"]) for row in mibig_genes if row["strain"] in all_set)
    charts.append(Chart("FS103", "paired_dot", "Per-gene MIBiG convergence — governance sensitivity",
                        "Governed hit-gene counts are paired with all packaged counts by convergence bin", [{"reference_bin": key, "governed": conv_counts[key], "all_packaged": all_conv[key]} for key in CONVERGENCE_BINS],
                        {"category": "reference_bin", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": "Query genes with source-reported hits"}))

    # KnownClusterBlast anchors from inventory. Names remain source labels only.
    anchored = [row for row in g_bgcs if row["kcb_state"] == "POPULATED"]
    state_counts = Counter(row["kcb_state"] for row in g_bgcs)
    charts.append(Chart("FS105", "bar", "KnownClusterBlast anchor availability — governed overview",
                        "Physical BGC rows are separated into source-populated and observed-zero KCB states; anchor names are not product identities", [{"kcb_state": state, "physical_bgcs": state_counts[state]} for state in ("POPULATED", "OBSERVED_ZERO")],
                        {"category": "kcb_state", "value": "physical_bgcs", "x_label": "Physical BGC rows"}))

    strain_kcb = []
    for sid in governed:
        rows = [row for row in g_bgcs if row["strain"] == sid and row["kcb_state"] == "POPULATED"]
        scores = [_n(row["kcb_score"]) for row in rows if str(row["kcb_score"]).strip()]
        strain_kcb.append({"strain": sid, "anchored_bgcs": len(rows), "median_kcb_score": _median(scores), "host": _host(strains[sid])})
    charts.append(Chart("FS106", "scatter", "KnownClusterBlast anchors — every governed strain",
                        "Every governed strain is labelled; KCB score is a source-derived similarity measure, not product identity", strain_kcb,
                        {"x": "anchored_bgcs", "y": "median_kcb_score", "label": "strain", "x_label": "BGC rows with KCB anchor", "y_label": "Median source KCB score", "x_min": 0, "y_min": 0}))

    class_kcb = []
    membership_by_bgc = defaultdict(list)
    for row in g_memberships: membership_by_bgc[(row["strain"], row["bgc_id"])].append(row)
    for cls in top_classes:
        rows = [row for row in g_memberships if row["product_class"] == cls]
        anchor_keys = {(row["strain"], row["bgc_id"]) for row in anchored}
        class_kcb.append({"class": cls, "anchored_pct": _pct(sum((row["strain"], row["bgc_id"]) in anchor_keys for row in rows), len(rows)), "memberships": len(rows)})
    charts.append(Chart("FS107", "bar", "KnownClusterBlast anchor availability by BGC class",
                        "Percent of nonexclusive BGC-class memberships with a source-populated KCB anchor", class_kcb,
                        {"category": "class", "value": "anchored_pct", "x_label": "Class memberships with KCB anchor (%)", "max": 100}))

    kcb_boundary = []
    for boundary in ("Edge", "Full-contig", "Interior", "MISSING"):
        rows = [row for row in g_bgcs if row["boundary"] == boundary]
        if rows: kcb_boundary.append({"boundary": boundary, "anchored_pct": _pct(sum(row["kcb_state"] == "POPULATED" for row in rows), len(rows)), "bgcs": len(rows)})
    charts.append(Chart("FS108", "bar", "KnownClusterBlast anchors by boundary context",
                        "Anchor availability is stratified without collapsing BGC boundary states", kcb_boundary,
                        {"category": "boundary", "value": "anchored_pct", "x_label": "Physical BGC rows with KCB anchor (%)", "max": 100}))

    host_kcb = []
    for group in HOST_ORDER:
        rows = [row for row in g_bgcs if row["host_group"] == group]
        host_kcb.append({"host": group, "anchored_pct": _pct(sum(row["kcb_state"] == "POPULATED" for row in rows), len(rows)), "bgcs": len(rows)})
    charts.append(Chart("FS109", "bar", "KnownClusterBlast anchors by host cohort",
                        "Anchor availability is normalized within explicit host groups; no host causality is inferred", host_kcb,
                        {"category": "host", "value": "anchored_pct", "x_label": "Physical BGC rows with KCB anchor (%)", "max": 100}))

    kcb_availability = []
    for sid in governed:
        rows = [row for row in g_bgcs if row["strain"] == sid]
        member = member_present.get((sid, "_2_inventory.csv"), False)
        fields = {
            "Inventory member": member,
            "KCB anchor populated": any(row["kcb_state"] == "POPULATED" for row in rows),
            "KCB score populated": any(str(row["kcb_score"]).strip() for row in rows),
        }
        for field, populated in fields.items():
            state, value = _state(populated, member if field != "Inventory member" else True)
            kcb_availability.append({"strain": sid, "field": field, "state": state, "value": value})
    charts.append(Chart("FS110", "state_heatmap", "KnownClusterBlast evidence availability",
                        "Present inventory members distinguish observed-zero KCB fields from missing source evidence", kcb_availability,
                        {"row": "strain", "column": "field", "value": "value", "state": "state"}))

    all_state = Counter(row["kcb_state"] for row in bgcs if row["strain"] in all_set)
    charts.append(Chart("FS111", "paired_dot", "KnownClusterBlast anchors — governance sensitivity",
                        "Governed and all-packaged physical-BGC counts are paired for populated and observed-zero KCB states", [{"kcb_state": state, "governed": state_counts[state], "all_packaged": all_state[state]} for state in ("POPULATED", "OBSERVED_ZERO")],
                        {"category": "kcb_state", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": "Physical BGC rows"}))

    # Module architecture.
    domain_counts = Counter()
    for row in g_domains: domain_counts[row["domain"]] += int(_n(row["call_rows"]))
    top_domains = _top(domain_counts, 15)
    charts.append(Chart("FS113", "bar", "NRPS/PKS module architecture — governed overview",
                        "Top antiSMASH domain call rows; annotations describe genomic capacity, not product structure", [{"domain": domain, "call_rows": domain_counts[domain]} for domain in top_domains],
                        {"category": "domain", "value": "call_rows", "x_label": "Source-reported domain call rows"}))

    strain_modules = []
    for sid in governed:
        rows = [row for row in g_modules if row["strain"] == sid and _n(row["module_rows"]) > 0]
        strain_modules.append({"strain": sid, "bgcs_with_module_evidence": len(rows), "median_distinct_domains": _median(_n(row["distinct_domains"]) for row in rows), "host": _host(strains[sid])})
    charts.append(Chart("FS114", "scatter", "NRPS/PKS module architecture — every governed strain",
                        "Every governed strain is labelled; module evidence is annotation-derived capacity only", strain_modules,
                        {"x": "bgcs_with_module_evidence", "y": "median_distinct_domains", "label": "strain", "x_label": "BGCs with module evidence", "y_label": "Median distinct domains per evidenced BGC", "x_min": 0, "y_min": 0}))

    class_domain_counts: Counter[tuple[str, str]] = Counter()
    class_bgc_counts = Counter(row["product_class"] for row in g_memberships)
    for row in g_domains:
        for cls in classes.get((row["strain"], row["bgc_id"]), set()):
            class_domain_counts[(cls, row["domain"])] += int(_n(row["call_rows"]))
    class_domains = [{"class": cls, "domain": domain, "calls_per_100_memberships": 100 * class_domain_counts[(cls, domain)] / class_bgc_counts[cls] if class_bgc_counts[cls] else 0} for cls in top_classes for domain in top_domains[:10]]
    charts.append(Chart("FS115", "heatmap", "NRPS/PKS module domains by BGC class",
                        "Domain calls are normalized per 100 nonexclusive BGC-class memberships", class_domains,
                        {"row": "class", "column": "domain", "value": "calls_per_100_memberships", "legend": "Domain calls per 100 BGC-class memberships"}))

    module_boundary = []
    for boundary in ("Edge", "Full-contig", "Interior", "MISSING"):
        values = [_n(row["distinct_domains"]) for row in g_modules if row["boundary"] == boundary]
        if values: module_boundary.append({"boundary": boundary, "q1": _quantile(values, .25), "median": _median(values), "q3": _quantile(values, .75), "bgcs": len(values)})
    charts.append(Chart("FS116", "dot_range", "NRPS/PKS module complexity by boundary context",
                        "Median and interquartile range of distinct source-reported domains per evidenced BGC", module_boundary,
                        {"category": "boundary", "low": "q1", "mid": "median", "high": "q3", "x_label": "Distinct domains per evidenced BGC"}))

    module_host = []
    for group in HOST_ORDER:
        values = [_n(row["distinct_domains"]) for row in g_modules if row["host_group"] == group]
        module_host.append({"host": group, "q1": _quantile(values, .25), "median": _median(values), "q3": _quantile(values, .75), "bgcs": len(values)})
    charts.append(Chart("FS117", "dot_range", "NRPS/PKS module complexity by host cohort",
                        "Module-domain complexity is descriptive annotation context; no host causality is inferred", module_host,
                        {"category": "host", "low": "q1", "mid": "median", "high": "q3", "x_label": "Distinct domains per evidenced BGC"}))

    module_availability = []
    for sid in governed:
        rows = [row for row in g_modules if row["strain"] == sid]
        member = member_present.get((sid, "_3_antismash_modules.csv"), False)
        fields = {
            "Module member": member,
            "BGCs evidenced": bool(rows),
            "Mapped rows": any(_n(row["mapped_rows"]) > 0 for row in rows),
            "Domain calls": any(_n(row["distinct_domains"]) > 0 for row in rows),
        }
        for field, populated in fields.items():
            state, value = _state(populated, member if field != "Module member" else True)
            module_availability.append({"strain": sid, "field": field, "state": state, "value": value})
    charts.append(Chart("FS118", "state_heatmap", "NRPS/PKS module evidence availability",
                        "Source-member, BGC evidence, mapping, and domain-call states remain distinct", module_availability,
                        {"row": "strain", "column": "field", "value": "value", "state": "state"}))

    all_domain_counts = Counter()
    for row in domains:
        if row["strain"] in all_set: all_domain_counts[row["domain"]] += int(_n(row["call_rows"]))
    charts.append(Chart("FS119", "paired_dot", "NRPS/PKS module domains — governance sensitivity",
                        "Governed and all-packaged source domain-call rows are paired", [{"domain": domain, "governed": domain_counts[domain], "all_packaged": all_domain_counts[domain]} for domain in _top(all_domain_counts, 15)],
                        {"category": "domain", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": "Source-reported domain call rows"}))

    # Substrate-call evidence.
    substrate_counts = Counter()
    for row in g_substrates: substrate_counts[row["substrate"]] += int(_n(row["call_rows"]))
    top_substrates = _top(substrate_counts, 15)
    charts.append(Chart("FS121", "bar", "Module substrate calls — governed cohort overview",
                        "Top antiSMASH substrate-consensus tokens; X and other ambiguous tokens remain explicit and are not chemical identities", [{"substrate": substrate, "call_rows": substrate_counts[substrate]} for substrate in top_substrates],
                        {"category": "substrate", "value": "call_rows", "x_label": "Source-reported substrate call rows"}))

    strain_substrates = []
    for sid in governed:
        rows = [row for row in g_substrates if row["strain"] == sid]
        strain_substrates.append({"strain": sid, "bgcs_with_substrate_calls": len({row["bgc_id"] for row in rows}), "distinct_substrate_tokens": len({row["substrate"] for row in rows}), "host": _host(strains[sid])})
    charts.append(Chart("FS122", "scatter", "Module substrate calls — every governed strain",
                        "Every governed strain is labelled; substrate tokens are annotation-derived and not product identities", strain_substrates,
                        {"x": "bgcs_with_substrate_calls", "y": "distinct_substrate_tokens", "label": "strain", "x_label": "BGCs with substrate calls", "y_label": "Distinct substrate-consensus tokens", "x_min": 0, "y_min": 0}))

    class_sub_counts: Counter[tuple[str, str]] = Counter()
    for row in g_substrates:
        for cls in classes.get((row["strain"], row["bgc_id"]), set()):
            class_sub_counts[(cls, row["substrate"])] += int(_n(row["call_rows"]))
    class_subs = [{"class": cls, "substrate": substrate, "calls_per_100_memberships": 100 * class_sub_counts[(cls, substrate)] / class_bgc_counts[cls] if class_bgc_counts[cls] else 0} for cls in top_classes for substrate in top_substrates[:10]]
    charts.append(Chart("FS123", "heatmap", "Module substrate calls by BGC class",
                        "Substrate-consensus tokens are normalized per 100 nonexclusive BGC-class memberships", class_subs,
                        {"row": "class", "column": "substrate", "value": "calls_per_100_memberships", "legend": "Substrate call rows per 100 BGC-class memberships"}))

    boundary_sub_counts: Counter[tuple[str, str]] = Counter()
    boundary_bgcs = Counter(row["boundary"] for row in g_bgcs)
    for row in g_substrates: boundary_sub_counts[(row["boundary"], row["substrate"])] += int(_n(row["call_rows"]))
    boundary_subs = [{"boundary": boundary, "substrate": substrate, "calls_per_100_bgcs": 100 * boundary_sub_counts[(boundary, substrate)] / boundary_bgcs[boundary] if boundary_bgcs[boundary] else 0} for boundary in ("Edge", "Full-contig", "Interior") for substrate in top_substrates[:10]]
    charts.append(Chart("FS124", "heatmap", "Module substrate calls by boundary context",
                        "Substrate-consensus call rows are normalized per 100 physical BGC rows in each boundary state", boundary_subs,
                        {"row": "boundary", "column": "substrate", "value": "calls_per_100_bgcs", "legend": "Substrate call rows per 100 physical BGCs"}))

    host_sub_counts: Counter[tuple[str, str]] = Counter()
    host_strains = Counter(_host(strains[sid]) for sid in governed)
    for row in g_substrates: host_sub_counts[(row["host_group"], row["substrate"])] += int(_n(row["call_rows"]))
    host_subs = [{"host": group, "substrate": substrate, "calls_per_strain": host_sub_counts[(group, substrate)] / host_strains[group] if host_strains[group] else 0} for group in HOST_ORDER for substrate in top_substrates[:10]]
    charts.append(Chart("FS125", "heatmap", "Module substrate calls by host cohort",
                        "Substrate-consensus call rows are normalized per governed strain; no host causality is inferred", host_subs,
                        {"row": "host", "column": "substrate", "value": "calls_per_strain", "legend": "Substrate call rows per strain"}))

    substrate_availability = []
    for sid in governed:
        rows = [row for row in g_substrates if row["strain"] == sid]
        member = member_present.get((sid, "_3_antismash_modules.csv"), False)
        fields = {
            "Module member": member,
            "BGCs with calls": bool(rows),
            "Distinct tokens": bool({row["substrate"] for row in rows}),
            "Resolved tokens": any(row["substrate"].upper() not in {"X", "UNKNOWN", "UNRESOLVED"} for row in rows),
        }
        for field, populated in fields.items():
            state, value = _state(populated, member if field != "Module member" else True)
            substrate_availability.append({"strain": sid, "field": field, "state": state, "value": value})
    charts.append(Chart("FS126", "state_heatmap", "Module substrate-call evidence availability",
                        "Present module members distinguish observed-zero substrate calls from missing source evidence", substrate_availability,
                        {"row": "strain", "column": "field", "value": "value", "state": "state"}))

    all_substrate_counts = Counter()
    for row in substrates:
        if row["strain"] in all_set: all_substrate_counts[row["substrate"]] += int(_n(row["call_rows"]))
    charts.append(Chart("FS127", "paired_dot", "Module substrate calls — governance sensitivity",
                        "Governed and all-packaged source substrate-call rows are paired", [{"substrate": substrate, "governed": substrate_counts[substrate], "all_packaged": all_substrate_counts[substrate]} for substrate in _top(all_substrate_counts, 15)],
                        {"category": "substrate", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": "Source-reported substrate call rows"}))

    assert tuple(chart.figure_id for chart in charts) == IMPLEMENTED_IDS_3
    return charts


def render_tranche_3(widget_data: str | Path, source_bundle: str | Path, outdir: str | Path) -> dict[str, Any]:
    widget_path, payload, all_ids, governed = _load(widget_data)
    bundle = Path(source_bundle).resolve()
    source_receipt = bundle / "SOURCE_BUNDLE_RECEIPT.json"
    if not source_receipt.is_file(): raise ValueError("source bundle has no SOURCE_BUNDLE_RECEIPT.json")
    destination = Path(outdir).resolve(); destination.mkdir(parents=True, exist_ok=True)
    figures_dir, data_dir, text_dir = destination / "figures", destination / "data", destination / "text"
    for directory in (figures_dir, data_dir, text_dir): directory.mkdir(parents=True, exist_ok=True)
    registry = {record["figure_set_id"]: record for record in build_registry()}
    charts = build_charts_3(payload, all_ids, governed, bundle)
    manifest = []
    for chart in charts:
        svg_path, csv_path, text_path = figures_dir / f"{chart.figure_id}.svg", data_dir / f"{chart.figure_id}_data.csv", text_dir / f"{chart.figure_id}_CAPTION_METHODS.md"
        svg_path.write_text(render_svg(chart), encoding="utf-8"); _write_rows(csv_path, chart.rows)
        spec = registry[chart.figure_id]
        ingress = "The sealed-package source bundle fulfills the curated-ingress gate for this render. " if chart.figure_id.startswith("FS09") or chart.figure_id in {"FS100", "FS101", "FS102", "FS103"} else ""
        text_path.write_text(
            f"# {chart.figure_id} — {chart.title}\n\n## Caption\n\n{spec['caption_template']}\n\n## Methods\n\n{spec['methods_template']}\n\n"
            f"## Render-specific note\n\n{ingress}{chart.subtitle}\n\n## Citation status\n\nCitations must be reviewed against the source release and upstream evidence channels at manuscript freeze.\n",
            encoding="utf-8")
        manifest.append({"figure_set_id": chart.figure_id, "title": chart.title, "kind": chart.kind, "rows": len(chart.rows), "svg": str(svg_path.relative_to(destination)), "data_csv": str(csv_path.relative_to(destination)), "caption_methods": str(text_path.relative_to(destination)), "svg_sha256": _sha256(svg_path), "data_sha256": _sha256(csv_path), "text_sha256": _sha256(text_path)})
    cards = "".join(f'<article><h2>{html.escape(item["figure_set_id"])} — {html.escape(item["title"])}</h2><img src="{html.escape(item["svg"])}" alt="{html.escape(item["title"])}"><p><a href="{html.escape(item["data_csv"])}">Plotted data</a> · <a href="{html.escape(item["caption_methods"])}">Caption and methods</a></p></article>' for item in manifest)
    index = destination / "OPEN_FIGURE_SET_TRANCHE_3.html"
    index.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codex Figure Factory tranche 3</title><style>body{font:15px/1.45 system-ui;margin:0;background:#f4f6f8;color:#17212b}header,main{max-width:1500px;margin:auto;padding:22px}article{background:white;border:1px solid #d8dee5;border-radius:8px;padding:14px;margin:0 0 20px}img{max-width:100%;height:auto}h1{margin-bottom:4px}h2{font-size:18px}a{color:#31688e}</style></head><body><header>' + f'<h1>Codex Figure Factory tranche 3</h1><p>28 sealed-evidence per-gene MIBiG, KCB, module, and substrate sets. {html.escape(GLOBAL_CLAIM_CEILING)}</p></header><main>{cards}</main></body></html>', encoding="utf-8")
    checks = _validate_outputs(destination, manifest, governed, IMPLEMENTED_IDS_3, ("FS098", "FS106", "FS114", "FS122"))
    receipt = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL", "profile": PROFILE, "source": {"widget_data": str(widget_path), "widget_sha256": _sha256(widget_path), "source_bundle": str(bundle), "source_bundle_receipt_sha256": _sha256(source_receipt)}, "governed_strains": len(governed), "all_packaged_strains": len(all_ids), "implemented_count": len(manifest), "implemented_ids": list(IMPLEMENTED_IDS_3), "claim_ceiling": GLOBAL_CLAIM_CEILING, "machine_checks": checks, "figures": manifest, "index": {"path": index.name, "sha256": _sha256(index)}}
    (destination / "TRANCHE_3_QA_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (destination / "FIGURE_MANIFEST.json").write_text(json.dumps({"schema_version": SCHEMA_VERSION, "figures": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--widget-data", required=True); parser.add_argument("--source-bundle", required=True); parser.add_argument("--outdir", required=True)
    args = parser.parse_args(argv); receipt = render_tranche_3(args.widget_data, args.source_bundle, args.outdir); emit(json.dumps(receipt, indent=2)); return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())

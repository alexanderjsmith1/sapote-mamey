#!/usr/bin/env python3
"""Render 92 source-backed non-lead figure sets (tranche 5).

This tranche completes seven governed lenses for thirteen evidence families and
adds the host-cohort class-co-occurrence lens. Lead-context lenses remain
unrendered until an explicit lead ledger is supplied.
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

import csv
import html
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .figure_set_registry import GLOBAL_CLAIM_CEILING, PROFILE, build_registry
from .figure_set_renderer import (
    Chart, HOST_ORDER, _host, _load, _sha256, _strain_key, _validate_outputs,
    _write_rows, render_svg,
)


SCHEMA_VERSION = "sapote-mamey.codex-figure-set-render.tranche5.v1"
FAMILY_BASES = {
    "LEN": 25, "CDS": 33, "RES": 73, "TRN": 81, "TTA": 89,
    "DOM": 129, "ACT": 137, "CCT": 145, "MIS": 153, "PRI": 161,
    "NOV": 169, "RGG": 177, "EVD": 193,
}
IMPLEMENTED_IDS_5 = tuple(
    ["FS021"]
    + [f"FS{base + offset:03d}" for base in FAMILY_BASES.values() for offset in range(7)]
)
LABEL_IDS_5 = tuple(f"FS{base + 1:03d}" for code, base in FAMILY_BASES.items() if code != "EVD") + ("FS194",)


@dataclass(frozen=True)
class Metric:
    code: str
    title: str
    unit: str
    field: str
    note: str


METRICS = (
    Metric("LEN", "Reported BGC length", "kb", "length_kb", "Reported antiSMASH region length; incomplete boundaries remain explicit."),
    Metric("CDS", "Physical CDS density", "CDS per 10 kb", "cds_per_10kb", "Physical CDS are deduplicated before the BGC-length join."),
    Metric("RES", "Resistance/self-protection routing tier", "tier ordinal", "resistance_ordinal", "Tier ordinals summarize source-derived routing evidence and do not validate self-protection."),
    Metric("TRN", "Transport-domain burden", "domain rows", "transporter_domains", "Transport annotations do not establish substrate, direction, or export."),
    Metric("TTA", "TTA context", "TTA codons", "tta_codons", "TTA occurrence is regulatory context and is not expression evidence."),
    Metric("DOM", "Domain architecture burden", "physical domain rows", "domain_rows", "Domain rows are deduplicated source annotations, not validated enzyme activities."),
    Metric("ACT", "Active-site motif evidence", "motif rows", "active_site_rows", "The sealed packages expose no active-site rows; structural unavailability is retained rather than converted to absence."),
    Metric("CCT", "Rare diagnostic chemistry triggers", "trigger memberships", "cctt_trigger_count", "Diagnostic marker memberships are routing evidence and do not define a pathway alone."),
    Metric("MIS", "Misanchor and routing-guard burden", "guard flags", "guard_count", "Guard flags explain routing and do not establish biological absence."),
    Metric("PRI", "AB/AF routing-prior midpoint", "routing-prior units", "prior_midpoint", "AB and AF are deterministic routing priors, not measured bioactivity."),
    Metric("NOV", "Novelty routing prior", "routing-prior units", "novelty_auto", "The deterministic novelty prior is not a novelty claim."),
    Metric("RGG", "RG-GMCI candidate-pair burden", "candidate pairs", "candidate_pairs", "Candidate pairs are cross-contig routing evidence, not physically validated pathways."),
)


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _num(value: Any) -> float | None:
    try:
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def _median(values: Iterable[float]) -> float:
    seq = list(values)
    return float(statistics.median(seq)) if seq else 0.0


def _quantile(values: Iterable[float], q: float) -> float:
    seq = sorted(float(value) for value in values)
    if not seq:
        return 0.0
    if len(seq) == 1:
        return seq[0]
    position = (len(seq) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    return seq[lo] if lo == hi else seq[lo] + (seq[hi] - seq[lo]) * (position - lo)


def _top(counter: Counter[str], n: int) -> list[str]:
    return [key for key, _value in sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))[:n]]


def _resistance_ordinal(value: str) -> float:
    upper = value.upper()
    if upper.startswith("T1_"): return 3.0
    if upper.startswith("T2_"): return 2.0
    if upper.startswith("T3_"): return 1.0
    return 0.0


def _metric_rows(bundle: Path) -> list[dict[str, Any]]:
    extended = _read(bundle / "BGC_EXTENDED_EVIDENCE.csv")
    domains = _read(bundle / "DOMAIN_FAMILY_CALLS.csv")
    rgg = _read(bundle / "RGGMCI_BGC_SUMMARY.csv")
    domain_total: Counter[tuple[str, str]] = Counter()
    for row in domains:
        domain_total[(row["strain"], row["bgc_id"])] += int(_num(row.get("physical_domain_rows")) or 0)
    rgg_map = {(row["strain"], row["bgc_id"]): _num(row.get("candidate_pairs")) or 0.0 for row in rgg}
    result: list[dict[str, Any]] = []
    for row in extended:
        flags = sum(bool((row.get(field) or "").strip()) for field in ("primary_metab_flag", "standing_rule", "misanchor_flag"))
        # v9.7.374 fix: a BGC downgraded by a standing rule (e.g. SACCHARIDE) or flagged
        # primary-metabolism/pigment keeps its raw AB/AF/novelty scores in the sealed triage
        # board (mamey/scoring.py::triage_bgcs() deliberately leaves those scores populated so
        # the exclusion reason is auditable) but is excluded from lead ranking there
        # (corrected_rank stays unset). PRI/NOV must not let that raw, pre-exclusion score pose
        # as a routing-prior/novelty LEAD in the governed cohort figures below.
        lead_excluded = bool((row.get("primary_metab_flag") or "").strip()) or bool((row.get("standing_rule") or "").strip())
        ab, af = _num(row.get("ab_auto")), _num(row.get("af_auto"))
        values = {
            "length_kb": _num(row.get("length_kb")),
            "cds_per_10kb": _num(row.get("cds_per_10kb")),
            "resistance_ordinal": _resistance_ordinal(row.get("resistance_tier") or ""),
            "transporter_domains": _num(row.get("transporter_domains")),
            "tta_codons": _num(row.get("tta_codons")),
            "domain_rows": float(domain_total[(row["strain"], row["bgc_id"])]),
            "active_site_rows": _num(row.get("active_site_rows")),
            "cctt_trigger_count": _num(row.get("cctt_trigger_count")),
            "guard_count": float(flags),
            "prior_midpoint": (ab + af) / 2.0 if ab is not None and af is not None else None,
            "novelty_auto": _num(row.get("novelty_auto")),
            "candidate_pairs": rgg_map.get((row["strain"], row["bgc_id"]), 0.0),
        }
        state_overrides = {"ACT": row.get("active_site_state") or "STRUCTURALLY_UNAVAILABLE"}
        for code in ("RES", "TRN", "TTA", "CCT"):
            if row.get("deep_profile_state") == "MISSING": state_overrides[code] = "MISSING"
        for code in ("MIS", "PRI", "NOV"):
            if row.get("triage_source_state") == "MISSING": state_overrides[code] = "MISSING"
        if row.get("domain_source_state") == "MISSING": state_overrides["DOM"] = "MISSING"
        if row.get("rggmci_source_state") == "MISSING": state_overrides["RGG"] = "MISSING"
        for metric in METRICS:
            value = values[metric.field]
            state = state_overrides.get(metric.code) or ("MISSING" if value is None else ("OBSERVED_ZERO" if value == 0 else "POPULATED"))
            result.append({
                "family": metric.code, "strain": row["strain"], "governance": row["governance"],
                "host_group": row["host_group"], "bgc_id": row["bgc_id"],
                "boundary": row["boundary"], "products": row["products"],
                "value": value if value is not None else "", "state": state,
                "ab_auto": ab if ab is not None else "", "af_auto": af if af is not None else "",
                "lead_excluded": lead_excluded,
            })
    return result


def _class_map(memberships: Sequence[dict[str, str]]) -> dict[tuple[str, str], set[str]]:
    result: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in memberships:
        result[(row["strain"], row["bgc_id"])].add(row["product_class"])
    return result


def _build_metric_charts(
    metric: Metric,
    rows_all: Sequence[dict[str, Any]],
    memberships_all: Sequence[dict[str, str]],
    strains: dict[str, Any],
    governed: Sequence[str],
) -> list[Chart]:
    base = FAMILY_BASES[metric.code]
    ids = [f"FS{base + offset:03d}" for offset in range(7)]
    governed_set = set(governed)
    rows = [row for row in rows_all if row["family"] == metric.code and row["strain"] in governed_set]
    if metric.code in {"PRI", "NOV"}:
        # v9.7.374 fix: standing-rule/primary-metabolism-excluded BGCs keep their raw AB/AF/
        # novelty scores in the source row (see _metric_rows) but must not be plotted as
        # routing-prior/novelty leads here -- drop them before any chart in this family is built
        # so the ECDF, per-strain median, per-class/boundary/host views, and the governance-
        # sensitivity comparison all stay lead-clean, matching corrected_rank's own exclusion.
        rows = [row for row in rows if not row.get("lead_excluded")]
    all_family = [row for row in rows_all if row["family"] == metric.code]
    if metric.code in {"PRI", "NOV"}:
        # v9.7.408 (Codex hostile audit Q3): the "all packaged" arm of the governance-sensitivity panel
        # must use the SAME locus eligibility as the governed arm, or the paired medians compare
        # exclusion policy instead of cohort membership. With the whole roster governed the arms are
        # now equal by construction (tests/test_tranche5_sensitivity_eligibility_parity_v97408.py).
        all_family = [row for row in all_family if not row.get("lead_excluded")]
    if metric.code == "ACT":
        return _build_active_site_charts(rows, all_family, memberships_all, strains, governed)
    populated = [row for row in rows if row["value"] != "" and row["state"] not in {"MISSING", "STRUCTURALLY_UNAVAILABLE"}]
    chart_rows = [{"boundary": row["boundary"], "value": row["value"]} for row in populated]
    ceiling = max((float(row["value"]) for row in populated), default=1.0)
    if ceiling <= 0: ceiling = 1.0
    charts = [Chart(ids[0], "ecdf", f"{metric.title} — governed cohort overview",
                    f"Raw BGC-level values stratified by declared boundary. {metric.note}", chart_rows,
                    {"series": "boundary", "value": "value", "x_label": metric.unit, "max": ceiling})]

    strain_rows = []
    for sid in governed:
        subset = [row for row in rows if row["strain"] == sid]
        values = [float(row["value"]) for row in subset if row["value"] != "" and row["state"] not in {"MISSING", "STRUCTURALLY_UNAVAILABLE"}]
        if metric.code == "PRI":
            x_values = [float(row["ab_auto"]) for row in subset if row["ab_auto"] != ""]
            y_values = [float(row["af_auto"]) for row in subset if row["af_auto"] != ""]
            x_value, y_value = _median(x_values), _median(y_values)
            x_label, y_label = "Median AB routing prior", "Median AF routing prior"
        else:
            x_value, y_value = len(subset), _median(values)
            x_label, y_label = "Physical BGC rows", f"Median {metric.unit}"
        strain_rows.append({"strain": sid, "x_value": x_value, "y_value": y_value, "host": _host(strains[sid]), "populated_bgcs": len(values)})
    charts.append(Chart(ids[1], "scatter", f"{metric.title} — every governed strain",
                        f"Every governed strain is labelled adjacent to its mark; non-outliers are retained. {metric.note}", strain_rows,
                        {"x": "x_value", "y": "y_value", "label": "strain", "x_label": x_label, "y_label": y_label, "x_min": 0, "y_min": 0}))

    governed_memberships = [row for row in memberships_all if row["strain"] in governed_set]
    memberships = _class_map(governed_memberships)
    class_counts = Counter(row["product_class"] for row in governed_memberships)
    top_classes = _top(class_counts, 15)
    values_by_class: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row["value"] == "" or row["state"] in {"MISSING", "STRUCTURALLY_UNAVAILABLE"}: continue
        for product_class in memberships.get((row["strain"], row["bgc_id"]), set()):
            values_by_class[product_class].append(float(row["value"]))
    class_rows = []
    for product_class in top_classes:
        values = values_by_class[product_class]
        for statistic, value in (("Median", _median(values)), ("Q75", _quantile(values, .75)), ("Q90", _quantile(values, .90))):
            class_rows.append({"class": product_class, "statistic": statistic, "value": value})
    charts.append(Chart(ids[2], "heatmap", f"{metric.title} by BGC class",
                        f"Nonexclusive class memberships retain physical BGC identity; summary statistics share {metric.unit}. {metric.note}", class_rows,
                        {"row": "class", "column": "statistic", "value": "value", "legend": metric.unit}))

    boundary_rows = []
    for boundary in ("Edge", "Full-contig", "Interior", "MISSING"):
        values = [float(row["value"]) for row in rows if row["boundary"] == boundary and row["value"] != "" and row["state"] not in {"MISSING", "STRUCTURALLY_UNAVAILABLE"}]
        if values or boundary != "MISSING":
            boundary_rows.append({"boundary": boundary, "q25": _quantile(values, .25), "median": _median(values), "q75": _quantile(values, .75), "n": len(values)})
    charts.append(Chart(ids[3], "dot_range", f"{metric.title} by BGC boundary context",
                        f"Points are medians and intervals are interquartile ranges; boundary states are not collapsed. {metric.note}", boundary_rows,
                        {"category": "boundary", "low": "q25", "mid": "median", "high": "q75", "x_label": metric.unit}))

    host_rows = []
    for host in HOST_ORDER:
        values = [float(row["value"]) for row in rows if row["host_group"] == host and row["value"] != "" and row["state"] not in {"MISSING", "STRUCTURALLY_UNAVAILABLE"}]
        host_rows.append({"host": host, "q25": _quantile(values, .25), "median": _median(values), "q75": _quantile(values, .75), "n": len(values)})
    charts.append(Chart(ids[4], "dot_range", f"{metric.title} by host cohort",
                        f"Host groups use the provenance-supported crosswalk and retain UNRESOLVED; no host causality is inferred. {metric.note}", host_rows,
                        {"category": "host", "low": "q25", "mid": "median", "high": "q75", "x_label": metric.unit}))

    state_rank = {"MISSING": -1, "STRUCTURALLY_UNAVAILABLE": -1, "OBSERVED_ZERO": 0, "POPULATED": 1}
    availability_rows = []
    for sid in governed:
        subset = [row for row in rows if row["strain"] == sid]
        states = Counter(row["state"] for row in subset)
        if states.get("POPULATED"): state = "POPULATED"
        elif states.get("OBSERVED_ZERO"): state = "OBSERVED_ZERO"
        elif states.get("STRUCTURALLY_UNAVAILABLE"): state = "STRUCTURALLY_UNAVAILABLE"
        else: state = "MISSING"
        availability_rows.append({"strain": sid, "measure": metric.code, "state": state, "value": state_rank[state], "bgcs": len(subset)})
    charts.append(Chart(ids[5], "state_heatmap", f"{metric.title} evidence availability",
                        f"Observed zero, missing, and structurally unavailable states remain distinct in plotted data. {metric.note}", availability_rows,
                        {"row": "strain", "column": "measure", "value": "value", "state": "state"}))

    all_memberships = _class_map(memberships_all)
    all_class_counts = Counter(row["product_class"] for row in memberships_all)
    sensitivity_classes = _top(all_class_counts, 12)
    def class_values(source_rows: Sequence[dict[str, Any]], mapping: dict[tuple[str, str], set[str]]) -> dict[str, list[float]]:
        values: dict[str, list[float]] = defaultdict(list)
        for row in source_rows:
            if row["value"] == "" or row["state"] in {"MISSING", "STRUCTURALLY_UNAVAILABLE"}: continue
            for product_class in mapping.get((row["strain"], row["bgc_id"]), set()):
                values[product_class].append(float(row["value"]))
        return values
    governed_values = class_values(rows, memberships)
    all_values = class_values(all_family, all_memberships)
    sensitivity_rows = [{"class": cls, "governed": _median(governed_values[cls]), "all_packaged": _median(all_values[cls])} for cls in sensitivity_classes]
    charts.append(Chart(ids[6], "paired_dot", f"{metric.title} — governance sensitivity",
                        f"Governed and all-packaged medians are paired for the same nonexclusive class denominator. {metric.note}", sensitivity_rows,
                        {"category": "class", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": metric.unit}))
    return charts


def _build_active_site_charts(
    rows: Sequence[dict[str, Any]],
    all_rows: Sequence[dict[str, Any]],
    memberships_all: Sequence[dict[str, str]],
    strains: dict[str, Any],
    governed: Sequence[str],
) -> list[Chart]:
    """Render state-first views when the source exposes no active-site table."""
    governed_set = set(governed)
    state_counts = Counter(row["state"] for row in rows)
    charts = [Chart("FS137", "bar", "Active-site motif evidence — governed cohort overview",
                    "The sealed source exposes no active-site rows; structural unavailability is plotted as an evidence state, not as motif absence.",
                    [{"evidence_state": state, "physical_bgcs": count} for state, count in sorted(state_counts.items())],
                    {"category": "evidence_state", "value": "physical_bgcs", "x_label": "Physical BGC rows"})]
    strain_rows = []
    for sid in governed:
        subset = [row for row in rows if row["strain"] == sid]
        unavailable = sum(row["state"] == "STRUCTURALLY_UNAVAILABLE" for row in subset)
        strain_rows.append({"strain": sid, "physical_bgcs": len(subset), "structurally_unavailable_pct": 100 * unavailable / max(1, len(subset)), "host": _host(strains[sid])})
    charts.append(Chart("FS138", "scatter", "Active-site evidence state — every governed strain",
                        "Every governed strain is labelled; structural unavailability is not interpreted as biological absence.", strain_rows,
                        {"x": "physical_bgcs", "y": "structurally_unavailable_pct", "label": "strain", "x_label": "Physical BGC rows", "y_label": "Structurally unavailable (%)", "x_min": 0, "y_min": 0, "y_max": 100}))
    memberships = _class_map([row for row in memberships_all if row["strain"] in governed_set])
    class_counts = Counter(row["product_class"] for row in memberships_all if row["strain"] in governed_set)
    classes = _top(class_counts, 15)
    class_states: Counter[tuple[str, str]] = Counter()
    class_den: Counter[str] = Counter()
    for row in rows:
        for cls in memberships.get((row["strain"], row["bgc_id"]), set()):
            class_states[(cls, row["state"])] += 1; class_den[cls] += 1
    state_order = ("POPULATED", "OBSERVED_ZERO", "STRUCTURALLY_UNAVAILABLE", "MISSING")
    charts.append(Chart("FS139", "heatmap", "Active-site evidence state by BGC class",
                        "Cells are percentages of nonexclusive class memberships in each evidence state.",
                        [{"class": cls, "state": state, "percent": 100 * class_states[(cls, state)] / max(1, class_den[cls])} for cls in classes for state in state_order],
                        {"row": "class", "column": "state", "value": "percent", "legend": "Class memberships (%)"}))
    for figure_id, title, category, categories, value_getter in (
        ("FS140", "Active-site evidence state by BGC boundary context", "boundary", ("Edge", "Full-contig", "Interior"), lambda row: row["boundary"]),
        ("FS141", "Active-site evidence state by host cohort", "host", HOST_ORDER, lambda row: row["host_group"]),
    ):
        den = Counter(value_getter(row) for row in rows); counts = Counter((value_getter(row), row["state"]) for row in rows)
        data = [{category: item, "state": state, "percent": 100 * counts[(item, state)] / max(1, den[item])} for item in categories for state in state_order]
        charts.append(Chart(figure_id, "heatmap", title,
                            "Evidence states retain structural unavailability and missingness; no absence claim is made.", data,
                            {"row": category, "column": "state", "value": "percent", "legend": "Physical BGC rows (%)"}))
    availability = []
    state_rank = {"MISSING": -1, "STRUCTURALLY_UNAVAILABLE": -1, "OBSERVED_ZERO": 0, "POPULATED": 1}
    for sid in governed:
        subset = [row for row in rows if row["strain"] == sid]
        state = "POPULATED" if any(row["state"] == "POPULATED" for row in subset) else ("STRUCTURALLY_UNAVAILABLE" if any(row["state"] == "STRUCTURALLY_UNAVAILABLE" for row in subset) else "MISSING")
        availability.append({"strain": sid, "measure": "ACT", "state": state, "value": state_rank[state]})
    charts.append(Chart("FS142", "state_heatmap", "Active-site evidence availability",
                        "Gray cells retain structurally unavailable or missing evidence as declared in plotted data.", availability,
                        {"row": "strain", "column": "measure", "value": "value", "state": "state"}))
    all_memberships = _class_map(memberships_all); all_counts = Counter(row["product_class"] for row in memberships_all)
    sensitivity = []
    for cls in _top(all_counts, 12):
        def unavailable_pct(source_rows, mapping):
            selected = [row for row in source_rows if cls in mapping.get((row["strain"], row["bgc_id"]), set())]
            return 100 * sum(row["state"] == "STRUCTURALLY_UNAVAILABLE" for row in selected) / max(1, len(selected))
        sensitivity.append({"class": cls, "governed": unavailable_pct(rows, memberships), "all_packaged": unavailable_pct(all_rows, all_memberships)})
    charts.append(Chart("FS143", "paired_dot", "Active-site evidence state — governance sensitivity",
                        "Governed and all-packaged structural-unavailability percentages use the same class denominator.", sensitivity,
                        {"category": "class", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": "Structurally unavailable (%)", "max": 100}))
    return charts


def _cooccurrence_host_chart(bundle: Path, governed: Sequence[str], strains: dict[str, Any]) -> Chart:
    governed_set = set(governed)
    rows = [row for row in _read(bundle / "BGC_CLASS_PAIRS.csv") if row["strain"] in governed_set]
    pair_counts = Counter(" + ".join(sorted((row["class_a"], row["class_b"]))) for row in rows)
    pairs = _top(pair_counts, 12)
    host_strains = Counter(_host(strains[sid]) for sid in governed)
    counts = Counter((_host(strains[row["strain"]]), " + ".join(sorted((row["class_a"], row["class_b"])))) for row in rows)
    data = [{"host": host, "class_pair": pair, "pairs_per_strain": counts[(host, pair)] / host_strains[host] if host_strains[host] else 0.0} for host in HOST_ORDER for pair in pairs]
    return Chart("FS021", "heatmap", "BGC class co-occurrence by host cohort",
                 "Nonexclusive within-BGC class pairs are normalized per governed strain; host association is context, not causality.", data,
                 {"row": "host", "column": "class_pair", "value": "pairs_per_strain", "legend": "Class-pair memberships per governed strain"})


def _evidence_charts(bundle: Path, memberships_all: Sequence[dict[str, str]], strains: dict[str, Any], governed: Sequence[str]) -> list[Chart]:
    rows_all = _read(bundle / "EVIDENCE_CHANNEL_STATES.csv")
    governed_set = set(governed)
    rows = [row for row in rows_all if row["strain"] in governed_set]
    positive = lambda state: state.upper() in {"PASS", "MAMEY_COMPLETE", "RECOVERY_VALIDATED"} or state.upper().startswith("COMPLETED")
    state_counts = Counter((row["channel_group"], row["state"]) for row in rows)
    overview = [{"state": f"{group}: {state}", "strain_channel_rows": count} for (group, state), count in sorted(state_counts.items(), key=lambda item: (-item[1], item[0]))[:18]]
    charts = [Chart("FS193", "bar", "Evidence completeness and governance — cohort overview",
                    "Engineering/package, source-scan, and evidence-channel states remain separate; missing evidence is not a biological negative.", overview,
                    {"category": "state", "value": "strain_channel_rows", "x_label": "Strain-channel rows"})]
    strain_rows = []
    for sid in governed:
        subset = [row for row in rows if row["strain"] == sid]
        complete = sum(positive(row["state"]) for row in subset)
        strain_rows.append({"strain": sid, "complete_channels": complete, "pending_or_gated_channels": len(subset) - complete, "host": _host(strains[sid])})
    charts.append(Chart("FS194", "scatter", "Evidence-channel landscape — every governed strain",
                        "Every governed strain is labelled; completed/pass-like and pending/gated channels are counted separately.", strain_rows,
                        {"x": "complete_channels", "y": "pending_or_gated_channels", "label": "strain", "x_label": "Completed or PASS-like channels", "y_label": "Pending, gated, or unavailable channels", "x_min": 0, "y_min": 0}))

    score = {sid: 100.0 * sum(positive(row["state"]) for row in rows if row["strain"] == sid) / max(1, sum(1 for row in rows if row["strain"] == sid)) for sid in governed}
    governed_memberships = [row for row in memberships_all if row["strain"] in governed_set]
    class_counts = Counter(row["product_class"] for row in governed_memberships)
    top_classes = _top(class_counts, 15)
    class_values: dict[str, list[float]] = defaultdict(list)
    for row in governed_memberships: class_values[row["product_class"]].append(score[row["strain"]])
    class_rows = [{"class": cls, "metric": "Median complete/pass-like %", "value": _median(class_values[cls])} for cls in top_classes]
    charts.append(Chart("FS195", "heatmap", "Evidence completeness by BGC class context",
                        "Package-level channel completeness is contextualized by nonexclusive class membership; it is not BGC-level biological evidence.", class_rows,
                        {"row": "class", "column": "metric", "value": "value", "legend": "Median complete/pass-like channels (%)"}))
    for figure_id, title, category, categories in (
        ("FS196", "Evidence completeness by BGC boundary context", "boundary", ("Edge", "Full-contig", "Interior")),
        ("FS197", "Evidence completeness by host cohort", "host", HOST_ORDER),
    ):
        values: dict[str, list[float]] = defaultdict(list)
        if category == "boundary":
            for row in _read(bundle / "BGC_RECORDS.csv"):
                if row["strain"] in governed_set: values[row["boundary"]].append(score[row["strain"]])
        else:
            for sid in governed: values[_host(strains[sid])].append(score[sid])
        data = [{category: item, "q25": _quantile(values[item], .25), "median": _median(values[item]), "q75": _quantile(values[item], .75)} for item in categories]
        charts.append(Chart(figure_id, "dot_range", title,
                            "Package-level channel states remain engineering/evidence context and are not biological outcomes.", data,
                            {"category": category, "low": "q25", "mid": "median", "high": "q75", "x_label": "Complete/pass-like channels (%)"}))

    channel_counts = Counter(row["channel"] for row in rows)
    channels = _top(channel_counts, 15)
    state_lookup = {(row["strain"], row["channel"]): row["state"] for row in rows}
    availability = []
    for sid in governed:
        for channel in channels:
            state = state_lookup.get((sid, channel), "MISSING")
            value = 1 if positive(state) else (-1 if state == "MISSING" else 0)
            availability.append({"strain": sid, "channel": channel, "state": state, "value": value})
    charts.append(Chart("FS198", "state_heatmap", "Evidence-channel availability by strain",
                        "Green marks completed/pass-like states, white retains gated or pending states, and gray marks missing rows.", availability,
                        {"row": "strain", "column": "channel", "value": "value", "state": "state"}))

    all_ids = sorted({row["strain"] for row in rows_all}, key=_strain_key)
    sensitivity = []
    for channel in channels:
        governed_states = [row["state"] for row in rows if row["channel"] == channel]
        all_states = [row["state"] for row in rows_all if row["channel"] == channel]
        sensitivity.append({"channel": channel, "governed": 100 * sum(map(positive, governed_states)) / max(1, len(governed_states)), "all_packaged": 100 * sum(map(positive, all_states)) / max(1, len(all_states)), "all_strains": len(all_ids)})
    charts.append(Chart("FS199", "paired_dot", "Evidence-channel state — governance sensitivity",
                        "The same channel definitions are compared in governed and all-packaged strain denominators.", sensitivity,
                        {"category": "channel", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": "Complete/pass-like strains (%)", "max": 100}))
    return charts


def build_charts_5(payload: dict[str, Any], governed: Sequence[str], bundle: Path) -> list[Chart]:
    strains = payload["strains"]
    memberships_all = _read(bundle / "BGC_CLASS_MEMBERSHIPS.csv")
    metric_rows = _metric_rows(bundle)
    charts = [_cooccurrence_host_chart(bundle, governed, strains)]
    for metric in METRICS:
        charts.extend(_build_metric_charts(metric, metric_rows, memberships_all, strains, governed))
    charts.extend(_evidence_charts(bundle, memberships_all, strains, governed))
    if tuple(chart.figure_id for chart in charts) != IMPLEMENTED_IDS_5:
        raise AssertionError("tranche 5 figure order does not match registry IDs")
    return charts


def render_tranche_5(widget_data: str | Path, source_bundle: str | Path, outdir: str | Path) -> dict[str, Any]:
    widget_path, payload, all_ids, governed = _load(widget_data)
    bundle = Path(source_bundle).resolve()
    source_receipt = bundle / "SOURCE_BUNDLE_RECEIPT.json"
    if not source_receipt.is_file():
        raise ValueError("source bundle has no SOURCE_BUNDLE_RECEIPT.json")
    destination = Path(outdir).resolve(); destination.mkdir(parents=True, exist_ok=True)
    figures_dir, data_dir, text_dir = destination / "figures", destination / "data", destination / "text"
    for directory in (figures_dir, data_dir, text_dir): directory.mkdir(parents=True, exist_ok=True)
    registry = {record["figure_set_id"]: record for record in build_registry()}
    charts = build_charts_5(payload, governed, bundle)
    manifest = []
    for chart in charts:
        svg_path = figures_dir / f"{chart.figure_id}.svg"
        csv_path = data_dir / f"{chart.figure_id}_data.csv"
        text_path = text_dir / f"{chart.figure_id}_CAPTION_METHODS.md"
        svg_path.write_text(render_svg(chart), encoding="utf-8")
        _write_rows(csv_path, chart.rows)
        spec = registry[chart.figure_id]
        text_path.write_text(
            f"# {chart.figure_id} — {chart.title}\n\n## Caption\n\n{spec['caption_template']}\n\n"
            f"## Methods\n\n{spec['methods_template']}\n\n## Render-specific note\n\n{chart.subtitle}\n\n"
            f"## Claim ceiling\n\n{GLOBAL_CLAIM_CEILING}\n\n## Citation status\n\n"
            "Citations must be reviewed against the source release and upstream evidence channels at manuscript freeze.\n",
            encoding="utf-8",
        )
        manifest.append({
            "figure_set_id": chart.figure_id, "title": chart.title, "kind": chart.kind, "rows": len(chart.rows),
            "svg": str(svg_path.relative_to(destination)), "data_csv": str(csv_path.relative_to(destination)),
            "caption_methods": str(text_path.relative_to(destination)), "svg_sha256": _sha256(svg_path),
            "data_sha256": _sha256(csv_path), "text_sha256": _sha256(text_path),
        })
    cards = "".join(
        f'<article><h2>{html.escape(item["figure_set_id"])} — {html.escape(item["title"])}</h2>'
        f'<img src="{html.escape(item["svg"])}" alt="{html.escape(item["title"])}">'
        f'<p><a href="{html.escape(item["data_csv"])}">Plotted data</a> · '
        f'<a href="{html.escape(item["caption_methods"])}">Caption and methods</a></p></article>'
        for item in manifest
    )
    index = destination / "OPEN_FIGURE_SET_TRANCHE_5.html"
    index.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Codex Figure Factory tranche 5</title><style>body{font:15px/1.45 system-ui;margin:0;background:#f4f6f8;color:#17212b}'
        'header,main{max-width:1500px;margin:auto;padding:22px}article{background:white;border:1px solid #d8dee5;border-radius:8px;padding:14px;margin:0 0 20px}'
        'img{max-width:100%;height:auto}h2{font-size:18px}a{color:#31688e}</style></head><body><header>'
        f'<h1>Codex Figure Factory tranche 5</h1><p>92 source-backed strain- and cohort-specific sets. {html.escape(GLOBAL_CLAIM_CEILING)}</p>'
        f'</header><main>{cards}</main></body></html>', encoding="utf-8")
    checks = _validate_outputs(destination, manifest, governed, IMPLEMENTED_IDS_5, LABEL_IDS_5)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "profile": PROFILE,
        "source": {"widget_data": str(widget_path), "widget_sha256": _sha256(widget_path), "source_bundle": str(bundle), "source_bundle_receipt_sha256": _sha256(source_receipt)},
        "governed_strains": len(governed), "all_packaged_strains": len(all_ids),
        "implemented_count": len(manifest), "implemented_ids": list(IMPLEMENTED_IDS_5),
        "lead_context_policy": "not rendered without an explicit lead ledger",
        "claim_ceiling": GLOBAL_CLAIM_CEILING, "machine_checks": checks, "figures": manifest,
        "index": {"path": index.name, "sha256": _sha256(index)},
    }
    (destination / "TRANCHE_5_QA_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (destination / "FIGURE_MANIFEST.json").write_text(json.dumps({"schema_version": SCHEMA_VERSION, "figures": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--widget-data", required=True); parser.add_argument("--source-bundle", required=True); parser.add_argument("--outdir", required=True)
    args = parser.parse_args(); result = render_tranche_5(args.widget_data, args.source_bundle, args.outdir)
    emit(json.dumps(result, indent=2)); raise SystemExit(0 if result["status"] == "PASS" else 1)

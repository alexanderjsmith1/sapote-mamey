"""Per-strain antibacterial/antifungal activity-lead routing report.

This module re-projects the existing ``AB_auto`` and ``AF_auto`` columns from
sealed Mamey triage boards.  It does not compute a new activity score and does
not claim compound identity, production, or bioactivity.

Every displayed BGC is required to carry the complete identity
``strain / full node-or-contig / region / BGC alias``.  An optional canonical
crosswalk can rebind stale source-local aliases by the physical
``(strain, node-or-contig, region)`` key.  When ``require_crosswalk`` is true,
unmatched rows are held out rather than guessed.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import math
import os
import re
from collections import defaultdict
from typing import Any

from .cohort_leads_ledger import find_triage_boards


AXES = ("antifungal", "antibacterial")
AF_PREFIXES = ("T43-NUC", "T43-PTM", "T43-PYE")
AB_PREFIXES = (
    "T43-LAN", "T43-LASSO", "T43-THA", "T43-PHO", "T43-AMC",
    "T43-BLA", "T43-GPA", "T43-BLT",
)
TIER_ORDER = {"exceptional": 5, "high": 4, "medium": 3, "low": 2, "inventory": 1}  # v9.7.409 A2 (AQUARIUS_01): Low ranks strictly above Inventory; matches package_addons.py
BOUNDARY_ORDER = {"interior": 3, "full-contig": 2, "edge": 1}

OUTPUT_COLUMNS = [
    "strain", "axis", "axis_rank_within_strain", "exact_locus",
    "full_node_or_contig", "region", "bgc_alias", "source_local_bgc_alias",
    "alias_binding_state", "identity_state", "axis_score", "other_axis_score",
    "lead_eligible", "selection_state", "Lead_tier_auto", "Corrected_rank",
    "Products", "Boundary", "Novelty_auto", "CCTT_triggers",
    "axis_diagnostic_triggers", "KCB_top", "KCB_score",
    "interpretability_tier", "interpretability_hold", "engine_version",
    "source_triage_board", "claim_ceiling",
]

UNBOUND_COLUMNS = [
    "strain", "full_node_or_contig", "region", "source_local_bgc_alias",
    "state", "reason", "source_triage_board",
]


def _num(value: Any, default: float = float("-inf")) -> float:
    try:
        text = str(value).strip()
        return float(text) if text else default
    except (TypeError, ValueError):
        return default


def _truthy(value: Any) -> bool:
    return str(value or "").strip().upper() not in {"", "NONE", "FALSE", "0", "NO", "N/A"}


def _tokens(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;,]", value or "") if part.strip()]


def _diagnostic_tokens(value: str, axis: str) -> list[str]:
    prefixes = AF_PREFIXES if axis == "antifungal" else AB_PREFIXES
    return [token for token in _tokens(value) if token.upper().startswith(prefixes)]


def _lead_eligible(row: dict[str, str]) -> bool:
    return bool((row.get("Corrected_rank") or "").strip()) and not any(
        _truthy(row.get(key))
        for key in ("Standing_rule", "Primary_metab_flag", "Misanchor_Flag", "Mobile_element_flag")
    )


def _read_manifest(package_dir: str) -> dict[str, Any]:
    path = os.path.join(package_dir, "manifest.json")
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _strain_for(board: str, manifest: dict[str, Any]) -> str:
    value = manifest.get("strain_id") or manifest.get("display_name")
    if value:
        return str(value).strip()
    return os.path.basename(board).replace("_4_triage_board.csv", "").strip()


def _physical_components(row: dict[str, str]) -> tuple[str, str]:
    contig = (row.get("Contig") or row.get("Node_ID") or "").strip()
    region = (row.get("antiSMASH_Region") or "").strip()
    return contig, region


def _load_crosswalk(path: str | None) -> dict[tuple[str, str, str], str]:
    if not path:
        return {}
    index: dict[tuple[str, str, str], str] = {}
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"strain", "full_node_or_contig", "region", "bgc_alias"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(
                "canonical crosswalk requires columns: strain, full_node_or_contig, region, bgc_alias"
            )
        for row in reader:
            key = (
                (row.get("strain") or "").strip(),
                (row.get("full_node_or_contig") or "").strip(),
                (row.get("region") or "").strip(),
            )
            alias = (row.get("bgc_alias") or "").strip()
            if not all(key) or not alias:
                raise ValueError(f"incomplete canonical crosswalk row: {row}")
            if key in index:
                raise ValueError(f"duplicate canonical physical key: {key}")
            index[key] = alias
    return index


def _rank_key(row: dict[str, str], axis: str) -> tuple[Any, ...]:
    score_col = "AF_auto" if axis == "antifungal" else "AB_auto"
    diagnostics = _diagnostic_tokens(row.get("CCTT_triggers") or "", axis)
    return (
        0 if _lead_eligible(row) else 1,
        -_num(row.get(score_col), 0.0),
        -TIER_ORDER.get((row.get("Lead_tier_auto") or "").strip().lower(), 0),
        -len(diagnostics),
        -BOUNDARY_ORDER.get((row.get("Boundary") or "").strip().lower(), 0),
        -_num(row.get("Novelty_auto"), 0.0),
        -_num(row.get("KCB_score"), 0.0),
        _num(row.get("Corrected_rank"), math.inf),
        (row.get("_canonical_alias") or row.get("BGC_ID") or ""),
    )


def _interpretability(row: dict[str, str]) -> tuple[str, str]:
    holds: list[str] = []
    if not _lead_eligible(row):
        holds.append("engine exclusion or downgrade")
    boundary = (row.get("Boundary") or "").strip().lower()
    if boundary == "edge":
        holds.append("edge-truncated interval")
    elif boundary == "full-contig":
        holds.append("full-contig call may remain biologically truncated")
    if row.get("_identity_state") == "SOURCE_PACKAGE_LOCATOR_ONLY":
        holds.append("canonical alias crosswalk not supplied")
    if holds:
        return "CONDITIONAL", "; ".join(holds)
    return "STRONGER_ROUTING_CANDIDATE", "no encoded exclusion or boundary warning"


def build_activity_leads(
    runs_dir: str,
    *,
    top_n: int = 5,
    canonical_crosswalk: str | None = None,
    require_crosswalk: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    """Build per-strain top-N AF/AB boards from sealed triage packages.

    ``canonical_crosswalk`` is a CSV with columns ``strain``,
    ``full_node_or_contig``, ``region``, and ``bgc_alias``.  The crosswalk is
    optional for a freshly sealed package whose alias is already authoritative.
    Set ``require_crosswalk=True`` when reconciling historical packages.
    """
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    crosswalk = _load_crosswalk(canonical_crosswalk)
    boards = find_triage_boards(runs_dir)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    unbound: list[dict[str, str]] = []
    versions: set[str] = set()

    for board in boards:
        package_dir = os.path.dirname(board)
        manifest = _read_manifest(package_dir)
        strain = _strain_for(board, manifest)
        engine = str(manifest.get("workflow_version") or manifest.get("engine_version") or "").strip()
        if engine:
            versions.add(engine)
        try:
            with open(board, newline="", encoding="utf-8-sig") as handle:
                source_rows = list(csv.DictReader(handle))
        except OSError:
            continue
        for source in source_rows:
            contig, region = _physical_components(source)
            source_alias = (source.get("BGC_ID") or "").strip()
            if not strain or not contig or not region or not source_alias:
                unbound.append({
                    "strain": strain,
                    "full_node_or_contig": contig,
                    "region": region,
                    "source_local_bgc_alias": source_alias,
                    "state": "INCOMPLETE_FOUR_PART_IDENTITY_NOT_ADMITTED",
                    "reason": "strain, full node-or-contig, region, and source alias are mandatory",
                    "source_triage_board": board,
                })
                continue
            key = (strain, contig, region)
            canonical_alias = crosswalk.get(key)
            if crosswalk and canonical_alias is None:
                unbound.append({
                    "strain": strain,
                    "full_node_or_contig": contig,
                    "region": region,
                    "source_local_bgc_alias": source_alias,
                    "state": "UNBOUND_SOURCE_LOCAL_ROW_NOT_ADMITTED",
                    "reason": "no unique physical-key match in canonical crosswalk",
                    "source_triage_board": board,
                })
                continue
            if require_crosswalk and canonical_alias is None:
                unbound.append({
                    "strain": strain,
                    "full_node_or_contig": contig,
                    "region": region,
                    "source_local_bgc_alias": source_alias,
                    "state": "CANONICAL_CROSSWALK_REQUIRED_NOT_ADMITTED",
                    "reason": "historical-package mode requires a canonical crosswalk",
                    "source_triage_board": board,
                })
                continue
            admitted = dict(source)
            admitted["_strain"] = strain
            admitted["_contig"] = contig
            admitted["_region"] = region
            admitted["_source_alias"] = source_alias
            admitted["_canonical_alias"] = canonical_alias or source_alias
            admitted["_identity_state"] = (
                "CANONICAL_CROSSWALK_PASS" if canonical_alias else "SOURCE_PACKAGE_LOCATOR_ONLY"
            )
            admitted["_engine"] = engine
            admitted["_board"] = board
            grouped[strain].append(admitted)

    output: list[dict[str, Any]] = []
    incomplete: dict[str, dict[str, int]] = {}
    for strain in sorted(grouped, key=str.casefold):
        source_rows = grouped[strain]
        for axis in AXES:
            ranked = sorted(source_rows, key=lambda row: _rank_key(row, axis))
            selected = ranked[:top_n]
            if len(selected) < top_n:
                incomplete.setdefault(strain, {})[axis] = len(selected)
            for rank, row in enumerate(selected, start=1):
                axis_col = "AF_auto" if axis == "antifungal" else "AB_auto"
                other_col = "AB_auto" if axis == "antifungal" else "AF_auto"
                alias = row["_canonical_alias"]
                exact = f"{strain} / {row['_contig']} / {row['_region']} / {alias}"
                interp, hold = _interpretability(row)
                output.append({
                    "strain": strain,
                    "axis": axis,
                    "axis_rank_within_strain": rank,
                    "exact_locus": exact,
                    "full_node_or_contig": row["_contig"],
                    "region": row["_region"],
                    "bgc_alias": alias,
                    "source_local_bgc_alias": row["_source_alias"],
                    "alias_binding_state": (
                        "UNCHANGED" if alias == row["_source_alias"]
                        else "PHYSICAL_KEY_REBOUND_TO_CANONICAL_ALIAS"
                    ),
                    "identity_state": row["_identity_state"],
                    "axis_score": _num(row.get(axis_col), 0.0),
                    "other_axis_score": _num(row.get(other_col), 0.0),
                    "lead_eligible": "YES" if _lead_eligible(row) else "NO",
                    "selection_state": (
                        "PRIMARY_ENGINE_ELIGIBLE" if _lead_eligible(row)
                        else "CONDITIONAL_FALLBACK_EXCLUDED"
                    ),
                    "Lead_tier_auto": (row.get("Lead_tier_auto") or "").strip(),
                    "Corrected_rank": (row.get("Corrected_rank") or "").strip(),
                    "Products": (row.get("Products") or "").strip(),
                    "Boundary": (row.get("Boundary") or "").strip(),
                    "Novelty_auto": (row.get("Novelty_auto") or "").strip(),
                    "CCTT_triggers": (row.get("CCTT_triggers") or "").strip(),
                    "axis_diagnostic_triggers": "; ".join(
                        _diagnostic_tokens(row.get("CCTT_triggers") or "", axis)
                    ),
                    "KCB_top": (row.get("KCB_top") or "").strip(),
                    "KCB_score": (row.get("KCB_score") or "").strip(),
                    "interpretability_tier": interp,
                    "interpretability_hold": hold,
                    "engine_version": row["_engine"],
                    "source_triage_board": row["_board"],
                    "claim_ceiling": (
                        "ROUTING_PRIOR_ONLY_NOT_COMPOUND_IDENTITY_PRODUCTION_OR_ACTIVITY"
                    ),
                })

    meta = {
        "n_strains": len(grouped),
        "n_rows": len(output),
        "top_n": top_n,
        "engine_versions": sorted(versions),
        "mixed_engine": len(versions) > 1,
        "unbound_rows": len(unbound),
        "incomplete_strains": incomplete,
        "complete": bool(grouped) and not incomplete,
        "canonical_crosswalk": canonical_crosswalk or "",
        "require_crosswalk": bool(require_crosswalk),
        "claim_safety": (
            "Routing priors only. Similarity is not identity; capacity is not production; "
            "missing evidence is not biological absence."
        ),
    }
    return output, unbound, meta


def _write_csv(path: str, rows: list[dict[str, Any]], columns: list[str]) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)
    return path


def write_activity_leads(
    rows: list[dict[str, Any]],
    unbound: list[dict[str, str]],
    meta: dict[str, Any],
    out_dir: str,
) -> dict[str, str]:
    """Write CSV, Markdown, and JSON outputs atomically where applicable."""
    os.makedirs(out_dir, exist_ok=True)
    leads_path = _write_csv(os.path.join(out_dir, "PER_STRAIN_ACTIVITY_LEADS.csv"), rows, OUTPUT_COLUMNS)
    unbound_path = _write_csv(os.path.join(out_dir, "PER_STRAIN_ACTIVITY_LEADS_UNBOUND.csv"), unbound, UNBOUND_COLUMNS)
    meta_path = os.path.join(out_dir, "PER_STRAIN_ACTIVITY_LEADS_META.json")
    tmp_meta = meta_path + ".tmp"
    with open(tmp_meta, "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_meta, meta_path)

    report_path = os.path.join(out_dir, "PER_STRAIN_ACTIVITY_LEADS_REPORT.md")
    by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by[(str(row["strain"]), str(row["axis"]))].append(row)
    lines = [
        "# Per-strain antibacterial and antifungal BGC lead boards",
        "",
        "**Status:** deterministic capacity-level routing report; scientific judgment remains required.",
        "",
        f"The report contains {meta['n_rows']} board positions across {meta['n_strains']} strains. ",
        "AF_auto and AB_auto are routing priors, not measured bioactivity.",
        "",
        "> Similarity is not identity; capacity is not production; missing evidence is not biological absence.",
        "",
    ]
    if meta["mixed_engine"]:
        lines += [
            "**Mixed-engine hold:** packages span " + ", ".join(meta["engine_versions"]) +
            "; cross-version score magnitudes are not strictly comparable.",
            "",
        ]
    for strain in sorted({str(row["strain"]) for row in rows}, key=str.casefold):
        lines += [f"## {strain}", ""]
        for axis in AXES:
            lines += [f"### {axis.capitalize()}-track top {meta['top_n']}", "", "| Rank | Exact locus | Prior | Interpretation |", "|---:|---|---:|---|"]
            for row in sorted(by[(strain, axis)], key=lambda item: int(item["axis_rank_within_strain"])):
                lines.append(
                    f"| {row['axis_rank_within_strain']} | {row['exact_locus']} | "
                    f"{float(row['axis_score']):.0f} | {row['interpretability_tier']}: "
                    f"{str(row['interpretability_hold']).replace('|', '/')} |"
                )
            lines.append("")
    tmp_report = report_path + ".tmp"
    with open(tmp_report, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    os.replace(tmp_report, report_path)
    return {
        "leads_csv": leads_path,
        "unbound_csv": unbound_path,
        "metadata_json": meta_path,
        "report_md": report_path,
    }


def run(
    runs_dir: str,
    out_dir: str,
    *,
    top_n: int = 5,
    canonical_crosswalk: str | None = None,
    require_crosswalk: bool = False,
) -> dict[str, Any]:
    rows, unbound, meta = build_activity_leads(
        runs_dir,
        top_n=top_n,
        canonical_crosswalk=canonical_crosswalk,
        require_crosswalk=require_crosswalk,
    )
    result = dict(meta)
    result["paths"] = write_activity_leads(rows, unbound, meta, out_dir)
    return result

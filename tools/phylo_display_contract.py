"""Shared, fail-closed display contract for EPA-ng and marker-tree renderers.

This module validates prepared display metadata. It does not infer taxonomy, locality,
assay state, topology, or reference membership.
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

ASSAY_SYMBOL = {"positive": "+", "negative": "-", "not_tested": "n.t.", "missing": "?"}
ROLES = {"query", "reference", "outgroup"}
LAYOUT_PROFILES = {
    "full_genus_single_line_v1": {
        "minimum_tree_fraction": 0.39,
        "minimum_tree_inches": 6.5,
        "single_line": True,
        "full_genus": True,
    }
}
REQUIRED_METADATA = {
    "tip", "role", "type_status", "taxon_display", "label_concise", "label_experiment",
    "raw_source", "source_category", "raw_geography", "geography",
    "candida_state", "mrsa_state", "assay_provenance", "experiment_id", "sample_id",
}
PROVENANCE_FIELDS = {"raw_source", "raw_geography", "candida_state", "mrsa_state"}
MISSING = {"", "unknown", "unresolved", "unbound", "not recorded", "missing", "n/a", "na"}


def digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_palette(path: str | Path) -> dict[tuple[str, str], str]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows or any(not {"field", "value", "color"} <= set(row) for row in rows):
        raise ValueError("PHYLO_PALETTE_SCHEMA")
    result: dict[tuple[str, str], str] = {}
    colors: dict[tuple[str, str], str] = {}
    for row in rows:
        field, value, color = row["field"].strip(), row["value"].strip(), row["color"].upper()
        if field not in {"source", "geography"} or value.casefold() in MISSING:
            raise ValueError("PHYLO_PALETTE_VALUE")
        if not re.fullmatch(r"#[0-9A-F]{6}", color):
            raise ValueError("PHYLO_PALETTE_COLOR")
        key, color_key = (field, value), (field, color)
        if key in result or color_key in colors:
            raise ValueError("PHYLO_PALETTE_DUPLICATE")
        result[key], colors[color_key] = color, value
    return result


def validate_layout_profile(name: str, tree_fraction: float) -> dict[str, object]:
    if name not in LAYOUT_PROFILES:
        raise ValueError("PHYLO_LAYOUT_PROFILE_UNSUPPORTED")
    profile = LAYOUT_PROFILES[name]
    if not 0 < float(tree_fraction) < 1:
        raise ValueError("PHYLO_LAYOUT_FRACTION")
    if float(tree_fraction) + 1e-9 < profile["minimum_tree_fraction"]:
        raise ValueError(
            f"PHYLO_LAYOUT_TREE_AREA_REGRESSION:{tree_fraction:.3f}<"
            f"{profile['minimum_tree_fraction']:.3f}"
        )
    return {"profile": name, **profile, "tree_fraction": float(tree_fraction)}


def _taxon_ok(value: str) -> bool:
    # Full genus, species or sp., optional subspecies, then a deliberate strain/culture suffix.
    return bool(re.fullmatch(
        r"[A-Z][A-Za-z-]+ (?:sp\.|[a-z][a-z-]+)(?: subsp\. [a-z][a-z-]+)?(?: .+)?", value
    ))


def validate_display_metadata(
    rows: list[dict[str, str]], provenance_rows: list[dict[str, str]],
    palette: dict[tuple[str, str], str], *, profile: str, tree_fraction: float,
) -> dict[str, object]:
    layout = validate_layout_profile(profile, tree_fraction)
    if not rows or any(not REQUIRED_METADATA <= set(row) for row in rows):
        raise ValueError("PHYLO_DISPLAY_METADATA_SCHEMA")
    tips = [row["tip"].strip() for row in rows]
    if any(not tip for tip in tips) or len(tips) != len(set(tips)):
        raise ValueError("PHYLO_DISPLAY_TIP_IDENTITY")
    for row in rows:
        tip, role = row["tip"].strip(), row["role"].strip().lower()
        if role not in ROLES:
            raise ValueError(f"PHYLO_DISPLAY_ROLE:{tip}")
        for field in ("taxon_display", "label_concise", "label_experiment", "raw_source",
                      "source_category", "raw_geography", "geography"):
            if row[field].strip().casefold() in MISSING:
                raise ValueError(f"PHYLO_DISPLAY_FIELD_UNBOUND:{tip}:{field}")
        if "\n" in row["label_concise"] or "\n" in row["label_experiment"]:
            raise ValueError(f"PHYLO_DISPLAY_MULTILINE_LABEL:{tip}")
        if not _taxon_ok(row["taxon_display"].strip()):
            raise ValueError(f"PHYLO_DISPLAY_TAXON_FORMAT:{tip}")
        if not row["label_concise"].startswith(row["taxon_display"]):
            raise ValueError(f"PHYLO_DISPLAY_LABEL_TAXON_DRIFT:{tip}")
        if role == "reference" and row["type_status"].strip() == "non_type" and " sp. " not in row["taxon_display"]:
            raise ValueError(f"PHYLO_DISPLAY_NONTYPE_LABEL:{tip}")
        if row["type_status"].strip() == "type" and "Type" not in row["label_concise"]:
            raise ValueError(f"PHYLO_DISPLAY_TYPE_MARKER:{tip}")
        for field in ("source_category", "geography"):
            palette_field = "source" if field == "source_category" else "geography"
            if (palette_field, row[field].strip()) not in palette:
                raise ValueError(f"PHYLO_DISPLAY_PALETTE_UNSUPPORTED:{tip}:{field}")
        states = (row["candida_state"].strip(), row["mrsa_state"].strip())
        if role == "query":
            if any(state not in ASSAY_SYMBOL for state in states):
                raise ValueError(f"PHYLO_DISPLAY_ASSAY_STATE:{tip}")
            if row["assay_provenance"].strip().casefold() in MISSING:
                raise ValueError(f"PHYLO_DISPLAY_ASSAY_PROVENANCE:{tip}")
            experiment, sample = row["experiment_id"].strip(), row["sample_id"].strip()
            if bool(experiment) != bool(sample):
                raise ValueError(f"PHYLO_DISPLAY_EXPERIMENT_BINDING:{tip}")
            if experiment and (experiment not in row["label_experiment"] or sample not in row["label_experiment"]):
                raise ValueError(f"PHYLO_DISPLAY_EXPERIMENT_LABEL:{tip}")
            if not experiment and row["label_experiment"] != row["label_concise"]:
                raise ValueError(f"PHYLO_DISPLAY_EXPERIMENT_UNBOUND:{tip}")
        elif any(states) or row["assay_provenance"].strip() or row["experiment_id"].strip() or row["sample_id"].strip():
            raise ValueError(f"PHYLO_DISPLAY_REFERENCE_ASSAY_NOT_BLANK:{tip}")
        elif row["label_experiment"] != row["label_concise"]:
            raise ValueError(f"PHYLO_DISPLAY_REFERENCE_EXPERIMENT_LABEL:{tip}")

    required_provenance = {(tip, field) for tip in tips for field in {"raw_source", "raw_geography"}}
    required_provenance |= {(row["tip"], field) for row in rows if row["role"].lower() == "query"
                            for field in {"candida_state", "mrsa_state"}}
    seen: set[tuple[str, str]] = set()
    by_tip = {row["tip"]: row for row in rows}
    for row in provenance_rows:
        if not {"tip", "field", "raw_value", "source", "evidence_sha256", "status"} <= set(row):
            raise ValueError("PHYLO_DISPLAY_PROVENANCE_SCHEMA")
        key = (row["tip"].strip(), row["field"].strip())
        if key in seen or key[0] not in set(tips) or key[1] not in PROVENANCE_FIELDS:
            raise ValueError("PHYLO_DISPLAY_PROVENANCE_IDENTITY")
        seen.add(key)
        if row["status"] not in {"bound", "not_recorded"} or not row["source"].strip():
            raise ValueError(f"PHYLO_DISPLAY_PROVENANCE_STATUS:{key[0]}:{key[1]}")
        sha = row["evidence_sha256"].strip()
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError(f"PHYLO_DISPLAY_PROVENANCE_HASH:{key[0]}:{key[1]}")
        if row["raw_value"] != by_tip[key[0]][key[1]]:
            raise ValueError(f"PHYLO_DISPLAY_PROVENANCE_VALUE:{key[0]}:{key[1]}")
    missing = required_provenance - seen
    if missing:
        tip, field = sorted(missing)[0]
        raise ValueError(f"PHYLO_DISPLAY_PROVENANCE_MISSING:{tip}:{field}")
    return {
        "status": "PHYLO_DISPLAY_CONTRACT_PASS",
        "tips": len(tips),
        "queries": sum(row["role"].lower() == "query" for row in rows),
        "all_tips_complete": True,
        "layout": layout,
        "assay_symbols": ASSAY_SYMBOL,
    }

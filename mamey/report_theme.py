"""Portable Sapote-Mamey report theme tokens.

Renderers may consume these tokens for Mode B cards and narrative reports.  The
theme changes presentation only; it does not alter evidence, scores, claims, or
authority state.
"""
from __future__ import annotations

from copy import deepcopy

THEME_NAME = "sapote-evidence-dossier"
TOKENS = {
    "colors": {
        "navy": "17375E", "teal": "007C83", "gold": "DCA73A",
        "cream": "F5F1E7", "pale_teal": "DDEFEF", "pale_red": "FBE9E7",
        "ink": "243648", "muted": "556575", "white": "FFFFFF",
    },
    "fonts": {"family": "Arial", "body_pt": 9.0, "title_pt": 26.0,
               "h1_pt": 15.5, "h2_pt": 11.7, "h3_pt": 10.5},
    "page": {"size": "LETTER", "margin_in": 1.0, "usable_width_dxa": 9360},
    "status_fills": {"PASS": "DDEFEF", "WARN": "FBE9E7", "HOLD": "F5F1E7",
                      "NOT_SCORED": "F5F1E7", "PRESENT": "DDEFEF", "ABSENT": "F5F1E7"},
}

THEME_VARIANTS = {
    "evidence_dossier": {
        "label": "Evidence Dossier",
        "best_for": "Mode B cards and technical reports",
        "colors": {"navy": "17375E", "teal": "007C83", "gold": "DCA73A", "cream": "F5F1E7", "pale_red": "FBE9E7"},
        "body_pt": 9.0, "density": "balanced",
    },
    "field_notebook": {
        "label": "Field Notebook",
        "best_for": "ecology synthesis and experiment planning",
        "colors": {"navy": "284B3B", "teal": "397D76", "gold": "C18A32", "cream": "F3F0E5", "pale_red": "F5E1D9"},
        "body_pt": 9.5, "density": "airy",
    },
    "dark_lab": {
        "label": "Dark Lab",
        "best_for": "screen presentations and dashboards",
        "colors": {"navy": "102A43", "teal": "2CB1BC", "gold": "F0B429", "cream": "E6EEF2", "pale_red": "F7C4C4"},
        "body_pt": 9.0, "density": "compact",
    },
    "minimal_clinical": {
        "label": "Minimal Clinical",
        "best_for": "handoffs, review packets, and printing",
        "colors": {"navy": "263238", "teal": "356B73", "gold": "9A6B16", "cream": "F7F7F5", "pale_red": "F1DEDA"},
        "body_pt": 9.5, "density": "quiet",
    },
}

SECTION_ROLES = {
    "identity": (1, 2, 3),
    "evidence": (4, 20, 29, 34, 45, 46),
    "interpretation": (5, 6, 7, 18, 19, 22, 33, 48),
    "safety": (8, 27, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 47),
}


def section_role(section_number: int) -> str:
    """Classify a Mode B section for presentation only."""
    try:
        n = int(section_number)
    except (TypeError, ValueError):
        return "safety"
    for role, numbers in SECTION_ROLES.items():
        if n in numbers:
            return role
    return "safety"


def section_accent(section_number: int) -> str:
    """Return the palette key for a section role."""
    return {"identity": "navy", "evidence": "teal", "interpretation": "gold", "safety": "muted"}[section_role(section_number)]


def status_badge(status: str) -> dict[str, str]:
    """Return renderer-neutral badge text/fill/foreground for a typed status."""
    normalized = str(status or "NOT_SCORED").upper()
    fill = status_fill(normalized)
    foreground = TOKENS["colors"]["ink"]
    return {"label": normalized, "fill": fill, "foreground": foreground}


def format_locus_identity(strain: str, node_or_contig: str, region: str, bgc_alias: str) -> str:
    """Format the mandatory identity order; reject incomplete identities."""
    values = [str(v).strip() for v in (strain, node_or_contig, region, bgc_alias)]
    if not all(values):
        raise ValueError("complete strain / node-or-contig / region / BGC alias identity is required")
    return " / ".join(values)


def status_fill(status: str) -> str:
    """Return a restrained fill for a typed status; unknown values stay neutral."""
    return TOKENS["status_fills"].get(str(status).upper(), TOKENS["colors"]["cream"])


def theme_variant(name: str = "evidence_dossier") -> dict[str, object]:
    """Return a copy of a named presentation preset; reject unknown names."""
    key = str(name).strip().lower().replace("-", "_")
    if key not in THEME_VARIANTS:
        raise ValueError(f"unknown Sapote-Mamey report theme variant: {name}")
    variant = THEME_VARIANTS[key]
    base = deepcopy(TOKENS)
    merged_tokens = {**base, "colors": {**base["colors"], **variant["colors"]},
                     "fonts": {**base["fonts"], "body_pt": variant["body_pt"]}}
    return {**deepcopy(variant), "name": key, "tokens": merged_tokens}

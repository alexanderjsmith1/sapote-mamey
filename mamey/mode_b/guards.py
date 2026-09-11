"""Mode B interpretation guards (v9.7.143a)."""
from __future__ import annotations

from typing import Any

LARGE_PROTEIN_TERMS: tuple[str, ...] = (
    "sdr",
    "oxidoreductase",
    "hydrolase",
    "dehydrogenase",
    "acyltransferase",
    "methyltransferase",
    "reductase",
)

DEFAULT_LARGE_PROTEIN_THRESHOLD_AA = 800

# PC-5 (v9.7.253 audit): core-synthase tokens whose mere presence means BLASTP family labels are
# insufficient and domain architecture is required. Named (parallel to LARGE_PROTEIN_TERMS) so both
# signal sets are equally auditable rather than one being an inline literal.
CORE_SYNTHASE_TERMS: tuple[str, ...] = (
    "pks",
    "nrps",
    "polyketide",
    "adenylation",
    "condensation",
)


def large_protein_misannotation_warning(row: dict[str, Any], threshold: int = DEFAULT_LARGE_PROTEIN_THRESHOLD_AA) -> str:
    """Return a warning when a huge protein has a small-enzyme-style label.

    Example: a 4,840 aa protein labelled "SDR family oxidoreductase" should be
    sent to HMMER/domain architecture rather than interpreted as a small SDR.
    """

    title = str(row.get("top_hit_title") or row.get("hit_title") or "").lower()
    try:
        aa = int(row.get("protein_length_aa") or row.get("aa_len") or row.get("query_length") or 0)
    except Exception:
        aa = 0
    if aa >= threshold and any(term in title for term in LARGE_PROTEIN_TERMS):
        return (
            "Large-protein override: do not interpret as standalone enzyme; "
            "domain architecture/HMMER required."
        )
    return ""


def requires_domain_architecture(row: dict[str, Any], threshold: int = DEFAULT_LARGE_PROTEIN_THRESHOLD_AA) -> bool:
    """True when BLASTP family labels are insufficient for Mode B interpretation."""

    try:
        aa = int(row.get("protein_length_aa") or row.get("aa_len") or row.get("query_length") or 0)
    except Exception:
        aa = 0
    title = str(row.get("top_hit_title") or row.get("hit_title") or "").lower()
    return aa >= threshold or any(term in title for term in CORE_SYNTHASE_TERMS)

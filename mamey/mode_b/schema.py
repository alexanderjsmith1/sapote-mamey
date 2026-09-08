"""Mode B canonical schema and validation helpers (v9.7.143a).

Mode B tables are used for biological interpretation of PKS/NRPS loci. Protein
length is not cosmetic metadata: it changes the interpretation of annotations such
as "SDR", "oxidoreductase", "hydrolase", or "acyltransferase". A 4,840 aa
SDR-labelled protein is a large modular/context protein, not a standalone SDR.

Pandas is imported lazily inside functions so importing mamey.mode_b does not add
a new hard runtime dependency beyond the existing package contract.
"""
from __future__ import annotations

MODEB_GENE_TABLE_REQUIRED: list[str] = [
    "node",
    "locus",
    "strand",
    "protein_length_aa",
    "top_hit_accession",
    "top_hit_title",
    "top_hit_species",
    "percent_identity",
    "percent_similarity",
    "query_coverage_pct",
    "gene_function_call",
    "modeb_role",
]

LENGTH_ALIASES: tuple[str, ...] = (
    "protein_length_aa",
    "aa_len",
    "query_length",
    "Protein size (aa)",
)

RENAME_ALIASES: dict[str, str] = {
    "hit_accession": "top_hit_accession",
    "hit_title": "top_hit_title",
    "hit_species": "top_hit_species",
    "functional_call": "gene_function_call",
    "gene_by_gene_call": "gene_function_call",
}


def normalize_modeb_gene_table(df):
    """Return a Mode B gene table with canonical field names.

    Accepts a pandas DataFrame and returns a DataFrame. Pandas is deliberately
    not imported at module import time.
    """

    out = df.copy()

    if "strand" not in out.columns:
        out["strand"] = "UNKNOWN_EXPLICIT"
    else:
        def _norm_strand(v):
            if v in (1, "+", "+1", "1", None):
                return "+" if v is not None else "UNKNOWN_EXPLICIT"
            if v in (-1, "-", "-1"):
                return "-"
            txt = str(v).strip()
            if txt in {"+", "1", "+1"}:
                return "+"
            if txt in {"-", "-1"}:
                return "-"
            return "UNKNOWN_EXPLICIT"
        out["strand"] = out["strand"].map(_norm_strand)

    found = [c for c in LENGTH_ALIASES if c in out.columns]
    if not found:
        raise ValueError("Mode B schema violation: no protein length column found")

    out["protein_length_aa"] = out[found[0]]
    for alias in found[1:]:
        out["protein_length_aa"] = out["protein_length_aa"].fillna(out[alias])

    for old, new in RENAME_ALIASES.items():
        if old in out.columns and new not in out.columns:
            out[new] = out[old]

    missing_len = (
        out["protein_length_aa"].isna()
        | (out["protein_length_aa"].astype(str).str.strip() == "")
    )
    if missing_len.any():
        id_cols = [c for c in ("node", "locus") if c in out.columns]
        missing = out.loc[missing_len, id_cols].to_dict("records") if id_cols else []
        raise ValueError(f"Mode B schema violation: missing protein_length_aa for {missing}")

    try:
        out["protein_length_aa"] = out["protein_length_aa"].astype(int)
    except Exception as exc:  # pragma: no cover - exact pandas error varies
        raise ValueError("Mode B schema violation: protein_length_aa is not integer-like") from exc

    if (out["protein_length_aa"] <= 0).any():
        raise ValueError("Mode B schema violation: nonpositive protein_length_aa")

    return out


def validate_modeb_gene_table(df) -> None:
    """Raise AssertionError when a table violates the Mode B evidence contract."""

    missing = [c for c in MODEB_GENE_TABLE_REQUIRED if c not in df.columns]
    if missing:
        raise AssertionError(f"Mode B table missing required columns: {missing}")

    bad_len = df["protein_length_aa"].isna() | (df["protein_length_aa"] <= 0)
    if bad_len.any():
        raise AssertionError("Mode B table has missing/nonpositive protein_length_aa")

    bad_strand = ~df["strand"].astype(str).isin(["+", "-", "UNKNOWN_EXPLICIT"])
    if bad_strand.any():
        raise AssertionError("Mode B table strand must use + / - / UNKNOWN_EXPLICIT; arrow-only strand notation is invalid")


def canonical_modeb_columns() -> list[str]:
    """Expose the required schema for docs/tests/exporters."""

    return list(MODEB_GENE_TABLE_REQUIRED)


# ---------------------------------------------------------------------------
# v9.7.372 publication-quality repair, Patch 4: the complete named-match
# channel-table contract for FINISHED_FULL48_CURRENT_EVIDENCE cards. Channels
# are NEVER merged: nr, ClusteredNR, and Swiss-Prot each carry their own full
# field set; ClusteredNR identity must never be presented as full-nr identity.
# `qcov NR` means not reported — never zero. A numeric percentage without its
# channel, accession, matched-protein name, and organism is incomplete.
#
# NOTE (v9.7.374 audit): the constants and canonical_matrix_columns() below
# document that contract but are NOT imported by the enforcing gate.
# mamey/modeb_structure_gate.py::_section4_complete_blastp_matrix_findings
# independently re-derives the same nr/ClusteredNR/Swiss-Prot channel split
# by substring-matching markdown table headers ("nr", "cluster", "swiss") —
# it does not reference MODEB_MATRIX_CHANNELS, MODEB_MATRIX_GENE_FIELDS,
# MODEB_MATRIX_CHANNEL_FIELDS, MODEB_MATRIX_MISSING_STATES,
# MODEB_MATRIX_PER_GENE_TAIL, or canonical_matrix_columns() at all (confirmed
# by grep: as of this note, this block's only callers anywhere in the tree
# are its own test, tests/test_publication_quality_repair_v9_7_372.py).
# Editing this contract (e.g. adding a channel to MODEB_MATRIX_CHANNELS)
# does NOT change gate behavior — the gate's header-matching logic must be
# updated separately and by hand. Treat this block as documentation of the
# intended contract, not as the gate's source of truth, until the two are
# actually wired together.

MODEB_MATRIX_GENE_FIELDS = [
    "membership",              # EXACT_REGION | BOUNDARY_CONTEXT_ONLY
    "node_or_contig_full",     # full assembly node/contig token
    "coordinates", "strand", "protein_length_aa",
    "antismash_function", "domains_hmms",
]

MODEB_MATRIX_CHANNEL_FIELDS = [
    "accession", "matched_protein_name_full", "organism",
    "pct_identity", "pct_positives", "query_coverage",
]

MODEB_MATRIX_CHANNELS = ["nr", "clusterednr", "swissprot"]     # required, kept separate
MODEB_MATRIX_OPTIONAL_CHANNELS = ["ebi_uniprot", "mibig"]      # additional when bound, never substitutes

MODEB_MATRIX_MISSING_STATES = [
    "NO_BOUND_HIT", "NOT_RUN", "RUNNING_NOT_YET_INGESTED", "INGEST_GAP",
    "PROVENANCE_HOLD", "NR",   # NR = not reported (e.g. qcov NR); never zero
]

MODEB_MATRIX_PER_GENE_TAIL = ["reconciliation", "claim_hold"]  # per-gene verdict + ceiling


def canonical_matrix_columns() -> list[str]:
    """The full finished-card gene x channel column set, channel-separated, for
    docs/tests/exporters. One gene per row; each channel contributes its own
    named-match field group; missing values use MODEB_MATRIX_MISSING_STATES."""
    cols = list(MODEB_MATRIX_GENE_FIELDS)
    for ch in MODEB_MATRIX_CHANNELS:
        cols += [f"{ch}_{f}" for f in MODEB_MATRIX_CHANNEL_FIELDS]
    cols += MODEB_MATRIX_PER_GENE_TAIL
    return cols

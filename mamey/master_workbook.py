"""Mamey master workbook writer.

The master workbook is the persistent cross-strain analysis substrate.
Every completed strain adds one row to each canonical schema-v1.1 sheet below
(cross-strain, one row per strain, or one row per BGC for B-series sheets).

The workbook is created fresh if it doesn't exist; otherwise it is updated
in-place and a dated immutable snapshot copy is written alongside it.

Sheet architecture (AUDIT_371 CORRECTED 2026-08-19 -- this docstring
previously described a legacy descriptive-name sheet scheme -- Dashboard,
Strain_Registry, BGC_Master, [code]_Summary/_Triage/etc -- that the live entry
point update_master_workbook() does NOT produce; that scheme's builder
functions (_write_per_strain_sheets, _update_class_matrix,
_update_known_cluster_matrix) still exist in this file but have zero callers
outside their own definitions -- confirmed dead code, not what a --master run
actually writes. See CANONICAL_V1_HEADERS below for the authoritative,
machine-checkable header list; this is a human-readable summary of it):

  A2_Strain_Registry    — one row per strain: assembly stats, taxonomy, top AB/AF leads
  A3_Run_Manifest       — one row per run: date, version, mode, package path
  A4_Completeness_Audit — pass/fail gate summary per strain
  B1_BGC_Master         — one row per BGC across all strains: full extraction fields
  B2_Product_Class_Matrix — strain x product-class count pivot
  B3_Known_Cluster_Matrix — strain x KCB top-hit reference presence
  B4_Cross_Strain_Scans — strain x source-derived-scan summary counts
  B5_BLASTp_Hits        — per-gene BLASTp hit rows (governed post-seal overlay)
  B6_Compound_Reference — per-BGC resolved compound/NPClassifier reference data
  C1_DAPR_Antibacterial / C2_DAPR_Antifungal — ranked AB/AF leads per strain
  C3_Lead_Tier_Summary / C4_Strain_Decision_Table — cross-strain lead rollups
  D1_RGGMCI_All_Strains — RG-GMCI review state per strain
  D2_RGGMCI_Top_Pairs / D3_RGGMCI_Promoted — top-N pairs / promoted split-pathway groups
  E1_Mode_B_Index .. E4_A_Domain_Summary — Sapote judgment-layer index/handoff sheets
  F1_Ecology_Readiness  — habitat readiness per strain
  G1_Literature_Index / G2_Validation_Roles — citation and validation-role tracking
  H1_Handoff_Log / H2_Gap_Queue — cross-platform handoff and open-gap tracking
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

from mamey import __version__

import contextlib as _contextlib
import json
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from .models import MameyRun, BGCRecord
from .xlsx_determinism import atomic_save_workbook_safely
from .crosswalk import assembly_locator
from .assembly import corrected_bgc_count, assembly_tier

# caps for the RG-GMCI master sheets — a review shortlist per strain, not the full pair dump
RGGMCI_D2_TOP_N = 25
RGGMCI_D3_TOP_N = 12


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

HDR_FILL_BLUE   = PatternFill("solid", fgColor="1F4E79")   # dark blue — persistent sheets
HDR_FILL_GREEN  = PatternFill("solid", fgColor="375623")   # dark green — per-strain sheets
HDR_FILL_ORANGE = PatternFill("solid", fgColor="833C00")   # dark orange — dashboard
HDR_FONT        = Font(color="FFFFFF", bold=True)
COL_WIDTH       = 22


def _style_header(ws, fill: PatternFill) -> None:
    for cell in ws[1]:
        cell.fill = fill
        cell.font = HDR_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for col in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col)].width = COL_WIDTH




def _is_effectively_empty(ws) -> bool:
    """True for a newly created openpyxl sheet with no real header/data."""
    return (ws.max_row == 1 and ws.max_column == 1 and ws.cell(1, 1).value is None)


def _write_header(ws, headers: list[str], fill: PatternFill) -> None:
    """Write headers explicitly to row 1.

    Do not use ws.append() on a sheet after probing ws.cell(1, 1):
    openpyxl may advance the internal current-row pointer and append headers
    to row 2, leaving row 1 blank. Downstream col_map readers then fail to
    find required headers such as 'Strain'.
    """
    for i, header in enumerate(headers, 1):
        ws.cell(1, i).value = header
    _style_header(ws, fill)


def _repair_leading_blank_header(ws, expected_first: str = "Strain") -> None:
    """Repair workbooks made by the v1.9.2 header bug.

    If row 1 is blank and row 2 starts with the expected header, delete the
    blank leading row so normal row-1 header maps work again.
    """
    if ws.max_row >= 2 and ws.cell(1, 1).value is None and ws.cell(2, 1).value == expected_first:
        ws.delete_rows(1, 1)


def _ensure(wb: Workbook, name: str) -> Any:
    """Return sheet, creating it if absent."""
    if name not in wb.sheetnames:
        return wb.create_sheet(name)
    return wb[name]


def _col_map(ws) -> dict[str, int]:
    """Return {header_text: column_index} for row 1."""
    return {
        str(ws.cell(1, c).value): c
        for c in range(1, ws.max_column + 1)
        if ws.cell(1, c).value is not None
    }


def _set(ws, row: int, col_map: dict[str, int], key: str, value: Any) -> None:
    if key in col_map:
        ws.cell(row, col_map[key]).value = value


# ---------------------------------------------------------------------------
# Strain short code for sheet names
# ---------------------------------------------------------------------------

def _sheet_code(strain_id: str) -> str:
    """Derive a sheet prefix from strain_id, capped so that code + the longest suffix stays
    within Excel's 31-char sheet-name limit. Longest suffix is "_Lead_Propagation" (17 chars),
    so the code is capped at 31 - 17 = 14. openpyxl does NOT raise on an over-31 name — it warns
    and writes a sheet Excel can't open, and two long codes could silently collide/overwrite.
    """
    # e.g. Actinomadura_rubrisoli_H3C3 → H3C3
    # e.g. AS-XXX is the public placeholder for a real AS-#### strain id
    _MAX_SUFFIX = len("_Lead_Propagation")  # 17 — the longest "{code}{suffix}" sheet name
    _CODE_CAP = 31 - _MAX_SUFFIX             # 14
    parts = strain_id.replace("-", "_").split("_")
    code = parts[-1]
    if len(code) > _CODE_CAP:
        code = code[:_CODE_CAP]
    return code


# ---------------------------------------------------------------------------
# Persistent cross-strain sheets — header definitions
# ---------------------------------------------------------------------------

# Legacy descriptive SHEET_HEADERS removed from the runner entry point in schema v1.1.
SHEET_HEADERS: dict[str, list[str]] = {}


def _ensure_headers(wb: Workbook, name: str, headers: list[str],
                    fill: PatternFill = HDR_FILL_BLUE) -> Any:
    ws = _ensure(wb, name)
    if _is_effectively_empty(ws):
        _write_header(ws, headers, fill)
    elif ws.cell(1, 1).value is None:
        _repair_leading_blank_header(ws, expected_first=headers[0])
        if ws.cell(1, 1).value is None:
            _write_header(ws, headers, fill)
    return ws


# ---------------------------------------------------------------------------
# Canonical schema-v1.1 workbook views (Gate 3 public-release contract)
# ---------------------------------------------------------------------------

CANONICAL_V1_HEADERS: dict[str, list[str]] = {
    "A2_Strain_Registry": [
        "strain", "taxonomy", "ecology_source", "habitat", "assembly_bp",
        "contigs", "n50", "gc_pct", "bgc_count", "interior_pct",
        "assembly_tier", "workflow_version", "package_status",
        "top_ab_bgc", "top_ab_class", "ab_score", "ab_band",
        "top_af_bgc", "top_af_class", "af_score", "af_band",
        "rggmci_state", "gap_next_action", "scope"
    ],
    "A3_Run_Manifest": ["run_date", "strain", "version", "mode", "antismash_profile", "input_zip", "raw_bgcs", "corrected_bgcs", "issues", "package_path"],
    "A4_Completeness_Audit": ["strain", "A2_registry", "B1_bgc_master", "B4_scans", "C1_dapr_ab", "C2_dapr_af", "D1_rggmci", "E1_mode_b", "F1_ecology", "overall", "gap_action"],
    "B1_BGC_Master": ["strain", "assembly_locator", "contig", "region", "BGC_ID", "start", "end", "length_kb", "products", "boundary", "arch", "kcb_top", "kcb_score", "kcb_evidence_state", "kcb_proteins", "cctt_triggers", "resistance_tier", "tta_tier", "ab_auto", "af_auto", "novelty_auto", "lead_tier_auto", "depth_floor", "closest_product_provenance", "source_kcb_file", "source_kcb_locator", "kcb_hit_rank", "denominator_type", "parse_confidence", "needs_manual_kcb_check", "product_claim_ceiling", "efls_status", "flank_census_tier1", "flank_census_tier2_todo", "cross_contig_candidate_set", "efls_claim_ceiling", "dkp_rank", "dkp_cdps_evidence", "dkp_oxidase_homology", "dkp_provenance", "dkp_claim_ceiling", "diagnostic_signal_score", "evidence_weight_tier", "claim_confidence", "claim_ceiling", "safe_claim", "engine_version"],
    # B2 columns v1.1 (.401, Alex-ruled 2026-09-02): +14 cohort-attested classes promoted from the
    # full-cohort 'other' remeasure (43 strains / 2,438 BGCs, n>=10 threshold — decision memo in
    # September 2 2026 Claude/COHORT_MASTER_v9.7.400_2026-09-02/). Backward-compatible: readers/
    # renderers take columns from the sheet, so pre-.401 workbooks keep folding these into 'other'.
    "B2_Product_Class_Matrix": ["strain", "label_provenance"] + ["NRPS", "NRPS-like", "PKS", "PKS-like", "T1PKS", "T2PKS", "T3PKS", "transAT-PKS", "RiPP", "terpene", "carotenoid", "saccharide", "halogenated", "lassopeptide", "azole-containing-RiPP", "lanthipeptide-class-i", "lanthipeptide-class-ii", "lanthipeptide-class-iii", "NRP-metallophore", "NI-siderophore", "betalactone", "fatty_acid", "hglE-KS", "NAPAA", "RiPP-like", "terpene-precursor", "quinone_isoprenoid_chain", "ectoine", "butyrolactone", "arylpolyene", "RRE-containing", "redox-cofactor", "ranthipeptide", "oligosaccharide", "hydrogen-cyanide", "aminopolycarboxylic-acid", "HR-T2PKS", "phosphonate", "other"] + ["counts_reliability"],
    "B3_Known_Cluster_Matrix": ["strain", "(columns: one per KCB top-hit reference)"],
    "B4_Cross_Strain_Scans": ["strain", "run_mode", "KCB_status", "RGGMCI_pairs", "RGGMCI_HIGH", "CCTT_triggers", "CCTT_HAL", "CCTT_LAN", "CCTT_LASSO", "CCTT_THA", "CCTT_PHO", "CCTT_ENE", "CGAD_chitin", "TFBS_DasR", "TFBS_total", "bldA_T4", "resistance_T1", "UMED_gaps", "EFLS_pairs"],
    # B5 (v1.2): external NCBI BLASTp top-N hits, one row per (strain, BGC, query gene, hit_rank).
    # Numeric fields are OBSERVED from the -outfmt-10 HitTable CSV; subject_desc/sciname/node/contig
    # are enriched from the companion Alignment XML when supplied (blank otherwise). Similarity =
    # positives_pct (KCB=similarity rule applies here too: a BLASTp hit is a similarity signal,
    # never a product-identity claim). Joins B1_BGC_Master on (strain, BGC_ID).
    "B5_BLASTp_Hits": ["strain", "BGC_ID", "contig", "query_locus", "query_len", "hit_rank", "subject_acc", "subject_desc", "sciname", "pct_identity", "positives_pct", "align_len", "mismatches", "gap_opens", "q_start", "q_end", "s_start", "s_end", "evalue", "bitscore", "subject_len", "source", "ingest_date"],
    # v9.7.186 NP Atlas: enriches each BGC's KCB-named compound with molecule-level chemistry
    # (npclassifier class, formula, exact mass, [M+H]/[M+Na], InChIKey, primary DOI/PMID). INVENTORY_ONLY.
    # NOT a BGC product-identity claim and carries NO genus-provenance field (see npatlas_resolver.py).
    "B6_Compound_Reference": ["strain", "BGC_ID", "kcb_named_compound", "kcb_score", "resolved", "npclassifier_pathway", "npclassifier_class", "mol_formula", "exact_mass", "m_plus_h", "m_plus_na", "inchikey", "npaid", "primary_doi", "primary_pmid", "primary_year", "evidence_tier", "claim_ceiling"],
    "C1_DAPR_Antibacterial": ["strain", "rank", "assembly_locator", "contig", "BGC_ID", "products", "score", "lead_tier", "band", "standing_rule", "corrected_rank", "kcb_top", "kcb_score", "boundary", "arch", "cctt", "status_note"],
    "C2_DAPR_Antifungal": ["strain", "rank", "assembly_locator", "contig", "BGC_ID", "products", "score", "lead_tier", "band", "standing_rule", "corrected_rank", "kcb_top", "kcb_score", "boundary", "arch", "cctt", "status_note"],
    "C3_Lead_Tier_Summary": ["strain", "top_ab_bgc", "top_ab_products", "ab_score", "ab_band", "top_af_bgc", "top_af_products", "af_score", "af_band", "sapote_composite", "recommended_role"],
    "C4_Strain_Decision_Table": ["sapote_rank", "strain", "sapote_score", "bgc_count", "assembly_tier", "top_lead", "top_kcb_score", "rggmci_high", "class_diversity", "high_value_hits", "rare_class_hits", "recommended_role"],
    "D1_RGGMCI_All_Strains": ["strain", "contigs", "review_required", "final_state", "promoted_grades", "fragment_sets", "promoted_bgcs", "interpretation"],
    "D2_RGGMCI_Top_Pairs": ["strain", "rank", "bgc_a", "bgc_b", "rggmci_score", "confidence", "products_a", "products_b", "shared_references", "interpretation"],
    "D3_RGGMCI_Promoted": ["group_id", "strain", "grade", "fragments", "evidence_basis", "claim_ceiling", "chemistry_consequence", "status"],
    "E1_Mode_B_Index": ["strain", "BGC_ID", "length_kb", "products", "subprograms", "mode_b_status", "analysis_platform", "date", "report_file", "layperson_summary", "fermentation_note"],
    "E2_Comparative_Pairs": ["pair_id", "strain_a", "bgc_a", "strain_b", "bgc_b", "length_a_kb", "length_b_kb", "products", "subprogram_match", "mean_pct_id_core", "mean_pct_id_all", "a_domain_match", "diverged_genes", "interpretation"],
    "E3_Megacluster_Registry": ["strain", "BGC_ID", "length_kb", "boundary", "products", "kcb_top", "kcb_score", "long_read_status", "notes"],
    "E4_A_Domain_Summary": ["strain", "BGC_ID", "module_position", "gene_locus_tag", "stachelhaus_code", "predicted_substrate", "method", "confidence", "notes"],
    "F1_Ecology_Readiness": ["strain", "taxonomy", "source", "habitat", "assembly_tier", "bgc_count", "ab_lead", "af_lead", "tfbs_hits", "cctt_classes", "readiness", "route"],
    "G1_Literature_Index": ["strain", "BGC_ID", "track", "citation", "doi", "evidence_purpose", "verification_status"],
    "G2_Validation_Roles": ["strain", "primary_role", "manuscript_use"],
    "H1_Handoff_Log": ["date", "platform", "direction", "strains_affected", "sheets_modified", "file_sha256", "validation_result", "notes"],
    "H2_Gap_Queue": ["priority", "gap_class", "strains", "required_input", "next_action", "assigned_platform", "status"],
    "H3_Schema_Version": ["Schema version", "v1.1"],
}

def _ensure_canonical_headers(wb: Workbook) -> None:
    if "A1_Dashboard" not in wb.sheetnames:
        ws = wb.create_sheet("A1_Dashboard", 0)
        ws["A1"] = "Sapote–Mamey Master Workbook"
        ws["A3"] = "Strains in registry"
        ws["A4"] = "Total BGC records"
        ws["A5"] = "Last updated"
        ws["A6"] = "Mamey version"
    for name, headers in CANONICAL_V1_HEADERS.items():
        _ensure_headers(wb, name, headers)

def _append_row_by_header(ws, values: dict[str, Any]) -> None:
    cm = _col_map(ws)
    # AUDIT_371 (schema-drift fix): a key present in `values` but not yet in the sheet's
    # existing header (e.g. a column added to CANONICAL_V1_HEADERS in a later engine version --
    # such as B1's engine_version, PROV-01 v9.7.336 -- merged into a master workbook created
    # before that column existed) used to be silently dropped by _set()'s `if key in col_map`
    # guard. That defeated the exact protection such a column exists to provide, for any master
    # older than the column. Extend the header for any new key here, mirroring the dynamic-
    # column-extension pattern already proven in _update_known_cluster_matrix (KCB family
    # columns). Historical rows above this one are correctly left blank for the new column --
    # this does not retroactively guess a value for prior strains, only ensures the field is
    # captured going forward, consistent with this codebase's fail-safe-not-fabricate posture.
    _next_col = ws.max_column + 1
    for key in values:
        if key not in cm:
            ws.cell(1, _next_col).value = key
            ws.cell(1, _next_col).fill = HDR_FILL_BLUE
            ws.cell(1, _next_col).font = HDR_FONT
            cm[key] = _next_col
            _next_col += 1
    row = ws.max_row + 1
    for key, value in values.items():
        _set(ws, row, cm, key, value)

def _b2_product_class_counts(products) -> dict[str, int]:
    """MW-01 (v9.7.338): count products into the canonical B2 columns, folding every
    non-canonical product into the ``other`` catch-all.

    The frozen B2 header names only the canonical classes; antiSMASH emits many more
    (RiPP-like, terpene-precursor, ectoine, arylpolyene, ...). The prior builder read each
    header column out of a Counter, so any product not named in the header was silently
    DROPPED — not even folded into ``other`` — and the matrix undercounted the strain's real
    product total. Bucketing non-canonical products into ``other`` restores the invariant:
    the row's product-class columns sum to the strain's total product count.

    BC2_399 fix: the canonical-membership check (`cls in canon`) was case-sensitive, but the
    frozen B2 header names several classes in uppercase ("NRPS", "T1PKS", "T2PKS", "T3PKS",
    "NRPS-like", "NRP-metallophore", "NI-siderophore") while the real antiSMASH product tokens
    on `bgc.products` (the caller's actual input, confirmed against
    mamey/class_architecture.py::_REAL_CLASSES) are lowercase. Every one of those classes was
    silently folded into `other` for every real strain ever accumulated into this persistent
    master workbook -- the same shape already fixed independently in mamey/cnbu.py (v9.7.371)
    and this round's mamey/cohort_figures.py / tools/reclass_check.py cards. Matching is now
    case-insensitive; the emitted row still uses the frozen canonical column names unchanged.

    ``counts_reliability`` is initialised to 0 here and overwritten by the caller with the
    assembly-tier reliability flag; it is never a product bucket.
    """
    cols = CANONICAL_V1_HEADERS["B2_Product_Class_Matrix"][1:]
    canon = set(cols) - {"other", "counts_reliability", "label_provenance"}
    canon_ci = {c.lower(): c for c in canon}
    row = {c: 0 for c in cols}
    for cls, n in Counter(products).items():
        key = canon_ci.get(str(cls).lower(), "other")
        row[key] += n
    return row


_CAROTENOID_LABEL_PROVENANCE = frozenset({"RAW_ANTISMASH", "GENE_BACKED"})
_CAROTENOID_GENE_MARKER = re.compile(
    r"(?:phytoene[ _-]?synthase|lycopene[ _-]?cyclase|\bcrt[by]\b|sqs_psy|lycopene_cycl)",
    re.I,
)


def _gene_backed_carotenoid_bgcs(run: "MameyRun") -> set[str]:
    """Return BGC IDs with a carotenoid core-gene marker already in source scans.

    This is a label-view selector, not a reclassification engine. It consumes the
    exact per-BGC domain observations and CDS products already produced by source
    scans. It never consults the historical correction ledger and never treats
    generic pigment/hopanoid evidence as carotenoid backing.
    """
    scans = getattr(run, "source_scans", None)
    if scans is None:
        return set()
    backed: set[str] = set()
    per_bgc = (getattr(scans, "domain_architecture", {}) or {}).get("per_bgc", {}) or {}
    for bgc_id, rec in per_bgc.items():
        domains = rec.get("domains", []) if isinstance(rec, dict) else []
        if any(_CAROTENOID_GENE_MARKER.search(str(d.get("domain", "")))
               for d in domains if isinstance(d, dict)):
            backed.add(str(bgc_id))

    pm = getattr(scans, "primary_metabolism", {}) or {}
    hits = (pm.get("hits", {}) or {}).get("pigment", []) if isinstance(pm, dict) else []
    for hit in hits:
        if not isinstance(hit, dict) or not _CAROTENOID_GENE_MARKER.search(str(hit.get("product", ""))):
            continue
        try:
            h_start, h_end = int(hit.get("start")), int(hit.get("end"))
        except (TypeError, ValueError):
            continue
        h_contig = str(hit.get("contig", ""))
        for bgc in run.bgcs:
            if h_contig == str(bgc.contig) and not (h_end < bgc.start or h_start > bgc.end):
                backed.add(str(bgc.bgc_id))
    return backed


def _b2_product_class_rows(run: "MameyRun", counts_reliability: str) -> list[dict[str, Any]]:
    """Build independently selectable raw and gene-backed B2 label views."""
    products = [c for bgc in run.bgcs for c in bgc.products]
    raw = {"strain": run.context.strain_id}
    raw.update(_b2_product_class_counts(products))
    raw["label_provenance"] = "RAW_ANTISMASH"
    raw["counts_reliability"] = counts_reliability

    gene = dict(raw)
    gene["label_provenance"] = "GENE_BACKED"
    gene["carotenoid"] = len(_gene_backed_carotenoid_bgcs(run))
    return [raw, gene]


def _completeness_verdicts(run: "MameyRun", triage: list) -> dict:
    """v9.7.376 (ACT-02): derive the A4_Completeness_Audit verdicts from the run's REAL
    extraction state instead of hardcoding PASS. A verdict is only PASS when the stage's
    data is actually present; stages whose data was never loaded report NOT_LOADED /
    NOT_COMPUTED / UNKNOWN (never PASS). overall is PASS_EXTRACTION only when every
    extraction-core stage passed; otherwise INCOMPLETE_EXTRACTION. E1_mode_b stays
    JUDGMENT_PENDING (judgment is deferred by design)."""
    ss = run.source_scans
    a2 = "PASS" if getattr(run.context, "strain_id", "") else "FAIL"
    b1 = "PASS" if run.bgcs else "NO_BGCS"
    b4 = "PASS" if ss is not None else "NOT_LOADED"
    c1 = "PASS" if triage else "NOT_LOADED"
    c2 = "PASS" if triage else "NOT_LOADED"
    d1 = "PASS" if (ss is not None and getattr(ss, "rggmci", None) is not None) else "NOT_COMPUTED"
    src = getattr(run.context, "source", "") or ""
    f1 = "PASS" if src and src != "not supplied" else "UNKNOWN"
    core_ok = (a2 == "PASS" and b4 == "PASS" and c1 == "PASS" and c2 == "PASS"
               and d1 == "PASS" and b1 in ("PASS", "NO_BGCS"))
    overall = "PASS_EXTRACTION" if core_ok else "INCOMPLETE_EXTRACTION"
    return {"A2_registry": a2, "B1_bgc_master": b1, "B4_scans": b4, "C1_dapr_ab": c1,
            "C2_dapr_af": c2, "D1_rggmci": d1, "E1_mode_b": "JUDGMENT_PENDING",
            "F1_ecology": f1, "overall": overall}


def _write_canonical_v1_views(wb: Workbook, run: MameyRun, triage: list[Any], counts: dict[str, Any]) -> None:
    """Write schema-v1.0 public-release sheets alongside legacy user-facing sheets.

    The legacy sheets are retained for backwards compatibility with earlier SID-XXX
    workbooks. These coded sheets are the Gate-3/Gate-5 merge contract.
    """
    _ensure_canonical_headers(wb)
    strain_id = run.context.strain_id
    ss = run.source_scans
    cctt_coupling = ss.cctt.get("bgc_coupling", {}) if ss else {}
    rt_per_bgc = ss.resistance_tiers.get("per_bgc", {}) if ss else {}
    tta_per_bgc = ss.blda_tta.get("per_bgc", {}) if ss else {}
    triage_by = {t.bgc_id: t for t in triage}
    from .compat_v941 import compatibility_fields_for_bgc
    # v9.7.8: the headline lead (feeds C3/C4/F1) must be the top *actionable* lead — exclude standing-rule
    # downgrades and primary-metabolism/pigment flags (corrected_rank is None for both). Fall back to the
    # full set only if every BGC is downgraded.
    _leads = [t for t in triage if t.corrected_rank is not None] or triage
    top_ab = max(_leads, key=lambda t: t.ab_score, default=None) if _leads else None
    top_af = max(_leads, key=lambda t: t.af_score, default=None) if _leads else None
    today = date.today().isoformat()
    habitat = _infer_habitat(run.context.source)
    package_status = "MAMEY_COMPLETE" if run.context.analysis_mode == "gold" else "PASS"

    _append_row_by_header(wb["A2_Strain_Registry"], {
        "strain": strain_id, "taxonomy": run.context.taxonomy, "ecology_source": run.context.source,
        "habitat": habitat, "assembly_bp": run.assembly.genome_bp, "contigs": run.assembly.contigs,
        "n50": run.assembly.n50, "gc_pct": run.assembly.gc_pct, "bgc_count": counts["raw"],
        "interior_pct": counts["interior_pct"], "assembly_tier": counts["assembly_tier"],
        "workflow_version": f"Mamey v{run.context.version}", "package_status": package_status,
        "top_ab_bgc": top_ab.bgc_id if top_ab else "", "top_ab_class": "", "ab_score": top_ab.ab_score if top_ab else "",
        "ab_band": top_ab.lead_tier if top_ab else "", "top_af_bgc": top_af.bgc_id if top_af else "",
        "top_af_class": "", "af_score": top_af.af_score if top_af else "", "af_band": top_af.lead_tier if top_af else "",
        "rggmci_state": "REVIEW_TRIGGERED_NO_PROMOTION", "gap_next_action": "; ".join(run.issues) if run.issues else "Load manifest into judgment session",
        # v9.7.185 P3: stamp scope so the non-actinomycete guard actually gates the cross-strain comparison.
        "scope": _scope_from_taxonomy(run.context.taxonomy),
    })
    _append_row_by_header(wb["A3_Run_Manifest"], {
        "run_date": today, "strain": strain_id, "version": f"Mamey v{run.context.version}",
        "mode": run.context.analysis_mode, "antismash_profile": getattr(run.context, "antismash_profile", "unknown"),
        "input_zip": run.context.input_zip, "raw_bgcs": counts["raw"],
        "corrected_bgcs": counts["corrected"], "issues": "; ".join(run.issues), "package_path": run.context.outdir,
    })
    _v = _completeness_verdicts(run, triage)
    _append_row_by_header(wb["A4_Completeness_Audit"], {
        "strain": strain_id, **_v,
        "gap_action": "; ".join(run.issues) if run.issues else (
            "Load manifest for Sapote judgment" if _v["overall"] == "PASS_EXTRACTION"
            else "Extraction incomplete — see NOT_LOADED/NOT_COMPUTED verdicts before judgment"),
    })
    for bgc in run.bgcs:
        t = triage_by.get(bgc.bgc_id)
        compat = compatibility_fields_for_bgc(bgc, t, ss)
        row_values = {
            "strain": strain_id, "assembly_locator": assembly_locator(bgc), "BGC_ID": bgc.bgc_id, "contig": bgc.node_id or bgc.contig, "region": bgc.antismash_region,
            "start": bgc.start, "end": bgc.end, "length_kb": bgc.length_kb, "products": "; ".join(bgc.products),
            "boundary": bgc.edge_status, "arch": bgc.architecture_confidence, "kcb_top": bgc.kcb_top or "",
            "kcb_score": bgc.kcb_cumulative,
            "kcb_evidence_state": getattr(bgc, "kcb_evidence_state", "UNKNOWN_KCB"),
            "kcb_proteins": bgc.kcb_protein_hits,
            "cctt_triggers": (getattr(bgc, "cctt_triggers", "") or ", ".join(cctt_coupling.get(bgc.bgc_id, []))),
            "resistance_tier": rt_per_bgc.get(bgc.bgc_id, {}).get("tier", ""),
            "tta_tier": tta_per_bgc.get(bgc.bgc_id, {}).get("bldA_tier", ""),
            "ab_auto": t.ab_score if t else "", "af_auto": t.af_score if t else "",
            "novelty_auto": t.novelty_score if t else "", "lead_tier_auto": t.lead_tier if t else "",
            "depth_floor": "full_mode_b" if run.context.analysis_mode == "gold" else "abbreviated_ledger",
            "closest_product_provenance": getattr(bgc, "closest_product_provenance", "UNRESOLVED"),
            "source_kcb_file": getattr(bgc, "source_kcb_file", "UNRESOLVED"),
            "source_kcb_locator": getattr(bgc, "source_kcb_locator", "UNRESOLVED"),
            "kcb_hit_rank": getattr(bgc, "kcb_hit_rank", "UNRESOLVED"),
            "denominator_type": getattr(bgc, "denominator_type", "UNRESOLVED"),
            "parse_confidence": getattr(bgc, "parse_confidence", "LOW"),
            "needs_manual_kcb_check": getattr(bgc, "needs_manual_kcb_check", "yes"),
            "product_claim_ceiling": getattr(bgc, "product_claim_ceiling", "unresolved; do not use product name"),
            # PROV-01 (v9.7.336): stamp the ENGINE that produced this row. A2/A3 already carry a
            # strain-level workflow_version, but every cross-strain figure and comparison joins on
            # B1_BGC_Master, which had no engine field — so a master accumulating strains across an
            # engine bump was silently mixed. That matters concretely: engine 1.9.114 changed
            # parsers.extract_domain_features (region de-dup), which feeds architecture_first, so
            # Arch_Capacity / Class_Conf / Lead_tier_auto are NOT comparable across that boundary.
            # Per-row, because a master is appended to one strain at a time.
            "engine_version": getattr(run.context, "version", "") or "",
        }
        row_values.update(compat)
        _append_row_by_header(wb["B1_BGC_Master"], row_values)
    # v9.7.367 CANDIDATE (Indigo2 §2 surface 2, the review lane wire-both ruling 2026-08-15): the
    # BeeCohort incident surface. A merged B1 row is appended with empty ab/af/novelty when its
    # triage record is missing ("t is None" above), and nothing downstream knows how many rows
    # should have arrived — so the deficit is invisible in a way a per-strain build's is not.
    # Reuse the canonical guard (same semantics as the per-strain surface), warn-only, on the
    # SAME triage list B1 wrote from. B1_BGC_Master only; DAPR C1/C2 are ranked-lead subsets
    # BY DESIGN and are exempt. Verdict goes to the degradation collector (receipt channel,
    # outside DETERMINISM_WHITELIST; cli drains it after the master update). Never raises.
    # v9.7.370 swallow triage: this guard PROTECTS the degradation-record call itself —
    # converting it to degradation.record() would be circular. Deliberate, named suppression.
    with _contextlib.suppress(Exception):
        from .scoring import assert_full_scoring_coverage
        _b1_cov = assert_full_scoring_coverage(run.bgcs, triage, strain=strain_id,
                                               raise_on_fail=False)
        if _b1_cov:
            from . import degradation as _degradation
            _degradation.record("master_workbook.B1_BGC_Master.coverage", _b1_cov,
                                strain=strain_id)
            emit(f"  WARNING (merge surface): {_b1_cov}")

    # v9.7.186 NP Atlas: for each BGC whose KCB hit names a compound, resolve it to NP Atlas
    # molecule-level chemistry + primary reference, written to its OWN sheet (B1 untouched above).
    # This enriches the KCB similarity reference; it makes no product-identity or genus claim.
    try:
        from .npatlas_resolver import compound_reference_row
        for _b in run.bgcs:
            _r = compound_reference_row(strain_id, _b.bgc_id, getattr(_b, "kcb_top", "") or "",
                                        getattr(_b, "kcb_cumulative", ""))
            if _r:
                _append_row_by_header(wb["B6_Compound_Reference"], _r)
    except Exception:
        ...  # reviewed-intentional empty handler: NP Atlas enrichment is optional; never block the workbook build
    # Distinct product-class diversity (C4_Strain_Decision_Table below reads this). The MW-01
    # B2 refactor above folds non-canonical products into `other`; class_diversity keeps its
    # original meaning = number of distinct antiSMASH product classes present.
    class_counts = Counter(c for bgc in run.bgcs for c in bgc.products)
    # PC-A3 (v9.7.101): B2 lists raw per-class counts, which are fragmentation-inflated for poor
    # assemblies and sit next to GOOD-assembly counts with no caveat. Flag reliability off the
    # assembly tier so a cross-strain consumer can filter: GOOD->OK, MODERATE->OK_WITH_NOTE,
    # POOR/VERY_POOR->LOW (raw counts inflated; use the corrected count for comparison).
    _tier = counts.get("assembly_tier", "")
    _counts_reliability = {
        "COMPLETE": "OK", "GOOD": "OK", "MODERATE": "OK_WITH_NOTE",
        "POOR": "LOW", "VERY_POOR": "LOW",
    }.get(_tier, "UNKNOWN")
    for row in _b2_product_class_rows(run, _counts_reliability):
        _append_row_by_header(wb["B2_Product_Class_Matrix"], row)
    # P-E (v9.7.84): build the B3 KCB pivot instead of writing a bare stub row. For this strain,
    # count BGCs per distinct top-KCB reference and write them as columns (one per reference).
    # NOTE: _set() silently ignores keys not already in the header, so dynamic reference columns
    # must be added to row 1 explicitly first. The reference label is each BGC's kcb_top (similarity
    # anchor, not identity). Columns accrete across the cohort; absent references leave honest blanks.
    from collections import Counter as _Counter
    _b3_ws = wb["B3_Known_Cluster_Matrix"]
    # Clean the stub header hint if present (a non-column placeholder from the frozen schema).
    _stub_col = None
    for _c in range(1, _b3_ws.max_column + 1):
        if str(_b3_ws.cell(1, _c).value or "").startswith("(columns:"):
            _stub_col = _c
    if _stub_col:
        _b3_ws.cell(1, _stub_col).value = None
    _kcb_refs = _Counter()
    for _b in run.bgcs:
        _ref = (getattr(_b, "kcb_top", "") or "").strip()
        if not _ref:
            continue
        _ref = _ref.split("|")[0].strip()[:60]  # drop "| knownclusterblast #n" noise
        if _ref:
            _kcb_refs[_ref] += 1
    # Ensure a column exists for each reference this strain hits (extend header on demand).
    _existing = {str(_b3_ws.cell(1, _c).value) for _c in range(1, _b3_ws.max_column + 1)
                 if _b3_ws.cell(1, _c).value is not None}
    for _ref in _kcb_refs:
        if _ref not in _existing:
            _b3_ws.cell(1, _b3_ws.max_column + 1).value = _ref
    _b3_row = {"strain": strain_id}
    _b3_row.update(dict(_kcb_refs))
    _append_row_by_header(_b3_ws, _b3_row)
    # P-A (v9.7.84): populate the per-trigger CCTT columns in B4 from the cctt counts dict.
    # The data was always present in ss.cctt["counts"] (keys like "T43-HAL_halogenase": n) but
    # was never mapped onto the B4 columns (CCTT_HAL, CCTT_LAN, ...), leaving them NULL and
    # blocking cross-strain CCTT comparison. Map by the T43-<CODE>_ prefix so the column gets the
    # count regardless of the descriptive suffix.
    _cctt_counts = ss.cctt.get("counts", {}) if ss else {}
    def _cctt_for(code: str) -> int:
        # sum any counts key whose token after "T43-" starts with <code> (e.g. "ENE" matches
        # "T43-ENE_enediyne"; "HAL" matches "T43-HAL_halogenase" but not "T43-XHAL_...").
        total = 0
        for k, v in _cctt_counts.items():
            if not k.startswith("T43-"):
                continue
            token = k[len("T43-"):].split("_", 1)[0]
            if token == code:
                total += int(v or 0)
        return total
    def _resistance_t1_count(scan) -> int:
        # PC-A4 (v9.7.101): the B4 aggregate previously read tier_counts["T1"], but the tier keys
        # are full strings ("T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"), so the lookup always
        # returned 0 even when per-BGC T1 self-protection clusters were present. Count per-BGC tiers
        # whose tier label starts with "T1" instead.
        if not scan:
            return 0
        per = (scan.resistance_tiers or {}).get("per_bgc", {})
        return sum(1 for v in per.values() if str(v.get("tier", "")).startswith("T1"))
    def _bldA_t4_count(scan) -> int:
        # PC-A4 (v9.7.101): scan_blda_tta returns {status, per_bgc, ...} with NO "bldA_T4" key, so
        # the old read ss.blda_tta.get("bldA_T4") was always 0. Count per-BGC records at tier T4.
        if not scan:
            return 0
        per = (scan.blda_tta or {}).get("per_bgc", {})
        return sum(1 for v in per.values() if v.get("bldA_tier") == "T4")
    # PC-A1 (v9.7.101): gold-only scans (resistance tiers, UMED gaps, EFLS pairs) do not run
    # in smoke/standard mode. Emitting 0 there is indistinguishable from a measured 0 and produced
    # a spurious cross-strain signal. Stamp the run_mode and render gold-only columns as "NA" for
    # non-gold strains so a reader (and any cross-strain consumer) can tell "not measured" from "zero".
    _run_mode = getattr(run.context, "analysis_mode", "") or "unknown"
    _gold = _run_mode == "gold"
    _na = lambda val: val if _gold else "NA"
    _append_row_by_header(wb["B4_Cross_Strain_Scans"], {
        "strain": strain_id, "run_mode": _run_mode, "KCB_status": "PASS", "RGGMCI_pairs": ss.rggmci.get("pairs_total", 0) if ss else 0,
        "RGGMCI_HIGH": ss.rggmci.get("high_pairs", 0) if ss else 0, "CCTT_triggers": sum(len(v) for v in cctt_coupling.values()),
        "CCTT_HAL": _cctt_for("HAL"), "CCTT_LAN": _cctt_for("LAN"), "CCTT_LASSO": _cctt_for("LASSO"),
        "CCTT_THA": _cctt_for("THA"), "CCTT_PHO": _cctt_for("PHO"), "CCTT_ENE": _cctt_for("ENE"),
        # v9.7.374 fix: both keys below were wrong -- CHITINASE_PATTERNS' real key is "CBM_CHITIN"
        # (uppercase/underscore, source_scans.py), not "cbm_chitin"; scan_tfbs() returns no top-level
        # "dasr_hits" key at all (grepped: zero writers anywhere) -- the real per-motif count lives at
        # ss.tfbs["counts"]["DasR_like_palindrome"] (TFBS_MOTIFS, source_scans.py). Both silently
        # defaulted to 0 for every strain via .get()'s fallback, so CGAD_chitin and TFBS_DasR have
        # been dead 0-columns in every master workbook -- and TFBS_DasR=0 alongside a genuinely
        # nonzero TFBS_total was internally inconsistent within the same row (12 total TFBS hits,
        # "0 of them DasR"). Reproduced live: a synthetic ss with real counts={"CBM_CHITIN":40} /
        # counts={"DasR_like_palindrome":12} still read 0/0 under the old keys.
        "CGAD_chitin": ss.chitinase.get("counts", {}).get("CBM_CHITIN", 0) if ss else 0,
        "TFBS_DasR": ss.tfbs.get("counts", {}).get("DasR_like_palindrome", 0) if ss else 0,
        "TFBS_total": ss.tfbs.get("total_hits", 0) if ss else 0, "bldA_T4": _bldA_t4_count(ss),
        "resistance_T1": _na(_resistance_t1_count(ss)),
        "UMED_gaps": _na(sum(1 for v in (ss.umed.get("per_bgc") or {}).values() if v.get("verdict") == "MATURATION_GAP_SOURCE_DERIVED") if ss else 0),
        "EFLS_pairs": _na(ss.efls.get("candidate_pair_count", 0) if ss else 0),
    })
    for sheet, key in (("C1_DAPR_Antibacterial", "ab_score"), ("C2_DAPR_Antifungal", "af_score")):
        # v9.7.8: actionable leads first (corrected_rank assigned), then standing-rule/primary-metab
        # downgrades — so a high-raw-score saccharide no longer sits at the top of the DAPR board.
        ordered = sorted(triage, key=lambda t: (t.corrected_rank is None, -getattr(t, key)))[:10]
        for rank, t in enumerate(ordered, 1):
            bgc = next((b for b in run.bgcs if b.bgc_id == t.bgc_id), None)
            if not bgc: continue
            if t.standing_rule_flag:
                note = f"DOWNGRADED (standing rule: {t.standing_rule_flag})"
            elif t.primary_metabolism_flag:
                note = "DOWNGRADED (primary-metabolism/pigment core gene)"
            else:
                note = "source-derived; judgment pending"
            _append_row_by_header(wb[sheet], {"strain": strain_id, "rank": rank, "assembly_locator": assembly_locator(bgc), "BGC_ID": bgc.bgc_id,
                "contig": bgc.node_id or bgc.contig or "contig_unresolved",
                "products": "; ".join(bgc.products), "score": getattr(t, key), "lead_tier": t.lead_tier,
                "band": t.lead_tier, "standing_rule": t.standing_rule_flag or "",
                "corrected_rank": t.corrected_rank if t.corrected_rank is not None else "",
                "kcb_top": bgc.kcb_top or "", "kcb_score": bgc.kcb_cumulative,
                "boundary": bgc.edge_status, "arch": bgc.architecture_confidence,
                "cctt": ", ".join(cctt_coupling.get(bgc.bgc_id, [])), "status_note": note})
    _append_row_by_header(wb["C3_Lead_Tier_Summary"], {"strain": strain_id, "top_ab_bgc": top_ab.bgc_id if top_ab else "", "ab_score": top_ab.ab_score if top_ab else "", "ab_band": top_ab.lead_tier if top_ab else "", "top_af_bgc": top_af.bgc_id if top_af else "", "af_score": top_af.af_score if top_af else "", "af_band": top_af.lead_tier if top_af else "", "top_ab_products": (next((b.products[0] for b in run.bgcs if b.bgc_id == (top_ab.bgc_id if top_ab else "")), "") or "")[:60],
        "top_af_products": (next((b.products[0] for b in run.bgcs if b.bgc_id == (top_af.bgc_id if top_af else "")), "") or "")[:60],
        "recommended_role": "Mamey extraction complete; Sapote judgment pending"})
    _append_row_by_header(wb["C4_Strain_Decision_Table"], {"sapote_rank": "", "strain": strain_id, "sapote_score": "", "bgc_count": counts["raw"], "assembly_tier": counts["assembly_tier"], "top_lead": top_ab.bgc_id if top_ab else "", "rggmci_high": ss.rggmci.get("high_pairs", 0) if ss else 0,
        "class_diversity": len(class_counts),
        "top_kcb_score": (next((b.kcb_cumulative for b in run.bgcs if b.bgc_id == top_ab.bgc_id), None) or "") if top_ab else "",
        "high_value_hits": sum(1 for t in triage if t.lead_tier in ("High", "Exceptional")),
        "rare_class_hits": sum(1 for t in triage if t.corrected_rank is not None and
            any(p.lower() not in ("saccharide","other","fatty_acid","terpene","butyrolactone") for p in
                (next((b.products for b in run.bgcs if b.bgc_id == t.bgc_id), []) or []))),
        "recommended_role": "judgment_pending"})
    _append_row_by_header(wb["D1_RGGMCI_All_Strains"], {"strain": strain_id, "contigs": run.assembly.contigs, "review_required": "Yes" if counts["edge"] + counts["full_contig"] > 5 else "No", "final_state": "REVIEW_TRIGGERED_NO_PROMOTION", "fragment_sets": len((ss.flbr if ss else {}).get("fragmented_megasynthase_bgcs", [])), "interpretation": "Pending — load manifest into judgment session"})
    # D2/D3: write the top-scoring RG-GMCI pairs into the master (previously defined in schema but
    # never populated — the cohort's cross-strain sheet came up empty despite rich per-strain pairs).
    # Capped per strain: a review shortlist, not the full pair dump (fragmented genomes over-pair on
    # shared class cores, so the top-N-by-score is the right view).
    ranked = (ss.rggmci.get("ranked_pairs", []) if ss else []) or []
    ranked = sorted(ranked, key=lambda p: -(p.get("rggmci_score") or 0))
    # v9.7.187: D2 = top-N by score PLUS any HIGH_RG_GMCI_RESCUE below the cap, so the board never
    # omits a pair D3 promoted (the run flag counts D3). Pre-fix, a HIGH pair scoring below
    # RGGMCI_D2_TOP_N landed in D3 but was truncated out of D2 — a silent-omission (AS-XXX family).
    _d2 = ranked[:RGGMCI_D2_TOP_N]
    _below_cap_high = [p for p in ranked[RGGMCI_D2_TOP_N:]
                       if p.get("rggmci_confidence") == "HIGH_RG_GMCI_RESCUE"]
    _d2 = _d2 + _below_cap_high
    for i, p in enumerate(_d2, start=1):
        _append_row_by_header(wb["D2_RGGMCI_Top_Pairs"], {
            "strain": strain_id, "rank": i, "bgc_a": p.get("bgc_a"), "bgc_b": p.get("bgc_b"),
            "rggmci_score": p.get("rggmci_score"), "confidence": p.get("rggmci_confidence"),
            "products_a": p.get("products_a"), "products_b": p.get("products_b"),
            "shared_references": "; ".join((p.get("best_sources") or [])[:3]) if isinstance(p.get("best_sources"), list) else (p.get("best_sources") or ""),
            "interpretation": p.get("interpretation_guard") or "RG-GMCI pair — claim-safe; CB-homology geometry, not asserted linkage"})
    promoted = [p for p in ranked if p.get("rggmci_confidence") == "HIGH_RG_GMCI_RESCUE"][:RGGMCI_D3_TOP_N]
    for i, p in enumerate(promoted, start=1):
        _append_row_by_header(wb["D3_RGGMCI_Promoted"], {
            "group_id": "%s_RG%02d" % (strain_id, i), "strain": strain_id, "grade": "HIGH_RG_GMCI",
            "fragments": p.get("pair"),
            "evidence_basis": "%s supporting refs (%s good-geometry); %s" % (
                p.get("supporting_references"), p.get("good_geometry_references"),
                "; ".join((p.get("best_sources") or [])[:2]) if isinstance(p.get("best_sources"), list) else ""),
            "claim_ceiling": "CB-homology reconstruction hypothesis; physical linkage unproven — confirm by long-read/boundary PCR",
            "chemistry_consequence": "%s / %s" % (p.get("products_a") or "?", p.get("products_b") or "?"),
            "status": "PROMOTED_CANDIDATE_PENDING_SAPOTE"})
    _append_row_by_header(wb["E1_Mode_B_Index"], {"strain": strain_id, "BGC_ID": "ALL", "mode_b_status": "JUDGMENT_PENDING", "analysis_platform": "Sapote/Claude", "date": today})
    # E3_Megacluster_Registry: BGCs ≥100 kb — deterministic from inventory.
    _MEGA_KB = 100.0
    for _bgc in run.bgcs:
        _len_kb = round((_bgc.end - _bgc.start) / 1000.0, 1) if _bgc.end and _bgc.start else 0.0
        if _len_kb >= _MEGA_KB:
            _append_row_by_header(wb["E3_Megacluster_Registry"], {
                "strain": strain_id, "BGC_ID": _bgc.bgc_id,
                "length_kb": _len_kb, "boundary": _bgc.edge_status,
                "products": "; ".join(_bgc.products[:4])[:80],
                "kcb_top": (_bgc.kcb_top or "")[:80],
                "kcb_score": _bgc.kcb_cumulative or "",
                "long_read_status": "not_assessed",
                "notes": "Deterministic extraction; confirm with long-read assembly or PCR",
            })
    _append_row_by_header(wb["F1_Ecology_Readiness"], {"strain": strain_id, "taxonomy": run.context.taxonomy, "source": run.context.source, "habitat": habitat, "assembly_tier": counts["assembly_tier"], "bgc_count": counts["raw"], "ab_lead": top_ab.bgc_id if top_ab else "", "af_lead": top_af.bgc_id if top_af else "", "tfbs_hits": ss.tfbs.get("total_hits", 0) if ss else 0,
        "cctt_classes": "; ".join(sorted(set(t for bgc_triggers in (cctt_coupling or {}).values() for t in bgc_triggers)))[:120] if cctt_coupling else "",
        "readiness": "SOURCE_DERIVED", "route": "Sapote judgment"})
    _append_row_by_header(wb["G2_Validation_Roles"], {"strain": strain_id, "primary_role": "benchmark/extraction", "manuscript_use": "pending Sapote judgment"})
    _append_row_by_header(wb["H1_Handoff_Log"], {"date": today, "platform": "Mamey", "direction": "extract_to_workbook", "strains_affected": strain_id, "sheets_modified": "canonical_v1_1_only", "validation_result": "PASS"})
    # P-F (v9.7.84): make the H2 gap entry strain- and finding-specific instead of a generic
    # "JUDGMENT_PENDING / Run Sapote/Claude deliverables" row. Derive the required-input and
    # next-action from the engine's own flags so an analysis chat can plan its work from the queue.
    _rg_high = ss.rggmci.get("high_pairs", 0) if ss else 0
    _tier = counts.get("assembly_tier", "")
    _cctt_total = sum(len(v) for v in cctt_coupling.values())
    _gap_inputs = []
    if _tier in ("VERY_POOR", "POOR"):
        _gap_inputs.append(f"{_tier} assembly")
    if _rg_high:
        _gap_inputs.append(f"{_rg_high} RGGMCI HIGH pair(s)")
    if _cctt_total:
        _gap_inputs.append(f"{_cctt_total} CCTT trigger(s)")
    _actions = ["Run Mode B AB+AF lead cards; ingest via mamey ingest-receipts"]
    if _rg_high:
        _actions.insert(0, f"Review {_rg_high} RGGMCI HIGH pair(s) before trusting lead ranking")
    if _tier in ("VERY_POOR", "POOR"):
        _actions.append("Treat edge/FC leads as truncation-flagged, not down-scored")
    _append_row_by_header(wb["H2_Gap_Queue"], {
        "priority": "H2", "gap_class": "JUDGMENT_PENDING", "strains": strain_id,
        "required_input": "; ".join(_gap_inputs) or "extraction complete",
        "next_action": " | ".join(_actions),
        "assigned_platform": "Sapote", "status": "OPEN"})
    ws = wb["H3_Schema_Version"]
    if ws.max_row < 2:
        ws.cell(2, 1).value = "Generated by"
        ws.cell(2, 2).value = "Mamey canonical v1.1 writer"
    if "A1_Dashboard" in wb.sheetnames:
        wsd = wb["A1_Dashboard"]
        wsd["B3"] = wb["A2_Strain_Registry"].max_row - 1
        wsd["B4"] = wb["B1_BGC_Master"].max_row - 1
        wsd["B5"] = today
        wsd["B6"] = f"Mamey v{run.context.version}"
        # PC-A1 (v9.7.101): flag a mixed-mode cohort. Gold-only scan columns are NA for non-gold
        # strains (above), but a reader should also see at the dashboard level that modes differ —
        # cross-strain comparison of the gold-only signals is only valid within one mode.
        b4 = wb["B4_Cross_Strain_Scans"]
        hdr = [c.value for c in b4[1]]
        if "run_mode" in hdr:
            mi = hdr.index("run_mode")
            modes = {b4.cell(r, mi + 1).value for r in range(2, b4.max_row + 1)
                     if b4.cell(r, mi + 1).value not in (None, "")}
            if len(modes) > 1:
                wsd["A8"] = "MIXED_MODE_COHORT"
                wsd["B8"] = ("strains were run in different modes (" + ", ".join(sorted(map(str, modes)))
                             + "); gold-only scan columns (resistance_T1, UMED_gaps, EFLS_pairs) are "
                             "NA for non-gold strains and are not comparable across modes")


# ---------------------------------------------------------------------------
# BGC_Class_Matrix helpers
# ---------------------------------------------------------------------------

ALL_AS_CLASSES = [
    "2dos", "CDPS", "NAGGN", "NAPAA", "NI-siderophore", "NRP-metallophore",
    "NRPS", "NRPS-like", "PKS-like", "RRE-containing", "RiPP-like",
    "T1PKS", "T2PKS", "T3PKS", "aminopolycarboxylic-acid", "arylpolyene",
    "atropopeptide", "azole-containing-RiPP", "azoxy-crosslink", "betalactone",
    "butyrolactone", "crocagin", "ectoine", "fatty_acid", "halogenated",
    "hglE-KS", "hydrogen-cyanide", "indole", "lanthipeptide-class-i",
    "lanthipeptide-class-ii", "lanthipeptide-class-iii", "lanthipeptide-class-iv",
    "lanthipeptide-class-v", "lassopeptide", "linaridin", "lincosamides",
    "nucleoside", "oligosaccharide", "other", "phenazine",
    "polyhalogenated-pyrrole", "quinone_isoprenoid_chain", "ranthipeptide",
    "redox-cofactor", "saccharide", "terpene", "terpene-precursor",
    "thioamide-NRP", "transAT-PKS", "transAT-PKS-like", "triceptide",
]


def _update_class_matrix(wb: Workbook, strain_id: str,
                          bgcs: list[BGCRecord]) -> None:
    ws = _ensure(wb, "BGC_Class_Matrix")

    # Build full class list from existing headers + new classes
    if _is_effectively_empty(ws):
        existing_classes: list[str] = []
    else:
        _repair_leading_blank_header(ws, expected_first="Strain")
        existing_classes = [
            str(ws.cell(1, c).value)
            for c in range(2, ws.max_column + 1)
            if ws.cell(1, c).value not in (None, "Total classified calls")
        ]

    # Count product classes for this strain
    product_counts: Counter = Counter()
    for bgc in bgcs:
        for p in bgc.products:
            product_counts[p.strip()] += 1

    # BC2_399 fix: real antiSMASH product tokens on bgc.products are lowercase for several of
    # ALL_AS_CLASSES's own curated entries ("NRPS", "T1PKS", "T2PKS", "T3PKS", "NRPS-like",
    # "NRP-metallophore", "NI-siderophore", ...), confirmed against
    # mamey/class_architecture.py::_REAL_CLASSES and this round's mamey/cnbu.py /
    # tools/reclass_check.py / mamey/master_workbook.py::_b2_product_class_counts fixes for the
    # identical field. Merging raw product keys directly into `all_classes` (below) previously
    # created a SECOND, differently-cased column for every such class -- e.g. both an "NRPS"
    # column (from ALL_AS_CLASSES, always empty, since no real product ever matches it exactly)
    # and a separate "nrps" column (holding the real counts) -- reproduced directly. No data was
    # lost, but the canonical curated column silently read as "this strain has zero", and the
    # real counts hid under an undocumented lowercase duplicate. Route each raw product token to
    # whichever casing is ALREADY established -- an existing sheet header entry first (so an
    # already-corrupted real workbook's existing columns are matched, not further duplicated),
    # then ALL_AS_CLASSES's own curated casing, falling back to the raw token unchanged for a
    # genuinely novel class in neither list (unchanged behavior for that case).
    existing_ci = {c.lower(): c for c in existing_classes}
    all_as_ci = {c.lower(): c for c in ALL_AS_CLASSES}
    canon_counts: Counter = Counter()
    for raw_cls, n in product_counts.items():
        key = existing_ci.get(raw_cls.lower()) or all_as_ci.get(raw_cls.lower()) or raw_cls
        canon_counts[key] += n
    product_counts = canon_counts
    # Also drop any ALL_AS_CLASSES entry that collides case-insensitively with an already
    # existing sheet header -- otherwise the curated list re-introduces the same duplicate
    # this fix exists to prevent (e.g. re-adding "NRPS" when the sheet already has "nrps").
    all_as_classes_deduped = [c for c in ALL_AS_CLASSES if c.lower() not in
                              {e.lower() for e in existing_classes}]

    # Merge class lists
    all_classes = list(dict.fromkeys(existing_classes + all_as_classes_deduped +
                                     list(product_counts.keys())))

    # Rebuild header if needed
    header = ["Strain"] + all_classes + ["Total classified calls"]
    if _is_effectively_empty(ws):
        _write_header(ws, header, HDR_FILL_BLUE)
    else:
        _repair_leading_blank_header(ws, expected_first="Strain")
        # Extend header with any new classes
        current_max = ws.max_column
        existing_header = {str(ws.cell(1, c).value): c for c in range(1, current_max + 1)}
        for cls in all_classes:
            if cls not in existing_header:
                ws.cell(1, current_max + 1).value = cls
                current_max += 1

    # Write row for this strain
    col_map = {str(ws.cell(1, c).value): c for c in range(1, ws.max_column + 1)}
    row = ws.max_row + 1
    ws.cell(row, col_map["Strain"]).value = strain_id
    total = 0
    for cls, count in product_counts.items():
        if cls in col_map:
            ws.cell(row, col_map[cls]).value = count
            total += count
    if "Total classified calls" in col_map:
        ws.cell(row, col_map["Total classified calls"]).value = total


def _update_known_cluster_matrix(wb: Workbook, strain_id: str,
                                  bgcs: list[BGCRecord]) -> None:
    ws = _ensure(wb, "Known_Cluster_Matrix")

    # Collect KCB families for this strain
    families: Counter = Counter()
    for bgc in bgcs:
        for hit in bgc.mibig_hits:
            families[hit] += 1
        if bgc.kcb_top:
            families[bgc.kcb_top] += 1

    if not families:
        return

    # Extend headers with new families
    if _is_effectively_empty(ws):
        _write_header(ws, ["Strain"], HDR_FILL_BLUE)
    else:
        _repair_leading_blank_header(ws, expected_first="Strain")

    col_map = {str(ws.cell(1, c).value): c for c in range(1, ws.max_column + 1)}
    for family in families:
        if family not in col_map:
            new_col = ws.max_column + 1
            ws.cell(1, new_col).value = family
            ws.cell(1, new_col).fill = HDR_FILL_BLUE
            ws.cell(1, new_col).font = HDR_FONT
            col_map[family] = new_col

    row = ws.max_row + 1
    ws.cell(row, col_map["Strain"]).value = strain_id
    for family, count in families.items():
        ws.cell(row, col_map[family]).value = count


# ---------------------------------------------------------------------------
# Per-strain sheet writers
# ---------------------------------------------------------------------------

def _write_per_strain_sheets(wb: Workbook, run: MameyRun) -> None:
    from .scoring import score_keywords, edge_penalty, product_text
    code = _sheet_code(run.context.strain_id)
    counts_dict = _bgc_counts(run.bgcs)
    ss = run.source_scans
    cctt_coupling = ss.cctt.get("bgc_coupling", {}) if ss else {}
    rt_per_bgc    = ss.resistance_tiers.get("per_bgc", {}) if ss else {}
    dss_per_bgc   = ss.per_bgc_dss.get("per_bgc", {}) if ss else {}
    tta_per_bgc   = ss.blda_tta.get("per_bgc", {}) if ss else {}

    # --- [code]_Summary ---
    ws_sum = _ensure(wb, f"{code}_Summary")
    ws_sum.append(["Field", "Value"])
    _style_header(ws_sum, HDR_FILL_GREEN)
    rows = [
        ("Strain",          run.context.display_name),
        ("Taxonomy",        run.context.taxonomy),
        ("Source",          run.context.source),
        ("Mode",            run.context.analysis_mode),
        ("Analysis date",   date.today().isoformat()),
        ("Genome bp",       run.assembly.genome_bp),
        ("Contigs",         run.assembly.contigs),
        ("N50",             run.assembly.n50),
        ("GC %",            run.assembly.gc_pct),
        ("Raw BGCs",        counts_dict["raw"]),
        ("Corrected BGCs",  counts_dict["corrected"]),
        ("Interior BGCs",   counts_dict["interior"]),
        ("Edge BGCs",       counts_dict["edge"]),
        ("Full-contig BGCs",counts_dict["full_contig"]),
        ("Assembly tier",   counts_dict["assembly_tier"]),
        ("Interior %",      counts_dict["interior_pct"]),
    ]
    for f, v in rows:
        ws_sum.append([f, v])
    ws_sum.append(["", ""])
    ws_sum.append(["Scan", "State", "Detail"])
    for scan_name, state, detail in run.scan_status.get("scans", []):
        ws_sum.append([scan_name, state, detail])
    ws_sum.append(["", ""])
    for issue in run.issues:
        ws_sum.append(["Issue", issue])

    # --- [code]_Triage ---
    ws_t = _ensure(wb, f"{code}_Triage")
    t_headers = [
        "BGC_ID", "Boundary", "Arch", "Products",
        "KCB top", "KCB score", "KCB proteins", "RiQ score",
        "AB auto", "AF auto", "Novelty auto", "Lead tier auto",
        "TTA tier", "CCTT triggers", "Resistance tier", "DSS",
        "Depth floor", "QS routing", "NAPAA flag",
    ]
    ws_t.append(t_headers)
    _style_header(ws_t, HDR_FILL_GREEN)

    qs_ids    = set(ss.qs_signals.get("qs_signal_bgc_ids", [])) if ss else set()
    napaa_ids = set(ss.qs_signals.get("napaa_bgc_ids", [])) if ss else set()

    from .scoring import triage_bgcs
    triage = triage_bgcs(run.bgcs, run.source_scans.rggmci if run.source_scans else None, run.source_scans if run.source_scans else None)
    triage_by_id = {t.bgc_id: t for t in triage}

    for bgc in sorted(run.bgcs, key=lambda b: b.bgc_id):
        t   = triage_by_id.get(bgc.bgc_id)
        tta = tta_per_bgc.get(bgc.bgc_id, {})
        rt  = rt_per_bgc.get(bgc.bgc_id, {})
        dss = dss_per_bgc.get(bgc.bgc_id, {})
        cctt_hits = ", ".join(cctt_coupling.get(bgc.bgc_id, []))

        # Depth floor determination (v1.2 §0 rules)
        depth = "abbreviated_ledger"
        if bgc.edge_status == "Interior":
            depth = "full_mode_b"
        elif cctt_hits:
            depth = "full_mode_b"
        elif bgc.kcb_cumulative and bgc.kcb_cumulative > 5000:
            depth = "full_mode_b"

        ws_t.append([
            bgc.bgc_id,
            bgc.edge_status,
            bgc.architecture_confidence,
            "; ".join(bgc.products[:8]),
            bgc.kcb_top or "",
            bgc.kcb_cumulative,
            bgc.kcb_protein_hits,
            bgc.riq_score,
            t.ab_score if t else "",
            t.af_score if t else "",
            t.novelty_score if t else "",
            t.lead_tier if t else "",
            tta.get("bldA_tier", ""),
            cctt_hits,
            rt.get("tier", ""),
            dss.get("dss", ""),
            depth,
            "QS_ECOLOGY_ONLY" if bgc.bgc_id in qs_ids else "",
            "NAPAA" if bgc.bgc_id in napaa_ids else "",
        ])

    # --- [code]_Lead_Propagation ---
    ws_lp = _ensure(wb, f"{code}_Lead_Propagation")
    lp_headers = [
        "Track", "Rank", "BGC_ID", "Products", "Boundary", "Arch",
        "WL_auto", "Lead tier", "KCB top", "KCB score", "KCB proteins",
        "RiQ score", "CCTT triggers", "Resistance tier", "DSS", "Notes",
    ]
    ws_lp.append(lp_headers)
    _style_header(ws_lp, HDR_FILL_GREEN)

    # AB track — top 15 by AB score
    ab_sorted = sorted(triage, key=lambda t: t.ab_score, reverse=True)[:15]
    for rank, t in enumerate(ab_sorted, 1):
        bgc = next((b for b in run.bgcs if b.bgc_id == t.bgc_id), None)
        if not bgc:
            continue
        cctt_hits = ", ".join(cctt_coupling.get(bgc.bgc_id, []))
        rt = rt_per_bgc.get(bgc.bgc_id, {})
        dss = dss_per_bgc.get(bgc.bgc_id, {})
        ws_lp.append([
            "AB", rank, bgc.bgc_id, "; ".join(bgc.products[:6]),
            bgc.edge_status, bgc.architecture_confidence,
            t.ab_score, t.lead_tier,
            bgc.kcb_top or "", bgc.kcb_cumulative, bgc.kcb_protein_hits,
            bgc.riq_score, cctt_hits, rt.get("tier", ""), dss.get("dss", ""), "",
        ])

    # AF track — top 15 by AF score
    af_sorted = sorted(triage, key=lambda t: t.af_score, reverse=True)[:15]
    for rank, t in enumerate(af_sorted, 1):
        bgc = next((b for b in run.bgcs if b.bgc_id == t.bgc_id), None)
        if not bgc:
            continue
        cctt_hits = ", ".join(cctt_coupling.get(bgc.bgc_id, []))
        rt = rt_per_bgc.get(bgc.bgc_id, {})
        dss = dss_per_bgc.get(bgc.bgc_id, {})
        ws_lp.append([
            "AF", rank, bgc.bgc_id, "; ".join(bgc.products[:6]),
            bgc.edge_status, bgc.architecture_confidence,
            t.af_score, t.lead_tier,
            bgc.kcb_top or "", bgc.kcb_cumulative, bgc.kcb_protein_hits,
            bgc.riq_score, cctt_hits, rt.get("tier", ""), dss.get("dss", ""), "",
        ])

    # --- [code]_Missingness (skeleton — filled by judgment layer) ---
    ws_m = _ensure(wb, f"{code}_Missingness")
    ws_m.append(["Category", "Item", "Status", "Action"])
    _style_header(ws_m, HDR_FILL_GREEN)
    ws_m.append(["Assembly", "Edge/FC fragmentation",
                 f"{counts_dict['edge']+counts_dict['full_contig']} of {counts_dict['raw']} BGCs are Edge/FC",
                 "Long-read sequencing for high-priority leads"])
    ws_m.append(["Judgment", "Mode B prose", "PENDING — load manifest into Mamey v1.2 prompt",
                 "Run standard or gold judgment session"])
    ws_m.append(["Chemistry", "HRMS/NMR", "Not performed", "Extract and fractionate top leads"])


# ---------------------------------------------------------------------------
# BGC counts helper
# ---------------------------------------------------------------------------

def _bgc_counts(bgcs: list[BGCRecord]) -> dict:
    c = Counter(b.edge_status for b in bgcs)
    raw = len(bgcs)
    interior = c.get("Interior", 0)
    edge = c.get("Edge", 0)
    fc = c.get("Full-contig", 0)
    interior_pct = round(interior / raw * 100, 1) if raw else None
    return {
        "raw": raw, "interior": interior, "edge": edge, "full_contig": fc,
        "corrected": corrected_bgc_count(interior, edge, fc),
        "interior_pct": interior_pct,
        "assembly_tier": assembly_tier(interior_pct),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _scope_from_taxonomy(taxonomy: str | None) -> str:
    """v9.7.185 P3: IN_SCOPE | OUT_OF_SCOPE | REVIEW from organism genus via cohort_resolver."""
    try:
        from .cohort_resolver import resolve_cohort
        st = resolve_cohort("", taxonomy or "").get("actino_status")
    except Exception:
        return "REVIEW"
    if st == "non_actinomycete":
        return "OUT_OF_SCOPE"
    if st == "actinomycete":
        return "IN_SCOPE"
    return "REVIEW"


def update_master_workbook(run: MameyRun, master_path: str | Path,
                            output_path: str | Path, prune_noncanonical: bool = False) -> None:
    """Append one strain's data using frozen schema-v1.1 sheets only.

    The legacy descriptive sheet path (Dashboard/Strain_Registry/BGC_Master)
    is intentionally not invoked here; public-release workbooks must contain
    only frozen coded sheets (A1/A2/B1/...).

    prune_noncanonical (default False): when True, non-canonical sheets are removed (the old behaviour).
    When False, extra sheets (Priority_Leads, Lead_Board, DAPR/RGGMCI boards, etc.) are PRESERVED — a
    richer workbook is no longer silently gutted by a direct call. The CLI v1.2 guard remains as defence in depth.
    """
    # AMBER_EXCLUSION_HARDENING (.353): refuse a hard-excluded strain at the source,
    # before it can be appended to a governed cross-strain sheet (BGC_Master / class
    # matrix / DAPR AB+AF boards). SSOT: exclusions.governed_excluded() = {AS-XXX}.
    # AS-XXX is governed (decontam strain-of-record) and passes.
    from .exclusion_gate import assert_strain_governable
    assert_strain_governable(run.context.strain_id)

    master_path = Path(master_path)
    output_path = Path(output_path)

    if master_path.exists():
        wb = load_workbook(master_path)
        expected = set(CANONICAL_V1_HEADERS) | {"A1_Dashboard"}
        if prune_noncanonical:
            # opt-in: drop non-canonical sheets so the output validates against the frozen v1.1 set only
            for sheet_name in list(wb.sheetnames):
                if sheet_name not in expected:
                    del wb[sheet_name]
        else:
            # default: preserve extra sheets (warn rather than delete)
            extra = [s for s in wb.sheetnames if s not in expected]
            if extra:
                emit(f"  [master] preserving {len(extra)} non-canonical sheet(s): {', '.join(extra[:8])}"
                      f"{'…' if len(extra) > 8 else ''} (pass prune_noncanonical=True to drop them)")
    else:
        wb = Workbook()
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]

    counts = _bgc_counts(run.bgcs)
    from .scoring import triage_bgcs
    triage = triage_bgcs(run.bgcs, run.source_scans.rggmci if run.source_scans else None, run.source_scans if run.source_scans else None)

    _ensure_canonical_headers(wb)
    from .workbook_dedup import drop_existing_strain
    _removed = drop_existing_strain(wb, run.context.strain_id)  # P2: idempotent re-ingest (kills double-append)
    if _removed:
        emit(f"  [master] idempotent re-ingest: dropped {_removed} stale row(s) for {run.context.strain_id}")
    _write_canonical_v1_views(wb, run, triage, counts)

    atomic_save_workbook_safely(wb, output_path)


def _infer_habitat(source: str) -> str:
    s = source.lower()
    if any(k in s for k in ("bee", "bumblebee", "apis", "bombus", "hymenoptera",
                             "ant", "attine", "atta", "acromyrmex", "wasp")):
        return "4_Hymenoptera"
    if any(k in s for k in ("moss", "bryophyte", "sphagnum", "liverwort", "lichen")):
        return "3_Bryophyte_lichen"
    if any(k in s for k in ("soil", "rhizosphere", "root", "sediment", "arid", "desert")):
        return "1_Terrestrial_soil"
    if any(k in s for k in ("marine", "ocean", "sea", "sponge", "reef", "coral")):
        return "2_Marine"
    if any(k in s for k in ("fungal", "mushroom", "mycelium", "garden")):
        return "7_Fungal"
    # v9.7.8: do NOT infer habitat from strain provenance (type-strain/accession) or fall back to a
    # taxonomy default — a wrong `1_Terrestrial_*` stamp can leak into ecological claims for bee/attine
    # SID strains. Anything not matched from the user-supplied source string is an explicit placeholder.
    return "ENGINE_DEFAULT_PLACEHOLDER"


def cross_strain_context(master_path: str | Path,
                          strain_id: str, source: str) -> dict:
    """Read the master workbook and return cross-strain context for the manifest.

    Called after update_master_workbook() so the new strain is already present.
    """
    master_path = Path(master_path)
    if not master_path.exists():
        return {"master_workbook": str(master_path),
                "related_strains_in_master": [],
                "shared_bgc_families": [],
                "habitat_peers_in_master": 0}

    wb = load_workbook(master_path, read_only=True, data_only=True)
    habitat = _infer_habitat(source)

    related: list[str] = []
    peers = 0

    if "A2_Strain_Registry" in wb.sheetnames:
        ws = wb["A2_Strain_Registry"]
        headers = [str(ws.cell(1, c).value) for c in range(1, ws.max_column + 1)]
        cm = {h: i for i, h in enumerate(headers)}
        for row in ws.iter_rows(min_row=2, values_only=True):
            sid = str(row[cm.get("strain", 0)]) if row[cm.get("strain", 0)] else ""
            if not sid or sid == strain_id:
                continue
            src_idx = cm.get("ecology_source", cm.get("source", 2))
            src = str(row[src_idx]) if src_idx < len(row) and row[src_idx] else ""
            if _infer_habitat(src) == habitat:
                peers += 1
                related.append(sid)

    # Shared BGC families from B3_Known_Cluster_Matrix
    shared_families: list[str] = []
    if "B3_Known_Cluster_Matrix" in wb.sheetnames:
        ws2 = wb["B3_Known_Cluster_Matrix"]
        header = [str(ws2.cell(1, c).value) for c in range(1, ws2.max_column + 1)]
        for row in ws2.iter_rows(min_row=2, values_only=True):
            if not row[0] or str(row[0]) != strain_id:
                continue
            for i, val in enumerate(row[1:], 1):
                if val and i < len(header):
                    shared_families.append(header[i])

    return {
        "master_workbook": str(master_path),
        "related_strains_in_master": related[:20],
        "shared_bgc_families": shared_families[:20],
        "habitat_peers_in_master": peers,
    }


# ---------------------------------------------------------------------------
# Judgment write-back (v9.7.67) — judgment_store → master workbook
# ---------------------------------------------------------------------------

def _read_dl_csv(path) -> list[dict]:
    import csv as _csv
    from pathlib import Path as _P
    p = _P(path)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(_csv.DictReader(fh))


# v9.7.89 (request §5/§20/§25): the six domain-level sheets + their headers. Created on demand so
# existing sheet gates are untouched; populated only when the domain_level/ tables exist.
_DOMAIN_SHEETS: dict[str, list[str]] = {
    "Domain_Rows_Long": ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "locus_tag",
                         "cds_start", "cds_end", "strand", "domain_name", "domain_description",
                         "evalue", "domain_role_category", "BGC_products", "KCB_top",
                         "AB_score", "AF_score"],
    "Domain_Role_Counts_By_BGC": ["Strain", "BGC_ID", "Assembly_Locator",
                                  "domain_role_category", "count"],
    "Domain_Role_Counts_By_Strain": ["Strain", "domain_role_category", "count"],
    "Domain_Architecture_Strings": ["Strain", "Rank", "BGC_ID", "Assembly_Locator",
                                    "Products", "domain_architecture_string", "n_domains"],
    "ASModules_Domain_Level": ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "Domain_total",
                               "Biosynthetic_core_domain_count", "Tailoring_domain_count",
                               "Transport_domain_count", "Regulatory_domain_count",
                               "Architecture_archetype"],
    "Domain_Claim_Safety": ["Strain", "Rank", "BGC_ID", "Assembly_Locator",
                            "Safe_domain_claims", "Unsafe_domain_claims", "Domain_claim_ceiling"],
}


def update_domain_level_sheets(domain_level_dir, master_workbook_path) -> dict[str, Any]:
    """v9.7.89: populate the six domain-level sheets from a domain_level/ output dir, and update
    the cross-strain master (B1_BGC_Master) with domain-burden fields for ranking beyond AB/AF.
    Creates sheets on demand (existing gates untouched). Idempotent per strain. No-op if no tables."""
    import openpyxl
    from pathlib import Path as _P
    from collections import Counter, defaultdict

    dl = _P(domain_level_dir)
    rows_long = _read_dl_csv(dl / "domain_rows_long.csv")
    role_by_bgc = _read_dl_csv(dl / "domain_role_counts_by_bgc.csv")
    complexity = _read_dl_csv(dl / "domain_complexity_metrics_by_bgc.csv")
    claims = _read_dl_csv(dl / "domain_safe_unsafe_claims.csv")
    if not rows_long and not complexity:
        return {"status": "NO_DOMAIN_TABLES", "sheets": 0}

    strains = sorted({r.get("Strain", "") for r in rows_long} |
                     {r.get("Strain", "") for r in complexity})

    wb = openpyxl.load_workbook(master_workbook_path)
    # ensure all six sheets exist with headers
    for name, header in _DOMAIN_SHEETS.items():
        if name not in wb.sheetnames:
            ws = wb.create_sheet(name)
            for j, h in enumerate(header, 1):
                ws.cell(1, j).value = h
        else:
            ws = wb[name]
            if ws.cell(1, 1).value is None:
                for j, h in enumerate(header, 1):
                    ws.cell(1, j).value = h

    def _clear_strain_rows(ws, strain_col_header="Strain"):
        cmap = _col_map(ws)
        sc = cmap.get(strain_col_header)
        if not sc:
            return
        for r in range(ws.max_row, 1, -1):
            if ws.cell(r, sc).value in strains:
                ws.delete_rows(r, 1)

    # Domain_Rows_Long
    ws = wb["Domain_Rows_Long"]; _clear_strain_rows(ws)
    for r in rows_long:
        _append_row_by_header(ws, r)

    # Domain_Role_Counts_By_BGC
    ws = wb["Domain_Role_Counts_By_BGC"]; _clear_strain_rows(ws)
    for r in role_by_bgc:
        _append_row_by_header(ws, r)

    # Domain_Role_Counts_By_Strain (aggregate)
    ws = wb["Domain_Role_Counts_By_Strain"]; _clear_strain_rows(ws)
    by_strain: dict[tuple, int] = Counter()
    for r in rows_long:
        by_strain[(r.get("Strain", ""), r.get("domain_role_category", ""))] += 1
    for (strain, role), n in sorted(by_strain.items()):
        _append_row_by_header(ws, {"Strain": strain, "domain_role_category": role, "count": n})

    # Domain_Architecture_Strings (ordered domain names per BGC)
    ws = wb["Domain_Architecture_Strings"]; _clear_strain_rows(ws)
    arch: dict[str, list] = defaultdict(list)
    meta: dict[str, dict] = {}
    for r in sorted(rows_long, key=lambda x: (x.get("BGC_ID", ""), int(x.get("cds_start") or 0))):
        arch[r["BGC_ID"]].append(r.get("domain_name", ""))
        meta[r["BGC_ID"]] = {"Strain": r.get("Strain", ""), "Rank": r.get("Rank", ""),
                             "Assembly_Locator": r.get("Assembly_Locator", ""),
                             "Products": r.get("BGC_products", "")}
    for bid, doms in arch.items():
        m = meta[bid]
        _append_row_by_header(ws, {"Strain": m["Strain"], "Rank": m["Rank"], "BGC_ID": bid,
                                   "Assembly_Locator": m["Assembly_Locator"],
                                   "Products": m["Products"],
                                   "domain_architecture_string": " - ".join(doms),
                                   "n_domains": len(doms)})

    # ASModules_Domain_Level (burden table from complexity)
    ws = wb["ASModules_Domain_Level"]; _clear_strain_rows(ws)
    for r in complexity:
        _append_row_by_header(ws, {k: r.get(k, "") for k in _DOMAIN_SHEETS["ASModules_Domain_Level"]})

    # Domain_Claim_Safety
    ws = wb["Domain_Claim_Safety"]; _clear_strain_rows(ws)
    for r in claims:
        _append_row_by_header(ws, r)

    # cross-strain master: add domain-burden columns to B1_BGC_Master for the BGCs present
    n_master = 0
    if "B1_BGC_Master" in wb.sheetnames:
        b1 = wb["B1_BGC_Master"]
        cmap = _col_map(b1)
        for col in ("Domain_total", "Core_domain_burden", "Tailoring_domain_burden"):
            if col not in cmap:
                newc = b1.max_column + 1
                b1.cell(1, newc).value = col
                cmap[col] = newc
        cx_by_bgc = {r["BGC_ID"]: r for r in complexity}
        bgc_col = cmap.get("BGC_ID") or cmap.get("bgc_id")
        if bgc_col:
            for r in range(2, b1.max_row + 1):
                bid = b1.cell(r, bgc_col).value
                cx = cx_by_bgc.get(bid)
                if cx:
                    b1.cell(r, cmap["Domain_total"]).value = cx.get("Domain_total", "")
                    b1.cell(r, cmap["Core_domain_burden"]).value = cx.get("Biosynthetic_core_domain_count", "")
                    b1.cell(r, cmap["Tailoring_domain_burden"]).value = cx.get("Tailoring_domain_count", "")
                    n_master += 1

    atomic_save_workbook_safely(wb, master_workbook_path)
    return {"status": "OK", "sheets": len(_DOMAIN_SHEETS), "strains": len(strains),
            "n_rows_long": len(rows_long), "n_master_updated": n_master}


def update_e2_comparative_pairs(bank_path: str | Path, master_workbook_path: str | Path,
                                gene_context_dir: str | Path | None = None) -> dict[str, Any]:
    """v9.7.88 9.7.88-J: populate E2_Comparative_Pairs from a cohort bank (≥2 strains).

    bank_path: a cohort bgc_data.json with BGCs from ≥2 strains.
    gene_context_dir: optional dir holding <strain>_gene_context.jsonl files (enables the
        a_domain_match signal). Looked up by strain id.
    Returns {"status", "n_pairs", "n_strains"}. No-op (status NOT_ENOUGH_STRAINS) for <2 strains.
    """
    import openpyxl
    from .comparative_pairs import build_comparative_pairs, load_bank
    from pathlib import Path as _P

    bank = load_bank(bank_path)
    strains = {b.get("sid") for b in bank.get("bgcs", []) if b.get("sid")}
    if len(strains) < 2:
        return {"status": "NOT_ENOUGH_STRAINS", "n_pairs": 0, "n_strains": len(strains)}

    # optional gene context per strain
    gctx: dict[str, dict] = {}
    if gene_context_dir:
        from .gene_context import load_gene_context
        gcd = _P(gene_context_dir)
        for sid in strains:
            # load_gene_context expects a package dir + strain id; here files may be flat in gcd
            ctx = load_gene_context(gcd, sid)
            if ctx:
                gctx[sid] = ctx

    rows = build_comparative_pairs(bank, gene_context_by_strain=gctx)

    wb = openpyxl.load_workbook(master_workbook_path)
    if "E2_Comparative_Pairs" not in wb.sheetnames:
        return {"status": "NO_E2_SHEET", "n_pairs": 0, "n_strains": len(strains)}
    ws = wb["E2_Comparative_Pairs"]
    # clear existing data rows (keep header) so re-runs are idempotent
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)
    for r in rows:
        _append_row_by_header(ws, r)
    atomic_save_workbook_safely(wb, master_workbook_path)
    return {"status": "OK", "n_pairs": len(rows), "n_strains": len(strains)}


def update_e1_from_judgment(package_dir: str | Path, master_workbook_path: str | Path) -> dict[str, Any]:
    """Write completed Mode B records from the judgment store into the master workbook.

    Called by Sapote (or the operator) after one or more Mode B batches are
    complete. Updates:
      - E1_Mode_B_Index: replaces the "ALL / JUDGMENT_PENDING" placeholder row
        with one row per BGC that has a COMPLETE entry in the judgment register.
        BGCs still PENDING get individual PENDING rows (replacing the aggregate).
      - A4_Completeness_Audit: E1_mode_b cell updated from JUDGMENT_PENDING to
        COMPLETE or IN_PROGRESS depending on the register.

    Uses the same atomic-save and drop_existing_strain patterns as update_master_workbook
    so a second call (e.g. after Batch 2) replaces Batch 1 rows cleanly.

    Returns a summary dict with counts and status.
    """
    import csv as _csv
    import datetime as _dt
    import os as _os

    pkg = Path(package_dir)
    wb_path = Path(master_workbook_path)

    if not wb_path.exists():
        raise FileNotFoundError(f"Master workbook not found: {wb_path}")

    from .judgment_store import read_register, read_laypersons, read_fermentation
    from .workbook_dedup import drop_existing_strain

    reg = read_register(pkg)
    strain_id = reg.get("strain_id") or _strain_from_pkg(pkg)
    today = _dt.date.today().isoformat()

    # Load BGC metadata from triage board for length_kb / products / subprograms
    triage_meta: dict[str, dict] = {}
    tb_candidates = list(pkg.glob("*_4_triage_board.csv"))
    if tb_candidates:
        with open(tb_candidates[0], newline="", encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                bid = row.get("BGC_ID", "")
                if bid:
                    triage_meta[bid] = row

    # Load per-BGC layperson + fermentation snippets
    lay_full = read_laypersons(pkg)
    ferm_full = read_fermentation(pkg)

    def _extract_section(text: str, bgc_id: str) -> str:
        """Extract the paragraph under '## BGC_ID' from accumulated section text."""
        import re as _re
        m = _re.search(
            rf"##\s+{_re.escape(bgc_id)}\s*\n+(.*?)(?=\n##\s|\Z)",
            text, _re.DOTALL
        )
        return m.group(1).strip() if m else ""

    wb = load_workbook(wb_path)
    _ensure_canonical_headers(wb)

    # Drop ALL prior E1 rows for this strain (replaces "ALL" placeholder + any partial prior run)
    _e1_ws = wb["E1_Mode_B_Index"]
    _e1_removed = 0
    for _r in range(_e1_ws.max_row, 1, -1):
        if _e1_ws.cell(row=_r, column=1).value == strain_id:
            _e1_ws.delete_rows(_r, 1)
            _e1_removed += 1

    # Write one row per BGC
    bgcs = reg.get("bgcs", {})
    n_written = 0
    n_complete = 0
    n_pending = 0

    for bgc_id in sorted(bgcs.keys()):
        bgc_rec = bgcs[bgc_id]
        status = bgc_rec.get("status", "PENDING")
        meta = triage_meta.get(bgc_id, {})

        # Length in kb from triage board (may be absent for very old packages)
        try:
            _start = int(meta.get("Start", 0) or 0)
            _end = int(meta.get("End", 0) or 0)
            length_kb = round((_end - _start) / 1000, 1) if _end > _start else ""
        except (ValueError, TypeError):
            length_kb = ""

        products = meta.get("Products", "")
        subprograms = meta.get("Arch_Capacity", "") or meta.get("Arch", "")
        report_file = bgc_rec.get("mode_b_file", "") or ""

        lay_snippet = _extract_section(lay_full, bgc_id) if status == "COMPLETE" else ""
        ferm_snippet = _extract_section(ferm_full, bgc_id) if status == "COMPLETE" else ""
        # Truncate to cell-safe length (Excel cells cap at 32767 chars; we stay well under)
        lay_snippet = lay_snippet[:800]
        ferm_snippet = ferm_snippet[:400]

        _append_row_by_header(_e1_ws, {
            "strain": strain_id,
            "BGC_ID": bgc_id,
            "length_kb": length_kb,
            "products": products[:120],
            "subprograms": subprograms[:80],
            "mode_b_status": status,
            "analysis_platform": "Sapote/Claude",
            "date": bgc_rec.get("timestamp", today)[:10] if status == "COMPLETE" else today,
            "report_file": report_file,
            "layperson_summary": lay_snippet,
            "fermentation_note": ferm_snippet,
        })
        n_written += 1
        if status == "COMPLETE":
            n_complete += 1
        else:
            n_pending += 1

    # Update A4_Completeness_Audit E1_mode_b cell for this strain
    e1_audit_status = (
        "COMPLETE" if n_pending == 0 and n_complete > 0
        else f"IN_PROGRESS_{n_complete}of{n_written}"
        if n_complete > 0 else "JUDGMENT_PENDING"
    )
    if "A4_Completeness_Audit" in wb.sheetnames:
        _a4 = wb["A4_Completeness_Audit"]
        _cm4 = _col_map(_a4)
        _e1_col = _cm4.get("E1_mode_b")
        _strain_col = _cm4.get("strain") or 1
        if _e1_col:
            for _r in range(2, _a4.max_row + 1):
                if _a4.cell(row=_r, column=_strain_col).value == strain_id:
                    _a4.cell(row=_r, column=_e1_col).value = e1_audit_status
                    break

    # Atomic save
    atomic_save_workbook_safely(wb, wb_path)

    return {
        "strain": strain_id,
        "bgcs_written": n_written,
        "bgcs_complete": n_complete,
        "bgcs_pending": n_pending,
        "e1_audit_status": e1_audit_status,
        "prior_rows_replaced": _e1_removed,
    }


def _strain_from_pkg(pkg: Path) -> str:
    """Infer strain ID from manifest in package dir."""
    m = pkg / "manifest.json"
    if m.exists():
        try:
            import json as _j
            return _j.loads(m.read_text(encoding="utf-8")).get("strain_id", pkg.name)
        except Exception:
            pass
    return pkg.name


# ---------------------------------------------------------------------------
# Group 2 Sapote judgment write-back functions (v9.7.71)
# ---------------------------------------------------------------------------
# Each function updates one or more master workbook sheets with Sapote judgment
# output. All follow the same pattern as update_e1_from_judgment:
#   1. Load workbook
#   2. Drop prior rows for this strain in the target sheet(s)
#   3. Write new rows
#   4. Update A4_Completeness_Audit where applicable
#   5. Atomic save (.tmp rename)
#
# Caller: Sapote (LLM judgment layer) after the relevant analysis step completes.
# ---------------------------------------------------------------------------

def update_c3c4_from_sapote(
    master_workbook_path: str | Path,
    strain_id: str,
    *,
    sapote_rank: int | str,
    sapote_score: float | str,
    sapote_composite: str = "",
    recommended_role: str = "",
) -> dict[str, Any]:
    """Update C3 and C4 with Sapote composite rank, score, and recommended role.

    Called after Sapote completes the cross-strain priority synthesis for this strain.
    sapote_rank and sapote_score are computed by Sapote after seeing all strains;
    they are cross-strain values, so Mamey cannot derive them at extraction time.

    Args:
        sapote_rank:      Integer rank of this strain among all project strains
                          (1 = highest priority). Can be a string like "1" or 1.
        sapote_score:     Numeric composite score (e.g. 87.5). Sapote-derived.
        sapote_composite: Free-text composite assessment (≤120 chars).
                          Example: "Priority A — 2 High leads, high novelty, MRSA-active"
        recommended_role: Strategic role for this strain in the project.
                          Example: "Lead compound strain — WAC cohort flagship"
    Returns summary dict.
    """
    import datetime as _dt
    import os as _os
    wb_path = Path(master_workbook_path)
    if not wb_path.exists():
        raise FileNotFoundError(f"Master workbook not found: {wb_path}")

    wb = load_workbook(wb_path)
    _ensure_canonical_headers(wb)
    from .workbook_dedup import drop_existing_strain

    today = _dt.date.today().isoformat()

    # Load existing C3/C4 rows BEFORE dropping to preserve deterministic fields.
    c3_existing: dict = {}
    c4_existing: dict = {}
    if "C3_Lead_Tier_Summary" in wb.sheetnames:
        ws = wb["C3_Lead_Tier_Summary"]
        cm = _col_map(ws)
        for r in range(2, ws.max_row + 1):
            if ws.cell(row=r, column=1).value == strain_id:
                c3_existing = {k: ws.cell(row=r, column=col).value for k, col in cm.items()}
                break
    if "C4_Strain_Decision_Table" in wb.sheetnames:
        ws = wb["C4_Strain_Decision_Table"]
        cm = _col_map(ws)
        strain_col = cm.get("strain") or 2
        for r in range(2, ws.max_row + 1):
            if ws.cell(row=r, column=strain_col).value == strain_id:
                c4_existing = {k: ws.cell(row=r, column=col).value for k, col in cm.items()}
                break

    # Drop existing rows. C4 needs explicit handling (strain is col 2 not col 1).
    # v9.7.335: scoped to C3/C4 — the unscoped call also wiped G2 (without restoring it), the
    # registry row and every BGC row for this strain.
    drop_existing_strain(wb, strain_id,
                         sheets=("C3_Lead_Tier_Summary", "C4_Strain_Decision_Table"))
    if "C4_Strain_Decision_Table" in wb.sheetnames:
        _c4ws = wb["C4_Strain_Decision_Table"]
        _c4cm = _col_map(_c4ws)
        _c4sc = _c4cm.get("strain") or 2
        _to_del = [r for r in range(_c4ws.max_row, 1, -1)
                   if _c4ws.cell(row=r, column=_c4sc).value == strain_id]
        for r in _to_del:
            _c4ws.delete_rows(r, 1)


    # Re-write C3 with enrichment
    c3_row = dict(c3_existing)
    c3_row["strain"] = strain_id
    c3_row["sapote_composite"] = (sapote_composite or "")[:120]
    c3_row["recommended_role"] = (recommended_role or "")[:200]
    _append_row_by_header(wb["C3_Lead_Tier_Summary"], c3_row)

    # Re-write C4 with enrichment
    c4_row = dict(c4_existing)
    c4_row["strain"] = strain_id
    c4_row["sapote_rank"] = sapote_rank
    c4_row["sapote_score"] = sapote_score
    c4_row["recommended_role"] = (recommended_role or "")[:200]
    _append_row_by_header(wb["C4_Strain_Decision_Table"], c4_row)

    atomic_save_workbook_safely(wb, wb_path)

    return {
        "strain": strain_id,
        "sapote_rank": sapote_rank,
        "sapote_score": sapote_score,
        "recommended_role": recommended_role,
        "sheets_updated": ["C3_Lead_Tier_Summary", "C4_Strain_Decision_Table"],
    }


def update_d3_from_sapote(
    master_workbook_path: str | Path,
    strain_id: str,
    promoted_pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update D3_RGGMCI_Promoted with Sapote-confirmed pair interpretations.

    Called after Sapote completes Mode B for the RG-GMCI anchor BGCs. Replaces the
    extraction-time PROMOTED_CANDIDATE_PENDING_SAPOTE rows with Sapote-confirmed
    evidence assessments.

    Each dict in promoted_pairs must contain:
        group_id:             e.g. "AS-XXX_RG01"
        evidence_basis:       Sapote-derived evidence summary (≤200 chars)
        claim_ceiling:        Updated claim ceiling after Mode B
        chemistry_consequence: Updated consequence string
        status:               e.g. "MODE_B_SUPPORTED" or "MODE_B_CONFIRMED"
        grade (optional):     RG-GMCI confidence grade
        fragments (optional): Pair string (e.g. "BGC001+BGC013")
    """
    import os as _os
    wb_path = Path(master_workbook_path)
    if not wb_path.exists():
        raise FileNotFoundError(f"Master workbook not found: {wb_path}")

    wb = load_workbook(wb_path)
    _ensure_canonical_headers(wb)

    # D3 is NOT in drop_existing_strain's PER_STRAIN list (strain is col 2, not col 1).
    # Drop D3 rows for this strain manually.
    if "D3_RGGMCI_Promoted" in wb.sheetnames:
        ws = wb["D3_RGGMCI_Promoted"]
        cm = _col_map(ws)
        strain_col = cm.get("strain") or 2
        to_del = [r for r in range(ws.max_row, 1, -1)
                  if ws.cell(row=r, column=strain_col).value == strain_id]
        for r in to_del:
            ws.delete_rows(r, 1)

    # Write updated rows
    for p in promoted_pairs:
        _append_row_by_header(wb["D3_RGGMCI_Promoted"], {
            "group_id":             p.get("group_id", f"{strain_id}_RG"),
            "strain":               strain_id,
            "grade":                p.get("grade", "HIGH_RG_GMCI"),
            "fragments":            p.get("fragments", ""),
            "evidence_basis":       (p.get("evidence_basis", ""))[:200],
            "claim_ceiling":        (p.get("claim_ceiling",
                "CB-homology reconstruction hypothesis; physical linkage unproven"))[:200],
            "chemistry_consequence": (p.get("chemistry_consequence", ""))[:120],
            "status":               p.get("status", "MODE_B_SUPPORTED"),
        })

    atomic_save_workbook_safely(wb, wb_path)

    return {
        "strain": strain_id,
        "pairs_written": len(promoted_pairs),
        "sheets_updated": ["D3_RGGMCI_Promoted"],
    }


def update_g1_from_sapote(
    master_workbook_path: str | Path,
    strain_id: str,
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update G1_Literature_Index with citations from a Sapote Literature Deep Dive.

    Called after Sapote runs a Literature Deep Dive on one or more BGCs for this
    strain. Appends (never replaces — a second call adds more citations) citation
    rows. De-duplicates on (strain, BGC_ID, doi) to prevent double-appending if
    called twice with overlapping citations.

    Each dict in citations must contain:
        BGC_ID:             e.g. "BGC001"
        track:              compound family / class (e.g. "bombyxamycin / azole-RiPP")
        citation:           PNAS-style formatted citation string (≤300 chars)
        doi:                DOI string (e.g. "10.1234/abc")
        evidence_purpose:   mechanism / clinical / biosynthesis / ecological / structural
        verification_status: Verified / Partial / Policy / GenBank
    """
    import os as _os
    wb_path = Path(master_workbook_path)
    if not wb_path.exists():
        raise FileNotFoundError(f"Master workbook not found: {wb_path}")

    wb = load_workbook(wb_path)
    _ensure_canonical_headers(wb)

    # G1 has (strain, BGC_ID) as key. De-duplicate on (strain, BGC_ID, doi, evidence_purpose).
    existing_keys: set[tuple] = set()
    if "G1_Literature_Index" in wb.sheetnames:
        ws = wb["G1_Literature_Index"]
        cm = _col_map(ws)
        sc = cm.get("strain") or 1
        bc = cm.get("BGC_ID") or 2
        dc = cm.get("doi") or 5
        epc = cm.get("evidence_purpose") or 6
        for r in range(2, ws.max_row + 1):
            s = ws.cell(row=r, column=sc).value
            b = ws.cell(row=r, column=bc).value
            d = ws.cell(row=r, column=dc).value
            ep = ws.cell(row=r, column=epc).value
            if s:
                existing_keys.add((str(s), str(b or ""), str(d or ""), str(ep or "")))

    written = 0
    for c in citations:
        key = (strain_id, str(c.get("BGC_ID", "")), str(c.get("doi", "")), str(c.get("evidence_purpose", "")))
        if key in existing_keys:
            continue   # skip exact duplicate
        _append_row_by_header(wb["G1_Literature_Index"], {
            "strain":              strain_id,
            "BGC_ID":              c.get("BGC_ID", ""),
            "track":               (c.get("track", ""))[:80],
            "citation":            (c.get("citation", ""))[:300],
            "doi":                 (c.get("doi", ""))[:100],
            "evidence_purpose":    c.get("evidence_purpose", ""),
            "verification_status": c.get("verification_status", "Partial"),
        })
        existing_keys.add(key)
        written += 1

    atomic_save_workbook_safely(wb, wb_path)

    return {
        "strain": strain_id,
        "citations_written": written,
        "citations_skipped_duplicate": len(citations) - written,
        "sheets_updated": ["G1_Literature_Index"],
    }


def update_g2_from_sapote(
    master_workbook_path: str | Path,
    strain_id: str,
    *,
    primary_role: str = "",
    manuscript_use: str = "",
) -> dict[str, Any]:
    """Update G2_Validation_Roles with Sapote strategic assessment.

    Called after Sapote completes the validation/strategic role assignment.
    Replaces the extraction-time placeholder row.

    Args:
        primary_role:    Sapote-assigned role (e.g. "lead compound strain",
                         "negative control", "ecological context strain")
        manuscript_use:  Planned manuscript role (e.g. "WAC cohort §3 lead — BGC001
                         feature strain; MRSA-active extract-level")
    """
    import os as _os
    wb_path = Path(master_workbook_path)
    if not wb_path.exists():
        raise FileNotFoundError(f"Master workbook not found: {wb_path}")

    wb = load_workbook(wb_path)
    _ensure_canonical_headers(wb)
    from .workbook_dedup import drop_existing_strain
    # v9.7.335: scoped — this used to clear the strain from all 18 per-strain sheets and restore
    # only G2, destroying the registry row and every BGC row for the strain.
    drop_existing_strain(wb, strain_id, sheets=("G2_Validation_Roles",))

    _append_row_by_header(wb["G2_Validation_Roles"], {
        "strain":        strain_id,
        "primary_role":  (primary_role or "")[:120],
        "manuscript_use": (manuscript_use or "")[:300],
    })

    atomic_save_workbook_safely(wb, wb_path)

    return {
        "strain": strain_id,
        "primary_role": primary_role,
        "manuscript_use": manuscript_use,
        "sheets_updated": ["G2_Validation_Roles"],
    }

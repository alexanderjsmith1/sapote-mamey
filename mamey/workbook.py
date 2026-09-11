from __future__ import annotations
from pathlib import Path
import json
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from .crosswalk import build_bgc_crosswalk, assembly_locator
from .models import MameyRun
from .scoring import bgc_count_summary
from .xlsx_determinism import atomic_save_workbook_safely

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(color="FFFFFF", bold=True)

def _style_sheet(ws):
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for col in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col)].width = 22

_DICT_SHEET_LIST_CAP = 300  # max item_* rows per list in a Group/Key/Value detail dump


def _write_dict_sheet(wb, title, data, *, max_items: int = _DICT_SHEET_LIST_CAP):
    ws = wb.create_sheet(title)
    ws.append(["Group", "Key", "Value"])
    def rec(prefix, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                rec(f"{prefix}.{k}" if prefix else str(k), v)
        elif isinstance(obj, list):
            n = len(obj)
            ws.append([prefix, "list_count", n])
            shown = min(n, max_items)
            for i, item in enumerate(obj[:max_items]):
                ws.append([prefix, f"item_{i+1}", str(item)[:1000]])
            if n > max_items:
                # v9.7.409 (DEEP_AUDIT2_workbook Finding 1): the sheet previously wrote the true
                # `list_count` (n) but only `max_items` item_* rows with NO marker — a shipped sheet
                # that states N and silently shows 300. Emit an explicit reconciling marker row so the
                # rows shown match the declared count. Deterministic (fixed cap). The full list still
                # lives in the sealed source CSV/JSON.
                ws.append([prefix, "list_truncated",
                           f"[truncated] showing {shown} of {n} items — "
                           f"full list in the sealed source CSV/JSON"])
        else:
            ws.append(["", prefix, str(obj)])
    rec("", data)
    _style_sheet(ws)


def _write_rggmci_sheets(wb, rggmci: dict):
    """Write structured RG-GMCI workbook tabs."""
    ranked_headers = [
        "pair", "bgc_a", "contig_a", "products_a", "edge_a",
        "bgc_b", "contig_b", "products_b", "edge_b",
        "rggmci_score", "rggmci_confidence", "supporting_references",
        "strong_supporting_references", "complete_or_chromosome_references",
        "good_geometry_references", "avg_min_identity", "max_protein_sum",
        "shared_reference_type_tokens", "shared_product_tokens", "best_sources",
        "interpretation_guard",
    ]
    ws = wb.create_sheet("RGGMCI_Ranked")
    ws.append(ranked_headers)
    for row in rggmci.get("ranked_pairs", []):
        ws.append([row.get(h, "") for h in ranked_headers])
    _style_sheet(ws)

    evidence_headers = [
        "pair", "bgc_a", "bgc_b", "ref", "source", "reference_type",
        "rank_a", "rank_b", "nprot_a", "nprot_b",
        "mean_identity_a", "mean_identity_b", "interval_a", "interval_b",
        "gap_locus_suffix", "overlap_locus_suffix", "adjacency_class",
        "shared_reference_type_tokens", "shared_product_tokens",
    ]
    ws = wb.create_sheet("RGGMCI_Evidence")
    ws.append(evidence_headers)
    for row in rggmci.get("evidence_rows", []):
        ws.append([row.get(h, "") for h in evidence_headers])
    _style_sheet(ws)

    summary_headers = ["Field", "Value"]
    ws = wb.create_sheet("RGGMCI_Summary")
    ws.append(summary_headers)
    for key in [
        "status", "algorithm", "pairing_scope", "reference_record_count",
        "clusterblast_txt_file_count", "pairs_total", "high_pairs",
        "moderate_pairs", "claim_safety",
    ]:
        ws.append([key, rggmci.get(key, "")])
    _style_sheet(ws)


def _write_cover_sheet(wb, run: "MameyRun") -> None:
    """D1: Cover sheet — first tab a collaborator sees, explains all other tabs in one sentence."""
    from .scoring import bgc_count_summary
    ws = wb.active
    ws.title = "README"
    counts = bgc_count_summary(run.bgcs)
    GREEN = PatternFill("solid", fgColor="2C5F2E")
    WHITE_BOLD = Font(color="FFFFFF", bold=True)
    BOLD = Font(bold=True)
    GREY = PatternFill("solid", fgColor="F0F0F0")

    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 55

    ws["A1"] = f"Sapote-Mamey Package — {run.context.strain_id}"
    ws["A1"].font = Font(color="FFFFFF", bold=True, size=13)
    ws["A1"].fill = GREEN

    meta = [
        ("Strain",          run.context.strain_id),
        ("Taxonomy",        run.context.taxonomy or "not verified"),
        ("Source",          run.context.source or "not supplied"),
        ("Mode",            run.context.analysis_mode),
        ("Mamey version",   run.context.version),
        ("Raw BGCs",        counts["raw"]),
        ("Corrected BGCs",  counts["corrected"]),
        ("Assembly tier",   counts["assembly_tier"]),
    ]
    for i, (label, val) in enumerate(meta, 3):
        ws[f"A{i}"] = label
        ws[f"A{i}"].font = BOLD
        ws[f"B{i}"] = val
        if i % 2 == 0:
            ws[f"A{i}"].fill = GREY
            ws[f"B{i}"].fill = GREY

    row = len(meta) + 4
    ws[f"A{row}"] = "⏳ JUDGMENT PENDING"
    ws[f"A{row}"].font = Font(bold=True, color="856404")
    ws[f"B{row}"] = ("This workbook contains deterministic extraction data only. "
                     "Mode B cards, ecology, and bench guidance require the Sapote judgment layer: "
                     "upload manifest.json to Claude and type 'Run full Sapote analysis on "
                     + run.context.strain_id + "'.")
    row += 2

    ws[f"A{row}"] = "WHAT'S IN EACH TAB"
    ws[f"A{row}"].font = WHITE_BOLD
    ws[f"A{row}"].fill = GREEN
    row += 1

    tab_guide = [
        ("Strain_Summary",           "Assembly metrics, BGC counts, corrected count, assembly tier"),
        ("BGC_Crosswalk",            "Maps Mamey BGC IDs to antiSMASH region labels and node/contig IDs"),
        ("BGC_Inventory",            "Full per-BGC row: coordinates, architecture grade, KCB, RiQ"),
        ("KCB_RiQ_Sweep",            "Known-cluster BLAST scores and RiQ values — similarity only"),
        ("Architecture_Confidence",  "A-E architecture grade and rationale per BGC"),
        ("Triage_First_Board",       "Pre-ranked BGCs: AB/AF/novelty scores, lead tier, claim confidence"),
        ("First_Pass_Scan_Status",   "Pass/fail status of all source-derived scans"),
        ("RGGMCI_Ranked",            "Cross-contig reconstruction pairs ranked by rescue confidence"),
        ("RGGMCI_Evidence",          "Evidence rows supporting each RG-GMCI pair"),
        ("RGGMCI_Summary",           "RG-GMCI run summary statistics"),
        ("FLBR_LMPKS",               "Fragment/LMPKS rescue scan results"),
        ("Chitinase_CGAD",           "Chitin/glycan-active defence scan (antifungal context gate)"),
        ("TFBS_Motif_Scan",          "Transcription factor binding site motifs"),
        ("bldA_TTA",                 "bldA/TTA codon gate per BGC"),
        ("Resistance_SelfProtection","Resistance-gene self-protection tiers"),
        ("CCTT_Source_Derived",      "Context-corroborated token triggers per BGC"),
        ("Resistance_Gene_Summary",  "Genome-wide resistance gene counts"),
        ("UMED_Maturation",          "Maturation-enzyme gap flags"),
        ("EFLS_Linkage",             "EFLS flank linkage evidence"),
        ("Per_BGC_DSS",              "Diagnostic signal score breakdown per BGC"),
        ("Cassette_Registry",        "Cassette marker registry hits"),
        ("QS_Signals",               "Quorum-sensing signal BGC routing"),
        # AUDIT_371: 20 real sheets had no entry here (confirmed by diffing every
        # wb.create_sheet(...) call against this list) -- added below, grouped by feature area,
        # in emission order. Descriptions for the P-MPG/P-AS-TABLES/P-LWC/SM-P1-008 sheets are
        # derived from their own explicit column headers a few lines up in this file (high
        # confidence); descriptions for the raw _write_dict_sheet scan-detail tabs (RGGMCI_Detail
        # through Glycosylation_Arms) are generic since this file does not define their internal
        # structure -- worth a domain reviewer sanity check on wording before fold.
        ("MIBiG_Per_Gene",           "Per-gene MIBiG BLAST evidence: query/subject gene, accession, %identity/coverage — similarity only"),
        ("MIBiG_Convergence",        "Per-BGC MIBiG reference convergence: dominant reference, convergence tier, class concordance"),
        ("MIBiG_Profile",            "Per-BGC MIBiG interpretability profile: recognizable-gene fraction, dominant reference"),
        ("antiSMASH_Modules",        "Structured antiSMASH PKS/NRPS module table (P-AS-TABLES)"),
        ("antiSMASH_RiPP_Motifs",    "Structured antiSMASH RiPP precursor/motif table"),
        ("antiSMASH_Motifs",         "Structured antiSMASH generic motif table"),
        ("antiSMASH_RREfinder",      "Structured RREfinder RiPP recognition-element table"),
        ("antiSMASH_HMM",            "Structured antiSMASH HMM domain-hit table"),
        ("P_LWC_Trial",              "Length-weighted capacity — TRIAL sensitivity metric per BGC, excluded from scoring"),
        ("P_LWC_Summary",            "P-LWC trial run summary statistics"),
        ("Triage_Board",             "BGC_ID-keyed triage board — SM-P1-008 ChatGPT-safe schema twin of Triage_First_Board"),
        ("WetLab_Decision_Matrix",   "Primary-axis wet-lab priority view: antibacterial vs antifungal routing per BGC"),
        ("Mode_B_Summary",           "Placeholder Mode-B status per BGC — judgment pending, filled by the Sapote layer"),
        ("RGGMCI_Detail",            "Raw per-field RG-GMCI scan dump (companion to structured RGGMCI_Ranked/Evidence/Summary)"),
        ("Regulators",               "Regulatory-gene scan detail per BGC"),
        ("Transporters",             "Transporter-gene scan detail per BGC"),
        ("Domain_Architecture_Detail","Per-BGC domain-count scan detail"),
        ("Resistance_Tiers",         "Resistance-gene tier (T1/T2/T3/NULL) per BGC"),
        ("WetLab_Class_Rows",        "Class-level wet-lab routing detail"),
        ("Glycosylation_Arms",       "Glycosylation tailoring-arm scan detail per BGC"),
    ]
    for tab, desc in tab_guide:
        ws[f"A{row}"] = tab
        ws[f"B{row}"] = desc
        if row % 2 == 0:
            ws[f"A{row}"].fill = GREY
            ws[f"B{row}"].fill = GREY
        row += 1

    ws.freeze_panes = "A3"


def write_per_strain_workbook(run: MameyRun, path: str | Path) -> None:
    wb = Workbook()
    _write_cover_sheet(wb, run)
    ws = wb.create_sheet("Strain_Summary")
    counts = bgc_count_summary(run.bgcs)
    ws.append(["Field", "Value"])
    for row in [("Strain", run.context.strain_id), ("Mamey version", run.context.version), ("Mode", run.context.analysis_mode), ("Genome bp", run.assembly.genome_bp), ("Contigs", run.assembly.contigs), ("N50", run.assembly.n50), ("GC pct", run.assembly.gc_pct), ("Raw BGCs", counts["raw"]), ("Interior", counts["interior"]), ("Edge", counts["edge"]), ("Full-contig", counts["full_contig"]), ("Corrected BGC count", counts["corrected"]), ("Assembly tier", counts["assembly_tier"])]:
        ws.append(list(row))
    _style_sheet(ws)

    ws = wb.create_sheet("BGC_Crosswalk")
    ws.append(["Node/contig ID", "antiSMASH region", "Assembly locator", "BGC", "User-facing label", "Contig", "Region number", "Source GBK", "Start", "End", "Contig length", "Edge", "Products"])
    for b in run.bgcs:
        ws.append([b.node_id or b.contig, b.antismash_region, assembly_locator(b), b.bgc_id, b.user_label, b.contig, b.region_number, b.source_gbk, b.start, b.end, b.contig_length, b.edge_status, "; ".join(b.products)])
    _style_sheet(ws)

    ws = wb.create_sheet("BGC_Inventory")
    ws.append(["Node/contig ID", "antiSMASH region", "Assembly locator", "BGC", "User-facing label", "Contig", "Region", "Source GBK", "Start", "End", "Length kb", "Edge", "Arch", "Arch rationale", "Products", "KCB top", "KCB score", "KCB evidence state", "KCB protein hits", "MIBiG hits", "RiQ", "RiQ label"])
    for b in run.bgcs:
        ws.append([b.node_id or b.contig, b.antismash_region, assembly_locator(b), b.bgc_id, b.user_label, b.contig, b.region_number, b.source_gbk, b.start, b.end, b.length_kb, b.edge_status, b.architecture_confidence, b.architecture_rationale, "; ".join(b.products), b.kcb_top, b.kcb_cumulative, getattr(b, "kcb_evidence_state", "UNKNOWN_KCB"), b.kcb_protein_hits, "; ".join(b.mibig_hits), b.riq_score, b.riq_label])
    _style_sheet(ws)

    ws = wb.create_sheet("KCB_RiQ_Sweep")
    ws.append(["BGC", "KCB top", "KCB cumulative", "KCB evidence state", "Protein hits", "MIBiG hits", "RiQ score", "RiQ label"])
    for b in run.bgcs:
        ws.append([b.bgc_id, b.kcb_top, b.kcb_cumulative, getattr(b, "kcb_evidence_state", "UNKNOWN_KCB"), b.kcb_protein_hits, "; ".join(b.mibig_hits), b.riq_score, b.riq_label])
    _style_sheet(ws)

    # P-MPG: per-gene MIBiG evidence and interpretability profile.
    mpg = (run.source_scans.mibig_per_gene if run.source_scans else {}) or {}
    ws = wb.create_sheet("MIBiG_Per_Gene")
    mpg_headers = ["BGC", "Query_gene", "Subject_gene", "MIBiG_accession", "MIBiG_compound",
                   "Reference_type", "%identity", "%coverage_raw",
                   "%coverage_interpretation", "Coverage_QC_flag", "BLAST_score", "Evalue",
                   "Reference_rank", "Reference", "Source_file"]
    ws.append(mpg_headers)
    for bid, hits in sorted((mpg.get("per_gene_mibig") or {}).items()):
        for h in hits:
            ws.append([bid, h.get("query_gene", ""), h.get("subject_gene", ""), h.get("mibig_accession", ""),
                       h.get("mibig_compound", ""), h.get("reference_type", ""), h.get("pct_identity", ""),
                       h.get("pct_coverage", ""), h.get("pct_coverage_interpretation", ""),
                       h.get("coverage_qc_flag", ""), h.get("blast_score", ""), h.get("evalue", ""),
                       h.get("reference_rank", ""), h.get("reference", ""), h.get("source_file", "")])
    _style_sheet(ws)
    ws = wb.create_sheet("MIBiG_Convergence")
    convergence_headers = [
        "BGC", "Products", "Boundary", "MIBiG_accession", "MIBiG_compound",
        "Reference_type", "Distinct_query_genes", "Distinct_subject_genes",
        "Query_gene_count_total", "Recognizable_query_gene_count",
        "Query_gene_share", "Recognizable_gene_share", "Median_identity",
        "Median_coverage_raw", "Median_coverage_interpretation", "Coverage_QC_flag",
        "Minimum_identity", "Best_reference_rank",
        "Source_rows", "Class_concordance", "Convergence_tier",
        "Convergence_tier_basis", "Convergence_rank", "Dominant_reference",
        "Dominance_status", "Runner_up_MIBiG_accession",
        "Runner_up_MIBiG_compound", "Runner_up_distinct_query_genes",
        "Dominance_gene_margin", "Claim_safety",
    ]
    ws.append(convergence_headers)
    convergence_keys = [
        "bgc_id", "products", "boundary", "mibig_accession", "mibig_compound",
        "reference_type", "distinct_query_genes", "distinct_subject_genes",
        "query_gene_count_total", "recognizable_query_gene_count",
        "query_gene_share", "recognizable_gene_share", "median_pct_identity",
        "median_pct_coverage", "median_pct_coverage_interpretation",
        "coverage_qc_flag", "minimum_pct_identity", "best_reference_rank",
        "source_row_count", "class_concordance", "convergence_tier",
        "convergence_tier_basis", "convergence_rank", "dominant_reference",
        "dominance_status", "runner_up_mibig_accession",
        "runner_up_mibig_compound", "runner_up_distinct_query_genes",
        "dominance_gene_margin", "claim_safety",
    ]
    for row in mpg.get("mibig_convergence") or []:
        ws.append([row.get(key, "") for key in convergence_keys])
    _style_sheet(ws)
    ws = wb.create_sheet("MIBiG_Profile")
    headers = ["BGC", "Query_gene_count", "Recognizable_gene_count",
               "Recognizable_gene_fraction", "Recognizable_min_identity",
               "Median_identity", "Distinct_refs", "Interpretation_class",
               "Dominant_MIBiG_accession", "Dominant_MIBiG_compound",
               "Dominant_distinct_query_genes", "Dominant_convergence_tier",
               "Report_only_contract"]
    ws.append(headers)
    for bid, row in sorted((mpg.get("bgc_mibig_profile") or {}).items()):
        ws.append([row.get("bgc_id", bid), row.get("query_gene_count", ""), row.get("recognizable_gene_count", ""),
                   row.get("recognizable_gene_fraction", row.get("mibig_gene_fraction", "")),
                   row.get("recognizable_min_pct_identity", ""), row.get("median_pct_identity", ""),
                   row.get("distinct_mibig_refs", ""), row.get("interpretation_class", ""),
                   row.get("dominant_mibig_accession", ""), row.get("dominant_mibig_compound", ""),
                   row.get("dominant_distinct_query_genes", ""), row.get("dominant_convergence_tier", ""),
                   row.get("report_only_contract", "")])
    _style_sheet(ws)

    # P-AS-TABLES: stable normalized evidence sheets; full source details remain
    # serialized in the JSON cells named by the schema.
    ast = (run.source_scans.antismash_structured if run.source_scans else {}) or {}
    from .antismash_tables import TABLE_COLUMNS
    for title, key in [
        ("antiSMASH_Modules", "modules"),
        ("antiSMASH_RiPP_Motifs", "ripp_motifs"),
        ("antiSMASH_Motifs", "motifs"),
        ("antiSMASH_RREfinder", "rrefinder"),
        ("antiSMASH_HMM", "hmm"),
    ]:
        rows = ast.get(key) or []
        ws = wb.create_sheet(title)
        cols = TABLE_COLUMNS[key]
        ws.append(cols)
        for r in rows:
            ws.append([json.dumps(r.get(c), sort_keys=True) if isinstance(r.get(c), (dict, list)) else r.get(c, "") for c in cols])
        _style_sheet(ws)

    # P-LWC remains a trial-only sensitivity surface and is excluded from
    # scoring.  Keeping it in the workbook makes the several-strain trial
    # auditable without turning it into a headline metric.
    from .length_weighted import length_weighted_profile, summary as lwc_summary
    lwc_rows = length_weighted_profile(run.bgcs)
    ws = wb.create_sheet("P_LWC_Trial")
    lwc_columns = list(lwc_rows[0]) if lwc_rows else ["bgc_id"]
    ws.append(lwc_columns)
    for row in lwc_rows:
        ws.append([row.get(column, "") for column in lwc_columns])
    _style_sheet(ws)
    ws = wb.create_sheet("P_LWC_Summary")
    ws.append(["Field", "Value"])
    for key, value in lwc_summary(lwc_rows).items():
        ws.append([key, value])
    _style_sheet(ws)

    ws = wb.create_sheet("Architecture_Confidence")
    ws.append(["BGC", "Grade", "Rationale"])
    for b in run.bgcs:
        ws.append([b.bgc_id, b.architecture_confidence, b.architecture_rationale])
    _style_sheet(ws)

    # AUDIT_374 fix: Standing_rule / Corrected_rank were missing from both triage sheets
    # below, so a standing-rule-excluded BGC (saccharide-exclusion, etc.) rendered with the SAME
    # "Inventory" lead_tier text as a genuinely-ranked, merely-low-scoring housekeeping BGC
    # (e.g. real AS-XXX package: BGC003/BGC038 are Inventory-tier WITH a real corrected_rank;
    # BGC002/BGC008/... are Inventory-tier but standing_rule_flag="saccharide-exclusion" and
    # corrected_rank=None) -- a reader of this sheet alone cannot tell which is which. This is
    # the same "excluded-BGC leak" pattern already found in models.py/_bgc_record(),
    # compile_report.py/_key_findings(), and widget_deliverable.py/_join_rows() this session;
    # master_workbook.py's own DAPR boards already carry these two columns (lines ~205-206,
    # 509-510) -- this sheet just never adopted the same fix.
    ws = wb.create_sheet("Triage_First_Board")
    ws.append(["BGC", "AB score", "AF score", "Novelty", "Lead tier", "Standing rule",
               "Corrected rank", "Claim confidence", "Rationale"])
    for t in run.triage:
        ws.append([t.bgc_id, t.ab_score, t.af_score, t.novelty_score, t.lead_tier,
                   t.standing_rule_flag or "", t.corrected_rank, t.claim_confidence, t.rationale])
    _style_sheet(ws)

    # SM-P1-008 / ChatGPT-safe workbook-gate compatibility sheets (v9.7.128).
    # The validator contract names these sheets explicitly; keep the node-first user-facing
    # sheets above, but also emit stable BGC_ID-keyed sheets so strict validation does not
    # falsely fail a populated workbook (the node-first workbook schema-mismatch defect).
    _bgc_by_id = {b.bgc_id: b for b in run.bgcs}

    ws = wb.create_sheet("Triage_Board")
    ws.append(["BGC_ID", "Assembly_Locator", "AB_score", "AF_score", "Novelty_score",
               "Lead_tier", "Standing_rule", "Corrected_rank", "Claim_confidence", "Rationale"])
    for t in run.triage:
        b = _bgc_by_id.get(t.bgc_id)
        ws.append([t.bgc_id, assembly_locator(b) if b else "", t.ab_score, t.af_score,
                   t.novelty_score, t.lead_tier, t.standing_rule_flag or "", t.corrected_rank,
                   t.claim_confidence, t.rationale])
    _style_sheet(ws)

    ws = wb.create_sheet("WetLab_Decision_Matrix")
    ws.append(["BGC_ID", "Assembly_Locator", "Primary_axis", "Priority_score",
               "Lead_tier", "Claim_confidence", "Decision_status", "Rationale"])
    for t in run.triage:
        b = _bgc_by_id.get(t.bgc_id)
        primary_axis = "Antifungal" if (t.af_score or 0) > (t.ab_score or 0) else "Antibacterial"
        priority_score = max(t.ab_score or 0, t.af_score or 0)
        ws.append([t.bgc_id, assembly_locator(b) if b else "", primary_axis, priority_score,
                   t.lead_tier, t.claim_confidence, "MAMEY_EXTRACTION_TRIAGE", t.rationale])
    _style_sheet(ws)

    ws = wb.create_sheet("Mode_B_Summary")
    ws.append(["BGC_ID", "Assembly_Locator", "Mode_B_status", "Sections_expected",
               "Sapote_judgment_status", "Notes"])
    for b in run.bgcs:
        ws.append([b.bgc_id, assembly_locator(b), "JUDGMENT_PENDING", "1-20",
                   "not_run_in_mamey_extraction",
                   "Placeholder row for workbook completeness gate; Sapote fills/updates judgment."])
    _style_sheet(ws)

    ws = wb.create_sheet("First_Pass_Scan_Status")
    ws.append(["Scan", "State", "Detail"])
    # scan_status is {"scans": [(name, state, detail), ...], "evidence_channels": {...}} —
    # iterate the scans list (matching master_workbook.py), NOT .items() over the top-level dict.
    for scan_name, state, detail in run.scan_status.get("scans", []):
        ws.append([scan_name, state, detail])
    _style_sheet(ws)

    if run.source_scans:
        _write_rggmci_sheets(wb, run.source_scans.rggmci)
        for title, data in [("FLBR_LMPKS", run.source_scans.flbr), ("RGGMCI_Detail", run.source_scans.rggmci), ("Chitinase_CGAD", run.source_scans.chitinase), ("TFBS_Motif_Scan", run.source_scans.tfbs), ("bldA_TTA", run.source_scans.blda_tta), ("Regulators", run.source_scans.regulators), ("Transporters", run.source_scans.transporters), ("Resistance_SelfProtection", run.source_scans.resistance), ("CCTT_Source_Derived", run.source_scans.cctt), ("Resistance_Gene_Summary", run.resistance_gene_summary()), ("Cassette_Registry", run.source_scans.cassettes), ("UMED_Maturation", run.source_scans.umed), ("EFLS_Linkage", run.source_scans.efls), ("Domain_Architecture_Detail", run.source_scans.domain_architecture), ("Resistance_Tiers", run.source_scans.resistance_tiers), ("WetLab_Class_Rows", run.source_scans.wetlab_rows), ("QS_Signals", run.source_scans.qs_signals), ("Glycosylation_Arms", run.source_scans.glycosylation_arms), ("Per_BGC_DSS", run.source_scans.per_bgc_dss)]:
            _write_dict_sheet(wb, title, data)

    atomic_save_workbook_safely(wb, path, canonicalize=True)

def _ensure(wb, sheet):
    if sheet not in wb.sheetnames:
        wb.create_sheet(sheet)
    return wb[sheet]

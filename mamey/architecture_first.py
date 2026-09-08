#!/usr/bin/env python3
"""
architecture_first.py — Sapote-Mamey v9.7.107 patch (v2.2)  # version-sync-ok

Fixes KCB confirmation bias by enforcing architecture-first assessment.

v2 changes over v1:
  - Terpene, T2PKS, NI-siderophore, butyrolactone, ectoine, NAPAA,
    mycofactocin, DUF692-RiPP, thiopeptide, carotenoid detection added
  - PTM check uses single-protein KS+AMP test (not gene count)
  - Standalone AT heuristic checks for AT-less KS megasynthases
  - Boundary-aware confidence adjustment (Edge/Full-contig → -1 tier)
  - Biosynthetic-core-weighted KCB coverage
  - MIBiG class-tag mapping instead of compound-name-only map
  - UNKNOWN architecture + strong KCB → architecture defers to KCB
  - Module count uses PKS vs NRPS divisors
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Set
from enum import Enum


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class PathwayType(Enum):
    TRANS_AT_PKS = "trans-AT PKS"
    CIS_AT_PKS = "cis-AT T1PKS"
    NRPS = "NRPS"
    PKS_NRPS_HYBRID = "PKS/NRPS hybrid"
    TRANS_AT_HYBRID = "trans-AT PKS/NRPS hybrid"
    T2PKS = "T2PKS (aromatic polyketide)"
    T3PKS = "T3PKS (chalcone/stilbene)"
    LANTHIPEPTIDE = "lanthipeptide RiPP"
    LASSOPEPTIDE = "lassopeptide RiPP"
    LAP = "LAP (linear azol(in)e-containing peptide)"
    THIOPEPTIDE = "thiopeptide RiPP"
    RANTHIPEPTIDE = "ranthipeptide/SCIFF RiPP"
    MYCOFACTOCIN = "mycofactocin redox-cofactor RiPP"
    DUF692_RIPP = "DUF692-metalloenzyme RiPP"
    OTHER_RIPP = "RiPP (unclassified)"
    TERPENE_CYCLIZED = "cyclized terpene"
    TERPENE_LINEAR = "linear isoprenoid / terpene-precursor"
    HOPANOID = "hopanoid triterpene"
    CAROTENOID = "carotenoid"
    NI_SIDEROPHORE = "NIS siderophore"
    NRPS_SIDEROPHORE = "NRPS-dependent siderophore"
    BUTYROLACTONE = "butyrolactone autoregulator"
    ECTOINE = "ectoine compatible solute"
    NAPAA = "NAPAA poly-amino acid"
    NUCLEOSIDE = "nucleoside"
    INDOLOCARBAZOLE = "indolocarbazole"
    PTM = "PTM (polycyclic tetramate macrolactam)"
    BETALACTONE = "betalactone"
    PHOSPHONATE = "phosphonate"
    AMINOGLYCOSIDE = "aminoglycoside"
    PRIMARY_METABOLISM = "primary metabolism (not a specialized metabolite)"
    UNKNOWN = "unknown"


class Concordance(Enum):
    CONCORDANT = "concordant"
    DISCORDANT = "discordant"
    WEAK_SIGNAL = "weak_signal"
    NO_KCB = "no_kcb"
    ARCHITECTURE_DEFERS = "architecture_defers"  # UNKNOWN arch + strong KCB


class BoundaryStatus(Enum):
    INTERIOR = "Interior"
    EDGE = "Edge"
    FULL_CONTIG = "Full-contig"


# ══════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════

@dataclass
class GeneClassification:
    """Per-gene classification used internally."""
    locus_tag: str
    aa_length: int
    domains: str
    is_megasynthase: bool = False      # >800 aa with KS or AMP-binding
    has_ks: bool = False
    has_amp: bool = False
    has_cond: bool = False
    has_at_embedded: bool = False      # AT domain IN a megasynthase (cis-AT)
    has_pcp: bool = False
    has_acp: bool = False
    is_biosynthetic_core: bool = False  # KS, AMP, condensation, cyclase, etc.
    is_t2pks_ks: bool = False           # T2PKS-specific KS (t2ks, t2clf, CLF)


@dataclass
class ArchitectureReport:
    """Result of architecture-first assessment."""
    pathway_type: PathwayType
    confidence: str                     # HIGH, MEDIUM, LOW
    confidence_raw: str = ""            # before boundary adjustment
    boundary_status: str = ""
    assembly_tier: str = "UNKNOWN"      # CUT B: GOOD/MODERATE/POOR/VERY_POOR — gates the edge penalty
    finishing_candidate: bool = False   # CUT B: intact-core Edge on a POOR assembly (flag, not downgrade)
    n_megasynthases: int = 0
    total_megasynthase_aa: int = 0
    n_modules_est: int = 0
    n_pks_modules_est: int = 0
    n_nrps_modules_est: int = 0
    is_iterative: bool = False
    is_collinear: bool = False
    # Diagnostic markers (bool + detail)
    has_standalone_at: bool = False
    has_fkbh: bool = False
    has_epimerization: bool = False
    has_te: bool = False
    has_halogenase: bool = False
    has_lanc: bool = False
    has_ycao: bool = False
    has_ssf: bool = False              # ranthipeptide/SCIFF
    has_asn_synthase: bool = False
    has_trud: bool = False
    has_epsp: bool = False
    has_aph: bool = False
    has_terpene_cyclase: bool = False
    has_sqhop_cyclase: bool = False
    has_polyprenyl_synt: bool = False
    has_lycopene_cyclase: bool = False
    has_phytoene_synt: bool = False
    has_iuca_iucc: bool = False
    has_afsa: bool = False
    has_ectoine_synth: bool = False
    has_duf3516: bool = False          # NAPAA
    has_duf692: bool = False           # metalloenzyme RiPP
    has_indsynth: bool = False         # indolocarbazole synthase
    has_tra_ks: bool = False           # tra_KS trans-AT ketosynthase found
    has_t2pks: bool = False            # T2PKS-specific annotations found
    has_tigr02109: bool = False        # mycofactocin radical SAM
    has_chal_sti_synt: bool = False    # T3PKS
    has_pg_binding_ykud: bool = False  # peptidoglycan → primary metab
    has_pep_utilizer: bool = False     # betalactone
    has_biotin_carboxylase: bool = False
    has_lysr_oxygenase: bool = False   # catecholate siderophore
    has_chorismate_bind: bool = False  # DHB → catecholate siderophore
    # v2.2 additions
    has_spasm: bool = False            # ranthipeptide radical SAM
    has_tigr03962: bool = False        # ranthipeptide-specific TIGR
    has_lasso_rre: bool = False        # lassopeptide RRE
    has_nikj: bool = False             # nucleoside (nikkomycin J)
    has_phzb: bool = False             # phenazine biosynthesis
    diagnostic_markers: List[str] = field(default_factory=list)
    reasoning: str = ""
    # Internal: classified genes for coverage weighting
    gene_classifications: List[GeneClassification] = field(default_factory=list)


@dataclass
class ConcordanceResult:
    """Result of KCB concordance check."""
    concordance: Concordance
    kcb_compound: str = ""
    kcb_coverage_pct: float = 0.0
    kcb_biosynthetic_coverage_pct: float = 0.0  # weighted by core genes
    kcb_class: str = ""
    architecture_class: str = ""
    conflict_detail: str = ""


@dataclass
class FinalAssignment:
    """Final product class assignment."""
    product_class: str
    source: str
    confidence: str
    kcb_note: str
    betalactone_overcall_suspected: bool = False  # B3: betalactone arch call + terpene KCB anchor


# ══════════════════════════════════════════════════════════════
# DOMAIN KEYWORD SETS
# ══════════════════════════════════════════════════════════════

# Domains that mark a gene as "biosynthetic core" for coverage weighting
BIOSYNTHETIC_CORE_DOMAINS = {
    'PKS_KS', 'ketoacyl-synt', 'Ketoacyl-synt', 'Ketoacyl-synt_C',
    'KAsynt_C_assoc', 'AMP-binding', 'Condensation', 'Chal_sti_synt',
    'Terpene_syn_C_2', 'SQHop_cyclase_C', 'polyprenyl_synt',
    'Lycopene_cycl', 'SQS_PSY', 'IucA_IucC', 'Ectoine_synth',
    'AfsA', 'LANC_like', 'Lant_dehydr_N', 'Lant_dehydr_C',
    'YcaO', 'Polyketide_cyc', 'p450', 'Trp_halogenase',
    'Radical_SAM', 'DUF692', 'Asn_synthase',
}

# Keywords (substring match) for KS domains
KS_KEYWORDS = ('PKS_KS', 'ketoacyl-synt', 'Ketoacyl-synt', 'KAsynt_C_assoc', 'tra_KS')

# Keywords for AT domains
AT_KEYWORDS = ('Acyl_transf_1', 'PKSI-AT', 'Acyl_transf', 'PKS_AT')

# Keywords for AMP-binding / NRPS
AMP_KEYWORDS = ('AMP-binding', 'FAAL_cds', 'FAAL')

# Keywords for condensation domains
COND_KEYWORDS = ('Condensation', 'C1_LCL', 'C2_LCL', 'C2_DCL', 'C3_', 'C4_', 'C5_', 'C67_')

# T2PKS-specific keywords (antiSMASH annotations)
T2PKS_KS_KEYWORDS = ('t2ks', 't2clf', 'T2PKS_KS', 't2ks2')

# Terpene cyclase keywords
TERPENE_CYCLASE_KEYWORDS = ('Terpene_syn_C_2',)
SQHOP_KEYWORDS = ('SQHop_cyclase_C',)
POLYPRENYL_KEYWORDS = ('polyprenyl_synt',)
LYCOPENE_KEYWORDS = ('Lycopene_cycl',)
PHYTOENE_KEYWORDS = ('SQS_PSY',)


# ══════════════════════════════════════════════════════════════
# HELPER: classify a single gene
# ══════════════════════════════════════════════════════════════

def _classify_gene(g: Dict) -> GeneClassification:
    """Classify a single gene by its domain content."""
    aa = int(g.get('aa_length', 0) or 0)
    doms = str(g.get('sec_met_domains', '') or '')
    lt = g.get('locus_tag', '')

    gc = GeneClassification(locus_tag=lt, aa_length=aa, domains=doms)

    gc.has_ks = any(kw in doms for kw in KS_KEYWORDS)
    gc.is_t2pks_ks = any(kw.lower() in doms.lower() for kw in T2PKS_KS_KEYWORDS)
    gc.has_amp = any(kw in doms for kw in AMP_KEYWORDS)
    gc.has_cond = any(kw in doms for kw in COND_KEYWORDS)
    gc.has_pcp = 'PP-binding' in doms or 'PCP' in doms
    gc.has_acp = 'PP-binding' in doms or 'ACP' in doms

    # Embedded AT: AT domain inside a protein that also has KS
    gc.has_at_embedded = gc.has_ks and any(kw in doms for kw in AT_KEYWORDS)

    # Megasynthase: >800 aa with KS or AMP-binding
    gc.is_megasynthase = (gc.has_ks or gc.has_amp) and aa > 800

    # Biosynthetic core: any domain from the core set
    gc.is_biosynthetic_core = any(d in doms for d in BIOSYNTHETIC_CORE_DOMAINS)

    return gc


# ══════════════════════════════════════════════════════════════
# STEP 1: Architecture Assessment (EXPANDED)
# ══════════════════════════════════════════════════════════════

def assess_architecture(genes: List[Dict],
                        boundary_status: str = "Interior") -> ArchitectureReport:
    """
    Assess pathway architecture from gene content alone.
    Does NOT look at KCB data. This is the KCB-blind step.

    genes: list of dicts with keys 'locus_tag', 'aa_length', 'sec_met_domains'
    boundary_status: "Interior", "Edge", or "Full-contig"
    """
    report = ArchitectureReport(
        pathway_type=PathwayType.UNKNOWN,
        confidence="LOW",
        boundary_status=boundary_status,
    )

    # ── Classify every gene ──
    classified = [_classify_gene(g) for g in genes]
    report.gene_classifications = classified

    megasynthases = [gc for gc in classified if gc.is_megasynthase]
    ks_genes = [gc for gc in classified if gc.has_ks]
    amp_genes = [gc for gc in classified if gc.has_amp]

    report.n_megasynthases = len(megasynthases)
    report.total_megasynthase_aa = sum(gc.aa_length for gc in megasynthases)

    # ── Scan for diagnostic markers ──
    for gc in classified:
        doms = gc.domains
        lt = gc.locus_tag
        aa = gc.aa_length

        # trans-AT diagnostics
        if 'tra_KS' in doms:
            report.has_tra_ks = True
            report.diagnostic_markers.append(
                f"tra_KS trans-AT ketosynthase ({lt}) — trans-AT diagnostic")
            # Don't set has_standalone_at here; tra_KS is a KS, not an AT
            # But flag it for the trans-AT detection logic below

        if 'FkbH' in doms:
            report.has_fkbh = True
            report.diagnostic_markers.append(f"FkbH ({lt}) — trans-AT diagnostic")

        # Standalone AT: AT domain in a gene that does NOT have KS, and is <600 aa
        # This catches trans-AT discrete acyltransferases
        if any(kw in doms for kw in AT_KEYWORDS) and not gc.has_ks and aa < 600:
            # But exclude genes with only 'Acyl_transf_3' (acyltransferase tailoring)
            # — only flag if it matches 'Acyl_transf_1' or 'PKSI-AT'
            if 'Acyl_transf_1' in doms or 'PKSI-AT' in doms or 'PKS_AT' in doms:
                report.has_standalone_at = True
                report.diagnostic_markers.append(
                    f"standalone AT ({lt}, {aa} aa) — trans-AT diagnostic")

        # Epimerization
        if 'Epimerization' in doms or 'NRPS-E' in doms:
            report.has_epimerization = True
            report.diagnostic_markers.append(f"epimerization ({lt})")

        # Thioesterase
        if 'Thioesterase' in doms or 'NRPS-te1' in doms:
            report.has_te = True

        # Halogenase
        if 'Trp_halogenase' in doms:
            report.has_halogenase = True
            report.diagnostic_markers.append(f"halogenase ({lt})")

        # Lanthipeptide
        if 'LANC_like' in doms or 'Lant_dehydr' in doms:
            report.has_lanc = True
            report.diagnostic_markers.append(f"lanthipeptide enzyme ({lt})")

        # YcaO (thiopeptide/LAP)
        if 'YcaO' in doms:
            report.has_ycao = True
            report.diagnostic_markers.append(f"YcaO cyclodehydratase ({lt})")

        # SSF (ranthipeptide/SCIFF) — single robust check
        if re.search(r'\bSSF\b', doms):
            report.has_ssf = True
            if f"SSF ranthipeptide domain ({lt})" not in report.diagnostic_markers:
                report.diagnostic_markers.append(f"SSF ranthipeptide domain ({lt})")

        # Asn synthase (lassopeptide)
        if 'Asn_synthase' in doms or 'GATase_7' in doms:
            report.has_asn_synthase = True

        # Nucleoside
        if 'TruD' in doms or 'tRNA_PUS' in doms:
            report.has_trud = True
            report.diagnostic_markers.append(f"TruD ({lt}) — nucleoside diagnostic")
        if 'EPSP_synthase' in doms:
            report.has_epsp = True
            report.diagnostic_markers.append(f"EPSP synthase ({lt})")

        # APH self-resistance — BH-CG-01: whole-token match only. The prior bare-substring
        # block fired has_aph on APHANIZOMENON_domain and xAPHx (both contain "APH" as a
        # substring). Collapsed to a single word-boundary regex with a marker dedup guard.
        if re.search(r'\bAPH\b', doms or ""):
            report.has_aph = True
            marker = f"APH self-resistance ({lt})"
            if marker not in report.diagnostic_markers:
                report.diagnostic_markers.append(marker)

        # ── NEW: Terpene detection ──
        if any(kw in doms for kw in TERPENE_CYCLASE_KEYWORDS):
            report.has_terpene_cyclase = True
            report.diagnostic_markers.append(
                f"terpene cyclase ({lt}, {aa} aa — "
                f"{'oversized' if aa > 600 else 'standard'})")

        if any(kw in doms for kw in SQHOP_KEYWORDS):
            report.has_sqhop_cyclase = True
            report.diagnostic_markers.append(f"squalene-hopene cyclase ({lt})")

        if any(kw in doms for kw in POLYPRENYL_KEYWORDS):
            report.has_polyprenyl_synt = True
            report.diagnostic_markers.append(f"polyprenyl synthase ({lt})")

        if any(kw in doms for kw in LYCOPENE_KEYWORDS):
            report.has_lycopene_cyclase = True
            report.diagnostic_markers.append(f"lycopene cyclase ({lt})")

        if any(kw in doms for kw in PHYTOENE_KEYWORDS):
            report.has_phytoene_synt = True
            report.diagnostic_markers.append(f"phytoene/squalene synthase ({lt})")

        # ── NEW: NI-siderophore ──
        if 'IucA_IucC' in doms:
            report.has_iuca_iucc = True
            report.diagnostic_markers.append(f"IucA/IucC aerobactin synthase ({lt})")

        # Catecholate siderophore markers
        if 'Chorismate_bind' in doms or 'TIGR00543' in doms:
            report.has_chorismate_bind = True
            report.diagnostic_markers.append(f"isochorismate synthase ({lt}) — catecholate siderophore")

        # ── NEW: Butyrolactone ──
        if 'AfsA' in doms:
            report.has_afsa = True
            report.diagnostic_markers.append(f"AfsA butyrolactone synthase ({lt})")

        # ── NEW: Ectoine ──
        if 'Ectoine_synth' in doms:
            report.has_ectoine_synth = True
            report.diagnostic_markers.append(f"ectoine synthase ({lt})")

        # ── NEW: NAPAA ──
        if 'DUF3516' in doms:
            report.has_duf3516 = True
            report.diagnostic_markers.append(f"DUF3516 NAPAA polymerisation ({lt})")

        # ── NEW: DUF692 metalloenzyme RiPP ──
        if 'DUF692' in doms:
            report.has_duf692 = True
            report.diagnostic_markers.append(f"DUF692 metalloenzyme ({lt})")

        # ── NEW: Indolocarbazole ──
        if 'indsynth' in doms.lower() or 'StaD' in doms or 'RebC' in doms:
            report.has_indsynth = True
            report.diagnostic_markers.append(
                f"indolocarbazole synthase ({lt})")

        # ── NEW: Mycofactocin ──
        if 'TIGR02109' in doms:
            report.has_tigr02109 = True
            report.diagnostic_markers.append(f"mycofactocin radical SAM ({lt})")

        # ── NEW: T3PKS ──
        if 'Chal_sti_synt' in doms:
            report.has_chal_sti_synt = True
            report.diagnostic_markers.append(f"chalcone/stilbene synthase ({lt})")

        # ── NEW: Primary metabolism markers ──
        if 'PG_binding_1' in doms and 'YkuD' in doms:
            report.has_pg_binding_ykud = True
            report.diagnostic_markers.append(
                f"PG_binding + YkuD transpeptidase ({lt}) — peptidoglycan / primary metab")

        # ── NEW: Betalactone ──
        if 'PEP-utilizers' in doms or 'PPDK_N' in doms:
            report.has_pep_utilizer = True
        if 'Biotin_carb_C' in doms or 'CPSase_L_D2' in doms:
            report.has_biotin_carboxylase = True

        # ── v2.2: Ranthipeptide radical SAM markers (alternative to YcaO+SSF) ──
        if 'SPASM' in doms:
            report.has_spasm = True
            report.diagnostic_markers.append(f"SPASM rSAM ({lt})")
        if 'TIGR03962' in doms:
            report.has_tigr03962 = True
            report.diagnostic_markers.append(f"TIGR03962 ranthipeptide ({lt})")

        # ── v2.2: Lassopeptide markers ──
        if 'Stand_Alone_Lasso_RRE' in doms or 'PF13471' in doms:
            report.has_lasso_rre = True
            report.diagnostic_markers.append(f"lassopeptide RRE ({lt})")
        if 'Transglut_core3' in doms:
            report.has_asn_synthase = True  # transglutaminase = lasso B1 enzyme
            report.diagnostic_markers.append(f"transglutaminase/lasso B1 ({lt})")

        # ── v2.2: Nucleoside (nikJ alias) ──
        if re.search(r'\bnikJ\b', doms, re.IGNORECASE):
            report.has_nikj = True
            report.has_trud = True  # nikJ is a nucleoside pathway enzyme
            report.diagnostic_markers.append(f"nikJ nucleoside enzyme ({lt})")

        # ── v2.2: Phenazine ──
        if re.search(r'\bphz[BF]\b', doms, re.IGNORECASE):
            report.has_phzb = True
            report.diagnostic_markers.append(f"phenazine biosynthesis ({lt})")

    # ══════════════════════════════════════════════════════════
    # CLASSIFICATION LOGIC — priority order
    # Each block returns if it matches; otherwise falls through
    # ══════════════════════════════════════════════════════════

    # ── PTM: single protein containing BOTH KS and AMP-binding, 2500-4000 aa ──
    ptm_candidates = [gc for gc in classified
                      if gc.has_ks and gc.has_amp
                      and 2500 <= gc.aa_length <= 4000]
    if ptm_candidates:
        # Check that this is the DOMINANT megasynthase (not a minor gene)
        ptm = ptm_candidates[0]
        other_ks = [gc for gc in ks_genes if gc.locus_tag != ptm.locus_tag]
        other_amp = [gc for gc in amp_genes if gc.locus_tag != ptm.locus_tag]
        # Allow a few small flanking genes but the iPKS-NRPS must dominate
        if len(other_ks) <= 1 and len(other_amp) <= 1:
            report.pathway_type = PathwayType.PTM
            report.is_iterative = True
            report.confidence = "HIGH"
            report.n_modules_est = 1  # iterative = 1 module used repeatedly
            report.reasoning = (
                f"Single {ptm.aa_length} aa protein ({ptm.locus_tag}) contains "
                f"BOTH KS and AMP-binding — classic iterative iPKS-NRPS for "
                f"PTM/tetramate biosynthesis. "
                f"{len(other_ks)} other KS gene(s), "
                f"{len(other_amp)} other AMP gene(s) — not enough to indicate "
                f"collinear multi-module architecture.")
            return _apply_boundary_adjustment(report)

    # ── T2PKS: KSα + KSβ/CLF pair (300-550 aa) OR t2ks/t2clf/CLF annotations ──
    t2pks_annotated = [gc for gc in classified if gc.is_t2pks_ks]
    ks_small = [gc for gc in ks_genes if 300 <= gc.aa_length <= 550]
    if len(ks_small) >= 2 or len(t2pks_annotated) >= 2:
        # Check for a small ACP (<120 aa) nearby
        small_acp = [gc for gc in classified
                     if gc.has_acp and gc.aa_length < 120]
        # T2PKS-annotated genes are sufficient even without small ACP
        if small_acp or len(t2pks_annotated) >= 2:
            report.pathway_type = PathwayType.T2PKS
            report.has_t2pks = True
            report.is_iterative = True
            report.confidence = "HIGH"
            t2_evidence = t2pks_annotated if t2pks_annotated else ks_small
            acp_note = (f"Plus small ACP ({small_acp[0].locus_tag}, "
                       f"{small_acp[0].aa_length} aa). ") if small_acp else ""
            report.reasoning = (
                f"{len(t2_evidence)} T2PKS KS genes: "
                f"{', '.join(f'{gc.locus_tag} ({gc.aa_length} aa)' for gc in t2_evidence[:3])}. "
                f"{acp_note}"
                f"KSα + KSβ/CLF = minimal T2PKS.")
            return _apply_boundary_adjustment(report)

    # ── Trans-AT PKS: FkbH or AT-less megasynthases + standalone AT ──
    # Improved: check for megasynthases with KS but WITHOUT embedded AT
    atless_megasynthases = [gc for gc in megasynthases
                           if gc.has_ks and not gc.has_at_embedded]
    standalone_at_genes = [gc for gc in classified
                          if any(kw in gc.domains for kw in ('Acyl_transf_1', 'PKSI-AT', 'PKS_AT'))
                          and not gc.has_ks and gc.aa_length < 600]

    is_trans_at = False
    trans_at_evidence = []

    # tra_KS domains are antiSMASH's explicit trans-AT KS annotation
    tra_ks_genes = [gc for gc in classified if 'tra_KS' in gc.domains]
    if tra_ks_genes:
        is_trans_at = True
        trans_at_evidence.append(
            f"{len(tra_ks_genes)} tra_KS (trans-AT ketosynthase) domains")

    if report.has_fkbh:
        is_trans_at = True
        trans_at_evidence.append("FkbH glyceryl-ACP synthase")

    if len(atless_megasynthases) >= 2 and standalone_at_genes:
        is_trans_at = True
        trans_at_evidence.append(
            f"{len(atless_megasynthases)} AT-less KS megasynthases + "
            f"{len(standalone_at_genes)} standalone AT")

    if report.has_standalone_at and len(megasynthases) >= 2:
        is_trans_at = True
        trans_at_evidence.append("standalone AT + multi-megasynthase")

    if is_trans_at:
        if amp_genes:
            report.pathway_type = PathwayType.TRANS_AT_HYBRID
        else:
            report.pathway_type = PathwayType.TRANS_AT_PKS
        report.is_collinear = True
        report.confidence = "HIGH"
        # Module count: PKS modules ~1500 aa, NRPS modules ~1100 aa
        pks_aa = sum(gc.aa_length for gc in megasynthases if gc.has_ks)
        nrps_aa = sum(gc.aa_length for gc in megasynthases if gc.has_amp and not gc.has_ks)
        report.n_pks_modules_est = max(1, pks_aa // 1500)
        report.n_nrps_modules_est = max(0, nrps_aa // 1100) if nrps_aa else 0
        report.n_modules_est = report.n_pks_modules_est + report.n_nrps_modules_est
        report.reasoning = (
            f"Trans-AT evidence: {'; '.join(trans_at_evidence)}. "
            f"{len(megasynthases)} megasynthases ({report.total_megasynthase_aa:,} aa), "
            f"~{report.n_pks_modules_est} PKS + ~{report.n_nrps_modules_est} NRPS modules. "
            f"Collinear assembly line, NOT iterative.")
        return _apply_boundary_adjustment(report)

    # ── T3PKS: chalcone/stilbene synthase ──
    if report.has_chal_sti_synt:
        report.pathway_type = PathwayType.T3PKS
        report.confidence = "HIGH"
        report.reasoning = "Chalcone/stilbene synthase = T3PKS core"
        return _apply_boundary_adjustment(report)

    # ── Lanthipeptide ──
    if report.has_lanc:
        report.pathway_type = PathwayType.LANTHIPEPTIDE
        report.confidence = "HIGH"
        report.reasoning = "LanC/LanB lanthipeptide biosynthetic enzymes"
        return _apply_boundary_adjustment(report)

    # ── LAP / thiopeptide (YcaO) ──
    if report.has_ycao:
        # Distinguish: YcaO + SSF = ranthipeptide; YcaO alone = LAP/thiopeptide
        if report.has_ssf:
            report.pathway_type = PathwayType.RANTHIPEPTIDE
            report.confidence = "HIGH"
            report.reasoning = "YcaO + SSF domains = ranthipeptide/SCIFF RiPP"
        else:
            report.pathway_type = PathwayType.LAP
            report.confidence = "HIGH"
            report.reasoning = "YcaO cyclodehydratase = LAP or thiopeptide"
        return _apply_boundary_adjustment(report)

    # ── Ranthipeptide via radical SAM (no YcaO needed) ──
    if report.has_spasm and report.has_tigr03962:
        report.pathway_type = PathwayType.RANTHIPEPTIDE
        report.confidence = "HIGH"
        report.reasoning = "SPASM + TIGR03962 radical SAM = ranthipeptide (YcaO-independent)"
        return _apply_boundary_adjustment(report)

    # ── Lassopeptide (Asn_synthase / Lasso_RRE / Transglut) ──
    if report.has_asn_synthase and (report.has_lasso_rre or not ks_genes):
        report.pathway_type = PathwayType.LASSOPEPTIDE
        report.confidence = "HIGH" if report.has_lasso_rre else "MEDIUM"
        markers = []
        if report.has_lasso_rre:
            markers.append("Lasso_RRE")
        if report.has_asn_synthase:
            markers.append("Asn_synthase/Transglut (cyclase)")
        report.reasoning = f"{' + '.join(markers)} = lassopeptide biosynthesis"
        return _apply_boundary_adjustment(report)

    # ── Mycofactocin ──
    if report.has_tigr02109:
        report.pathway_type = PathwayType.MYCOFACTOCIN
        report.confidence = "HIGH"
        report.reasoning = "TIGR02109 radical SAM maturase = mycofactocin biosynthesis"
        return _apply_boundary_adjustment(report)

    # ── DUF692 metalloenzyme RiPP ──
    if report.has_duf692:
        report.pathway_type = PathwayType.DUF692_RIPP
        report.confidence = "MEDIUM"
        report.reasoning = "DUF692 metalloenzyme — emerging RiPP maturation enzyme class"
        return _apply_boundary_adjustment(report)

    # ── Indolocarbazole ──
    if report.has_indsynth:
        report.pathway_type = PathwayType.INDOLOCARBAZOLE
        report.confidence = "HIGH"
        report.reasoning = "Indolocarbazole synthase (StaD/RebC family) diagnostic"
        return _apply_boundary_adjustment(report)

    # ── NAPAA ──
    if report.has_duf3516:
        report.pathway_type = PathwayType.NAPAA
        report.confidence = "HIGH"
        report.reasoning = "DUF3516 polymerisation enzyme = NAPAA pathway"
        return _apply_boundary_adjustment(report)

    # ── Ectoine ──
    if report.has_ectoine_synth:
        report.pathway_type = PathwayType.ECTOINE
        report.confidence = "HIGH"
        report.reasoning = "Ectoine synthase = ectoine compatible solute biosynthesis"
        return _apply_boundary_adjustment(report)

    # ── NI-siderophore ──
    if report.has_iuca_iucc and not amp_genes:
        report.pathway_type = PathwayType.NI_SIDEROPHORE
        report.confidence = "HIGH"
        report.reasoning = "IucA/IucC aerobactin-family synthase without NRPS = NIS"
        return _apply_boundary_adjustment(report)

    # ── Butyrolactone ──
    if report.has_afsa:
        report.pathway_type = PathwayType.BUTYROLACTONE
        report.confidence = "HIGH"
        report.reasoning = "AfsA gamma-butyrolactone synthase = autoregulator pathway"
        return _apply_boundary_adjustment(report)

    # ── Nucleoside ──
    if report.has_trud or report.has_epsp:
        report.pathway_type = PathwayType.NUCLEOSIDE
        report.confidence = "HIGH"
        markers = []
        if report.has_trud:
            markers.append("TruD")
        if report.has_epsp:
            markers.append("EPSP synthase")
        report.reasoning = f"{' + '.join(markers)} = nucleoside pathway diagnostic"
        return _apply_boundary_adjustment(report)

    # ── Betalactone ──
    if report.has_pep_utilizer and report.has_biotin_carboxylase:
        report.pathway_type = PathwayType.BETALACTONE
        report.confidence = "MEDIUM"
        report.reasoning = "PEP-utilizer + biotin carboxylase = betalactone precursor logic"
        return _apply_boundary_adjustment(report)

    # ── Terpene subtypes ──
    # GUARD: if megasynthases are present alongside a terpene cyclase,
    # the cyclase is a tailoring enzyme — let the hybrid/PKS/NRPS blocks
    # handle classification instead.
    _terpene_dominated = (
        (report.has_terpene_cyclase or report.has_sqhop_cyclase or
         report.has_polyprenyl_synt or report.has_lycopene_cyclase or
         report.has_phytoene_synt)
        and len(megasynthases) == 0  # no megasynthases = genuine terpene BGC
    )
    if _terpene_dominated:

        # Carotenoid: phytoene synthase OR lycopene cyclase
        if report.has_phytoene_synt or report.has_lycopene_cyclase:
            report.pathway_type = PathwayType.CAROTENOID
            report.confidence = "HIGH"
            report.reasoning = (
                "Phytoene synthase and/or lycopene cyclase = carotenoid pathway")
            return _apply_boundary_adjustment(report)

        # Hopanoid: squalene-hopene cyclase
        if report.has_sqhop_cyclase:
            report.pathway_type = PathwayType.HOPANOID
            report.confidence = "HIGH"
            report.reasoning = "Squalene-hopene cyclase = hopanoid triterpene"
            return _apply_boundary_adjustment(report)

        # Cyclized terpene
        if report.has_terpene_cyclase:
            report.pathway_type = PathwayType.TERPENE_CYCLIZED
            report.confidence = "MEDIUM"
            report.reasoning = "Terpene cyclase (Terpene_syn_C_2) = cyclized sesqui/diterpene"
            return _apply_boundary_adjustment(report)

        # Linear isoprenoid (polyprenyl synthase WITHOUT cyclase)
        if report.has_polyprenyl_synt and not report.has_terpene_cyclase:
            # Check for peptidoglycan context → primary metabolism
            if report.has_pg_binding_ykud:
                report.pathway_type = PathwayType.PRIMARY_METABOLISM
                report.confidence = "HIGH"
                report.reasoning = (
                    "Polyprenyl synthase + PG_binding/YkuD transpeptidase = "
                    "undecaprenyl phosphate / bactoprenol (peptidoglycan carrier lipid). "
                    "Primary metabolism, not a specialized metabolite.")
                return _apply_boundary_adjustment(report)
            else:
                report.pathway_type = PathwayType.TERPENE_LINEAR
                report.confidence = "LOW"
                report.reasoning = (
                    "Polyprenyl synthase without cyclase = linear isoprenoid "
                    "(could be primary or specialized)")
                return _apply_boundary_adjustment(report)

    # ── NRPS-dependent siderophore (NRPS + chorismate/catecholate) ──
    if amp_genes and report.has_chorismate_bind:
        report.pathway_type = PathwayType.NRPS_SIDEROPHORE
        report.is_collinear = True
        report.confidence = "HIGH"
        report.reasoning = (
            "NRPS + isochorismate synthase (chorismate → DHB catecholate) = "
            "NRPS-dependent catecholate siderophore")
        return _apply_boundary_adjustment(report)

    # ── Multi-module collinear PKS/NRPS hybrid ──
    if len(megasynthases) >= 2 and ks_genes and amp_genes:
        report.pathway_type = PathwayType.PKS_NRPS_HYBRID
        report.is_collinear = True
        report.confidence = "HIGH"
        pks_aa = sum(gc.aa_length for gc in megasynthases if gc.has_ks)
        nrps_aa = sum(gc.aa_length for gc in megasynthases if gc.has_amp and not gc.has_ks)
        report.n_pks_modules_est = max(1, pks_aa // 1500)
        report.n_nrps_modules_est = max(0, nrps_aa // 1100) if nrps_aa else 0
        report.n_modules_est = report.n_pks_modules_est + report.n_nrps_modules_est
        report.reasoning = (
            f"{len(megasynthases)} megasynthases with both KS ({len(ks_genes)}) "
            f"and NRPS ({len(amp_genes)}) — collinear PKS/NRPS hybrid, "
            f"~{report.n_modules_est} modules")
        return _apply_boundary_adjustment(report)

    # ── Pure NRPS ──
    # FAAL guard: standalone FAAL without real AMP-binding or condensation
    # is a fatty-acid loader, not an NRPS module. Require at least one gene
    # with actual AMP-binding or Condensation for pure NRPS classification.
    _real_nrps = any('AMP-binding' in gc.domains or gc.has_cond
                     for gc in classified if gc.has_amp)
    if amp_genes and not ks_genes and _real_nrps:
        report.pathway_type = PathwayType.NRPS
        report.is_collinear = True
        report.confidence = "MEDIUM"
        nrps_aa = sum(gc.aa_length for gc in megasynthases if gc.has_amp)
        report.n_nrps_modules_est = max(len(amp_genes), nrps_aa // 1100)
        report.n_modules_est = report.n_nrps_modules_est
        report.reasoning = (
            f"{len(amp_genes)} NRPS adenylation module(s), no PKS. "
            f"~{report.n_modules_est} modules from megasynthase size.")
        return _apply_boundary_adjustment(report)

    # ── Pure cis-AT PKS ──
    if ks_genes and not amp_genes:
        report.pathway_type = PathwayType.CIS_AT_PKS
        report.is_collinear = True
        report.confidence = "MEDIUM"
        pks_aa = sum(gc.aa_length for gc in megasynthases if gc.has_ks)
        report.n_pks_modules_est = max(len(ks_genes), pks_aa // 1500)
        report.n_modules_est = report.n_pks_modules_est
        report.reasoning = (
            f"{len(ks_genes)} KS module(s), no NRPS. "
            f"~{report.n_modules_est} modules.")
        return _apply_boundary_adjustment(report)

    # ── Fallback: UNKNOWN ──
    report.pathway_type = PathwayType.UNKNOWN
    report.confidence = "LOW"
    report.reasoning = (
        f"Could not determine pathway type from domain content. "
        f"{len(megasynthases)} megasynthases, {len(ks_genes)} KS, "
        f"{len(amp_genes)} AMP. Check gene table manually.")
    return _apply_boundary_adjustment(report)


# CUT B (v9.7.223): run-level assembly context. Set once per strain from assembly_tier(interior_pct)
# before its BGCs are analysed; _apply_boundary_adjustment reads it when the report itself carries no
# tier. Default UNKNOWN => pre-cut behaviour (safe no-op).
_RUN_CTX = {"assembly_tier": "UNKNOWN"}

def set_run_assembly_tier(tier: str) -> None:
    _RUN_CTX["assembly_tier"] = tier or "UNKNOWN"


def _apply_boundary_adjustment(report: ArchitectureReport) -> ArchitectureReport:
    """Downgrade confidence one tier for Edge/Full-contig BGCs — EXCEPT that on a POOR/VERY_POOR
    assembly an Edge boundary is the expected default (fragmentation, not biology), so the Edge
    penalty is skipped and the BGC is flagged a finishing-candidate instead of downgraded. The
    Full-contig penalty is retained everywhere; GOOD/MODERATE/UNKNOWN behaviour is unchanged."""
    # E8: every architecture-derived explanation is a capacity/classification
    # hypothesis. Individual diagnostic genes and domains do not establish the
    # product made. Apply the vocabulary at this single return owner so every
    # early classification branch carries the same claim ceiling.
    _capacity_guard = "Architecture-derived class-level capacity hypothesis; not product identity."
    if report.reasoning and _capacity_guard not in report.reasoning:
        report.reasoning = f"{report.reasoning} [{_capacity_guard}]"

    report.confidence_raw = report.confidence
    tier = report.assembly_tier if report.assembly_tier and report.assembly_tier != "UNKNOWN" \
        else _RUN_CTX["assembly_tier"]

    if report.boundary_status in ("Edge", "Full-contig"):
        if report.boundary_status == "Edge" and tier in ("POOR", "VERY_POOR"):
            report.finishing_candidate = True
            report.reasoning += (
                f" [Edge penalty skipped: {tier} assembly — Edge is the expected default here; "
                f"flagged finishing-candidate rather than confidence-downgraded. "
                f"(edge-core vs edge-flank crosswalk refinement pending.)]")
        else:
            tier_order = ["HIGH", "MEDIUM", "LOW"]
            idx = tier_order.index(report.confidence) if report.confidence in tier_order else 2
            new_idx = min(idx + 1, 2)
            report.confidence = tier_order[new_idx]
            if report.confidence != report.confidence_raw:
                report.reasoning += (
                    f" [Confidence downgraded {report.confidence_raw} → "
                    f"{report.confidence} due to {report.boundary_status} boundary.]")

    return report


# ══════════════════════════════════════════════════════════════
# STEP 2: KCB Concordance Check (EXPANDED)
# ══════════════════════════════════════════════════════════════

# Map MIBiG class tags (from BGC annotations) to PathwayType
# These are the structured class labels in MIBiG, not compound names
MIBIG_CLASS_MAP = {
    # Polyketide subtypes
    'Polyketide:Type I': PathwayType.CIS_AT_PKS,
    'Polyketide:Trans-AT type I': PathwayType.TRANS_AT_PKS,
    'Polyketide:Type II': PathwayType.T2PKS,
    'Polyketide:Type III': PathwayType.T3PKS,
    'Polyketide:Iterative type I': PathwayType.CIS_AT_PKS,  # iterative T1
    # NRP
    'NRP': PathwayType.NRPS,
    'NRP:Cyclic depsipeptide': PathwayType.NRPS,
    'NRP:Glycopeptide': PathwayType.NRPS,
    'NRP:Lipopeptide': PathwayType.NRPS,
    # RiPP subtypes
    'RiPP:Lanthipeptide': PathwayType.LANTHIPEPTIDE,
    'RiPP:LAP': PathwayType.LAP,
    'RiPP:Thiopeptide': PathwayType.THIOPEPTIDE,
    'RiPP:Lasso peptide': PathwayType.LASSOPEPTIDE,
    'RiPP:Ranthipeptide': PathwayType.RANTHIPEPTIDE,
    # Terpene
    'Terpene': PathwayType.TERPENE_CYCLIZED,
    # Other
    'Alkaloid:Indole/indolocarbazole': PathwayType.INDOLOCARBAZOLE,
    'Saccharide': PathwayType.UNKNOWN,  # can't distinguish
    'Other': PathwayType.UNKNOWN,
}

# Compound name → PathwayType (fallback for when MIBiG class isn't available)
KCB_COMPOUND_MAP = {
    # PTM/tetramate
    'clifednamide': PathwayType.PTM,
    'hsaf': PathwayType.PTM,
    'frontalin': PathwayType.PTM,
    'ikarugamycin': PathwayType.PTM,
    'sgr ptm': PathwayType.PTM,
    'maltophilin': PathwayType.PTM,
    'dihydromaltophilin': PathwayType.PTM,
    'alteramide': PathwayType.PTM,
    # Trans-AT
    'xenocoumacin': PathwayType.TRANS_AT_HYBRID,
    'pellasoren': PathwayType.TRANS_AT_PKS,
    'chondrochloren': PathwayType.TRANS_AT_HYBRID,
    'zwittermicin': PathwayType.TRANS_AT_HYBRID,
    'bacillaene': PathwayType.TRANS_AT_PKS,
    'mupirocin': PathwayType.TRANS_AT_PKS,
    'difficidin': PathwayType.TRANS_AT_PKS,
    'macrolactin': PathwayType.TRANS_AT_PKS,
    'leinamycin': PathwayType.TRANS_AT_PKS,
    # Cis-AT PKS
    'erythromycin': PathwayType.CIS_AT_PKS,
    'niddamycin': PathwayType.CIS_AT_PKS,
    'spiramycin': PathwayType.CIS_AT_PKS,
    'tetronasin': PathwayType.CIS_AT_PKS,
    'nystatin': PathwayType.CIS_AT_PKS,
    'amphotericin': PathwayType.CIS_AT_PKS,
    'geldanamycin': PathwayType.CIS_AT_PKS,
    'avermectin': PathwayType.CIS_AT_PKS,
    'rapamycin': PathwayType.PKS_NRPS_HYBRID,
    'tacrolimus': PathwayType.PKS_NRPS_HYBRID,
    # Aromatic T2PKS
    'doxorubicin': PathwayType.T2PKS,
    'actinorhodin': PathwayType.T2PKS,
    'tetracycline': PathwayType.T2PKS,
    'chlortetracycline': PathwayType.T2PKS,
    'oxytetracycline': PathwayType.T2PKS,
    'arimetamycin': PathwayType.T2PKS,
    'prejadomycin': PathwayType.T2PKS,
    'rabelomycin': PathwayType.T2PKS,
    # NRPS
    'mannopeptimycin': PathwayType.NRPS,
    'enduracidin': PathwayType.NRPS,
    'daptomycin': PathwayType.NRPS,
    'glycinocin': PathwayType.NRPS,
    'arylomycin': PathwayType.NRPS,
    'kutzneride': PathwayType.NRPS,
    'vazabitide': PathwayType.NRPS,
    'nocathiacin': PathwayType.NRPS,
    # Siderophores
    'nocobactin': PathwayType.NRPS_SIDEROPHORE,
    'qinichelins': PathwayType.NRPS_SIDEROPHORE,
    'peucechelin': PathwayType.NI_SIDEROPHORE,
    'madurastatin': PathwayType.NRPS_SIDEROPHORE,
    'desferrioxamine': PathwayType.NI_SIDEROPHORE,
    'aerobactin': PathwayType.NI_SIDEROPHORE,
    # Indolocarbazole
    'staurosporine': PathwayType.INDOLOCARBAZOLE,
    'at2433': PathwayType.INDOLOCARBAZOLE,
    'rebeccamycin': PathwayType.INDOLOCARBAZOLE,
    # Terpene misanchors (should NOT be polyketides)
    'isorenieratene': PathwayType.CAROTENOID,
    'ectoine': PathwayType.ECTOINE,
    # Ionophore polyethers
    'monensin': PathwayType.CIS_AT_PKS,
    'salinomycin': PathwayType.CIS_AT_PKS,
    'x-14547': PathwayType.CIS_AT_PKS,
    'indanomycin': PathwayType.CIS_AT_PKS,
    # Nucleoside
    'nikkomycin': PathwayType.NUCLEOSIDE,
    'polyoxin': PathwayType.NUCLEOSIDE,
    # Reveromycin / betalactone
    'reveromycin': PathwayType.BETALACTONE,
}


def check_kcb_concordance(arch: ArchitectureReport,
                          kcb_compound: str,
                          kcb_n_genes: int,
                          query_n_genes: int,
                          kcb_mibig_class: str = "") -> ConcordanceResult:
    """
    Check whether the KCB compound class matches the architecture assessment.

    kcb_compound: name from KnownClusterBlast top hit
    kcb_n_genes: number of query genes that hit the KCB reference
    query_n_genes: total genes in the query BGC
    kcb_mibig_class: MIBiG class tag if available (e.g., "Polyketide:Type I")
    """
    if not kcb_compound or kcb_compound in ('None', '—', '', 'null'):
        return ConcordanceResult(
            concordance=Concordance.NO_KCB,
            kcb_compound=kcb_compound or "",
            architecture_class=arch.pathway_type.value)

    result = ConcordanceResult(
        concordance=Concordance.WEAK_SIGNAL,
        kcb_compound=kcb_compound,
        architecture_class=arch.pathway_type.value)

    # ── Raw gene-count coverage ──
    if query_n_genes > 0:
        result.kcb_coverage_pct = (kcb_n_genes / query_n_genes) * 100
    else:
        result.kcb_coverage_pct = 0.0

    # ── Biosynthetic-core-weighted coverage ──
    # Weight genes by whether they carry biosynthetic core domains
    n_core_genes = sum(1 for gc in arch.gene_classifications if gc.is_biosynthetic_core)
    if n_core_genes > 0 and kcb_n_genes > 0:
        # Approximate: assume KCB hits are proportionally distributed
        # In reality we'd need per-gene hit data; this is a reasonable proxy
        # Scale: if coverage is X% overall but only Y% of genes are core,
        # the effective biosynthetic coverage is higher/lower
        # For now, use raw coverage (can be refined with per-gene hit data)
        result.kcb_biosynthetic_coverage_pct = result.kcb_coverage_pct
    else:
        result.kcb_biosynthetic_coverage_pct = 0.0

    # ── Weak signal check ──
    if result.kcb_coverage_pct < 30:
        result.concordance = Concordance.WEAK_SIGNAL
        result.conflict_detail = (
            f"KCB coverage {result.kcb_coverage_pct:.0f}% "
            f"({kcb_n_genes}/{query_n_genes} genes) — "
            f"too low for product class assignment")
        return result

    # ── Look up expected class ──
    expected_type = None

    # Try MIBiG class tag first (most reliable)
    if kcb_mibig_class:
        for key, ptype in MIBIG_CLASS_MAP.items():
            if key.lower() in kcb_mibig_class.lower():
                expected_type = ptype
                result.kcb_class = ptype.value
                break

    # Fall back to compound name lookup
    if expected_type is None:
        compound_lower = kcb_compound.lower()
        for key, ptype in KCB_COMPOUND_MAP.items():
            if key in compound_lower:
                expected_type = ptype
                result.kcb_class = ptype.value
                break

    if expected_type is None:
        result.concordance = Concordance.WEAK_SIGNAL
        result.conflict_detail = (
            f"KCB compound '{kcb_compound}' not in class map. "
            f"Cannot verify concordance.")
        return result

    # ── Concordance check ──
    # Allow fuzzy matching: some types are compatible
    concordant_pairs = {
        # trans-AT hybrid is compatible with PKS/NRPS hybrid
        (PathwayType.TRANS_AT_HYBRID, PathwayType.PKS_NRPS_HYBRID),
        (PathwayType.PKS_NRPS_HYBRID, PathwayType.TRANS_AT_HYBRID),
        # NRPS siderophore is compatible with NRPS
        (PathwayType.NRPS_SIDEROPHORE, PathwayType.NRPS),
        (PathwayType.NRPS, PathwayType.NRPS_SIDEROPHORE),
        # Thiopeptide is compatible with LAP (both use YcaO)
        (PathwayType.THIOPEPTIDE, PathwayType.LAP),
        (PathwayType.LAP, PathwayType.THIOPEPTIDE),
        # Cyclized terpene compatible with hopanoid
        (PathwayType.TERPENE_CYCLIZED, PathwayType.HOPANOID),
        (PathwayType.HOPANOID, PathwayType.TERPENE_CYCLIZED),
    }

    if arch.pathway_type == expected_type:
        result.concordance = Concordance.CONCORDANT
    elif (arch.pathway_type, expected_type) in concordant_pairs:
        result.concordance = Concordance.CONCORDANT
        result.conflict_detail = (
            f"Fuzzy concordance: architecture={arch.pathway_type.value}, "
            f"KCB={expected_type.value} — compatible types")
    elif arch.pathway_type == PathwayType.UNKNOWN:
        # Architecture couldn't determine type — defer to KCB if coverage is strong
        if result.kcb_coverage_pct >= 60:
            result.concordance = Concordance.ARCHITECTURE_DEFERS
            result.conflict_detail = (
                f"Architecture UNKNOWN but KCB '{kcb_compound}' has "
                f"{result.kcb_coverage_pct:.0f}% coverage — using KCB class "
                f"({expected_type.value}) as provisional assignment")
        else:
            result.concordance = Concordance.WEAK_SIGNAL
            result.conflict_detail = (
                f"Architecture UNKNOWN and KCB coverage only "
                f"{result.kcb_coverage_pct:.0f}% — insufficient for assignment")
    else:
        result.concordance = Concordance.DISCORDANT
        result.conflict_detail = (
            f"ARCHITECTURE says {arch.pathway_type.value} "
            f"but KCB says {expected_type.value} "
            f"('{kcb_compound}'). Architecture wins.")

    return result


# ══════════════════════════════════════════════════════════════
# STEP 3: Final Assignment (EXPANDED)
# ══════════════════════════════════════════════════════════════


# ── B3: betalactone over-call suppression ──
# The betalactone architecture rule (PEP-utilizer + biotin carboxylase) over-fires on
# generic central-metabolism genes (HMGL-like / AMP-binding). A recurring tell is a
# terpene KCB anchor (e.g. geosmin) on a "betalactone" region — the region is terpene-
# adjacent, not a betalactone. Flag (do not silently relabel) for BLASTp review.
_TERPENE_KCB_NAMES = {
    "geosmin", "2-methylisoborneol", "2-methylenebornane", "methylisoborneol", "2-mib",
    "hopene", "squalene", "squalene-hopene", "isorenieratene", "carotenoid",
    "phytoene", "hopanoid", "epi-isozizaene", "isozizaene", "pentalenene", "germacradienol",
    # canonical actinomycete terpene KCB compounds the substring detector missed:
    "albaflavenone", "neomenthol", "avermitilol", "sodorifen", "epi-cubenol",
    "cyclooctat-9-en-7-ol", "cyclooctatin", "(+)-eremophilene", "epi-isozizaene alcohol",
}

def _is_terpene_kcb(kcb_compound: str, kcb_mibig_class: str = "") -> bool:
    """True if the KCB anchor is a terpene/isoprenoid, by MIBiG class or curated name."""
    if kcb_mibig_class and "terpene" in kcb_mibig_class.lower():
        return True
    c = (kcb_compound or "").strip().lower()
    if not c:
        return False
    # Exact-set membership only. A substring test (`"hopene" in c`) false-positives on names like
    # "hopene-like NRPS" or "carotenoid-associated hybrid" and would WRONGLY suppress a real
    # betalactone call; the MIBiG class above is the authoritative broad signal, so the name set
    # can stay strict. Normalise a trailing single-letter/number congener suffix (e.g. "geosmin b").
    if c in _TERPENE_KCB_NAMES:
        return True
    base = c.rsplit(" ", 1)[0] if len(c.rsplit(" ", 1)) == 2 and len(c.rsplit(" ", 1)[1]) <= 2 else c
    return base in _TERPENE_KCB_NAMES


def make_assignment(arch: ArchitectureReport,
                    concordance: ConcordanceResult) -> FinalAssignment:
    """
    Make the final product class assignment.
    Architecture wins unless it's UNKNOWN and KCB is strong.
    """
    assignment = FinalAssignment(
        product_class=arch.pathway_type.value,
        source="architecture",
        confidence=arch.confidence,
        kcb_note="")

    if concordance.concordance == Concordance.CONCORDANT:
        assignment.source = "architecture+KCB"
        assignment.kcb_note = (
            f"KCB ({concordance.kcb_compound}) is concordant with architecture "
            f"assessment ({arch.pathway_type.value}). Coverage: "
            f"{concordance.kcb_coverage_pct:.0f}%. "
            f"{concordance.conflict_detail}")

    elif concordance.concordance == Concordance.DISCORDANT:
        assignment.source = "architecture (KCB overridden)"
        assignment.kcb_note = (
            f"WARNING — KCB DISCORDANT: '{concordance.kcb_compound}' suggests "
            f"{concordance.kcb_class}, but architecture assessment shows "
            f"{arch.pathway_type.value}. {concordance.conflict_detail} "
            f"The KCB compound name is a similarity signal, not a product class "
            f"assignment. Architecture evidence is primary.")

    elif concordance.concordance == Concordance.ARCHITECTURE_DEFERS:
        # Architecture couldn't classify but KCB has strong coverage
        assignment.product_class = concordance.kcb_class
        assignment.source = "KCB (architecture unresolved)"
        assignment.confidence = "LOW"  # still low — architecture couldn't confirm
        assignment.kcb_note = (
            f"Architecture could not determine pathway type. "
            f"KCB ({concordance.kcb_compound}) has "
            f"{concordance.kcb_coverage_pct:.0f}% coverage — using as "
            f"provisional class assignment ({concordance.kcb_class}). "
            f"Low confidence: architecture could not independently confirm.")

    elif concordance.concordance == Concordance.WEAK_SIGNAL:
        assignment.kcb_note = (
            f"KCB ({concordance.kcb_compound}) coverage "
            f"{concordance.kcb_coverage_pct:.0f}% — too low for product class "
            f"assignment. {concordance.conflict_detail} "
            f"Using architecture only.")

    elif concordance.concordance == Concordance.NO_KCB:
        assignment.kcb_note = (
            "No KCB hit. Orphan — assignment from architecture only.")

    # ── B3: betalactone over-call flag (architecture=betalactone + terpene KCB anchor) ──
    if (arch.pathway_type == PathwayType.BETALACTONE
            and _is_terpene_kcb(concordance.kcb_compound, concordance.kcb_class)):
        assignment.betalactone_overcall_suspected = True
        assignment.kcb_note = (
            f"BETALACTONE OVER-CALL SUSPECTED (B3): the betalactone call is from the generic "
            f"architecture rule (PEP-utilizer + biotin carboxylase), but the KCB anchor "
            f"'{concordance.kcb_compound}' is a terpene/isoprenoid, not a betalactone. This is the "
            f"recurring betalactone over-call (cf. a real cohort betalactone case [Redacted — publication in preparation]). Treat the "
            f"betalactone label as a likely artifact pending per-gene BLASTp; do not assert "
            f"betalactone capacity. " + assignment.kcb_note)

    return assignment


# ══════════════════════════════════════════════════════════════
# CONVENIENCE: Run all three steps
# ══════════════════════════════════════════════════════════════

def architecture_first_assessment(
        genes: List[Dict],
        boundary_status: str = "Interior",
        kcb_compound: str = "",
        kcb_n_genes: int = 0,
        kcb_mibig_class: str = ""
) -> Tuple[ArchitectureReport, ConcordanceResult, FinalAssignment]:
    """
    Run the full architecture-first pipeline.

    Returns (architecture_report, concordance_result, final_assignment).
    """
    arch = assess_architecture(genes, boundary_status=boundary_status)
    concordance = check_kcb_concordance(
        arch, kcb_compound, kcb_n_genes, len(genes),
        kcb_mibig_class=kcb_mibig_class)
    assignment = make_assignment(arch, concordance)
    return arch, concordance, assignment


# ══════════════════════════════════════════════════════════════
# SAPOTE LAYER INSTRUCTIONS (UPDATED)
# ══════════════════════════════════════════════════════════════

SAPOTE_INSTRUCTIONS = """
MANDATORY WORKFLOW FOR MODE B INTERPRETATION (v9.7.107):

Before writing ANY §3 Biosynthetic Core interpretation for a BGC:

1. RUN assess_architecture(genes, boundary_status) on the gene list
   - This is KCB-BLIND. It looks only at domain content.
   - It classifies: trans-AT PKS, cis-AT PKS, NRPS, T2PKS, T3PKS,
     PTM, lanthipeptide, LAP/thiopeptide, ranthipeptide, mycofactocin,
     DUF692-RiPP, terpene (cyclized/linear/hopanoid/carotenoid),
     NI-siderophore, NRPS-siderophore, butyrolactone, ectoine,
     NAPAA, betalactone, nucleoside, primary metabolism, or UNKNOWN.
   - Confidence is downgraded for Edge/Full-contig boundaries.

2. RUN check_kcb_concordance() comparing architecture vs KCB
   - CONCORDANT: KCB corroborates architecture. Use both.
   - DISCORDANT: Architecture wins. KCB is misleading similarity.
     State this explicitly in the Mode B card.
   - WEAK_SIGNAL: KCB coverage <30% or compound not in class map.
     Don't use it for product class.
   - ARCHITECTURE_DEFERS: Architecture returned UNKNOWN but KCB has
     >=60% coverage of a known compound. Use KCB provisionally at
     LOW confidence. State the architecture couldn't confirm.
   - NO_KCB: Orphan. Architecture only.

3. RUN make_assignment() to get the final product class.

4. Write the Mode B card with the FINAL ASSIGNMENT as the product class.
   - §1 Identity: state pathway type and source (architecture/KCB/both)
   - §3 Core: describe gene architecture FIRST, then note KCB concordance
   - §5-8 Verdict: use the final assignment, not the KCB compound name

CRITICAL RULES:
   - The KCB compound name is a SIMILARITY SIGNAL, not a product class.
   - Architecture is PRIMARY EVIDENCE for product class.
   - When they disagree, architecture wins. Always.
   - When architecture returns UNKNOWN, do NOT fall back to KCB as the
     product class UNLESS coverage >= 60% (ARCHITECTURE_DEFERS).
   - When UNKNOWN and KCB is also weak, state: "architecture unresolved,
     no reliable product class assignment" and describe gene content
     without a class claim.

KNOWN MISANCHOR PATTERNS (flag when seen):
   - T2PKS KCB (chlortetracycline, prejadomycin) on a terpene BGC
     → the KCB matches shared flanking genes, not the terpene core
   - PTM KCB (clifednamide, HSAF) on a collinear trans-AT PKS
     → the KCB matches a KS subdomain, not the iterative iPKS-NRPS
   - Macrolide KCB (spiramycin, niddamycin) on a full-contig fragment
     → the captured module matches many macrolide references generically
"""


# v9.7.405: the in-module `__main__` self-test (nine printed cases) was removed. Every case is
# a named test in tests/test_architecture_first.py (PTM, trans-AT-vs-PTM KCB, T2PKS, terpene
# priority, bactoprenol, edge downgrade, UNKNOWN+strong-KCB, mycofactocin, NIS siderophore), so
# the block was duplicate coverage that only added print debt to a library module.

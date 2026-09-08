"""Source-derived scanning engine — all pattern dictionaries and scan functions.

Pattern groups (13):
    DOMAIN_CLASS_PATTERNS     — NRPS/PKS/RiPP/tailoring domain classification
    CHITINASE_PATTERNS        — GH18/GH19/AA10/LPMO/GlcNAc chitinolysis signals
    REGULATOR_PATTERNS        — DasR/LuxR/TetR/SARP/GBL/etc. per-BGC regulator families
    TRANSPORTER_PATTERNS      — ABC/MFS/RND/MATE/efflux/export families
    RESISTANCE_PATTERNS       — Beta-lactamase/Erm/VanHAX/APH-AAC/fosfomycin/self-resistance
    CCTT_PATTERNS             — class-defining cryptic-class triggers (T43-* family; count == len(CCTT_PATTERNS))
    CASSETTE_PATTERNS         — 15 cassette families (release/glycosylation/halogenation/…)
    PRIMARY_METABOLISM_PATTERNS— housekeeping/pigment/replication-core false-positive families
    UMED_PATTERNS             — RiPP/nucleoside maturation enzyme detection
    TFBS_MOTIFS               — 12 TFBS palindrome/box motifs for upstream scanning
    MOBILE_ELEMENT_PATTERNS   — integrase/recombinase/transposase/conjugation/ICE detection
    VETO_CONTEXT_PATTERNS     — glycogen-trehalose/hglE/sugar-kinase/copalyl cross-reaction vetoes
    FLBR_PATTERNS             — megasynthase KS/AT/NRPS module fragment detection

Scan functions (14):
    _scan_patterns()                  — generic CDS-list pattern scanner (shared by most scans)
    scan_cassettes()                  — per-BGC cassette family coupling
    scan_umed()                       — maturation enzyme gap detection
    scan_tfbs()                       — upstream TFBS motif scanning
    scan_blda_tta()                   — bldA-dependent TTA codon burden (actinomycete-gated)
    scan_efls()                       — shared-evidence fragment linkage (all-vs-all, edge-filtered)
    scan_flbr()                       — LMPKS/megasynthase fragment detection + orphan KS motifs
    scan_domain_architecture()        — per-BGC domain profile from antiSMASH GBK features
    resistance_tier_classification()  — tiered self-protection/resistance with class concordance
    scan_qs_signals()                 — QS signal + NAPAA routing flags
    scan_glycosylation_arm_candidates() — §34.5 saccharide glycosylation-arm trap
    compute_per_bgc_dss()             — per-BGC diagnostic signal score (0–5)
    scan_orphan_megasynthase_motifs() — KS/AT active-site motif scan on orphan contigs
    generate_wetlab_rows()            — per-BGC class-default wet-lab guidance rows

Registry overlay (B2 Phase 1):
    When registry_inventory_v1.9.4.json is present and self-consistent, module globals
    are reassigned from the registry build (regex/motif targets only; HMM/DIAMOND markers
    ride along as catalog). Set MAMEY_DISABLE_REGISTRY_DETECTOR=1 to force in-code fallback.
    Parity tested by tests/test_b2_registry_parity.py.
"""
from __future__ import annotations
import re
from collections import defaultdict
from typing import Any
from .models import BGCRecord, CDSFeature, DomainFeature, SourceScanBundle
from .crosswalk import contig_key as _contig_key   # T-4: single shared normaliser (was a local def here)
from .dkp_cdps import scan_dkp_cdps


DOMAIN_CLASS_PATTERNS = {
    "NRPS_A": [r"\bA\b", r"AMP-binding", r"adenylation", r"NRPS_A"],
    "NRPS_C": [r"\bC\b", r"condensation", r"NRPS_C"],
    "NRPS_T_PCP": [r"\bT\b", r"PCP", r"thiolation"],
    "NRPS_E": [r"\bE\b", r"epimerization"],
    "TE_release": [r"\bTE\b", r"thioesterase"],
    "PKS_KS": [r"PKS_KS", r"\bKS\b", r"ketosynthase", r"ketoacyl synthase"],
    "PKS_AT": [r"PKS_AT", r"\bAT\b", r"acyltransferase"],
    "PKS_DH": [r"PKS_DH", r"\bDH\b", r"dehydratase"],
    "PKS_ER": [r"PKS_ER", r"\bER\b", r"enoylreductase"],
    "PKS_KR": [r"PKS_KR", r"\bKR\b", r"ketoreductase"],
    "PKS_ACP": [r"PKS_ACP", r"\bACP\b", r"acyl carrier"],
    "RiPP_precursor": [r"precursor", r"leader peptide", r"core peptide"],
    "YcaO_TOMM": [r"YcaO", r"cyclodehydratase"],
    "Halogenase": [r"(?<!de)halogenase"],
    "Glycosyltransferase": [r"glycosyltransferase", r"\bGT\b"],
    "Methyltransferase": [r"methyltransferase"],
    "Oxidoreductase": [r"oxidoreductase", r"dehydrogenase", r"oxygenase"],
    "Aminotransferase": [r"aminotransferase", r"transaminase"],
    "Transporter": [r"transporter", r"efflux", r"exporter"],
    "Regulator": [r"regulator", r"transcriptional"],
}

CHITINASE_PATTERNS = {
    "GH18": [r"gh18", r"glycoside hydrolase family 18", r"chitinase"],
    "GH19": [r"gh19", r"glycoside hydrolase family 19"],
    "AA10_LPMO": [r"aa10", r"lpmo", r"lytic polysaccharide monooxygenase"],
    "CBM_CHITIN": [r"chitin.?binding", r"cbm", r"carbohydrate.binding"],
    "GlcNAc": [r"glcnac", r"n-acetylglucosamine", r"nag[a-z]", r"dasr"],
}
REGULATOR_PATTERNS = {
    "DasR_GntR": [r"dasr", r"gntr"], "LuxR": [r"luxr"], "TetR": [r"tetr"],
    "LysR": [r"lysr"], "SARP": [r"sarp", r"streptomyces antibiotic regulatory protein"],
    "MarR": [r"marr"], "LacI": [r"laci"], "AraC": [r"arac"],
    "TwoComponent": [r"response regulator", r"histidine kinase", r"two-component"],
    "Fur_Zur": [r"\bfur\b", r"\bzur\b", r"ferric uptake regulator", r"zinc uptake regulator"],
    "IolR": [r"iolr"], "PhoP": [r"phop", r"phor"], "OsdR": [r"osdr"],
    # F11: GBL receptor + AdpA master switch. NOTE these are commonly annotated generically as
    # "TetR-family"/"AraC-family" transcriptional regulators, so the keyword route under-detects —
    # the genome-wide GBL_AdpA_like box scan finds them but the per-BGC gene call falls through to
    # TetR/AraC. Full resolution needs the PF03279 (A-factor receptor) HMM; these keywords catch the
    # functionally-named subset only.
    "GBL": [r"gamma-butyrolactone", r"\bbutyrolactone\b", r"a-factor receptor", r"autoregulator receptor",
            r"\barpr\b", r"\barpa\b", r"\bscbr\b", r"\bbara\b", r"\badpa\b", r"\bbldh\b"],
}
TRANSPORTER_PATTERNS = {
    "ABC": [r"abc transporter", r"atp-binding cassette"], "MFS": [r"major facilitator", r"\bmfs\b"],
    "RND": [r"rnd transporter", r"resistance-nodulation"], "MATE": [r"mate transporter"],
    "Efflux": [r"efflux"], "Export": [r"exporter", r"secretion"],
}
RESISTANCE_PATTERNS = {
    "Beta_lactamase_fold": [r"beta.?lactamase", r"metallo-beta-lactamase"],
    # \b word boundaries prevent "erm" matching "terminal", "intermediate", "thermophile" etc.
    "Erm_methylase": [r"\berm\b", r"rrna methyltransferase", r"23s rrna methyltransferase",
                      r"erythromycin resistance methyltransferase"],
    # \b prevents "vanh/vana/vanx" matching "vanadium", "vanadic" etc.
    "VanHAX_like": [r"\bvanh\b", r"\bvana\b", r"\bvanx\b", r"d-ala-d-lac",
                    r"vancomycin resistance"],
    "APH_AAC": [r"aminoglycoside phosphotransferase", r"aminoglycoside acetyltransferase",
                r"\baph\b", r"\baac\b"],
    "Fosfomycin": [r"\bfoma\b", r"\bfomb\b", r"fosfomycin resistance"],
    "Self_resistance_general": [r"resistance protein", r"immunity protein", r"self-resistance"],
}
CCTT_PATTERNS = {
    "T43-HAL_halogenase": [r"(?<!de)halogenase", r"flavin-dependent halogenase", r"tryptophan halogenase"],
    "T43-XHAL_fluorinase_chlorinase": [r"fluorinase", r"chlorinase", r"\bsall\b", r"\bfla\b", r"sam-dependent halogenase"],
    "T43-PHO_phosphonate": [r"(?<!carboxy)phosphonate(?!.*transporter)(?!.*utilization)(?!.*c-?p lyase)(?!.*phn[g-m]\b)", r"\bpep_mutase\b", r"pep mutase(?!\s*family)", r"phosphoenolpyruvate mutase(?!\s*family)"],
    "T43-NUC_nucleoside": [r"nikkomycin", r"polyoxin", r"\bnikj\b", r"\bnikd\b", r"\bnikc\b", r"peptidyl[- ]nucleoside", r"chitin synthase inhibit"],
    "T43-BLA_betalactam": [r"\bnocardicin\b", r"isopenicillin n synthase(?!\s*family)", r"\bpcbab\b", r"\bpcbc\b", r"acv synthetase", r"beta-lactam synthetase", r"\bbls\b", r"clavaminate synthase", r"deacetoxycephalosporin", r"monobactam", r"\bnat\b nocardicin"],
    "T43-AMC_aminocyclitol": [r"aminocyclitol", r"dois", r"btrc", r"2-deoxy-scyllo-inosose"],
    "T43-ENE_enediyne": [r"enediyne"],
    "T43-LAN_lanthipeptide": [r"lanthipeptide", r"lantibiotic", r"\blanc\b", r"\blanm\b"],
    "T43-LASSO_lassopeptide": [r"lassopeptide", r"lasso peptide"],
    "T43-THA_thioamide": [r"thioamide", r"ycaO"],
    "T43-DKP_cdps": [r"cyclodipeptide synthase", r"\bcdps\b", r"diketopiperazine"],
    "T43-IDC_indolocarbazole": [r"indolocarbazole", r"rebeccamycin", r"staurosporine", r"indsynth"],
    "T43-PTM_hsaf_tetramate": [r"\bhsaf\b", r"maltophilin", r"dihydromaltophilin", r"heat.?stable.?antifungal", r"tetramate", r"tetramic acid", r"xanthobaccin", r"frontalamide", r"alteramide", r"clifednamide", r"ikarugamycin", r"combamide", r"polycyclic tetramate macrolactam"],
    "T43-TET_tetronate_spirotetronate": [r"tetronate", r"spirotetronate", r"fkbh", r"(?<!acyl)glyceryl"],
    "T43-NN_n_n_bond": [r"n-n bond", r"diazo", r"\bcreE\b", r"\bcreD\b", r"azoxy", r"hydrazine"],
    # v9.7.119→1.9.99: three class-defining triggers wired off committed diagnostics that already
    # existed in the architecture/mis-anchor layers but had no trigger-floor representation.
    # T43-PYE: polyene macrolide (antifungal). The arylpolyene pigment is excluded by negative lookbehind
    # (same token logic as _POLYENE_ANCHOR). NOTE: the AF diagnostic bonus is additionally gated on
    # ks_domain_count >= _POLYENE_MIN_KS in scoring.py, so a polyene NAME on a <4-KS fragment fires the
    # pattern but is treated as uncorroborated (no bonus; mis-anchor guard runs). Pattern + scoring gate
    # together keep the trigger consistent with the existing polyene mis-anchor guard.
    "T43-PYE_polyene_macrolide": [r"(?<!aryl)polyene macrolide", r"(?<!aryl)polyene antifungal",
        r"\bnatamycin\b", r"\bpimaricin\b", r"\bcandicidin\b", r"\bamphotericin\b", r"\bnystatin\b",
        r"\bfilipin\b", r"\brimocidin\b", r"\bfaeriefungin\b", r"\btetramycin\b", r"\blucensomycin\b",
        r"\bpartricin\b", r"\bperimycin\b", r"\baureofungin\b", r"\bhamycin\b", r"\btrichomycin\b",
        r"\blevorin\b", r"\bfungichromin\b", r"\bselvamicin\b", r"\breedsmycin\b",
        r"\btetraene\b", r"\bpentaene\b", r"\bhexaene\b", r"\bheptaene\b"],
    # T43-GPA: glycopeptide (antibacterial). Committed markers are the OxyB/OxyA/OxyC oxidative-coupling
    # P450s and the non-proteinogenic-AA machinery (DPGS, HPG aminotransferase) — glycopeptide-specific.
    # The class_architecture rule-0a gate (nrps_c>=6 + halogenase + glycosyltransferase) is the structural
    # corroborator; the corroboration set below rejects a bare glycosyltransferase in a saccharide cluster.
    "T43-GPA_glycopeptide": [r"\boxyB\b", r"\boxyA\b", r"\boxyC\b", r"\bdpgs\b",
        r"3,5-dihydroxyphenylglycine", r"4-hydroxyphenylglycine", r"\bhpg\b aminotransferase",
        r"\bglycopeptide\b", r"\bvancomycin\b", r"\bteicoplanin\b", r"\bbalhimycin\b",
        r"\bchloroeremomycin\b", r"\bpekiskomycin\b", r"\bristocetin\b", r"\bristomycin\b"],
    # T43-BLT: betalactone (antibacterial; some members cytotoxic — routed AB, chemotype layer flags
    # cytotoxic members). Committed logic = PEP-utilizer + biotin-carboxylase PAIR (architecture_first),
    # never either token alone. Named compounds also fire directly.
    "T43-BLT_betalactone": [r"\bbetalactone\b", r"\bbeta-lactone\b", r"\bsalinosporamide\b",
        r"\bplatensimycin\b", r"\bplatencin\b", r"\blactacystin\b", r"\bebelactone\b", r"\bovalicin\b"],
}

# N-05/A-04 — context corroboration for class-DEFINING CCTT triggers.
#
# A class-definitive trigger (T43-BLA, T43-LAN, …) should co-occur with the antiSMASH product class it
# implies. When it fires on an incompatible class (T43-BLA on a terpene = A4; T43-PTM on a lasso; T43-TET's
# loose `glyceryl` token on a diacylglyceryl transferase; T43-PHO on an isocitrate-lyase/PEP-mutase FAMILY
# protein or a phosphonate TRANSPORTER), the trigger matched a single token with no corroborating context —
# a candidate false positive. We do not DELETE such firings (the call could be a genuinely novel/mis-classified
# locus — evidence conservation); we FLAG them so a class-capacity claim is not built on an uncorroborated
# trigger. Tailoring-enzyme triggers (halogenase/fluorinase) and broad triggers (N-N bond) are class-PROMISCUOUS
# by biology and never flagged. Cohort scan that sized this gap: tools/scan_cctt_class_compat.py.
CCTT_PROMISCUOUS = {"T43-HAL_halogenase", "T43-XHAL_fluorinase_chlorinase", "T43-NN_n_n_bond"}

# trigger -> antiSMASH product-class substrings (lowercased) that corroborate it. A firing whose BGC carries
# none of these is context-uncorroborated. None / absent => not gated (treated as corroborated).
CCTT_CLASS_COMPAT = {
    "T43-BLA_betalactam": {"nrps", "beta-lactam", "betalactam", "lactam"},
    "T43-LAN_lanthipeptide": {"lanthipeptide", "lanthi", "ripp"},
    "T43-LASSO_lassopeptide": {"lassopeptide", "lasso", "ripp"},
    "T43-DKP_cdps": {"nrps", "cdps", "diketopiperazine", "other", "cyclodipeptide"},
    "T43-PHO_phosphonate": {"phosphonate", "phosph"},
    "T43-NUC_nucleoside": {"nucleoside", "amglyccycl", "ripp", "ccna"},
    "T43-PTM_hsaf_tetramate": {"pks", "nrps", "transat", "hybrid", "t1pks", "t2pks"},  # HSAF = PKS-NRPS hybrid
    "T43-TET_tetronate_spirotetronate": {"pks", "t1pks", "tetronate", "transat"},
    "T43-IDC_indolocarbazole": {"nrps", "indole", "indolocarbazole"},
    "T43-AMC_aminocyclitol": {"amglyccycl", "aminoglycoside", "aminocyclitol", "saccharide"},
    "T43-ENE_enediyne": {"pks", "t1pks", "enediyne", "transat"},
    "T43-THA_thioamide": {"ripp", "nrps", "thioamitides", "lap", "thiopeptide"},
    "T43-PYE_polyene_macrolide": {"t1pks", "pks", "transat", "transat-pks", "polyene", "polyketide"},
    "T43-GPA_glycopeptide": {"nrps", "nrps-like", "glycopeptide"},
    "T43-BLT_betalactone": {"betalactone", "nrps", "pks", "t1pks"},
}


def cctt_trigger_corroborated(trigger: str, products: list) -> bool:
    """True if a class-defining trigger is corroborated by the BGC's product class (or is not gated)."""
    if trigger in CCTT_PROMISCUOUS:
        return True
    compat = CCTT_CLASS_COMPAT.get(trigger)
    if not compat:
        return True
    blob = " ".join(products or []).lower()
    return any(k in blob for k in compat)


def cctt_context_uncorroborated(per_bgc: dict, bgcs: list) -> list:
    """List of class-defining CCTT firings whose BGC product class does not corroborate the trigger.

    Returns [{"bgc": id, "trigger": t, "products": [...]}, …] — diagnostic; evidence-preserving (does not
    drop the firing). The judgment/claim layer treats a flagged trigger as ambiguous, not class-capacity.
    """
    prod_by_bgc = {b.bgc_id: (b.products or []) for b in (bgcs or [])}
    out = []
    for bgc_id, trigs in (per_bgc or {}).items():
        products = prod_by_bgc.get(bgc_id, [])
        for t in trigs:
            if t in CCTT_CLASS_COMPAT and not cctt_trigger_corroborated(t, products):
                out.append({"bgc": bgc_id, "trigger": t, "products": list(products)})
    return out


FLBR_PATTERNS = {
    "mod_KS": [r"modular.?ks", r"ketosynthase", r"pks ks", r"beta-ketoacyl synthase"],
    "hyb_KS": [r"hybrid.?ks", r"nrps.*pks", r"pks.*nrps"],
    "tra_KS": [r"trans.?at", r"trans-acyltransferase"],
    "mega_NRPS": [r"nonribosomal peptide synthetase"],
}


CASSETTE_PATTERNS = {
    "release_macrocyclization": [r"thioesterase", r"\bte\b", r"cyclase", r"macrocycl", r"esterase", r"reductase release"],
    "glycosylation": [r"glycosyltransferase", r"glycosyl", r"sugar", r"deoxysugar", r"gt\b"],
    "halogenation": [r"(?<!de)halogenase", r"fluorinase", r"chlorinase", r"brominase"],
    # BC2-408: same false-positive class as CCTT's T43-PHO_phosphonate (whose own guards this
    # cassette twin never received): bare "phosphonate" matches phosphonate ABC-TRANSPORTER/
    # UPTAKE annotations (not biosynthesis) and the "carboxyphosphonate"/SMCOG1231 isocitrate-
    # lyase-superfamily substring (~84% of the CCTT trigger's own over-firing on the live cohort
    # before its fix, per tests/test_cctt_token_cleanups.py); bare "pep mutase"/"phosphoenol-
    # pyruvate mutase" match the ICL-superfamily "... mutase FAMILY protein" annotation. This
    # cassette is registry entry MMC-004, TIER_1_DIAGNOSTIC/HIGH, wet_lab_routes includes
    # antibacterial_fractionation -- and the registry's OWN claim_safety text already (wrongly)
    # asserts "The regex already vetoes C-P lyase / phn transporter / utilization false-
    # positives," which was true only of the CCTT trigger, not this cassette. Mirrors T43-PHO's
    # exact guards.
    "phosphonate": [r"(?<!carboxy)phosphonate(?!.*transporter)(?!.*utilization)(?!.*c-?p lyase)(?!.*phn[g-m]\b)",
                    r"pep mutase(?!\s*family)", r"phosphoenolpyruvate mutase(?!\s*family)", r"foma", r"fomb"],
    # BC2-408 round 2: bare "nucleoside" matched primary-metabolism annotations that have nothing
    # to do with nucleoside-antibiotic (nikkomycin/polyoxin-class) biosynthesis -- verified live:
    # "nucleoside diphosphate kinase" (a universal core-metabolic enzyme present in essentially
    # every bacterial genome), "purine nucleoside phosphorylase" (purine salvage), "nucleoside
    # hydrolase" (nucleotide catabolism) all fired. CCTT's own T43-NUC_nucleoside sibling never had
    # a bare "nucleoside" token at all -- mirrors its exact set instead (anchored nikj/nikd/nikc,
    # peptidyl-nucleoside, chitin-synthase-inhibition phrase).
    "nucleoside": [r"peptidyl[- ]nucleoside", r"nikkomycin", r"polyoxin",
                   r"\bnikj\b", r"\bnikd\b", r"\bnikc\b", r"chitin synthase inhibit"],
    # BC2-408 round 2: bare "aminoglycoside" matched the aminoglycoside-modifying RESISTANCE
    # enzyme families -- verified live: "aminoglycoside phosphotransferase",
    # "aminoglycoside N-acetyltransferase", "aminoglycoside 6-adenylyltransferase" all fired.
    # These confer resistance TO aminoglycosides (self-protection/detox), not synthesis OF one --
    # the same uptake/resistance-vs-biosynthesis confusion already fixed for T43-PHO/phosphonate
    # above. CCTT's own T43-AMC_aminocyclitol sibling never carried a bare "aminoglycoside" token
    # at all -- mirrors its exact set.
    "aminoglycoside_aminocyclitol": [r"aminocyclitol", r"dois", r"btrc", r"2-deoxy-scyllo-inosose"],
    "tetronate_spirotetronate": [r"tetronate", r"spirotetronate", r"fkbh", r"(?<!acyl)glyceryl"],
    "thioamide_ycao": [r"thioamide", r"ycaO"],
    # BC2-408 round 2: bare, unanchored "lanc"/"lanm"/"lant"/"lanp" substrings -- verified live:
    # "atlantic salmon protein" and "planthopper" both fired (pure substring collisions with no
    # relation to lanthipeptide biosynthesis), and "Lant_dehydr_N"/"Lant_dehydr_C" fired via the
    # bare "lant" token the same way this file's OWN UMED_PATTERNS docstring (a few hundred lines
    # above) already diagnosed and fixed for a different dict entry ("LanT_C39_transporter_
    # peptidase"): "`lant` is an unanchored substring... so every gene in a lanthipeptide cluster
    # was bucketed as a LanT C39 transporter-peptidase." CCTT's own T43-LAN_lanthipeptide sibling
    # already guards lanc/lanm with \b word boundaries; this cassette twin never received the same
    # treatment. Mirrors CCTT's \b convention and extends it to lant/lanp using this file's own
    # already-established UMED_PATTERNS guard shape (excluding a following `_` for lant, so
    # Lant_dehydr_* still correctly excludes -- that domain is real lanthipeptide machinery, but
    # via its own dedicated match, not a substring coincidence).
    "lanthipeptide": [r"lanthipeptide", r"lantibiotic",
                       r"(?<![A-Za-z])lanc(?![A-Za-z])", r"(?<![A-Za-z])lanm(?![A-Za-z])",
                       r"(?<![A-Za-z])lant(?![A-Za-z_])", r"(?<![A-Za-z])lanp(?![A-Za-z])"],
    "lassopeptide": [r"lassopeptide", r"lasso peptide"],
    "tomm_azole_ripp": [r"azole", r"tomm", r"cyclodehydratase", r"dehydrogenase", r"ripp"],
    # BC2-408: bare "polyene" (no guard) matches "arylpolyene" as a substring -- arylpolyenes are
    # APE-type PIGMENTS, not polyene-macrolide antifungal chemistry (the exact confusion
    # scoring.py's PIGMENT_NONLEAD_CLASSES and this file's own T43-PYE trigger
    # (`(?<!aryl)polyene macrolide`) already guard against elsewhere). This cassette is registry
    # entry MMC-012, TIER_1_DIAGNOSTIC/HIGH ("Strong Candida/antifungal-track cue"), and surfaces
    # directly in the per-strain workbook's Cassette_Registry sheet (mamey/workbook.py) -- an
    # arylpolyene pigment gene firing it would misdirect real antifungal-fractionation wet-lab
    # follow-up at a pigment locus. Same negative-lookbehind convention already used on
    # "halogenation" two lines above (`(?<!de)halogenase`, guarding "dehalogenase").
    "polyene_ptm_hsaf": [r"(?<!aryl)polyene", r"hsaf", r"maltophilin", r"tetramate", r"pks-nrps"],
    "siderophore_metallophore": [r"siderophore", r"metallophore", r"nrp-metallophore", r"iron", r"ferric"],
    "transporter_resistance": [r"transporter", r"efflux", r"exporter", r"resistance", r"immunity"],
    "chitin_glycan_ecology": [r"chitinase", r"gh18", r"gh19", r"aa10", r"lpmo", r"glcnac", r"dasr"],
}

# v9.7.86 D1: explicit, hand-verified cassette-family -> registry-id crosswalk.
# The mapping is positional (the n-th CASSETTE_PATTERNS family <-> MMC-00n) but MUST be
# explicit, NOT a name-token join: a naive token join mis-resolves "tomm_azole_ripp" to
# MMK-CCTT-011 (the T43-IDC indolocarbazole marker) on the "carb-AZOLE" substring. This
# map is the single source of truth for resolving a Cassette_Registry family to its
# enriched registry_inventory description. Verified against registry_inventory_v1.9.4.
CASSETTE_REGISTRY_MAP = {
    "release_macrocyclization":      "MMC-001",
    "glycosylation":                 "MMC-002",
    "halogenation":                  "MMC-003",
    "phosphonate":                   "MMC-004",
    "nucleoside":                    "MMC-005",
    "aminoglycoside_aminocyclitol":  "MMC-006",
    "tetronate_spirotetronate":      "MMC-007",
    "thioamide_ycao":                "MMC-008",
    "lanthipeptide":                 "MMC-009",
    "lassopeptide":                  "MMC-010",
    "tomm_azole_ripp":               "MMC-011",   # NOT MMK-CCTT-011 (indolocarbazole)
    "polyene_ptm_hsaf":              "MMC-012",
    "siderophore_metallophore":      "MMC-013",
    "transporter_resistance":        "MMC-014",
    "chitin_glycan_ecology":         "MMC-015",
}

# v9.7.7 P0 guard — non-bioactivity core-gene families. CDS-product (not domain) patterns so the
# scan works in standard/bounded mode where HMM domains may be absent. Two families:
#   housekeeping  -> primary metabolism (the SID-XXX topoisomerase / dTMP-kinase false-positive class)
#   pigment       -> carotenoid/hopanoid/spore-pigment/melanin (the carotenoid-as-antifungal class)
# These are consumed by the scorer to suppress keyword credit for regions whose OWN product label is a
# weak/over-call class (NRPS-like, terpene, saccharide, arylpolyene) — i.e. antiSMASH fired on a lone
# adenylation/terpene/sugar signal embedded in housekeeping/pigment genes. A committed biosynthetic
# class (full NRPS/PKS/RiPP) or a Tier-1 CCTT diagnostic overrides the flag.
PRIMARY_METABOLISM_PATTERNS = {
    "housekeeping": [
        r"topoisomerase", r"\bgyrase\b", r"\btoprim\b", r"topoisom", r"dna_topoiso",
        r"\btopa\b", r"\bgyra\b", r"\bgyrb\b", r"\bparc\b", r"\bpare\b", r"topa_bact", r"dna_topoisoiv",
        r"thymidylate kinase", r"\bdtmp\b", r"thymidylate_kin", r"\btmk\b",
        r"ribosomal protein", r"dna polymerase", r"dna-directed rna polymerase",
        r"aminoacyl-trna", r"trna synthetase", r"trna ligase", r"elongation factor",
    ],
    "pigment": [
        r"lycopene", r"carotenoid", r"phytoene", r"\bcrti\b", r"\bcrtb\b", r"\bcrte\b",
        r"squalene-hopene", r"squalene.hopene cyclase", r"\bhopene\b", r"hopanoid",
        r"\bwhie\b", r"spore pigment", r"\bmelanin\b", r"tyrosinase",
        r"ap/?e_ks2", r"arylpolyene-specific",
    ],
    # BH-002 (v9.7.122): PQQ (pyrroloquinoline quinone) biosynthesis — primary metabolic cofactor.
    # Per project standing rule: PQQ (PqqD + PqqE/TIGR03859) → primary metabolic DROP.
    # Three annotation paths antiSMASH uses: sec_met_domains PqqD, TIGRFAM TIGR03859, or named product.
    # Precision guard: primary_flag suppresses only when own_classes ⊆ WEAK_OVERCALL_CLASSES and no
    # Tier-1 diagnostic fires — a lanthipeptide or NRPS cluster with an incidental PQQ gene is safe.
    "cofactor_pqq": [
        r"\bpqqd\b", r"\bpqqe\b", r"\bpqqf\b",         # PQQ biosynthesis enzyme family (sec_met_domain paths)
        r"\btigr03859\b",                                # TIGRFAM: PqqE radical SAM (TIGR03859)
        r"pyrroloquinoline quinone",                     # named-product path
        r"pqq biosynthesis",                             # annotation phrase variants
    ],
    # BH-006 (v9.7.122): ectoine — compatible-solute / osmolyte primary metabolism, not a drug lead.
    # Per project standing rule: ectoine → primary-metabolism DROP. Same precision guard as cofactor_pqq:
    # floors only when own_classes ⊆ WEAK_OVERCALL_CLASSES and no Tier-1 diagnostic fires, so a committed
    # cluster carrying an incidental ect gene is safe. All cohort ectoine BGCs are already Inventory —
    # this is audit/traceability hardening, not a live promotion fix.
    "cofactor_ectoine": [
        r"\bectoine\b", r"\bectoine synthase\b", r"\bectABC\b",
        r"\bectA\b", r"\bectB\b", r"\bectC\b",
        r"ectoine compatible solute",
    ],
    # Second arm (pm_guard): DNA-replication-core machinery the housekeeping family misses. Curated to
    # specific replisome/initiation terms (descriptive phrases preferred over ambiguous bare gene symbols,
    # e.g. DnaA-like ATPases) so it floors only via the same precision guard: fires only when the BGC's OWN
    # product class is a weak/over-call label and no Tier-1 diagnostic is present.
    "replication_core": [
        r"replicative dna helicase", r"replicative helicase", r"\bdnab\b",
        r"dna primase", r"\bdnag\b", r"primosom",
        r"chromosomal replication init", r"replication initiator protein",
        r"dna polymerase iii", r"\bdnae\b", r"\bdnan\b", r"sliding clamp", r"dna sliding clamp",
        r"single.stranded dna.binding", r"\bdna ligase\b", r"\breplisome\b", r"replication fork",
    ],
}

# v9.7.240 (P3): four UMED buckets were built from bare gene-symbol substrings and
# space-separated domain names. Both shapes misfire on antiSMASH annotation text.
#
#   * `lant` is an unanchored substring. It matched `lanthipeptide`, `Lant_dehydr_N`,
#     `Lant_dehydr_C` and `Lanthipeptide_LanB_RRE` — so every gene in a lanthipeptide
#     cluster was bucketed as a LanT C39 transporter-peptidase. On AS-XXX: 14 hits,
#     including three 44 aa RamS precursors, the LanKC, both LanBs and both LanCs.
#     None of them carries a C39 or a peptidase domain. `Lant_dehydr_*` in particular
#     is the LanB DEHYDRATASE, the opposite end of the pathway from LanT.
#   * antiSMASH writes `Peptidase_S9`, not `peptidase s9`, so that pattern never fired:
#     AS-XXX's real class-III leader-protease candidate (ctg13_105, Peptidase_S9 +
#     Peptidase_S9_N) landed in no bucket while FlaP_AplP_S9_protease reported 0.
#     `\brre\b` fails on `Lanthipeptide_LanB_RRE` for the same reason — `_` is a word
#     character, so there is no word boundary before `RRE`.
#
# Guards are asymmetric on purpose, and the asymmetry is the whole fix:
#   `lant` -> reject a following letter OR `_`  (blocks Lant_dehydr_N, LanTHipeptide)
#   `rre`  -> reject a following/preceding letter only (`_RRE` must still match)
# M16B / YcaO_TfuA / nucleoside_maturation are deliberately UNTOUCHED: their symbols
# legitimately appear as prefixes (nikkomycin `nikS`, `M16B`), so guarding them would
# cut recall rather than precision.
#
# These literals must stay bit-identical to registry_inventory_v1.9.4.json's mamey_umed
# entries and to mamey_markers.py MMK-UMED-00{1,2,3,6}; tests/test_b2_registry_parity.py
# enforces the first, tools/gen_marker_catalog.py regenerates from the second.
UMED_PATTERNS = {
    "LanP_S8_protease": [r"(?<![A-Za-z])lanp(?![A-Za-z])", r"subtilisin", r"peptidase[ _-]?s8", r"serine protease"],
    "LanT_C39_transporter_peptidase": [r"(?<![A-Za-z])lant(?![A-Za-z_])", r"(?<![A-Za-z])c39(?![A-Za-z])", r"peptidase.*abc", r"abc.*peptidase"],
    "FlaP_AplP_S9_protease": [r"(?<![A-Za-z])flap(?![A-Za-z])(?!\s*endonuclease)", r"(?<![A-Za-z])aplp(?![A-Za-z])", r"peptidase[ _-]?s9"],
    "M16B_metalloprotease": [r"m16", r"metalloprotease", r"pitrilysin"],
    "YcaO_TfuA_thioamide": [r"ycao", r"tfua", r"thioamide"],
    "RiPP_RRE": [r"ripp recognition element", r"(?<![A-Za-z])rre(?![A-Za-z])"],
    "nucleoside_maturation": [r"nik", r"nucleoside", r"radical sam", r"aminotransferase"],
}

TFBS_MOTIFS = {
    "DasR_like_palindrome": ["TGTCTAGACNA", "TGTNANNNNNNTNACA"],
    "DmdR_iron_box_like": ["TTAGGTTAGGCTAACCTAA"],
    "LexA_SOS_like": ["CTGTATATATATACAG", "CGAACNNNNGTTCG"],
    "BldD_like": ["GTCTAGAC"],
    "FuR_like": ["GATAATGATAATCATTATC"],
    "Zur_like": ["AAATGTTATAACATTT"],
    "IolR_like": ["TGTGANNNNNNTCACA"],
    "PhoP_box_like": ["GTTCANNNNNGTTC"],
    "ANR_FNR_like": ["TTGATNNNNATCAA"],
    "GBL_AdpA_like": ["TGGCSNGWWY"],
    "SARP_BTAD_like": ["TCGAGNNNNCTCGA"],
    "PAS_LuxR_like": ["ACCTGTNNNNACAGGT"],
}

# ---------------------------------------------------------------------------
# B2 Phase 1 — registry-backed detection.
#
# The dict literals above are the historical hand-maintained patterns and now
# serve as the in-code FALLBACK + parity reference. The canonical source of
# truth is registry_inventory_v1.9.4.json, loaded via registry_detector. When
# the registry is present and self-consistent, we reassign the module globals
# from it; the registry-derived dicts are asserted bit-identical to these
# literals by tests/test_b2_registry_parity.py (the regression anchor).
#
# Only regex/motif targets fire in Phase 1. HMM/DIAMOND/BLASTP/manual markers
# (e.g. T43-TOMM, the 29 HMM-only markers) ride along as catalog and do NOT
# expand detection until the Phase-2 wiring runs where those tools exist. Set
# MAMEY_DISABLE_REGISTRY_DETECTOR=1 to force the in-code fallback.
# ---------------------------------------------------------------------------
REGISTRY_DETECTOR_ACTIVE = False
try:  # pragma: no cover - exercised via parity test, guarded for robustness
    import os as _os

    if _os.environ.get("MAMEY_DISABLE_REGISTRY_DETECTOR") != "1":
        from . import registry_detector as _rd

        _built = _rd.build_pattern_dicts()
        # Reassign module globals in place. If any name is absent from the
        # build the hardcoded literal is left untouched (defensive).
        for _name, _dict in _built.items():
            globals()[_name] = _dict
        REGISTRY_DETECTOR_ACTIVE = True
except Exception as _reg_exc:  # noqa: BLE001 - never let registry issues break scanning
    # Any failure (missing file, schema drift, count mismatch) falls back to
    # the hardcoded literals above. Detection continues unchanged.
    REGISTRY_DETECTOR_ACTIVE = False
    from . import degradation as _degradation_mod
    _degradation_mod.record("source_scans.registry_detector_activation", _reg_exc)


def _hay(cds: CDSFeature) -> str:
    # Annotation search haystack only.  Do not include /translation or raw
    # nucleotide sequence: those fields make regex scans slow and can trigger
    # catastrophic backtracking for patterns like abc.*peptidase.
    vals = [cds.product or "", cds.locus_tag or ""]
    skip = {"translation", "nucleotide_seq", "sequence"}
    for k, v in cds.qualifiers.items():
        if str(k).lower() in skip:
            continue
        vals.append(str(k))
        vals.extend(str(x) for x in v[:8])
    return " ".join(vals).lower()

# PERF-05: precompile marker patterns once instead of re-invoking re.search on
# UNCOMPILED string patterns for every CDS x marker x pattern (~4.19M compile-cache
# lookups per run). The pattern dicts passed to _scan_patterns are module-level
# constants (or the registry-detector reassignments made at import) whose identity is
# stable for the process, so we cache the compiled form keyed by the dict's id(). The
# stored reference to the source dict keeps it alive (so id() cannot be reused) and lets
# us confirm identity on hit. re.compile(p, re.I).search(h) is exactly equivalent to
# re.search(p, h, flags=re.I), so scan output is byte-identical.
_COMPILED_PATTERN_CACHE: dict[int, tuple[dict, dict]] = {}


def _compiled_patterns(patterns: dict[str, list[str]]) -> dict[str, list]:
    """Return {group: [compiled-regex, ...]} for `patterns`, compiled once and cached."""
    key = id(patterns)
    cached = _COMPILED_PATTERN_CACHE.get(key)
    if cached is not None and cached[0] is patterns:
        return cached[1]
    compiled = {group: [re.compile(p, re.I) for p in pats] for group, pats in patterns.items()}
    _COMPILED_PATTERN_CACHE[key] = (patterns, compiled)
    return compiled


def _scan_patterns(cds_list: list[CDSFeature], patterns: dict[str, list[str]]) -> dict[str, Any]:
    compiled = _compiled_patterns(patterns)
    buckets = {k: [] for k in patterns}
    for cds in cds_list:
        h = _hay(cds)
        for group, pats in compiled.items():
            if any(p.search(h) for p in pats):
                buckets[group].append({"contig": cds.contig, "start": cds.start, "end": cds.end, "strand": cds.strand, "locus_tag": cds.locus_tag, "product": cds.product})
    return {"status": "SOURCE_DERIVED", "counts": {k: len(v) for k, v in buckets.items()}, "hits": buckets, "claim_safety": "Annotation/keyword-derived first pass; confirm with HMMER/BLAST before manuscript use."}

def _bgc_overlap_or_near(cds: CDSFeature, bgc: BGCRecord, flank: int = 10000) -> bool:
    return cds.contig == bgc.contig and not (cds.end < bgc.start - flank or cds.start > bgc.end + flank)

def bgc_coupling(bgcs: list[BGCRecord], scan_hits: dict[str, Any], flank: int = 10000) -> dict[str, list[str]]:
    by_bgc = defaultdict(list)
    for group, hits in scan_hits.get("hits", {}).items():
        for h in hits:
            fake = CDSFeature(h["contig"], h["start"], h["end"], h.get("strand", 0), h.get("locus_tag"), h.get("product"), None, {})
            for bgc in bgcs:
                if _bgc_overlap_or_near(fake, bgc, flank=flank):
                    by_bgc[bgc.bgc_id].append(group)
    return {k: sorted(set(v)) for k, v in by_bgc.items()}

# ---- related-family vetoes: CCTT/resistance diagnostics over-call on cross-reacting relatives ----
# A class-definitive call must beat its nearest cross-reacting family at the same locus. Three cases
# caught in the SID campaign: glycogen/trehalose sugar-kinase APH -> false T43-NUC + T1; hglE/hglD
# glycolipid ketosynthase -> false T43-ENE (PREV-001 cross-reaction with ene_KS).
VETO_CONTEXT_PATTERNS = {
    "glycogen_trehalose": [r"glycogen", r"trehalose", r"malto-?oligosyl", r"\btrey\b", r"\btres\b",
                           r"\bglgx\b", r"\bglgb\b", r"\bglge\b", r"4-alpha-glucan", r"alpha-amylase",
                           r"\bcbm_?48\b", r"pullulanase", r"isoamylase", r"glucan branching"],
    "hglE_hglD": [r"\bhgle\b", r"\bhgld\b", r"hgle-ks", r"heterocyst glycolipid"],
    "sugar_kinase": [r"sugar kinase", r"carbohydrate kinase", r"hexokinase", r"fructokinase",
                     r"galactokinase", r"sugar-phosphate kinase", r"ribokinase"],
    "copalyl_terpene": [r"copalyl", r"\bcdps\b.{0,4}diphosphate", r"diphosphate synthase",
                        r"geranylgeranyl", r"\bggps\b", r"ent-copalyl", r"terpene cyclase",
                        r"ent-cdps", r"\bipps\b", r"isopentenyl"],
}

# v9.7.33 #28 — mobile-element / ICE gene families (gene-level, annotation-based). The HGT guard reads these so
# a region built of mobility machinery but mis-typed by antiSMASH as a biosynthetic class (e.g. an ICE that
# antiSMASH labels "lanthipeptide-class-v") is still recognized as mobile context. CORE = mobility determinants;
# the rest are accessory ICE/conjugation/defense genes that, together with a core gene, signal an ICE-like locus.
MOBILE_ELEMENT_PATTERNS = {
    "integrase":     [r"\bintegrase\b", r"phage integrase", r"tyrosine integrase", r"\bxis\b"],
    "recombinase":   [r"\brecombinase\b", r"site-specific recombinase", r"\bxerc\b", r"\bxerd\b", r"serine recombinase"],
    "transposase":   [r"\btransposase\b", r"\btransposon\b", r"insertion sequence", r"\btnp\b", r"\bis[0-9]{2,}\b"],
    "conjugation":   [r"\bftsk\b", r"\bspoiiie\b", r"conjugal", r"conjugative", r"type iv secretion", r"\brelaxase\b", r"\bmobl\b"],
    "tox_repeat":    [r"\brhs\b", r"rhs repeat", r"\bwxg\b", r"\blxg\b", r"\byd repeat\b"],
    "rep_initiator": [r"replication initiat", r"\brepa\b", r"\brepb\b", r"plasmid replication"],
}
MOBILE_ELEMENT_CORE = {"integrase", "recombinase", "transposase"}

def _region_context(cds_list: list, bgc, flank: int = 10000) -> set:
    ctx = set()
    for cds in cds_list:
        if not _bgc_overlap_or_near(cds, bgc, flank=flank):
            continue
        h = _hay(cds)
        for fam, pats in VETO_CONTEXT_PATTERNS.items():
            if any(re.search(p, h, flags=re.I) for p in pats):
                ctx.add(fam)
    return ctx


def _mobile_context(cds_list: list, bgc, flank: int = 10000) -> set:
    """v9.7.33 #28 — gene-level mobile-element families found in/near the BGC region. Mirrors _region_context but
    scans MOBILE_ELEMENT_PATTERNS, so an ICE/transposon mis-typed as a biosynthetic class is still detected."""
    fams = set()
    for cds in cds_list:
        if not _bgc_overlap_or_near(cds, bgc, flank=flank):
            continue
        h = _hay(cds)
        for fam, pats in MOBILE_ELEMENT_PATTERNS.items():
            if any(re.search(p, h, flags=re.I) for p in pats):
                fams.add(fam)
    return fams


# CCTT marker -> (veto context family, own-class product token, note)
CCTT_VETOES = {
    "T43-NUC_nucleoside": ("glycogen_trehalose", "nucleoside",
                           "sugar-kinase/glycogen-trehalose context (APH misreads as nucleoside)"),
    "T43-ENE_enediyne":   ("hglE_hglD", "enediyne",
                           "hglE/hglD glycolipid ketosynthase cross-reacts with ene_KS (PREV-001)"),
    "T43-DKP_cdps":       ("copalyl_terpene", "cyclodipeptide",
                           "copalyl diphosphate synthase (ent-CDPS, a terpene cyclase) collides with the "
                           "cyclodipeptide synthase (CDPS) gene token — veto unless region is typed cyclodipeptide"),
}

def _region_domain_names(cds_list: list, bgc, flank: int = 10000) -> set:
    """Collect domain/family names annotated on CDS in/near a BGC region — the substrate the
    tetronate cassette grader needs. Pulls from each CDS's searchable text (sec_met, PFAM/TIGR,
    product) so FkbH / FabH-KSIII / Diels-Alderase presence can be graded."""
    names: set = set()
    for cds in cds_list:
        if not _bgc_overlap_or_near(cds, bgc, flank=flank):
            continue
        h = _hay(cds)
        # named domains the grader keys on (FkbH/PF04113 starter; FabH/KSIII closure; Diels-Alderase spiro)
        for tok in ("FkbH", "PF04113", "fabH", "ACP_syn_III", "ksIII", "PF08541", "PF08545",
                    "Diels_aldr", "PF13570", "PP-binding", "PF00550", "ACP", "PCP", "Chal_sti_synt_N",
                    "Chal_sti_synt_C"):
            if re.search(re.escape(tok), h, flags=re.I):
                names.add(tok)
    return names


def apply_cctt_vetoes(cctt: dict, bgcs: list, cds_list: list) -> dict:
    """Drop a class-definitive CCTT call when a dominant cross-reacting family is in-region and the
    region is not independently typed as that class. Records what was vetoed for the audit trail.

    v9.7.194: also grade a co-firing T43-TET (tetronate) via `tetronate_cassette_completeness` and,
    when T43-PTM and T43-TET co-fire on the same BGC, record a PTM-vs-TET precedence annotation.
    FkbH is necessary-not-sufficient — a starter-only FkbH does NOT raise tetronate over PTM (it also
    feeds non-tetronate glyceryl routes); only a FabH/KSIII closure or a Diels-Alderase does. This
    wires the previously-orphaned grader into the real co-fire site (AS-XXX BGC020 case)."""
    coupling = cctt.get("bgc_coupling", {})
    by_id = {b.bgc_id: b for b in bgcs}
    vetoed = {}
    tet_grades = {}
    ptm_tet_precedence = {}
    try:
        from .antismash_evidence import tetronate_cassette_completeness
    except Exception as _deg_exc:
        tetronate_cassette_completeness = None
        from . import degradation as _degradation
        _degradation.record("source_scans.apply_cctt_vetoes.tetronate_completeness", _deg_exc)
    for bgc_id, markers in list(coupling.items()):
        bgc = by_id.get(bgc_id)
        if not bgc:
            continue
        ctx = _region_context(cds_list, bgc)
        kept, drops = [], []
        for m in markers:
            v = CCTT_VETOES.get(m)
            if v and v[0] in ctx and v[1] not in {t.strip() for t in re.split(r"[;,/|]+|\s+", " ".join(bgc.products).lower()) if t.strip()}:
                drops.append({"marker": m, "reason": v[2]})
                continue
            kept.append(m)
        coupling[bgc_id] = kept
        if drops:
            vetoed[bgc_id] = drops
        # tetronate cassette grade + PTM/TET co-fire precedence (uses the kept markers)
        has_tet = any(m.startswith("T43-TET") for m in kept)
        has_ptm = any(m.startswith("T43-PTM") for m in kept)
        if has_tet and tetronate_cassette_completeness is not None:
            doms = _region_domain_names(cds_list, bgc)
            grade = tetronate_cassette_completeness(doms)
            tet_grades[bgc_id] = grade
            if has_ptm:
                g = grade.get("grade", "")
                if g in ("TET_CASSETTE_SPIRO", "TET_CASSETTE_COMPLETE"):
                    note = ("tetronate ring-closure supported (FkbH + FabH-KSIII/Diels-Alderase) — "
                            "spirotetronate call takes precedence; PTM co-fire is KCB/tetramate "
                            "cross-reactivity (PTM and tetronate are tetramate-adjacent)")
                elif g in ("TET_CASSETTE_STARTER_ONLY", "TET_NO_STARTER"):
                    note = ("FkbH starter-only / absent — tetronate NOT ring-closure-supported; "
                            "PTM call retains precedence, T43-TET is starter-signal only")
                else:  # INDETERMINATE (edge-truncated)
                    note = ("tetronate ring-closure indeterminate (edge-truncated) — PTM vs "
                            "spirotetronate unresolved; long-read closure needed. Neither call "
                            "asserted; product identity requires isolation")
                ptm_tet_precedence[bgc_id] = {"grade": grade.get("grade"), "note": note}
    cctt["bgc_coupling"] = {k: v for k, v in coupling.items() if v}
    cctt["related_family_vetoes"] = vetoed
    if tet_grades:
        cctt["tetronate_cassette_grades"] = tet_grades
    if ptm_tet_precedence:
        cctt["ptm_tet_precedence"] = ptm_tet_precedence
    cctt["veto_claim_safety"] = ("Related-family vetoes applied: NUC vetoed in glycogen/trehalose context; "
                                 "ENE vetoed in hglE/hglD (PREV-001) context, unless the region is independently "
                                 "typed as that class.")
    return cctt


def couple_kcb_ptm(bgcs: list[BGCRecord], cctt: dict, flbr: dict) -> dict:
    """v9.7.19 §4-sibling for the HSAF/PTM antifungal class. The CDS-only T43-PTM scan misses
    KCB-identified HSAF/PTM clusters because the identity lives in the knownclusterblast neighbourhood,
    not the product label (e.g. AS-XXX BGC020: a generic `NRPS,T1PKS` label but a KCB neighbourhood naming
    heat-stable-antifungal-factor / maltophilin / xanthobaccin, single hybrid-KS architecture). Per BGC,
    also test the KCB anchor (kcb_top + mibig_hits + closest_candidate_kcb_product) — Route A — and a LONE
    hybrid-KS megasynthase architecture carrying a tetramate/macrolactam signal — Route B, KCB-name-
    independent. The SPECIFIC compound-name terms (the active T43-PTM pattern, sourced from the registry
    when active) keep this from firing on generic NRPS/PKS; Route B is gated on `mod_KS` being ABSENT (a
    single hybrid megasynthase, not a multi-module assembly line) so a generic hybrid does not trip it.
    Adds the T43-PTM trigger to bgc_coupling; the AF diagnostic bonus then applies via AF_DIAGNOSTIC_TRIGGERS."""
    coupling = cctt.setdefault("bgc_coupling", {})
    flbr_cpl = (flbr or {}).get("bgc_coupling", {})
    ptm_terms = CCTT_PATTERNS.get("T43-PTM_hsaf_tetramate", [])   # tracks the active (registry or literal) pattern
    ptm_re = re.compile("|".join(ptm_terms), re.I) if ptm_terms else None
    routes: dict[str, str] = {}
    TRIG = "T43-PTM_hsaf_tetramate"
    for bgc in bgcs:
        if TRIG in coupling.get(bgc.bgc_id, []):
            continue  # already fired via the CDS scan
        parts = list(bgc.products) + list(getattr(bgc, "mibig_hits", []) or [])
        if bgc.kcb_top:
            parts.append(bgc.kcb_top)
        ccp = getattr(bgc, "closest_candidate_kcb_product", "")
        if ccp and ccp != "UNRESOLVED":
            parts.append(ccp)
        ev = " ".join(parts).lower()
        fl = set(flbr_cpl.get(bgc.bgc_id, []))
        lone_hybrid = ("hyb_KS" in fl) and ("mod_KS" not in fl)      # single hybrid megasynthase, not multi-module
        route_a = bool(ptm_re.search(ev)) if ptm_re else False       # KCB/product names the PTM compound
        route_b = lone_hybrid and bool(re.search(r"tetramate|macrolactam", ev))  # architecture + tetramate class
        if route_a or route_b:
            coupling[bgc.bgc_id] = sorted(set(coupling.get(bgc.bgc_id, []) + [TRIG]))
            routes[bgc.bgc_id] = "kcb_anchor" if route_a else "lone_hybrid_architecture"
    cctt["ptm_kcb_coupling"] = routes
    return cctt


def reverse_complement(seq: str) -> str:
    return seq.translate(str.maketrans("ACGTNacgtn", "TGCANtgcan"))[::-1]


def motif_to_regex(motif: str) -> str:
    m = motif.upper()
    repl = {"N": "[ACGT]", "W": "[AT]", "S": "[GC]", "R": "[AG]", "Y": "[CT]"}
    return "".join(repl.get(ch, re.escape(ch)) for ch in m)

def scan_tfbs(contigs: dict[str, str], cds_list: list[CDSFeature], upstream_bp: int = 300) -> dict[str, Any]:
    hits = []
    for cds in cds_list:
        seq = contigs.get(cds.contig)
        if not seq:
            continue
        if cds.strand >= 0:
            s, e = max(0, cds.start - upstream_bp - 1), max(0, cds.start - 1)
            window, window_start = seq[s:e].upper(), s + 1
        else:
            s, e = min(len(seq), cds.end), min(len(seq), cds.end + upstream_bp)
            window, window_start = reverse_complement(seq[s:e]).upper(), s + 1
        for motif_name, motifs in TFBS_MOTIFS.items():
            for motif in motifs:
                for m in re.finditer(motif_to_regex(motif), window):
                    hits.append({"motif": motif_name, "pattern": motif, "contig": cds.contig, "approx_position": window_start + m.start(), "target_locus": cds.locus_tag, "target_product": cds.product, "strand": cds.strand})
    counts = defaultdict(int)
    for h in hits:
        counts[h["motif"]] += 1
    return {"status": "MOTIF_SCAN_PRELIMINARY", "upstream_bp": upstream_bp, "counts": dict(counts), "hits": hits[:1000], "total_hits": len(hits), "claim_safety": "Simple motif scan; replace with calibrated TFBS models/background scoring before manuscript use."}

def scan_blda_tta(cds_list: list[CDSFeature], bgcs: list[BGCRecord], organism: str = "") -> dict[str, Any]:
    # v9.7.87 Item A: bldA-dependent translational control is actinomycete-specific. On a
    # non-actinomycete the TTA codons counted below are GC-content noise, not a developmental
    # signal — so the per-BGC tier must ALSO report NOT_APPLICABLE, not a T1–T4 tier. v9.7.86
    # P-9 fixed only the adapter's scan VERDICT; this gates the per-BGC tier (surfaced by the
    # A3 manifest field) so the manifest is internally consistent on non-actino genomes.
    from .cohort_resolver import actino_status as _actino_status
    _non_actino = _actino_status(organism or "") == "non_actinomycete"

    per_bgc = {b.bgc_id: {"tta_codons": 0, "total_codons": 0, "tta_cds": 0, "total_cds": 0, "tta_loci": []} for b in bgcs}
    for cds in cds_list:
        nt = (cds.nucleotide_seq or "").upper()
        codons = [nt[i:i+3] for i in range(0, len(nt) - 2, 3)] if nt else []
        tta_count = sum(1 for c in codons if c == "TTA")
        for bgc in bgcs:
            if _bgc_overlap_or_near(cds, bgc, flank=0):
                per_bgc[bgc.bgc_id]["total_cds"] += 1
                per_bgc[bgc.bgc_id]["total_codons"] += len(codons)
                per_bgc[bgc.bgc_id]["tta_codons"] += tta_count
                if tta_count:
                    per_bgc[bgc.bgc_id]["tta_cds"] += 1
                    per_bgc[bgc.bgc_id]["tta_loci"].append(cds.locus_tag)
    for bgc_id, d in per_bgc.items():
        if _non_actino:
            # TTA counts are still recorded (above) for transparency, but no tier is asserted.
            d["bldA_tier"] = "NOT_APPLICABLE"
            d["bldA_interpretation"] = ("bldA/TTA gating is actinomycete-specific; "
                                        f"{organism or 'this organism'} is non-actinomycete — "
                                        "TTA counts are GC-content noise, not a developmental signal.")
            continue
        if d["tta_codons"] == 0:
            d["bldA_tier"] = "T1"
            d["bldA_interpretation"] = "No TTA codons detected in BGC CDS."
        elif d["tta_codons"] <= 2:
            d["bldA_tier"] = "T2"
            d["bldA_interpretation"] = "Low TTA burden; possible minor bldA sensitivity."
        elif d["tta_codons"] <= 5:
            d["bldA_tier"] = "T3"
            d["bldA_interpretation"] = "Moderate TTA burden; bldA-sensitive expression is plausible."
        else:
            d["bldA_tier"] = "T4"
            d["bldA_interpretation"] = "High TTA burden; strongly bldA-sensitive lead flag."
    _status = "NOT_APPLICABLE" if _non_actino else "SOURCE_DERIVED"
    return {"status": _status, "per_bgc": per_bgc, "organism_actino_gated": _non_actino,
            "claim_safety": "TTA codons counted from CDS nucleotide sequence extracted from GenBank features. T4 marks >=6 TTA codons. Per-BGC tier is NOT_APPLICABLE on non-actinomycetes (v9.7.87)."}

def scan_cassettes(cds_list: list[CDSFeature], bgcs: list[BGCRecord]) -> dict[str, Any]:
    scan = _scan_patterns(cds_list, CASSETTE_PATTERNS)
    coupling = bgc_coupling(bgcs, scan, flank=5000)
    per_bgc = {}
    for bgc in bgcs:
        cats = coupling.get(bgc.bgc_id, [])
        per_bgc[bgc.bgc_id] = {
            "cassette_families": cats,
            "cassette_count": len(cats),
            "cassette_status": "SOURCE_SUPPORTED" if cats else "NO_SOURCE_DERIVED_CASSETTE"
        }
    scan.update({"bgc_coupling": coupling, "per_bgc": per_bgc})
    return scan

def scan_umed(cds_list: list[CDSFeature], bgcs: list[BGCRecord]) -> dict[str, Any]:
    scan = _scan_patterns(cds_list, UMED_PATTERNS)
    coupling = bgc_coupling(bgcs, scan, flank=5000)
    per_bgc = {}
    for bgc in bgcs:
        product_text = " ".join(bgc.products).lower()
        # BH-005: token-split before membership test so "thioamide" does not match inside
        # "thioamide-NRP" (its own assembly-line class, not RiPP-style maturation), nor
        # "nucleoside" inside "nucleoside-sugar".
        _prod_tokens = {t.strip() for t in re.split(r"[;,/|]+|\s+", product_text) if t.strip()}
        needs_maturation = any(x in _prod_tokens for x in ["ripp", "lanthipeptide", "lassopeptide", "thioamide", "azole", "nucleoside"])
        hits = coupling.get(bgc.bgc_id, [])
        if needs_maturation and hits:
            verdict = "IN_CLUSTER_OR_PROXIMAL_MATURATION_SOURCE_SUPPORTED"
        elif needs_maturation and not hits:
            verdict = "MATURATION_GAP_SOURCE_DERIVED"
        else:
            verdict = "NOT_MATURATION_GATED"
        per_bgc[bgc.bgc_id] = {"needs_maturation": needs_maturation, "umed_hits": hits, "verdict": verdict}
    scan.update({"bgc_coupling": coupling, "per_bgc": per_bgc, "claim_safety": "Source-derived maturation scan; HMMER confirmation still recommended."})
    return scan

def scan_efls(bgcs: list[BGCRecord], cassettes: dict[str, Any], cctt: dict[str, Any], flbr: dict[str, Any]) -> dict[str, Any]:
    """Preliminary shared-evidence linkage scan.

    Pairing scope is all-vs-all, but output is filtered to pairs where at
    least one member is Edge or Full-contig. This captures Interior+Edge
    split-pathway scenarios, such as an interior macrolide core with an
    edge-truncated saccharide/tailoring arm.
    """
    candidates = []
    cassette_map = cassettes.get("per_bgc", {})
    cctt_map = cctt.get("bgc_coupling", {})
    # v9.7.409 (DEEP_AUDIT2_resource_dos #3): bound the all-vs-all pair scan (and its candidate list)
    # to a sane BGC count. Output was already sliced [:500]; this bounds the WORK too.
    from .pair_scan_caps import cap_pair_scan_items
    bgcs = cap_pair_scan_items(bgcs, label="scan_efls")
    for i, a in enumerate(bgcs):
        for b in bgcs[i+1:]:
            if a.edge_status == "Interior" and b.edge_status == "Interior":
                continue
            shared_products = sorted(set(x.lower() for x in a.products) & set(x.lower() for x in b.products))
            shared_mibig = sorted(set(a.mibig_hits) & set(b.mibig_hits))
            ca = set(cassette_map.get(a.bgc_id, {}).get("cassette_families", []))
            cb = set(cassette_map.get(b.bgc_id, {}).get("cassette_families", []))
            shared_cassettes = sorted(ca & cb)
            cta = set(cctt_map.get(a.bgc_id, []))
            ctb = set(cctt_map.get(b.bgc_id, []))
            shared_cctt = sorted(cta & ctb)

            # Weight known shared references more heavily, but allow
            # cassette/CCTT/product overlap to nominate source-derived pairs.
            score = len(shared_products) + 2 * len(shared_mibig) + len(shared_cassettes) + len(shared_cctt)
            if score:
                relation = "COMPLEMENTARY_OR_SHARED_EVIDENCE" if score >= 3 else "WEAK_SHARED_EVIDENCE"
                candidates.append({
                    "bgc_a": a.bgc_id,
                    "bgc_b": b.bgc_id,
                    "edge_status_a": a.edge_status,
                    "edge_status_b": b.edge_status,
                    "score": score,
                    "relation": relation,
                    "shared_products": shared_products,
                    "shared_mibig": shared_mibig,
                    "shared_cassettes": shared_cassettes,
                    "shared_cctt": shared_cctt
                })
    return {
        "status": "SOURCE_DERIVED_PRELIMINARY_LINKAGE",
        "pairing_scope": "all_vs_all_filtered_to_at_least_one_edge_or_full_contig",
        "candidate_pairs": sorted(candidates, key=lambda x: x["score"], reverse=True)[:500],
        "candidate_pair_count": len(candidates),
        "claim_safety": "Preliminary shared-evidence linkage only; not physical contig linkage or Jaccard protein-overlap confirmation.",
        "flbr_context": {"flag": flbr.get("flbr_flag"), "grade": flbr.get("flbr_grade")}
    }

def scan_flbr(cds_list: list[CDSFeature], bgcs: list[BGCRecord]) -> dict[str, Any]:
    scan = _scan_patterns(cds_list, FLBR_PATTERNS)
    total_ks = sum(scan["counts"].get(k, 0) for k in ["mod_KS", "hyb_KS", "tra_KS"])
    total_mega = total_ks + scan["counts"].get("mega_NRPS", 0)
    fragmented_bgcs = [b.bgc_id for b in bgcs if b.edge_status in {"Edge", "Full-contig"} and any(x in " ".join(b.products).lower() for x in ["pks", "nrps", "transat"])]
    if total_ks >= 4 and fragmented_bgcs:
        flag, grade = "LMPKS_FRAGMENT_SET", "STRONG"
    elif total_mega >= 4 or fragmented_bgcs:
        flag, grade = "MEGASYNTHASE_FRAGMENT_SUSPECT", "WEAK"
    else:
        flag, grade = "NULL", "NULL"
    orphan = scan_orphan_megasynthase_motifs(cds_list, bgcs)
    _link_orphans_to_fragmented(orphan["ks_bearing"], bgcs, fragmented_bgcs)
    rescue = _rescue_readiness(bgcs, len(orphan["ks_bearing"]), len(orphan["at_only"]), len(fragmented_bgcs))
    scan.update({"flbr_flag": flag, "flbr_grade": grade, "genome_wide_ks_like_count": total_ks, "genome_wide_megasynthase_like_count": total_mega, "fragmented_megasynthase_bgcs": fragmented_bgcs, "bgc_coupling": bgc_coupling(bgcs, scan),
                 "orphan_megasynthase_candidates": orphan["ks_bearing"],
                 "orphan_at_hydrolase_ambiguous": orphan["at_only"],
                 "orphan_megasynthase_claim_safety": "Tier-1 (orphan_megasynthase_candidates): KS active-site motif (DTACSSS) on a CDS outside every called cluster (core ±20 kb flank, contig matched on node id/length not coverage). Candidate megasynthase fragment — motif-derived, NOT a confirmed domain; KS+AT co-occurrence is the strongest signal; physical linkage to any region is unproven (candidate co-locus, long-read/gap-PCR required). Tier-2 (orphan_at_hydrolase_ambiguous): AT/GHSxG ONLY — the alpha/beta-hydrolase nucleophile elbow shared by esterases/thioesterases/lipases/epoxide-hydrolases/dehalogenases/peptidases. NOT megasynthase evidence on its own; most parsimoniously a standalone hydrolase (especially at 250-400 aa). Listed for completeness, not as a lead.",
                 "orphan_linkage_claim_safety": "Per-orphan rescue work-order (Tier-1 KS only). same_contig: gap_estimate_bp is the exact coordinate distance to the named fragmented megasynthase's nearest edge — a gap-PCR/long-read target; candidate co-locus, NOT a confirmed join. cross_contig: orphan is on a separate contig from every called cluster; candidate_partner_bgcs names the fragmented PKS-class leads it could rejoin, but the specific pairing is unresolvable without long-read/assembly-graph evidence.",
                 **rescue})
    return scan


def _link_orphans_to_fragmented(ks_orphans: list[dict[str, Any]], bgcs: list[BGCRecord],
                                fragmented_ids: list[str]) -> list[dict[str, Any]]:
    """Per-orphan rescue work-order: pair each Tier-1 KS orphan to a fragmented megasynthase lead. Mutates
    each orphan dict in place. same_contig => exact coordinate gap_estimate_bp (gap-PCR/long-read target);
    cross_contig => unresolvable without long-read/assembly-graph, so the candidate fragmented PKS-class
    partners are named, not paired. Claim-safe: candidate co-locus, NOT a confirmed join."""
    frag_set = set(fragmented_ids)
    frag = [b for b in bgcs if b.bgc_id in frag_set]
    by_contig: dict[str, list[BGCRecord]] = {}
    for b in frag:
        by_contig.setdefault(_contig_key(b.contig), []).append(b)
    frag_pks_ids = [b.bgc_id for b in frag
                    if any(x in " ".join(b.products).lower() for x in ("pks", "transat"))]

    def _gap(o: dict[str, Any], b: BGCRecord) -> int:
        if o["end"] < b.start:
            return b.start - o["end"]
        if o["start"] > b.end:
            return o["start"] - b.end
        return 0

    for o in ks_orphans:
        same = by_contig.get(_contig_key(o["contig"]), [])
        if same:
            nb = min(same, key=lambda b: _gap(o, b))
            o["nearest_fragmented_bgc"] = nb.bgc_id
            o["gap_estimate_bp"] = _gap(o, nb)
            o["linkage"] = "same_contig"
        else:
            o["nearest_fragmented_bgc"] = None
            o["gap_estimate_bp"] = None
            o["linkage"] = "cross_contig"
            o["candidate_partner_bgcs"] = frag_pks_ids
    return ks_orphans


def _rescue_readiness(bgcs: list[BGCRecord], orphan_ks_count: int, orphan_at_count: int,
                      fragmented_count: int) -> dict[str, Any]:
    """Genome-level contig-rescue triage signal. High orphan-KS + fragmented-megasynthase counts on a
    sub-Good assembly => reassembly/long-read would likely rejoin megasynthase fragments into complete
    clusters. Heuristic triage aid, NOT a claim about any specific cluster. Orphan KS = Tier-1 only."""
    total = len(bgcs) or 1
    interior = sum(1 for b in bgcs if getattr(b, "edge_status", None) == "Interior")
    interior_frac = round(interior / total, 3)
    not_good = interior_frac < 0.70   # rescue is only meaningful below Good assembly
    if not_good and orphan_ks_count >= 3 and fragmented_count >= 5:
        tier = "HIGH"
    elif not_good and (orphan_ks_count >= 1 or fragmented_count >= 3):
        tier = "MODERATE"
    else:
        tier = "LOW"
    return {
        "orphan_megasynthase_count": orphan_ks_count,
        "orphan_at_ambiguous_count": orphan_at_count,
        "fragmented_megasynthase_count": fragmented_count,
        "assembly_interior_fraction": interior_frac,
        "rescue_priority_score": fragmented_count + orphan_ks_count,
        "rescue_readiness": tier,
        "rescue_readiness_claim_safety": "Heuristic genome-level triage aid, NOT a claim about any specific "
        "cluster. rescue_priority_score = fragmented_megasynthase_count + orphan_megasynthase_count "
        "(Tier-1 KS only; AT-only excluded). Tier requires a sub-Good assembly (interior_fraction < 0.70): "
        "on a Good assembly these counts more likely reflect genuinely separate loci, so tier = LOW. HIGH = "
        "many fragments AND many loose KS pieces on a poor assembly — the textbook reassembly/long-read target.",
    }


# Conserved megasynthase active-site motifs for annotation-independent orphan-contig detection.
# KS = beta-ketoacyl synthase catalytic cysteine (DTACSSS / ETACSSS) — specific to ketosynthases.
# AT = acyltransferase active-site serine (GHSxG) — the alpha/beta-hydrolase nucleophile elbow, SHARED with
# esterases/thioesterases/lipases/dehalogenases/peptidases, so AT-only is NOT megasynthase evidence and is
# tiered out of the headline list. These let FLBR see KS fragments on orphan contigs that antiSMASH left
# unannotated (the gap the correction's G2 flagged). Motif presence is a CANDIDATE, not a confirmed domain.
_KS_ACTIVE_SITE = re.compile(r"[DE]TAC[ST]S")
_AT_ACTIVE_SITE = re.compile(r"GHS[LIVMFQAW]G")
# antiSMASH region GBKs include flanking genes beyond the core Start/End; exclude CDS within this margin of a
# called cluster core so in-cluster flank megasynthase CDS are not mis-flagged as orphans (feedback §1).
_ORPHAN_FLANK = 20000


def scan_orphan_megasynthase_motifs(cds_list: list[CDSFeature], bgcs: list[BGCRecord]) -> dict[str, list[dict[str, Any]]]:
    """Candidate megasynthase fragments on orphan contigs (CDS outside every called BGC core ±20 kb flank),
    detected by conserved active-site motifs. Annotation-independent; claim-safe. Tiered by motif specificity:
    KS-bearing (evidential) vs AT-only (alpha/beta-hydrolase-ambiguous, NOT a megasynthase claim)."""
    ranges: dict[str, list[tuple[int, int]]] = {}
    for b in bgcs:
        ranges.setdefault(_contig_key(b.contig), []).append((b.start, b.end))

    def _in_or_flanking_bgc(cds: CDSFeature) -> bool:
        for s, e in ranges.get(_contig_key(cds.contig), []):
            # widen the core window by the antiSMASH region flank on both sides, so flank CDS aren't orphans
            if cds.start < e + _ORPHAN_FLANK and cds.end > s - _ORPHAN_FLANK:
                return True
        return False

    ks_bearing: list[dict[str, Any]] = []
    at_only: list[dict[str, Any]] = []
    for cds in cds_list:
        seq = cds.translation or ""
        if len(seq) < 200 or _in_or_flanking_bgc(cds):
            continue
        prod = (cds.product or "").lower()
        # already-annotated megasynthases are counted by the text scan; annotated hydrolases would inflate AT
        if any(k in prod for k in ("ketoacyl", "polyketide", "pks", "acyltransferase", "nrps",
                                   "amp-binding", "esterase", "lipase", "hydrolase", "thioesterase")):
            continue
        has_ks = bool(_KS_ACTIVE_SITE.search(seq))
        has_at = bool(_AT_ACTIVE_SITE.search(seq))
        if has_ks:
            ks_bearing.append({"contig": cds.contig, "locus_tag": cds.locus_tag,
                               "start": cds.start, "end": cds.end,
                               "length_aa": len(seq), "motifs": ["KS"] + (["AT"] if has_at else [])})
        elif has_at:
            entry = {"contig": cds.contig, "locus_tag": cds.locus_tag, "length_aa": len(seq),
                     "motifs": ["AT"],
                     "parsimony": "GHSxG = alpha/beta-hydrolase nucleophile elbow; most parsimoniously "
                                  "esterase/thioesterase/lipase, NOT a megasynthase fragment"}
            if len(seq) <= 400:
                entry["likely_standalone_hydrolase"] = True
            at_only.append(entry)
    return {"ks_bearing": ks_bearing, "at_only": at_only}


def _domain_hay(dom: DomainFeature) -> str:
    vals = [dom.feature_type, dom.domain or "", dom.database or "", dom.locus_tag or "", dom.evalue or ""]
    if dom.bitscore is not None:
        vals.append(str(dom.bitscore))
    for k, v in dom.qualifiers.items():
        vals.append(k)
        vals.extend(v)
    return " ".join(vals)

# v9.7.374 patch-candidate (bcherry AS-XXX/BGC032 dry-run audit): the bare single-letter/short
# abbreviation regexes below were matching against the FULL free-text haystack (_domain_hay),
# which includes Pfam/TIGRFAM `description` prose. Ordinary English routinely satisfies a bare
# \bA\b / \bC\b / \bT\b / \bE\b match (the article "a"; "C-term"/"C-like" abbreviations;
# amino-acid letter lists like "(G, H, P, S and T)") -- live-reproduced on a real sealed AS-XXX
# package: Lanthipeptide_LanB_RRE -> false NRPS_A (via "a class I..." in its own description),
# LANC_like -> false NRPS_C (via "...C-like protein"), Lant_dehydr_C -> false NRPS_C (via
# "...C-term"), tRNA-synt_2b -> false NRPS_T_PCP (via "...and T)"). This directly inflated
# per_bgc_dss (compute_per_bgc_dss reads domain_counts for its Tier-1 domain check), producing a
# real shipped manifest.json claim "Tier-1 domain(s): ['NRPS_A']" for a pure-RiPP lanthipeptide
# region with zero real NRPS domains. Fix: bare/short abbreviation patterns now match only the
# domain's own short-form token (dom.domain), not the free-text qualifier haystack; multi-word
# literal patterns (e.g. "adenylation", "dehydratase", "acyl carrier") keep searching the full
# haystack as before -- unchanged for this patch.
_BARE_ABBREV_PATTERNS = {
    r"\bA\b", r"\bC\b", r"\bT\b", r"\bE\b", r"\bTE\b", r"\bKS\b", r"\bAT\b",
    r"\bDH\b", r"\bER\b", r"\bKR\b", r"\bACP\b", r"\bGT\b",
}

def scan_domain_architecture(bgcs: list[BGCRecord], domains: list[DomainFeature]) -> dict[str, Any]:
    per_bgc = {b.bgc_id: {"domain_counts": {}, "domains": [], "module_count": 0, "core_summary": []} for b in bgcs}
    # v9.7.185 P13: track what lands in the Other_domain catch-all so a classifier gap self-announces.
    _other_breakdown: dict[str, int] = {}
    _known_core = ("PKS_KS", "PKS_AT", "PKS_DH", "PKS_ER", "PKS_KR", "PKS_ACP")
    _misfiled_core: dict[str, int] = {}
    for dom in domains:
        h = _domain_hay(dom)
        dom_token = dom.domain or ""
        classes = []
        for cls, pats in DOMAIN_CLASS_PATTERNS.items():
            hit = False
            for p in pats:
                haystack = dom_token if p in _BARE_ABBREV_PATTERNS else h
                if re.search(p, haystack, flags=re.I):
                    hit = True
                    break
            if hit:
                classes.append(cls)
        if not classes and dom.domain:
            classes.append("Other_domain")
            _other_breakdown[dom.domain] = _other_breakdown.get(dom.domain, 0) + 1
            if dom.domain in _known_core:
                _misfiled_core[dom.domain] = _misfiled_core.get(dom.domain, 0) + 1
        for bgc in bgcs:
            if dom.contig == bgc.contig and not (dom.end < bgc.start or dom.start > bgc.end):
                rec = per_bgc[bgc.bgc_id]
                # v9.7.335: parsers.py extracts "aSModule" (it even says so in a comment); this
                # tested "module" and so counted ZERO for every BGC in every manifest — the
                # authoritative handoff told the judgment kernel each megasynthase had no modules.
                if dom.feature_type == "aSModule":
                    rec["module_count"] += 1
                # v9.7.374 patch-candidate (bcherry AS-XXX widget-runtime audit): aSModule and
                # CDS_motif features are not themselves domain instances -- an aSModule's own
                # "domains" qualifier lists every constituent domain's full name (e.g. a single
                # module summary feature literally contains the substrings "PKS_KS", "PKS_AT",
                # "PKS_DH", "PKS_KR" concatenated), and a CDS_motif is a conserved active-site
                # sub-motif WITHIN one physical domain (e.g. 4 separate "PKSI-AT-*_m*" motif
                # features inside a single AT domain), not a second/third/fourth/fifth AT domain.
                # Letting either feature_type increment domain_counts double/multi-counts the
                # SAME physical domain once per constituent-name mention or once per submotif.
                # Live-reproduced on a real gold AS-XXX run (BGC021, NODE_32_..., 2 real AT
                # domains): domain_counts['PKS_AT'] read 10 before this fix (2 real aSDomain
                # PKS_AT hits + 1 aSModule self-match + 4 CDS_motif submotif hits + ...), 2 after
                # -- matching AS-XXX_3_antismash_modules.csv's real per-domain row count exactly.
                # This is independent of and compatible with the already-staged sibling card
                # AUDIT_374_domain_class_patterns_bare_abbrev_haystack_fix (that card
                # narrows which TEXT the classifier searches; this one narrows which FEATURE
                # TYPES are allowed to increment a count at all -- different mechanism, same
                # scan_domain_architecture() function, non-overlapping lines).
                for cls in classes:
                    if dom.feature_type in ("aSModule", "CDS_motif"):
                        continue
                    rec["domain_counts"][cls] = rec["domain_counts"].get(cls, 0) + 1
                rec["domains"].append({
                    "contig": dom.contig,
                    "start": dom.start,
                    "end": dom.end,
                    "feature_type": dom.feature_type,
                    "domain": dom.domain,
                    "bitscore": dom.bitscore,
                    "evalue": dom.evalue,
                    "classes": classes
                })
    for rec in per_bgc.values():
        counts = rec["domain_counts"]
        summary = []
        if counts.get("PKS_KS"):
            summary.append(f"PKS_KS×{counts.get('PKS_KS')}")
        if counts.get("NRPS_A"):
            summary.append(f"NRPS_A×{counts.get('NRPS_A')}")
        if counts.get("TE_release"):
            summary.append("release/TE")
        if counts.get("Glycosyltransferase"):
            summary.append("glycosylation")
        if counts.get("Halogenase"):
            summary.append("halogenation")
        if counts.get("YcaO_TOMM"):
            summary.append("YcaO/TOMM")
        rec["core_summary"] = summary
        rec["domain_hit_count"] = len(rec["domains"])
    return {
        "status": "SOURCE_DERIVED_STRUCTURED_DOMAINS",
        "per_bgc": per_bgc,
        # v9.7.185 P13: expose Other_domain offenders + any misfiled core token (empty = P11 holding).
        "other_domain_breakdown": dict(sorted(_other_breakdown.items(), key=lambda kv: -kv[1])[:25]),
        "misfiled_core_tokens": _misfiled_core,
        "claim_safety": "Parsed antiSMASH GBK domain feature types; not HMMER-recomputed."
    }

RES_CLASS_CONCORDANCE = {
    "VanHAX_like": ["glycopeptide"],
    "Erm_methylase": ["macrolide", "lincosamide", "lanthipeptide", "ripp", "lassopeptide", "thiopeptide"],
    "APH_AAC": ["aminoglycoside", "aminocyclitol", "nucleoside"],
    "Fosfomycin": ["phosphonate"],
    "Beta_lactamase_fold": ["betalactone", "beta-lactone", "betalactam", "beta-lactam"],
}

def resistance_tier_classification(bgcs: list[BGCRecord], resistance_scan: dict[str, Any], transporters: dict[str, Any], cds_list: list | None = None) -> dict[str, Any]:
    diagnostic_groups = {"Erm_methylase", "VanHAX_like", "APH_AAC", "Fosfomycin"}
    generic_groups = {"Beta_lactamase_fold", "Self_resistance_general"}
    res_coupling = resistance_scan.get("bgc_coupling", {})
    trans_coupling = transporters.get("bgc_coupling", {})
    per_bgc = {}
    for bgc in bgcs:
        groups = set(res_coupling.get(bgc.bgc_id, []))
        trans = set(trans_coupling.get(bgc.bgc_id, []))
        product_text = " ".join(bgc.products).lower()
        # v9.7.33 #28: HGT guard is now gene-level, not product-label-only. A region antiSMASH mis-types as a
        # biosynthetic class (e.g. an ICE labeled "lanthipeptide-class-v") still surfaces its mobility machinery.
        product_mobile = any(x in product_text for x in ["transpos", "integrase", "mobile"])
        mobile_fams = set(_mobile_context(cds_list, bgc)) if cds_list is not None else set()
        if product_mobile:
            mobile_fams = mobile_fams | {"product_label"}
        # DOMINANT = a core mobility determinant (integrase/recombinase/transposase) plus >=1 further mobile
        # family (ICE-like: integrase + conjugation/rep/tox-repeat), or >=3 mobile families total. A lone
        # incidental flanking transposase (1 family) is NOT dominant, so genuine BGCs near an IS element are safe.
        core_hit = bool(mobile_fams & MOBILE_ELEMENT_CORE)
        mobile_dominant = (core_hit and len(mobile_fams) >= 2) or (len(mobile_fams) >= 3)
        hgt_guard = "MOBILE_CONTEXT_POSSIBLE" if mobile_fams else "NO_MOBILE_CONTEXT_SOURCE_DERIVED"
        # APH-sugar-kinase veto: APH_AAC in a glycogen/trehalose/sugar-kinase context is a sugar kinase,
        # not a self-resistance determinant (SID-XXX BGC043/BGC005 over-call).
        veto_note = ""
        if cds_list is not None and "APH_AAC" in groups:
            ctx = _region_context(cds_list, bgc)
            if ("glycogen_trehalose" in ctx or "sugar_kinase" in ctx):
                groups = groups - {"APH_AAC"}
                veto_note = " [APH_AAC vetoed: sugar-kinase/glycogen-trehalose context, not self-resistance]"
        diag = groups & diagnostic_groups
        # class-matched co-localization: a resistance group matching the product class is high-confidence
        # self-protection and outranks a generic transporter.
        concord = sorted({g for g in groups if any(c in product_text for c in RES_CLASS_CONCORDANCE.get(g, []))})
        if diag:
            tier = "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"
            if concord:
                confidence = "HIGH_CLASS_CONCORDANT"
                rationale = f"Diagnostic self-protection {sorted(diag)} class-concordant with product ({concord}) -> high-confidence self-resistance.{veto_note}"
            else:
                confidence = "MODERATE_CLASS_UNVERIFIED"
                rationale = f"Diagnostic resistance group(s): {sorted(diag)}; class-concordance not established -> verify.{veto_note}"
        elif groups & generic_groups:
            tier = "T2_RESISTANCE_LIKE_SOURCE_DERIVED"
            confidence = "MODERATE_CLASS_CONCORDANT" if concord else "LOW"
            rationale = f"Resistance-like group(s): {sorted(groups & generic_groups)}{' (class-concordant: '+str(concord)+')' if concord else ''}; requires class-concordance review.{veto_note}"
        elif trans:
            tier = "T3_TRANSPORTER_ONLY_ROUTING"
            confidence = "LOW"
            rationale = f"Transporter/exporter group(s): {sorted(trans)}; use for extraction/polarity routing, not mechanism.{veto_note}"
        else:
            tier = "NULL_NO_SOURCE_DERIVED_RESISTANCE"
            confidence = "NONE"
            rationale = f"No source-derived resistance/self-protection or transporter evidence proximal to BGC.{veto_note}"
        per_bgc[bgc.bgc_id] = {
            "tier": tier,
            "confidence": confidence,
            "class_concordant_groups": concord,
            "rationale": rationale,
            "resistance_groups": sorted(groups),
            "transporter_groups": sorted(trans),
            "hgt_guard": hgt_guard,
            "mobile_families": sorted(mobile_fams),
            "mobile_dominant": mobile_dominant
        }
    counts = {}
    for v in per_bgc.values():
        counts[v["tier"]] = counts.get(v["tier"], 0) + 1
    return {
        "status": "SOURCE_DERIVED_TIERED",
        "tier_counts": counts,
        "per_bgc": per_bgc,
        "claim_safety": "Tiered from source annotations/proximity only; class-concordance weighting and sugar-kinase APH veto applied; curated BLAST/HMM confirmation still required."
    }

WETLAB_CLASS_DEFAULTS = [
    ("phosphonate", {"mw_range": "150–900 Da; often polar", "ionization": "ESI−/ESI+", "uv_handle": "often weak UV", "extraction": "polar aqueous/MeOH fractions", "assay": "antibacterial panel", "confirm": "P31-NMR, HRMS formula with phosphorus, MS/MS"}),
    ("halogenated", {"mw_range": "class-dependent", "ionization": "ESI+ and ESI−", "uv_handle": "Cl/Br isotope pattern", "extraction": "EtOAc plus MeOH fractions", "assay": "bioassay-guided fractionation", "confirm": "HRMS isotope pattern; MS/MS"}),
    ("lanthipeptide", {"mw_range": "1–4 kDa peptide", "ionization": "ESI+ multiply charged", "uv_handle": "peptide UV 210–230 nm", "extraction": "polar peptide extraction; SPE/C18", "assay": "Gram-positive antibacterial panel", "confirm": "MS/MS peptide fragments; dehydration pattern"}),
    ("lassopeptide", {"mw_range": "1–3 kDa peptide", "ionization": "ESI+ multiply charged", "uv_handle": "peptide UV", "extraction": "MeOH/butanol/polar SPE", "assay": "Gram-positive antibacterial and stability tests", "confirm": "MS/MS, heat/protease stability"}),
    ("thioamide", {"mw_range": "peptide-like; variable", "ionization": "ESI+", "uv_handle": "possible thioamide long-wavelength shoulder", "extraction": "polar to mid-polar fractions", "assay": "antibacterial/cytotoxicity caution", "confirm": "MS/MS and sulfur-rich formula"}),
    ("t1pks", {"mw_range": "300–1500+ Da", "ionization": "ESI+ and ESI−", "uv_handle": "depends on conjugation", "extraction": "EtOAc/MeOH", "assay": "AB/AF depending on family", "confirm": "HRMS, MS/MS, UV if conjugated"}),
    ("nrps", {"mw_range": "500–2500+ Da", "ionization": "ESI+ common", "uv_handle": "peptide UV; chromophores if aromatic", "extraction": "MeOH/butanol/C18 SPE", "assay": "AB/AF/siderophore as appropriate", "confirm": "MS/MS amino-acid-like fragments"}),
    ("siderophore", {"mw_range": "400–1500 Da", "ionization": "ESI+/-; Fe-complex shifts", "uv_handle": "CAS assay; Fe-complex color", "extraction": "iron-limited media; polar fractions", "assay": "CAS, growth rescue/competition", "confirm": "CAS+, Fe adducts, iron-repression"}),
    ("metallophore", {"mw_range": "400–1500 Da", "ionization": "metal adducts possible", "uv_handle": "CAS or metal-shift assays", "extraction": "polar fractions; metal limitation", "assay": "metal competition/ecology", "confirm": "metal adduct HRMS"}),
    ("terpene", {"mw_range": "150–700 Da", "ionization": "GC-MS for volatile; LC-MS for decorated", "uv_handle": "pigments/carotenoids visible; many weak UV", "extraction": "organic extraction; GC-MS for volatiles", "assay": "ecology/stress/pigment", "confirm": "GC-MS/LC-MS, UV/Vis for pigments"}),
    ("t2pks", {"mw_range": "300–1200 Da aromatic", "ionization": "ESI+/-", "uv_handle": "strong UV/Vis; often colored", "extraction": "EtOAc, MeOH; monitor pigments", "assay": "AB/cytotoxicity/AF depending family", "confirm": "UV/Vis + HRMS + MS/MS"}),
    ("polyene", {"mw_range": "600–1200+ Da", "ionization": "ESI+/-", "uv_handle": "diagnostic polyene UV/Vis", "extraction": "organic, protect from light", "assay": "Candida/antifungal priority", "confirm": "UV polyene spectrum + HRMS"}),
]

def wetlab_row_for_bgc(bgc: BGCRecord, defaults_list: list | None = None) -> dict[str, Any]:
    text = " ".join(bgc.products).lower()
    chosen = "general"
    defaults = {"mw_range": "unknown; class-dependent", "ionization": "ESI+ and ESI− full scan",
                "uv_handle": "DAD full scan", "extraction": "parallel EtOAc and MeOH/polar fractions",
                "assay": "bioactivity-guided fractionation", "confirm": "fraction-linked activity + HRMS/MS"}
    for key, d in (defaults_list or WETLAB_CLASS_DEFAULTS):
        # v9.7.374 fix: "polyene" is a glued substring of "arylpolyene" -- a pigment/
        # false-positive class this same file already treats as non-bioactive elsewhere
        # (the (?<!aryl) guard on T43-PYE_polyene_macrolide above and on _POLYENE_ANCHOR
        # below). scoring.py's _key_present() documents this identical "polyene inside
        # arylpolyene" collision as "the source of the AB/AF inflation" and fixes it with a
        # delimiter-bounded match -- but this table's `key in text` substring check was never
        # given the same guard, so every arylpolyene-only BGC fell through to the genuine-
        # antifungal-polyene wet-lab row (mw_range/extraction/"Candida/antifungal priority"
        # assay guidance it does not deserve). No other key in this table glues onto a
        # superstring the same way, so only "polyene" needs the guard.
        if key == "polyene" and not re.search(r"(?<!aryl)polyene", text):
            continue
        if key in text:
            chosen, defaults = key, d
            break
    return {
        "bgc_id": bgc.bgc_id,
        "class_key": chosen,
        "edge_status": bgc.edge_status,
        "architecture_confidence": bgc.architecture_confidence,
        "mw_range": defaults["mw_range"],
        "ionization": defaults["ionization"],
        "uv_or_color_handle": defaults["uv_handle"],
        "extraction": defaults["extraction"],
        "assay": defaults["assay"],
        "confirm_refute": defaults["confirm"],
        "claim_safety": "Class-default wet-lab guidance from source-derived product class; refine with literature/metabolomics."
    }

def generate_wetlab_rows(bgcs: list[BGCRecord], extended_defaults: list | None = None) -> dict[str, Any]:
    """Generate per-BGC wet-lab rows, merging base and extended class defaults."""
    combined = list(WETLAB_CLASS_DEFAULTS)
    if extended_defaults:
        # Extended entries supplement base; base entries take priority on key collision
        existing_keys = {k for k, _ in combined}
        combined += [(k, v) for k, v in extended_defaults if k not in existing_keys]
    rows = [wetlab_row_for_bgc(b, combined) for b in bgcs]
    return {
        "status": "SOURCE_DERIVED_CLASS_LOOKUP",
        "rows": rows,
        "row_count": len(rows),
        "class_coverage": sorted(set(r["class_key"] for r in rows)),
        "claim_safety": "Per-BGC class-default wet-lab rows; not literature-verified.",
    }


# ---------------------------------------------------------------------------
# QS signal detection — Sapote §33.3 routing flag
# ---------------------------------------------------------------------------

QS_PRODUCT_LABELS = {
    "butyrolactone", "hserlactone", "bdsf", "furan",
    "gamma-butyrolactone", "autoinducer",
}

QS_CDS_PATTERNS = [
    r"luxI", r"afsA", r"rpfF", r"autoinducer synthase",
    r"acyl-homoserine lactone synthase", r"AHL synthase",
    r"gamma-butyrolactone synthase",
]


def scan_qs_signals(bgcs: list[BGCRecord], cds_list: list[CDSFeature]) -> dict[str, Any]:
    """Flag BGCs whose products or CDS annotations indicate a QS signal compound.

    These BGCs must be routed to ecology only (Sapote §33.3).  They must not
    receive an AB/AF mechanistic-link WL bonus.  They are recorded separately
    so Sapote-slim can apply the routing without re-parsing.
    """
    qs_bgc_ids = []
    for bgc in bgcs:
        product_text = " ".join(bgc.products).lower()
        # BH-010: token-split before membership test so "furan" does not match inside
        # "furanomycin" / "furopyridine" (PKS classes, not quorum-sensing signals).
        _prod_tokens = {t.strip() for t in re.split(r"[;,/|]+|\s+", product_text) if t.strip()}
        if any(label in _prod_tokens for label in QS_PRODUCT_LABELS):
            qs_bgc_ids.append(bgc.bgc_id)
            continue
        # Also scan proximal CDS for LuxI/AfsA synthase annotations
        for cds in cds_list:
            if not _bgc_overlap_or_near(cds, bgc, flank=0):
                continue
            h = _hay(cds)
            if any(re.search(p, h, flags=re.I) for p in QS_CDS_PATTERNS):
                qs_bgc_ids.append(bgc.bgc_id)
                break
    napaa_bgc_ids = []
    for bgc in bgcs:
        product_text = " ".join(bgc.products).lower()
        if "napaa" in product_text or "poly-amino acid" in product_text or "polyamino acid" in product_text:
            napaa_bgc_ids.append(bgc.bgc_id)

    return {
        "status": "SOURCE_DERIVED",
        "qs_signal_bgc_ids": sorted(set(qs_bgc_ids)),
        "qs_signal_count": len(set(qs_bgc_ids)),
        "napaa_bgc_ids": sorted(set(napaa_bgc_ids)),
        "napaa_count": len(set(napaa_bgc_ids)),
        "routing": "QS BGCs: ecology_only — do not apply AB/AF mechanistic-link WL bonus. NAPAA BGCs: neutral — common and frequently adjacent to genuine BGCs; not excluded from comparative claims (build -r).",
        "claim_safety": "QS signal and NAPAA routing is product-label and annotation derived; confirm biochemically.",
    }


# ---------------------------------------------------------------------------
# Glycosylation-arm candidate detection — Sapote §34.5 trap (v8.10.2)
# ---------------------------------------------------------------------------

# MIBiG compound families known to incorporate deoxysugars.
# Used to determine whether a saccharide BGC KCB hit is a glycosylated-compound
# reference (triggering the ≥3-protein-hit threshold rule).
GLYCOSYLATED_COMPOUND_KEYWORDS = {
    "macrolide", "erythromycin", "tylosin", "spiramycin", "avermectin",
    "amphotericin", "nystatin", "candicidin", "glycopeptide", "vancomycin",
    "teicoplanin", "aminoglycoside", "streptomycin", "kanamycin", "neomycin",
    "gentamicin", "tobramycin", "deoxysugar", "glycosylat", "angucycline",
    "anthracycline", "doxorubicin", "mithramycin", "elloramycin", "urdamycin",
    "chromomycin", "olivomycin", "landomycin", "granaticin", "griseusin",
    "aklavinone", "steffimycin", "aclacinomycin", "nogalamycin",
}


def scan_glycosylation_arm_candidates(bgcs: list[BGCRecord]) -> dict[str, Any]:
    """Identify saccharide BGCs meeting the §34.5 glycosylation-arm trap criteria.

    Fires when:
      (a) BGC product label contains 'saccharide'
      (b) KCB top hit references a glycosylated-compound family
      (c) kcb_protein_hits >= 3   (the v8.10.2 threshold)

    Returns a list of candidate BGC IDs with their evidence for Sapote §34.5.
    1-2 protein hits = incidental overlap, noted only.
    """
    candidates = []
    incidental = []
    for bgc in bgcs:
        product_text = " ".join(bgc.products).lower()
        if "saccharide" not in product_text:
            continue
        kcb_top_text = (bgc.kcb_top or "").lower()
        mibig_text = " ".join(bgc.mibig_hits).lower()
        combined = kcb_top_text + " " + mibig_text
        is_glycosylated_ref = any(kw in combined for kw in GLYCOSYLATED_COMPOUND_KEYWORDS)
        if not is_glycosylated_ref:
            continue
        protein_hits = bgc.kcb_protein_hits or 0
        rec = {
            "bgc_id": bgc.bgc_id,
            "products": bgc.products,
            "kcb_top": bgc.kcb_top,
            "kcb_protein_hits": protein_hits,
            "mibig_hits": bgc.mibig_hits,
            "edge_status": bgc.edge_status,
        }
        if protein_hits >= 3:
            rec["trap_verdict"] = (
                "GLYCOSYLATION_ARM_TRAP_FIRED — ≥3 protein hits against glycosylated-compound "
                "reference on saccharide BGC; check resident deoxysugar/NDP-sugar/GT domains; "
                "run EFLS cross-contig check for aglycone BGC; pair at Architecture C if found."
            )
            candidates.append(rec)
        elif protein_hits >= 1:
            rec["trap_verdict"] = (
                f"INCIDENTAL_OVERLAP — {protein_hits} protein hit(s) against glycosylated-compound "
                "reference; below ≥3-hit threshold; note only, do not fire full sub-rule."
            )
            incidental.append(rec)
    return {
        "status": "SOURCE_DERIVED",
        "glycosylation_arm_candidates": candidates,
        "incidental_overlap": incidental,
        "candidate_count": len(candidates),
        "threshold_note": "≥3 protein hits fires the §34.5 sub-rule; 1-2 hits = incidental overlap, note only.",
        "claim_safety": "Source-derived; requires EFLS cross-contig confirmation and domain inspection before reporting.",
    }


# ---------------------------------------------------------------------------
# Per-BGC Diagnostic Signal Score (DSS) — Sapote §34.3
# ---------------------------------------------------------------------------

def compute_per_bgc_dss(
    bgcs: list[BGCRecord],
    domain_architecture: dict[str, Any],
    resistance_tiers: dict[str, Any],
    cctt: dict[str, Any],
) -> dict[str, Any]:
    """Compute a source-derived Diagnostic Signal Score (0-5) per BGC.

    This pre-computes the §34.3 DSS so Sapote-slim does not need to
    re-derive it from scratch.  Scores are approximate; Sapote applies
    the authoritative formula.

    Scoring (additive, capped at 5):
      +2  Tier-1 domain evidence: named domain class from aSDomain/PFAM
             (PKS_KS, NRPS_A, TE_release, YcaO_TOMM, Halogenase, RiPP_precursor)
      +1  KCB protein_hits >= 5 (strong homology anchor)
      +1  Resistance tier T1 within BGC proximity
      +1  CCTT T43 trigger coupled to this BGC
    """
    da_per_bgc = (domain_architecture or {}).get("per_bgc", {})
    rt_per_bgc = (resistance_tiers or {}).get("per_bgc", {})
    cctt_coupling = (cctt or {}).get("bgc_coupling", {})

    tier1_domain_classes = {
        "PKS_KS", "NRPS_A", "TE_release", "YcaO_TOMM",
        "Halogenase", "RiPP_precursor",
    }

    per_bgc = {}
    for bgc in bgcs:
        score = 0
        reasons = []

        # +2 for Tier-1 domain class present.
        # sorted(): tier1_domain_classes is a set, so an unsorted comprehension orders hits by
        # hash (randomized per process) -> non-reproducible manifest.json/Project_Memory_Snapshot.
        # Order is cosmetic (score is presence-only), so sorting only adds determinism.
        da = da_per_bgc.get(bgc.bgc_id, {})
        domain_counts = da.get("domain_counts", {})
        tier1_hits = sorted(cls for cls in tier1_domain_classes if domain_counts.get(cls, 0) > 0)
        if tier1_hits:
            score += 2
            reasons.append(f"Tier-1 domain(s): {tier1_hits}")

        # +1 for strong KCB
        if bgc.kcb_protein_hits is not None and bgc.kcb_protein_hits >= 5:
            score += 1
            reasons.append(f"KCB protein_hits={bgc.kcb_protein_hits}")

        # +1 for T1 resistance tier
        rt = rt_per_bgc.get(bgc.bgc_id, {})
        if rt.get("tier", "").startswith("T1"):
            score += 1
            reasons.append("Resistance tier T1")

        # +1 for CCTT T43 trigger
        if cctt_coupling.get(bgc.bgc_id):
            score += 1
            reasons.append(f"CCTT trigger(s): {cctt_coupling[bgc.bgc_id]}")

        per_bgc[bgc.bgc_id] = {
            "dss": min(5, score),
            "reasons": reasons,
            "claim_safety": "Source-derived DSS; Sapote §34.3 applies the authoritative formula.",
        }

    return {
        "status": "SOURCE_DERIVED",
        "per_bgc": per_bgc,
        "note": "DSS 0-5; pre-computed for Sapote-slim handoff. Sapote §34.3 is authoritative.",
    }


# ---------------------------------------------------------------------------
# Extended WETLAB_CLASS_DEFAULTS — adds missing CCTT-triggered classes
# ---------------------------------------------------------------------------

WETLAB_CLASS_DEFAULTS_EXTENDED = [
    ("enediyne", {
        "mw_range": "~300–1000 Da aglycone; glycosylated higher",
        "ionization": "ESI+ and ESI−",
        "uv_handle": "UV ~300–400 nm; chromophore diagnostic",
        "extraction": "Organic + polar; handle carefully — cytotoxic",
        "assay": "⚠ cytotoxicity screen first; MRSA only with selectivity data",
        "confirm": "HRMS; CalC/apo-protein self-resistance confirmation required",
    }),
    ("aminocyclitol", {
        "mw_range": "300–800 Da polar",
        "ionization": "ESI+ preferred",
        "uv_handle": "weak UV; no strong chromophore",
        "extraction": "Polar aqueous/MeOH; ion-exchange or SAX SPE",
        "assay": "Antibacterial panel; aminoglycoside MIC",
        "confirm": "HRMS with 31P-NMR if phosphonate; MS/MS fragmentation",
    }),
    ("nucleoside", {
        "mw_range": "200–700 Da",
        "ionization": "ESI+ and ESI−",
        "uv_handle": "UV 262 nm (nucleobase); not standard C18",
        "extraction": "Polar/SAX; ion-pair RP-HPLC",
        "assay": "Candida chitin-synthase panel; cytotoxicity caution",
        "confirm": "HRMS; UV 262 nm; MS/MS glycosidic bond fragments",
    }),
    ("tomm_azole", {
        "mw_range": "800–2500 Da heterocyclic peptide",
        "ionization": "ESI+ multiply charged",
        "uv_handle": "UV ~310–370 nm thiazole/oxazole chromophore",
        "extraction": "MeOH/butanol; C18 SPE",
        "assay": "Antibacterial panel; RiPP-class stability tests",
        "confirm": "MS/MS heterocycle-loss fragments; HRMS",
    }),
    ("hsaf", {
        "mw_range": "450–600 Da",
        "ionization": "ESI+",
        "uv_handle": "~305 nm + ~270 nm; acid-labile tetramate ring",
        "extraction": "EtOAc pH ≥6 — do NOT use pH <4 (destroys tetramate)",
        "assay": "Candida antifungal priority (+2 WL); fungal MIC panel",
        "confirm": "HRMS; characteristic UV dual bands; tetramate MS/MS",
    }),
    ("carbapenem", {
        "mw_range": "250–500 Da",
        "ionization": "ESI+ and ESI−",
        "uv_handle": "UV ~300 nm beta-lactam region",
        "extraction": "Polar aqueous; SPE; unstable — process fresh",
        "assay": "MRSA/Gram-negative panel; beta-lactamase stability test",
        "confirm": "HRMS; beta-lactam ring MS/MS",
    }),
    ("phenazine", {
        "mw_range": "180–400 Da",
        "ionization": "ESI+ and ESI−",
        "uv_handle": "Strong UV/Vis; visible pigment (yellow/orange/red)",
        "extraction": "EtOAc; monitor pigment visually on plates",
        "assay": "Visual plate screen; Gram-positive/negative MIC; ecology only for attine context",
        "confirm": "UV/Vis spectrum + HRMS; no Escovopsis-defence bonus in attine context",
    }),
    ("indolocarbazole", {
        "mw_range": "300–600 Da",
        "ionization": "ESI+",
        "uv_handle": "strong UV ~340–380 nm",
        "extraction": "EtOAc/MeOH; ⚠ cytotoxic — selectivity data required",
        "assay": "⚠ cytotoxicity screen mandatory; no direct Candida mechanism",
        "confirm": "HRMS; UV 340–380 nm; indolocarbazole MS/MS pattern",
    }),
    ("t3pks", {
        "mw_range": "200–500 Da",
        "ionization": "ESI+/−",
        "uv_handle": "UV (resorcinol/pyrone ring)",
        "extraction": "EtOAc",
        "assay": "Bioactivity-guided fractionation; ecology context",
        "confirm": "HRMS; phenolic MS/MS",
    }),
]


def scan_primary_metabolism(cds_list: list[CDSFeature], bgcs: list[BGCRecord]) -> dict[str, Any]:
    """Per-BGC non-bioactivity core-gene families (housekeeping / pigment).

    Coupling uses flank=0 so only the BGC's OWN CDS count — the false positive (SID-XXX topoisomerase,
    carotenoid cyclase) is genes INSIDE the mis-called region, not flanking neighbours. The scorer
    consumes `per_bgc[bgc_id]["families"]` and suppresses AB/AF keyword credit when the region's own
    product label is a weak/over-call class and no Tier-1 diagnostic fires.
    """
    scan = _scan_patterns(cds_list, PRIMARY_METABOLISM_PATTERNS)
    coupling = bgc_coupling(bgcs, scan, flank=0)
    per_bgc = {b.bgc_id: {"families": coupling.get(b.bgc_id, [])} for b in bgcs}
    return {"status": "SOURCE_DERIVED", "hits": scan["hits"], "counts": scan["counts"],
            "bgc_coupling": coupling, "per_bgc": per_bgc,
            "claim_safety": ("CDS-product-derived housekeeping/pigment families. Suppression applies "
                             "only when the BGC's OWN product class is a weak/over-call label "
                             "(nrps-like/terpene/saccharide/arylpolyene) and no Tier-1 diagnostic fires.")}


# Gene-filter mis-anchor guards (v9.7.15). KCB = similarity, not identity: a product-name anchor that lacks
# the class's committed diagnostic gene/architecture is a spurious hit for THIS locus.
_AMINOGLYCOSIDE_ANCHOR = re.compile(
    r"(?:gentamicin|gentamycin|kanamycin|neomycin|tobramycin|butirosin|ribostamycin|paromomycin|sisomicin|"
    r"fortimicin|apramycin|kasugamycin|hygromycin|spectinomycin|streptomycin|aminoglycoside|"
    r"2-deoxystreptamine|2-deoxy-streptamine|tetrachlorizine|"
    r"amikacin|arbekacin|dibekacin|netilmicin|isepamicin|verdamicin|sagamicin|gentamine|"
    r"lividomycin|bluensomycin|hygromycin b|destomycin|validamycin|sorbistin|fortimycin|istamycin)\b", re.I)
# committed first step of 2-deoxystreptamine aminoglycoside biosynthesis (btrC/kanC/neoC family)
_DOIS_GENE = re.compile(
    r"2-deoxy-scyllo-inosose synthase|2-deoxy-scyllo-inosose|scyllo-inosose|deoxy-scyllo-inos|"
    r"\bdois\b|2-deoxystreptamine|aminocyclitol|2-deoxy-scyllo-inosamine|glucose-6-phosphate cyclase", re.I)
_POLYENE_ANCHOR = re.compile(
    r"(?:natamycin|pimaricin|candicidin|amphotericin|nystatin|reedsmycin|filipin|rimocidin|faeriefungin|"
    r"tetramycin|lucensomycin|partricin|eco-02301|(?<!aryl)polyene macrolide|(?<!aryl)polyene antifungal|"
    r"perimycin|aureofungin|hamycin|trichomycin|mycoheptin|levorin|fungichromin|chainin|"
    r"flavofungin|nystatin a|amphotericin b|pentamycin|methylpentaene|polyfungin|"
    r"selvamicin|eco-0501|nystatin-like|tetraene|pentaene|hexaene|heptaene|tetraene macrolide|polyene-macrolide)\b", re.I)
_POLYENE_MIN_KS = 4   # a genuine polyene macrolide backbone is a large modular PKS
# §4.3 PREV-001 enediyne guard. A genuine enediyne is a named enediyne natural product on a real enediyne PKS;
# the prevalent hglE-KS / hexacosalactone glycolipid domain (PREV-001) can mis-anchor as "enediyne".
_ENEDIYNE_SPECIFIC = re.compile(
    r"(?:calicheamicin|dynemicin|esperamicin|neocarzinostatin|c-1027|c1027|maduropeptin|kedarcidin|"
    r"sporolide|cyanosporaside|uncialamycin|namenamicin|shishijimicin|tiancimycin|yangpumicin|"
    r"golfomycin|deoxydynemicin|enediyne polyketide)\b", re.I)
_ENEDIYNE_GENERIC = re.compile(r"enediyne|ene_ks|ene-ks", re.I)
_PREV001_SIGNAL = re.compile(r"\bhgle\b|hgle-ks|prev-001|hexacosalactone", re.I)


# ── KCB class-compatibility map (v9.7.63) ──────────────────────────────────────────────
# Maps compound-name SUBSTRINGS (lower-case) found in KCB_top to the antiSMASH product-class
# tokens that SHOULD be present in the BGC's own products for the anchor to be plausible.
# A BGC whose own product set has ZERO overlap with the expected classes for its KCB anchor
# receives a class-mismatch flag (suppresses anchor-derived AB/AF/novelty credit).
#
# Design principles:
# 1. Conservative: only flag when the compound family is chemically unambiguous.
# 2. Compound-specific: "γ-butyrolactone" is compatible with butyrolactone BGCs; "difficidin"
#    (NRPS/PKS macrolide) is NOT — so the map keys target the specific compound, not the family.
# 3. No false-positive on legitimate cross-class anchors: NRPS/PKS hybrids are intentionally
#    permissive (a T1PKS BGC with kiramycin anchor is still a PKS locus).
# 4. One-sided: the map says "if you see this compound, these classes should be present."
#    It does NOT say "only these compounds apply to these classes."
#
# Expected class tokens are antiSMASH product labels (lower-case, as in BGCRecord.products).
# Use frozenset so order doesn't matter; overlap check is any intersection.

_KCB_CLASS_COMPAT: list[tuple[re.Pattern, frozenset[str], str]] = [
    # T2PKS aromatic polyketides — require T2PKS or t2pks backbone
    # kinamycin: diazobenzofluorene, aromatic T2PKS from Streptomyces
    (re.compile(r"kinamycin", re.I),
     frozenset({"t2pks", "hr-t2pks", "nrps", "t1pks"}),
     "kinamycin is an aromatic T2PKS diazobenzofluorene; NI-siderophore loci lack the T2PKS backbone"),
    # prejadomycin: angucycline aromatic T2PKS
    (re.compile(r"prejadomycin|jadomycin|rabelomycin", re.I),
     frozenset({"t2pks", "hr-t2pks"}),
     "prejadomycin/jadomycin are angucycline T2PKS natural products; terpene loci lack the T2PKS backbone"),
    # accramycin / aclacinomycin / anthracycline T2PKS
    (re.compile(r"accramycin|aclacinomycin|aclarubicin", re.I),
     frozenset({"t2pks", "hr-t2pks"}),
     "accramycin/aclacinomycin are anthracycline T2PKS compounds; saccharide/melanin loci lack T2PKS"),
    # Chlorinated NRPS hybrids — require NRPS or PKS, not just halogenated
    # colibrimycin: a complex NRPS-PKS compound; halogenated-only loci are mismatch
    (re.compile(r"colibrimycin", re.I),
     frozenset({"nrps", "t1pks", "t2pks", "ripp"}),
     "colibrimycin is an NRPS/PKS hybrid; a halogenated;other-only locus lacks the NRPS/PKS backbone"),
    # Macrolide / polyene T1PKS — require T1PKS backbone
    # cyphomycin: a polyene T1PKS; butyrolactone loci lack PKS
    (re.compile(r"cyphomycin", re.I),
     frozenset({"t1pks", "transat-pks", "pks"}),
     "cyphomycin is a polyene T1PKS macrolide; butyrolactone loci lack the PKS backbone"),
    # difficidin: NRPS/PKS hybrid
    (re.compile(r"difficidin", re.I),
     frozenset({"t1pks", "nrps", "pks", "transat-pks"}),
     "difficidin is an NRPS/PKS macrolide; butyrolactone loci lack the NRPS/PKS backbone"),
    # Aminoglycoside T1PKS
    # colabomycin: zorbamycin-family aminoglycoside
    (re.compile(r"colabomycin|zorbamycin", re.I),
     frozenset({"t1pks", "nrps", "pks", "t2pks"}),
     "colabomycin/zorbamycin are NRPS/PKS glycopeptides; butyrolactone/terpene/saccharide loci lack the backbone"),
    # Nucleoside anchors
    # showdomycin: nucleoside; not a butyrolactone compound
    (re.compile(r"showdomycin", re.I),
     frozenset({"nucleoside", "nrps", "t1pks"}),
     "showdomycin is a nucleoside; butyrolactone loci lack nucleoside biosynthetic machinery"),
    # Minimalist PKS / furanomycin-class
    # coelimycin: aromatic T1PKS yellow pigment (Streptomyces)
    (re.compile(r"coelimycin", re.I),
     frozenset({"t1pks", "t2pks", "pks"}),
     "coelimycin P1 is a T1PKS/aromatic PKS compound; butyrolactone loci lack the PKS backbone"),
    # methylenomycin: furanomycin-class T1PKS
    (re.compile(r"methylenomycin", re.I),
     frozenset({"t1pks", "pks", "t2pks"}),
     "methylenomycin is a T1PKS furanomycin-class compound; butyrolactone loci lack the PKS backbone"),
    # NRPS lipodepsipeptides appearing on fatty_acid loci
    # chlorizidine: chlorinated indolizidine from NRPS
    (re.compile(r"chlorizidine", re.I),
     frozenset({"nrps", "t1pks", "pks"}),
     "chlorizidine is an NRPS-derived alkaloid; fatty_acid;other loci lack the NRPS backbone"),
    # Phosphonate compounds: require phosphonate in own products
    # phosphonoglycans: ONLY a mismatch when phosphonate is absent (saccharide-only loci)
    # NOTE: this fires correctly on saccharide-only loci; phosphonate BGCs pass because
    # expected_classes includes "phosphonate" and their own products contain it.
    (re.compile(r"phosphonoglycan", re.I),
     frozenset({"phosphonate"}),
     "phosphonoglycans require a phosphonate biosynthetic locus; saccharide-only loci lack the C-P lyase pathway"),
]

_KCB_COMPOUND_EXTRACT = re.compile(r"BGC\d+(?:\.\d+)?\s*\|\s*([^|]+?)\s*\|", re.I)


def _check_kcb_class_compat(kcb_top: str, own_products: list[str]) -> tuple[bool, str]:
    """Return (mismatch_flag, reason_string) for a KCB anchor vs own product class.

    Returns (True, reason) when the KCB compound family is chemically incompatible with
    the BGC's own antiSMASH product class — i.e. the anchor is a spurious similarity hit.
    Returns (False, "") when compatible or when no rule fires.

    This is a conservative, compound-specific check. It fires only on known-bad compound
    families and only when the BGC's own class set has ZERO overlap with the expected classes
    for that compound. The existing per-gene guards (aminoglycoside/DOIS, polyene/KS, enediyne)
    are not replaced — this adds CLASS-LEVEL checking on top.
    """
    if not kcb_top:
        return False, ""
    # Extract compound name from KCB_top ("BGCxxxxxx | compound name | ...")
    m = _KCB_COMPOUND_EXTRACT.search(kcb_top)
    compound_text = m.group(1).strip().lower() if m else kcb_top.lower()
    own_lower = {p.strip().lower() for p in own_products if p.strip()}
    for pattern, expected_classes, reason in _KCB_CLASS_COMPAT:
        if pattern.search(compound_text) or pattern.search(kcb_top.lower()):
            if not (own_lower & expected_classes):
                return True, reason
    return False, ""


def scan_misanchor_guards(cds_list: list[CDSFeature], bgcs: list[BGCRecord]) -> dict[str, Any]:
    """Per-BGC gene-filter mis-anchor guards (claim-safety; KCB = similarity not identity):
      - aminoglycoside anchor WITHOUT a committed DOIS (2-deoxy-scyllo-inosose synthase) gene  -> mis-anchor
      - polyene-macrolide anchor WITHOUT a modular-PKS backbone (>= _POLYENE_MIN_KS PKS_KS domains) -> mis-anchor
      - enediyne anchor: GENUINE (named enediyne + real enediyne PKS -> [E-signal]) vs PREV-001 artifact
        (generic enediyne signal co-occurring with the hglE-KS/hexacosalactone glycolipid domain, no named
        enediyne compound -> spurious enediyne call)
    The anchor is the KCB product-similarity hit (kcb_top / closest_candidate_kcb_product), NOT the locus's own
    antiSMASH product class — so an `arylpolyene` class does not read as a polyene-macrolide anchor. A mis-anchor
    means the KCB product name is spurious for this locus; the scorer suppresses the anchor-derived AB/AF/novelty
    credit unless a Tier-1 diagnostic independently fires."""
    by_contig: dict[str, list[CDSFeature]] = {}
    for c in cds_list:
        by_contig.setdefault(c.contig, []).append(c)
    per_bgc = {}
    for b in bgcs:
        own = [c for c in by_contig.get(b.contig, []) if c.start < b.end and c.end > b.start]
        # the ANCHOR is the KCB similarity hit; the product class is used only for the diagnostic check below
        kcb_anchor = " ".join([b.kcb_top or "", b.closest_candidate_kcb_product or ""]).lower()
        products_txt = " ".join(b.products).lower()
        amino_text = kcb_anchor + " " + products_txt   # antiSMASH has an 'aminoglycoside' class
        amino_m = _AMINOGLYCOSIDE_ANCHOR.search(amino_text)
        amino = bool(amino_m)
        dois = any(_DOIS_GENE.search(c.product or "") for c in own)
        polyene_m = _POLYENE_ANCHOR.search(kcb_anchor)   # KCB compound name only (no 'arylpolyene' class)
        polyene = bool(polyene_m)
        ksd = getattr(b, "ks_domain_count", 0) or 0
        # §4.3 enediyne discrimination
        ene_m = _ENEDIYNE_SPECIFIC.search(kcb_anchor)
        ene_specific = bool(ene_m)
        ene_generic = bool(_ENEDIYNE_GENERIC.search(kcb_anchor + " " + products_txt))
        prev001 = bool(_PREV001_SIGNAL.search(kcb_anchor + " " + products_txt))
        ene_ks = getattr(b, "ene_ks_count", 0) or 0
        if ene_specific and ene_ks >= 1:
            ene_verdict = "GENUINE_E_SIGNAL"        # named enediyne + warhead PKS -> [E-signal]
        elif ene_specific:
            ene_verdict = "ENEDIYNE_MISANCHOR"           # named enediyne KCB hit but NO ene_KS -> similarity-only
        elif ene_generic and prev001:
            ene_verdict = "PREV001_ARTIFACT"             # generic enediyne signal that is really the hglE glycolipid
        elif ene_generic:
            ene_verdict = "E_SIGNAL_UNRESOLVED"          # generic enediyne, no hglE -> [E-signal], unconfirmed
        else:
            ene_verdict = ""
        # matched anchor compound(s) — persisted so a reviewer can audit a firing without re-parsing (Doc 8 rec#3)
        matched = {k: m.group(0) for k, m in (("aminoglycoside", amino_m), ("polyene", polyene_m),
                                              ("enediyne", ene_m)) if m}
        # v9.7.63: class-level KCB mismatch check (compound family vs own product class).
        # Use the same combined anchor as the other mis-anchor guards above.  The raw
        # rank-1 KCB line is commonly a genome self-hit while the resolved MIBiG product
        # is retained in closest_candidate_kcb_product; checking kcb_top alone silently
        # skipped the class guard for that resolved-product path.
        class_mismatch, class_mismatch_reason = _check_kcb_class_compat(
            kcb_anchor, b.products)
        per_bgc[b.bgc_id] = {
            "aminoglycoside_anchor": amino, "dois_present": dois,
            "aminoglycoside_misanchor": amino and not dois,
            "polyene_anchor": polyene, "ks_domain_count": ksd,
            "polyene_misanchor": polyene and ksd < _POLYENE_MIN_KS,
            "enediyne_verdict": ene_verdict, "ene_ks_count": ene_ks,
            "enediyne_misanchor": ene_verdict in ("PREV001_ARTIFACT", "ENEDIYNE_MISANCHOR"),
            "esignal_enediyne": ene_verdict == "GENUINE_E_SIGNAL",
            "matched_anchor": matched,
            "class_mismatch": class_mismatch,
            "class_mismatch_reason": class_mismatch_reason,
        }
    return {"status": "SOURCE_DERIVED", "per_bgc": per_bgc,
            "claim_safety": ("KCB is similarity, not identity. An aminoglycoside (2-deoxystreptamine) anchor "
                             "requires a committed DOIS (2-deoxy-scyllo-inosose synthase) gene in the locus; a "
                             "polyene-macrolide anchor requires a modular PKS backbone (>=4 PKS_KS domains); an "
                             "enediyne call requires a named enediyne natural product on a real enediyne PKS "
                             "([E-signal]) and is treated as a PREV-001 (hglE-KS/hexacosalactone glycolipid) "
                             "artifact when only a generic enediyne signal co-occurs with the hglE signature. "
                             "Absent the diagnostic the anchor is spurious for this locus and its AB/AF/novelty "
                             "credit is suppressed unless a Tier-1 diagnostic independently fires.")}


def run_source_scans(bgcs: list[BGCRecord], cds_list: list[CDSFeature], contigs: dict[str, str], domains: list[DomainFeature] | None = None, organism: str = "") -> SourceScanBundle:
    from .class_architecture import annotate_architecture
    annotate_architecture(bgcs, cds_list, domains or [])  # v9.7.21: per-BGC class-capacity call onto each record
    chitin = _scan_patterns(cds_list, CHITINASE_PATTERNS); chitin["bgc_coupling"] = bgc_coupling(bgcs, chitin)
    regs = _scan_patterns(cds_list, REGULATOR_PATTERNS); regs["bgc_coupling"] = bgc_coupling(bgcs, regs)
    trans = _scan_patterns(cds_list, TRANSPORTER_PATTERNS); trans["bgc_coupling"] = bgc_coupling(bgcs, trans)
    res = _scan_patterns(cds_list, RESISTANCE_PATTERNS); res["bgc_coupling"] = bgc_coupling(bgcs, res)
    cctt = _scan_patterns(cds_list, CCTT_PATTERNS); cctt["bgc_coupling"] = bgc_coupling(bgcs, cctt)
    cctt = apply_cctt_vetoes(cctt, bgcs, cds_list)
    tfbs = scan_tfbs(contigs, cds_list)
    blda = scan_blda_tta(cds_list, bgcs, organism=organism)
    flbr = scan_flbr(cds_list, bgcs)
    cctt = couple_kcb_ptm(bgcs, cctt, flbr)          # v9.7.19: KCB-aware HSAF/PTM coupling (Route A/B)
    # v9.7.19 — bridge per_bgc: the scorer's diagnostic-marker layer reads cctt["per_bgc"], but the CCTT
    # scan only ever set cctt["bgc_coupling"], so the AF/AB diagnostic bonus (T43-NUC etc.) was DEAD in
    # production (it fired only in tests that mocked per_bgc). Mirror the finalized coupling into per_bgc.
    cctt["per_bgc"] = dict(cctt.get("bgc_coupling", {}))
    # W27: per-trigger BGC-carrying counts — how many DISTINCT BGCs carry each T43 trigger. This is a
    # different measurement from cctt["counts"], which is the raw HIT count per bucket (gene/motif level).
    # One BGC can carry many hits, so the two diverge: e.g. 8 T43-PHO HITS all inside a single BGC is one
    # dedicated phosphonate locus, NOT a phosphonate-rich strain. Surfacing both keeps that distinction.
    from collections import Counter as _CCTTCounter
    _carry = _CCTTCounter()
    for _trigs in cctt["per_bgc"].values():
        for _t in set(_trigs):
            _carry[_t] += 1
    cctt["trigger_bgc_counts"] = dict(_carry)
    # N-05/A-04: flag class-defining triggers that fired on a class-incompatible BGC (no corroborating
    # product class). Evidence-preserving — recorded, not deleted; the claim layer treats these as ambiguous.
    _uncorr = cctt_context_uncorroborated(cctt["per_bgc"], bgcs)
    cctt["context_uncorroborated"] = _uncorr
    _ubb: dict[str, list[str]] = {}
    for _e in _uncorr:
        _ubb.setdefault(_e["bgc"], []).append(_e["trigger"])
    cctt["context_uncorroborated_by_bgc"] = _ubb
    cassettes = scan_cassettes(cds_list, bgcs)
    umed = scan_umed(cds_list, bgcs)
    efls = scan_efls(bgcs, cassettes, cctt, flbr)
    domain_architecture = scan_domain_architecture(bgcs, domains or [])
    resistance_tiers = resistance_tier_classification(bgcs, res, trans, cds_list=cds_list)
    wetlab_rows = generate_wetlab_rows(bgcs, WETLAB_CLASS_DEFAULTS_EXTENDED)
    qs_signals = scan_qs_signals(bgcs, cds_list)
    glycosylation_arms = scan_glycosylation_arm_candidates(bgcs)
    per_bgc_dss = compute_per_bgc_dss(bgcs, domain_architecture, resistance_tiers, cctt)
    dkp_cdps = scan_dkp_cdps("", bgcs, cds_list, domains or [])
    cctt["dkp_cdps_context"] = dkp_cdps
    rggmci = {"status": "PENDING_NOT_RUN", "reason": "RG-GMCI requires antiSMASH ClusterBlast ZIP context and is filled by cli.run_one_strain before triage/reporting."}
    primary_metabolism = scan_primary_metabolism(cds_list, bgcs)
    misanchor_guards = scan_misanchor_guards(cds_list, bgcs)
    # C1 v9.7.58: run concordance on every BGC using the found CCTT markers as the marker set.
    # Result is a per-BGC dict keyed by bgc_id -> {"verdict": str, "matched_compound": str, "details": str}.
    # Non-blocking: a missing library or any per-BGC failure produces NO_REFERENCE rather than crashing.
    concordance_per_bgc = {}
    try:
        from .concordance import concordance_for_bgc
        _cctt_per_bgc = (cctt or {}).get("per_bgc", {}) or {}
        for _bgc in bgcs:
            try:
                # v9.7.352 FIX (AMBER_CORRECTNESS FIX 1): per_bgc is a dict-of-LISTS
                # ({bgc_id: [trigger, ...]}) sourced from bgc_coupling — NOT a dict-of-dicts.
                # The old `isinstance(..., dict)` ternary was inverted, so _found was [] for
                # 100% of BGCs, forcing every anchor-resolving cluster to DISCORDANT and
                # silently killing the antimicrobial-recall boost. Read the list directly.
                _v = _cctt_per_bgc.get(getattr(_bgc, "bgc_id", ""), [])
                _found = list(_v.keys()) if isinstance(_v, dict) else list(_v)
                _res = concordance_for_bgc(_bgc, _found)
                concordance_per_bgc[getattr(_bgc, "bgc_id", "?")] = {
                    "verdict": _res.verdict,
                    "matched_compound": _res.matched_compound or "",
                    "matched_class": _res.matched_class or "",
                    "marker_frac": round(_res.markers_present_of_expected, 3) if _res.markers_present_of_expected is not None else None,
                    "size_ok": _res.size_ok,
                    "details": _res.notes or "",
                }
            except Exception as _deg_exc:
                concordance_per_bgc[getattr(_bgc, "bgc_id", "?")] = {"verdict": "NO_REFERENCE", "details": "per-bgc error"}
                from . import degradation as _degradation
                _degradation.record("source_scans.run_source_scans.concordance_per_bgc", _deg_exc,
                                    bgc_id=getattr(_bgc, "bgc_id", "?"))
    except Exception as _deg_exc:
        # concordance module unavailable; field stays empty dict
        from . import degradation as _degradation
        _degradation.record("source_scans.run_source_scans.concordance_module", _deg_exc)
    return SourceScanBundle(chitin, tfbs, blda, regs, trans, res, cctt, flbr, cassettes, umed, efls,
                            domain_architecture, resistance_tiers, wetlab_rows,
                            qs_signals, glycosylation_arms, per_bgc_dss, rggmci, primary_metabolism,
                            misanchor_guards, concordance_per_bgc)

"""singleton_filter.py — biosynthetic-relevance filter for the genome-unique singleton metric.

WHY THIS EXISTS
---------------
The rarity/singleton metric in enrichment_sections.py ranks domains by genome-wide frequency, and a
"genome-unique singleton" (frequency == 1) is treated as a novelty signal. On a fragmented genome this
over-counts: a domain can be genome-unique simply because the genome carries a single copy of a
housekeeping gene, not because it is a distinctive biosynthetic enzyme.

Concrete over-count cases from AS-XXX (v9.7.114):
  * BGC045 — 10 raw singletons, but 4 are ribosomal proteins + EF-G (translation machinery captured
    at the contig edge). Biosynthetic-real count: ~6.
  * BGC052 — 7 raw singletons, ALL of them α-glucan/glycogen enzymes (GlgE pathway = primary
    metabolism). Biosynthetic-real count: 0. This is a DROP, not a frontier lead.
  * BGC015 — 11 raw singletons (3rd-highest in strain), but most are regulatory (ArsR, HisKA),
    storage-lipid (PHB_acc), and MEP-isoprenoid primary metabolism. Biosynthetic-real count: ~2.
  * BGC063 — 13 raw singletons (highest), but ~5 are DNA-metabolism (UvrD/DEAD helicases, ParB).
    Biosynthetic-real count: ~8.

Without filtering, raw count mis-ranks BGC015 (11, mostly noise) above BGC007 (7, nearly all genuine
RiPP-maturation machinery). The filter restores the correct novelty ordering.

WHAT THIS DOES
--------------
Classifies each genome-unique domain as BIOSYNTHETIC_RELEVANT or HOUSEKEEPING using two signals:

  1. An explicit housekeeping-Pfam blocklist (the families that are genome-unique by single-copy, not
     by biosynthetic distinctiveness) — translation, DNA replication/repair, CRISPR-Cas, core central
     metabolism (glycogen, menaquinone, MEP isoprenoid), chaperones, and general transport.

  2. The antiSMASH gene-function tag of the gene carrying the domain. A domain on a gene tagged
     'biosynthetic' or 'biosynthetic-additional' is kept even if its Pfam is ambiguous; a domain on
     an untagged gene whose Pfam is on the blocklist is dropped.

The filter NEVER drops a domain on a gene antiSMASH tagged as biosynthetic-core. It is conservative:
when in doubt, a domain is kept (counted as biosynthetic-relevant), so the filter only removes
clear housekeeping noise.

MATCHING DISCIPLINE (v9.7.116 fix)
----------------------------------
The original module matched blocklist stems as bare case-insensitive substrings (`stem in domain`).
That is the substring-containment bug class (cf. the v9.7.115 marker/evidence-gate fixes): a short
stem false-matches inside an unrelated biosynthetic domain name, so the filter would SILENTLY DROP a
genuine biosynthetic singleton — the exact opposite of its purpose. Confirmed false drops under the
old rule: `Trans_AT_S1`, `PKS_Docking_S1`, `Peptidase_S1` (all caught by bare `s1`), `NADHpyr_redox`
(`nadh`), `GtrA_like` (`gtra`), `ABC1_kinase` (`abc1`).

Fix: three tiers of token-boundary matching instead of bare substring —
  * PREFIX stems   — distinctive (≥5 chars or clearly housekeeping); match as a delimited token
                     prefix, so 'Ribosom' catches 'Ribosomal_S7'/'Ribosom_S12'.
  * EXACT stems    — specific identifiers; match a complete delimited token, so 'GlgE' catches
                     'GlgE_dom' but not a longer token that merely starts with those letters.
  * WHOLE stems    — short/ambiguous tokens that collide across families ('S1', 'DEAD', 'NADH',
                     'GtrA', 'ABC1'); match ONLY when they ARE the entire domain name, so
                     'Peptidase_S1' / 'NADHpyr_redox' / 'GtrA_like' are no longer false-dropped.

INTEGRATION
-----------
Pure Mamey (deterministic). Used by:
  * the singleton-map / booklet generator (filtered count alongside raw count)
  * the enrichment_sections rarity ranking (down-weight housekeeping so genuine catalytic singletons
    rank first)
  * the tier-bias scatter (filtered singleton count is the true novelty axis)

It does NOT change any score, tier, or rank in the engine — it annotates the singleton metric only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Housekeeping Pfam/TIGRFAM blocklist, split by matching discipline (v9.7.116).
#
# PREFIX  : distinctive token, matched as a delimited prefix (catches inflected forms).
# EXACT   : specific identifier, matched as a complete delimited token.
# WHOLE   : short/ambiguous, matched only as the entire domain name (collision-safe).
# ---------------------------------------------------------------------------

_HOUSEKEEPING_PREFIX: dict[str, list[str]] = {
    "translation": [
        "Ribosom", "tRNA", "Trna", "aminoacyl", "GTP_EFTU", "LepA",
        "TIGR00484", "TIGR00485", "TIGR01029", "TIGR00981",
    ],
    "dna_replication_repair": [
        "DnaB", "Helicase", "UvrD", "UvrA", "ParBc", "DNA_processg",
        "AP_endonuc", "Exo_endo_phos", "DNA_pol", "Topoisom", "Primase",
        "Resolvase", "Integrase",
    ],
    "mobile_element_defense": [
        "CRISPR", "Cas_Cas", "Cas1", "Cas2", "Cas4", "DDE_Tnp", "Transposase",
        "T4SS-DNA_transf", "RHS_repeat",
    ],
    "central_metabolism": [
        # glycogen / alpha-glucan
        "GlgE", "Malt_amylase", "Phosphorylase", "Pullulan", "Mak_N_cap", "Alpha-amylase",
        "GalP_UDP", "TIGR02094", "TIGR02100", "TIGR02456", "CBM_48", "Glyco_hydro_20",
        # menaquinone / ubiquinone
        "VitK2", "Ubie", "UbiE", "CofH",
        # MEP isoprenoid precursor (primary)
        "GcpE", "IspD", "IspG", "IspH", "TIGR00612",
        # storage lipids / general lipid handling
        "PHB_acc", "PhaC", "Lipase_GDSL",
        # respiration / nucleotide salvage
        "Cyt_bd_oxida", "Proton_antipo", "Ribonuc_L-PSP",
        # amino-acid / nucleotide primary biosynthesis
        "Asp_Glu_race", "Pro_racemase", "A_deaminase", "IU_nuc_hydro",
        "Carboxyl_trans", "Heme_oxygenase", "F420_oxidored",
    ],
    "chaperone_stress": [
        "GroEL", "GroES", "DnaK", "DnaJ", "ClpB", "Clp_N",
        "Pro_isomerase", "Ferritin",
    ],
    "general_transport_regulation": [
        "Cation_efflux", "ECF_trnsprt", "Mg_trans", "Na_Ala_symp",
        # housekeeping cell-division / envelope
        "CrgA", "FhaA",
    ],
}

# EXACT tokens — specific but short enough that a prefix rule could over-reach.
_HOUSEKEEPING_EXACT: dict[str, list[str]] = {
    "translation": ["EFG", "EF-G", "EF_Ts", "EF-Tu"],
    "dna_replication_repair": ["HHH_3", "HHH_9", "Tex_N", "Tex_YqgF", "RecA"],
    "mobile_element_defense": ["Uma2"],
    "central_metabolism": ["Dxr", "Dxs", "DHDPS", "ACC_epsilon", "PAP2", "GalKase",
                           "P_proprotein"],
    "chaperone_stress": ["ClpB_D2", "DSBA", "OsmC", "cNMP_binding", "AHSA1"],
    "general_transport_regulation": ["Proton_antipo_M", "FtsX", "EamA", "ArAE", "FG-GAP", "SHOCT"],
}

# WHOLE-name tokens — short/ambiguous; collide with biosynthetic domains as substrings or token
# prefixes (S1↔Peptidase_S1/Trans_AT_S1, NADH↔NADHpyr_redox, GtrA↔GtrA_like, ABC1↔ABC1_kinase,
# DEAD↔a bare DEAD-box helicase). Match ONLY when the stem is the entire domain name.
_HOUSEKEEPING_WHOLE: dict[str, list[str]] = {
    "translation": ["S1"],                 # ribosomal S1 (inflected forms caught by 'Ribosom' prefix)
    "dna_replication_repair": ["DEAD"],    # DEAD-box helicase (bare); 'DEAD_box' falls through to tag
    "central_metabolism": ["NADH", "ABC1", "PCLP", "GtrA"],
    "chaperone_stress": [],
}

_PREFIX_SET: frozenset[str] = frozenset(
    s.lower() for stems in _HOUSEKEEPING_PREFIX.values() for s in stems)
_EXACT_SET: frozenset[str] = frozenset(
    s.lower() for stems in _HOUSEKEEPING_EXACT.values() for s in stems)
_WHOLE_SET: frozenset[str] = frozenset(
    s.lower() for stems in _HOUSEKEEPING_WHOLE.values() for s in stems)

# Domains that look housekeeping by name but ARE biosynthetically meaningful in a BGC context —
# an allowlist that overrides the blocklist.
_BIOSYNTHETIC_OVERRIDE: frozenset[str] = frozenset(
    d.lower() for d in [
        "RHS", "Ntox30",          # RHS contact-dependent toxins — ecological weapons, keep
        "Hemerythrin",            # non-heme di-iron tailoring — keep
        "Spermine_synth",         # polyamine incorporation into RiPP — keep
        "Peptidase_M23", "LysM",  # cell-wall enzymes inside antifungal BGCs — keep
        "Transglycosylas",
    ]
)

# antiSMASH gene-function tags that protect a domain from being filtered regardless of its Pfam.
_PROTECTED_TAGS = ("biosynthetic (rule-based-clusters)", "biosynthetic-additional", "biosynthetic (core)")


def _prefix_hit(domain_l: str) -> str | None:
    for stem in _PREFIX_SET:
        if re.search(rf"(?:^|[_-]){re.escape(stem)}", domain_l):
            return stem
    return None


def _exact_hit(domain_l: str) -> str | None:
    for stem in _EXACT_SET:
        if re.search(rf"(?:^|[_-]){re.escape(stem)}(?=[_-]|$)", domain_l):
            return stem
    return None


def _whole_hit(domain_l: str) -> str | None:
    return domain_l if domain_l in _WHOLE_SET else None


@dataclass
class SingletonClassification:
    domain: str
    biosynthetic_relevant: bool
    reason: str


def classify_singleton(domain: str, antismash_function: str = "") -> SingletonClassification:
    """Classify one genome-unique domain as biosynthetic-relevant or housekeeping.

    Decision order (first match wins):
      1. Curated biosynthetic override — always keep (handles cell-wall/toxin/tailoring enzymes
         whose names could otherwise be mistaken for housekeeping).
      2. Housekeeping blocklist — always drop. Runs BEFORE the antiSMASH tag because antiSMASH tags an
         entire rule-based cluster (including its primary-metabolism genes) as 'biosynthetic'; a
         glycogen enzyme inside a saccharide cluster carries a 'biosynthetic (saccharide)' tag but is
         still primary metabolism. The Pfam identity is authoritative for clear housekeeping families.
         Matching is token-bounded (prefix / exact / whole-name), never a bare substring (v9.7.116).
      3. antiSMASH biosynthetic tag — keep (protects genuine but Pfam-ambiguous tailoring enzymes).
      4. antiSMASH regulatory/transport tag (no biosynthetic role) — drop.
      5. Default — keep (conservative; unknown domains may be novel).
    """
    dl = domain.lower()
    fn = (antismash_function or "").lower()

    # 1. Explicit biosynthetic override — always keep.
    if dl in _BIOSYNTHETIC_OVERRIDE:
        return SingletonClassification(domain, True, "biosynthetic override (curated)")

    # 2. Housekeeping blocklist (token-bounded) — always drop, authoritative over the antiSMASH tag.
    hit = _prefix_hit(dl) or _exact_hit(dl) or _whole_hit(dl)
    if hit:
        return SingletonClassification(domain, False, f"housekeeping ({hit})")

    # 3. antiSMASH tagged the gene biosynthetic — keep a Pfam-ambiguous domain.
    if any(tag in fn for tag in _PROTECTED_TAGS):
        return SingletonClassification(domain, True, "antiSMASH biosynthetic tag")

    # 4. regulatory / transport antiSMASH tag with no biosynthetic role — drop.
    if any(t in fn for t in ("regulatory (smcogs)", "transport (smcogs)")) and "biosynthetic" not in fn:
        return SingletonClassification(domain, False, "antiSMASH regulatory/transport tag")

    # 5. Default: keep (conservative — unknown domains are treated as potentially novel).
    return SingletonClassification(domain, True, "retained (no housekeeping match)")


def filter_singletons(
    domains: list[str],
    antismash_function: str = "",
) -> tuple[list[str], list[str]]:
    """Split a gene's genome-unique domains into (biosynthetic_relevant, housekeeping).

    All domains on the gene share the same antismash_function (it is a per-gene tag).
    """
    keep, drop = [], []
    for d in domains:
        c = classify_singleton(d, antismash_function)
        (keep if c.biosynthetic_relevant else drop).append(d)
    return keep, drop


def filtered_singleton_count(
    gene_singletons: list[tuple[list[str], str]],
) -> tuple[int, int]:
    """Compute (raw, filtered) singleton-gene counts for a BGC.

    Parameters
    ----------
    gene_singletons:
        list of (domain_list, antismash_function) tuples, one per gene that carries ≥1 genome-unique
        domain. A gene counts toward the filtered total if it retains ≥1 biosynthetic-relevant
        singleton after filtering.
    """
    raw = 0
    filtered = 0
    for domains, fn in gene_singletons:
        if not domains:
            continue
        raw += 1
        keep, _ = filter_singletons(domains, fn)
        if keep:
            filtered += 1
    return raw, filtered

"""compound_class.py — deterministic compound-class annotation layer (v9.7.86).

Purpose
-------
Record, per BGC, the chemotype the cluster's own evidence is consistent with, with
its evidence trail. This is an ANNOTATION layer, not a score-bucket layer: it captures
what the engine already has access to (antiSMASH's own t2pks/terpene product-class
predictions, the resolved MIBiG product line, product classes, fired triggers) and
records it as structured fields. Most chemotypes are RECORDED ONLY (no score impact,
no comparability cost). A small, well-anchored set carries a SCORED consequence.

Evidence priority (most defensible first)
-----------------------------------------
1. antiSMASH `t2pks.product_classes` prediction (computed from the biosynthetic
   machinery; e.g. doxorubicin -> ['angucycline','aureolic acid','tetracycline',
   'anthracycline']). Read from the already-extracted product_class_predictions.
2. The resolved MIBiG product line (`closest_candidate_kcb_product`) matched against
   curated family term sets. This rides the P-7-clean own-evidence path; raw kcb_top
   is NEVER consulted here.
3. antiSMASH product classes on the BGC (`products`) as a coarse fallback.

Scoring consequence policy (the ONLY scoring change; the comparability boundary)
--------------------------------------------------------------------------------
- polyene_macrolide   -> AF (antifungal) signal.        [calibrated: 3 refs]
- anthracycline       -> own cytotoxic/antitumor category, scored & flagged.  [7 refs]
- ionophore           -> AB signal, conservative, single-reference-flagged.   [1 ref]
All other chemotypes are ANNOTATE-ONLY (record the label + evidence, no score move).

Calibrated against 32 MIBiG reference clusters (2026-06-19). Negatives that must NOT
move: marineosin (alkaloid), tautomycetin (linear PKS), yanuthone D / solanapyrone D
(fungal). Arylpolyene pigment is explicitly excluded from polyene_macrolide.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --- pharmacology categories -------------------------------------------------
PH_ANTIFUNGAL = "antifungal"
PH_ANTIBACTERIAL = "antibacterial"
PH_CYTOTOXIC = "cytotoxic/antitumor"
PH_OTHER = "other/uncharacterised"

# --- chemotype taxonomy ------------------------------------------------------
# Each entry: chemotype -> (pharmacology, scored_consequence, term set).
# scored_consequence is one of: None (annotate-only), ("af", w), ("ab", w),
# ("anthracycline", w) for the own-category scored path.
# Term sets are matched (lowercased, word-ish) against own-evidence text only.

@dataclass(frozen=True)
class Chemotype:
    name: str
    pharmacology: str
    scored: tuple | None          # None | ("af"|"ab"|"anthracycline", weight)
    terms: tuple[str, ...]
    note: str = ""
    single_reference: bool = False
    confidence: str = "MODERATE"   # HIGH (calibrated, multi-ref) | MODERATE | LOW (1-ref label)


# Order matters: more specific / higher-confidence chemotypes first, so the first
# match wins. Anthracycline before generic aromatic-T2PKS; polyene-macrolide before
# generic macrolide.
CHEMOTYPES: tuple[Chemotype, ...] = (
    # ---- SCORED categories (well-anchored, HIGH confidence) ----
    Chemotype(
        "polyene_macrolide", PH_ANTIFUNGAL, ("af", 22),
        ("nystatin", "amphotericin", "candicidin", "pimaricin", "natamycin",
         "filipin", "salinilactam", "meilingmycin", "avermectin", "milbemycin",
         "rimocidin", "polyene macrolide", "polyene-macrolactam"),
        note="Polyene-macrolide antifungal; arylpolyene pigment is excluded.",
        confidence="HIGH",
    ),
    Chemotype(
        "anthracycline", PH_CYTOTOXIC, ("anthracycline", 0),
        ("anthracycline", "doxorubicin", "daunorubicin", "cosmomycin",
         "aclarubicin", "aclacinomycin", "cinerubin", "aranciamycin",
         "rhodomycin", "nogalamycin", "elloramycin", "medermycin",
         "steffimycin", "cosmomycin"),
        note="Anthracycline: DNA-intercalating topoisomerase-II poison; cytotoxic/antitumor. "
             "Own category; routed off the clean antibacterial board with a cytotoxicity flag.",
        confidence="HIGH",
    ),
    Chemotype(
        "ionophore", PH_ANTIBACTERIAL, ("ab", 14),
        ("nanchangmycin", "monensin", "salinomycin", "lasalocid", "nigericin",
         "polyether ionophore"),
        note="Polyether ionophore; antibacterial/anticoccidial, NOT antifungal.",
        single_reference=True, confidence="MODERATE",
    ),
    # ---- ANNOTATE-ONLY cytotoxic chemotypes (record + cytotoxic flag, no score) ----
    Chemotype(
        "diazofluorene", PH_CYTOTOXIC, None,
        ("diazofluorene", "kinamycin", "lomaiviticin"),
        note="Diazofluorene: N-N diazo warhead; intensely cytotoxic. NOTE: the diazo "
             "machinery may not trip T43-NN if the cluster lacks the diazo/creE/creD tokens.",
        confidence="MODERATE",
    ),
    Chemotype(
        "cytotoxic_aromatic_other", PH_CYTOTOXIC, None,
        ("fredericamycin", "azinomycin"),
        note="Cytotoxic/antitumor aromatic polyketide outside the named chemotypes.",
        confidence="LOW",
    ),
    # ---- ANNOTATE-ONLY antibacterial / other aromatic chemotypes ----
    Chemotype(
        "tetracycline", PH_ANTIBACTERIAL, None,
        ("tetracycline", "chlortetracycline", "oxytetracycline"),
        note="Tetracycline: ribosome-targeting antibacterial.",
        confidence="MODERATE",
    ),
    Chemotype(
        "angucycline", PH_ANTIBACTERIAL, None,
        ("angucycline", "rabelomycin", "urdamycin", "jadomycin", "be-7585a",
         "gaudimycin", "landomycin"),
        note="Angucycline benz[a]anthracene aromatic polyketide; mixed antibacterial/cytotoxic.",
        confidence="MODERATE",
    ),
    Chemotype(
        "pyranonaphthoquinone", PH_ANTIBACTERIAL, None,
        ("pyranonaphthoquinone", "benzoisochromanequinone", "frenolicin",
         "medermycin", "enterocin", "granaticin", "actinorhodin", "alnumycin"),
        note="Pyranonaphthoquinone / benzoisochromanequinone aromatic polyketide.",
        confidence="MODERATE",
    ),
    Chemotype(
        "ansamycin", PH_ANTIBACTERIAL, None,
        ("ansamycin", "rifamycin", "rubradirin", "ansamitocin", "ansacarbamitocin",
         "naphthomycin", "geldanamycin"),
        note="Ansamycin / aminocoumarin-adjacent; antibacterial (rifamycin class).",
        confidence="MODERATE",
    ),
    Chemotype(
        "macrolide_other", PH_OTHER, None,
        ("spinosyn", "spinosad", "erythromycin", "tylosin", "spiramycin",
         "borrelidin", "ml-449", "macrolide"),
        note="Macrolide outside the polyene-macrolide antifungal class (e.g. spinosyn insecticide, "
             "erythromycin-class antibacterial, borrelidin). Recorded; not scored as a class.",
        confidence="LOW",
    ),
    Chemotype(
        "aromatic_t2pks_other", PH_ANTIBACTERIAL, None,
        ("colabomycin", "erdacin", "aureolic", "mithramycin", "chromomycin"),
        note="Aromatic type-II polyketide outside the named chemotypes.",
        confidence="LOW",
    ),
    # ---- ANNOTATE-ONLY new families (broadened coverage; LOW confidence, 1-ref labels) ----
    Chemotype(
        "glycopeptide", PH_ANTIBACTERIAL, None,
        ("glycopeptide", "balhimycin", "vancomycin", "teicoplanin", "chloroeremomycin",
         "ristocetin", "a47934"),
        note="Glycopeptide antibiotic (vancomycin class); Gram-positive cell-wall target. "
             "Common in Amycolatopsis.",
        confidence="LOW",
    ),
    Chemotype(
        "phenazine", PH_ANTIBACTERIAL, None,
        ("phenazine", "endophenazine", "phenazine-1-carboxylic", "iodinin"),
        note="Phenazine redox-active antibacterial/antifungal pigmented metabolite.",
        confidence="LOW",
    ),
    Chemotype(
        "nucleoside_antibiotic", PH_ANTIBACTERIAL, None,
        ("caprazamycin", "liposidomycin", "muraymycin", "tunicamycin",
         "liponucleoside", "capuramycin"),
        note="Nucleoside / liponucleoside antibiotic (MraY-targeting cell-wall inhibitor). "
             "Distinct from the peptidyl-nucleoside antifungals (nikkomycin/polyoxin) the "
             "T43-NUC trigger tracks.",
        confidence="LOW",
    ),
    Chemotype(
        "halogenated_phenolic", PH_ANTIBACTERIAL, None,
        ("pentabromopseudilin", "bromophenol", "bmp ", "pyrrole-phenol"),
        note="Brominated/halogenated phenolic-pyrrole metabolite (Pseudoalteromonas bmp class).",
        confidence="LOW",
    ),
    Chemotype(
        "prenylated_indole", PH_OTHER, None,
        ("xiamenmycin", "indolosesquiterpene", "prenylated indole", "prenylated-indole"),
        note="Prenylated indole / indolosesquiterpene metabolite.",
        confidence="LOW",
    ),
)

# Tokens that must NEVER be read as a lead chemotype (pigments and primary metabolites
# that antiSMASH product_classes can superficially type as aromatic polyketides).
PIGMENT_EXCLUSION = (
    "arylpolyene", "aryl-polyene", "ape ", "flaviolin",
    "spore pigment", "spore-pigment", "whie", "pentangular polyphenol",
    "tetracenomycin",  # spore-pigment context; only excluded for polyene_macrolide call below
)
# Fungal mycotoxins / phytotoxins and primary metabolites that are not antibacterial leads.
NONLEAD_EXCLUSION = ("patulin", "solanapyrone", "yanuthone", "eicosapentaenoic",
                     "fatty acid", "spore pigment")

# antiSMASH t2pks.product_classes -> our chemotype name. These come straight from
# antiSMASH's machinery-based prediction and are the PRIMARY evidence when present.
ANTISMASH_CLASS_MAP = {
    "anthracycline": "anthracycline",
    "tetracycline": "tetracycline",
    "angucycline": "angucycline",
    "aureolic acid": "aromatic_t2pks_other",
    "pyranonaphthoquinone": "pyranonaphthoquinone",
}


@dataclass
class CompoundClassAnnotation:
    chemotype: str = ""                 # canonical chemotype name, or ""
    pharmacology: str = ""              # antifungal | antibacterial | cytotoxic/antitumor | ...
    evidence_source: str = ""          # antismash_t2pks | resolved_mibig_product | products | none
    class_evidence: str = ""           # human-readable trail of what matched
    scored_axis: str = ""              # "" | af | ab | anthracycline
    scored_weight: float = 0.0
    cytotoxic_flag: bool = False
    single_reference: bool = False
    confidence: str = ""               # HIGH | MODERATE | LOW (label confidence)

    def as_dict(self) -> dict[str, Any]:
        return {
            "chemotype": self.chemotype,
            "pharmacology": self.pharmacology,
            "evidence_source": self.evidence_source,
            "class_evidence": self.class_evidence,
            "scored_axis": self.scored_axis,
            "scored_weight": self.scored_weight,
            "cytotoxic_flag": self.cytotoxic_flag,
            "single_reference": self.single_reference,
            "confidence": self.confidence,
        }


def _own_evidence_text(bgc) -> str:
    """Own-evidence text for term matching. NEVER includes raw kcb_top (preserves P-7).
    Uses: products + resolved MIBiG product line + mibig_hits accessions."""
    parts: list[str] = []
    parts.extend(getattr(bgc, "products", []) or [])
    rp = getattr(bgc, "closest_candidate_kcb_product", "") or ""
    if rp and rp != "UNRESOLVED":
        parts.append(rp)
    return " ".join(parts).lower()


def _chemotype_by_terms(text: str) -> Chemotype | None:
    if not text:
        return None
    pigment = any(p in text for p in PIGMENT_EXCLUSION)
    for ct in CHEMOTYPES:
        if ct.name == "polyene_macrolide" and pigment:
            continue  # arylpolyene pigment trap: never call it a polyene macrolide
        for term in ct.terms:
            if term in text:
                return ct
    return None


def _chemotype_from_antismash(product_classes: list[str]) -> tuple[Chemotype | None, str]:
    """Map antiSMASH t2pks.product_classes to a chemotype. anthracycline wins over the
    others if present (it is the most specific / highest-consequence)."""
    pcs = [p.lower() for p in (product_classes or [])]
    if "anthracycline" in pcs:
        target = "anthracycline"
    else:
        target = next((ANTISMASH_CLASS_MAP[p] for p in pcs if p in ANTISMASH_CLASS_MAP), None)
    if not target:
        return None, ""
    ct = next((c for c in CHEMOTYPES if c.name == target), None)
    return ct, ", ".join(product_classes)


def annotate_bgc(bgc, product_class_predictions: list[dict] | None = None) -> CompoundClassAnnotation:
    """Produce the compound-class annotation for one BGC.

    product_class_predictions: the already-extracted antiSMASH t2pks/terpene predictions
    (list of dicts with record_id + product_classes), filtered to this BGC's contig by
    the caller, or None when JSON evidence is off.
    """
    ann = CompoundClassAnnotation()

    # 0) Hard non-lead exclusion: fungal mycotoxins/phytotoxins, primary metabolites,
    #    and spore pigments are never lead chemotypes. Abstain entirely (claim-safe),
    #    even if a downstream term would otherwise match.
    text = _own_evidence_text(bgc)
    if any(x in text for x in NONLEAD_EXCLUSION):
        ann.evidence_source = "none"
        ann.class_evidence = "non-lead (pigment / fungal toxin / primary metabolite) — abstained"
        return ann

    # 1) Specific resolved product NAME first. antiSMASH t2pks.product_classes returns a
    #    SET of candidate classes (a tetracycline cluster legitimately resembles
    #    anthracyclines structurally), so a specific MIBiG name like "chlortetracycline"
    #    or "kinamycin" is a more specific identification than the antiSMASH class set and
    #    must win over it. Own-evidence text only (never raw kcb_top -> preserves P-7).
    ct = _chemotype_by_terms(text)
    if ct:
        rp = getattr(bgc, "closest_candidate_kcb_product", "") or ""
        src = "resolved_mibig_product" if (rp and rp != "UNRESOLVED") else "products"
        ann.evidence_source = src
        matched = next((t for t in ct.terms if t in text), "")
        ann.class_evidence = f"own-evidence term '{matched}' (source: {src})"

    # 2) antiSMASH machinery-based prediction (when the resolved name did not resolve a
    #    chemotype, e.g. UNRESOLVED product line). Still a strong, machinery-based signal.
    if ct is None and product_class_predictions:
        merged: list[str] = []
        for r in product_class_predictions:
            merged.extend(r.get("product_classes") or [])
        ct, ev = _chemotype_from_antismash(merged)
        if ct:
            ann.evidence_source = "antismash_t2pks"
            ann.class_evidence = f"antiSMASH product_classes: {ev}"

    if ct is None:
        ann.evidence_source = "none"
        return ann

    # populate annotation
    ann.chemotype = ct.name
    ann.pharmacology = ct.pharmacology
    ann.cytotoxic_flag = (ct.pharmacology == PH_CYTOTOXIC)
    ann.single_reference = ct.single_reference
    ann.confidence = ct.confidence
    # an antiSMASH-class-only call (no specific name) is one confidence step less certain
    if ann.evidence_source == "antismash_t2pks" and ct.confidence == "HIGH":
        ann.confidence = "MODERATE"

    # scored consequence (the only scoring change)
    if ct.scored is not None:
        axis, weight = ct.scored
        ann.scored_axis = axis
        ann.scored_weight = float(weight)

    return ann

"""modeb_class_checklist.py (v9.7.164) — class-triggered content expectations for Mode B cards.

Purpose: a char floor alone can be padded or can false-flag a legitimately tight section.
What distinguishes a genuinely deep card from a thin one is CLASS-SPECIFIC CONTENT — a
thioamide card that never mentions the O->S mass shift or a thioamidation cassette is thin
in substance even if it clears a char floor; a lassopeptide card that never addresses the
leader/core split or the B/C maturation enzymes is likewise hollow.

These checklists are derived empirically from pre-program reference cards (the v5.3 workflow
AS-XXX / AS-XXX bespoke cards) that represent the depth target. Each entry is a
class -> list of (concept, [aliases]) the card is EXPECTED to address somewhere. Missing
concepts are reported as CONTENT_GAP findings (WARN by default) — additive to, never a
replacement for, the char-floor depth gate. This encodes "if you see a thioamide, here is
what to look for" as a mechanical check, not just prose guidance.

The checklist is advisory/opt-in (check_class_content=True) and never blocks structurally;
it is a depth-quality signal that points the author at the specific biology the class demands.
"""
from __future__ import annotations

import re

# class-token -> list of (concept_label, [alias regexes / substrings]) expected in a deep card.
# Aliases are matched case-insensitively as substrings against the whole card body.
_CLASS_EXPECTATIONS: dict[str, list[tuple[str, list[str]]]] = {
    "thioamide": [
        ("thioamidation cassette (YcaO/TfuA family)", ["ycao", "tfua", "thioamidation cassette", "thioamide-forming"]),
        ("O->S diagnostic mass shift for LC-MS", ["o->s", "o→s", "+15.9", "15.977", "sulfur substitution", "thioamide signature"]),
        ("thioamide chemistry (backbone amide->thioamide)", ["thioamide", "thioamidat"]),
        ("metallophore / metal-limitation regulation if Dap/Sbn present", ["metallophore", "dmdr", "zur", "fur", "metal limitation", "sbna", "sbnb", "diaminopropionate", "dap"]),
    ],
    "lassopeptide": [
        ("precursor A peptide (leader + core split)", ["precursor", "leader", "core peptide", "a peptide"]),
        ("lasso B protease (leader removal)", ["b protease", "b protein", "cysteine protease", "leader removal", "leader peptidase"]),
        ("lasso C lactam synthetase (isopeptide macrolactam)", ["lactam synthetase", "c protein", "cyclase", "isopeptide", "macrolactam"]),
        ("RiPP recognition element / threading topology", ["rre", "pqqd", "recognition element", "threading", "threaded", "asparagine synth"]),
    ],
    "lanthipeptide": [
        ("precursor + leader/core", ["precursor", "leader", "core peptide"]),
        ("dehydratase (LanB/LanM)", ["lanb", "lanm", "dehydratase", "dehydrat"]),
        ("cyclase (LanC) / thioether ring", ["lanc", "cyclase", "thioether", "lanthionine"]),
    ],
    "nrps": [
        ("module architecture (C/A/T logic)", ["condensation", "adenylation", "c domain", "a domain", "module"]),
        ("adenylation substrate specificity / Stachelhaus", ["stachelhaus", "substrate specificity", "specificity code", "predicted substrate"]),
        ("thioesterase / release mechanism", ["thioesterase", "te ", "release", "cyclisation", "cyclization"]),
    ],
    "t1pks": [
        ("module architecture (KS/AT/ACP)", ["ketosynthase", "acyltransferase", "ks domain", "at domain", "acp", "module"]),
        ("reductive loop (KR/DH/ER) / oxidation state", ["ketoreductase", "dehydratase", "enoylreductase", "kr", "dh", "er", "reductive loop"]),
        ("AT substrate specificity (malonyl/methylmalonyl)", ["malonyl", "methylmalonyl", "extender", "at specificity"]),
    ],
    "terpene": [
        ("terpene synthase / cyclase", ["terpene synthase", "cyclase", "prenyltransferase"]),
        ("precursor (GPP/FPP/GGPP)", ["gpp", "fpp", "ggpp", "isoprenoid", "prenyl"]),
    ],
    "siderophore": [
        ("metal-limitation regulation (Fur/DmdR)", ["fur", "dmdr", "iron", "metal limitation", "iron repressor"]),
        ("iron-chelating moiety", ["hydroxamate", "catecholate", "chelat", "siderophore"]),
    ],
    "metallophore": [
        ("metal-limitation regulation (Fur/DmdR/ZuR)", ["fur", "dmdr", "zur", "metal limitation", "iron repressor", "zinc"]),
        ("chelating scaffold / Dap or related", ["chelat", "diaminopropionate", "dap", "staphyloferrin", "zincophorin", "metallophore"]),
    ],
    "nucleoside": [
        ("nucleoside / nucleobase core formation (this is a NUCLEOSIDE, not a RiPP: no leader/precursor peptide)", ["nucleobase", "c-glycos", "ribosyl", "pentose", "aminohexuron", "core formation", "not a ripp", "no leader", "no precursor peptide"]),
        ("subtype + mechanism as CLASS context only (peptidyl-nucleoside / chitin-synthase inhibitor = antifungal, e.g. polyoxin/nikkomycin; liponucleoside / translocase-I (MraY) inhibitor = antibacterial, e.g. capuramycin/muraymycin/tunicamycin)", ["polyoxin", "nikkomycin", "chitin synthase", "capuramycin", "muraymycin", "tunicamycin", "caprazamycin", "translocase", "mray", "peptidyl-nucleoside", "liponucleoside"]),
        ("housekeeping-vs-secondary distinction — tRNA-modification enzymes (truD etc.) are PRIMARY metabolism; a nucleoside-antibiotic capacity call must NOT rest on a tRNA-modification gene or a bare name and is necessary-not-sufficient", ["housekeeping", "primary metabolism", "necessary-not-sufficient", "not a nucleoside antibiotic", "not a nucleoside-antibiotic"]),
        ("nucleoside tailoring set (2OG-Fe(II) oxygenase, aminotransferase, radical-SAM, and a peptide-bond ligase for peptidyl-nucleosides)", ["2og", "fe(ii) oxygen", "aminotransferase", "radical sam", "radical-sam", "atp-grasp", "amide bond", "peptide-bond ligase"]),
        ("self-resistance / immunity expectation as corroboration, not proof — an antibacterial nucleoside that inhibits an ESSENTIAL producer target (translocase-I/MraY or lipid-II/peptidoglycan machinery) is expected to co-encode a self-resistance determinant (a resistant target paralog or a dedicated exporter); its presence corroborates a secondary-metabolite antibiotic call and its absence weakens one, whereas a chitin-synthase-inhibitor antifungal has no essential producer target so self-resistance is not expected", ["self-resistance", "self resistance", "immunity", "resistant paralog", "resistant target", "target paralog", "duplicated target", "co-encoded resistance", "no essential producer target"]),
    ],
}

# antiSMASH product-label token -> checklist key
_LABEL_TO_KEY = [
    ("thioamide", "thioamide"),
    ("lassopeptide", "lassopeptide"),
    ("lasso", "lassopeptide"),
    ("lanthipeptide", "lanthipeptide"),
    ("lanthi", "lanthipeptide"),
    ("nrp-metallophore", "metallophore"),
    ("metallophore", "metallophore"),
    ("siderophore", "siderophore"),
    ("t1pks", "t1pks"),
    ("transat-pks", "t1pks"),
    ("nucleoside", "nucleoside"),
    ("terpene", "terpene"),
    ("nrps", "nrps"),
]


def classes_for_products(products: str) -> list[str]:
    """Map an antiSMASH product label string to the checklist keys that apply.
    A hybrid label (e.g. 'NRPS; thioamide-NRP') can trigger several checklists."""
    p = (products or "").lower()
    keys: list[str] = []
    for token, key in _LABEL_TO_KEY:
        if token in p and key not in keys:
            keys.append(key)
    return keys


def check_class_content(card_md: str, products: str) -> list[dict]:
    """Return CONTENT_GAP findings for class-specific concepts the card fails to address.
    Advisory (severity WARN); additive to the char-floor depth gate. Empty list = the card
    addresses every expected concept for its class(es)."""
    body = (card_md or "").lower()
    findings: list[dict] = []
    seen_keys = classes_for_products(products)
    for key in seen_keys:
        for concept, aliases in _CLASS_EXPECTATIONS.get(key, []):
            if not any(a in body for a in aliases):
                findings.append({
                    "code": "CONTENT_GAP",
                    "severity": "WARN",
                    "class": key,
                    "concept": concept,
                    "message": f"{key} card does not appear to address: {concept}",
                })
    return findings


# --- class-conflict adjudication (v9.7.354) -------------------------------------------------
# antiSMASH can fire BOTH a PTM/tetramate CCTT trigger and a tetronate CCTT trigger on one locus.
# These are chemically DISTINCT grammars and must be adjudicated, not merged into one story:
#   * FkbH + a discrete ACP builds glyceryl-S-ACP — the starter logic of TETRONATE biosynthesis
#     (necessary-not-sufficient; the ring needs a co-located FabH-family KSIII closure enzyme). It is
#     NOT an HSAF/PTM hallmark.  (cf. mamey/antismash_evidence.py FkbH/fabH markers, the v9.7.183 gate.)
#   * A PTM/HSAF assignment needs an ORNITHINE-selective A-domain (an Aminotran_3 annotation alone does
#     NOT demonstrate ornithine selectivity) plus the canonical HSAF set (sterol desaturase, ferredoxin
#     reductase, arginase).
# This check WARNs (never blocks) when both triggers fire and the card does not visibly adjudicate them.

_PTM_TRIGGER_TOKENS = ("ptm", "tetramate", "hsaf")
_TET_TRIGGER_TOKENS = ("tetronate", "spirotetronate")
_ADJUDICATION_MARKERS = (
    "tetramate vs tetronate", "tetronate vs tetramate", "class-conflict", "class conflict",
    "competing tetronate", "competing hypothes", "adjudicat", "fkbh", "ornithine-selective",
    "ornithine selective", "necessary-not-sufficient",
)


def check_class_conflict(card_md: str, cctt_triggers) -> list[dict]:
    """Return a CLASS_CONFLICT WARN when PTM(tetramate) and tetronate CCTT triggers BOTH fired but the
    card does not adjudicate the two grammars. cctt_triggers may be a string or an iterable of strings.
    Advisory (severity WARN); empty list = no conflict, or the card adjudicates it."""
    if isinstance(cctt_triggers, (list, tuple, set)):
        trigs = " ".join(str(t) for t in cctt_triggers).lower()
    else:
        trigs = str(cctt_triggers or "").lower()
    has_ptm = any(t in trigs for t in _PTM_TRIGGER_TOKENS)
    has_tet = any(t in trigs for t in _TET_TRIGGER_TOKENS)
    if not (has_ptm and has_tet):
        return []
    body = (card_md or "").lower()
    if any(m in body for m in _ADJUDICATION_MARKERS):
        return []
    return [{
        "code": "CLASS_CONFLICT",
        "severity": "WARN",
        "class": "ptm|tetronate",
        "concept": ("PTM(tetramate) and tetronate CCTT triggers both fired — the card must adjudicate "
                    "(FkbH+ACP => tetronate review, necessary-not-sufficient, needs FabH-KSIII ring "
                    "closure; PTM needs an ornithine-selective A-domain, not just Aminotran_3), not "
                    "commit to one grammar"),
        "message": "dual PTM+tetronate CCTT triggers are not adjudicated in the card body",
    }]

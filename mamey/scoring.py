from __future__ import annotations
import re
from collections import Counter
from .assembly import corrected_bgc_count, assembly_tier
from . import antimicrobial_recall as _amr
from .models import BGCRecord, TriageRecord


# --- canonical lead-exclusion predicate (v9.7.376, Tier-0 shared helper) ------------------------
# triage_bgcs (below) withholds a BGC's corrected_rank when the engine flags it out of lead
# prioritization for any of THREE reasons: a standing-rule downgrade, the primary-metabolism guard,
# or the mobile-element guard. Nine downstream deliverable surfaces re-derived "is this excluded?"
# inconsistently (two figures helpers checked different key sets — figures_sapote silently omitted
# the mobile-element signal). This is the single source of truth so every consumer applies the same
# 3-signal check regardless of row schema. See AUDIT_374_META_excluded_bgc_leak_pattern.
#
# AUDIT_378 (excluded-BGC-leak family, root-cause pass): the two callers that existed when
# this helper was written (figures_extra.py / figures_sapote.py) both read bgc_data.json, whose
# rows use these lowercase snake_case keys. But the single MOST COMMON real row schema in this
# codebase is `_4_triage_board.csv`'s own DictReader rows, which use the CSV's literal TitleCase
# headers ("Standing_rule", "Primary_metab_flag", "Mobile_element_flag") — none of which matched
# any variant below. Confirmed empirically: is_lead_excluded() returned False on a raw CSV row
# carrying a real, populated Standing_rule value, entirely silently. This is very likely WHY at
# least 3 later consumers (compile_report.py, af_dossier.py, resistance_dossier.py) each
# independently reinvented their own Corrected_rank-blank check instead of calling this "canonical"
# helper on their CSV rows — it simply didn't work against that schema. Adding the real CSV column
# names as recognized variants makes this helper actually schema-agnostic across BOTH real row
# shapes in the codebase, matching what its own docstring already claims.
_LX_STANDING = ("standing_rule_flag", "standing_rule", "Standing_rule")
_LX_PRIMARY = ("primary_metabolism_flag", "primary_metab_flag", "primary_metabolism", "Primary_metab_flag")
_LX_MOBILE = ("mobile_element_flag", "mobile_element", "Mobile_element_flag")


def _lx_truthy(v) -> bool:
    return bool(v) and str(v).strip().upper() not in ("", "NONE", "FALSE", "0")


def is_lead_excluded(row) -> bool:
    """True when the engine withheld this BGC from lead prioritization (standing-rule downgrade,
    primary-metabolism guard, or mobile-element guard). Accepts any deliverable row schema; checks
    every known key variant so no consumer silently drops a signal its row names differently."""
    g = row.get
    return (any(_lx_truthy(g(k)) for k in _LX_STANDING)
            or any(_lx_truthy(g(k)) for k in _LX_PRIMARY)
            or any(_lx_truthy(g(k)) for k in _LX_MOBILE))

from . import degradation as _degradation
from .source_scans import CCTT_CLASS_COMPAT as _GATED_CLASS_TRIGGERS  # v9.7.35 #28: canonical gated set (no drift)

# ---------------------------------------------------------------------------
# Extraction-side triage scoring provenance
# ---------------------------------------------------------------------------
# These weights are *routing priors* used to sort BGCs for the judgment layer.
# They are not final WL/DAPR scores and must not be cited as biological proof.
# Provenance:
# - AB_KEYWORDS: classes commonly enriched for antibacterial leads in the Mamey
#   v1.1/v1.2 workflow (NRPS/PKS, lanthipeptides, phosphonates, carbapenems,
#   aminoglycoside-like and phenazine logic).
# - AF_KEYWORDS: classes with antifungal-search relevance in the workflow
#   (polyene/tetramate/HSAF-like, selected PKS/NRPS, siderophore ecology).
# - NOVELTY_KEYWORDS: rare/fragile or cryptic classes that should not be buried
#   by low KCB/RiQ evidence in fragmented assemblies.
# - edge_penalty: fragmentation lowers confidence and sorting priority but does
#   not erase diagnostic markers; final claim confidence is decided by the
#   Mamey judgment kernel.
# Reviewers may tune these constants, but changes should be recorded in the
# changelog because downstream batch ordering depends on them.


AB_KEYWORDS = {"nrps": 12, "t1pks": 10, "t2pks": 12, "hr-t2pks": 14, "transat-pks": 14, "lanthipeptide": 12, "lassopeptide": 10, "thioamide": 14, "thiopeptide": 14, "thiazolylpeptide": 14, "phosphonate": 15, "aminoglycoside": 14, "saccharide": 8, "phenazine": 10, "carbapenem": 18, "halogenated": 8, "ripp": 8, "azole": 8}
AF_KEYWORDS = {"t1pks": 10, "transat-pks": 12, "nrps": 8, "hsaf": 20, "polyene": 18, "nystatin": 20, "candicidin": 18, "tetramate": 16, "terpene": 6, "siderophore": 4, "metallophore": 4, "nucleoside": 18, "nikkomycin": 20, "polyoxin": 20, "chitin": 12, "ptm": 12, "sgr ptm": 14}

# Diagnostic-marker layer (option 2+3 fix): CCTT/cassette triggers that PROVE a bioactivity class even when the
# product label and KCB anchor carry no matching word (the nikkomycin/BGC008 case — labelled only "nucleoside;
# other", KCB-dark, but T43-NUC + the NikJ TIGRFAM make it a definitive antifungal). The scorer reads these so
# diagnostic evidence reaches the tier gate instead of being computed and dropped.
AF_DIAGNOSTIC_TRIGGERS = {"T43-NUC", "T43-PTM", "T43-PYE"}  # nucleoside chitin-synthase inhibitors + HSAF/PTM macrolactams + polyene macrolides -> antifungal
AB_DIAGNOSTIC_TRIGGERS = {"T43-LAN", "T43-LASSO", "T43-THA",  # lanthi/lasso/thioamide -> anti-Gram-positive
                          # v9.7.20: two textbook antibacterial classes wired to grant the diagnostic AB bonus,
                          # making the high-confidence detector layer consistent with the keyword weights the
                          # scorer already carries (phosphonate=15, aminoglycoside=14, the top AB keywords).
                          # T43-PHO: phosphonate antibiotics (fosfomycin/dehydrophos class). T43-AMC: amino-
                          # glycoside/aminocyclitol (kanamycin/gentamicin class) — and because T43-AMC FIRES only
                          # on its own 2-deoxy-scyllo-inosose/dois/btrC diagnostic, a fired AMC is a real
                          # aminoglycoside, not the similarity-only KCB anchor the mis-anchor guard suppresses.
                          # T43-BLA (v9.7.21): beta-lactam class (nocardicin/monobactam, isopenicillin/clavam) ->
                          # antibacterial. Like T43-AMC it fires only on its own biosynthetic diagnostics, so a
                          # fired BLA is a real beta-lactam cluster, not a similarity-only anchor.
                          # T43-GPA / T43-BLT (v1.9.99): glycopeptide (OxyB/DPGS committed markers, vancomycin
                          # class) and betalactone (PEP-utilizer + biotin-carboxylase pair, platensimycin class)
                          # -> antibacterial. Both fire only on their own biosynthetic diagnostics (not a
                          # similarity-only anchor), mirroring T43-AMC/T43-BLA.
                          "T43-PHO", "T43-AMC", "T43-BLA", "T43-GPA", "T43-BLT"}
# v9.7.19 tuning (blast-radius audit): the TIER_1 floor (float a Tier-1-diagnostic BGC to >=Medium so a
# KCB-dark gene-only CLASS lead isn't buried) must NOT fire on a lone tailoring-enzyme marker. Halogenase /
# fluorinase-chlorinase signal a MODIFICATION, not a product class — they occur across many classes and are
# common, so a lone one is not the class lead the floor exists to rescue (it accounted for ~half of all
# floored BGCs). A class-defining marker that CO-OCCURS still floors; the tailoring marker stays a recorded
# CCTT signal. NOT applied to the AF/AB diagnostic bonus or the primary-metab/misanchor exemptions.
TIER1_FLOOR_EXCLUDED_PREFIXES = ("T43-HAL_", "T43-XHAL_")
DIAGNOSTIC_BONUS = 25                                       # added to the relevant axis when a diagnostic trigger fires
NOVELTY_KEYWORDS = {"transat-pks": 18, "thioamide": 15, "phosphonate": 15, "enediyne": 18, "azoxy": 18, "ranthipeptide": 12, "ripp": 10, "nrps": 8, "t1pks": 8, "t2pks": 8, "hgle": 12}

def product_text(bgc: BGCRecord) -> str:
    parts = list(bgc.products) + list(bgc.mibig_hits)
    if bgc.kcb_top:
        parts.append(bgc.kcb_top)
    # v9.7.19: also fold in the closest MIBiG product line, so the AF/AB keyword score sees the full top
    # KCB anchor per region (the HSAF/PTM name often lives here, not in kcb_top, which can be a genome
    # self-hit). "UNRESOLVED" is the no-candidate sentinel and is skipped.
    ccp = getattr(bgc, "closest_candidate_kcb_product", "")
    if ccp and ccp != "UNRESOLVED":
        parts.append(ccp)
    return " ".join(parts).lower()


def scoring_class_text(bgc: BGCRecord) -> str:
    """Text the AB/AF/novelty KEYWORD scorer should see — the BGC's OWN class evidence only.

    v9.7.85 (P-7 contamination fix): `product_text` folds in `bgc.kcb_top`, which for the
    common genome-self-hit case is a free-text genome description like
    "Natronosporangium hydrolyticum ... | Type: NRPS,NRPS-like,T1PKS,T2PKS". Those class
    tokens describe the REFERENCE ORGANISM'S other clusters, not this BGC, yet score_keywords
    over the full blob banked them as this BGC's own class credit — e.g. a bare `saccharide`
    BGC (AS-XXX BGC053) scored +34 AB from nrps/t1pks/t2pks that are not in its products.
    The saccharide standing rule masked the outcome there, but the inflation is latent on any
    non-excluded BGC whose KCB anchor description happens to contain class words.

    Fix: the keyword scorer sees the BGC's own `products`, its `mibig_hits`, and a RESOLVED
    MIBiG product line (`closest_candidate_kcb_product` when not UNRESOLVED — this is the
    matched-cluster product name, e.g. "HSAF"/"clifednamide", a legitimate class signal per
    the v9.7.19 rationale). It does NOT see the raw `kcb_top` genome-description blob. KCB
    still informs novelty (kcb_cumulative) and display (preferred_kcb_anchor) as before; only
    the per-class KEYWORD CREDIT is scoped to the cluster's own evidence.
    """
    parts = list(bgc.products) + list(bgc.mibig_hits)
    ccp = getattr(bgc, "closest_candidate_kcb_product", "")
    if ccp and ccp != "UNRESOLVED":
        parts.append(ccp)
    return " ".join(parts).lower()



def preferred_kcb_anchor(bgc: BGCRecord) -> tuple[str, str]:
    """Best display anchor for the 'known-cluster hit' field (P1-C). `kcb_top` is the raw rank-1
    knownclusterblast line, which a genome self-hit dominates: across a 3,422-BGC corpus only ~2.2% surface
    a MIBiG accession in `kcb_top`, vs ~59% resolved in deep analysis (the granaticin positive control was
    the visible tip — its `kcb_top` is the S. vietnamensis genome self-hit, masking the granaticin MIBiG
    line). The resolved MIBiG line is ALREADY captured separately in `closest_candidate_kcb_product` /
    `closest_mibig_accession` when `closest_product_provenance == "MIBIG_REFERENCE_LINE"`. Consumers that
    display the known-cluster hit (workbook kcb column, figures, lead tables, B3 family recompute) should
    call this and prefer the resolved field; it surfaces an already-captured field, it does NOT re-rank
    `kcb_top`. Still a SIMILARITY signal — KCB = similarity, not identity. Returns (anchor_text, provenance)."""
    prov = getattr(bgc, "closest_product_provenance", "UNRESOLVED")
    ccp = getattr(bgc, "closest_candidate_kcb_product", "UNRESOLVED")
    acc = getattr(bgc, "closest_mibig_accession", "UNRESOLVED")
    if prov == "MIBIG_REFERENCE_LINE" and ccp and ccp != "UNRESOLVED":
        label = f"{ccp} ({acc})" if acc and acc != "UNRESOLVED" else ccp
        return label, "MIBIG_REFERENCE_LINE"
    return (bgc.kcb_top or "UNRESOLVED"), (prov if prov and prov != "UNRESOLVED" else "KCB_TOP_FIELD")

# Pigment / non-lead product classes that must not inflate routing priors.
# Arylpolyenes are APE-type pigments, NOT polyene-macrolide antifungals — they
# previously scored on the AF axis via a bare substring match of "polyene".
PIGMENT_NONLEAD_CLASSES = {"arylpolyene", "ladderane"}

# v9.7.7 P0 guard: weak/over-call product labels. antiSMASH commonly fires these on a lone
# adenylation / terpene / sugar / pigment signal. A region whose OWN product class is *only* these AND
# that carries a housekeeping/pigment core-gene marker (scan_primary_metabolism) is a
# primary-metabolism / pigment false positive (SID-XXX topoisomerase "NRPS-like"; carotenoid "terpene";
# arylpolyene pigment). A committed class (nrps/t1pks/lanthipeptide/…) or a Tier-1 diagnostic overrides.
WEAK_OVERCALL_CLASSES = {"nrps-like", "terpene", "terpene-precursor", "saccharide", "arylpolyene",
                         "other", "t2pks", "t3pks", "pks-like", "fatty_acid", "redox-cofactor",
                         "quinone_isoprenoid_chain",
                         # BH-007 / BH-007b: iron/metal-acquisition classes are not drug-lead backbones.
                         # Marking them weak lets the NI-SIDEROPHORE / NRP-METALLOPHORE downgrade fire on
                         # pure iron-acquisition clusters, while a co-present committed backbone (NRPS/PKS/
                         # RiPP/lanthipeptide) still reads as committed and keeps its lead via the guard.
                         "ni-siderophore", "nrp-metallophore"}

# F2 — RiPP-family product classes. A RiPP region that is a truncated sub-8kb fragment with no precursor
# captured cannot be evaluated as a product (e.g. a lone LanM synthetase, or a dehydratase beside a
# gas-vesicle operon). RIPP_FRAGMENT_FLOOR caps such fragments at Inventory so they can't float above a
# complete cluster on a modifying-enzyme + KCB signal alone. Size+edge are conservative precursor proxies
# (full RiPP cores with precursor + maturation + transport are larger / Interior); a gene-level
# precursor-CDS signal would refine this further.
RIPP_FAMILY_CLASSES = {"lanthipeptide", "lassopeptide", "lasso", "lap", "thioamitide", "ripp", "ripp-like",
                       "sactipeptide", "thiopeptide", "linaridin", "lanthidin", "bacteriocin",
                       "lipolanthine", "rre-containing", "graspetide", "sphaerimicin"}
RIPP_FRAGMENT_MAX_KB = 8.0

# v9.7.8 permanent-exclusion standing rules — always-on board downgrades (independent of the gene-marker
# gate). Detected from product label + KCB anchor. These DOWNGRADE the lead tier and drop the row from the
# corrected lead order, but DO NOT zero the raw scores (evidence trail preserved). Note: for hglE-KS the
# structural novelty (zero KCB) still stands — only the drug-lead / habitat-specificity claim is downgraded,
# so the novelty score is intentionally left intact.
# B1 (build -r): standing rules are read from the registry (mamey/data/rules_registry.json, the single
# source of truth) — NOT a hardcoded duplicate. The registry is loaded ONCE and cached at module level so
# this stays off the per-BGC hot path. A registry id maps to the flag string the triage note expects; rules
# whose pattern must match OWN product labels (not a KCB/MIBiG anchor) are listed in _OWN_PRODUCTS_ONLY.
from mamey.rules import (load_registry as _load_registry,
                         load_inventory_tier_policy as _load_inventory_tier_policy,
                         _guarded as _rule_guarded)

_RULE_FLAG = {"SACCHARIDE": "saccharide-exclusion", "NAPAA": "NAPAA-exclusion", "HGLE-KS-PREV-001": "hglE-KS-PREV-001",
              # BH-007 / BH-007b: iron/metal-acquisition exclusions. NOT in _BYPASS_COMMITTED_CLASS_GUARD,
              # so a committed NRPS/PKS/RiPP backbone co-carrying the siderophore arm keeps its lead.
              "NI-SIDEROPHORE": "NI-siderophore-exclusion", "NRP-METALLOPHORE": "NRP-metallophore-exclusion"}
# These match the BGC's OWN product class labels (not a KCB/MIBiG anchor), like saccharide.
_OWN_PRODUCTS_ONLY = {"SACCHARIDE", "NI-SIDEROPHORE", "NRP-METALLOPHORE"}
# Rules that bypass the committed-class guard: NAPAA and hglE-KS are annotation-domain flags that fire
# even when a cluster has committed PKS/NRPS backbone classes. A cluster with both T1PKS and hglE-KS
# is still a hexacosalactone-class downgrade; a cluster with both NRPS and NAPAA annotation is still
# NAPAA-excluded. Without this bypass, standing_rule_flag stays empty on these mixed-class clusters
# (Audit Flag A from M56 BGC044/BGC049 analysis). (v9.7.58)
_BYPASS_COMMITTED_CLASS_GUARD = {"NAPAA", "HGLE-KS-PREV-001"}
_DOWNGRADE_RULES = None

def _downgrade_rules():
    """Lead-blocking downgrade rules from the registry, compiled once and cached."""
    global _DOWNGRADE_RULES
    if _DOWNGRADE_RULES is None:
        _DOWNGRADE_RULES = tuple(r for r in _load_registry() if r.action == "downgrade" and r.lead_blocking)
    return _DOWNGRADE_RULES


def standing_rule_for(own_products_text: str, full_text: str) -> str:
    """Return ';'-joined permanent-exclusion rules that fire, sourced from the registry.

    A standing-rule downgrade NEVER buries a committed biosynthetic lead: it applies only when the BGC's
    OWN product classes are exclusively weak/over-call labels. A real NRPS/PKS/RiPP that merely carries a
    saccharide tailoring arm keeps its lead status. saccharide is read from OWN products only; KCB-anchor
    rules read the full product+MIBiG+KCB text, but the committed-class guard still protects real leads
    whose KCB anchor merely resembles an excluded product (KCB = similarity).

    Exception: rules in _BYPASS_COMMITTED_CLASS_GUARD (NAPAA, hglE-KS-PREV-001) fire even on committed-class
    clusters because they are annotation-domain flags — a PKS cluster that also carries the hglE-KS domain
    or NAPAA annotation is still subject to those standing rules regardless of backbone class.
    """
    own_classes = {t.strip() for t in re.split(r"[;,/|]+|\s+", own_products_text) if t.strip()}
    committed = own_classes and not (own_classes <= WEAK_OVERCALL_CLASSES)
    hits = []
    for rule in _downgrade_rules():
        if committed and rule.id.upper() not in _BYPASS_COMMITTED_CLASS_GUARD:
            continue   # committed biosynthetic lead — standing rules do not apply (except bypass set)
        text = own_products_text if rule.id.upper() in _OWN_PRODUCTS_ONLY else full_text
        for pat in rule.patterns:
            m = pat.search(text)
            if m and not (rule.false_positive_guard and _rule_guarded(m.group(0), text, m.start(), rule.false_positive_guard)):
                hits.append(_RULE_FLAG.get(rule.id.upper(), rule.id.lower()))
                break
    return ";".join(hits)


def standing_rule_reason(flag: str) -> str:
    """Return the registry-owned machine reason and evidence distinctions."""
    reverse = {value: key for key, value in _RULE_FLAG.items()}
    reasons: list[str] = []
    by_id = {rule.id.upper(): rule for rule in _downgrade_rules()}
    for item in (part.strip() for part in str(flag).split(";") if part.strip()):
        rule = by_id.get(reverse.get(item, item).upper())
        if rule is None:
            continue
        detail = rule.reason_code or rule.id
        if rule.evidence_distinctions:
            detail += "; " + "; ".join(rule.evidence_distinctions)
        reasons.append(detail)
    return " | ".join(reasons)

# More-specific subclass -> the generic class it already implies. When the
# subtype is present the generic must NOT also bank its weight (e.g. "hr-t2pks"
# must not additionally count "t2pks"; "transat-pks" must not also count "t1pks").
SUBCLASS_SUBSUMES = {"hr-t2pks": "t2pks", "transat-pks": "t1pks"}


def _key_present(key: str, text: str) -> bool:
    """True iff `key` occurs as a delimiter-bounded class token in `text`.

    Boundaries are any non-alphanumeric char (hyphen, underscore, space, ';' …).
    This keeps legitimate delimited subtypes ("t2pks" in "hr-t2pks", "azole" in
    "azole-containing-ripp", "siderophore" in "ni-siderophore") while rejecting
    glued substrings ("polyene" inside "arylpolyene") — the source of the AB/AF
    inflation. `text` is already lower-cased by `product_text`.
    """
    return re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", text) is not None


def score_keywords(text: str, weights: dict[str, int]) -> float:
    """Sum class-routing weights, once per distinct class.

    Fixes two defects: (1) substring matching that let pigments score as
    antifungals and let nested PKS subtype labels double-count; (2) unbounded
    stacking of every nested token. Delimited-word matching + subsumption mean a
    region banks each chemical class at most once, at its most-specific weight.
    """
    matched = {key for key in weights
               if key not in PIGMENT_NONLEAD_CLASSES and _key_present(key, text)}
    for sub, generic in SUBCLASS_SUBSUMES.items():
        if sub in matched and generic in matched:
            matched.discard(generic)
    return float(sum(weights[k] for k in matched))

def edge_penalty(edge_status: str) -> float:
    # v9.7.84: edge/full-contig penalty NEUTRALIZED to zero.
    # Rationale (empirically grounded, AS cohort + selvamicin case): the boundary penalty
    # had no measurement basis — Edge/FC BGCs show no truncation signature in their base
    # score (mean base AB Interior 34.7 vs Edge 35.7 vs FC 35.3; keyword credit and span
    # equivalent across boundary status), so the penalty was a flat pessimism prior, not a
    # correction for missing genes. At the Medium threshold it was decisive (flipped 83% of
    # near-threshold Edge/FC leads to Inventory) on an unmeasured assumption — burying exactly
    # the overlooked fragments this tool exists to surface (e.g. selvamicin BGC0001773, a
    # Full-contig high-value attine antifungal polyene, sank to Inventory partly on this penalty).
    # Truncation uncertainty is preserved as a CONFIDENCE signal via architecture_confidence
    # (Edge/FC -> Arch C/D) and the edge_status field in the rationale, NOT as a score deduction.
    # The function is retained (returns 0) so all call sites and the 0.35/0.2 multipliers stay
    # intact and a future calibrated penalty can be reintroduced from one place if outcome data warrants.
    return 0.0

def render_rationale(bgc, *, rg_note="", floored=False, floor_triggers=(), ripp_floored=False, af_diag=False,
                     corrob_triggers=(), _uncorr=frozenset(), triggers=frozenset(), primary_flag=False,
                     pm_families=(), standing_rule="", misanchor_flag="", esignal_note="", mobile_flag=False,
                     mobile_families=()):
    """Build the TriageRecord rationale string. Split out of the inline TriageRecord construction so the
    rendering is unit-testable independently of scoring (auditor #17). Pure formatting, no scoring logic;
    output is byte-identical to the prior inline f-string. D2 (.406): the KCB evidence state is named only
    when it is recorded on the record and is not OBSERVED — an object without the field (legacy record,
    test fixture) renders exactly as before; an absent KCB input never moves novelty and is named so the
    reader sees why."""
    _kcb_state = getattr(bgc, "kcb_evidence_state", None)
    _kcb_state_note = f"; KCB_state={_kcb_state}" if _kcb_state and _kcb_state != "OBSERVED" else ""
    return f"{bgc.edge_status}; Arch {bgc.architecture_confidence}; KCB={bgc.kcb_cumulative}{_kcb_state_note}; RiQ={bgc.riq_score}; products={', '.join(bgc.products[:5]) or 'unresolved'}{('; ARCH-CAPACITY: ' + bgc.architecture_capacity + ' [' + bgc.architecture_class_confidence + ']') if getattr(bgc, 'architecture_capacity', '') else ''}{rg_note}{('; DIAG-FLOOR: ' + ','.join(floor_triggers) + ' floored to Medium') if floored else ''}{('; RIPP-FRAGMENT-FLOOR: completeness=fragment_no_precursor (RiPP-family, truncated <8kb, no precursor captured) — capped at bottom tier (Low for RiPP-family, class-gated)') if ripp_floored else ''}{('; AF-diagnostic('+','.join(t for t in corrob_triggers if any(d in t for d in AF_DIAGNOSTIC_TRIGGERS))+')') if af_diag else ''}{('; CCTT-UNCORROBORATED ('+','.join(sorted(_uncorr & set(triggers)))+'): fired on class-incompatible locus — excluded from class-capacity bonus/floor') if (_uncorr & set(triggers)) else ''}{('; PRIMARY-METAB/PIGMENT FLAG ('+','.join(sorted(pm_families))+'): AB/AF credit suppressed — housekeeping/pigment core, treat as non-bioactivity') if primary_flag else ''}{('; STANDING-RULE DOWNGRADE ('+standing_rule+'): excluded from corrected lead rank; reason=' + standing_rule_reason(standing_rule) + ('; structural novelty unaffected' if 'hglE' in standing_rule else '')) if standing_rule else ''}{('; MIS-ANCHOR ('+misanchor_flag+'): KCB anchor lacks its class diagnostic — anchor-derived credit suppressed') if misanchor_flag else ''}{('; MOBILE-ELEMENT DEMOTION ('+','.join(mobile_families)+'): region dominated by mobile/ICE machinery, not independently class-typed — AB/AF credit suppressed') if mobile_flag else ''}{esignal_note}"


# --- AQUARIUS_01 (v9.7.350/.351): class-gated bottom tier ----------------------------------------
# the Developer or User's rule (2026-08-04): the Inventory tier is reserved for genuinely low-interest HOUSEKEEPING
# classes. A BGC whose product classes are ALL housekeeping stays "Inventory"; a BGC carrying any
# specialized / antimicrobial-capable class that merely scored below the Medium threshold is labelled
# "Low" (a real specialized cluster, deprioritized) instead of being buried in Inventory. This relabels
# ONLY the bottom bucket, by CLASS. It changes no AB/AF/novelty score and no tier at Medium or above.
# Claim-safe: tiers are auto-floor ROUTING PRIORS, not measured activity; "specialized" is biosynthetic-
# class CAPACITY, never a product/activity claim. Judgment deferred.
# The class policy is loaded once from the governed rules registry.  No parallel
# hard-coded allow-list is retained in the scorer.
_INVENTORY_TIER_POLICY = _load_inventory_tier_policy()
CORE_HOUSEKEEPING_INVENTORY_CLASSES = frozenset(
    _INVENTORY_TIER_POLICY["core_housekeeping_classes"])
HOUSEKEEPING_INVENTORY_CLASSES = frozenset(
    _INVENTORY_TIER_POLICY["housekeeping_classes"])
INVENTORY_AMBIGUOUS_REVIEW_TOKENS = frozenset(
    _INVENTORY_TIER_POLICY["ambiguous_review_tokens"])
_NEUTRAL_PRODUCT_TOKENS = frozenset(_INVENTORY_TIER_POLICY["neutral_tokens"])
_INVENTORY_SUBSTRING_ALIASES = tuple(
    (a["contains"], a["canonical"])
    for a in _INVENTORY_TIER_POLICY["substring_aliases"])


def _norm_product_class(t: str) -> str:
    t = t.strip().lower()
    for needle, canonical in _INVENTORY_SUBSTRING_ALIASES:
        if needle in t:
            return canonical
    return t


def is_housekeeping_only(bgc) -> bool:
    """True iff every resolved product class is in HOUSEKEEPING_INVENTORY_CLASSES.
    An unresolved region (no class) is treated as background — unchanged from prior Inventory.

    v9.7.374: a raw token that is itself one of the registry's own `ambiguous_review_tokens`
    (e.g. 'oligosaccharide') blocks the housekeeping-only verdict rather than being silently
    folded into the housekeeping class by `_norm_product_class`'s substring alias ('oligo' +
    'saccharide' contains the 'saccharide' substring). This enforces the registry's own stated
    policy — "Rows containing an ambiguous_review_token ... require a keyed human disposition
    before a cohort-level reviewed-Inventory claim" — by routing such rows to the visible 'Low'
    bottom tier instead of the buried 'Inventory' tier until that review happens.
    `INVENTORY_AMBIGUOUS_REVIEW_TOKENS` was loaded from the registry at module scope but never
    consulted anywhere before this fix."""
    classes = set()
    for p in getattr(bgc, "products", []) or []:
        for raw_tok in re.split(r"[;,/]", str(p).lower()):
            raw_tok = raw_tok.strip()
            if raw_tok in INVENTORY_AMBIGUOUS_REVIEW_TOKENS:
                return False
            c = _norm_product_class(raw_tok)
            if c and c not in _NEUTRAL_PRODUCT_TOKENS:
                classes.add(c)
    return (not classes) or (classes <= HOUSEKEEPING_INVENTORY_CLASSES)


def bottom_tier(bgc) -> str:
    """Bottom-of-ladder label: 'Inventory' for housekeeping-only, else the new 'Low'."""
    return "Inventory" if is_housekeeping_only(bgc) else "Low"


def triage_bgcs(bgcs: list[BGCRecord], rggmci: dict | None = None, scans=None) -> list[TriageRecord]:
    """Sort BGCs for judgment, with RG-GMCI rescue support applied first.

    RG-GMCI support raises routing priority for fragmented regions that are
    linked to other BGC fragments through high/moderate shared-reference
    geometry. It does not raise claim confidence.

    `scans` (optional SourceScanBundle): when supplied, the per-BGC CCTT/cassette
    diagnostic layer is read so a definitive bioactivity marker (e.g. T43-NUC for a
    nucleoside chitin-synthase inhibitor) (a) adds a bonus to the relevant axis and
    (b) floors the tier to at least Medium — fixing the failure where diagnostic
    evidence is computed but never reaches the text-only tier gate. Backward
    compatible: scans=None reproduces the prior behaviour exactly.
    """
    records = []
    rg_support: dict[str, list[dict]] = {}
    for pair in (rggmci or {}).get("ranked_pairs", []):
        conf = pair.get("rggmci_confidence")
        if conf not in {"HIGH_RG_GMCI_RESCUE", "MODERATE_RG_GMCI_CANDIDATE"}:
            continue
        for bid in (pair.get("bgc_a"), pair.get("bgc_b")):
            if bid:
                rg_support.setdefault(bid, []).append(pair)
    # per-BGC diagnostic markers (defensive: tolerate missing/odd shapes)
    cctt_per_bgc: dict = {}
    rt_per_bgc: dict = {}
    pm_per_bgc: dict = {}
    mis_per_bgc: dict = {}
    cctt_uncorrob_by_bgc: dict = {}
    if scans is not None:
        try:
            cctt_per_bgc = (getattr(scans, "cctt", {}) or {}).get("per_bgc", {}) or {}
        except Exception as _deg_exc:
            cctt_per_bgc = {}
            _degradation.record("scoring.triage_bgcs.cctt_per_bgc", _deg_exc)
        try:
            cctt_uncorrob_by_bgc = (getattr(scans, "cctt", {}) or {}).get("context_uncorroborated_by_bgc", {}) or {}
        except Exception as _deg_exc:
            cctt_uncorrob_by_bgc = {}
            _degradation.record("scoring.triage_bgcs.cctt_uncorrob_by_bgc", _deg_exc)
        try:
            rt_per_bgc = (getattr(scans, "resistance_tiers", {}) or {}).get("per_bgc", {}) or {}
        except Exception as _deg_exc:
            rt_per_bgc = {}
            _degradation.record("scoring.triage_bgcs.rt_per_bgc", _deg_exc)
        try:
            pm_per_bgc = (getattr(scans, "primary_metabolism", {}) or {}).get("per_bgc", {}) or {}
        except Exception as _deg_exc:
            pm_per_bgc = {}
            _degradation.record("scoring.triage_bgcs.pm_per_bgc", _deg_exc)
        try:
            mis_per_bgc = (getattr(scans, "misanchor_guards", {}) or {}).get("per_bgc", {}) or {}
        except Exception as _deg_exc:
            mis_per_bgc = {}
            _degradation.record("scoring.triage_bgcs.mis_per_bgc", _deg_exc)
    for bgc in bgcs:
        txt = product_text(bgc)
        # v9.7.85 (P-7): keyword credit scores the BGC's OWN class evidence only, NOT the raw
        # kcb_top genome-description blob (which folds in the reference organism's unrelated
        # class tokens and inflated AB/AF — see scoring_class_text). `txt` (full product_text)
        # is retained below for the uses that legitimately want the anchor text.
        class_txt = scoring_class_text(bgc)
        # AUG3_07 (protocluster-split de-inflation): a composite region's `products` is the UNION of its
        # merged single-class protoclusters, so score_keywords banks every co-captured class and inflates
        # AB/AF. Score each protocluster's OWN product class and take the strongest, instead of the union.
        # chemical_hybrid regions keep their union text (genuine single compound). Adds no new claim.
        _pc_prods = [(p.get("product") or "") for p in (getattr(bgc, "protocluster_breakdown", None) or []) if p.get("product")]
        _overmerge_state = getattr(bgc, "overmerge_state", "")
        if _overmerge_state in {"", "NOT_VERIFIABLE"}:  # backward-compatible records from older packages
            _overmerge_state = (
                "OVERMERGE_SUSPECT"
                if getattr(bgc, "protocluster_count", 0) >= 2
                and not getattr(bgc, "has_chemical_hybrid", False)
                else "NO_OVERMERGE_SIGNAL"
            )
        _deinflate = (_overmerge_state == "OVERMERGE_SUSPECT"
                      and len({p.lower() for p in _pc_prods}) >= 2)
        if _deinflate:
            base_ab = 25 + max(score_keywords(pp.lower(), AB_KEYWORDS) for pp in _pc_prods)
            base_af = 20 + max(score_keywords(pp.lower(), AF_KEYWORDS) for pp in _pc_prods)
            novelty = 30 + max(score_keywords(pp.lower(), NOVELTY_KEYWORDS) for pp in _pc_prods)
        else:
            base_ab = 25 + score_keywords(class_txt, AB_KEYWORDS)
            base_af = 20 + score_keywords(class_txt, AF_KEYWORDS)
            novelty = 30 + score_keywords(class_txt, NOVELTY_KEYWORDS)
        # v9.7.86: compound-class scored consequence. Only the three well-anchored families
        # carry one (polyene_macrolide -> AF, ionophore -> AB, anthracycline -> own category).
        # The annotation was computed from own-evidence only (P-7-clean), so applying its
        # weight here does not reintroduce kcb_top contamination. anthracycline's "own
        # category" is a routing/flag, not an AB/AF lift, so it adds 0 to AB/AF (weight 0).
        _cca = getattr(bgc, "compound_class_annotation", {}) or {}
        _cc_axis = _cca.get("scored_axis") or ""
        _cc_w = float(_cca.get("scored_weight") or 0.0)
        # v1.9.99: record polyene-macrolide chemotype AF credit so a corroborated T43-PYE
        # diagnostic can SUBSUME it (clamp, not stack) — the diagnostic is the higher-confidence
        # signal for the same class; stacking keyword+chemotype+diagnostic would over-score polyenes.
        _polyene_chemotype_af = 0.0
        if _cc_axis == "af":
            base_af += _cc_w
            if str(_cca.get("chemotype") or "") == "polyene_macrolide":
                _polyene_chemotype_af = _cc_w
        elif _cc_axis == "ab":
            base_ab += _cc_w
        # anthracycline (_cc_axis == "anthracycline"): own cytotoxic category, carried as a
        # flag + routing in the annotation; no AB/AF score change here.
        # diagnostic-marker layer: prefixes match T43-NUC_nucleoside etc.
        triggers = cctt_per_bgc.get(bgc.bgc_id, []) or []
        if isinstance(triggers, dict):
            triggers = list(triggers.keys())
        # N-05 phase 2: an uncorroborated class-defining trigger (fired on a class-incompatible BGC — e.g. T43-PHO
        # on a T3PKS, T43-BLA on a terpene) is not a genuine class signal HERE. It is recorded (evidence-conserving)
        # but must NOT grant the AB/AF diagnostic bonus, exempt the primary-metab/mis-anchor guards, or floor the
        # tier. The class-capacity claim is built only from corroborated triggers; the judgment layer still sees the
        # flagged trigger for review.
        _uncorr = set(cctt_uncorrob_by_bgc.get(bgc.bgc_id, []) or [])
        # v9.7.35 #28: corroboration <-> mobile composition. A gated class-defining trigger on a
        # MOBILE-DOMINANT region whose class-defining enzyme is absent (architecture class
        # confidence LOW) is NOT corroborated by a mere matching product LABEL. Mark it
        # uncorroborated so it loses the AB/AF diagnostic bonus AND stops setting tier1_diag
        # (which was suppressing the v9.7.33 mobile-element demotion -- the two guards did not
        # compose). Verified on real data: NZ_CP029601.1 BGC032 (mobile-dominant ICE, label
        # lanthipeptide-class-v, no LanC/LanM cyclase, siderophore KCB). Promiscuous triggers
        # (HAL/XHAL/NN) are not in _GATED_CLASS_TRIGGERS, so a genuine halogenated cluster on a
        # mobile background is untouched.
        _rt28 = rt_per_bgc.get(bgc.bgc_id, {})
        if (isinstance(_rt28, dict) and _rt28.get("mobile_dominant")
                and str(getattr(bgc, "architecture_class_confidence", "")).upper() == "LOW"):
            _uncorr |= {t for t in triggers if t in _GATED_CLASS_TRIGGERS}
        corrob_triggers = [t for t in triggers if t not in _uncorr]
        trig_str = " ".join(str(t) for t in corrob_triggers)
        # T43-PYE architecture gate: a genuine polyene macrolide backbone is a large modular PKS
        # (>= _POLYENE_MIN_KS PKS_KS domains). A polyene NAME on a sub-4-KS fragment must NOT grant the
        # AF diagnostic bonus and must NOT set tier1_diag (which would disable the polyene mis-anchor
        # guard below). Demote PYE to uncorroborated in that case so the guard runs and the rationale
        # reports it. Mirrors the "fires only on its own biosynthetic diagnostic" contract of T43-AMC/BLA.
        _pye = [t for t in corrob_triggers if "T43-PYE" in str(t)]
        if _pye:
            _ks = (mis_per_bgc.get(bgc.bgc_id, {}) or {}).get("ks_domain_count", 0) or 0
            if _ks < 4:
                _uncorr |= set(_pye)
                corrob_triggers = [t for t in triggers if t not in _uncorr]
                trig_str = " ".join(str(t) for t in corrob_triggers)
        # v1.9.99 triple-count clamp: if T43-PYE is corroborated (survived the KS-gate) AND a polyene
        # chemotype AF credit was already applied above, subsume the chemotype credit — the diagnostic
        # bonus replaces it rather than stacking. Mirrors architecture-subclass-subsumes-parent.
        _pye_corrob = any("T43-PYE" in str(t) for t in corrob_triggers)
        if _pye_corrob and _polyene_chemotype_af > 0:
            base_af -= _polyene_chemotype_af
        af_diag = any(t in trig_str for t in AF_DIAGNOSTIC_TRIGGERS)
        ab_diag = any(t in trig_str for t in AB_DIAGNOSTIC_TRIGGERS)
        if af_diag: base_af += DIAGNOSTIC_BONUS
        if ab_diag: base_ab += DIAGNOSTIC_BONUS
        rt = rt_per_bgc.get(bgc.bgc_id, {})
        rt_tier = (rt.get("tier") if isinstance(rt, dict) else rt) or ""
        # v9.7.37 PC-12: domain/context-evidence corroboration on the RESISTANCE axis -- the #28 principle
        # (trust domain/context evidence over the bare label/tier on a mobile background) applied one axis over.
        # A T1 self-protection tier on a MOBILE-DOMINANT region is genuine self-resistance only if the resistance
        # is class-concordant with the cluster's own product. A non-concordant resistance group on an ICE/
        # transposon background is horizontally-acquired CARGO, not self-protection, so it must NOT establish a
        # tier-1 diagnostic -- which was independently suppressing the #28 mobile-element demotion on the
        # resistance path, leaving an ICE impostor a Medium lead even after #28 fixed the class path. Conservative:
        # fires only on mobile_dominant AND T1 AND no class-concordant group; a genuine self-resistant cluster
        # (concordant group present, e.g. VanHAX in a glycopeptide) keeps tier-1 status, and non-mobile regions
        # are untouched. Verified: NZ_CP029601.1 BGC032 (APH_AAC, class_concordant_groups=[], mobile-dominant ICE).
        t1_self_protection = str(rt_tier).startswith("T1")
        if (t1_self_protection and isinstance(rt, dict) and rt.get("mobile_dominant")
                and not rt.get("class_concordant_groups")):
            t1_self_protection = False
        tier1_diag = bool(corrob_triggers) or t1_self_protection
        # v9.7.7 P0 guard: suppress AB/AF keyword credit for primary-metabolism / pigment regions.
        # Fires only when (a) a housekeeping/pigment core-gene marker is in the BGC's OWN CDS, (b) the
        # BGC's OWN product class is exclusively weak/over-call labels (no committed biosynthetic class),
        # and (c) no Tier-1 diagnostic fires. This de-ranks the SID-XXX topoisomerase "NRPS-like" #1-AB
        # false positive and the carotenoid-"terpene"-as-antifungal false positive without touching real
        # clusters (a committed class label or a CCTT diagnostic exempts the region).
        pm = pm_per_bgc.get(bgc.bgc_id, {})
        pm_families = set(pm.get("families", [])) if isinstance(pm, dict) else set()
        own_classes = {t.strip() for t in re.split(r"[;,/|]+|\s+", " ".join(bgc.products).lower()) if t.strip()}
        primary_flag = bool(pm_families) and bool(own_classes) and own_classes <= WEAK_OVERCALL_CLASSES and not tier1_diag
        if primary_flag:
            base_ab = min(base_ab, 25.0)   # strip keyword credit to the floor on both bioactivity axes
            base_af = min(base_af, 20.0)
        # v9.7.33 #28 mobile-element/ICE demotion: a region DOMINATED by mobility machinery (ICE/transposon),
        # mis-typed by antiSMASH as a biosynthetic class, is not a biosynthesis lead. Demote AB/AF when the
        # source-derived HGT guard reports mobile-dominant AND no real class evidence corroborates the region
        # (no corroborated CCTT trigger, no T1 self-resistance). A corroborated class signal exempts it
        # (CCTT-veto discipline), so genuine clusters with incidental flanking mobile genes are untouched.
        mobile_dominant = bool(rt.get("mobile_dominant")) if isinstance(rt, dict) else False
        mobile_families = sorted(rt.get("mobile_families", [])) if isinstance(rt, dict) else []
        mobile_flag = mobile_dominant and not tier1_diag
        if mobile_flag:
            base_ab = min(base_ab, 25.0)
            base_af = min(base_af, 20.0)
        # v9.7.15 gene-filter mis-anchor guards: a KCB product-name anchor lacking its committed class
        # diagnostic is spurious for this locus. Suppress the anchor-derived axis credit (claim-safe;
        # exempt when a Tier-1 diagnostic independently fires, mirroring the primary-metab guard).
        mis = mis_per_bgc.get(bgc.bgc_id, {}) if isinstance(mis_per_bgc, dict) else {}
        misanchor_parts = []
        # MISANCHOR-01 (v9.7.337): the exemption used to be the GLOBAL `not tier1_diag`, i.e. ANY
        # Tier-1 diagnostic erased BOTH clamps. That is class-blind, and it inflates the axis the
        # anchor was wrong about. Reproduced on the project's own fixture: a `RiPP-like` locus with
        # a `natamycin` polyene anchor and ZERO PKS KS domains scored AF 20.0 / Inventory with the
        # flag `polyene_anchor_<4_PKS_KS(ks=0)`; adding the UNRELATED nucleoside trigger
        # `T43-NUC_nucleoside` moved it to AF 45.0 / Medium with the flag erased. A nucleoside
        # diagnostic supports nucleoside capacity; it says nothing about whether a polyene backbone
        # exists, and the locus still has no KS domains. Rescue is now class-specific: only the
        # diagnostic that speaks to THAT anchor's committed machinery can lift THAT clamp.
        # Unrelated Tier-1 evidence keeps its own positive credit (the DIAGNOSTIC_BONUS above is
        # untouched) — it simply no longer launders a comparator the locus cannot support.
        # The guards are themselves the machinery test: scan_misanchor_guards emits
        # `polyene_misanchor` only when the locus carries < 4 PKS KS domains, and
        # `aminoglycoside_misanchor` only when the committed DOIS/aminocyclitol evidence is absent.
        # So if the class-specific machinery existed the flag would never have been emitted, and no
        # trigger — related or not — should be able to lift it. Applying them unconditionally is
        # both simpler and stricter than a trigger-keyed rescue.
        if isinstance(mis, dict):
            if mis.get("aminoglycoside_misanchor"):
                base_ab = min(base_ab, 25.0)
                misanchor_parts.append("aminoglycoside_anchor_no_DOIS")
            if mis.get("polyene_misanchor"):
                # H4/v9.7.352 (PI ruling, the Developer or User 2026-08-05): "Don't demote nucleosides. They are
                # antifungals. Any nucleoside machinery should be noted and brought to the user's
                # attention." A stray polyene KCB anchor on a locus that carries its OWN corroborated,
                # non-polyene AF diagnostic (T43-NUC nucleoside chitin-synthase inhibitor; T43-PTM
                # HSAF/PTM macrolactam) must NOT clamp that independent AF credit. This narrows
                # MISANCHOR-01: the polyene-comparator credit is still stripped when the polyene
                # anchor is the SOLE AF evidence, but a corroborated nucleoside/AF diagnostic keeps
                # its credit and the machinery is SURFACED in the rationale instead of silently sunk.
                _indep_af_diag = any(t in trig_str for t in (AF_DIAGNOSTIC_TRIGGERS - {"T43-PYE"}))
                if _indep_af_diag:
                    _nuc = "T43-NUC" in trig_str
                    misanchor_parts.append(
                        ("nucleoside_AF_machinery_present" if _nuc else "independent_AF_diagnostic_present")
                        + f":polyene_anchor_not_clamped(ks={mis.get('ks_domain_count', 0)})")
                else:
                    base_af = min(base_af, 20.0)
                    misanchor_parts.append(f"polyene_anchor_<{4}_PKS_KS(ks={mis.get('ks_domain_count', 0)})")
        # §4.3 enediyne guard (independent of tier1_diag): a PREV-001/hglE artifact must not keep the +18
        # enediyne novelty credit; a genuine enediyne carries an [E-signal] claim-safety note (no lab-safety/BSL-2 warning is emitted — selective biosafety flags give false reassurance; chemical handling is governed by lab SOPs).
        esignal_note = ""
        if isinstance(mis, dict):
            if mis.get("enediyne_misanchor"):
                novelty -= NOVELTY_KEYWORDS.get("enediyne", 0)   # strip the spurious enediyne novelty
                _ev = mis.get("enediyne_verdict", "")
                misanchor_parts.append("enediyne_anchor_no_ene_KS(similarity_only)" if _ev == "ENEDIYNE_MISANCHOR"
                                       else "enediyne_anchor_is_PREV-001_hglE_artifact")
            elif mis.get("esignal_enediyne"):
                esignal_note = "; [E-signal] named-enediyne KCB anchor (similarity, structure NOT confirmed) — treat as enediyne candidate"
        # v9.7.63: class-level KCB mismatch flag — compound family incompatible with own product class.
        # Fires independently of tier1_diag (same rationale as enediyne guard: if the anchor is wrong,
        # we flag it regardless of whether a diagnostic independently rescues the AB/AF credit).
        if isinstance(mis, dict) and mis.get("class_mismatch"):
            misanchor_parts.append(f"class_mismatch({mis.get('class_mismatch_reason', 'KCB compound class incompatible with own products')[:60]})")
        misanchor_flag = "; ".join(misanchor_parts)
        # An explicit UNKNOWN_KCB state wins over a contradictory stale score:
        # absence is not comparator evidence in either novelty direction.
        _kcb_observed = getattr(bgc, "kcb_evidence_state", "UNKNOWN_KCB") != "UNKNOWN_KCB"
        if _kcb_observed and bgc.kcb_cumulative is not None and bgc.kcb_cumulative > 10000:
            novelty -= 15
        # v9.7.402 (audit W402-23): missing KCB evidence used to add +5 novelty here — the same
        # direction as an OBSERVED low-similarity comparator (the riq_score branch below). UNKNOWN
        # is not evidence of novelty; unavailable/degraded KCB parsing (a parser-degraded run, an
        # antiSMASH JSON that failed to parse, bounded-mode truncation) must not be able to earn
        # novelty credit it did not observe. Removed the credit entirely rather than substituting a
        # different value — a missing input moves nothing, in either direction. KCB=None is already
        # visible in the rendered rationale (render_rationale's `KCB={bgc.kcb_cumulative}`), so this
        # is a pure credit removal, not a loss of transparency.
        if bgc.riq_score is not None and bgc.riq_score < 0.5:
            novelty += 10
        penalty = edge_penalty(bgc.edge_status)
        support = rg_support.get(bgc.bgc_id, [])
        # AUDIT_374 (rggmci_rescue_bonus_accessory_only_unguarded): a rescue bonus needs BOTH
        # RG-GMCI homology geometry (proof 1, already gated by rggmci_confidence) AND biosynthetic-logic
        # complementarity (proof 2). clusterblast_genes.py::rescue_functional_complementarity() computes
        # exactly that second proof as functional_rescue_class, and its own docstring calls ACCESSORY_ONLY
        # "weak rescue" (both fragments are tailoring-only, not a core+accessory split) -- an affirmative
        # refutation of proof 2, the same status OVERLAPPING_PARALOG already has for the subject-tiling
        # channel (see rggmci.py:1086-1105, "the exact single-proof rescue the two-proof rule exists to
        # block"). A pair missing the field entirely (older fixtures / profiling unavailable) still counts
        # -- absence of a profile is not a refutation, so this stays backward compatible.
        def _rescue_eligible(p):
            return (p.get("functional_rescue_class") or "").strip() != "ACCESSORY_ONLY"
        high_rg = any(p.get("rggmci_confidence") == "HIGH_RG_GMCI_RESCUE" and _rescue_eligible(p) for p in support)
        mod_rg = any(p.get("rggmci_confidence") == "MODERATE_RG_GMCI_CANDIDATE" and _rescue_eligible(p) for p in support)
        # BC2-407: extend the primary_flag exemption to mobile_flag -- a mobile-dominant, uncorroborated
        # region (ICE/transposon mis-typed as biosynthetic, v9.7.33 #28) is exactly as much "not a
        # genuine biosynthetic fragment to rescue" as a primary-metabolism/pigment false positive already
        # is. Before this fix, rescue_bonus ignored mobile_flag entirely, so a HIGH_RG_GMCI_RESCUE pairing
        # could add back +8 AB/AF/novelty on top of the mobile guard's own ab<=25/af<=20 floor -- directly
        # contradicting the guard's own rationale text ("AB/AF credit suppressed") the moment rescue
        # applied. Reproduced live: a mobile_dominant/uncorroborated fixture scored ab=25/af=20 without
        # rescue, ab=33/af=28 WITH a HIGH_RG_GMCI_RESCUE(COMPLEMENTARY) pairing -- the floor visibly
        # breached by the same mechanism primary_flag was already protected against.
        rescue_bonus = 0 if (primary_flag or mobile_flag) else (8 if high_rg else 4 if mod_rg else 0)  # flagged primary/pigment/mobile regions are not biosynthetic fragments to rescue
        # Reduce, but do not erase, the fragmentation penalty when RG-GMCI
        # supplies independent split-pathway evidence. Claim confidence remains
        # governed by architecture and judgment-layer evidence.
        #
        # NOTE (v9.1 two-level rule): Interior BGCs that are split-pathway
        # anchors get edge_penalty=0 here (Interior → 0 in edge_penalty).
        # The fragmentation penalty only applies to Edge/FC fragments.
        # The judgment layer (slim kernel Module 3) enforces the two-level
        # rule: anchor retains standalone Arch grade; only the pathway unit
        # label is Arch C. This code is consistent with that rule.
        effective_penalty = max(0, penalty - (8 if high_rg else 4 if mod_rg else 0))
        ab = max(0, min(100, base_ab + rescue_bonus - effective_penalty * 0.35))
        af = max(0, min(100, base_af + rescue_bonus - effective_penalty * 0.35))
        nov = max(0, min(100, novelty + rescue_bonus - effective_penalty * 0.2))
        best = max(ab, af, nov)
        tier = "Exceptional" if best >= 85 else "High" if best >= 70 else "Medium" if best >= 50 else bottom_tier(bgc)
        # TIER_1 diagnostic floor: a definitive CLASS marker (CCTT T43 / T1 self-protection) can't be buried by a
        # low text/KCB score — float it to at least Medium so KCB-dark, gene-only leads still reach lead tier.
        # v9.7.19: a lone tailoring-enzyme marker (halogenase / fluorinase-chlorinase) is NOT a class call and
        # does not floor on its own; a class-defining marker that co-occurs still does.
        floored = False
        floor_triggers = [t for t in corrob_triggers if not str(t).startswith(TIER1_FLOOR_EXCLUDED_PREFIXES)]
        # v9.7.37 PC-12: the tier-floor consumes the SAME cargo-aware T1 signal as tier1_diag, so an ICE-cargo
        # resistance on a mobile-dominant region no longer floats an impostor to Medium (t1_self_protection is
        # already False for that case). floor_triggers is corroborated-only, so #28 already keeps it empty here.
        tier1_floor = bool(floor_triggers) or t1_self_protection
        if tier1_floor and tier in ("Inventory", "Low"):
            tier = "Medium"; floored = True
        # v1.9.111 glycopeptide machinery floor (the Developer or User-requested): when the architecture call is
        # glycopeptide with HIGH confidence, the class is machinery-confirmed by construction --
        # the glycopeptide pre-check requires >=6 NRPS-C domains + a halogenase + a
        # glycosyltransferase, i.e. the crosslinking/tailoring machinery is present (>=4 genes
        # incl. the P450/Oxy crosslinker). A confirmed glycopeptide should not sit below High just
        # because an overmerged region diluted its text/KCB capacity base. Floor to High.
        # Claim-safe: this is CAPACITY (machinery consistent with glycopeptide production), not a
        # production claim; it never raises above High and never overrides a standing-rule/RiPP
        # downgrade below.
        glyco_machinery_floored = False
        _arch_cap = (getattr(bgc, "architecture_capacity", "") or "").lower()
        _arch_conf = str(getattr(bgc, "architecture_class_confidence", "")).upper()
        if _arch_cap == "glycopeptide" and _arch_conf == "HIGH" and tier in ("Medium", "Inventory", "Low"):
            tier = "High"; glyco_machinery_floored = True; floored = True
        # v9.7.8 permanent-exclusion downgrade: saccharide / NAPAA / hglE-KS-PREV-001 cap the lead tier
        # (raw scores preserved). For hglE-KS the structural novelty still stands — only the drug-lead claim
        # is downgraded, so nov/AB/AF are intentionally left untouched here.
        standing_rule = standing_rule_for(" ".join(bgc.products).lower(), txt)
        # RG-01 (2026-07-28): the former NAPAA fallback branch is DELETED. The registry
        # (rules_registry.json, the SSOT) declares NAPAA status="neutral"/action="none" — its
        # lead-blocking was RETIRED 2026-06-14 — so NAPAA must NOT floor an own-product BGC to
        # Inventory. It is now driven only through standing_rule_for (which returns "" for NAPAA).
        # hglE-KS remains registry-flagged non-blocking (action=flag) but is still detected directly
        # from product annotations for traceability, so its downgrade branch is kept below.
        _prods_lower = {p.lower() for p in bgc.products}
        if not standing_rule:
            if "hgle-ks" in _prods_lower or any("hgle" in p for p in _prods_lower):
                # v9.7.61 CCTT co-occurrence exemption: if any CCTT class trigger fired on this
                # BGC, the biosynthetic content extends beyond the generic hglE-KS glycolipid
                # machinery — suppress the standing-rule downgrade and let the CCTT-driven tier
                # logic govern. AS-XXX tambjamine/T43-NN is the canonical case.
                _cctt_present = bool(triggers)  # `triggers` set above from cctt_per_bgc
                if not _cctt_present:
                    standing_rule = "hglE-KS-PREV-001"
        if standing_rule:
            # saccharide/hglE-KS standing-rule -> housekeeping -> Inventory (unchanged);
            # any non-housekeeping standing-rule target -> Low (class-gated bottom, AQUARIUS_01).
            tier = bottom_tier(bgc); floored = False
        # F2 — RiPP completeness floor: a RiPP-family product on a truncated, sub-8kb region has no
        # precursor/core captured and can't be evaluated as a product. Cap at Inventory so a lone
        # modifying enzyme + KCB can't float a fragment above a complete cluster. Never touches Interior.
        ripp_floored = False
        _prods = {p.lower() for p in bgc.products}
        _is_ripp = bool(_prods & RIPP_FAMILY_CLASSES) or any(
            any(rf in p for rf in RIPP_FAMILY_CLASSES) for p in _prods)
        _end = getattr(bgc, "end", 0) or 0
        _start = getattr(bgc, "start", 0) or 0
        _clen = getattr(bgc, "contig_length", 0) or 0
        _span_kb = abs(_end - _start) / 1000.0 if _end else _clen / 1000.0
        if (_is_ripp and getattr(bgc, "edge_status", "") in ("Edge", "Full-contig")
                and 0 < _span_kb < RIPP_FRAGMENT_MAX_KB and tier in ("Exceptional", "High", "Medium")):
            tier = bottom_tier(bgc); ripp_floored = True   # RiPP-family -> 'Low' (specialized), not 'Inventory'
        conf = {"A": "High", "B": "Moderate-High", "C": "Moderate", "D": "Low-Moderate", "E": "Low"}.get(bgc.architecture_confidence, "Unknown")
        # AUDIT_377 (rg_note_ineligible_pair_misattribution): `support` holds every
        # HIGH/MODERATE-confidence pair for this BGC, but NOT every pair is rescue-ELIGIBLE --
        # the two-proof gate (_rescue_eligible, same test the rescue_bonus/effective_penalty
        # computation above already uses) can refute a pair's biosynthetic-logic proof
        # (functional_rescue_class == ACCESSORY_ONLY) while a different pair in the same list
        # IS eligible, or while NO pair in the list is eligible. The prior code took
        # `support[0]` unconditionally, so the rationale could assert "RG-GMCI=HIGH_RG_GMCI_RESCUE"
        # for a BGC that received ZERO rescue bonus (sole pair ineligible), or attribute the
        # rescue to the wrong, ineligible pair while a different eligible pair actually granted
        # it. Select the SAME pair the bonus computation would credit: the first eligible HIGH
        # pair, else the first eligible MODERATE pair; omit the note entirely when neither
        # exists (no rescue was actually granted, so no rescue should be claimed).
        def _first_eligible_pair(conf_label):
            return next((p for p in support if p.get("rggmci_confidence") == conf_label and _rescue_eligible(p)), None)
        _rg_pair = _first_eligible_pair("HIGH_RG_GMCI_RESCUE") or _first_eligible_pair("MODERATE_RG_GMCI_CANDIDATE")
        rg_note = ""
        if _rg_pair:
            rg_note = f"; RG-GMCI={_rg_pair.get('rggmci_confidence')} via {_rg_pair.get('pair')}"
        _rat = render_rationale(bgc, rg_note=rg_note, floored=floored, floor_triggers=floor_triggers, ripp_floored=ripp_floored, af_diag=af_diag, corrob_triggers=corrob_triggers, _uncorr=_uncorr, triggers=triggers, primary_flag=primary_flag, pm_families=pm_families, standing_rule=standing_rule, misanchor_flag=misanchor_flag, esignal_note=esignal_note, mobile_flag=mobile_flag, mobile_families=mobile_families)
        _conc = ((scans.concordance_per_bgc or {}).get(bgc.bgc_id, {}) or {}) if scans and getattr(scans, "concordance_per_bgc", None) else {}
        _conc_verdict = _conc.get("verdict", "") or ""
        # v9.7.62 UMED gap flag: MATURATION_GAP when a RiPP/nucleoside BGC has no nearby maturation genes.
        # Sourced from scans.umed["per_bgc"][bgc_id]["verdict"]; "" when not applicable or scan absent.
        _umed_per_bgc = {}
        if scans and getattr(scans, "umed", None):
            _umed_per_bgc = (scans.umed.get("per_bgc") or {})
        _umed_verdict = (_umed_per_bgc.get(bgc.bgc_id) or {}).get("verdict", "") or ""
        _umed_gap = "MATURATION_GAP" if _umed_verdict == "MATURATION_GAP_SOURCE_DERIVED" else ""
        _amr_res = _amr.recall_scores(
            round(ab, 1), round(af, 1),
            closest_mibig_accession=getattr(bgc, "closest_mibig_accession", "") or "",
            closest_kcb_product=getattr(bgc, "closest_candidate_kcb_product", "") or "",
            misanchor_flag=misanchor_flag,
            concordance_verdict=_conc_verdict,
        )
        records.append(TriageRecord(bgc.bgc_id, round(ab,1), round(af,1), round(nov,1), tier, conf, _rat, primary_metabolism_flag=primary_flag, standing_rule_flag=standing_rule, misanchor_flag=(misanchor_flag + (" | E-signal" if esignal_note else "")), mobile_element_flag=(",".join(mobile_families) if mobile_flag else ""), contig=getattr(bgc, "contig", ""), user_label=getattr(bgc, "user_label", ""), architecture_capacity=getattr(bgc, "architecture_capacity", ""), architecture_class_confidence=getattr(bgc, "architecture_class_confidence", ""), concordance_verdict=_conc_verdict, umed_gap_flag=_umed_gap, ab_recall=_amr_res["ab_recall"], af_recall=_amr_res["af_recall"], recall_family=_amr_res["anchor_family"]))
    records = sorted(records, key=lambda r: max(r.ab_score, r.af_score, r.novelty_score), reverse=True)
    # corrected_rank: sequential lead rank over rows NOT downgraded by a standing rule and NOT flagged
    # primary-metabolism/pigment. Downgraded rows keep their raw scores but get corrected_rank=None.
    rank = 0
    for r in records:
        if not r.standing_rule_flag and not r.primary_metabolism_flag and not r.mobile_element_flag:
            rank += 1
            r.corrected_rank = rank
    return records

def bgc_count_summary(bgcs: list[BGCRecord]) -> dict:
    c = Counter(b.edge_status for b in bgcs)
    raw = len(bgcs)
    interior, edge, fc = c.get("Interior", 0), c.get("Edge", 0), c.get("Full-contig", 0)
    interior_pct = round((interior / raw) * 100.0, 1) if raw else None
    return {"raw": raw, "interior": interior, "edge": edge, "full_contig": fc, "corrected": corrected_bgc_count(interior, edge, fc), "interior_pct": interior_pct, "assembly_tier": assembly_tier(interior_pct)}

def needs_multibatch(bgcs: list[BGCRecord], rescue_triggered: bool = False) -> tuple[bool, str]:
    counts = bgc_count_summary(bgcs)
    edge_fc = counts["edge"] + counts["full_contig"]
    if counts["raw"] > 25:
        return True, "raw BGC count > 25"
    if edge_fc > 15:
        return True, "edge/full-contig BGC count > 15"
    if rescue_triggered:
        return True, "fragmented-cluster rescue review triggered"
    return False, ""  # M-A1 fix: was implicitly returning None on common path


# ── v9.7.20 absolute-default completeness invariant ──────────────────────────────────────────────────
# Every BGC is assessed on ab / af / novelty — NOT just the lead-tier ones. The engine scores all BGCs by
# construction (triage_bgcs loops the full BGC list, Edge / Full-contig / small-contig fragments included —
# none are skipped). This invariant exists to catch DOWNSTREAM loss: a merge or workbook build that carries
# scores for leads only, as the BeeCohort cohort merge did (~9% of BGCs scored). It is meant to be run on the
# produced triage/workbook so a user is always confronted with incomplete coverage rather than shipping it
# silently. Opting out is a deliberate source edit, not a default.
def scoring_coverage(bgcs, triage):
    """Return (covered, total, unscored_bgc_ids). Full coverage == every BGC has ab/af/novelty populated."""
    by_id = {t.bgc_id: t for t in triage}
    unscored = []
    for b in bgcs:
        bid = getattr(b, "bgc_id", None)
        t = by_id.get(bid)
        if t is None or t.ab_score is None or t.af_score is None or t.novelty_score is None:
            unscored.append(bid)
    total = len(bgcs)
    return total - len(unscored), total, unscored


def assert_full_scoring_coverage(bgcs, triage, *, strain: str = "", raise_on_fail: bool = True):
    """Default-on guard: FAIL loudly when any BGC lacks an ab/af/novelty assessment.

    raise_on_fail=True -> raises ValueError (use in CI / package QA). False -> returns the warning string
    (use where a caller wants to surface, not abort). Returns '' on full coverage.
    """
    covered, total, unscored = scoring_coverage(bgcs, triage)
    if not unscored:
        return ""
    pct = (100 * covered // total) if total else 0
    msg = (f"SCORING-COVERAGE FAIL{(' [' + strain + ']') if strain else ''}: {covered}/{total} BGCs scored "
           f"({pct}%). Every BGC must be assessed for ab/af/novelty (absolute default), not leads only. "
           f"Unscored: {', '.join(map(str, unscored[:20]))}{' …' if len(unscored) > 20 else ''}")
    if raise_on_fail:
        raise ValueError(msg)
    return msg

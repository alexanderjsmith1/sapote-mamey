"""Class-aware Diagnostic Rescue layer (v9.7.24).

Promotes split-pathway reconstructions that RG-GMCI's *generic* geometry gate demotes, when the
pairing is backed by **class-definitive diagnostic evidence** plus **complementary reference tiling**.

Motivating case (a Bombus-associated Streptomyces, internal): BGC013/NODE_182 (T43-IDC indolocarbazole
core) + BGC001/NODE_105
(halogenase/saccharide arm) tile complementarily onto NZ_KB913036 (8 reference genes, 0 overlap).
RG-GMCI demotes this to LOW_SHARED_REFERENCE_SIGNAL because the two arms sit on separate contigs
with no adjacency geometry — but two-arms-on-two-contigs is exactly the EXPECTED topology of a
diagnostic split in a fragmented assembly. This layer recognises that and rescues it.

CLAIM CEILING (enforced on every lead): a clusterblast-scaffolded reconstruction *hypothesis* —
a homology-guided split-pathway linkage. NOT a nucleotide-level contig join and NOT a product-identity
claim. Physical linkage requires long-read resequencing or PCR across the contig boundary.

NOTE (SSOT): `parse_cb` and the reference-gene tiling below are a faithful port of the primitives in
`tools/build_reconstruction.py`. They are duplicated here so the *engine* has no dependency on the
tools/ tree. Consolidating both onto one shared primitive is a tracked follow-up (do not let them drift).
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

import glob
import os
import re
from typing import Any, Callable, Optional

# --- class roles -------------------------------------------------------------------------------
# CORE = class-definitive backbone trigger (the molecule's identity-bearing core).
# v9.7.374 fix: this tuple was frozen at its v9.7.24 vintage and never updated when source_scans.py
# added three more class-defining CCTT triggers at v9.7.119 (T43-GPA_glycopeptide,
# T43-PYE_polyene_macrolide, T43-BLT_betalactone -- see source_scans.py CCTT_PATTERNS/CCTT_CLASS_COMPAT,
# each carrying a real committed-marker regex and a CCTT_CLASS_COMPAT entry exactly like every other
# CORE trigger below). Because `roles()` does substring matching against the joined CCTT-trigger
# string, a BGC whose only class-defining trigger was one of these three could never be recognised as
# carrying a `core` role, so `assess_pair()` silently returned None for it (not a rescue candidate)
# instead of being evaluated for a genuine glycopeptide/polyene-macrolide/betalactone split-pathway
# rescue -- a coverage gap, not a crash, matching the vocabulary-drift bug class already fixed once
# this session in good_guesses.py's _REFERENCE_DARK_CLASSES.
CORE_TRIGGERS = (
    "T43-IDC", "T43-PTM", "T43-NUC", "T43-BLA", "T43-AMC", "T43-NN",
    "T43-ENE", "T43-LAN", "T43-LASSO", "T43-THA", "T43-DKP", "T43-TET", "T43-PHO",
    "T43-GPA", "T43-PYE", "T43-BLT",
)
# ARM = complementary tailoring trigger (halogenation) recognised as a partner arm.
ARM_TRIGGERS = ("T43-HAL", "T43-XHAL")
# ARM products = tailoring evidence carried as antiSMASH product labels (saccharide/glycosylation/halogenation).
ARM_PRODUCT_TOKENS = ("saccharide", "glycosyl", "halogenated")

CLAIM_CEILING = (
    "Clusterblast-scaffolded reconstruction hypothesis: a homology-guided split-pathway linkage, "
    "NOT a nucleotide-level contig join and NOT a product-identity claim. Confirm physical linkage "
    "by long-read resequencing or PCR across the contig boundary."
)

# precision floors for HIGH-confidence promotion
COVERED_FLOOR = 8       # total reference genes the two arms must tile (BGC013+BGC001 = 8)
PER_ARM_FLOOR = 2       # each arm must contribute >= this many genes to the shared scaffold
# only TRUNCATED clusters can be halves of a split pathway. A complete (Interior) cluster is whole,
# so a pair with an Interior member is co-occurrence, not a split — excluded from rescue entirely.
# (Validated on public GOOD-assembly genomes, where Interior+Interior pairs flooded false HIGH leads.)
TRUNCATED_EDGE = {"Edge", "Full-contig"}

# --- KCB-class concordance (precision gate; see adjudication 2026-06-15) -------------------------
# A true split tiles two halves of ONE compound class, so a HIGH rescue requires the core and arm to
# KCB to compatible biosynthetic families. The map is curated (the MIBiG index subclasses are too
# coarse — AT2433 and loonamycin both read 'other'). Without a family on a side, concordance is
# 'indeterminate' (evaluated but family-less, not a data gap) and the lead is capped at MODERATE.
import json as _json  # noqa: E402

_FAMILY_MAP_PATH = os.path.join(os.path.dirname(__file__), "data", "families", "kcb_compound_family.json")


def load_family_map(path: str | None = None) -> dict:
    """Load the curated KCB-accession -> biosynthetic-family map (+ compatible_pairs).

    Returns {} with a ``_skipped`` key when the map is absent or corrupt, so
    callers can distinguish 'concordance SKIPPED' from 'concordance evaluated
    with an empty map'.  Prints a warning — fail-loud, not fail-silent.
    """
    p = path or _FAMILY_MAP_PATH
    try:
        with open(p, encoding="utf-8") as fh:
            return _json.load(fh)
    except Exception as exc:
        import sys
        emit(
            f"WARNING: family map unavailable ({p}): {exc}. "
            "KCB-class concordance gate is SKIPPED for this session.",
            file=sys.stderr,
        )
        return {"_skipped": True}


def kcb_family(kcb: Any, fmap: dict) -> Optional[str]:
    """Resolve a KCB anchor string to a biosynthetic family via its MIBiG accession."""
    m = re.search(r"(BGC\d{7})", str(kcb or ""))
    if not m:
        return None
    return (fmap.get("by_accession") or {}).get(m.group(1))


def _concordance(cf: Optional[str], af: Optional[str], fmap: dict) -> str:
    if cf is None or af is None:
        return "indeterminate"  # evaluated, but a side lacks a KCB family — not missing data
    if cf == af:
        return "concordant"
    compat = {tuple(sorted(p)) for p in (fmap.get("compatible_pairs") or [])}
    return "concordant" if tuple(sorted((cf, af))) in compat else "discordant"

# tier ordering for sorting (higher = stronger)
_TIER_RANK = {
    "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE": 3,
    "DIAGNOSTIC_RESCUE_MODERATE": 2,
    "DIAGNOSTIC_RESCUE_LOW": 1,
}


def _as_list(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, (list, tuple, set)):
        return [str(i) for i in x]
    return [str(x)]


def roles(cctt: Any, products: Any) -> dict[str, Any]:
    """Return roles for one BGC.

    cores: class-definitive triggers present.
    arms: complementary tailoring roles present ('halogenase' / 'saccharide').
    hal_trigger: True if a HAL/XHAL CCTT trigger is present (the *diagnostic* tailoring signal).
    saccharide_only: True if the only arm signal is a saccharide product (glycosylation noise per the
        permanent-exclusion standing rule — not sufficient on its own to drive a HIGH rescue).
    """
    cctt_s = " ".join(_as_list(cctt))
    prod_s = " ".join(_as_list(products)).lower()
    cores = [t for t in CORE_TRIGGERS if t in cctt_s]
    hal_trigger = any(t in cctt_s for t in ARM_TRIGGERS)
    arms: list[str] = []
    if hal_trigger or "halogenated" in prod_s:
        arms.append("halogenase")
    if "saccharide" in prod_s or "glycosyl" in prod_s:
        arms.append("saccharide")
    arms = sorted(set(arms))
    saccharide_only = arms == ["saccharide"]
    return {"cores": cores, "arms": arms, "hal_trigger": hal_trigger,
            "saccharide_only": saccharide_only}


# --- clusterblast tiling primitive (ported from tools/build_reconstruction.py; keep in sync) -----
def parse_cb(path: str) -> dict[str, dict[str, Any]]:
    """Parse one clusterblast region txt -> {accession: {source, type, cum_score, hits:[{query,subject,...}]}}."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    refs: dict[str, dict[str, Any]] = {}
    for block in txt.split(">>")[1:]:
        acc = re.search(r"\n\s*\d+\.\s+(\S+)", block)
        if not acc:
            continue
        acc = acc.group(1)
        src = re.search(r"Source:\s*(.+)", block)
        typ = re.search(r"Type:\s*(.+)", block)
        cum = re.search(r"Cumulative BLAST score:\s*([\d.]+)", block)
        hits = []
        tb = block.split("Table of Blast hits")
        if len(tb) > 1:
            for line in tb[1].splitlines():
                p = line.split("	")
                q0 = p[0].strip()
                if len(p) >= 4 and q0 and re.match(r"^[A-Za-z][\w.]*_?\d", q0):
                    try:
                        blast_score = int(p[3])
                    except (ValueError, IndexError):
                        blast_score = 0
                    hits.append({
                        "query": q0,
                        "subject": p[1].strip(),
                        "blast_score": blast_score,
                    })
        refs[acc] = {"source": (src.group(1).strip() if src else ""),
                     "type": (typ.group(1).strip() if typ else ""),
                     "cum_score": float(cum.group(1)) if cum else 0.0, "hits": hits}
    return refs


def _cb_for_node(cb_dir: str, node_prefix: str) -> dict[str, dict[str, Any]]:
    if not (cb_dir and node_prefix):
        return {}
    files = glob.glob(os.path.join(cb_dir, "%s_*.txt" % node_prefix))
    return parse_cb(files[0]) if files else {}


# v9.7.81 P2: unify locus-proxy with rggmci._locus_key (namespace-aware prefix+number split)
# The old _locus_num extracted only the last digit run, which could collide across
# prefix namespaces (AMK09_RS30055 vs B082_RS0106330 both yield a bare integer).
# Import rggmci's namespace-aware implementation to share the SSOT.
try:
    from .rggmci import _locus_key as _rggmci_locus_key
    _HAVE_RGGMCI_LOCUS_KEY = True
except ImportError:
    _HAVE_RGGMCI_LOCUS_KEY = False


def _locus_num(name: str) -> int | None:
    # v9.7.81: use rggmci._locus_key when available for cross-module SSOT.
    # Falls back to the old last-digit-run approach if rggmci is unavailable.
    s = re.sub(r"\.\d+$", "", name or "")
    if _HAVE_RGGMCI_LOCUS_KEY:
        _pre, num = _rggmci_locus_key(s)
        return num  # may be None
    m = re.findall(r"(\d+)", s)
    return int(m[-1]) if m else None


# Adjacency thresholds (locus-number proxy for genomic position). A genuine split tiles two
# NEAR-BY loci of one reference cluster; complementary-but-DISTANT loci are two clusters that merely
# share a genome (the RG-GMCI false-grouping). Tune via cross-strain retest.
ADJ_MAX_LOCUS_GAP = 60
ADJ_MAX_SPAN = 400


def _adjacent(sa: set, sb: set) -> tuple[bool, int | None, int | None]:
    na = {n for n in (_locus_num(s) for s in sa) if n is not None}
    nb = {n for n in (_locus_num(s) for s in sb) if n is not None}
    if not na or not nb:
        return True, None, None  # no locus numbers -> cannot judge; stay permissive, don't block
    gap = min(abs(a - b) for a in na for b in nb)
    span = max(na | nb) - min(na | nb)
    return (gap <= ADJ_MAX_LOCUS_GAP and span <= ADJ_MAX_SPAN), gap, span


def tile_pair(cb_a: dict, cb_b: dict) -> dict[str, Any]:
    """Complementary-tiling verdict over the best shared reference between two fragments' clusterblast.

    COMPLEMENTARY requires both (1) low reference-gene overlap (<=0.15) AND (2) ADJACENT subject loci
    (near each other in the reference). Complementary-but-distant loci are two clusters sharing a
    genome, not a split — they get RECONSTRUCTION_NOT_SUPPORTED_DISTANT_LOCI.
    """
    shared = set(cb_a) & set(cb_b)
    if not shared:
        return {"best_scaffold": None, "covered": 0, "overlap": 0,
                "overlap_fraction": None, "verdict": "NO_SHARED_REFERENCE"}

    def strength(acc):
        return (len(cb_a[acc]["hits"]) + len(cb_b[acc]["hits"]),
                cb_a[acc]["cum_score"] + cb_b[acc]["cum_score"])

    best = max(shared, key=strength)
    sa = {h["subject"] for h in cb_a[best]["hits"]}
    sb = {h["subject"] for h in cb_b[best]["hits"]}
    overlap = sa & sb
    smaller = min(len(sa), len(sb))
    of = round(len(overlap) / smaller, 3) if smaller else 1.0
    adj, gap, span = _adjacent(sa, sb)
    if of <= 0.15 and adj:
        verdict = "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY"
    elif of <= 0.15 and not adj:
        verdict = "RECONSTRUCTION_NOT_SUPPORTED_DISTANT_LOCI"
    elif of <= 0.50:
        verdict = "RECONSTRUCTION_WEAK_PARTIAL_OVERLAP"
    else:
        verdict = "RECONSTRUCTION_NOT_SUPPORTED_HIGH_REFERENCE_OVERLAP"
    return {"best_scaffold": best, "covered": len(sa | sb), "overlap": len(overlap),
            "genes_a": len(sa), "genes_b": len(sb),
            "overlap_fraction": of, "verdict": verdict,
            "adjacency_gap": gap, "adjacency_span": span,
            "ref_source": cb_b[best]["source"] or cb_a[best]["source"]}


def make_tiling_fn(cb_dir: str, node_of: Callable[[str], str]) -> Callable[[str, str], dict]:
    """Build a deep-tiling function from a clusterblast dir. node_of(bgc_id) -> contig node prefix."""
    cache: dict[str, dict] = {}

    def _cb(bgc_id: str) -> dict:
        if bgc_id not in cache:
            cache[bgc_id] = _cb_for_node(cb_dir, node_of(bgc_id))
        return cache[bgc_id]

    def tiling(bgc_a: str, bgc_b: str) -> dict:
        return tile_pair(_cb(bgc_a), _cb(bgc_b))

    return tiling


# --- assessment / promotion --------------------------------------------------------------------
def assess_pair(pair_rec: dict, cctt_a: Any, cctt_b: Any,
                deep_tiling: Optional[dict] = None,
                kcb_a: Any = None, kcb_b: Any = None,
                family_map: Optional[dict] = None) -> Optional[dict]:
    """Assess one RG-GMCI pair for diagnostic rescue. Returns a lead dict or None (not a candidate)."""
    a, b = pair_rec.get("bgc_a"), pair_rec.get("bgc_b")
    ra = roles(cctt_a, pair_rec.get("products_a"))
    rb = roles(cctt_b, pair_rec.get("products_b"))

    # need a class core on one side and a complementary arm on the other
    core_side = arm_side = None
    if ra["cores"] and rb["arms"]:
        core_side, arm_side = ("a", "b")
    elif rb["cores"] and ra["arms"]:
        core_side, arm_side = ("b", "a")
    else:
        return None

    # EDGE GATE: only truncated fragments can be halves of a split pathway. If either member is a
    # complete (Interior) cluster, this is co-occurrence on a shared reference, not a split — drop it.
    edge_a = str(pair_rec.get("edge_a") or "")
    edge_b = str(pair_rec.get("edge_b") or "")
    if edge_a not in TRUNCATED_EDGE or edge_b not in TRUNCATED_EDGE:
        return None

    core_bgc = a if core_side == "a" else b
    arm_bgc = a if arm_side == "a" else b
    core_node = pair_rec.get("contig_a") if core_side == "a" else pair_rec.get("contig_b")
    arm_node = pair_rec.get("contig_a") if arm_side == "a" else pair_rec.get("contig_b")
    cores = ra["cores"] if core_side == "a" else rb["cores"]
    arm_roles = ra if arm_side == "a" else rb
    arms = arm_roles["arms"]
    # the diagnostic tailoring signal is a HAL/XHAL trigger; a bare-saccharide arm is glycosylation
    # noise (saccharide is a permanent-exclusion class) and cannot drive a HIGH rescue on its own.
    arm_is_diagnostic = arm_roles["hal_trigger"]

    # shared scaffold present? (deep tiling preferred; else fall back to RG-GMCI best_sources)
    scaffold = None
    covered = overlap = None
    overlap_fraction = None
    verdict = None
    genes_core = genes_arm = None
    if deep_tiling and deep_tiling.get("best_scaffold"):
        scaffold = deep_tiling["best_scaffold"]
        covered = deep_tiling["covered"]
        overlap = deep_tiling["overlap"]
        overlap_fraction = deep_tiling["overlap_fraction"]
        verdict = deep_tiling["verdict"]
        # genes_a/genes_b are keyed to pair bgc_a/bgc_b; map to core/arm
        ga, gb = deep_tiling.get("genes_a"), deep_tiling.get("genes_b")
        genes_core = ga if core_side == "a" else gb
        genes_arm = ga if arm_side == "a" else gb
    else:
        bs = pair_rec.get("best_sources") or ""
        m = re.search(r"\b([A-Z]{2}_?[A-Z0-9]+\d)\s*\(", bs)
        scaffold = m.group(1) if m else None

    has_core = bool(cores)
    has_arm = bool(arms)
    has_shared = bool(scaffold)
    complementary = verdict == "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY" and (
        overlap == 0 or (overlap_fraction or 1) <= 0.15)
    # floors only apply when deep tiling is available
    meets_floor = (covered is None) or (
        covered >= COVERED_FLOOR and (genes_core or 0) >= PER_ARM_FLOOR and (genes_arm or 0) >= PER_ARM_FLOOR)

    if has_core and arm_is_diagnostic and has_shared and complementary and meets_floor:
        tier = "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"
    elif has_core and has_arm and has_shared and complementary:
        # convergent tiling but arm is saccharide-only (glycosylation noise) or below floor
        tier = "DIAGNOSTIC_RESCUE_MODERATE"
    elif has_core and has_arm and has_shared:
        tier = "DIAGNOSTIC_RESCUE_MODERATE"
    elif has_core and has_arm:
        tier = "DIAGNOSTIC_RESCUE_LOW"
    else:
        return None

    # KCB-class concordance gate: a HIGH split must tile two halves of the SAME compound class.
    core_kcb = kcb_a if core_side == "a" else kcb_b
    arm_kcb = kcb_a if arm_side == "a" else kcb_b
    core_family = arm_family = None
    concordance = "not_evaluated"
    if family_map and not family_map.get("_skipped"):
        core_family = kcb_family(core_kcb, family_map)
        arm_family = kcb_family(arm_kcb, family_map)
        concordance = _concordance(core_family, arm_family, family_map)
        if tier == "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE":
            if concordance == "discordant":
                tier = "DIAGNOSTIC_RESCUE_LOW"     # cross-family — co-occurrence, not a split
            elif concordance == "indeterminate":
                tier = "DIAGNOSTIC_RESCUE_MODERATE"  # cannot confirm class concordance

    core_class = cores[0].split("_")[0] if cores else "?"
    safe = (
        f"{core_bgc} ({core_node}, {core_class} core) + {arm_bgc} ({arm_node}, "
        f"{'/'.join(arms)} arm) show biosynthetic capacity consistent with a SPLIT pathway"
        + (f"; complementary tiling onto {scaffold} (homology-based scaffold; {covered} reference genes, {overlap} overlap)."
           if complementary else f"; shared-reference signal on {scaffold} (homology-based, not physical)." if scaffold else ".")
        + " Reconstruction hypothesis only — not a contig join, not a product identity."
    )
    return {
        "pair": pair_rec.get("pair"),
        "core_bgc": core_bgc, "core_node": core_node, "core_triggers": ";".join(cores),
        "core_edge": edge_a if core_side == "a" else edge_b,
        "arm_bgc": arm_bgc, "arm_node": arm_node, "arm_roles": ";".join(arms),
        "arm_edge": edge_a if arm_side == "a" else edge_b,
        "arm_is_diagnostic_halogenase": arm_is_diagnostic,
        "core_kcb_family": core_family,
        "arm_kcb_family": arm_family,
        "kcb_concordance": concordance,
        "rescue_tier": tier,
        "shared_scaffold": scaffold,
        "ref_source": (deep_tiling or {}).get("ref_source"),
        "reference_genes_covered": covered,
        "reference_gene_overlap": overlap,
        "genes_on_scaffold_core": genes_core,
        "genes_on_scaffold_arm": genes_arm,
        "overlap_fraction": overlap_fraction,
        "tiling_verdict": verdict,
        "rggmci_confidence": pair_rec.get("rggmci_confidence"),
        "rggmci_gate": pair_rec.get("acceptance_gate"),
        "promoted_over_rggmci": tier == "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"
        and str(pair_rec.get("rggmci_confidence", "")).startswith("LOW"),
        "claim_ceiling": CLAIM_CEILING,
        "safe_claim": safe,
    }


def build_leads(rggmci_full: dict, cctt_per_bgc: dict, deep_tiling_fn: Optional[Callable] = None,
                kcb_per_bgc: Optional[dict] = None, family_map: Optional[dict] = None) -> list[dict]:
    """Build the ranked Diagnostic Rescue lead list from an RG-GMCI full payload + per-BGC CCTT.

    When `kcb_per_bgc` + `family_map` are supplied, the KCB-class concordance gate is active:
    HIGH requires the core and arm to KCB to compatible biosynthetic families.
    """
    kcb_per_bgc = kcb_per_bgc or {}
    seen: set[str] = set()
    leads: list[dict] = []
    pools = (rggmci_full.get("ranked_pairs") or []) + (rggmci_full.get("split_candidates") or [])
    for pr in pools:
        pair = pr.get("pair")
        if not pair or pair in seen:
            continue
        a, b = pr.get("bgc_a"), pr.get("bgc_b")
        deep = deep_tiling_fn(a, b) if deep_tiling_fn else None
        lead = assess_pair(pr, cctt_per_bgc.get(a), cctt_per_bgc.get(b), deep_tiling=deep,
                           kcb_a=kcb_per_bgc.get(a), kcb_b=kcb_per_bgc.get(b), family_map=family_map)
        if lead:
            seen.add(pair)
            leads.append(lead)
    leads.sort(key=lambda x: (_TIER_RANK.get(x["rescue_tier"], 0),
                              x.get("reference_genes_covered") or 0), reverse=True)
    # Honesty pass: a fragment has ONE true complement, so a BGC appearing in multiple HIGH leads
    # means those are COMPETING hypotheses, not independent facts. Annotate (do not silently drop).
    high = [l for l in leads if l["rescue_tier"] == "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"]
    part = {}
    for l in high:
        part.setdefault(l["core_bgc"], []).append(l["pair"])
        part.setdefault(l["arm_bgc"], []).append(l["pair"])
    for l in high:
        competitors = {p for p in part.get(l["core_bgc"], []) + part.get(l["arm_bgc"], []) if p != l["pair"]}
        l["competing_hypothesis_count"] = len(competitors)
        l["mutually_exclusive_best"] = (len(part.get(l["core_bgc"], [])) == 1
                                        and len(part.get(l["arm_bgc"], [])) == 1)
    return leads

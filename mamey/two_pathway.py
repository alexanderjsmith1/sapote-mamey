"""two_pathway.py — gene-only multi-pathway detection (v9.7.127).

Flags a BGC window where the gene architecture shows TWO core biosynthetic engines of DIFFERENT
class (PKS / NRPS / RiPP / terpene) separated by a moderate gap — i.e. a "single-class" antiSMASH
product label may be hiding a second pathway. This is KCB-independent: it scores on domains and
expected function, not on KnownClusterBlast.

This is the original KCB-patch "two-cluster hypothesis" (Fix 3), reframed and validated on real
data. The validation across six reference strains drove two
constraints that kill the false-positive modes:
  - per-BGC only (never aggregate across antiSMASH regions / contigs) — contig aggregation was the
    dominant false positive on poorly-assembled strains;
  - require a CLASS CHANGE between adjacent engines (a large gap within one same-class modular
    assembly line is one pathway, not two), and a gap in a bounded range (8–60 kb).

A flagged window is a capacity-level signal for the card author, never a product claim.
"""
from __future__ import annotations

import csv
from pathlib import Path

# Core synthase/synthetase domains grouped by biosynthetic class. A gene carrying one of these is a
# class-defining engine. (Names match antiSMASH sec_met_domain tokens.)
CORE_CLASS_DOMAINS = {
    "PKS": {"PKS_KS", "ketoacyl-synt", "mod_KS", "PKS_AT", "hglE", "hglE-KS", "t2pks", "Chal_sti_synt"},
    "NRPS": {"Condensation", "AMP-binding", "A-OX"},
    "RiPP": {"YcaO", "Lant_dehydr", "LANC_like", "Lant_dehydr_C"},
    "terpene": {"Terpene_synth", "Terpene_synth_C", "SQHop_cyclase", "phytoene_synt"},
}
# AUDIT_374: case-insensitive lookup built once at import time. Real antiSMASH domain
# labels for this family appear under multiple casings elsewhere in this codebase --
# ks_phylogeny.py's own _EXCLUDED_DOMAIN_TOKENS explicitly normalizes to lowercase and lists
# {"hgle-ks", "hgle_ks", "hgle"} as separate real variants, with a comment noting a pre-ship bug
# caught 2026-08-10 in this exact domain family. _classify() below previously matched only the
# bare literal "hglE" (case-sensitive, no -KS suffix), so a real "hgle"/"HglE"/"hglE-KS"-labeled
# gene silently fell through as an unclassified (non-core) gene -- dropping it from the two-
# pathway engine count entirely rather than misclassifying it, so genuine PKS engines carrying
# this label could go undetected.
_CORE_CLASS_DOMAINS_L = {cls: {d.lower() for d in dset} for cls, dset in CORE_CLASS_DOMAINS.items()}

GAP_MIN = 8_000     # below this, two cores are one modular assembly line
GAP_MAX = 60_000    # above this, likely separate co-located clusters / aggregation, not one window
_SUPPORT_WINDOW = 15_000  # a real engine center has a non-core support gene within this distance

# Class pairs that form a STANDARD single biosynthetic pathway and must NOT be flagged as two:
# PKS<->NRPS hybrids are ubiquitous single assembly lines. RiPP (ribosomal) and terpene (cyclase)
# machinery do NOT co-assemble with non-ribosomal PKS/NRPS into one product, so a RiPP or terpene
# engine adjacent to a PKS/NRPS/other engine across a gap is the genuine two-pathway signal.
_HYBRID_PAIRS = {frozenset({"PKS", "NRPS"})}


def _is_disconnect_pair(c1: str, c2: str) -> bool:
    """True when the two engine classes do not form a standard single pathway (so a gap between
    them suggests two pathways). PKS<->NRPS is excluded as the canonical hybrid."""
    if c1 == c2:
        return False
    return frozenset({c1, c2}) not in _HYBRID_PAIRS


def _classify(domains) -> str | None:
    """Return the biosynthetic class of a gene's domain list, or None if not a core engine."""
    dl = [str(d).lower() for d in domains]
    for cls, dset in _CORE_CLASS_DOMAINS_L.items():
        if any(d in dset for d in dl):
            return cls
    # PATCH-044 (v9.7.128): antiSMASH emits the chalcone/stilbene synthase (T3PKS) core as
    # ``Chal_sti_synt_C`` / ``Chal_sti_synt_N``, never the bare ``Chal_sti_synt`` stem. Prefix-
    # match so all suffix variants (and any future ones) are assigned to the PKS engine class.
    if any(d.startswith("chal_sti_synt") for d in dl):
        return "PKS"
    return None


def _split_domains(raw) -> list[str]:
    """gene_by_gene sec_met_domains may be a list or a ';'/','-joined string."""
    if isinstance(raw, (list, tuple)):
        return [str(d).split(" ")[0] for d in raw]
    s = str(raw or "").strip()
    if not s or s in ("—", "None", "[]"):
        return []
    s = s.strip("[]").replace("'", "").replace('"', "")
    return [tok.strip().split(" ")[0] for tok in s.replace(";", ",").split(",") if tok.strip()]


def detect_two_pathway(genes: list[dict]) -> dict:
    """Analyze one BGC's genes (rows with cds_start, cds_end, sec_met_domains).

    Returns: {"two_pathway": bool, "engines": [(locus, class)...], "splits": [...], "detail": str}
    A split is recorded only for adjacent engines of DIFFERENT class separated by GAP_MIN..GAP_MAX,
    with a non-core support gene on each side (so each is a genuine center, not a stray domain).
    """
    parsed = []
    for g in genes:
        try:
            s = int(g.get("cds_start") or 0)
            e = int(g.get("cds_end") or s)
        except (TypeError, ValueError):
            continue
        doms = _split_domains(g.get("sec_met_domains"))
        parsed.append((g.get("locus_tag", ""), s, e, doms, _classify(doms)))
    parsed.sort(key=lambda x: x[1])

    engines = [(lt, s, e, c) for lt, s, e, doms, c in parsed if c]
    if len(engines) < 2:
        return {"two_pathway": False, "engines": [(lt, c) for lt, _, _, c in engines],
                "splits": [], "detail": ""}

    splits = []
    for (lt1, s1, e1, c1), (lt2, s2, e2, c2) in zip(engines, engines[1:]):
        gap = s2 - e1
        if not _is_disconnect_pair(c1, c2) or not (GAP_MIN <= gap <= GAP_MAX):
            continue
        # each engine should sit among non-core genes (a real center, not a stray domain): look for
        # a non-core support gene in the gap region between the two engines, on each engine's side.
        midpoint = (e1 + s2) / 2
        left = any(s1 < s < midpoint and _classify(d) is None for _, s, _, d, _ in parsed)
        right = any(midpoint < s < e2 and _classify(d) is None for _, s, _, d, _ in parsed)
        if left or right:  # at least one flanking support gene in the gap
            splits.append({"e1": lt1, "c1": c1, "e2": lt2, "c2": c2, "gap": gap})

    if not splits:
        return {"two_pathway": False, "engines": [(lt, c) for lt, _, _, c in engines],
                "splits": [], "detail": ""}

    classes = sorted({c for sp in splits for c in (sp["c1"], sp["c2"])})
    detail = "; ".join(f"{sp['c1']}→{sp['c2']} ({sp['gap']:,}bp)" for sp in splits)
    return {"two_pathway": True, "engines": [(lt, c) for lt, _, _, c in engines],
            "splits": splits, "classes": classes, "detail": detail}


def two_pathway_by_bgc(package_dir: str | Path) -> dict[str, dict]:
    """Run detection for every BGC in the package gene-by-gene table.

    Returns {bgc_id: verdict}. Reads <strain>_gene_by_gene_all_bgcs.csv. Per-BGC only — never
    aggregates across BGCs (the validated guard against contig-aggregation false positives).
    """
    pkg = Path(package_dir)
    tables = sorted(pkg.glob("*_gene_by_gene_all_bgcs.csv"))
    if not tables:
        return {}
    rows_by_bgc: dict[str, list[dict]] = {}
    # A bare `except Exception: return {}` here discarded every row already parsed and returned an
    # empty dict, which the caller reads as "no BGC is two-pathway" and then writes a SUCCESS phase
    # receipt (bgcs_evaluated=0). Let a genuine read/parse failure propagate to cli.py's outer
    # handler, which already records an ERROR receipt and a [WARN] issue.
    with open(tables[0], newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            bid = (row.get("bgc_id") or "").strip()
            if bid:
                rows_by_bgc.setdefault(bid, []).append(row)
    return {bid: detect_two_pathway(genes) for bid, genes in rows_by_bgc.items()}


def two_pathway_flag_cell(verdict: dict | None) -> str:
    """Triage-board cell for the Two_Pathway_Flag column. Empty when single-pathway."""
    if not verdict or not verdict.get("two_pathway"):
        return ""
    classes = "+".join(verdict.get("classes", []))
    return f"TWO_PATHWAY:{classes} ({verdict['detail']})"

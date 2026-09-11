#!/usr/bin/env python3
"""Mode-B cards — deterministic per-BGC scaffolds, Blue, 2026-07-18.

One Markdown card per BGC per strain. Fills every *deterministic* Mode-B field (identity, assembly context,
composition tag, architecture domain-counts, full domain inventory with context, domain-bearing gene table,
auto-priors, KCB/novelty) by assembling from the sealed package + per-strain domains.csv + domain_reference.
Leaves the *judgment* fields as explicit stubs for Sapote / wet-lab — Mamey extracts.

Orphan cores and tailoring cassettes are SURFACED with a banner, never demoted (fragmented-assembly policy).

Usage: python build_cards.py --all
       python build_cards.py --strain AS-XXX
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

import argparse
import csv
import os
import re
from collections import defaultdict

from .series_common import find_packages, load_package, strain_of
from .bigscape_namespace import validate_membership_rows

# Engine port (v9.7.330): the original Lab Quest/Blue workbench script hardcoded absolute paths under
# the user's home. As an engine subcommand these become optional inputs that DEGRADE GRACEFULLY:
# domains come from the sealed package (BLUE_01's <strain>_domains.csv); the external enrichments
# (curated bgc_gcf.csv, the cohort BLASTp tree, the strain-metadata workbooks) are opt-in flags and
# resolve to empty when absent, so a card always renders from the package alone.
MODE_B = None
LOCUS = None
MC = None

CORE_CATS = {"PKS-core", "NRPS-core"}
TAIL_CATS = {"tailoring-oxidoreduction", "tailoring-methylation", "tailoring-glycosylation",
             "tailoring-halogenation", "tailoring-other", "RiPP-maturation", "terpene/prenyl"}
CAT_ORDER = ["PKS-core", "PKS-reductive", "NRPS-core", "carrier", "loading", "release",
             "tailoring-oxidoreduction", "tailoring-methylation", "tailoring-glycosylation",
             "tailoring-halogenation", "tailoring-other", "RiPP-maturation", "terpene/prenyl",
             "transport", "regulatory", "resistance", "structural", "uncharacterized", "other"]


def load_reference(path: str) -> dict:
    ref = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            ref[r["domain"]] = (r["category"], r["context"], r["pfam_acc"])
    return ref


def load_rggmci(pkg: str) -> dict:
    """bgc -> list of split-pathway pair rows involving it (RG-GMCI rescue layer)."""
    import glob as _g
    out = defaultdict(list)
    hits = _g.glob(os.path.join(pkg, "*_4A_RGGMCI_ranked_pairs.csv"))
    if not hits:
        return out
    with open(hits[0], encoding="utf-8", errors="ignore") as fh:
        for r in csv.DictReader(fh):
            for me, partner, pprod in ((r.get("bgc_a"), r.get("bgc_b"), r.get("products_b")),
                                       (r.get("bgc_b"), r.get("bgc_a"), r.get("products_a"))):
                if me:
                    out[me].append({"partner": partner, "partner_products": pprod,
                                    "confidence": r.get("rggmci_confidence", ""),
                                    "score": r.get("rggmci_score", ""),
                                    "rescue_class": r.get("functional_rescue_class", ""),
                                    "terminus": r.get("terminus_truncation_rescue", ""),
                                    "shared_products": r.get("shared_product_tokens", ""),
                                    "guard": r.get("interpretation_guard", "")})
    return out


# Optional external BLASTp enrichment (opt-in; not shipped). None = degrade to no BLASTp overlay.
ENRICHED_BLASTP = None
BLASTP_ROOT = None


def _short(s: str, n: int = 46) -> str:
    s = (s or "").strip().strip('"')
    return s if len(s) <= n else s[:n - 1] + "…"


def load_clusterblast(pkg: str) -> dict:
    """(bgc, gene) -> (pct_id, organism, ref_acc); best hit per gene by blast_score. Universal per package."""
    import glob as _g
    out: dict = {}
    hits = _g.glob(os.path.join(pkg, "*_4A2_ClusterBlast_per_gene.csv"))
    if not hits:
        return out
    best: dict = {}
    with open(hits[0], encoding="utf-8", errors="ignore") as fh:
        for r in csv.DictReader(fh):
            k = (r.get("bgc_id", ""), r.get("query_gene", ""))
            try:
                sc = float(r.get("blast_score") or 0)
            except ValueError:
                sc = 0
            if k[1] and sc >= best.get(k, -1):
                best[k] = sc
                out[k] = (r.get("pct_identity", ""), r.get("reference_source", ""), r.get("reference", ""))
    return out


def load_convergence(pkg: str) -> dict:
    """bgc_id -> ranked list of per-gene MIBiG-convergence rows (P_MPG/P_LWC), from
    *_3_mibig_convergence.csv. This interpreted layer (convergence_tier, recognizable_gene_share,
    dominance_status, class_concordance, verbatim claim_safety) is the PRIMARY Mode-B family evidence,
    held above single-hit KCB and the keyword AF appendix. Reader-side; tiers are reporting strata,
    not final Sapote judgments."""
    import glob as _g
    out: dict = defaultdict(list)
    hits = _g.glob(os.path.join(pkg, "*_3_mibig_convergence.csv"))
    if not hits:
        return out
    with open(hits[0], encoding="utf-8", errors="ignore") as fh:
        for r in csv.DictReader(fh):
            b = r.get("bgc_id", "")
            if b:
                out[b].append(r)
    for b in out:
        out[b].sort(key=lambda r: int(re.sub(r"\D", "", r.get("convergence_rank", "") or "9999") or "9999"))
    return out


def convergence_layer_present(pkg: str) -> bool:
    """True when the package actually SHIPS a per-gene MIBiG-convergence table.

    v9.7.336: needed to tell "the layer ran and found no family for this BGC" (genuinely
    reference-dark — an evidence-backed novelty prior) apart from "the layer is not in this
    package at all" (says nothing). Every package sealed before v9.7.332 lacks it, and the
    reporting-v2 gate deliberately treats those as LEGACY_NOT_APPLICABLE rather than invalid —
    so without this probe a card would print a novelty prior derived from a file that was
    never written, on every BGC of every pre-.332 package.
    """
    import glob as _g
    return bool(_g.glob(os.path.join(pkg, "*_3_mibig_convergence.csv")))


def load_blastp_all() -> dict:
    """strain -> {(bgc, gene): (pct_id, desc, sciname, aa)} from enriched cohort file (rank-1) + per-BGC top10."""
    import glob as _g
    idx: dict = defaultdict(dict)
    if ENRICHED_BLASTP and os.path.exists(ENRICHED_BLASTP):
        with open(ENRICHED_BLASTP, encoding="utf-8", errors="ignore") as fh:
            for r in csv.DictReader(fh):
                if (r.get("hit_rank") or "") not in ("1", ""):
                    continue
                s, b, g = r.get("strain", ""), r.get("bgc", ""), r.get("gene", "")
                if s and g:
                    idx[s][(b, g)] = (r.get("pct_identity", ""), r.get("subject_desc", ""),
                                      r.get("sciname", ""), r.get("aa", ""))
    # per-BGC top10 files fill strains missing from the enriched file
    for f in (_g.glob(os.path.join(BLASTP_ROOT, "AS-*", "**", "*_blastp_top10*.csv"), recursive=True)
              if BLASTP_ROOT else []):
        try:
            rows = list(csv.DictReader(open(f, encoding="utf-8", errors="ignore")))
        except OSError:
            continue
        for r in rows:
            if (r.get("hit_rank") or "") not in ("1", ""):
                continue
            s, b, g = r.get("strain", ""), r.get("bgc_id", r.get("bgc", "")), r.get("gene", "")
            if s and g and (b, g) not in idx[s]:
                idx[s][(b, g)] = (r.get("pct_identity", ""), r.get("subject_def", ""),
                                  r.get("subject_organism", ""), r.get("aa_length", ""))
    return idx


# Optional strain-metadata workbooks (opt-in; not shipped). None = degrade to no measured-bioactivity join.
STRAIN_TABLE = None
ISOLATES_TABLE = None


def _as_key(v) -> str | None:
    m = re.match(r"\s*A\.?S\.?[-# ]?(\d+)\b", str(v or ""), re.I)
    return f"AS-{m.group(1)}" if m else None


def load_isolates_meta() -> dict:
    """AS-### -> {genus, host, activity} from the source institution 'All Isolates' sheet (free-text bioactivity).
    Fallback source for strains not in the clean Hymenoptera table; activity is qualitative screen text."""
    out: dict = {}
    try:
        import openpyxl
    except ImportError:
        return out
    if not ISOLATES_TABLE:
        return out
    try:
        wb = openpyxl.load_workbook(ISOLATES_TABLE, read_only=True, data_only=True)
    except OSError:
        return out
    if "All Isolates" not in wb.sheetnames:
        return out

    def clean_genus(v):
        s = re.sub(r"^16S\s*[=:]\s*", "", str(v or "").strip(), flags=re.I).strip()
        return s if re.match(r"^[A-Z][a-z]{3,}(\s(sp|sp\.))?$", s) else ""

    for r in wb["All Isolates"].iter_rows(values_only=True):
        key = next((_as_key(c) for c in r[:3] if _as_key(c)), None)
        if not key or key in out:
            continue
        genus = clean_genus(r[21] if len(r) > 21 else "") or clean_genus(r[3] if len(r) > 3 else "")
        host = str((r[17] if len(r) > 17 else "") or (r[16] if len(r) > 16 else "") or "").strip()
        txt = " ".join(str(r[i]) for i in (7, 8) if len(r) > i and r[i])
        acts = [seg.strip() for seg in re.split(r"[;.]", txt) if re.search(r"MRSA|Candida|activ|inhib", seg, re.I)]
        out[key] = {"genus": genus, "host": host, "activity": " · ".join(acts)[:140],
                    "candida": "", "mrsa": "", "closest": "", "sim": "", "src": "isolation records"}
    return out


def load_strain_meta() -> dict:
    """AS-### -> {host, genus, closest, sim, candida, mrsa} from the Hymenoptera strain table."""
    out: dict = {}
    try:
        import openpyxl
    except ImportError:
        return out
    if not STRAIN_TABLE:
        return out
    try:
        wb = openpyxl.load_workbook(STRAIN_TABLE, read_only=True, data_only=True)
    except OSError:
        return out
    for r in wb.active.iter_rows(min_row=2, values_only=True):
        sid = str(r[2] or "").strip()
        if not sid:
            continue
        m = re.search(r"(\d+)", sid)
        key = f"AS-{m.group(1)}" if sid.upper().startswith("AS") and m else sid
        sim = r[6]
        try:
            sim = f"{float(sim) * 100:.1f}%" if float(sim) <= 1 else f"{float(sim):.1f}%"
        except (TypeError, ValueError):
            sim = str(sim or "").strip()
        out[key] = {"host": str(r[0] or "").strip(), "genus": str(r[3] or "").strip(),
                    "closest": str(r[4] or "").strip(), "sim": sim,
                    "candida": str(r[7] or "").strip(), "mrsa": str(r[8] or "").strip(),
                    "activity": "", "src": "Hymenoptera table"}
    return out


def load_lead_boards(pkg: str) -> dict:
    """bgc -> {af_rank, af_score, af_tier, af_n, ab_rank, ab_score, ab_tier, ab_n}."""
    import glob as _g
    out: dict = defaultdict(dict)
    for tag, sc in (("AF", "AF_score"), ("AB", "AB_score")):
        hits = _g.glob(os.path.join(pkg, f"*_4c_{tag}_lead_board.csv"))
        if not hits:
            continue
        rows = list(csv.DictReader(open(hits[0], encoding="utf-8", errors="ignore")))
        n = len(rows)
        for r in rows:
            b = (r.get("BGC_ID") or "").strip()
            if b:
                out[b][f"{tag.lower()}_rank"] = r.get("Board_rank", "")
                out[b][f"{tag.lower()}_score"] = r.get(sc, "")
                out[b][f"{tag.lower()}_tier"] = r.get("Lead_tier", "")
                out[b][f"{tag.lower()}_n"] = n
    return out


def load_gcf(gcf_csv=None) -> dict:
    """(strain, bgc) -> BiGSCAPE GCF membership row, from an optional precomputed bgc_gcf.csv."""
    out: dict = {}
    path = gcf_csv
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            rows = validate_membership_rows(
                csv.DictReader(fh), key_fields=("strain", "bgc")
            )
            for r in rows:
                out[(r["strain"], r["bgc"])] = r
    return out


# antiSMASH gene_functions "kind" keywords, most-specific first (so the "-additional"
# subtype is matched before the bare "biosynthetic" prefix). Used to distill a short role
# label for the domain-bearing-genes table when the package ships no explicit role column.
_ROLE_KEYS = (
    ("biosynthetic-additional", "biosynthetic (additional)"),
    ("biosynthetic",            "biosynthetic (core)"),
    ("transport",               "transport"),
    ("regulatory",              "regulatory"),
    ("resistance",              "resistance"),
    ("other",                   "other"),
)


def _distill_role(gene_functions: str) -> str:
    """Reduce an antiSMASH gene_functions string to a one-word role, or '' if none."""
    g = (gene_functions or "").lower()
    for key, label in _ROLE_KEYS:
        if key in g:
            return label
    return ""


def _gene_meta_from_cds_table(strain: str, pkg: str) -> dict:
    """locus_tag -> (role, product), read from the sealed package's `<strain>_cds_table.csv`.

    The gold-run domains.csv is domain-resolved and carries no per-gene role/product, so we
    recover them from the flat per-CDS table (columns product, gene_functions). Returns {}
    when the table is absent (older packages) — callers then fall back to blank role/product."""
    import glob as _g
    meta: dict = {}
    if not pkg:
        return meta
    hits = _g.glob(os.path.join(pkg, f"{strain}_cds_table.csv")) or _g.glob(os.path.join(pkg, "*_cds_table.csv"))
    if not hits:
        return meta
    try:
        with open(hits[0], encoding="utf-8", errors="ignore") as fh:
            for r in csv.DictReader(fh):
                lt = (r.get("locus_tag") or "").strip()
                if lt:
                    meta[lt] = (_distill_role(r.get("gene_functions") or ""),
                                (r.get("product") or "").strip())
    except Exception:
        return {}
    return meta


def load_domains_csv(strain: str, pkg: str = None) -> dict:
    """bgc -> {'genes': {locus:(role,product)}, 'domains': [(locus,domain)]}.

    Reads the per-strain domain passthrough. Prefers the sealed package's own
    `<strain>_domains.csv`; falls back to a `locus_maps/by_strain/<strain>/` layout if given.

    Schema-tolerant column mapping (v9.7.331): the gold-run core emits the
    `bgc_id,locus_tag,feature_type,domain,pfam_acc,…` schema, while the legacy BLUE_01
    passthrough used `bgc,locus,role,product,domain`. Accept either. role/product are not in
    the core-run domains.csv, so when they're absent they're recovered per-locus from the
    package's `<strain>_cds_table.csv`."""
    import glob as _g
    path = None
    if pkg:
        hits = _g.glob(os.path.join(pkg, f"{strain}_domains.csv")) or _g.glob(os.path.join(pkg, "*_domains.csv"))
        path = hits[0] if hits else None
    if not path and LOCUS:
        cand = os.path.join(LOCUS, "by_strain", strain, f"{strain}_domains.csv")
        path = cand if os.path.exists(cand) else None
    out = defaultdict(lambda: {"genes": {}, "domains": []})
    if not path or not os.path.exists(path):
        return out
    gene_meta = _gene_meta_from_cds_table(strain, pkg)
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            b = (r.get("bgc") or r.get("bgc_id") or "").strip()
            if not b:
                continue
            loc = (r.get("locus") or r.get("locus_tag") or "").strip()
            dom = (r.get("domain") or "").strip()
            # role/product: honour explicit legacy columns; otherwise recover from cds_table.
            role, prod = r.get("role"), r.get("product")
            if role is None or prod is None:
                m_role, m_prod = gene_meta.get(loc, ("", ""))
                role = m_role if role is None else role
                prod = m_prod if prod is None else prod
            if loc:
                out[b]["genes"].setdefault(loc, (role or "", prod or ""))
            if dom:
                out[b]["domains"].append((loc, dom))
    return out


def composition(cats_present: set, cls: str) -> tuple[str, str]:
    has_core = bool(cats_present & CORE_CATS)
    has_tail = bool(cats_present & TAIL_CATS)
    if has_core and has_tail:
        return "core + tailoring", ""
    if has_core:
        return "core-only (orphan core)", "> **Surfaced orphan core.** A PKS/NRPS core with no co-localized tailoring — often the tailoring is on another contig in these fragmented assemblies. Kept and annotated, not demoted."
    if has_tail:
        return "tailoring-cassette (orphan accessory)", "> **Surfaced orphan tailoring cassette.** Accessory/tailoring enzymes with no co-localized PKS/NRPS core — the core may sit on another contig. Kept and annotated, not demoted."
    if cls and cls.lower() not in ("other", "unknown", ""):
        return f"other-class ({cls})", ""
    return "bare (no core/tailoring domains detected)", ""


# --- v9.7.331: taxonomy claim-safety (16S provenance + genome-scale novelty deferral) ---
# Judgment-deferred taxonomy string: a 16S-only genus assignment can over-claim novelty. Three
# calibration shapes motivate the rule: (A) 16S reads "candidate new genus" with no local same-genus
# 16S, but MLSA+ANI later places the strain INSIDE a known genus as a candidate novel *species*;
# (B) a strain that is a genuine novel genus by genome-scale distance (low ANI to any named genus);
# (C) a strain that resolves to a known species once ANI is computed. Rule: a 16S-derived
# genus is capacity-level -> label its provenance, and DEFER any genus-level novelty claim to genome-scale
# evidence. meta['genus_evidence'] in _GENOME_SCALE_EVIDENCE marks a genome-confirmed call that may be
# emitted cleanly (the future hook for wiring MLSA/ANI results back into the card).
_GENUS_NOVELTY_RE = re.compile(
    r"\b(?:new|novel|candidate)\b[\s\S]{0,40}\bgenus\b|\bgenus\b[\s\S]{0,40}\b(?:new|novel|candidate)\b",
    re.I,
)
_GENOME_SCALE_EVIDENCE = {"mlsa", "ani", "genome", "genome-scale", "genome_scale", "polyphasic"}


def _taxonomy_line(meta: dict, esc=None) -> str:
    """Claim-safe strain taxonomy string for a Mode-B card header.

    (i) 16S-derived genus calls carry an explicit provenance tag; (ii) genus-level novelty language
    ("candidate new genus") asserted from 16S alone is stripped and replaced with a capacity-safe
    "closest genus (16S) ...; genus-level novelty pending genome-scale delineation (MLSA/ANI)" string.
    A genome-scale-confirmed call (meta['genus_evidence']) is emitted with its genus intact."""
    if esc is None:
        esc = lambda s: (s or "").replace("|", "·").strip()
    genus = str(meta.get("genus") or "").strip()
    closest = str(meta.get("closest") or "").strip()
    sim = str(meta.get("sim") or "").strip()
    genome_scale = str(meta.get("genus_evidence") or "").strip().lower() in _GENOME_SCALE_EVIDENCE
    if _GENUS_NOVELTY_RE.search(genus) and not genome_scale:
        anchor = esc(closest) or "—"
        s = f"closest genus (16S) *{anchor}*"
        if sim:
            s += f" ~{esc(sim)}"
        return s + "; genus-level novelty pending genome-scale delineation (MLSA/ANI)"
    tax = esc(genus) or "—"
    if closest:
        prov = "genome-scale" if genome_scale else "16S"
        tax += f" ({prov}; closest *{esc(closest)}*" + (f" ~{esc(sim)}" if sim else "") + ")"
    elif genus and not genome_scale:
        tax += " (16S)"
    return tax


def card(strain: str, rec, dd: dict, ref: dict, rgg: list, cblast: dict, blastp: dict, gcf: dict,
         meta: dict, boards: dict, conv: list = None, conv_layer: bool = None,
         verdict_block: str = "") -> str:
    bgc = rec.bgc
    genes = dd.get(bgc, {}).get("genes", {})
    dom_occ = dd.get(bgc, {}).get("domains", [])
    esc = lambda s: (s or "").replace("|", "·").strip()
    dom_by_gene: dict[str, list[str]] = defaultdict(list)
    for loc, dom in dom_occ:
        dom_by_gene[loc].append(dom)
    # categorize occurrences
    cat_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    cats_present: set[str] = set()
    for _loc, dom in dom_occ:
        cat, _ctx, _pf = ref.get(dom, ("other", "", ""))
        cat_counts[cat][dom] += 1
        cats_present.add(cat)
    comp, banner = composition(cats_present, rec.cls)
    high_rescue = [p for p in rgg if "HIGH" in (p["confidence"] or "").upper()]
    if banner and high_rescue:
        partners = ", ".join(sorted({p["partner"] for p in high_rescue}))
        banner = banner.rstrip(".") + f" — **RGGMCI-rescued** (HIGH split-pathway link to {partners}; see the RG-GMCI section)."
    edge = "yes — likely truncated at contig boundary" if rec.is_edge else "no"
    frag = "yes (<20 kb)" if rec.len_kb and rec.len_kb < 20 else "no"
    # architecture module counts (factual raw counts)
    def cnt(*names):
        return sum(v for dom, v in ((d, sum(1 for l, x in dom_occ if x == d)) for d in names))
    ks = cnt("PKS_KS"); at = cnt("PKS_AT", "Acyl_transf_1"); kr = cnt("PKS_KR")
    dh = cnt("PKS_DH", "PKS_DH2", "PKS_DHt"); er = cnt("PKS_ER")
    cond = sum(1 for l, x in dom_occ if x.startswith("Condensation") or x == "Heterocyclization")
    aden = cnt("AMP-binding", "TIGR01733", "A-OX"); pcp = cnt("PCP", "PP-binding")

    def bio(v):
        return "**+**" if v.strip() in ("+", "Y", "yes", "Yes", "TRUE", "True", "1") else (esc(v) or "not tested")

    L = []
    L.append(f"# Mode-B card — {strain} · {bgc}")
    L.append("")
    if meta:
        tax = _taxonomy_line(meta, esc)   # v9.7.331: 16S provenance + genome-scale novelty deferral
        L.append(f"**Strain:** {strain} · {tax}" + (f" · host/source *{esc(meta['host'])}*" if meta.get("host") else ""))
        if meta.get("candida") or meta.get("mrsa"):
            L.append(f"**Measured bioactivity (strain-level):** Candida/antifungal {bio(meta.get('candida',''))} · "
                     f"MRSA/antibacterial {bio(meta.get('mrsa',''))}  ·  _src: {meta.get('src','')}_")
        elif meta.get("activity"):
            L.append(f"**Reported activity (strain-level, crude/fraction screen):** {esc(meta['activity'])}  ·  "
                     f"_src: {meta.get('src','')}_")
        L.append("")
    L.append(f"**Class:** {rec.cls}  ·  **Contig:** {rec.contig or '—'}  ·  "
             f"**Length:** {rec.len_kb:.1f} kb  ·  **Composition:** {comp}")
    if banner:
        L += ["", banner]
    L += ["", "## Facts (deterministic)", "",
          "| field | value |", "|---|---|",
          f"| Genes with annotated domains | {len(genes)} |",
          f"| Domain occurrences / unique | {len(dom_occ)} / {len({d for _l, d in dom_occ})} |",
          f"| Composition | {comp} |",
          f"| Contig-edge | {edge} |",
          f"| Fragment | {frag} |", ""]
    # auto-priors
    L += ["## Auto-priors — routing values, **not** measured activity", "",
          "| AB prior | AF prior | Novelty | Lead tier | KCB top hit |", "|---|---|---|---|---|",
          f"| {rec.ab:g} | {rec.af:g} | {rec.novelty or '—'} | {rec.lead_tier or '—'} | "
          f"{esc(rec.kcb_top) or 'no known-cluster match'} |", "",
          "> Priors are mamey auto-floor routing numbers, not activity. KCB = *similarity* to a "
          "characterized cluster, not identity; an empty top hit is a novelty prior, not proof of a new compound.", ""]
    if boards:
        af = (f"**AF (antifungal) lead board: rank {boards['af_rank']}/{boards['af_n']}** "
              f"(score {boards.get('af_score','—')}, {boards.get('af_tier','—')})" if boards.get("af_rank") else "")
        ab = (f"AB (antibacterial) lead board: rank {boards['ab_rank']}/{boards['ab_n']} "
              f"(score {boards.get('ab_score','—')}, {boards.get('ab_tier','—')})" if boards.get("ab_rank") else "")
        line = " · ".join(x for x in (af, ab) if x)
        if line:
            L += [line, "", "> Lead-board rank = mamey's within-strain routing order (AF-primary), still a "
                  "capacity prior, not measured activity.", ""]
    # Per-gene MIBiG convergence — PRIMARY family evidence (P_MPG/P_LWC). Wired reader-side from the
    # sealed package's *_3_mibig_convergence.csv; held above single-hit KCB and the keyword AF appendix.
    # convergence_tier is a reporting stratum, not a final judgment; a reference-dark locus (no row) is a
    # novelty prior, not proof of a new compound.
    crows = conv or []
    L += ["## Per-gene MIBiG convergence — primary family evidence", ""]
    if crows:
        L += ["| rank | MIBiG family (accession) | tier | genes | gene-share | med %id/cov | class | dominance |",
              "|---:|---|---|---:|---:|---|---|---|"]
        for r in crows[:5]:
            # CONV-01 (v9.7.338): print the 0–100 capped coverage-interpretation, not the raw
            # median_pct_coverage (which can exceed 100% — 109 rank≤5 rows printed >100%, e.g. 102.9 —
            # defeating the coverage≠identity contract). Fall back to raw only if the interp field is
            # absent (packages sealed before the interpretation column existed).
            _covi = r.get('median_pct_coverage_interpretation')
            _cov = _covi if _covi not in (None, "") else r.get('median_pct_coverage', '')
            L.append(
                f"| {esc(r.get('convergence_rank',''))} | {esc(r.get('mibig_compound',''))[:34]} "
                f"({esc(r.get('mibig_accession',''))}) | {esc(r.get('convergence_tier',''))} | "
                f"{esc(r.get('distinct_query_genes',''))} | {esc(r.get('recognizable_gene_share',''))} | "
                f"{esc(r.get('median_pct_identity',''))}/{esc(_cov)} | "
                f"{esc(r.get('class_concordance',''))} | {esc(r.get('dominance_status',''))} |")
        top = crows[0]
        cs = next((r.get("claim_safety", "") for r in crows if r.get("claim_safety")), "")
        strong = (top.get("convergence_tier", "") in ("H1_HIGH_DENSITY", "H2_STRONG_FAMILY")
                  and top.get("class_concordance", "") == "CONCORDANT")
        read = (" — **strong concordant** multi-gene family evidence (lead-grade)." if strong
                else " — held as a **caution** (low tier or class-discordant), not a lead.")
        L += ["", f"> **Convergence read:** top family *{esc(top.get('mibig_compound',''))[:40]}* "
              f"at tier **{esc(top.get('convergence_tier',''))}**{read}  {esc(cs)}", ""]
    elif conv_layer:
        # The layer RAN and returned no family for this locus — an evidence-backed negative.
        L += ["_No per-gene MIBiG convergence for this locus (**reference-dark**). Family evidence falls to "
              "the CCTT / AF-score channel and de-novo domain logic; the absence of a family match is a "
              "novelty prior, **not** proof of a new compound._", ""]
    else:
        # v9.7.336: the layer is ABSENT from this package (pre-v9.7.332 seal, or P_MPG produced no
        # table) — or its presence was never established. Absence of a check is not a negative
        # result: printing the reference-dark novelty prior here would assert a family-evidence
        # conclusion drawn from a file that was never written.
        L += ["_This package does not carry the per-gene MIBiG-convergence table "
              "(`*_3_mibig_convergence.csv`), so **no family-convergence statement can be made for this "
              "locus** — this is *not* a reference-dark finding and *not* a novelty prior. Packages "
              "sealed before v9.7.332 predate the layer; re-run on engine >= 1.9.114 to populate it._", ""]
    # architecture
    # v9.7.343 surfacing patch: the engine's already-computed capacity verdict
    # (Arch_Capacity/Class_Conf + Diagnostic-Rescue), precomputed in process_strain.
    if verdict_block:
        L += [verdict_block, ""]
    L += ["## Architecture (domain counts)", ""]
    arch = []
    if ks or at:
        arch.append(f"- **PKS:** ~{ks} extension module(s) (KS), {at} AT, reductive loop KR {kr} / DH {dh} / ER {er}")
    if cond or aden:
        arch.append(f"- **NRPS:** ~{cond} condensation step(s) (C), {aden} adenylation (A), {pcp} carrier (PCP/ACP)")
    for cat in ("RiPP-maturation", "terpene/prenyl"):
        if cat in cat_counts:
            arch.append(f"- **{cat}:** {sum(cat_counts[cat].values())} domain hit(s) "
                        f"({', '.join(sorted(cat_counts[cat]))[:80]})")
    tail = [c for c in cat_counts if c.startswith("tailoring-")]
    if tail:
        arch.append(f"- **Tailoring:** " + "; ".join(
            f"{c.split('-', 1)[1]} ×{sum(cat_counts[c].values())}" for c in tail if c in cat_counts))
    L += (arch or ["- (no core/tailoring biosynthetic domains detected on this locus)"]) + [""]
    # domain inventory grouped
    L += ["## Domain inventory (context from domain reference)", ""]
    for cat in CAT_ORDER:
        if cat not in cat_counts:
            continue
        L.append(f"**{cat}**")
        for dom in sorted(cat_counts[cat], key=lambda d: -cat_counts[cat][d]):
            _c, ctx, pf = ref.get(dom, ("other", "", ""))
            n = cat_counts[cat][dom]
            pfx = f" ({pf})" if pf else ""
            L.append(f"- `{dom}`{pfx} ×{n} — {ctx}")
        L.append("")
    # gene table (domain-bearing) with per-gene homology: BLASTp (NCBI) preferred, else ClusterBlast; + size
    def homolog(loc):
        bp = blastp.get((bgc, loc))
        if bp and (bp[0] or bp[1] or bp[2]):
            pid, desc, sci, aa = bp
            name = _short(f"{esc(desc)}" + (f" · {esc(sci)}" if sci else ""))
            return (f"{pid}% " if pid else "") + name + " ᴮᴾ", aa
        cb = cblast.get((bgc, loc))
        if cb and (cb[0] or cb[1]):
            pid, org, _acc = cb
            return (f"{pid}% " if pid else "") + _short(esc(org)) + " ᶜᴮ", ""
        return "—", ""
    n_bp = sum(1 for loc in genes if (bgc, loc) in blastp)
    hdr_note = f" · homolog: ᴮᴾ BLASTp (NCBI), ᶜᴮ ClusterBlast" + (f" · BLASTp on {n_bp}/{len(genes)} genes" if n_bp else "")
    L += [f"## Domain-bearing genes{hdr_note}", "", "| locus | role | aa | domains | top homolog |", "|---|---|---:|---|---|"]
    for loc in sorted(genes, key=lambda l: (re.sub(r".*_", "", l).zfill(6))):
        role, prod = genes[loc]
        doms = ", ".join(esc(d) for d in dom_by_gene.get(loc, [])) or "—"
        hom, aa = homolog(loc)
        L.append(f"| `{loc}` | {role or '—'} | {aa or '—'} | {doms} | {hom} |")
    # RG-GMCI split-pathway linkage layer (rescue across contigs; BLASTp-aided later)
    L += ["", "## RG-GMCI split-pathway linkage"]
    if rgg:
        rgg_sorted = sorted(rgg, key=lambda p: -int(re.sub(r"\D", "", p["score"] or "0") or 0))
        L += ["", "Candidate partner loci that may belong to the same pathway split across contigs "
              "(fragmented-assembly rescue). Homology-guided, **not** nucleotide-level joining.", "",
              "| partner BGC | confidence | score | rescue class | terminus-split | partner products |",
              "|---|---|---:|---|---|---|"]
        for p in rgg_sorted:
            L.append(f"| {p['partner']} | {esc(p['confidence'])} | {p['score']} | {esc(p['rescue_class']) or '—'} | "
                     f"{p['terminus'] or '—'} | {esc(p['partner_products']) or '—'} |")
        sp = esc(next((p["shared_products"] for p in rgg_sorted if p["shared_products"]), ""))
        if sp:
            L += ["", f"**Shared product tokens:** {sp}"]
        bp_here = sum(1 for loc in genes if (bgc, loc) in blastp)
        bp_line = (f"- [ ] **BLASTp follow-up** (aids RG-GMCI): BLASTp present for {bp_here} gene(s) here — "
                   "check whether the partner locus shares the same subject proteins; record the link below."
                   if bp_here else
                   "- [ ] **BLASTp follow-up** (aids RG-GMCI): no BLASTp yet for this BGC — run it, then confirm "
                   "the shared-reference proteins bridge these loci.")
        L += ["", bp_line,
              "> " + (esc(rgg_sorted[0]["guard"]) or "Homology-guided shared-reference linkage; not nucleotide-level joining.")]
    else:
        L += ["", "No split-pathway linkage proposed for this BGC (stands alone in the RG-GMCI pass)."]
    # BiGSCAPE gene-cluster family (cross-cohort integration: AS + SID + type-strain)
    L += ["", "## BiGSCAPE gene-cluster family (cross-cohort)"]
    g = gcf.get((strain, bgc))
    if g and int(g["family_size"]) > 1:
        comp_bits = f"{g['n_AS']} AS · {g['n_SID']} SID · {g['n_type']} type-strain"
        if int(g["n_mibig"]) > 0:
            comp_bits += f" · MIBiG: {esc(g['mibig_refs'])}"
        L += ["", f"Family **{g['family_id']}** (`{g['qualified_family_id']}`) — {g['family_size']} members ({comp_bits}).",
              "", f"**Shares this family with:** {esc(g['cross_members']) or '—'}", ""]
        if g["n_SID"] != "0" and g["n_type"] == "0":
            L.append("_Cohort signal: clusters with SID (Hymenoptera-associated) isolates but no reference "
                     "type strain — a candidate host-associated–specific family._")
        L.append(f"> BiGSCAPE GCF at cutoff {g['normalized_cutoff']} (qualified namespace). Same family = similar architecture, "
                 "not the same compound.")
    elif g:
        L += ["", f"Family of 1 — not clustered with any other cohort BGC at cutoff {g['normalized_cutoff']} "
              "(architecturally distinct within AS+Type+SID)."]
    else:
        L += ["", "Not present in the BiGSCAPE cohort run (below its length cutoff, or not indexed)."]
    # judgment stubs
    L += ["", "## Judgment (deferred — Sapote / wet-lab)", "",
          "- [ ] **Product-class hypothesis:** ",
          "- [ ] **Novelty call** (vs KCB / MIBiG): ",
          "- [ ] **Priority** (isolate / express / deprioritize): ",
          "- [ ] **BLASTp / expression notes:** ",
          "- [ ] **Cross-strain link** (same domain-combo elsewhere? see AS_bgc_domain_signatures.csv): ",
          "",
          "---",
          "_Capacity-level, claim-safe: domain/gene calls are antiSMASH annotations (facts). Architecture "
          "counts, composition, and priors are deterministic; any product or activity reading is a hypothesis "
          "to be tested. Mamey extracts._"]
    return "\n".join(L) + "\n"


def process_strain(strain: str, pkg: str, ref: dict, blastp_all: dict, gcf: dict, meta_all: dict,
                   out_root: str = None) -> int:
    dd = load_domains_csv(strain, pkg)
    rggmci = load_rggmci(pkg)
    cblast = load_clusterblast(pkg)
    conv = load_convergence(pkg)
    conv_layer = convergence_layer_present(pkg)
    boards = load_lead_boards(pkg)
    blastp = blastp_all.get(strain, {})
    meta = meta_all.get(strain, {})
    recs = load_package(pkg)
    out_dir = os.path.join(out_root or os.path.join(pkg, "modeb_cards"), strain)
    os.makedirs(out_dir, exist_ok=True)
    idx = [f"# Mode-B cards — {strain} ({len(recs)} BGCs)", "",
           "| BGC | class | kb | composition | novelty | lead | RG-GMCI | KCB top |",
           "|---|---|---:|---|---|---|---|---|"]
    # v9.7.343: surface the engine's capacity verdicts (triage board + Diagnostic-Rescue).
    try:
        from . import card_verdicts as _cv
    except Exception:
        _cv = None
    for rec in sorted(recs, key=lambda r: (re.sub(r"\D", "", r.bgc).zfill(4))):
        rgg = rggmci.get(rec.bgc, [])
        vblock = _cv.render_block(pkg, rec.bgc) if _cv else ""
        c = card(strain, rec, dd, ref, rgg, cblast, blastp, gcf, meta, boards.get(rec.bgc, {}),
                 conv=conv.get(rec.bgc, []), conv_layer=conv_layer, verdict_block=vblock)
        # Atomic write (.tmp + os.replace): a killed process (SIGKILL/OOM/power loss) must never
        # leave a truncated/empty card overwriting a previously-valid one on disk.
        card_path = os.path.join(out_dir, f"{strain}_{rec.bgc}_card.md")
        _tmp = card_path + ".tmp"
        with open(_tmp, "w", encoding="utf-8") as fh:
            fh.write(c)
        os.replace(_tmp, card_path)
        cats = set()
        for _l, dom in dd.get(rec.bgc, {}).get("domains", []):
            cats.add(ref.get(dom, ("other",))[0])
        comp, _ = composition(cats, rec.cls)
        kcb = (rec.kcb_top or "").replace("|", "·").strip() or "—"
        best = next((p["partner"] for p in sorted(rgg, key=lambda p: -int(re.sub(r"\D", "", p["score"] or "0") or 0))
                     if "HIGH" in (p["confidence"] or "").upper()), "")
        rgg_cell = f"HIGH→{best}" if best else ("candidate" if rgg else "—")
        idx.append(f"| [{rec.bgc}]({strain}_{rec.bgc}_card.md) | {rec.cls} | {rec.len_kb:.0f} | "
                   f"{comp} | {rec.novelty or '—'} | {rec.lead_tier or '—'} | {rgg_cell} | {kcb[:40]} |")
    # Atomic write (.tmp + os.replace): same crash-safety as the per-card writes above.
    readme_path = os.path.join(out_dir, "README.md")
    _tmp = readme_path + ".tmp"
    with open(_tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(idx) + "\n")
    os.replace(_tmp, readme_path)
    return len(recs)


def emit_cards_for_package(package_dir: str, out_root: str = None, reference: str = None,
                           gcf_csv: str = None, strain_meta=None) -> int:
    """Emit compact per-BGC Mode-B data cards for ONE sealed package. Degrades gracefully: domains
    come from the package (BLUE_01), external enrichments (reference/gcf/blastp/meta) resolve to
    empty when not supplied. Returns the number of cards written."""
    pkg = str(package_dir)
    strain = strain_of(pkg)
    ref = load_reference(reference) if (reference and os.path.exists(reference)) else {}
    gcf = load_gcf(gcf_csv)
    meta_all = dict(strain_meta or {})
    return process_strain(strain, pkg, ref, {}, gcf, meta_all, out_root=out_root)


def register_subparser(sub):
    """Register the `emit-modeb-cards` post-seal subcommand (called from cli.py).

    Complementary to `emit-modeb-template` (the full §1-§48 authoring scaffold): this emits Blue's
    compact, auto-filled per-BGC DATA card (composition tag, RG-GMCI split-pathway banner, auto-
    priors, architecture domain-counts) for triage/quick-look. Non-blocking; reads a sealed package.
    """
    mc = sub.add_parser("emit-modeb-cards",
                        help="compact auto-filled per-BGC Mode-B data cards for a sealed package "
                             "(composition, RG-GMCI banner, priors, architecture counts); non-blocking")
    mc.add_argument("--package", required=True, help="sealed package dir")
    mc.add_argument("--out", default=None, dest="out_root",
                    help="output dir (default: <package>/modeb_cards/)")
    mc.add_argument("--reference", default=None,
                    help="optional domain_reference.tsv (domain->category); without it domains group as 'other'")
    mc.add_argument("--gcf-csv", default=None, dest="gcf_csv",
                    help="optional precomputed bgc_gcf.csv for GCF membership")
    mc.set_defaults(func=run_from_args)
    return mc


def run_from_args(args) -> int:
    n = emit_cards_for_package(args.package, out_root=getattr(args, "out_root", None),
                               reference=getattr(args, "reference", None),
                               gcf_csv=getattr(args, "gcf_csv", None))
    dest = getattr(args, "out_root", None) or os.path.join(args.package, "modeb_cards")
    emit(f"emit-modeb-cards: {n} card(s) -> {dest}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit compact deterministic Mode-B data cards per BGC")
    ap.add_argument("--package", required=True, help="sealed package dir")
    ap.add_argument("--out", default=None, dest="out_root")
    ap.add_argument("--reference", default=None)
    ap.add_argument("--gcf-csv", default=None, dest="gcf_csv")
    return run_from_args(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())

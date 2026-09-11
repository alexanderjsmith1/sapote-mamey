"""Mamey deterministic enrichment-section generators (Mode B §11-§20).

Each card must carry >= MIN_ENRICHMENT_CHARS of combined §11-§20 content (enforced by
mode_b_quality_gate). These generators draft enrichment sections deterministically from
the gene table + manifest so the floor is always reachable from data, never padded prose.

Design contract (per the genome-wide coverage analysis on the validation strains):
  - Two sections are TRUE catch-alls (fire on every card with >=1 domain-bearing gene):
        emit_rarest_genes / emit_rarest_domains  (rarity-ranked, genome-wide frequency)
        emit_domain_inventory                    (full domain census)
  - Broad sections fire on most cards:
        emit_nrps_pks_typing      (NRPS/PKS cards)
        emit_peptide_precursor    (RiPP / short-ORF cards)
  - Class-specific sections fire where the substrate exists (N/A otherwise, honestly):
        emit_substrate_audit (A-domains), emit_phylo_placement (core enzyme),
        emit_expression_design (Interior), emit_halogenase_subtyping (halogenase)

The card composer calls applicable generators until the combined block clears the floor,
preferring the most informative applicable sections first. Sections that don't apply
return an explicit N/A stub (short) that is NOT counted toward the floor — only authored
content counts. Every card can always reach the floor via the catch-alls.

This is the deterministic (Mamey) layer; Sapote may expand any drafted section with
judgment-layer interpretation, but the floor is reachable without it.
"""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from dataclasses import dataclass


# Domains that are ubiquitous NRPS/PKS machinery — not "interesting" as rare markers.
_COMMON_MACHINERY = frozenset({
    "PP-binding", "AMP-binding", "AMP-binding_C", "PCP", "Condensation",
    "NRPS-A_a3", "NRPS-A_a6", "NRPS-A_a8", "NRPS-A_a2", "ACP", "Acyl_transf_1",
    "Ketoacyl-synt", "Ketoacyl-synt_C", "PKS_KS", "PKS_AT", "KR", "PKS_KR",
})
_HALOGENASE_KEYS = ("halogenase", "Trp_halogenase", "Flavin_halogen")
# NOTE: 'thio' as a bare substring false-matches Thioesterase/Thioredoxin/thiolation (all common,
# non-RiPP). Anchored to the specific RiPP thio-class forms instead (Patch Chat fix, v9.7.112).
_RIPP_PRECURSOR_KEYS = ("leader", "precursor", "lanthi", "lasso", "sacti", "thiopeptide",
                        "thioamitide", "RiPP", "ranthi", "Nif11", "LanC", "LanB", "YcaO", "PqqD")
_NRPS_PKS_KEYS = ("AMP-binding", "Condensation", "Ketoacyl", "PKS", "Acyl_transf",
                  "C2_LCL", "C1_LCL", "C2_DCL", "KAsynt", "NRPS-A")


@dataclass(frozen=True)
class Gene:
    locus: str
    domains: tuple[str, ...]
    aa: int


def parse_genes(rows) -> list[Gene]:
    """rows: iterable of dicts with locus_tag, sec_met_domains, aa_length."""
    out = []
    for r in rows:
        d = (r.get("sec_met_domains") or "").strip()
        if d in ("—", "", "None"):
            continue
        doms = tuple(x.strip() for x in d.split(";") if x.strip())
        if not doms:
            continue
        lt = (r.get("locus_tag") or "").strip()
        if not lt:
            continue  # EVAL-P04: skip a row with no locus_tag (was r["locus_tag"] -> KeyError past the try/except)
        # EVAL-P09: tolerate non-numeric aa_length ("123 aa", "1,024") instead of crashing int()
        aa = int("".join(ch for ch in str(r.get("aa_length") or "0") if ch.isdigit()) or "0")
        out.append(Gene(lt, doms, aa))
    return out


def genome_domain_frequency(all_genes_by_bgc: dict[str, list[Gene]]) -> Counter:
    """Genome-wide domain-family instance counts, so 'rarest' is data-grounded."""
    freq = Counter()
    for genes in all_genes_by_bgc.values():
        for g in genes:
            for dm in g.domains:
                freq[dm] += 1
    return freq


# ---------------------------------------------------------------------------
# Catch-all sections (fire on every card with >=1 domain-bearing gene)
# ---------------------------------------------------------------------------

def emit_rarest_genes(genes: list[Gene], freq: Counter, n: int = 3) -> str:
    """§ Rarest genes — the 1-3 genes carrying the least common domain content.

    v9.7.116: housekeeping singletons (ribosomal proteins, EF-G, DNA helicases, CRISPR-Cas,
    glycogen/menaquinone/MEP-isoprenoid enzymes — genome-unique by single-copy, not by biosynthetic
    distinctiveness) are down-weighted via a secondary sort key, so a genuine catalytic singleton
    always ranks above a co-captured housekeeping gene at the same genome frequency. Nothing is
    dropped — the ranking just stops surfacing ribosomal proteins as the "rarest" finding.
    """
    if not genes:
        return ""
    from .singleton_filter import classify_singleton

    def _is_housekeeping(g: Gene) -> bool:
        # a gene is housekeeping-only if NONE of its domains survive the biosynthetic-relevance filter
        return not any(classify_singleton(dm).biosynthetic_relevant for dm in g.domains)

    # score each gene by (housekeeping-last, rarity of its rarest domain): genuine biosynthetic
    # singletons sort first; among equals, the rarer (lower genome count) ranks higher.
    def gene_rank(g: Gene):
        rarity = min((freq.get(dm, 1) for dm in g.domains), default=9999)
        return (_is_housekeeping(g), rarity)
    ranked = sorted(genes, key=gene_rank)[:n]
    parts = ["§ Rarest genes. The least common domain content in this cluster (by "
             "genome-wide domain frequency, biosynthetic singletons prioritised over co-captured "
             "housekeeping) is carried by:"]
    for g in ranked:
        rarest = min(g.domains, key=lambda d: freq.get(d, 1))
        ct = freq.get(rarest, 1)
        scope = ("unique to this gene across the genome" if ct == 1
                 else f"seen in only {ct} genes genome-wide")
        parts.append(f"  {g.locus} ({g.aa} aa) — carries {rarest} ({scope}); "
                     f"full domain set: {', '.join(g.domains)}.")
    return "\n".join(parts)


def emit_rarest_domains(genes: list[Gene], freq: Counter, n: int = 3) -> str:
    """§ Rarest domains — the 1-3 least common domain families in the cluster.

    v9.7.116: housekeeping domains are down-weighted (secondary sort) so a genome-unique catalytic
    domain ranks above a co-captured housekeeping family at the same frequency.
    """
    if not genes:
        return ""
    from .singleton_filter import classify_singleton
    local = {}
    for g in genes:
        for dm in g.domains:
            local.setdefault(dm, g.locus)
    # housekeeping-last, then by genome-wide rarity
    ranked = sorted(local, key=lambda d: (not classify_singleton(d).biosynthetic_relevant,
                                          freq.get(d, 1)))[:n]
    parts = ["§ Rarest domains. Ranked by genome-wide frequency (biosynthetic singletons prioritised "
             "over co-captured housekeeping), the most distinctive domain families present are:"]
    for dm in ranked:
        ct = freq.get(dm, 1)
        scope = ("a genome-unique singleton" if ct == 1 else f"{ct} occurrences genome-wide")
        parts.append(f"  {dm} on {local[dm]} ({scope}).")
    return "\n".join(parts)


def emit_domain_inventory(genes: list[Gene]) -> str:
    """§ Domain inventory — full census of catalytic/accessory domains (true catch-all)."""
    if not genes:
        return ""
    cnt = Counter()
    for g in genes:
        for dm in g.domains:
            cnt[dm] += 1
    catalytic = [d for d in cnt if d not in _COMMON_MACHINERY]
    top = sorted(cnt.items(), key=lambda x: -x[1])[:12]
    body = ", ".join(f"{d} (x{c})" if c > 1 else d for d, c in top)
    out = ("§ Domain inventory. This cluster carries "
           f"{len(genes)} domain-bearing genes spanning {len(cnt)} domain families. "
           f"Most-represented: {body}. "
           f"Of these, {len(catalytic)} families sit outside the common NRPS/PKS carrier "
           "machinery and represent the cluster's specific tailoring/structural content.")
    # For small clusters (where the top-12 census is the whole picture), add a per-gene functional
    # line so the inventory is a complete locus-by-locus map — also keeps the catch-all reliably
    # above the enrichment floor on clusters with few genes.
    if len(genes) <= 12:
        out += " Per-gene domain content: " + "; ".join(
            f"{g.locus} → {', '.join(g.domains)}" for g in genes) + "."
    return out


# ---------------------------------------------------------------------------
# Broad sections
# ---------------------------------------------------------------------------

def emit_nrps_pks_typing(genes: list[Gene]) -> str:
    """§ NRPS/PKS typing — module architecture where adenylation/KS machinery exists."""
    a_doms = [g for g in genes if any("AMP-binding" in d or "NRPS-A" in d for d in g.domains)]
    ks_doms = [g for g in genes if any("Ketoacyl" in d or "PKS_KS" in d or "KAsynt" in d
                                       for d in g.domains)]
    at_doms = [g for g in genes if any("Acyl_transf" in d for d in g.domains)]
    if not (a_doms or ks_doms):
        return ""
    bits = ["§ NRPS/PKS typing. "]
    if a_doms:
        biggest = max(a_doms, key=lambda g: g.aa)
        bits.append(f"{len(a_doms)} adenylation-bearing gene(s); the largest is {biggest.locus} "
                    f"({biggest.aa} aa), the principal assembly-line module. ")
    if ks_doms:
        bits.append(f"{len(ks_doms)} ketosynthase-bearing PKS gene(s)"
                    + (f", with {len(at_doms)} acyltransferase(s) for extender selection. "
                       if at_doms else ". "))
    arch = ("hybrid PKS-NRPS" if a_doms and ks_doms else
            "NRPS" if a_doms else "PKS")
    bits.append(f"Architecture class: {arch}. Module count constrains the predicted product "
                "length; specificity codes would refine the monomer set (see substrate audit).")
    return "".join(bits)


def emit_peptide_precursor(genes: list[Gene], products: str) -> str:
    """§ Peptide-precursor scan — RiPP precursors / short ORFs."""
    short = [g for g in genes if g.aa and g.aa <= 100]
    ripp_like = [g for g in genes
                 if any(any(k.lower() in d.lower() for k in _RIPP_PRECURSOR_KEYS)
                        for d in g.domains)]
    is_ripp = "ripp" in products.lower() or "lanthi" in products.lower()
    if not (short or ripp_like or is_ripp):
        return ""
    bits = ["§ Peptide-precursor scan. "]
    if ripp_like:
        bits.append(f"{len(ripp_like)} gene(s) carry RiPP-maturation/precursor-associated "
                    f"domains ({', '.join(g.locus for g in ripp_like[:4])}). ")
    if short:
        bits.append(f"{len(short)} short ORF(s) (<=100 aa) are candidate precursor peptides; "
                    "the smallest are the likeliest core-peptide carriers. ")
    bits.append("Precursor identification is the entry point for a RiPP structure prediction; "
                "leader/core boundary and modification motifs would be read from the precursor.")
    return "".join(bits)


# ---------------------------------------------------------------------------
# Class-specific sections (N/A is honest; not counted toward floor)
# ---------------------------------------------------------------------------

def emit_halogenase_subtyping(genes: list[Gene]) -> str:
    """§ Halogenase subtyping — fires only where a halogenase domain exists."""
    hal = [g for g in genes if any(any(h.lower() in d.lower() for h in _HALOGENASE_KEYS)
                                   for d in g.domains)]
    if not hal:
        return ""
    parts = ["§ Halogenase subtyping. This cluster encodes halogenation capacity:"]
    for g in hal:
        which = next((d for d in g.domains if any(h.lower() in d.lower()
                                                  for h in _HALOGENASE_KEYS)), "halogenase")
        parts.append(f"  {g.locus} ({g.aa} aa) — {which}; flavin-dependent tryptophan/"
                     "phenol halogenases predict a chlorinated/brominated congener "
                     "(diagnostic isotope envelope in MS).")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Composer — assemble enrichment block until the floor is cleared
# ---------------------------------------------------------------------------

def compose_enrichment(genes: list[Gene], freq: Counter, products: str,
                       floor: int = 1000) -> tuple[str, list[str]]:
    """Assemble §11-§20 enrichment from applicable generators until >= floor chars.

    Returns (enrichment_text, section_names_used). Ordering principle: the universal
    rarity anchors lead (they always have content and are genuinely informative), then
    rare-but-present class-specific sections (halogenase, peptide-precursor) which are
    distinctive when they fire, then broad typing, then the generic domain-inventory
    filler last. This ensures a distinctive feature (e.g. a halogenase) is never dropped
    merely because an earlier generic section already cleared the floor.
    """
    candidates = [
        # universal anchors first — always present, genuinely informative
        ("rarest_domains",    emit_rarest_domains(genes, freq)),
        ("rarest_genes",      emit_rarest_genes(genes, freq)),
        # rare-but-present class-specific sections — distinctive when they fire
        ("halogenase_subtyping", emit_halogenase_subtyping(genes)),
        ("peptide_precursor", emit_peptide_precursor(genes, products)),
        # broad typing
        ("nrps_pks_typing",   emit_nrps_pks_typing(genes)),
        # generic filler last
        ("domain_inventory",  emit_domain_inventory(genes)),
    ]
    used, blocks, total = [], [], 0
    for name, text in candidates:
        if not text:
            continue
        used.append(name)
        blocks.append(text)
        total += len(text)
        if total >= floor:
            break
    # v9.7.122 (SM-P0-001 fix): the generators emit unnumbered "§ Name." headers, but the
    # quality gate's enrichment detector (_RE_ENRICHMENT_HEAD) only counts numbered §11–§20
    # headers. Without numbering, _enrichment_chars() returns (0,0) and every compose_enrichment
    # card silently fails the §11–§20 floor despite carrying full content. Number each block's
    # leading "§ " into its §11.. slot at compose time.
    numbered = []
    for i, block in enumerate(blocks):
        numbered.append(re.sub(r'^§ ', f'§{11 + i} ', block, count=1))
    return "\n\n".join(numbered), used


def genes_for_bgc(package_dir, bgc_id: str) -> list:
    """Read the gene rows for one BGC from the package gene-by-gene table → list[Gene].

    Returns [] if the table is absent or the BGC has no domain-bearing genes. Used by
    augment_enrichment() to drive the deterministic generators at card-write time.
    """
    import csv as _csv
    from pathlib import Path as _Path
    pkg = _Path(package_dir)
    candidates = sorted(pkg.glob("*_gene_by_gene_all_bgcs.csv"))
    if not candidates:
        return []
    rows = []
    try:
        with open(candidates[0], newline="", encoding="utf-8") as f:
            for r in _csv.DictReader(f):
                if (r.get("bgc_id") or "").strip() == bgc_id:
                    rows.append(r)
    except Exception:
        return []
    return parse_genes(rows)


def augment_enrichment(package_dir, bgc_id: str, products: str = "", floor: int = 2000) -> str:
    """Deterministic §11–§20 enrichment for one BGC, drawn from the package gene table.

    v9.7.125 (the BGC028/BGC023 secondary finding): HIGH-tier cards whose hand-authored §11–§20
    fell below the FULL floor can append this generator content to clear the floor honestly —
    the rarest-domain/rarest-gene/inventory census is real data, not padding. Returns "" if no
    gene table or no domain-bearing genes (the caller then leaves the card as-authored).

    The numbering is offset-aware via compose_enrichment, but a card that already has authored
    §11–§20 should append this under a clearly-labelled deterministic block; the caller decides
    placement. Here we just return the composed text.
    """
    genes = genes_for_bgc(package_dir, bgc_id)
    if not genes:
        return ""
    # genome-wide frequency needs all BGCs' genes for a real "rarest" ranking
    import csv as _csv
    from pathlib import Path as _Path
    pkg = _Path(package_dir)
    all_by_bgc: dict[str, list] = {}
    candidates = sorted(pkg.glob("*_gene_by_gene_all_bgcs.csv"))
    if candidates:
        try:
            rows_by_bgc: dict[str, list] = {}
            with open(candidates[0], newline="", encoding="utf-8") as f:
                for r in _csv.DictReader(f):
                    rows_by_bgc.setdefault((r.get("bgc_id") or "").strip(), []).append(r)
            all_by_bgc = {k: parse_genes(v) for k, v in rows_by_bgc.items()}
        except Exception:
            all_by_bgc = {bgc_id: genes}
    freq = genome_domain_frequency(all_by_bgc or {bgc_id: genes})
    text, _used = compose_enrichment(genes, freq, products, floor=floor)
    return text

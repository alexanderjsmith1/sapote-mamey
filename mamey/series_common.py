#!/usr/bin/env python3
"""Figure Series — shared loader + palette (Blue, 2026-07-18).

One rich per-BGC record feeds the whole "BGC Contig Map" series (1a → 3c). Each figure script imports
`load_package()` and renders a different view/encoding of the SAME data, so variations are cheap and
consistent. Stdlib only; claim-safe (positions/lengths/counts are facts; AB/AF/novelty are auto-priors,
not measurements). Later tiers (2x domains, 3x interpretation) already have their channels here.

Record fields (see BGCRecord): bgc, contig, contig_len, start, end, len_kb, cls, is_edge,
ab, af, novelty, lead_tier, kcb_top, n_core, domains (ordered per-core domain tokens).
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field

NODE_LEN_RE = re.compile(r"length_(\d+)")

# class -> colour, aligned with the mamey 8m legend family (fallback grey)
CLASS_COLOR = {
    "PKS": "#2e7d4f", "terpene": "#b5732a", "NRPS": "#3d6fa8", "phosphonate": "#b23b3b",
    "RiPP": "#7d4f9e", "ectoine": "#c0559b", "RRE-containing": "#4a3f7a", "NI-siderophore": "#ff6f6f",
    "butyrolactone": "#f5a623", "melanin": "#0d3b52", "NRP-metallophore": "#7fae6a",
    "other": "#8a6d3b", "hydrogen-cyanide": "#6b6fa8", "lanthipeptide": "#7d4f9e",
}
CLASS_FALLBACK = "#9e9e9e"

# comparison-set palette + order (for faceting cohort figures by strain_set)
SET_COLOR = {"AS": "#c0392b", "SID": "#2e7d4f", "type-strain": "#2c6fa8", "other": "#888888"}
SET_ORDER = ["AS", "SID", "type-strain", "other"]


def set_rank(s: str) -> int:
    return SET_ORDER.index(s) if s in SET_ORDER else len(SET_ORDER)


# non-actinomycete genera that appear in the comparison set as ecological outgroups (bee/ant-associated
# fungi + non-Actinobacteria) — excluded from the actinomycete BGC figures. Blocklist model: the set is
# curated actinomycetes + a few named outgroups, so unknown/new genera default to actinomycete.
NON_ACTINO_GENERA = {
    "leucoagaricus", "leucocoprinus", "neurospora", "aspergillus", "penicillium", "candida",
    "saccharomyces",                                   # fungi
    "oscillatoria", "nostoc", "anabaena", "synechocystis",  # cyanobacteria
    "paenibacillus", "bacillus", "melissococcus", "melissospora", "enterococcus", "lactobacillus",
    "clostridium",                                     # Firmicutes
    "deinococcus",                                     # Deinococcota
    "burkholderia", "pseudomonas", "escherichia", "serratia", "klebsiella",  # Proteobacteria
}


def full_genus(pkg: str) -> str:
    """First token of the package name = genus. AS-/SID-/AJS- isolates -> 'Streptomyces' (actinomycete)."""
    base = re.sub(r"_gene_by_gene_all_bgcs\.csv$", "", os.path.basename(_find(pkg, "_gene_by_gene_all_bgcs.csv") or ""))
    if re.match(r"(AS|SID|AJS)", base):
        return "Streptomyces"
    return base.split("_")[0]


def is_actinomycete(pkg: str) -> bool:
    return full_genus(pkg).lower() not in NON_ACTINO_GENERA


def find_packages(mc_root: str, actino_only: bool = True) -> list[str]:
    """Discover sealed package dirs under a mamey_packages root; drop non-actinomycete outgroups by
    default (Leucoagaricus, Deinococcus, the bee-pathogen Firmicutes, cyanobacteria, fungi)."""
    pkgs = sorted({os.path.dirname(gt) for gt in
                   glob.glob(os.path.join(mc_root, "*", "**", "*_gene_by_gene_all_bgcs.csv"), recursive=True)})
    return [p for p in pkgs if is_actinomycete(p)] if actino_only else pkgs


@dataclass
class BGCRecord:
    bgc: str
    contig: str = ""
    contig_len: int = 0
    start: int = 0
    end: int = 0
    len_kb: float = 0.0
    cls: str = "other"
    is_edge: bool = False
    ab: float = 0.0
    af: float = 0.0
    novelty: str = ""
    lead_tier: str = ""
    kcb_top: str = ""
    n_core: int = 0
    n_tailoring: int = 0
    n_resistance: int = 0
    n_context: int = 0
    domains: list[str] = field(default_factory=list)          # flat, all core domain tokens
    core_genes: list = field(default_factory=list)            # ordered [(locus, cds_start, [tokens])]


def _find(pkg: str, suffix: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(pkg, f"*{suffix}")))
    return hits[0] if hits else None


def _rows(path: str | None) -> list[dict]:
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="ignore", newline="") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]  # skip mamey provenance lines
    return list(csv.DictReader(lines))


def contig_len(name: str) -> int:
    m = NODE_LEN_RE.search(name or "")
    return int(m.group(1)) if m else 0


def color_for(cls: str) -> str:
    return CLASS_COLOR.get(cls, CLASS_FALLBACK)


def strain_of(pkg: str) -> str:
    """Display label for a package. AS-###/SID#### keep their ID; a Genus_species_strain comparison
    genome becomes 'G. species strain' (so the Actinomadura type strains stay distinct)."""
    base = os.path.basename(_find(pkg, "_gene_by_gene_all_bgcs.csv") or "STRAIN")
    stem = re.sub(r"_gene_by_gene_all_bgcs\.csv$", "", base)
    m = re.match(r"((?:AS|AJS|SID|PENDING)-?\d+\w*)", stem)
    if m:
        return m.group(1)
    parts = stem.split("_")
    if len(parts) >= 2 and parts[0][:1].isupper() and parts[0].isalpha():
        return f"{parts[0][0]}. " + " ".join(parts[1:])  # Genus_species_strain -> G. species strain
    return stem


def _is_core(fn: str) -> bool:
    fn = (fn or "").strip().lower()
    return "core biosynthetic" in fn or fn == "core"


def load_package(pkg: str) -> list[BGCRecord]:
    rec: dict[str, BGCRecord] = {}

    # coordinates, boundary, per-core domains, core count — from the gene table
    for r in _rows(_find(pkg, "_gene_by_gene_all_bgcs.csv")):
        b = (r.get("bgc_id") or "").strip()
        if not b:
            continue
        rr = rec.setdefault(b, BGCRecord(bgc=b, start=10**15, end=0))
        rr.contig = rr.contig or (r.get("contig") or "")
        try:
            rr.start = min(rr.start, int(r["bgc_start"]))
            rr.end = max(rr.end, int(r["bgc_end"]))
        except (ValueError, KeyError):
            pass
        if (r.get("boundary_flag") or "").strip():
            rr.is_edge = rr.is_edge or ("edge" in r["boundary_flag"].lower()
                                        or "partial" in r["boundary_flag"].lower()
                                        or "full-contig" in r["boundary_flag"].lower())
        _role = (r.get("gene_function_inference", "") or "").strip().lower()
        if "self-resistance" in _role or "resistance / export" in _role:
            rr.n_resistance += 1
        elif any(t in _role for t in ("tailoring", "chain release", "glycosylation",
                                      "maturation", "halogenation")):
            rr.n_tailoring += 1
        elif not _is_core(_role):
            rr.n_context += 1
        if _is_core(r.get("gene_function_inference", "")):
            rr.n_core += 1
            dom = (r.get("sec_met_domains") or "").strip()
            toks = [t.strip() for t in dom.replace(";", ",").split(",") if t.strip()] if dom else []
            if toks:
                rr.domains.extend(toks)
            try:
                cds = int(r.get("cds_start") or r.get("bgc_start") or 0)
            except ValueError:
                cds = 0
            rr.core_genes.append(((r.get("locus_tag") or "").strip(), cds, toks))

    # class / edge / length — from the 8m figure data (authoritative length_kb)
    for r in _rows(_find(pkg, "_8m_fig_genome_atlas_data.csv")):
        b = (r.get("bgc_id") or "").strip()
        if b in rec:
            rec[b].cls = (r.get("primary_class") or "other").strip()
            rec[b].len_kb = float(r.get("length_kb") or 0)
            e = (r.get("edge_status") or "").lower()
            rec[b].is_edge = rec[b].is_edge or ("edge" in e or "partial" in e or "full-contig" in e)

    # priority priors — from the triage board
    for r in _rows(_find(pkg, "_4_triage_board.csv")):
        b = (r.get("BGC_ID") or "").strip()
        if b in rec:
            try:
                rec[b].ab = float(r.get("AB_auto") or 0)
            except ValueError:
                pass
            try:
                rec[b].af = float(r.get("AF_auto") or 0)
            except ValueError:
                pass
            rec[b].novelty = (r.get("Novelty_auto") or "").strip()
            rec[b].lead_tier = (r.get("Lead_tier_auto") or "").strip()
            rec[b].kcb_top = (r.get("KCB_top") or "").strip()

    # finalize: contig length, fallback length, order core genes, drop coordinate-less records
    out = []
    for rr in rec.values():
        if rr.start >= 10**15:
            continue
        rr.contig_len = contig_len(rr.contig)
        if not rr.len_kb:
            rr.len_kb = (rr.end - rr.start) / 1000
        rr.core_genes.sort(key=lambda g: g[1])  # by cds_start -> positional order
        out.append(rr)
    return out


def strain_set(pkg: str) -> str:
    """Group a package by its comparison set, inferred from path + label: 'AS', 'SID', 'type-strain',
    or 'other'. Type strains live under a 'Type Strains' folder / carry a 'Genus species' label."""
    label = strain_of(pkg)
    path = pkg.replace(os.sep, "/").lower()
    if re.search(r"SID[-_ ]?\d", label) or re.match(r"SID", label) or "/sid" in path:
        return "SID"  # e.g. 'Streptomyces_sp_SID5914' -> 'S. sp SID5914', or a 'SID-####' id
    if label.startswith("AS"):
        return "AS"
    if "type strain" in path or ". " in label:  # 'A. species strain'
        return "type-strain"
    return "other"


def rggmci_high_pairs(pkg: str) -> list[tuple[str, str]]:
    """HIGH-confidence RG-GMCI split-pathway pairs (one biological BGC split across two regions)."""
    pairs = []
    for r in _rows(_find(pkg, "_4A_RGGMCI_ranked_pairs.csv")):
        conf = (r.get("rggmci_confidence") or "").upper()
        a, b = (r.get("bgc_a") or "").strip(), (r.get("bgc_b") or "").strip()
        if "HIGH" in conf and a and b:
            pairs.append((a, b))
    return pairs


def assembly_metrics(pkg: str) -> dict:
    """Real assembly QC from the sealed intake.json (genome_bp, contigs, n50, gc_pct)."""
    p = _find(pkg, "_1_intake.json")
    if not p or not os.path.exists(p):
        return {}
    try:
        d = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    a = d.get("assembly", d)
    return {k: a.get(k) for k in ("genome_bp", "contigs", "n50", "gc_pct") if isinstance(a, dict)}


def by_contig(records: list[BGCRecord]) -> dict[str, list[BGCRecord]]:
    d = defaultdict(list)
    for rr in records:
        d[rr.contig].append(rr)
    return d

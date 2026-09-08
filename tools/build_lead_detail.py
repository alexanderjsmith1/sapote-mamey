#!/usr/bin/env python3
"""
build_lead_detail.py — per-lead BGC detail extractor for the Sapote judgment layer.

Mamey produces strain-level inventory + triage; this tool drills into the NOMINATED
antifungal / antibacterial leads and emits the gene-, domain-, resistance- and
transport-level evidence the judgment layer needs to write a mechanism-aware Mode B
card, plus the corrected RG-GMCI fragment-rescue grouping for each lead.

It is designed to feed an ITERATIVE Sapote thinking step (see
docs/modules/SAPOTE_LEAD_DETAIL_MODULE.md):
  pass 1  gene inventory      (deterministic — this tool)
  pass 2  module/role assignment   (Sapote reasons over pass-1 JSON)
  pass 3  mechanism hypothesis + literature punch-card questions (Sapote)

Usage:
  python tools/build_lead_detail.py --package <pkg_dir> --gbk-dir <dir_with_region_gbks> \
        --leads BGC002,BGC031,BGC038,BGC063 [--out lead_detail.json]

Inputs it reads (all already in a Mamey package):
  <package>/manifest.json
  <package>/AS-XXX_4A_RGGMCI_full.json   (or any *RGGMCI_full.json)
  region GBKs (antiSMASH region001.gbk files) — pointed to by --gbk-dir

No network required. Deterministic.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, os, re, glob
from collections import defaultdict
import sys as _sys, os as _os


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_dump_json


# ── GBK parsing ───────────────────────────────────────────────────────────────
def parse_region_gbk(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    genes = []
    for block in txt.split("\n     CDS ")[1:]:
        loc = block.split("\n", 1)[0].strip()
        def q(name):
            m = re.search(r'/%s="([^"]*)"' % name, block, re.S)
            return re.sub(r"\s+", " ", m.group(1)).strip() if m else None
        kind = q("gene_kind") or ""
        func = q("gene_functions") or ""
        secmet = [s.strip() for s in re.findall(r'/sec_met_domain="([^"(]+)', block)]
        domains = [d.strip() for d in re.findall(r'/NRPS_PKS="Domain: ([^"(]+)', block)]
        gene = q("gene")
        # locus_tag (ctgN_M) — the identifier shown in the antiSMASH HTML viewer, so the
        # user can find the gene in the browser and pull its translation for BLASTp.
        locus_tag = q("locus_tag") or q("protein_id") or "?"
        genes.append({
            "locus_tag": locus_tag, "loc": loc[:30], "gene": gene, "kind": kind,
            "sec_met": secmet, "nrps_pks_domains": domains,
            "functions": (func or "")[:140],
        })
    return genes


# Resistance / transport / regulatory classifiers from gene evidence
RES_MARKERS = ["APH", "AAC", "beta-lactam", "betalactam", "Erm", "Van", "Fosfomycin",
               "ABC_tran", "resistance"]
def classify_genes(genes):
    biosynthetic, resistance, transport, regulatory, tailoring = [], [], [], [], []
    TAIL = {"p450", "oMT", "nMT", "cMT", "MT", "Methyltransf", "halogenase", "Trp_halogenase",
            "FkbH", "Glycos_transf", "Glyco_transf", "MGT", "RmlD", "DAO", "Aminotran"}
    for g in genes:
        sig = " ".join(g["sec_met"] + g["nrps_pks_domains"] + [g["functions"], g["kind"], g["gene"] or ""])
        low = sig.lower()
        if any(m.lower() in low for m in RES_MARKERS) and "resist" in low or any(
                m in sig for m in ["APH", "AAC"]):
            resistance.append(g)
        if "transport" in low or "ABC_tran" in sig or "MFS" in sig:
            transport.append(g)
        if "regulat" in low or "Pkinase" in sig or "TetR" in sig or "LuxR" in sig:
            regulatory.append(g)
        if g["sec_met"] or g["nrps_pks_domains"] or "biosynthetic" in g["kind"]:
            biosynthetic.append(g)
            if any(t in sig for t in TAIL):
                tailoring.append(g)
    return {"biosynthetic": biosynthetic, "tailoring": tailoring, "resistance": resistance,
            "transport": transport, "regulatory": regulatory}


# ── corrected RG-GMCI rescue grouping ────────────────────────────────────────
# FIX: rescue strength is reference + shared-protein evidence, NOT product-token
# agreement. A split cluster has DIFFERENT product annotations on each fragment
# (core on one contig, tailoring/sugar on another), so requiring a shared product
# token systematically rejects real splits. Grade on strong_supporting_references,
# complete_or_chromosome_references and max_protein_sum instead.
def rescue_groups(rggmci, min_strong=1):
    pairs = rggmci.get("ranked_pairs") or []
    def n(p, k):
        try:
            return float(p.get(k) or 0)
        except Exception:
            return 0
    strong = [p for p in pairs if n(p, "strong_supporting_references") >= min_strong]
    adj = defaultdict(list)
    nodes = set()
    for p in strong:
        a, b = p["bgc_a"], p["bgc_b"]
        nodes |= {a, b}
        adj[a].append((b, p)); adj[b].append((a, p))
    seen, comps = set(), []
    for node in nodes:
        if node in seen:
            continue
        stack, comp = [node], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x); comp.add(x)
            for y, _ in adj[x]:
                if y not in seen:
                    stack.append(y)
        comps.append(comp)
    out = []
    for comp in sorted(comps, key=len, reverse=True):
        deg = {bid: len(set(y for y, _ in adj[bid])) for bid in comp}
        # hub flag: a group with one dominant high-degree node is a hub-component
        # that may over-merge; clean 2-fragment groups are the highest-confidence splits.
        hub = max(deg.values()) if deg else 0
        edges = []
        for p in strong:
            if p["bgc_a"] in comp and p["bgc_b"] in comp:
                edges.append({"pair": p["pair"], "score": n(p, "rggmci_score"),
                              "strong_refs": n(p, "strong_supporting_references"),
                              "complete_refs": n(p, "complete_or_chromosome_references"),
                              "shared_proteins": n(p, "max_protein_sum")})
        edges.sort(key=lambda e: (-e["strong_refs"], -e["shared_proteins"], -e["score"]))
        out.append({
            "fragments": sorted(comp, key=lambda x: int(x[3:])),
            "size": len(comp),
            "degree": deg,
            "verdict": ("CLEAN_SPLIT" if len(comp) == 2 else
                        "HUB_COMPONENT_NEEDS_SUBRESOLUTION"),
            "hub_max_degree": hub,
            "top_edges": edges[:6],
        })
    return out


def lead_detail(manifest, rggmci, gbk_dir, leads):
    by_id = {b["bgc_id"]: b for b in manifest["bgcs"]}
    groups = rescue_groups(rggmci)
    group_of = {}
    for gi, g in enumerate(groups):
        for f in g["fragments"]:
            group_of[f] = gi
    # map BGC -> source gbk basename via manifest notes
    def gbk_for(b):
        for nstr in (b.get("notes") or []):
            if "source_gbk" in nstr:
                base = os.path.basename(nstr.split("=", 1)[-1])
                hits = glob.glob(os.path.join(gbk_dir, base))
                return hits[0] if hits else None
        return None
    cards = []
    for bid in leads:
        b = by_id.get(bid)
        if not b:
            cards.append({"bgc_id": bid, "error": "not in manifest"})
            continue
        gpath = gbk_for(b)
        genes = parse_region_gbk(gpath) if gpath else []
        cls = classify_genes(genes)
        gi = group_of.get(bid)
        # contig / ctg label so the lead can be found in the antiSMASH HTML and BLASTp'd
        contig = b.get("contig") or ""
        _m = re.search(r"NODE_(\d+)", contig)
        ctg = "ctg%s" % _m.group(1) if _m else None
        cards.append({
            "bgc_id": bid,
            "contig": contig,
            "ctg": ctg,                     # antiSMASH viewer prefix; locus tags are ctg_<n>
            "products": b.get("products"),
            "size_kb": round((b.get("end", 0) - b.get("start", 0)) / 1000, 1),
            "architecture_confidence": b.get("architecture_confidence"),
            "edge_status": b.get("edge_status"),
            "kcb_anchor": b.get("closest_candidate_kcb_product"),
            "mibig": b.get("closest_mibig_accession"),
            "claim_ceiling": b.get("product_claim_ceiling"),
            "pass1_gene_inventory": {
                "total_cds": len(genes),
                "biosynthetic": [{"locus_tag": g["locus_tag"], "loc": g["loc"],
                                   "domains": (g["sec_met"] + g["nrps_pks_domains"]), "gene": g["gene"]}
                                  for g in cls["biosynthetic"]],
                "tailoring": [g["locus_tag"] for g in cls["tailoring"]],
                "resistance_genes": [{"locus_tag": g["locus_tag"], "loc": g["loc"],
                                       "evidence": (g["sec_met"] + [g["functions"]])[:2]} for g in cls["resistance"]],
                "transporters": [g["locus_tag"] for g in cls["transport"]],
                "regulators": [g["locus_tag"] for g in cls["regulatory"]],
            },
            "rescue_group": gi,
            "rescue_group_fragments": groups[gi]["fragments"] if gi is not None else None,
            "rescue_verdict": groups[gi]["verdict"] if gi is not None else "NO_STRONG_RESCUE",
            # passes 2 & 3 are written by the Sapote judgment layer
            "pass2_module_roles": "TO BE COMPLETED BY SAPOTE (assign each biosynthetic gene a module/role)",
            "pass3_mechanism_and_lit_questions": "TO BE COMPLETED BY SAPOTE (mechanism hypothesis + punch-card questions)",
        })
    return {"strain_id": manifest.get("strain_id"), "rescue_groups": groups, "leads": cards}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--gbk-dir", required=True)
    ap.add_argument("--leads", required=True, help="comma-separated BGC ids")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    manifest = _read_json(os.path.join(a.package, "manifest.json"))
    rgf = glob.glob(os.path.join(a.package, "*RGGMCI_full.json"))
    rggmci = _read_json(rgf[0]) if rgf else {"ranked_pairs": []}
    leads = [x.strip() for x in a.leads.split(",") if x.strip()]
    result = lead_detail(manifest, rggmci, a.gbk_dir, leads)
    out = a.out or os.path.join(a.package, "lead_detail.json")
    atomic_dump_json(result, out, indent=2)
    emit("wrote", out)
    emit("rescue groups:", len(result["rescue_groups"]),
          "| leads detailed:", len(result["leads"]))


if __name__ == "__main__":
    main()

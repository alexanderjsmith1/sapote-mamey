#!/usr/bin/env python3
"""
build_reconstruction.py — clusterblast-scaffolded split-pathway reconstruction.

In a fragmented assembly a single BGC is routinely broken across contigs. knownclusterblast
(MIBiG) names the compound but is too sparse to ORDER the pieces. clusterblast (CB) searches
the full GenBank/RefSeq set, which contains COMPLETE-genome clusters — a complete CB
reference is a scaffold the fragments tile onto, and (because it is a fully annotated genome)
it RE-ANNOTATES query genes the draft called "hypothetical." This tool turns the raw
`clusterblast/` hit tables into a reconstruction hypothesis for a set of fragments.

It does three things the homology score alone does not:
  1. tiling          — orders each fragment's genes against a shared complete CB reference
  2. CB re-annotation — reports what the reference says each query gene is (rescues poor calls)
  3. flank census     — walks the rest of each contig ("look downstream") and states which
                        flank genes also hit the reference family vs. which are unexplained

Claim ceiling: a reconstruction HYPOTHESIS scaffolded on CB homology; not nucleotide joining.
Confirm by long-read resequencing or PCR across the contig boundary.

Usage:
  python tools/build_reconstruction.py --package <pkg> --clusterblast-dir <raw/clusterblast> \
      --gbk-dir <region_gbks> --fragments BGC013,BGC001 [--out reconstruction.md]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, json, os, re, sys


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text


def parse_cb(path):
    """Parse one clusterblast region txt -> {accession: {...}}."""
    txt = open(path, encoding="utf-8", errors="replace").read()
    refs = {}
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
                p = line.split("\t")
                # query gene is the first field; accept any locus-tag naming
                # (ctgN_M for SPAdes, or real tags like GT350_26620 for WGS genomes).
                q0 = p[0].strip()
                if len(p) >= 4 and q0 and re.match(r"^[A-Za-z][\w.]*_?\d", q0):
                    hits.append({"query": q0, "subject": p[1].strip(),
                                 "pid": p[2].strip(), "score": p[3].strip()})
        refs[acc] = {"source": (src.group(1).strip() if src else ""),
                     "type": (typ.group(1).strip() if typ else ""),
                     "cum_score": float(cum.group(1)) if cum else 0.0, "hits": hits}
    return refs


def subj_sortkey(subject):
    m = re.search(r"(\d+)$", subject)
    return int(m.group(1)) if m else 0


def gene_inventory(gbk_path):
    """All CDS on the contig (for the flank census), with locus tag + best annotation."""
    txt = open(gbk_path, encoding="utf-8", errors="replace").read()
    genes = []
    for block in txt.split("\n     CDS ")[1:]:
        def q(n):
            m = re.search(r'/%s="([^"]*)"' % n, block, re.S)
            return re.sub(r"\s+", " ", m.group(1)).strip() if m else None
        lt = q("locus_tag") or q("protein_id") or "?"
        sm = re.findall(r'/sec_met_domain="([^"(]+)', block)
        gene = q("gene")
        prod = q("product")
        label = gene or (",".join(s.strip() for s in sm) if sm else (prod or "hypothetical"))
        genes.append({"locus_tag": lt, "label": label[:60]})
    return genes


def reconstruct(package, cb_dir, gbk_dir, frag_ids):
    manifest = _read_json(os.path.join(package, "manifest.json"))
    by_id = {b["bgc_id"]: b for b in manifest["bgcs"]}
    frags = []
    for fid in frag_ids:
        b = by_id.get(fid)
        if not b:
            continue
        contig = b.get("contig") or ""
        # Derive the contig prefix robustly from the source_gbk note rather than assuming
        # NODE_ (SPAdes) naming — public WGS genomes use accession contigs (e.g. WWKJ01000828.1).
        src_base = None
        for nstr in (b.get("notes") or []):
            if "source_gbk" in nstr:
                src_base = os.path.basename(nstr.split("=", 1)[-1])
                break
        if src_base:
            prefix = re.sub(r"\.region\d+\.gbk$", "", src_base)   # WWKJ01000828.1  or  NODE_182_len...
        else:
            prefix = contig
        m = re.search(r"NODE_(\d+)", contig)
        ctg = "ctg" + m.group(1) if m else (prefix.split(".")[0] if prefix else None)
        cbp = glob.glob(os.path.join(cb_dir, "%s_*.txt" % prefix)) if prefix else []
        gbp = glob.glob(os.path.join(gbk_dir, "%s*.region*.gbk" % prefix)) if prefix else []
        frags.append({"bgc": fid, "node": prefix, "ctg": ctg,
                      "products": ";".join(b.get("products") or []),
                      "cb": parse_cb(cbp[0]) if cbp else {},
                      "genes": gene_inventory(gbp[0]) if gbp else []})
    # shared CB references across all fragments
    refsets = [set(f["cb"].keys()) for f in frags if f["cb"]]
    shared = set.intersection(*refsets) if len(refsets) == len(frags) and refsets else set()
    # rank shared refs by total query genes covered + summed cum_score
    def ref_strength(acc):
        cov = sum(len(f["cb"][acc]["hits"]) for f in frags)
        sc = sum(f["cb"][acc]["cum_score"] for f in frags)
        return (cov, sc)
    ranked = sorted(shared, key=ref_strength, reverse=True)
    best = ranked[0] if ranked else None
    return manifest.get("strain_id"), frags, ranked, best


def reconstruction_verdict(frags, best):
    """Overlap-fraction on shared reference-gene coverage gates the reconstruction ACCEPTANCE.

    A genuine physical split tiles COMPLEMENTARY parts of one reference (low overlap). If the two
    fragments map to overlapping reference genes, that is not a clean split (likely duplication or
    mis-pairing) and the reconstruction is demoted to NOT_SUPPORTED — coordinate-coverage grounds.
    """
    sets = [set(h["subject"] for h in f["cb"].get(best, {}).get("hits", [])) for f in frags] if best else []
    sets = [x for x in sets if x]
    if len(sets) < 2:
        return {"verdict": "RECONSTRUCTION_UNEVALUABLE_SINGLE_OR_NO_COVERAGE",
                "overlap_fraction": None, "covered": sum(len(s) for s in sets), "overlap": 0}
    overlap = set.intersection(*sets)
    smaller = min(len(s) for s in sets)
    of = round(len(overlap) / smaller, 3) if smaller else 1.0
    if of <= 0.15:
        v = "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY"
    elif of <= 0.50:
        v = "RECONSTRUCTION_WEAK_PARTIAL_OVERLAP"
    else:
        v = "RECONSTRUCTION_NOT_SUPPORTED_HIGH_REFERENCE_OVERLAP"
    return {"verdict": v, "overlap_fraction": of, "covered": sum(len(s) for s in sets), "overlap": len(overlap)}


def render(strain, frags, ranked, best):
    L = [f"# Split-pathway reconstruction — {strain}",
         "### " + " + ".join("%s (%s)" % (f["bgc"], f["ctg"]) for f in frags),
         "",
         "*clusterblast-scaffolded · CB = reconstruction geometry, KCB = identity · claim-safe*",
         ""]
    if not best:
        L.append("**No shared clusterblast reference across these fragments** — reconstruction "
                 "not supported by CB; fall back to functional-complementarity evidence only.")
        return "\n".join(L)

    # 1. shared scaffold
    L.append("## 1 · Shared clusterblast scaffold")
    L.append("")
    L.append(f"Best shared reference: **`{best}`**")
    for f in frags:
        r = f["cb"].get(best, {})
        L.append(f"- {f['bgc']} / {f['ctg']}: {len(r.get('hits', []))} genes hit "
                 f"`{best}` ({r.get('type','?')}; cum {r.get('cum_score',0):.0f}) — "
                 f"_{r.get('source','')[:60]}_")
    if len(ranked) > 1:
        L.append(f"- (also shared: {', '.join('`%s`' % a for a in ranked[1:5])})")
    L.append("")

    # 2. tiling table (ordered by reference-gene position)
    L.append("## 2 · Tiling onto the scaffold (ordered by reference-gene position)")
    L.append("")
    L.append("| reference gene (scaffold order) | query gene | %id | which fragment |")
    L.append("|---|---|---|---|")
    rows = []
    for f in frags:
        for h in f["cb"].get(best, {}).get("hits", []):
            rows.append((subj_sortkey(h["subject"]), h["subject"], h["query"], h["pid"], f["bgc"]))
    rows.sort()
    for _, subj, query, pid, frag in rows:
        L.append(f"| `{subj}` | `{query}` | {pid}% | {frag} |")
    covered = {(f["bgc"]): set(h["query"] for h in f["cb"].get(best, {}).get("hits", [])) for f in frags}
    # complementary / overlap test — overlap-fraction gates reconstruction acceptance (v9.7.22-m)
    v = reconstruction_verdict(frags, best)
    L.append("")
    L.append(f"**Tiling verdict:** fragments cover **{v['covered']}** reference genes with "
             f"**{v['overlap']}** shared (overlap-fraction {v['overlap_fraction']}) -> **{v['verdict']}**.")
    if v["verdict"] == "RECONSTRUCTION_NOT_SUPPORTED_HIGH_REFERENCE_OVERLAP":
        L.append("> Both fragments map to overlapping reference segments — NOT a clean complementary "
                 "split (likely duplication or mis-pairing). Reconstruction NOT supported on "
                 "coordinate-coverage grounds; do not assert a physical join.")
    elif v["verdict"] == "RECONSTRUCTION_WEAK_PARTIAL_OVERLAP":
        L.append("> Partial reference-coordinate overlap — inspect the shared genes before asserting a split.")
    L.append("")

    # 3. CB re-annotation of poorly-annotated query genes
    L.append("## 3 · clusterblast re-annotation (rescues poorly-annotated genes)")
    L.append("")
    L.append("Query genes the draft annotated generically, re-read against the complete reference:")
    rean = []
    for f in frags:
        glab = {g["locus_tag"]: g["label"] for g in f["genes"]}
        for h in f["cb"].get(best, {}).get("hits", []):
            lab = glab.get(h["query"], "")
            if lab in ("hypothetical", "") or "hypothetical" in lab.lower():
                rean.append(f"- `{h['query']}` (draft: {lab or 'hypothetical'}) → reference "
                            f"`{h['subject']}` at {h['pid']}% — part of the {f['cb'][best]['type']} scaffold")
    L.extend(rean if rean else ["- (no purely-hypothetical query genes among the hits)"])
    L.append("")

    # 4. flank census — "look downstream"
    L.append("## 4 · Contig-flank census (look downstream — what else is on the contig?)")
    L.append("")
    L.append("Every CDS on each contig, flagged by whether it hits the shared scaffold family. "
             "Genes that do **not** hit are stated honestly as unexplained, not assumed absent.")
    for f in frags:
        hitq = set(h["query"] for h in f["cb"].get(best, {}).get("hits", []))
        # also count hits to ANY shared/indolocarbazole-family ref, not just best
        anyq = set()
        for acc, r in f["cb"].items():
            anyq |= set(h["query"] for h in r["hits"])
        L.append(f"\n**{f['bgc']} / {f['ctg']} — {len(f['genes'])} CDS:**")
        for g in f["genes"]:
            mark = ("★ scaffold" if g["locus_tag"] in hitq else
                    ("· CB-family" if g["locus_tag"] in anyq else "  unexplained"))
            L.append(f"- `{g['locus_tag']}` [{mark}] {g['label']}")
    L.append("")
    L.append("> **Downstream check:** flank genes marked `unexplained` are the honest boundary — "
             "they may be the next pathway genes, or unrelated neighbours. The census states what "
             "the contig edge cannot resolve rather than implying nothing is there.")
    L.append("")

    # 5. claim ceiling
    L.append("## 5 · Claim ceiling")
    L.append("")
    L.append("Reconstruction **hypothesis** scaffolded on clusterblast homology — not "
             "nucleotide-level joining. Weight comes from convergence (multiple genes on each "
             "fragment hitting the same reference family) and from functional complementarity, "
             "not from any single gene. Confirm physical linkage by long-read resequencing or "
             "PCR across the contig boundary.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--clusterblast-dir", required=True)
    ap.add_argument("--gbk-dir", required=True)
    ap.add_argument("--fragments", required=True, help="comma-separated BGC ids")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    frag_ids = [x.strip() for x in a.fragments.split(",") if x.strip()]
    strain, frags, ranked, best = reconstruct(a.package, a.clusterblast_dir, a.gbk_dir, frag_ids)
    md = render(strain, frags, ranked, best)
    out = a.out or os.path.join(a.package, "reconstruction.md")
    atomic_write_text(out, md)
    emit("wrote", out)
    emit("fragments:", len(frags), "| shared CB refs:", len(ranked),
          "| best scaffold:", best)


if __name__ == "__main__":
    main()

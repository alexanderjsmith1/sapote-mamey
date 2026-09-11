#!/usr/bin/env python3
"""
build_genelevel_triage.py — Mamey deterministic pre-pass that does the gene-level heavy
lifting, so the Sapote judgment layer is *told where to look* instead of having to notice.

Two products:

  (1) MARKER FLAGS — scan every region for diagnostic biosynthetic/antimicrobial marker
      genes; any region carrying one is flagged "examine gene-by-gene", with the marker and
      its locus tag. This is the "Mamey tells Sapote there is something to examine" step.

  (2) CROSS-CONTIG CLUSTERBLAST SPLITS — find each clusterblast (CB) reference that is hit on
      MORE THAN ONE query contig, and classify it:
         SPLIT_CANDIDATE   one BGC broken across contigs (reconstruct)
         RELATED_STRAIN    a phylogenetically close reference that shares MANY separate BGCs
                           with the query — NOT a split (do not reconstruct)
      The disambiguation is the hard part the analyst flagged. Heuristic, in order:
        - a reference hit on MANY contigs (> max_contigs) → RELATED_STRAIN (it shares lots of
          loci because it is a close genome, not because one BGC fragmented);
        - if 2-3 contigs and their hit reference-genes are COMPLEMENTARY (low overlap) →
          SPLIT_CANDIDATE (each contig covers a different part of the one reference locus);
        - if the contigs hit the SAME reference genes (high overlap) → RELATED_STRAIN/paralog
          (two copies of the locus, or shared-BGC noise), not a core+tailoring split;
        - a shared KCB anchor across the contigs and contig-edge/full-contig status both
          raise the split score.

No network. Deterministic. Feeds build_reconstruction.py (for the SPLIT_CANDIDATEs) and the
Sapote gene-by-gene pass (for the MARKER FLAGS).

Usage:
  python tools/build_genelevel_triage.py --package <pkg> --clusterblast-dir <raw/clusterblast> \
      --gbk-dir <region_gbks> [--out triage.json] [--max-contigs 4]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# diagnostic markers that tell Sapote "examine this region gene-by-gene"
MARKERS = {
    "nikJ": "nikkomycin (antifungal, chitin-synthase)", "phzB": "phenazine (antibacterial)",
    "phzF": "phenazine", "tra_KS": "trans-AT PKS", "AHBA_syn": "ansamycin",
    "StrR": "aminoglycoside (StrR-regulated)", "YcaO": "thiopeptide/azole-RiPP (antibacterial)",
    "Lant_dehydr": "lanthipeptide", "DUF4135": "class-II lanthipeptide",
    "indsynth": "indolocarbazole core", "Trp_halogenase": "halogenated metabolite",
    "Condensation": "NRPS module", "PKS_KS": "modular PKS", "TauD": "non-heme halogenase",
    "MGT": "glycosyltransferase (tailoring)", "p450": "P450 (tailoring)",
}


def parse_cb(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for block in txt.split(">>")[1:]:
        acc = re.search(r"\n\s*\d+\.\s+(\S+)", block)
        if not acc:
            continue
        hits = []
        tb = block.split("Table of Blast hits")
        if len(tb) > 1:
            for line in tb[1].splitlines():
                p = line.split("\t")
                q0 = p[0].strip() if p else ""
                if len(p) >= 4 and q0 and re.match(r"^[A-Za-z][\w.]*_?\d", q0):
                    hits.append((q0, p[1].strip()))
        if hits:
            out[acc.group(1)] = hits
    return out


def scan_markers(gbk_path):
    txt = open(gbk_path, encoding="utf-8", errors="replace").read()
    found = []
    for block in txt.split("\n     CDS ")[1:]:
        lt = re.search(r'/locus_tag="([^"]*)"', block)
        lt = lt.group(1) if lt else "?"
        for mk, desc in MARKERS.items():
            # v9.7.115: match the marker as a BOUNDED TOKEN inside the qualifier value, not a bare
            # substring. The old pattern flagged 'comp450X' as p450 and 'transMGTase' as MGT. The
            # boundary treats letters/digits as word-chars (so mid-word hits are rejected) but allows
            # '_' as a separator, so legitimate forms like Cytochrome_p450_6 / sugar_MGT_1 still match.
            for vm in re.finditer(r'(?:/gene|/sec_met_domain|/NRPS_PKS)="?([^"]*)', block):
                if re.search(r'(?<![A-Za-z0-9])%s(?![A-Za-z0-9])' % re.escape(mk), vm.group(1)):
                    found.append((lt, mk, desc))
                    break
    return found


def ord_of(subject):
    nums = re.findall(r"\d+", subject)
    return int(nums[-1]) if nums else 0


def triage(package, cb_dir, gbk_dir, max_contigs):
    manifest = _read_json(os.path.join(package, "manifest.json"))
    by_contig, by_id = {}, {}
    for b in manifest["bgcs"]:
        contig = (b.get("contig") or "")
        prefix = None
        for nstr in (b.get("notes") or []):
            if "source_gbk" in nstr:
                prefix = re.sub(r"\.region\d+\.gbk$", "", os.path.basename(nstr.split("=", 1)[-1]))
        b["_prefix"] = prefix or contig
        by_contig[b["_prefix"]] = b
        by_id[b["bgc_id"]] = b

    # ---- (1) marker flags ----
    marker_flags = []
    for b in manifest["bgcs"]:
        gp = glob.glob(os.path.join(gbk_dir, "%s*.region*.gbk" % b["_prefix"]))
        if not gp:
            continue
        mk = scan_markers(gp[0])
        if mk:
            marker_flags.append({"bgc_id": b["bgc_id"], "contig": b["_prefix"],
                                  "products": b.get("products"),
                                  "kcb_anchor": b.get("closest_candidate_kcb_product"),
                                  "markers": [{"locus_tag": l, "marker": m, "meaning": d} for l, m, d in mk]})

    # ---- (2) cross-contig CB references ----
    ref_index = {}   # reference -> {contig: set(subject_genes)}
    for b in manifest["bgcs"]:
        cbp = glob.glob(os.path.join(cb_dir, "%s_*.txt" % b["_prefix"]))
        if not cbp:
            continue
        for acc, hits in parse_cb(cbp[0]).items():
            ref_index.setdefault(acc, {}).setdefault(b["_prefix"], set())
            for _q, subj in hits:
                ref_index[acc][b["_prefix"]].add(subj)

    splits, related = [], []
    candidates = []
    for acc, contigs in ref_index.items():
        if len(contigs) < 2:
            continue
        clist = sorted(contigs)
        all_subj = [s for cs in contigs.values() for s in cs]
        union = set(all_subj)
        overlap = len(all_subj) - len(union)   # repeated subject genes across contigs
        overlap_frac = overlap / max(len(all_subj), 1)
        bgcs = [by_contig[c] for c in clist if c in by_contig]
        anchors = set((x.get("closest_candidate_kcb_product") or "") for x in bgcs)
        edges = [(x.get("edge_status") or "") for x in bgcs]
        edge_bias = sum(1 for e in edges if e in ("Edge", "Full-contig")) / max(len(edges), 1)
        candidates.append({"reference": acc, "contigs": clist,
                           "bgc_ids": [by_contig[c]["bgc_id"] for c in clist if c in by_contig],
                           "contig_key": tuple(clist), "n_contigs": len(contigs),
                           "ref_genes_total": len(union), "overlap": overlap,
                           "overlap_frac": round(overlap_frac, 2),
                           "shared_kcb_anchor": (len(anchors - {""}) == 1),
                           "edge_bias": round(edge_bias, 2)})

    # how many distinct references does each contig-set hit? A contig-set homologous to MANY references
    # is matching a whole compound FAMILY (related-BGC-class), not tiling one unique split.
    from collections import Counter
    set_refcount = Counter(c["contig_key"] for c in candidates)

    for c in candidates:
        n_refs_for_set = set_refcount[c["contig_key"]]
        if c["n_contigs"] > max_contigs:
            verdict, reason = "RELATED_STRAIN", \
                "reference hit on %d contigs (> %d) — shares many loci, likely a close genome" % (c["n_contigs"], max_contigs)
        elif c["overlap_frac"] >= 0.34:
            verdict, reason = "RELATED_BGC_CLASS", \
                "contigs hit the SAME reference genes (overlap %.0f%%) — shared class core, not complementary tiling" % (100 * c["overlap_frac"])
        elif n_refs_for_set >= 3:
            verdict, reason = "RELATED_BGC_CLASS", \
                "this contig-set matches %d references of the same family — class-level homology, not a unique split" % n_refs_for_set
        elif c["n_contigs"] > 3:
            verdict, reason = "RELATED_BGC_CLASS", \
                "%d contigs on one reference — too many for a clean 2–3 fragment split" % c["n_contigs"]
        else:
            verdict = "SPLIT_CANDIDATE"
            reason = "%d contigs, complementary coverage (overlap %.0f%%, %d/%d ref-genes unique)" % (
                c["n_contigs"], 100 * c["overlap_frac"], c["ref_genes_total"] - c["overlap"], c["ref_genes_total"])
            if c["shared_kcb_anchor"]:
                reason += "; shared KCB anchor"
            if c["edge_bias"] >= 0.5:
                reason += "; contig-edge/full-contig"
        rec = {k: c[k] for k in ("reference", "contigs", "bgc_ids", "n_contigs",
                                  "ref_genes_total", "overlap", "overlap_frac",
                                  "shared_kcb_anchor", "edge_bias")}
        rec["verdict"] = verdict
        rec["reason"] = reason
        (splits if verdict == "SPLIT_CANDIDATE" else related).append(rec)
    # collapse duplicate split candidates that are the same contig-set (keep the best-supported reference)
    best = {}
    for s in splits:
        k = tuple(s["contigs"])
        if k not in best or (s["ref_genes_total"] - s["overlap"]) > (best[k]["ref_genes_total"] - best[k]["overlap"]):
            best[k] = s
    splits = sorted(best.values(), key=lambda r: (-int(r["shared_kcb_anchor"]),
                                                   -(r["ref_genes_total"] - r["overlap"])))

    return {"strain_id": manifest.get("strain_id"),
            "marker_flags": marker_flags,
            "split_candidates": splits,
            "related_refs": related,
            "summary": {"regions_flagged_for_gene_by_gene": len(marker_flags),
                        "split_candidates": len(splits),
                        "related_refs_filtered": len(related)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--clusterblast-dir", required=True)
    ap.add_argument("--gbk-dir", required=True)
    ap.add_argument("--max-contigs", type=int, default=4)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = triage(a.package, a.clusterblast_dir, a.gbk_dir, a.max_contigs)
    out = a.out or os.path.join(a.package, "genelevel_triage.json")
    with atomic_open(out, "w", encoding="utf-8") as _f:
        json.dump(res, _f, indent=2)
    emit("wrote", out)
    emit(json.dumps(res["summary"], indent=2))


if __name__ == "__main__":
    main()

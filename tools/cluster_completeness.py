#!/usr/bin/env python3
r"""cluster_completeness — is a truncated cluster incomplete by assembly, or by biology?

For a query BGC on a short/edge contig, the question that matters for every downstream claim is:
which genes are missing, and are they missing because the assembly ran off the contig (an
artifact) or because the strain genuinely lacks them (biology)? This answers it against one or
more complete reference clusters, and — unlike a raw ortholog matrix — it is *truncation-aware*:
it looks at WHERE the query's genes map onto the reference, so a gap all on one side of an
edge/full-contig cluster reads as truncation, while a gap in the interior reads as real loss.

    cluster_completeness.py \
        --query "AS-XXX_BGC008:query.gbk" --query-boundary full-contig \
        --reference "x-80:x80.gbk" --reference "NPDC08785:npdc.gbk" \
        --outdir OUT

A gene is a "cluster gene" if present in >= half the references (robust to flanking singletons).
Completeness = cluster genes with a query ortholog / cluster genes. Missing cluster genes are
reported with their functional label and their position in the reference; if the query is
edge/full-contig and the missing genes sit at a reference end, the report flags likely truncation
and states the capacity the complete cluster would add. Capacity/architecture-level — homology,
not product identity.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, json, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path


# ---- alignment core (global identity, clinker-consistent; shared discipline) ------------------
def _aligner():
    from Bio import Align
    from Bio.Align import substitution_matrices
    a = Align.PairwiseAligner()
    a.substitution_matrix = substitution_matrices.load("BLOSUM62")
    a.open_gap_score = -11; a.extend_gap_score = -1; a.mode = "global"
    return a


def _gid(al, s1, s2):
    aln = al.align(s1, s2)[0]
    a, b = aln[0], aln[1]
    length = len(a); m = 0
    for x, y in zip(a, b):
        if x == y and x not in "-.":
            m += 1
        elif x == y:
            length -= 1
    return 100 * m / length if length else 0


def _genes(gbk):
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    out = []
    for rec in SeqIO.parse(str(gbk), "genbank"):
        for i, f in enumerate(rec.features):
            if f.type == "CDS" and "translation" in f.qualifiers:
                lab = (f.qualifiers.get("gene", [None])[0]
                       or (f.qualifiers.get("sec_met_domain", [None])[0] or "").split("(")[0].strip()
                       or None)
                out.append({"tag": f.qualifiers.get("locus_tag", ["orf"])[0],
                            "aa": f.qualifiers["translation"][0], "label": lab,
                            "start": int(f.location.start)})
    return out


def assess(query_genes, references, min_id=30.0):
    """references: list of (label, genes). Returns completeness report dict."""
    al = _aligner()
    # 1) reference consensus cluster: cluster genes = ref genes with an ortholog in >= half the refs
    #    Represent each reference gene by whether it recurs across references, and its position rank.
    nref = len(references)
    # build cross-reference ortholog groups (single linkage) to find recurrent cluster genes
    ref_flat = [(ri, gi, g) for ri, (_, gs) in enumerate(references) for gi, g in enumerate(gs)]
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b): parent[find(a)] = find(b)
    for i in range(len(ref_flat)):
        ri, gi, gi_g = ref_flat[i]
        for j in range(i + 1, len(ref_flat)):
            rj, gj, gj_g = ref_flat[j]
            if ri == rj:
                continue
            if _gid(al, gi_g["aa"], gj_g["aa"]) >= min_id:
                union((ri, gi), (rj, gj))
    groups = {}
    for ri, gi, g in ref_flat:
        groups.setdefault(find((ri, gi)), []).append((ri, gi, g))
    # recurrent cluster genes: in a STRICT MAJORITY of references (both, when there are two),
    # so flanking/genome-context singletons present in only one reference are excluded
    thresh = 1 if nref == 1 else nref // 2 + 1
    cluster_genes = []
    for root, members in groups.items():
        rset = set(ri for ri, _, _ in members)
        if len(rset) >= thresh:
            rep = members[0][2]
            label = next((g["label"] for _, _, g in members if g["label"]), rep["tag"])
            # per-reference position, so we can order in a single coherent frame later
            pos_by_ref = {ri: g["start"] for ri, _, g in members}
            cluster_genes.append({"label": label, "rep_aa": rep["aa"],
                                  "n_refs": len(rset), "pos_by_ref": pos_by_ref})
    # 2) does the query have an ortholog of each cluster gene?
    for cg in cluster_genes:
        cg["query_id"] = round(max((_gid(al, cg["rep_aa"], q["aa"]) for q in query_genes), default=0), 1)
        cg["present_in_query"] = cg["query_id"] >= min_id
    present = [cg for cg in cluster_genes if cg["present_in_query"]]
    missing = [cg for cg in cluster_genes if not cg["present_in_query"]]
    n = len(cluster_genes)
    completeness = round(100 * len(present) / n, 1) if n else 0
    # 3) truncation-awareness via CONTIGUITY in a single reference frame.
    #    Order cluster genes by position in the reference that contains the most of them, then
    #    check whether missing genes fall OUTSIDE the span of present genes (ends -> truncation)
    #    or BETWEEN present genes (interior -> real loss / divergence).
    interior_missing = end_missing = 0
    if missing and present:
        counts = [sum(1 for cg in cluster_genes if ri in cg["pos_by_ref"]) for ri in range(nref)]
        frame = max(range(nref), key=lambda ri: counts[ri]) if nref else 0
        framed = [cg for cg in cluster_genes if frame in cg["pos_by_ref"]]
        framed.sort(key=lambda cg: cg["pos_by_ref"][frame])
        pres_idx = [i for i, cg in enumerate(framed) if cg["present_in_query"]]
        if pres_idx:
            lo_i, hi_i = min(pres_idx), max(pres_idx)
            for i, cg in enumerate(framed):
                if not cg["present_in_query"]:
                    if lo_i < i < hi_i:
                        interior_missing += 1
                    else:
                        end_missing += 1
    edge_like = missing and interior_missing == 0   # all missing genes at the ends
    return {"n_cluster_genes": n, "n_present": len(present), "n_missing": len(missing),
            "completeness_pct": completeness,
            "present": [{"label": p["label"], "n_refs": p["n_refs"], "query_id": p["query_id"]} for p in present],
            "missing": [{"label": m["label"], "n_refs": m["n_refs"], "query_id": m["query_id"]} for m in missing],
            "interior_missing": interior_missing, "end_missing": end_missing,
            "missing_end_loaded": bool(edge_like)}


def tier(pct):
    return ("near-complete" if pct >= 85 else "substantial" if pct >= 60
            else "partial" if pct >= 35 else "fragment")


def interpret(report, query_label, query_boundary, ref_labels):
    pct = report["completeness_pct"]
    lines = [f"{query_label} carries {report['n_present']}/{report['n_cluster_genes']} "
             f"of the reference cluster genes ({pct}% — {tier(pct)}), measured against "
             f"{', '.join(ref_labels)}."]
    if report["missing"]:
        mnames = ", ".join(m["label"][:26] for m in report["missing"])
        lines.append(f"Missing: {mnames}.")
    else:
        lines.append("No reference cluster gene is missing from the query.")
    trunc = (query_boundary or "").lower() in ("edge", "full-contig", "full_contig")
    if report["missing"]:
        im, em = report.get("interior_missing", 0), report.get("end_missing", 0)
        if trunc and report["missing_end_loaded"]:
            lines.append(
                f"The query is annotated '{query_boundary}' and all {em} missing gene(s) fall at the "
                f"ends of the reference cluster, outside the span of genes the query does have — "
                f"consistent with TRUNCATION (the assembly ran off the contig), not gene loss. The "
                f"complete cluster would add capacity for: "
                f"{', '.join(m['label'][:26] for m in report['missing'])}.")
        elif im > 0:
            lines.append(
                f"{im} of the missing gene(s) fall in the INTERIOR of the reference cluster (between "
                f"genes the query does have), which truncation cannot explain — so this points to a "
                f"genuine biological difference, not just an assembly artifact"
                + (f"; the remaining {em} at the ends may be truncation." if em else "."))
        elif trunc:
            lines.append(
                f"The query is '{query_boundary}', so the {em} end-missing gene(s) may be truncation, "
                f"but the layout is ambiguous.")
        else:
            lines.append(
                "The query is interior (not contig-limited), so the missing genes are more likely a "
                "genuine biological difference than an assembly artifact.")
    lines.append("Completeness is measured on global-identity orthology (homology), not product "
                 "identity; capacity-level throughout.")
    return "\n\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Assess a truncated cluster's completeness vs complete references.")
    ap.add_argument("--query", required=True, metavar="LABEL:query.gbk")
    ap.add_argument("--reference", action="append", required=True, metavar="LABEL:ref.gbk")
    ap.add_argument("--query-boundary", default="", help="interior | edge | full-contig (from triage)")
    ap.add_argument("--min-id", type=float, default=30.0)
    ap.add_argument("--outdir", default="completeness_out")
    a = ap.parse_args(argv)
    qlab, qpath = a.query.split(":", 1)
    refs = []
    for spec in a.reference:
        lab, path = spec.split(":", 1); refs.append((lab, _genes(path)))
    qgenes = _genes(qpath)
    report = assess(qgenes, refs, min_id=a.min_id)
    report["query"] = qlab; report["query_boundary"] = a.query_boundary
    report["references"] = [l for l, _ in refs]
    report["tier"] = tier(report["completeness_pct"])
    report["interpretation"] = interpret(report, qlab, a.query_boundary, [l for l, _ in refs])
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    (Path(a.outdir) / f"{qlab}_completeness.json").write_text(json.dumps(report, indent=2))
    with open(Path(a.outdir) / f"{qlab}_missing_genes.csv", "w", newline="") as fh:
        w = _SafeWriter(fh); w.writerow(["status", "gene_label", "n_refs_with_it", "query_best_id_pct"])
        for m in report["missing"]:
            w.writerow(["MISSING", m["label"], m["n_refs"], m["query_id"]])
        for p in report["present"]:
            w.writerow(["present", p["label"], p["n_refs"], p["query_id"]])
    emit(f"[cluster_completeness] {qlab}: {report['completeness_pct']}% complete ({report['tier']}), {report['n_present']}/{report['n_cluster_genes']} cluster genes; {report['n_missing']} missing.", '[cluster_completeness] ' + report['interpretation'].split('\n\n')[-2 if report['missing'] else -1], sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

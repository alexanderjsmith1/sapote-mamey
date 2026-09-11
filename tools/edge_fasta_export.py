#!/usr/bin/env python3
"""edge_fasta_export.py — Export a FASTA of edge-proximal genes for directed BLASTp.

For a given Edge or Full-contig BGC, identifies genes within a set distance of the
contig boundary (default 2 kb), collects the KCB/CB reference protein IDs that the
BGC's own genes hit, and exports:
  1. Proteins from the BGC's own contig that are within <window> bp of the edge
  2. The gene-level KCB / CB context showing which reference genes were hit

This gives a short protein FASTA (typically 3–12 sequences) that the analyst can
submit to NCBI BLASTp to identify the functions of edge-proximal genes that
antiSMASH did not formally annotate as part of the BGC.

Usage:
    python3 tools/edge_fasta_export.py \\
        --antismash-zip <AS-XXX.zip> \\
        --package-dir   <mamey_package_dir> \\
        --bgc-id        BGC001 \\
        --out           edge_fasta_BGC001 \\
        [--window 2000] [--top-n-ref 5]

Outputs:
    <out>_edge_proximal.faa    — proteins ≤ window bp from contig edge
    <out>_kcb_gene_context.txt — which reference proteins each BGC gene hit
    <out>_candidate_reconstruction.txt — plain-language reconstruction summary

Claim-safety: all inferences are similarity-based. No compound identity claims.
"""
import argparse, csv, io, os, re, sys, zipfile
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.render_safe import safe_kcb_display

try:
    from Bio import SeqIO  # type: ignore
    _HAS_BIO = True
except ImportError:
    _HAS_BIO = False
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from mamey._gbk_shim import parse_genbank_text as _shim_parse
    except ImportError:
        _shim_parse = None


def _parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--antismash-zip", required=True)
    ap.add_argument("--package-dir",   required=True)
    ap.add_argument("--bgc-id",        required=True, help="e.g. BGC001")
    ap.add_argument("--out",           default=None,  help="output stem (default: <bgc-id>_edge)")
    ap.add_argument("--window",        type=int, default=2000,
                    help="bp from contig edge to include (default 2000)")
    ap.add_argument("--top-n-ref",     type=int, default=5,
                    help="top N reference genome hits to include from CB (default 5)")
    return ap.parse_args()


# ── Parse triage board to find the BGC ──────────────────────────────────────

def get_bgc_info(package_dir: str, bgc_id: str) -> dict:
    pkg = Path(package_dir)
    triage_files = list(pkg.glob("*_4_triage_board.csv"))
    if not triage_files:
        raise FileNotFoundError(f"No triage board in {package_dir}")
    with open(triage_files[0], newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("BGC_ID") == bgc_id:
                return row
    raise ValueError(f"{bgc_id} not found in triage board")


# ── Parse full-assembly GBK for proteins on the BGC's contig ────────────────

def get_contig_proteins(zip_path: str, contig_name: str) -> list:
    """Return list of {lt, seq, start, end, product, strand} for all CDS on the contig."""
    proteins = []
    # Extract NODE number for matching
    nm = re.search(r"NODE_(\d+)", contig_name)
    node_num = nm.group(1) if nm else None

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        full_gbks = [n for n in names if n.endswith(".gbk")
                     and "region" not in n.lower()
                     and "__MACOSX" not in n
                     and n.count("/") <= 1]
        if not full_gbks:
            sys.stderr.write(("[edge_fasta] No full-assembly GBK found") + "\n")
            return proteins
        raw = zf.read(full_gbks[0]).decode("utf-8", errors="replace")

    if not _HAS_BIO:
        sys.stderr.write(("[edge_fasta] biopython not available — cannot parse GBK") + "\n")
        return proteins

    import warnings; warnings.filterwarnings("ignore")
    for rec in SeqIO.parse(io.StringIO(raw), "genbank"):
        rec_nm = re.search(r"NODE_(\d+)", rec.id)
        if node_num and rec_nm and rec_nm.group(1) != node_num:
            continue
        contig_len = len(rec.seq)
        for feat in rec.features:
            if feat.type != "CDS":
                continue
            trans = feat.qualifiers.get("translation", [None])[0]
            if not trans:
                continue
            lt  = feat.qualifiers.get("locus_tag", [""])[0]
            prod = feat.qualifiers.get("product", ["hypothetical protein"])[0]
            start = int(feat.location.start) + 1
            end   = int(feat.location.end)
            strand = "+" if feat.location.strand >= 0 else "-"
            # Distance from nearest edge
            dist_start = start - 1
            dist_end   = contig_len - end
            dist_edge  = min(dist_start, dist_end)
            near_end   = "START" if dist_start < dist_end else "END"
            proteins.append({
                "lt": lt, "seq": trans, "start": start, "end": end,
                "strand": strand, "product": prod,
                "dist_edge": dist_edge, "near_end": near_end,
                "contig_len": contig_len,
            })
        if rec_nm and node_num and rec_nm.group(1) == node_num:
            break  # found the right contig, stop

    return proteins


# ── Parse KCB for gene-level hits ───────────────────────────────────────────

def get_kcb_gene_hits(zip_path: str, contig_name: str, region_num: int) -> dict:
    """Return {query_gene: [(ref_protein, pct_id, score)]} from KCB."""
    hits = defaultdict(list)
    nm = re.search(r"NODE_(\d+)", contig_name)
    if not nm:
        return hits
    node_num = nm.group(1)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        kcb_files = [n for n in names
                     if "knownclusterblast" in n.lower()
                     and f"NODE_{node_num}_" in n
                     and f"_c{region_num}." in n
                     and n.endswith(".txt")
                     and "__MACOSX" not in n]
        if not kcb_files:
            # Try any KCB file for this node
            kcb_files = [n for n in names
                         if "knownclusterblast" in n.lower()
                         and f"NODE_{node_num}" in n
                         and n.endswith(".txt")
                         and "__MACOSX" not in n]

        for fname in kcb_files[:2]:
            try:
                text = zf.read(fname).decode("utf-8", errors="replace")
            except Exception:
                continue
            for line in text.split("\n"):
                parts = line.split("\t")
                if len(parts) >= 4 and re.match(r"ctg\S+", parts[0]):
                    try:
                        hits[parts[0]].append({
                            "ref_protein": parts[1],
                            "pct_id": float(parts[2]),
                            "score": float(parts[3]),
                        })
                    except (ValueError, IndexError):
                        pass
    return hits


def get_cb_top_refs(zip_path: str, contig_name: str, region_num: int, top_n: int = 5) -> list:
    """Return top N genome-neighbour reference accessions from CB."""
    nm = re.search(r"NODE_(\d+)", contig_name)
    if not nm:
        return []
    node_num = nm.group(1)
    refs = []

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        cb_files = [n for n in names
                    if n.lower().startswith("clusterblast/")
                    and f"NODE_{node_num}" in n
                    and f"_c{region_num}." in n
                    and n.endswith(".txt")]
        if not cb_files:
            cb_files = [n for n in names
                        if n.lower().startswith("clusterblast/")
                        and f"NODE_{node_num}" in n
                        and n.endswith(".txt")]
        for fname in cb_files[:1]:
            try:
                text = zf.read(fname).decode("utf-8", errors="replace")
            except Exception:
                continue
            # Parse "Significant hits:" section
            sig = text.find("Significant hits:")
            if sig < 0:
                continue
            for line in text[sig:sig+2000].split("\n"):
                m = re.match(r"\d+\.\s+(\S+)\s+(.+)", line)
                if m:
                    refs.append({"accession": m.group(1), "description": m.group(2).strip()})
                if len(refs) >= top_n:
                    break
    return refs


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = _parse_args()
    out_stem = args.out or f"{args.bgc_id}_edge"

    sys.stdout.write((f"\n[edge_fasta] BGC: {args.bgc_id} | window: {args.window} bp") + "\n")

    # Get BGC info from triage board
    bgc = get_bgc_info(args.package_dir, args.bgc_id)
    contig = bgc.get("Contig", "")
    boundary = bgc.get("Boundary", "")
    products = bgc.get("Products", "")
    kcb_top = bgc.get("KCB_top", "")
    kcb_safe = safe_kcb_display(bgc)
    kcb_score = bgc.get("KCB_score", "")

    nm = re.search(r"NODE_(\d+)", contig)
    node_num = nm.group(1) if nm else "?"
    region_m = re.search(r"(\d+)$", args.bgc_id)
    region_num = int(region_m.group(1)) if region_m else 1

    sys.stdout.write((f"  Contig: NODE_{node_num} ({boundary})") + "\n")
    sys.stdout.write((f"  Products: {products}") + "\n")
    sys.stdout.write((f"  KCB anchor: {kcb_safe}") + "\n")

    # Get all proteins on the contig
    proteins = get_contig_proteins(args.antismash_zip, contig)
    if not proteins:
        sys.stdout.write(("[edge_fasta] No proteins found — check biopython installation") + "\n")
        return

    contig_len = proteins[0]["contig_len"] if proteins else 0
    sys.stdout.write((f"  Contig length: {contig_len:,} bp | {len(proteins)} CDS total") + "\n")

    # Filter to edge-proximal proteins
    edge_prots = [p for p in proteins if p["dist_edge"] <= args.window]
    sys.stdout.write((f"  Proteins within {args.window} bp of contig edge: {len(edge_prots)}") + "\n")

    # Get KCB gene-level hits
    kcb_hits = get_kcb_gene_hits(args.antismash_zip, contig, region_num)

    # Get CB top genome references
    cb_refs = get_cb_top_refs(args.antismash_zip, contig, region_num, args.top_n_ref)

    # Write FASTA
    faa_path = out_stem + "_edge_proximal.faa"
    n_written = 0
    with atomic_open(faa_path) as f:
        # First: BGC's own edge-proximal proteins
        for p in sorted(edge_prots, key=lambda x: x["start"]):
            locus = p["lt"] or f"NODE{node_num}_{p['start']}"
            # Find KCB hits for this gene
            kcb_ref = ""
            for query_lt, hit_list in kcb_hits.items():
                if hit_list and (locus in query_lt or query_lt in locus):
                    best = max(hit_list, key=lambda h: h["score"])
                    kcb_ref = f" | KCB_hit={best['ref_protein']} {best['pct_id']:.0f}%id"
                    break
            header = (f">{locus} "
                      f"contig=NODE_{node_num} "
                      f"pos={p['start']}-{p['end']}({p['strand']}) "
                      f"dist_from_edge={p['dist_edge']}bp "
                      f"near={p['near_end']} "
                      f"product={p['product']}"
                      f"{kcb_ref}")
            f.write(header + "\n")
            # Wrap at 60 chars
            seq = p["seq"]
            for i in range(0, len(seq), 60):
                f.write(seq[i:i+60] + "\n")
            n_written += 1

    sys.stdout.write((f"  Written {n_written} sequences → {faa_path}") + "\n")

    # Write KCB gene context
    ctx_path = out_stem + "_kcb_gene_context.txt"
    with atomic_open(ctx_path) as f:
        f.write(f"KCB gene-level hit context for {args.bgc_id} on NODE_{node_num}\n")
        f.write(f"BGC: {products}\n")
        f.write(f"KCB anchor: {kcb_safe}\n\n")
        f.write("Gene-level BLAST hits (query gene → reference protein, %identity):\n")
        f.write("-" * 70 + "\n")
        for query_lt, hit_list in sorted(kcb_hits.items()):
            best_hits = sorted(hit_list, key=lambda h: -h["score"])[:3]
            for h in best_hits:
                f.write(f"  {query_lt:<20} → {h['ref_protein']:<20} "
                        f"{h['pct_id']:>5.1f}%id  score={h['score']:.0f}\n")

        f.write("\nTop genome-neighbour references (clusterblast):\n")
        f.write("-" * 70 + "\n")
        for i, ref in enumerate(cb_refs, 1):
            f.write(f"  {i}. {ref['accession']:<20} {ref['description'][:55]}\n")

    # Write candidate reconstruction summary
    rec_path = out_stem + "_candidate_reconstruction.txt"
    with atomic_open(rec_path) as f:
        f.write(f"CANDIDATE RECONSTRUCTION SUMMARY — {args.bgc_id}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"BGC: {args.bgc_id} ({boundary}) on NODE_{node_num} ({contig_len:,} bp)\n")
        f.write(f"Products: {products}\n")
        f.write(f"KCB best anchor: {kcb_safe}\n\n")
        f.write(f"Assembly break position: {boundary} — contig terminates at the cluster edge.\n")
        f.write(f"The pathway likely continues beyond this contig boundary.\n\n")

        f.write(f"Edge-proximal genes ({args.window} bp window, {len(edge_prots)} proteins):\n")
        for p in sorted(edge_prots, key=lambda x: x["start"]):
            kcb_note = ""
            for query_lt, hit_list in kcb_hits.items():
                if hit_list and ((p["lt"] and p["lt"] in query_lt) or (p["lt"] and query_lt in p["lt"])):
                    best = max(hit_list, key=lambda h: h["score"])
                    kcb_note = f" → KCB: {best['ref_protein']} ({best['pct_id']:.0f}%id)"
                    break
            f.write(f"  {p['lt'] or 'unnamed':<18} {p['start']:>7}-{p['end']:<7} "
                    f"({p['dist_edge']}bp from {p['near_end']}){kcb_note}\n")

        f.write(f"\nTop genome references sharing this cluster (clusterblast):\n")
        for ref in cb_refs[:3]:
            f.write(f"  {ref['accession']}: {ref['description'][:60]}\n")

        f.write(f"\nRecommended action:\n")
        f.write(f"  1. Submit <out>_edge_proximal.faa to NCBI BLASTp (up to {n_written} queries)\n")
        f.write(f"  2. Use top CB references ({', '.join(r['accession'] for r in cb_refs[:2])})\n"
                f"     to identify what genes are present on the other side of the assembly break\n")
        f.write(f"  3. Compare BLASTp hit functions against the KCB reference to determine\n"
                f"     whether the edge-proximal genes complete the pathway\n\n")
        f.write(f"Claim-safety: all inferences are similarity-based. No compound identity.\n")

    sys.stdout.write((f"  Written KCB context → {ctx_path}") + "\n")
    sys.stdout.write((f"  Written reconstruction summary → {rec_path}") + "\n")

    # Quick stdout summary
    sys.stdout.write((f"\n  Edge-proximal proteins (sorted by distance from edge):") + "\n")
    for p in sorted(edge_prots, key=lambda x: x["dist_edge"])[:8]:
        sys.stdout.write((f"    {p['lt'] or 'unnamed':<18} {p['start']:>7}-{p['end']:<7} "
              f"{p['dist_edge']:>5}bp from {p['near_end']}  {p['product'][:45]}") + "\n")


if __name__ == "__main__":
    main()

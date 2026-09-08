#!/usr/bin/env python3
"""dark_gene_scan.py — Dark-gene rescue scanner for edge/FC BGCs.

For each high-KCB Edge or Full-contig BGC, searches all CDS translations on
contigs NOT called by antiSMASH for proteins homologous to the edge BGC's own
genes. Hits suggest pathway genes antiSMASH found but did not incorporate into
a BGC call — likely fragments of the same split cluster.

Approach: seed proteins come from the edge BGC's own called contig (directly
available from the full-assembly GBK). Each seed is searched against all
translations on uncalled contigs using local pairwise alignment with a k-mer
pre-filter. Each hit is linked back to its KCB reference protein so the role
in the reference pathway can be inferred.

Usage:
    python3 tools/dark_gene_scan.py \\
        --antismash-zip <antiSMASH_output.zip> \\
        --package-dir   <mamey_package_dir> \\
        --out           dark_gene_results.csv \\
        [--min-identity 35] [--min-coverage 50] [--top-n 3] \\
        [--max-bgcs 10] [--max-seeds 12] [--max-uncalled 8000]

Outputs:
    <out>.csv — per-hit table: seed BGC, hit contig/position, identity, coverage,
                inferred KCB reference protein, claim-safety note.

Claim-safety: hits reported as similarity only. Biosynthetic role requires
experimental confirmation. KCB = similarity, not identity.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, io, json, os, re, sys, zipfile
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path
from collections import defaultdict

try:
    from Bio import SeqIO  # type: ignore
    from Bio.Align import PairwiseAligner
    _HAS_BIO = True
except ImportError:
    _HAS_BIO = False

# Shim is always loaded as a fallback — used when biopython is absent OR raises on parse.
try:
    from mamey._gbk_shim import parse_genbank_text as _gbk_shim
except ImportError:
    _gbk_shim = None

MIN_IDENTITY_DEFAULT  = 35
MIN_COVERAGE_DEFAULT  = 50
KCB_SCORE_FLOOR       = 1000   # minimum KCB cumulative score to qualify an edge BGC
KMER_K                = 5
KMER_THRESHOLD        = 0.07   # minimum Jaccard similarity before full alignment
LEN_RATIO_MAX         = 3.0    # skip if seed/target length ratio exceeds this


def _parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--antismash-zip", required=True)
    ap.add_argument("--package-dir",   required=True)
    ap.add_argument("--out",           default="dark_gene_scan")
    ap.add_argument("--min-identity",  type=float, default=MIN_IDENTITY_DEFAULT)
    ap.add_argument("--min-coverage",  type=float, default=MIN_COVERAGE_DEFAULT)
    ap.add_argument("--top-n",         type=int,   default=3)
    ap.add_argument("--max-bgcs",      type=int,   default=12,
                    help="Max edge BGCs to process (sorted by KCB score desc)")
    ap.add_argument("--max-seeds",     type=int,   default=12,
                    help="Max seed proteins per edge BGC")
    ap.add_argument("--max-uncalled",  type=int,   default=8000,
                    help="Max uncalled-contig proteins to search against")
    return ap.parse_args()


# ── Bio alignment ────────────────────────────────────────────────────────────

def _make_aligner():
    al = PairwiseAligner()
    al.mode = 'local'
    al.match_score    =  2
    al.mismatch_score = -1
    al.open_gap_score  = -11
    al.extend_gap_score = -1
    return al


def _align(aligner, seq_a: str, seq_b: str) -> tuple[float, float]:
    """Return (pct_identity, pct_coverage) over aligned region; (0,0) if no alignment."""
    try:
        alignments = aligner.align(seq_a, seq_b)
        best = next(iter(alignments), None)
        if best is None:
            return 0.0, 0.0
        # aligned_length includes gaps; use coordinates
        aln_len = best.length
        if not aln_len:
            return 0.0, 0.0
        # count matches
        import numpy as np
        a_arr = np.frombuffer(best[0].encode(), dtype='uint8')
        b_arr = np.frombuffer(best[1].encode(), dtype='uint8')
        # trim to same length (alignment may pad)
        min_len = min(len(a_arr), len(b_arr), aln_len)
        matches = int(np.sum(a_arr[:min_len] == b_arr[:min_len]))
        pct_id  = 100.0 * matches / aln_len
        pct_cov = 100.0 * aln_len / len(seq_a)
        return round(pct_id, 1), round(pct_cov, 1)
    except Exception:
        return 0.0, 0.0


def _kmer_sim(a: str, b: str, k: int = KMER_K) -> float:
    if len(a) < k or len(b) < k:
        return 0.0
    sa = {a[i:i+k] for i in range(len(a) - k + 1)}
    sb = {b[i:i+k] for i in range(len(b) - k + 1)}
    union = len(sa | sb)
    return len(sa & sb) / union if union else 0.0


# ── GBK parsing ─────────────────────────────────────────────────────────────

def _extract_all_proteins(zip_path: str) -> dict:
    """Parse full-assembly GBK → {contig_id: [protein_dict]}"""
    contig_proteins: dict = defaultdict(list)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        full_gbks = [n for n in names
                     if n.endswith('.gbk')
                     and 'region' not in n.lower()
                     and '__MACOSX' not in n
                     and n.count('/') <= 1]
        if not full_gbks:
            return {}
        raw = zf.read(full_gbks[0]).decode('utf-8', errors='replace')

    # Parse GBK: prefer biopython, fall back to shim on ImportError or parse failure.
    try:
        if not _HAS_BIO:
            raise ImportError("biopython not available")
        _gbk_records = list(SeqIO.parse(io.StringIO(raw), 'genbank'))
    except Exception:
        if _gbk_shim is None:
            return {}
        _gbk_records = _gbk_shim(raw)
    for rec in _gbk_records:
        ctg = rec.id
        for feat in rec.features:
            if feat.type != 'CDS':
                continue
            trans = feat.qualifiers.get('translation', [None])[0]
            if not trans or len(trans) < 30:
                continue
            lt   = feat.qualifiers.get('locus_tag',  [''])[0]
            prod = feat.qualifiers.get('product', ['hypothetical protein'])[0]
            contig_proteins[ctg].append({
                'lt': lt, 'seq': trans,
                'start': int(feat.location.start) + 1,
                'end':   int(feat.location.end),
                'product': prod,
                'contig': ctg,
            })
    return dict(contig_proteins)


# ── KCB parsing ──────────────────────────────────────────────────────────────

def _parse_kcb_hits(zip_path: str, ctg_node: str, region_num: int) -> dict:
    """Return {ref_protein_id: query_locus_tag} for best KCB hit, for this BGC."""
    result = {}  # ref_protein -> query_locus
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        candidates = [n for n in names
                      if 'knownclusterblast' in n.lower()
                      and ctg_node in n
                      and n.endswith('.txt')
                      and '__MACOSX' not in n]
        key = f"_c{region_num}."
        matches = [c for c in candidates if key in c] or candidates
        for fname in matches[:2]:
            try:
                text = zf.read(fname).decode('utf-8', errors='replace')
            except Exception:
                continue
            # Find highest-score reference block
            best_score = 0
            best_map = {}
            blocks = re.split(r'\n>>\n', text)
            for block in blocks[1:]:
                lines = block.split('\n')
                score = 0
                local_map = {}
                for l in lines:
                    if l.startswith('Cumulative BLAST score:'):
                        try:
                            score = float(l.split(':')[1].strip())
                        except Exception:
                            pass
                    parts = l.split('\t')
                    if len(parts) >= 3 and re.match(r'ctg\S+', parts[0]):
                        try:
                            pct = float(parts[2])
                        except Exception:
                            continue
                        if pct >= 30:
                            local_map[parts[1]] = parts[0]  # ref_prot -> query_gene
                if score > best_score and local_map:
                    best_score = score
                    best_map = local_map
            result.update(best_map)
    return result  # {ref_protein_id: query_locus_tag_in_assembly}


# ── Triage board ─────────────────────────────────────────────────────────────

def _load_triage(package_dir: str) -> list:
    pkg = Path(package_dir)
    files = list(pkg.glob('*_4_triage_board.csv'))
    if not files:
        raise FileNotFoundError(f"No triage board in {package_dir}")
    return list(csv.DictReader(open(files[0])))


def _kcb_score(row: dict) -> float:
    s = row.get('KCB_score', '')
    m = re.search(r'[\d.]+$', str(s).strip())
    return float(m.group()) if m else 0.0


def _node_num(s: str) -> str | None:
    m = re.search(r'NODE_(\d+)', s)
    return m.group(1) if m else None


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = _parse_args()

    if not _HAS_BIO:
        emit("[dark_gene_scan] ERROR: biopython required (Bio.Align.PairwiseAligner)")
        sys.exit(1)

    # Parse assembly.
    # v9.7.410 (CLAUDE_410 r_figure_templates): two consecutive single-arg emits merged with the
    # default sep="\n" — byte-identical on stdout, one fewer emission site. This absorbs the single
    # new site added by tools/gen_figure_r_manifest.py so PRINT_WARN_THRESHOLD stays at 1278.
    # Ceilings only go down (see the v9.7.408 paydown note on that constant).
    emit(f"\n[dark_gene_scan] {Path(args.antismash_zip).name}",
         "  Parsing full-assembly GBK...", sep="\n")
    contig_proteins = _extract_all_proteins(args.antismash_zip)
    if not contig_proteins:
        emit("  ERROR: no proteins extracted"); return
    total_prots = sum(len(v) for v in contig_proteins.values())
    emit(f"  {len(contig_proteins)} contigs | {total_prots:,} CDS translations")

    # Load triage board
    tb = _load_triage(args.package_dir)
    strain_id = Path(args.package_dir).name  # use dir name as default

    # Map called contigs
    called_nodes = set()
    for r in tb:
        n = _node_num(r.get('Contig', ''))
        if n:
            called_nodes.add(n)

    # Partition proteins
    called_ctg_map: dict = {}    # node_num -> contig_id
    uncalled_prots: list = []
    for ctg, prots in contig_proteins.items():
        n = _node_num(ctg)
        if n in called_nodes:
            called_ctg_map[n] = ctg
        else:
            # Cap per-contig to avoid huge assemblies dominating
            uncalled_prots.extend(prots[:200])

    uncalled_prots = uncalled_prots[:args.max_uncalled]
    n_uncalled_ctg = len(contig_proteins) - len(called_nodes)
    emit(f"  Called contigs: {len(called_nodes)} | "
          f"Uncalled: {n_uncalled_ctg} | "
          f"Uncalled proteins: {len(uncalled_prots):,}")

    if not uncalled_prots:
        emit("  No uncalled-contig proteins — nothing to scan"); return

    # Select edge BGCs
    edge_bgcs = sorted(
        [r for r in tb
         if r.get('Boundary') in ('Edge', 'Full-contig')
         and _kcb_score(r) >= KCB_SCORE_FLOOR],
        key=_kcb_score, reverse=True
    )[:args.max_bgcs]
    emit(f"  Edge/FC BGCs (KCB≥{KCB_SCORE_FLOOR}): {len(edge_bgcs)}")

    aligner = _make_aligner()
    results: list = []
    seen_global: set = set()  # (hit_contig, hit_start) — deduplicate across BGCs

    for bgc in edge_bgcs:
        bgc_id    = bgc.get('BGC_ID', '')
        ctg_raw   = bgc.get('Contig', '')
        products  = bgc.get('Products', '')
        kcb_top   = bgc.get('KCB_top', '')
        boundary  = bgc.get('Boundary', '')
        n = _node_num(ctg_raw)
        if not n or n not in called_ctg_map:
            continue

        ctg_key = called_ctg_map[n]
        seed_prots = contig_proteins.get(ctg_key, [])[:args.max_seeds]

        # Load KCB reference-protein map for this BGC
        region_m = re.search(r'(\d+)$', bgc_id)
        kcb_ref_map = {}
        if region_m:
            kcb_ref_map = _parse_kcb_hits(
                args.antismash_zip, f"NODE_{n}", int(region_m.group(1)))
        # Invert: query_locus -> ref_protein (to look up by seed locus tag)
        locus_to_ref = {v: k for k, v in kcb_ref_map.items()}

        bgc_hits = []
        for seed in seed_prots:
            if len(seed['seq']) < 50:
                continue
            for target in uncalled_prots:
                # Length ratio pre-filter
                lr = max(len(seed['seq']), len(target['seq'])) / max(min(len(seed['seq']), len(target['seq'])), 1)
                if lr > LEN_RATIO_MAX:
                    continue
                # k-mer pre-filter
                if _kmer_sim(seed['seq'], target['seq']) < KMER_THRESHOLD:
                    continue
                pid, pcov = _align(aligner, seed['seq'], target['seq'])
                if pid >= args.min_identity and pcov >= args.min_coverage:
                    key = (_node_num(target['contig']), target['start'])
                    if key in seen_global:
                        continue
                    seen_global.add(key)
                    # Infer KCB ref protein: try to match seed locus tag
                    # seed locus tag e.g. "ctg28_63"; KCB map uses ctg-prefixed names
                    seed_lt_short = seed['lt'].split('_')
                    ref_prot = locus_to_ref.get(seed['lt'], '')
                    if not ref_prot:
                        # try ctg-style lookup
                        for k_lt, ref in locus_to_ref.items():
                            if any(p in k_lt for p in seed_lt_short[-1:]):
                                ref_prot = ref
                                break
                    hit_node = _node_num(target['contig'])
                    bgc_hits.append({
                        'strain':       strain_id,
                        'bgc_id':       bgc_id,
                        'boundary':     boundary,
                        'bgc_products': products[:40],
                        'kcb_ref':      kcb_top[:40],
                        'seed_locus':   seed['lt'],
                        'seed_product': seed['product'][:40],
                        'inferred_ref_protein': ref_prot or 'unresolved',
                        'hit_node':     f"NODE_{hit_node or '?'}",
                        'hit_contig':   target['contig'],
                        'hit_locus':    target['lt'],
                        'hit_start':    target['start'],
                        'hit_end':      target['end'],
                        'hit_product':  target['product'][:50],
                        'pct_identity': pid,
                        'pct_coverage': pcov,
                        'claim_note':   'similarity only — not identity; '
                                        'biosynthetic role requires experimental confirmation',
                    })

        # Sort by identity, keep top_n per BGC
        bgc_hits.sort(key=lambda h: -h['pct_identity'])
        results.extend(bgc_hits[:args.top_n * 3])  # keep a few per BGC

    # Final sort and cap
    results.sort(key=lambda r: -r['pct_identity'])

    # Write output
    out_csv = args.out + '.csv'
    if results:
        with open(out_csv, 'w', newline='') as f:
            w = _SafeDictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)
        emit(f"\n[dark_gene_scan] Written: {out_csv} ({len(results)} rows)")
    else:
        emit("\n[dark_gene_scan] No dark-gene hits above thresholds")

    # Summary
    bgcs_hit = len(set(r['bgc_id'] for r in results))
    nodes_hit = len(set(r['hit_node'] for r in results))
    emit(f"[dark_gene_scan] {bgcs_hit} BGCs with hits | "
          f"{nodes_hit} uncalled nodes implicated | "
          f"{len(results)} total hits")

    return results


if __name__ == '__main__':
    main()

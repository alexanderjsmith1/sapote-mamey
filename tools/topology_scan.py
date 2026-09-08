#!/usr/bin/env python3
"""topology_scan.py — detect inverted (non-co-directional) BGC strand-block topology and
characterise the unannotated genes inside it.

Motivation: some BGC families are organised as a tripartite +/-/+ strand block — flanking
biosynthetic genes on one strand, a reversed tailoring cassette on the other — rather than the
usual co-directional layout. This architecture (observed e.g. in the an example strain NODE_162 nucleoside
cluster) is a conserved family feature, not an assembly artefact, and it tends to co-occur with
genes antiSMASH leaves completely unannotated (bare locus_tag + translation only). Those bare
genes are the highest-value experimental targets precisely because the standard pipeline says
nothing about them.

This tool is pure extraction (deterministic, reproducible, no external calls):
  1. Segments each region's CDS into maximal same-strand runs and classifies the run pattern
     (CO_DIRECTIONAL, SINGLE_FLIP, INVERTED_BLOCK [tripartite A/-A/A], or COMPLEX).
  2. Flags genes that are UNANNOTATED (no gene_functions / gene_kind / sec_met_domain / product
     beyond 'hypothetical'), and notes diagnostic features it CAN see deterministically:
       - N-/C-terminal truncation at a contig edge
       - TTA (bldA-dependent) leucine codon in the CDS
       - any clusterblast/knownclusterblast homolog antiSMASH already computed for that gene
  3. Writes the bare genes' protein sequences to <out>_unannotated.faa, ready for an EXTERNAL
     blastp (which the engine intentionally does not run — see note). If a results TSV is supplied
     via --blastp-results, its top hit per gene is merged into the report.

Outputs: <out>_topology.csv (per-gene), <out>_summary.json (per-region verdicts),
         <out>_unannotated.faa (bare-gene proteins for external blastp).

Note on blastp: Mamey is the deterministic extraction layer; live homology search against external
databases (nr, etc.) is non-reproducible across runs and needs network/DB the pipeline doesn't
own, so it is kept OUT of the engine. This tool prepares the FASTA and ingests results, making the
blastp an explicit, user-invoked, file-mediated step rather than a hidden engine action.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, json, os, re
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_open, atomic_dump_json
try:
    from Bio import SeqIO  # type: ignore
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
    from mamey._gbk_shim import parse_genbank_text as _pgbt
    class _ShimSeqIO:
        @staticmethod
        def parse(handle, fmt):
            if hasattr(handle, 'read'):
                text = handle.read()
            else:
                with open(handle) as _fh:
                    text = _fh.read()
            return iter(_pgbt(text))
    SeqIO = _ShimSeqIO()

# ---- TTA codon detection (bldA-gated, late secondary-metabolite genes) ----
def has_tta(nt_seq, strand):
    """True if the CDS contains a TTA leucine codon in-frame (on its coding strand).
       Returns False if the sequence is undefined (e.g. a GBK with no ORIGIN block)."""
    try:
        s = str(nt_seq).upper()
    except Exception:
        return False
    if not s or set(s) - set("ACGTN"):
        return False
    if strand == -1:
        comp = str.maketrans("ACGT","TGCA")
        s = s.translate(comp)[::-1]
    return any(s[i:i+3] == "TTA" for i in range(0, len(s)-2, 3))

def is_annotated(q):
    """A CDS is 'annotated' if antiSMASH attached any functional signal."""
    if any(k in q for k in ("gene_functions","gene_kind","sec_met_domain")): return True
    prod = (q.get("product",[""])[0] or "").strip().lower()
    return prod not in ("", "hypothetical protein", "(none)", "unknown")

def gene_label(q):
    """Best short functional label antiSMASH already has, else ''. Never invents."""
    for g in q.get("gene_functions", []):
        m = re.search(r"(SMCOG\d+:\s*[^()]+|rule-based-clusters\)\s*\w+:\s*\w+|[\w-]+:\s*\w+)", g)
        if m: return re.sub(r"\s+", " ", m.group(1)).strip()[:48]
    sd = q.get("sec_met_domain", [])
    if sd:
        m = re.match(r"(\w+)", sd[0]); 
        if m: return m.group(1)
    return ""

def classify_runs(strands):
    """Classify a list of per-gene strands into a topology pattern."""
    # build maximal same-strand runs (ignore None/unstranded)
    runs = []
    for st in strands:
        if not runs or runs[-1][0] != st: runs.append([st, 0])
        runs[-1][1] += 1
    nruns = len(runs)
    pattern = "/".join(f"{'+' if r[0]==1 else '-' if r[0]==-1 else '?'}x{r[1]}" for r in runs)
    if nruns == 1:
        kind = "CO_DIRECTIONAL"
    elif nruns == 2:
        kind = "SINGLE_FLIP"
    elif nruns == 3 and runs[0][0] == runs[2][0] and runs[1][0] == -runs[0][0]:
        kind = "INVERTED_BLOCK"          # the A / -A / A tripartite signature
    else:
        kind = "COMPLEX"
    return kind, pattern, runs

def parse_clusterblast_for_gene(cb_dir, contig_stem, locus):
    """Return the single best per-gene homolog antiSMASH already computed (cb or kcb), or None.
       Deterministic: just reads files already on disk."""
    best = None
    for sub in ("clusterblast","knownclusterblast"):
        d = os.path.join(cb_dir, sub) if cb_dir else None
        if not d or not os.path.isdir(d): continue
        for fp in (os.path.join(d, f) for f in os.listdir(d)
                   if f.startswith(contig_stem) and f.endswith(".txt")):
            txt = open(fp).read()
            for m in re.finditer(rf"^{re.escape(locus)}\t(\S+)\t(\d+)\t(\d+)\t", txt, re.M):
                subj, ident, score = m.group(1), int(m.group(2)), int(m.group(3))
                if best is None or score > best["score"]:
                    best = {"subject": subj, "identity": ident, "score": score, "source": sub}
    return best

def scan_region(gbk, cb_dir=None):
    rec = next(SeqIO.parse(gbk, "genbank"))
    rlen = len(rec.seq)
    contig_stem = re.sub(r"\.region\d+\.gbk$", "", os.path.basename(gbk))
    contig_stem = re.match(r"(NODE_\d+|[\w]+?)(?:_length|\.region|$)", contig_stem)
    contig_stem = contig_stem.group(1) if contig_stem else os.path.basename(gbk)[:20]
    genes = []
    for f in rec.features:
        if f.type != "CDS": continue
        q = f.qualifiers
        loc = q.get("locus_tag", ["?"])[0]
        s, e = int(f.location.start), int(f.location.end)
        st = f.location.strand
        ann = is_annotated(q)
        label = gene_label(q) if ann else ""
        # deterministic diagnostics
        trunc = ""
        if s <= 3: trunc = "N-trunc(5'edge)" if st == 1 else "C-trunc(5'edge)"
        if e >= rlen - 3: trunc = (trunc + ";" if trunc else "") + ("C-trunc(3'edge)" if st == 1 else "N-trunc(3'edge)")
        seq = f.extract(rec.seq) if hasattr(f, "extract") else rec.seq[s:e]
        # v9.7.374 (audit lane): `seq` above was computed via f.extract() (which correctly
        # joins CompoundLocation segments AND reverse-complements for strand==-1) and then
        # discarded -- this line re-sliced the RAW genomic envelope `rec.seq[s:e]` instead, which
        # for a compound ("join") CDS location includes whatever lies BETWEEN the joined segments
        # (e.g. an intervening ORF or spacer), not just the true coding sequence. Live-reproduced:
        # a synthetic compound-location CDS with a TTA-free real coding sequence (join of two
        # non-TTA segments) but a TTA-bearing gap between them reported tta_codon=True from the
        # raw-envelope slice, vs the correct False from the properly extracted/joined sequence --
        # a false bldA-dependence flag purely from non-coding sequence. Use the already-computed,
        # correctly joined/oriented `seq`; pass strand=1 so has_tta does not re-apply a
        # reverse-complement on top of the one extract() already performed (regression-checked
        # against the pre-fix simple-strand-(-1) case: both give identical results there).
        tta = has_tta(seq, 1)
        cbhit = (parse_clusterblast_for_gene(cb_dir, contig_stem, loc) if (not ann and cb_dir) else None)
        prot = q.get("translation", [""])[0]
        genes.append({"locus": loc, "start": s, "end": e, "strand": st, "annotated": ann,
                      "label": label, "truncated": trunc, "tta_codon": tta,
                      "cb_homolog": cbhit, "aa_len": len(prot), "protein": prot})
    kind, pattern, runs = classify_runs([g["strand"] for g in genes])
    return {"contig": contig_stem, "region_len": rlen, "topology": kind,
            "run_pattern": pattern, "n_runs": len(runs), "genes": genes}

def merge_blastp(genes, results_tsv):
    """Merge an external blastp results TSV (qseqid sseqid pident ... stitle) top-hit per gene."""
    if not results_tsv or not os.path.exists(results_tsv): return
    top = {}
    for line in open(results_tsv):
        p = line.rstrip("\n").split("\t")
        if len(p) < 3: continue
        q = p[0]
        try: pid = float(p[2])
        except (ValueError, IndexError): continue
        if q not in top or pid > top[q][0]:
            title = p[-1] if len(p) > 3 else p[1]
            top[q] = (pid, p[1], title)
    for g in genes:
        if g["locus"] in top:
            pid, sid, title = top[g["locus"]]
            g["blastp_top"] = {"subject": sid, "identity": pid, "title": title[:80]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gbk", nargs="+", required=True, help="region GBK(s)")
    ap.add_argument("--cb-dir", default=None, help="dir containing clusterblast/ + knownclusterblast/ (optional)")
    ap.add_argument("--blastp-results", default=None, help="optional external blastp TSV (qseqid sseqid pident ... stitle) to merge")
    ap.add_argument("--only-inverted", action="store_true", help="only report regions with INVERTED_BLOCK/COMPLEX topology")
    ap.add_argument("--out", default="topology_scan")
    a = ap.parse_args()

    regions = [scan_region(g, a.cb_dir) for g in a.gbk]
    if a.blastp_results:
        for r in regions: merge_blastp(r["genes"], a.blastp_results)
    if a.only_inverted:
        regions = [r for r in regions if r["topology"] in ("INVERTED_BLOCK","COMPLEX")]

    # per-gene CSV
    with atomic_open(a.out + "_topology.csv", newline="") as fh:
        w = _SafeWriter(fh)
        w.writerow(["contig","topology","run_pattern","locus","start","end","strand",
                    "annotated","label","truncated","tta_codon","cb_homolog","cb_identity","aa_len","blastp_title"])
        for r in regions:
            for g in r["genes"]:
                cb = g.get("cb_homolog") or {}
                bp = g.get("blastp_top") or {}
                w.writerow([r["contig"], r["topology"], r["run_pattern"], g["locus"],
                            g["start"], g["end"], "+" if g["strand"]==1 else "-",
                            g["annotated"], g["label"], g["truncated"], g["tta_codon"],
                            cb.get("subject",""), cb.get("identity",""), g["aa_len"], bp.get("title","")])

    # summary JSON (drop protein seqs)
    summ = []
    for r in regions:
        unann = [g for g in r["genes"] if not g["annotated"]]
        summ.append({"contig": r["contig"], "topology": r["topology"], "run_pattern": r["run_pattern"],
                     "n_genes": len(r["genes"]), "n_unannotated": len(unann),
                     "unannotated_loci": [g["locus"] for g in unann],
                     "tta_unannotated": [g["locus"] for g in unann if g["tta_codon"]],
                     "truncated": [g["locus"] for g in r["genes"] if g["truncated"]]})
    atomic_dump_json(summ, a.out + "_summary.json", indent=1)

    # bare-gene proteins -> FASTA for an EXTERNAL blastp
    n_faa = 0
    with atomic_open(a.out + "_unannotated.faa", "w") as fh:
        for r in regions:
            for g in r["genes"]:
                if not g["annotated"] and g["protein"]:
                    fh.write(f">{g['locus']} {r['contig']} {g['start']}-{g['end']} "
                             f"strand={'+' if g['strand']==1 else '-'} aa={g['aa_len']}"
                             f"{' TTA' if g['tta_codon'] else ''}{' '+g['truncated'] if g['truncated'] else ''}\n")
                    fh.write(g["protein"] + "\n")
                    n_faa += 1

    inv = [r["contig"] for r in regions if r["topology"] in ("INVERTED_BLOCK","COMPLEX")]
    emit(f"wrote {a.out}_topology.csv, _summary.json, _unannotated.faa ({n_faa} bare proteins)")
    if inv: emit(f"INVERTED/COMPLEX topology in: {', '.join(inv)}")

if __name__ == "__main__":
    main()

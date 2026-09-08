#!/usr/bin/env python3
"""comparator_select.py — pick a phylogenomic comparator genome by the 16S method.

Mechanizes: 16S query -> blastn vs a TYPE-STRAIN-ONLY 16S DB -> nearest NAMED type
            -> look up that type's GENOME in the genome inventory (size-checked).

Why this exists: comparators are otherwise chosen ad hoc (e.g. a query shown against an *unnamed*
sp. strain). This forces the deterministic path: the nearest *named* type strain, with the identity
number always reported, and the genome resolved from the inventory rather than guessed.

It is NON-DESTRUCTIVE (read-only): runs blastn, reads the inventory, prints/writes a table.
Nothing is moved, downloaded, or deleted.

Inputs
  a 16S query FASTA (one or more sequences; header should carry the strain id, e.g. >QUERY-ID ...)

Nearest-NAMED-type rule
  The top blastn hit whose organism has a real species epithet. Hits whose epithet is
  sp./cf./aff./bacterium/uncultured/endophyte/symbiont (unnamed/provisional) are SKIPPED for the
  "named" pick but still reported as raw context, so an unnamed strain can never masquerade as the
  named comparator again.

Genome resolution
  The 16S accession (NR_/NG_) is NOT a genome accession, so the genome is matched by name: inventory
  rows whose genus == the hit genus AND whose path/filename contains the species epithet. Each
  candidate is reported with size + an actinomycete size-sanity flag (~5-13 Mb).

Usage
  python Tools/comparator_select.py QUERY_16S.fasta [--db blast_dbs/16S_ribosomal_RNA]
         [--inventory OFFICIAL_DATA/GENOME_INVENTORY.tsv] [--blastn <path>] [--top 5]
         [--out comparators.tsv]
Requires blastn on PATH or via --blastn (conda env 'blast' has 2.16.0):
  <path>/blastn
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, re, shutil, subprocess, sys, tempfile
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path

# Generic engine tool: NO hardcoded user/project paths. All locations come from the environment
# (set by the working folder) or CLI args, with generic relative fallbacks under the run root.
ROOT = Path(os.environ.get("SAPOTE_ROOT", os.getcwd()))
DEF_DB  = Path(os.environ.get("SAPOTE_16S_DB", ROOT / "blast_dbs" / "16S_ribosomal_RNA"))
DEF_INV = Path(os.environ.get("SAPOTE_GENOME_INVENTORY", ROOT / "OFFICIAL_DATA" / "GENOME_INVENTORY.tsv"))
DEF_BLASTN = os.environ.get("SAPOTE_BLASTN") or shutil.which("blastn") or ""
DEF_SEED = Path(os.environ.get("SAPOTE_16S_SEED", ROOT / "reference" / "16S_seed.fasta"))

# epithets that are NOT a real named species -> excluded from the "nearest NAMED type" pick
_UNNAMED = re.compile(r"^(sp\.?|cf\.?|aff\.?|bacterium|genomosp\.?|"
                      r"uncultured|endophyt\w*|symbiont|str\.?|strain)$", re.I)
# actinomycete genome-size sanity window (bp); outside -> flag for manual check
_LO, _HI = 5_000_000, 13_000_000


def parse_org(stitle: str):
    """From a 16S DB title -> (genus, species_epithet, is_named). Returns ('', '', False) if unclear."""
    # titles look like: "Genusname speciesname strain XYZ 16S ribosomal RNA, partial sequence"
    toks = stitle.replace("[", "").replace("]", "").split()
    if len(toks) < 2:
        return "", "", False
    genus, sp = toks[0], toks[1].rstrip(",")
    named = bool(re.match(r"^[A-Z][a-z]+$", genus)) and not _UNNAMED.match(sp) and re.match(r"^[a-z-]+$", sp) is not None
    return genus, sp, named


def extract_16s_from_genome(genome: Path, seed: Path, blastn: Path, strain_id: str, workdir: Path):
    """No barrnap: blastn a seed 16S against the genome (-subject), extract the best HSP span.
    Returns the path to a written 16S FASTA, or exits with a clear message if no 16S-length hit.
    """
    # NCBI BLAST+ mis-parses spaces in -subject/-query paths -> stage both in a space-free tmp dir.
    g_safe = workdir / "genome.fna"
    s_safe = workdir / "seed.fasta"
    shutil.copyfile(genome, g_safe)
    shutil.copyfile(seed, s_safe)
    if s_safe.stat().st_size == 0:
        sys.exit(f"seed 16S is empty: {seed}")
    fmt = "6 sseqid pident length sstart send evalue bitscore"
    cmd = [str(blastn), "-query", str(s_safe), "-subject", str(g_safe), "-outfmt", fmt,
           "-max_target_seqs", "5"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"16S extraction blastn failed on {genome}:\n{p.stderr.strip()}")
    best = None
    for line in p.stdout.splitlines():
        f = line.split("\t")
        if len(f) < 7:
            continue
        sseqid, pid, ln, ss, se = f[0], float(f[1]), int(f[2]), int(f[3]), int(f[4])
        if ln < 700:             # below this it is a fragment, not a usable 16S
            continue
        if best is None or ln > best[2]:
            best = (sseqid, pid, ln, ss, se)
    if best is None:
        sys.exit(f"no 16S span (>=700bp) found in {genome} — 16S likely split across contigs; "
                 f"extract manually or use MLSA")
    sseqid, pid, ln, ss, se = best
    partial = ln < 1400  # near-full-length 16S ~1500bp; flag shorter as assembly-fragmented
    lo, hi = min(ss, se), max(ss, se)
    strand = "minus" if ss > se else "plus"
    # pull the span with blastdbcmd-free approach: use blastn's own subject seq via samtools-free slice
    seq = _read_contig(genome, sseqid)
    if seq is None:
        sys.exit(f"could not read contig {sseqid} from {genome}")
    sub = seq[lo - 1:hi]
    if strand == "minus":
        sub = _revcomp(sub)
    out = workdir / f"{strain_id}_16S.fasta"
    out.write_text(f">{strain_id}_16S_rRNA_extracted len={len(sub)} src={sseqid}:{lo}-{hi}({strand}) "
                   f"seedpid={pid:.1f}{' PARTIAL' if partial else ''}\n{sub}\n")
    return out, dict(contig=sseqid, span=f"{lo}-{hi}", strand=strand, len=len(sub),
                     seed_pid=pid, partial=partial)


def _read_contig(genome: Path, sseqid: str):
    """Return the nucleotide string of contig sseqid from a FASTA (no Bio dependency)."""
    want, cur, buf, out = sseqid, None, [], None
    for line in genome.open():
        if line.startswith(">"):
            if cur == want:
                out = "".join(buf); break
            cur = line[1:].split()[0]
            buf = []
        else:
            if cur == want:
                buf.append(line.strip())
    if out is None and cur == want:
        out = "".join(buf)
    return out


def _revcomp(s: str):
    return s.translate(str.maketrans("ACGTacgtNn", "TGCAtgcaNn"))[::-1]


def run_blastn(query: Path, db: Path, blastn: Path, top: int):
    fmt = "6 qseqid sacc pident length qlen qstart qend evalue bitscore stitle"
    cmd = [str(blastn), "-query", str(query), "-db", str(db), "-outfmt", fmt,
           "-max_target_seqs", str(max(top * 6, 30)), "-num_threads", "4"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"blastn failed:\n{p.stderr.strip()}")
    rows = []
    for line in p.stdout.splitlines():
        f = line.split("\t")
        if len(f) < 10:
            continue
        qseqid, sacc, pident, length, qlen = f[0], f[1], float(f[2]), int(f[3]), int(f[4])
        stitle = f[9]
        cov = 100.0 * length / qlen if qlen else 0.0
        genus, sp, named = parse_org(stitle)
        rows.append(dict(qseqid=qseqid, sacc=sacc, pident=pident, aln=length, qlen=qlen,
                         cov=cov, genus=genus, sp=sp, named=named, stitle=stitle))
    return rows


def load_inventory(inv: Path):
    if not inv.exists():
        return []
    return list(csv.DictReader(inv.open(), delimiter="\t"))


def find_genomes(inv_rows, genus: str, sp: str):
    """Inventory rows matching genus AND species epithet appearing in the path. Size-sanity flagged."""
    out = []
    spl = sp.lower()
    for r in inv_rows:
        if r.get("genus", "") != genus:
            continue
        path = r.get("canonical_path", "")
        base = os.path.basename(path).lower().replace("-", "_")
        if spl and spl in base:
            try:
                bp = int(r.get("bp") or 0)
            except ValueError:
                bp = 0
            flag = "" if _LO <= bp <= _HI else f"SIZE?({bp}bp outside {_LO//10**6}-{_HI//10**6}Mb)"
            out.append((path, bp, r.get("accession", ""), flag))
    out.sort(key=lambda t: (t[3] != "", -t[1]))  # size-OK first, then largest
    return out


def per_query(rows, inv_rows, n_named: int = 3):
    """Group blast rows by query; pick the closest N DISTINCT named types + genome candidates each."""
    byq: dict[str, list] = {}
    for r in rows:
        byq.setdefault(r["qseqid"], []).append(r)
    results = []
    for q, hits in byq.items():
        hits.sort(key=lambda r: (-r["pident"], -r["cov"]))
        picks, seen = [], set()
        for h in hits:
            if not h["named"]:
                continue
            key = (h["genus"], h["sp"])
            if key in seen:
                continue
            seen.add(key)
            h = dict(h, genomes=find_genomes(inv_rows, h["genus"], h["sp"]))
            picks.append(h)
            if len(picks) >= n_named:
                break
        results.append(dict(query=q, picks=picks, top_raw=hits[0]))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description="Select a comparator genome via the 16S->named-type->inventory method.")
    ap.add_argument("query", help="16S query FASTA, OR a genome FASTA with --from-genome")
    ap.add_argument("--from-genome", action="store_true",
                    help="treat the positional arg as a genome; extract 16S first (no barrnap needed)")
    ap.add_argument("--strain", default="", help="strain id for --from-genome output header (default: filename)")
    ap.add_argument("--seed", default=str(DEF_SEED), help="seed 16S FASTA for --from-genome extraction")
    ap.add_argument("--db", default=str(DEF_DB))
    ap.add_argument("--inventory", default=str(DEF_INV))
    ap.add_argument("--blastn", default=DEF_BLASTN)  # resolved from $SAPOTE_BLASTN / PATH at import
    ap.add_argument("--n-named", type=int, default=3, help="closest N distinct NAMED types to report (default 3)")
    ap.add_argument("--top", type=int, default=5, help="raw hits to fetch per query (internal)")
    ap.add_argument("--out", help="write a TSV of the picks")
    a = ap.parse_args(argv)

    if not a.blastn or not Path(a.blastn).exists():
        sys.exit("blastn not found; set $SAPOTE_BLASTN or pass --blastn /path/to/blastn")
    if not Path(a.query).exists():
        sys.exit(f"input not found: {a.query}")

    query_path = Path(a.query)
    tmp = None
    if a.from_genome:
        if not Path(a.seed).exists():
            sys.exit(f"seed 16S not found: {a.seed} (pass --seed)")
        strain = a.strain or query_path.stem
        tmp = Path(tempfile.mkdtemp(prefix="cmp16s_"))
        query_path, ext = extract_16s_from_genome(query_path, Path(a.seed), Path(a.blastn), strain, tmp)
        emit(f"[extract] {strain}: 16S {ext['len']}bp from {ext['contig']}:{ext['span']} "
              f"({ext['strand']}, seed {ext['seed_pid']:.1f}% id) -> {query_path}")

    rows = run_blastn(query_path, Path(a.db), Path(a.blastn), a.top)
    inv = load_inventory(Path(a.inventory))
    if not inv:
        emit(f"[warn] inventory empty/missing ({a.inventory}) — genome lookup skipped", file=sys.stderr)
    results = per_query(rows, inv, a.n_named)

    out_rows = []
    for res in results:
        q = res["query"]
        emit(f"\n=== {q} ===")
        if not res["picks"]:
            emit("  no NAMED type in top hits (all sp./environmental)")
            tr = res["top_raw"]
            emit(f"    top raw hit: {tr['genus']} {tr['sp']} ({tr['pident']:.2f}%, {tr['sacc']}) [UNNAMED]")
        for rank, n in enumerate(res["picks"], 1):
            emit(f"  #{rank} {n['genus']} {n['sp']}  "
                  f"(16S {n['pident']:.2f}% id, {n['cov']:.0f}% cov, aln {n['aln']}bp, {n['sacc']})")
            if n["genomes"]:
                path, bp, acc, flag = n["genomes"][0]
                more = f"  (+{len(n['genomes'])-1} more copies)" if len(n["genomes"]) > 1 else ""
                emit(f"       genome: {path}  [{bp}bp {acc or '-'}] {flag}{more}")
            else:
                emit(f"       genome: NONE on disk -> search NCBI Nucleotide (~5-13Mb assembly)")
            out_rows.append([q, rank, f"{n['genus']} {n['sp']}", f"{n['pident']:.2f}",
                             f"{n['cov']:.0f}", n["sacc"],
                             n["genomes"][0][0] if n["genomes"] else "",
                             n["genomes"][0][3] if n["genomes"] else "no-genome-on-disk"])

    if a.out:
        with open(a.out, "w", newline="") as f:
            w = _SafeWriter(f, delimiter="\t")
            w.writerow(["query", "rank", "named_type", "pct_id_16S", "cov_pct", "16S_acc",
                        "best_genome_path", "flag"])
            w.writerows(out_rows)
        emit(f"\n-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""marker_candidate_search.py — find NCBI comparator genomes for an AS strain by
BLASTing 1-2 reliable markers, and turn the hits into a bounded candidate panel.

The comparator-DISCOVERY front-end of the two-tier phylogenomics workflow
(docs/GTOTREE_WORKFLOW.md). It decides *which* reference genomes to fetch before any
tree is built, using taxonomically reliable markers:
  * 16S rRNA  — universal, but over-lumps (98-100% 16S can still be distinct by ANI)
  * rpoB / gyrB — protein-coding, better species/genus resolution (ship as MLSA seeds)
Two markers cross-check each other; a hit strong on both is a better comparator than a
hit strong on 16S alone.

It is a THIRD candidate-discovery route feeding Codex's bounded-panel builder, alongside
`rank_clusterblast_phylo_candidates.py` — NOT a competing planner. Output is a candidate
panel TSV in the exact `build_phylo_panel.py` columns.

GOVERNANCE — plan-only where it counts. Reference discovery and genome download hit the
network and therefore require explicit user approval (docs/phylogenomics.md,
docs/LLM_COMPANION_TOOL_PROTOCOL.md). This tool:
  * PLANS the marker BLAST (prints the exact command) and, given a BLAST result table,
    turns it into a candidate panel — both offline/pure;
  * PLANS the genome downloads (prints `datasets download ...` commands) — it never
    downloads and never runs a remote BLAST itself.
Default channel is a LOCAL RefSeq marker DB (remote NCBI is rate-limited/unreliable and
must never carry a personal email/ID). Pass --remote only to emit remote-blast commands.

CLAIM SAFETY: a marker hit is taxonomic proximity, not identity; ANI still delimits
species. Class-level hypotheses, judgment deferred.

Subcommands:
  plan-blast   --assembly A.fna --query AS-XXX [--markers 16S,rpoB] [--db DB] [--remote]
               -> prints the marker-extraction + BLAST commands to run (with approval)
  to-panel     --hits hits.tsv --query AS-XXX --marker 16S [--max-hits 3]
               [--out panel.tsv] [--min-pident 0]
               -> parse a BLAST outfmt6 hit table -> candidate panel TSV (pure, tested)
  plan-download --panel panel.tsv [--out download.sh]
               -> prints `datasets download genome accession ...` (never runs it)
"""
import sys
import os
import re
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

PANEL_COLS = ["candidate_id", "role", "source_path",
              "selection_basis", "related_query_ids"]
# reliable markers; protein markers reuse the MLSA seed proteins shipped with the bundle
MARKER_SEEDS = {"rpoB": "rpoB.faa", "gyrB": "gyrB.faa", "atpD": "atpD.faa",
                "recA": "recA.faa", "trpB": "trpB.faa"}
RRNA_MARKERS = {"16S"}
_HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS_DIR = os.path.normpath(os.path.join(_HERE, os.pardir, "mamey", "data", "phylo_seeds"))

# outfmt6 default column order used by both blastn and blastp when unspecified
OUTFMT6 = ["qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
           "qstart", "qend", "sstart", "send", "evalue", "bitscore"]

# a RefSeq/nt subject id often carries an accession we can resolve to a genome, e.g.
# "NR_074327.1", "ref|NZ_CP012.1|", "gi|..|ref|NC_....|". Pull the assembly-ish accession.
_ACC = re.compile(r'\b((?:GC[AF]_\d+\.\d+)|(?:N[A-Z]_[A-Z0-9]+\.\d+)|(?:[A-Z]{1,2}\d{5,8}\.\d+))\b')


def accession_from_subject(sseqid):
    """Best-effort genome/sequence accession from a BLAST subject id. Pure; tested."""
    m = _ACC.search(sseqid or "")
    return m.group(1) if m else (sseqid or "").split("|")[-1].strip() or sseqid


def parse_outfmt6(path, columns=OUTFMT6):
    """Read a tab-delimited BLAST outfmt6 table -> list[dict]. Pure; tested."""
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            rows.append({columns[i]: parts[i] for i in range(min(len(columns), len(parts)))})
    return rows


def hits_to_candidates(rows, query, marker, max_hits=3, min_pident=0.0):
    """BLAST hits -> ordered, de-duplicated candidate list. Pure; unit-tested.

    Ranks by bitscore desc, dedups by resolved accession (keeps the best hit per genome),
    drops self-ish/below-threshold hits, and keeps the top `max_hits`. Each candidate is a
    REFERENCE row for build_phylo_panel with selection_basis=marker_blast_<marker>.
    """
    seen, cands = set(), []
    for r in sorted(rows, key=lambda x: float(x.get("bitscore", 0) or 0), reverse=True):
        try:
            pid = float(r.get("pident", 0) or 0)
        except ValueError:
            pid = 0.0
        if pid < min_pident:
            continue
        acc = accession_from_subject(r.get("sseqid", ""))
        if not acc or acc in seen:
            continue
        # never propose the query itself as its own comparator
        if query and query.lower() in acc.lower():
            continue
        seen.add(acc)
        cands.append({"candidate_id": acc, "role": "REFERENCE", "source_path": "",
                      "selection_basis": f"marker_blast_{marker}",
                      "related_query_ids": query, "pident": f"{pid:.1f}"})
        if len(cands) >= max_hits:
            break
    return cands


def write_panel(cands, path, query=None):
    """Write candidates (+ the query as a QUERY row) as a build_phylo_panel TSV."""
    with open(path, "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t")
        w.writerow(PANEL_COLS)
        if query:
            w.writerow([query, "QUERY", "", "", ""])
        for c in cands:
            w.writerow([c["candidate_id"], c["role"], c["source_path"],
                        c["selection_basis"], c["related_query_ids"]])


def cmd_plan_blast(a):
    markers = [m.strip() for m in a.markers.split(",") if m.strip()]
    emit("# marker_candidate_search: PLAN ONLY — review, then run with approval "
          "(reference discovery is a networked step).")
    emit(f"# query={a.query}  assembly={a.assembly}  channel="
          f"{'REMOTE NCBI' if a.remote else 'LOCAL DB'}")
    for m in markers:
        if m in RRNA_MARKERS:
            emit(f"\n## {m}: extract rRNA (needs barrnap; rRNA cannot be blastp-seeded)")
            emit(f"barrnap --kingdom bac {a.assembly} | "
                  f"awk '$3==\"rRNA\" && /16S/' > {a.query}_{m}.gff   # then bedtools getfasta")
            db = a.db or "<local 16S RefSeq db>"
            if a.remote:
                emit(f"blastn -query {a.query}_{m}.fna -db nt -remote "
                      f"-outfmt 6 -max_target_seqs 25 -out {a.query}_{m}_hits.tsv   "
                      f"# NO personal email/ID; rate-limited")
            else:
                emit(f"blastn -query {a.query}_{m}.fna -db {db} "
                      f"-outfmt 6 -max_target_seqs 25 -num_threads 4 -out {a.query}_{m}_hits.tsv")
        elif m in MARKER_SEEDS:
            seed = os.path.join(SEEDS_DIR, MARKER_SEEDS[m])
            emit(f"\n## {m}: protein marker (seed {seed})", f"prodigal -i {a.assembly} -a {a.query}.faa -p single -q   # once per assembly", sep="\n")
            db = a.db or "<local RefSeq protein db>"
            emit(f"blastp -query {seed} -db {db} "
                  f"-outfmt 6 -max_target_seqs 25 -num_threads 4 -out {a.query}_{m}_hits.tsv")
        else:
            emit(f"# WARN unknown marker '{m}' (known: 16S, {', '.join(MARKER_SEEDS)})")
    emit(f"\n# then: python tools/marker_candidate_search.py to-panel "
          f"--hits {a.query}_<marker>_hits.tsv --query {a.query} --marker <marker> "
          f"--out {a.query}_candidates.tsv")
    return 0


def cmd_to_panel(a):
    rows = parse_outfmt6(a.hits)
    cands = hits_to_candidates(rows, a.query, a.marker,
                               max_hits=a.max_hits, min_pident=a.min_pident)
    if a.out:
        write_panel(cands, a.out, query=a.query)
        sys.stderr.write(f"wrote {len(cands)} candidate(s) + query -> {a.out}\n")
    else:
        w = _SafeWriter(sys.stdout, delimiter="\t")
        w.writerow(PANEL_COLS)
        for c in cands:
            w.writerow([c[k] for k in PANEL_COLS])
    sys.stderr.write("  next: merge marker panels, then build_phylo_panel.py -> "
                     "plan_gtotree_iqtree.py -> APPROVAL -> tree.\n")
    return 0


def cmd_plan_download(a):
    rows = list(csv.DictReader(open(a.panel), delimiter="\t"))
    accs = [r["candidate_id"] for r in rows if r.get("role") == "REFERENCE"]
    lines = ["#!/usr/bin/env bash",
             "# PLAN ONLY — genome download is a networked, approval-gated step. Review first.",
             "set -euo pipefail"]
    for acc in accs:
        lines.append(f"datasets download genome accession {acc} "
                     f"--include genome --filename {acc}.zip   # then unzip -> <acc>.fna")
    out = "\n".join(lines) + "\n"
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(out)
        sys.stderr.write(f"wrote {len(accs)} download command(s) -> {a.out} (run with approval)\n")
    else:
        emit(out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="marker-BLAST comparator discovery (plan-only)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan-blast")
    p.add_argument("--assembly", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--markers", default="16S,rpoB")
    p.add_argument("--db")
    p.add_argument("--remote", action="store_true")
    p.set_defaults(fn=cmd_plan_blast)

    p = sub.add_parser("to-panel")
    p.add_argument("--hits", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--marker", required=True)
    p.add_argument("--max-hits", type=int, default=3)
    p.add_argument("--min-pident", type=float, default=0.0)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_to_panel)

    p = sub.add_parser("plan-download")
    p.add_argument("--panel", required=True)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_plan_download)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())

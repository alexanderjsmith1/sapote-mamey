#!/usr/bin/env python3
"""phylo_autopilot.py — one front door for "upload 16S and/or genomes -> gated trees".

The pipeline pieces already exist and are gated:
  * 16S single-locus  -> tools/phylo_place.py  (build-ref -> place -> report; EPA-ng)
  * whole genomes     -> tools/build_tree.sh   (phylo_preflight -> GToTree -> IQ-TREE)
  * a tree is only shown after tools/tree_sanity_check.py PASSES.

What did NOT exist, and what this adds, is the GLUE a user needs to not think about any of that:

  1. CLASSIFY each uploaded file as an rRNA locus (~1-2 kb single nucleotide seq), a whole genome
     (many/long nucleotide contigs), or protein — heuristic, no network.
  2. ASSIGN a genus to every 16S query by top-hit BLAST against a curated 16S type-strain DB, and
     ROUTE it to the right per-genus / per-cohort tree. Crucially, a query whose nearest type strain
     is OUTSIDE the actinomycete target set (a Proteobacterium/Bacteroidota contaminant, say) is
     FLAGGED, never silently forced onto an actinomycete backbone — the exact failure this cohort
     hit in practice (AS-XXX -> Pseudescherichia, AS-XXX -> Taibaiella).
  3. AUTO-BUILD the reference set for each group by pulling type strains for exactly the observed
     genera out of that same DB (so a rare-genus upload gets a rare-genus backbone with no manual
     curation), then hand off to phylo_place with the group stamped in.

This module never runs ML inference itself and never renders a tree past a gate: it prepares inputs,
writes an auditable routing table, and shells the existing gated tools (which enforce the
tree-approval and sanity gates). It is import-safe: the BLAST/DB calls are injectable so the routing
logic is unit-tested without a database present.

Claim-safety: a top-hit genus is a NEIGHBORHOOD, not a species identity or an ANI call; judgment is
deferred to the downstream tools and to the human.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

# --------------------------------------------------------------------------------------------------
# Routing config: which genera belong to which tree, and which are off-target / non-target.
# TARGET_GROUPS maps a route-class -> the group name phylo_place is called with. RARE_ACTINO_GENERA
# is the allowlist of actinomycete genera that share the "rare_genera" combined backbone; anything
# actinomycete but not here and not Streptomyces/Nocardia is OFF_TARGET_ACTINO (kept, flagged);
# anything not actinomycete at all is FLAG_OTHER (held out of the actino trees entirely).
# --------------------------------------------------------------------------------------------------
STREPTOMYCES = {"Streptomyces", "Streptomydes", "Streptomyes"}  # tolerate common misspellings
NOCARDIA = {"Nocardia"}
RARE_ACTINO_GENERA = {
    "Micromonospora", "Actinomadura", "Pseudonocardia", "Saccharopolyspora", "Actinomycetospora",
    "Saccharothrix", "Kribbella", "Streptosporangium", "Amycolatopsis", "Actinacidiphila", "Kutzneria",
    "Kitasatospora", "Nocardiopsis", "Nocardioides", "Peterkaempfera", "Actinophytocola", "Actinoplanes",
    "Gandjariella", "Actinospineispora", "Microlunatus", "Jongsikchunia", "Micropolyspora",
    "Lentzea", "Actinosynnema", "Dactylosporangium", "Catellatospora", "Nonomuraea", "Actinocorallia",
}
# Actinomycetota but a distant order from the target discovery set — real, but not for these trees.
OFF_TARGET_ACTINO_GENERA = {
    "Brachybacterium", "Microbacterium", "Kocuria", "Dietzia", "Tsukamurella", "Mycolicibacterium",
    "Mycobacterium", "Corynebacterium", "Rhodococcus", "Gordonia", "Arthrobacter", "Cellulomonas",
    "Micrococcus", "Bifidobacterium",
}

ROUTE_STREPTOMYCES = "STREPTOMYCES"
ROUTE_NOCARDIA = "NOCARDIA"
ROUTE_RARE = "RARE_ACTINO"
ROUTE_OFF_TARGET = "OFF_TARGET_ACTINO"
ROUTE_FLAG = "FLAG_OTHER"

ROUTE_TO_GROUP = {
    ROUTE_STREPTOMYCES: "streptomyces",
    ROUTE_NOCARDIA: "nocardia",
    ROUTE_RARE: "rare_genera",
}


def route_genus(genus: str) -> str:
    """Map a top-hit genus to a route-class. Bracketed provisional names (`[Mycobacterium]`) and a
    trailing 'sp.'/'sp' are normalised away first."""
    g = re.sub(r"[\[\]]", "", (genus or "")).strip()
    g = re.sub(r"\s+(sp\.?|genomosp\.?)$", "", g)
    if g in STREPTOMYCES:
        return ROUTE_STREPTOMYCES
    if g in NOCARDIA:
        return ROUTE_NOCARDIA
    if g in RARE_ACTINO_GENERA:
        return ROUTE_RARE
    if g in OFF_TARGET_ACTINO_GENERA:
        return ROUTE_OFF_TARGET
    return ROUTE_FLAG


# --------------------------------------------------------------------------------------------------
# Input classification (heuristic, no network).
# --------------------------------------------------------------------------------------------------
_PROT_ONLY = set("EFILPQZ")  # amino-acid-only letters that never appear in a DNA alphabet


def _fasta_records(path):
    name, seq = None, []
    with open(path) as fh:
        for ln in fh:
            if ln.startswith(">"):
                if name is not None:
                    yield name, "".join(seq)
                name, seq = ln[1:].strip(), []
            else:
                seq.append(ln.strip())
    if name is not None:
        yield name, "".join(seq)


def classify_input(path: str, rrna_max_len=5_000, genome_min_contig=10_000,
                   genome_min_total=500_000) -> str:
    """Return 'protein', 'rrna', or 'genome'.

    Classification is by per-record LENGTH, not record count: a user may legitimately upload one
    multi-FASTA holding many 16S sequences (one per strain), which must NOT be mistaken for a genome.
    A genome is recognised by having any long contig (>= genome_min_contig) or a large total
    (>= genome_min_total); an rRNA set is one-or-many records that are all short (<= rrna_max_len).
    """
    recs = list(_fasta_records(path))
    if not recs:
        return "empty"
    total = sum(len(s) for _, s in recs)
    max_len = max(len(s) for _, s in recs)
    letters = set("".join(s.upper() for _, s in recs[:5]))
    if letters & _PROT_ONLY:
        return "protein"
    if max_len >= genome_min_contig or total >= genome_min_total:
        return "genome"
    if max_len <= rrna_max_len:
        return "rrna"
    return "genome"


# --------------------------------------------------------------------------------------------------
# Genus assignment: parse a BLAST tabular result (qseqid stitle pident length ...). The runner is
# injectable so tests exercise the parser + router with no DB.
# --------------------------------------------------------------------------------------------------
_ACC_LEAD = re.compile(r"^(NR_?|[A-Z]{1,2}_?)\d", re.I)  # NR_######, NZ_..., two-letter accessions


def _title_genus(stitle: str) -> str:
    """The genus from a subject title. `blastn -outfmt 6 stitle` leads with the genus, but a
    `blastdbcmd` %t title leads with the accession (`NR_###### Genus species ...`) — skip a leading
    accession-like token so BOTH conventions yield the genus."""
    toks = stitle.split()
    if not toks:
        return ""
    first = toks[0]
    if _ACC_LEAD.match(first) and len(toks) > 1:
        first = toks[1]
    return re.sub(r"[\[\]]", "", first)


def parse_blast_genus(blast_tsv_text: str) -> dict:
    """{qseqid: {'genus','pident','aln_len','title'}} from `-outfmt '6 qseqid stitle pident length'`,
    keeping the first (best) hit per query."""
    out = {}
    for ln in blast_tsv_text.splitlines():
        p = ln.rstrip("\n").split("\t")
        if len(p) < 4:
            continue
        qid, stitle, pid, aln = p[0], p[1], p[2], p[3]
        if qid in out:
            continue
        genus = _title_genus(stitle)
        try:
            pidf = float(pid)
        except ValueError:
            pidf = 0.0
        out[qid] = {"genus": genus, "pident": pidf, "aln_len": aln, "title": stitle}
    return out


def assign_genus(query_fasta, db, blastn="blastn", threads=2, runner=subprocess.run) -> dict:
    r = runner([blastn, "-query", query_fasta, "-db", db, "-max_target_seqs", "1", "-max_hsps", "1",
                "-num_threads", str(threads), "-outfmt", "6 qseqid stitle pident length"],
               capture_output=True, text=True)
    if getattr(r, "returncode", 1) != 0:
        raise RuntimeError(f"blastn failed: {getattr(r,'stderr','')[:400]}")
    return parse_blast_genus(r.stdout)


def genera_for_reference(assigned: dict) -> dict:
    """Group observed genera by their target group name. Only routable actino classes get a
    reference; FLAG_OTHER / OFF_TARGET are reported, not built into a tree."""
    groups = {}
    for _q, info in assigned.items():
        cls = route_genus(info["genus"])
        grp = ROUTE_TO_GROUP.get(cls)
        if grp is None:
            continue
        groups.setdefault(grp, set()).add(re.sub(r"[\[\]]", "", info["genus"]).strip())
    return {g: sorted(s) for g, s in groups.items()}


def build_reference_fasta(genera, db, out_fasta, blastdbcmd="blastdbcmd", cap_per_genus=30,
                          sentinels=("Streptomyces", "Nocardia"), sentinel_cap=8,
                          outgroup=("Corynebacterium",), outgroup_cap=2, runner=subprocess.run) -> int:
    """Pull up to cap_per_genus type-strain 16S per genus (plus a few sentinels + a distant outgroup)
    out of a BLAST 16S DB into out_fasta. Returns the sequence count. Genus membership is decided on
    the DB title's leading word after the accession — the same convention phylo_place uses."""
    r = runner([blastdbcmd, "-db", db, "-entry", "all", "-outfmt", "%a\t%t"],
               capture_output=True, text=True)
    if getattr(r, "returncode", 1) != 0:
        raise RuntimeError(f"blastdbcmd title dump failed: {getattr(r,'stderr','')[:400]}")
    titles = [ln.split("\t", 1) for ln in r.stdout.splitlines() if "\t" in ln]

    want = []
    for g, cap in ([(x, cap_per_genus) for x in genera]
                   + [(x, sentinel_cap) for x in sentinels]
                   + [(x, outgroup_cap) for x in outgroup]):
        n = 0
        for acc, title in titles:
            first = title.strip().split()[0] if title.strip().split() else ""
            if first == g:
                want.append(acc)
                n += 1
                if n >= cap:
                    break
    want = sorted(set(want))
    if not want:
        raise RuntimeError("no reference accessions matched the requested genera")
    accfile = out_fasta + ".acc"
    with open(accfile, "w") as fh:
        fh.write("\n".join(want) + "\n")
    r2 = runner([blastdbcmd, "-db", db, "-entry_batch", accfile, "-outfmt", "%f"],
                capture_output=True, text=True)
    if getattr(r2, "returncode", 1) != 0:
        raise RuntimeError(f"blastdbcmd fetch failed: {getattr(r2,'stderr','')[:400]}")
    with open(out_fasta, "w") as fh:
        fh.write(r2.stdout)
    return r2.stdout.count(">")


def write_routing_table(assigned: dict, out_tsv: str) -> None:
    with open(out_tsv, "w") as fh:
        fh.write("query\ttophit_genus\tpident\taln_len\troute_class\tgroup\ttophit_title\n")
        for q in sorted(assigned):
            info = assigned[q]
            cls = route_genus(info["genus"])
            grp = ROUTE_TO_GROUP.get(cls, "-")
            fh.write(f"{q}\t{info['genus']}\t{info['pident']:.2f}\t{info['aln_len']}\t"
                     f"{cls}\t{grp}\t{info['title']}\n")


def plan_from_inputs(paths) -> dict:
    """Classify a list of uploaded files into {'rrna':[...], 'genome':[...], 'protein':[...]}."""
    plan = {"rrna": [], "genome": [], "protein": [], "empty": []}
    for p in paths:
        plan.setdefault(classify_input(p), []).append(p)
    return plan


# --------------------------------------------------------------------------------------------------
def workspace_root_guess(marker="OFFICIAL_DATA/STRAIN_METADATA.tsv"):
    """First directory holding OFFICIAL_DATA/STRAIN_METADATA.tsv among: the cwd's parents (the caller's
    workspace), then this file's parents. None if nowhere (then nothing is exported and phylo_place decides)."""
    from pathlib import Path as _P
    here = os.path.dirname(os.path.abspath(__file__)); cwd = os.path.abspath(os.getcwd())
    for c in [cwd] + [str(q) for q in _P(cwd).parents] + [here] + [str(q) for q in _P(here).parents]:
        if os.path.exists(os.path.join(c, marker)):
            return c
    return None


# CLI. `plan` and `route` are dry (no ML); `run-16s` shells phylo_place per group (gated downstream).
# --------------------------------------------------------------------------------------------------
def _iter_inputs(indir):
    for root, _d, files in os.walk(indir):
        for f in files:
            if f.lower().endswith((".fa", ".fasta", ".fna", ".faa", ".fas")):
                yield os.path.join(root, f)


def cmd_plan(a):
    plan = plan_from_inputs(list(_iter_inputs(a.indir)))
    print(json.dumps({k: v for k, v in plan.items() if v}, indent=2))


def cmd_route(a):
    assigned = assign_genus(a.query, a.db, threads=a.threads)
    write_routing_table(assigned, a.out)
    refs = genera_for_reference(assigned)
    from collections import Counter
    cls = Counter(route_genus(i["genus"]) for i in assigned.values())
    print(json.dumps({"n_query": len(assigned), "route_classes": dict(cls),
                      "reference_genera_by_group": refs, "routing_table": a.out}, indent=2))


def cmd_run_16s(a):
    """Route a 16S multi-FASTA, auto-build a reference for one group, and (unless --dry-run) shell
    phylo_place for that group. phylo_place enforces the tree-approval gate; this never bypasses it."""
    os.makedirs(a.outdir, exist_ok=True)
    assigned = assign_genus(a.query, a.db, threads=a.threads)
    write_routing_table(assigned, os.path.join(a.outdir, "routing_table.tsv"))
    refs = genera_for_reference(assigned)
    genera = refs.get(a.group, [])
    if not genera:
        print(f"[autopilot] no queries routed to group '{a.group}'. Available: {sorted(refs)}")
        return 2
    ref_fa = os.path.join(a.outdir, f"{a.group}_reference.fasta")
    n = build_reference_fasta(genera, a.db, ref_fa, cap_per_genus=a.cap_per_genus)
    # subset the query fasta to the members of this group
    members = {q for q, i in assigned.items() if ROUTE_TO_GROUP.get(route_genus(i["genus"])) == a.group}
    grp_q = os.path.join(a.outdir, f"{a.group}_query.fasta")
    with open(grp_q, "w") as out:
        for name, seq in _fasta_records(a.query):
            if name.split()[0] in members:
                out.write(f">{name}\n{seq}\n")
    print(f"[autopilot] group={a.group} genera={genera} ref_seqs={n} queries={len(members)}")
    if a.dry_run:
        print(f"[autopilot] dry-run: reference={ref_fa} query={grp_q} — "
              f"run phylo_place 'all' with --approved-by to build the gated tree.")
        return 0
    pp = a.phylo_place or os.path.join(os.path.dirname(os.path.abspath(__file__)), "phylo_place.py")
    cmd = [sys.executable, pp, "all", ref_fa, "--group", a.group, "--query", grp_q,
           "--outdir", os.path.join(a.outdir, "placement"), "--threads", str(a.threads),
           "--bootstrap", str(a.bootstrap),
           "--one-per-species", "--approved-by", a.approved_by]
    print("[autopilot] ->", " ".join(cmd))
    env = dict(os.environ)
    if not (env.get("SAPOTE_WORKSPACE_ROOT") or env.get("SAPOTE_ROOT")):
        # AMBER-409 patch 2 (defence in depth): phylo_place resolves OFFICIAL_DATA through workspace_root(),
        # which falls back to cwd. Pin it here so the front door works from any directory even against an
        # engine without the phylo_place walk-up.
        wr = workspace_root_guess()
        if wr:
            env["SAPOTE_WORKSPACE_ROOT"] = wr
    return subprocess.run(cmd, env=env).returncode


def build_argparser():
    ap = argparse.ArgumentParser(description="Autopilot: uploaded 16S/genomes -> routed, gated trees.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="classify uploaded files (16S / genome / protein), no ML")
    p.add_argument("indir")
    p.set_defaults(func=cmd_plan)

    r = sub.add_parser("route", help="assign genus + route every 16S query (writes a routing table)")
    r.add_argument("--query", required=True)
    r.add_argument("--db", required=True, help="BLAST 16S type-strain DB prefix")
    r.add_argument("--out", default="routing_table.tsv")
    r.add_argument("--threads", type=int, default=2)
    r.set_defaults(func=cmd_route)

    x = sub.add_parser("run-16s", help="route + auto-build reference + gated phylo_place for one group")
    x.add_argument("--query", required=True)
    x.add_argument("--db", required=True)
    x.add_argument("--group", required=True, choices=sorted(set(ROUTE_TO_GROUP.values())))
    x.add_argument("--outdir", required=True)
    x.add_argument("--approved-by", default="", help="records tree-approval authorization (required unless --dry-run)")
    x.add_argument("--cap-per-genus", type=int, default=30)
    x.add_argument("--bootstrap", type=int, default=10,
                   help="reference-backbone bootstraps (default 10: EPA-ng supplies per-query "
                        "support, so a placement backbone does not need 100 — that costs hours). "
                        "Raise only to publish the reference tree itself with node support.")
    x.add_argument("--threads", type=int, default=2)
    x.add_argument("--phylo-place", default="")
    x.add_argument("--dry-run", action="store_true")
    x.set_defaults(func=cmd_run_16s)
    return ap


def main(argv=None):
    a = build_argparser().parse_args(argv)
    if getattr(a, "cmd", None) == "run-16s" and not a.dry_run and not a.approved_by:
        print("[autopilot] refusing to build a tree without --approved-by (tree-approval gate). "
              "Use --dry-run to prepare inputs only.", file=sys.stderr)
        return 1
    return a.func(a) or 0


if __name__ == "__main__":
    raise SystemExit(main())

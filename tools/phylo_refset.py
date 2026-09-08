#!/usr/bin/env python3
"""phylo_refset.py — build a RIGHT-SIZED, DE-DUPLICATED 16S reference set for phylogenetic placement.

Two problems this fixes, both raised by the Developer or User:
  1. "someone downloaded 400+ nocardia genomes, we don't need THAT many!" -> reference sets must be
     query-relevant and right-sized, not bulk. => marker-BLAST: BLAST each query 16S against the local
     RefSeq 16S DB, take the top-N NAMED hits per query, union them. That is the whole backbone.
  2. "You have duplicate reference strains in your streptomyces tree, where you looked up 2 culture-
     collection identifiers for the same strain." => dedup, in two tiers:
       Tier 1 (metadata): collapse records that are the SAME species + SAME strain token but have two
              RefSeq accessions (e.g. S. mashuensis DSM 40221 = NR_026174 = NR_116638).
       Tier 2 (sequence): collapse SAME-species records whose 16S is near-identical (>= --identity, default
              99.5%) -> these are the same physical type strain deposited under different culture-collection
              IDs (e.g. sampsonii ATCC 25495 vs NRRL B-12325; cavourensis/atroolivaceus). This is the case
              a strain-token match alone cannot catch, so it is done by the sequence itself.
     Every collapse is written to a report so the decision is auditable, never silent.

Then it appends the ONE correct outgroup pulled from the outgroup generator (outgroup_registry.py ->
OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv), so the finished refs.fasta is ready for `phylo_place.py build-ref`.

Subcommands:
  marker-blast --query Q.fasta [--top 5] [--db DB] --out refs_raw.fasta
  dedup refs.fasta --out refs_dedup.fasta [--identity 99.5] [--report R.tsv]
  add-outgroup refs.fasta --genus Streptomyces [--scope genus] --out refs_final.fasta
  build --query Q.fasta --group streptomyces --outgroup-genus Streptomyces --out refs_final.fasta
        (marker-blast -> dedup -> add-outgroup, one shot)

Read-only against the RefSeq DB; needs the 'blast' env (blastn, blastdbcmd, makeblastdb). Candidate Tools/
asset; pairs with phylo_place.py. NOT engine-wired.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, re, subprocess, sys, tempfile
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bundle root for `import mamey` (v9.7.367 A10)
from mamey.workspace_root import workspace_root

ROOT = str(workspace_root())
DB16S = os.environ.get("NCBI_16S_DB", f"{ROOT}/Tools/databases/ncbi_16S_RefSeq/16S_ribosomal_RNA")
BLAST_BIN = os.environ.get("BLAST_BIN", f"{ROOT}/miniconda3/envs/blast/bin")

UNNAMED = re.compile(r"\b(sp|cf|aff|bacterium|uncultured|endophyte|symbiont|genomosp)\b\.?", re.I)
# recognized culture collections -> priority when choosing which duplicate to KEEP (type-strain collections first)
COLL_PRIORITY = ["DSM", "ATCC", "NBRC", "JCM", "NRRL", "CBS", "LMG", "KCTC", "CGMCC", "BCRC", "VKM"]


def _bin(name):
    p = os.path.join(BLAST_BIN, name)
    return p if os.path.exists(p) else (__import__("shutil").which(name) or "")


def _read_fasta(path):
    """Return list of (header, seq) preserving order."""
    recs, nm, buf = [], None, []
    for ln in open(path, encoding="utf-8", errors="replace"):
        if ln.startswith(">"):
            if nm is not None:
                recs.append((nm, "".join(buf)))
            nm = ln[1:].strip(); buf = []
        else:
            buf.append(ln.strip())
    if nm is not None:
        recs.append((nm, "".join(buf)))
    return recs


def _write_fasta(recs, path):
    with open(path, "w") as fh:
        for h, s in recs:
            fh.write(f">{h}\n")
            for i in range(0, len(s), 80):
                fh.write(s[i:i + 80] + "\n")


def _parse_header(h):
    """(genus, species, strain_token_norm, accession). Robust to 'strain_' and to no-strain headers."""
    acc = ""
    m = re.search(r"(N[RG]_\d+(?:\.\d+)?)", h)
    if m:
        acc = m.group(1)
    core = h[:m.start()].rstrip("_") if m else h
    toks = core.split("_")
    genus = toks[0] if toks else ""
    species = toks[1] if len(toks) > 1 else ""
    rest = toks[2:]
    if rest and rest[0] == "strain":
        rest = rest[1:]
    strain = re.sub(r"[^A-Za-z0-9]", "", "".join(rest)).upper()
    return genus, species, strain, acc


def _coll_rank(strain):
    for i, c in enumerate(COLL_PRIORITY):
        if strain.startswith(c):
            return i
    return len(COLL_PRIORITY)


def _rep_score(rec):
    """Higher = better representative to KEEP. Prefer a recognized type collection, a present strain token,
    a longer sequence, then a stable (lower) accession for determinism."""
    h, s = rec
    g, sp, strain, acc = _parse_header(h)
    accnum = int(re.sub(r"\D", "", acc) or 0)
    return (-_coll_rank(strain), 1 if strain else 0, len(s.replace("-", "")), -accnum)


# ---------------------------------------------------------------- dedup
def dedup(recs, identity=99.5, min_cov=90.0, report=None, verbose=True):
    """Two-tier collapse. Returns (kept_recs, collapses[list of dicts])."""
    collapses = []
    # ---- Tier 1: same (genus, species, strain_token) ----
    groups = {}
    for r in recs:
        g, sp, strain, acc = _parse_header(r[0])
        key = (g.lower(), sp.lower(), strain)
        groups.setdefault(key, []).append(r)
    tier1 = []
    for key, members in groups.items():
        if len(members) == 1 or key[2] == "":     # no strain token => can't assert same-strain by metadata
            tier1.extend(members if key[2] else members)
            continue
        members.sort(key=_rep_score, reverse=True)
        keep = members[0]
        tier1.append(keep)
        for drop in members[1:]:
            collapses.append({"tier": 1, "kept": keep[0], "dropped": drop[0],
                              "reason": "same species+strain token (duplicate RefSeq accession)",
                              "identity": ""})
    # records with empty strain token were appended once above only if key[2]=="" branch; ensure no dup:
    tier1 = [r for i, r in enumerate(tier1) if r not in tier1[:i]]

    # ---- Tier 2: same-species near-identical 16S (different culture-collection IDs) ----
    if len(tier1) > 1:
        bn = _bin("makeblastdb"); bl = _bin("blastn")
        if not (bn and bl):
            if verbose:
                emit("[dedup] WARN: blast env not found — Tier 2 (sequence) skipped; Tier 1 only.")
        else:
            with tempfile.TemporaryDirectory() as td:
                # safe temp ids -> map back
                idmap = {}
                fa = os.path.join(td, "in.fasta")
                with open(fa, "w") as fh:
                    for i, (h, s) in enumerate(tier1):
                        sid = f"s{i}"
                        idmap[sid] = (h, s)
                        fh.write(f">{sid}\n{s}\n")
                subprocess.run([bn, "-in", fa, "-dbtype", "nucl", "-out", os.path.join(td, "db")],
                               capture_output=True, text=True)
                res = subprocess.run([bl, "-query", fa, "-db", os.path.join(td, "db"),
                                      "-outfmt", "6 qseqid sseqid pident length qlen slen", "-max_target_seqs", "50"],
                                     capture_output=True, text=True)
                # union-find over same-species near-identical pairs
                parent = {sid: sid for sid in idmap}

                def find(x):
                    while parent[x] != x:
                        parent[x] = parent[parent[x]]; x = parent[x]
                    return x

                def union(a, b):
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        parent[rb] = ra
                pair_ident = {}
                for ln in res.stdout.splitlines():
                    q, s, pid, length, qlen, slen = ln.split("\t")
                    if q == s:
                        continue
                    pid = float(pid); length = int(length); qlen = int(qlen); slen = int(slen)
                    cov = 100.0 * length / min(qlen, slen)
                    gq, spq, _, _ = _parse_header(idmap[q][0])
                    gs, sps, _, _ = _parse_header(idmap[s][0])
                    if (gq.lower(), spq.lower()) != (gs.lower(), sps.lower()):
                        continue                       # only collapse within the SAME species (conservative)
                    if pid >= identity and cov >= min_cov:
                        union(q, s)
                        pair_ident[tuple(sorted((q, s)))] = pid
                clusters = {}
                for sid in idmap:
                    clusters.setdefault(find(sid), []).append(sid)
                kept = []
                for root, members in clusters.items():
                    recs_m = [idmap[m] for m in members]
                    recs_m_sorted = sorted(recs_m, key=_rep_score, reverse=True)
                    keep = recs_m_sorted[0]
                    kept.append(keep)
                    for drop in recs_m_sorted[1:]:
                        # find an identity to quote
                        ids = [v for k, v in pair_ident.items()]
                        collapses.append({"tier": 2, "kept": keep[0], "dropped": drop[0],
                                          "reason": "same species, 16S-indistinguishable (same strain under a different "
                                                    "culture-collection ID, or a con-specific duplicate); redundant tip",
                                          "identity": f"{max(ids):.2f}" if ids else ""})
                tier1 = kept

    kept = tier1
    if report:
        with open(report, "w") as fh:
            fh.write("tier\tkept\tdropped\treason\tpct_identity\n")
            for c in collapses:
                fh.write(f"{c['tier']}\t{c['kept']}\t{c['dropped']}\t{c['reason']}\t{c['identity']}\n")
    if verbose:
        emit(f"[dedup] {len(recs)} -> {len(kept)} references ({len(collapses)} duplicates collapsed)")
        for c in collapses:
            emit(f"   T{c['tier']} drop {c['dropped']}\n        keep {c['kept']}  ({c['reason']}"
                  f"{'; %s%% id' % c['identity'] if c['identity'] else ''})")
    return kept, collapses


# ---------------------------------------------------------------- marker-blast
def marker_blast(query, top=5, db=DB16S, verbose=True):
    """BLAST each query 16S vs RefSeq 16S; union of top-N NAMED hits; return refs as (header, seq)."""
    bl = _bin("blastn"); bdc = _bin("blastdbcmd")
    if not (bl and bdc):
        sys.exit("blastn/blastdbcmd not found; set BLAST_BIN or install the 'blast' env")
    # degap query if aligned
    qrecs = _read_fasta(query)
    with tempfile.TemporaryDirectory() as td:
        qfa = os.path.join(td, "q.fasta")
        _write_fasta([(h, s.replace("-", "")) for h, s in qrecs], qfa)
        res = subprocess.run([bl, "-query", qfa, "-db", db,
                              "-outfmt", "6 qseqid sacc pident length stitle", "-max_target_seqs", str(top * 4)],
                             capture_output=True, text=True)
        if res.returncode != 0:
            sys.exit(f"blastn failed:\n{res.stderr[:400]}")
        per_q = {}
        for ln in res.stdout.splitlines():
            parts = ln.split("\t")
            if len(parts) < 5:
                continue
            q, sacc, pid, length, stitle = parts[0], parts[1], parts[2], parts[3], parts[4]
            if UNNAMED.search(stitle.split(" 16S")[0]):   # skip sp./uncultured for the NAMED backbone
                continue
            per_q.setdefault(q, [])
            if len(per_q[q]) < top and sacc not in [a for a, _ in per_q[q]]:
                per_q[q].append((sacc, stitle))
        # union of accessions
        acc_title = {}
        for q, hits in per_q.items():
            for sacc, stitle in hits:
                acc_title.setdefault(sacc, stitle)
        if verbose:
            emit(f"[marker-blast] {len(qrecs)} queries -> {len(acc_title)} unique named reference accessions "
                  f"(top {top}/query)")
        # extract sequences + build clean headers
        recs = []
        for acc, title in sorted(acc_title.items()):
            seq = subprocess.run([bdc, "-db", db, "-entry", acc], capture_output=True, text=True)
            if seq.returncode != 0 or not seq.stdout.strip():
                continue
            body = "".join(seq.stdout.splitlines()[1:])
            # header: Genus_species_strain_ACC from the title
            t = re.sub(r"\s+16S ribosomal RNA.*$", "", title)
            t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
            recs.append((f"{t}_{acc}", body))
    return recs


# ---------------------------------------------------------------- add-outgroup
def add_outgroup(recs, genus, scope="genus", verbose=True):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import outgroup_registry as OG
    except Exception as e:
        sys.exit(f"cannot import outgroup_registry.py (keep it beside phylo_refset.py): {e}")
    fa = OG.get_16s(genus, scope=scope, quiet=not verbose)
    og = _read_fasta(fa)
    have = {_parse_header(h)[:2] for h, _ in recs}
    added = [r for r in og if _parse_header(r[0])[:2] not in have]
    if verbose:
        emit(f"[add-outgroup] {genus} -> {[h for h,_ in added] or 'already present'}")
    return recs + added


# ---------------------------------------------------------------- subcommands
def cmd_marker_blast(a):
    recs = marker_blast(a.query, top=a.top, db=a.db)
    _write_fasta(recs, a.out)
    emit(f"[marker-blast] wrote {len(recs)} refs -> {a.out}")
    return 0


def cmd_dedup(a):
    recs = _read_fasta(a.refs)
    kept, _ = dedup(recs, identity=a.identity, report=a.report or a.out.replace(".fasta", "_DEDUP_REPORT.tsv"))
    _write_fasta(kept, a.out)
    emit(f"[dedup] wrote {len(kept)} refs -> {a.out}")
    return 0


def cmd_add_outgroup(a):
    recs = _read_fasta(a.refs)
    recs = add_outgroup(recs, a.genus, a.scope)
    _write_fasta(recs, a.out)
    emit(f"[add-outgroup] wrote {len(recs)} refs -> {a.out}")
    return 0


def cmd_build(a):
    emit(f"== phylo_refset build: {a.group} ==")
    recs = marker_blast(a.query, top=a.top, db=a.db)
    kept, _ = dedup(recs, identity=a.identity,
                    report=a.out.replace(".fasta", "_DEDUP_REPORT.tsv"))
    og_genus = a.outgroup_genus or a.group.capitalize()
    kept = add_outgroup(kept, og_genus, a.scope)
    _write_fasta(kept, a.out)
    emit(f"[build] {a.group}: {len(kept)} references (deduped + outgroup) -> {a.out}\n"
          f"        next: phylo_place.py build-ref \"{a.out}\" --group {a.group} --approved-by <name>")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Right-sized, de-duplicated 16S reference set for placement.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    mb = sub.add_parser("marker-blast"); mb.add_argument("--query", required=True)
    mb.add_argument("--top", type=int, default=5); mb.add_argument("--db", default=DB16S)
    mb.add_argument("--out", required=True); mb.set_defaults(func=cmd_marker_blast)

    dd = sub.add_parser("dedup"); dd.add_argument("refs"); dd.add_argument("--out", required=True)
    dd.add_argument("--identity", type=float, default=99.5); dd.add_argument("--report")
    dd.set_defaults(func=cmd_dedup)

    ao = sub.add_parser("add-outgroup"); ao.add_argument("refs"); ao.add_argument("--genus", required=True)
    ao.add_argument("--scope", default="genus"); ao.add_argument("--out", required=True)
    ao.set_defaults(func=cmd_add_outgroup)

    bd = sub.add_parser("build"); bd.add_argument("--query", required=True); bd.add_argument("--group", required=True)
    bd.add_argument("--top", type=int, default=5); bd.add_argument("--db", default=DB16S)
    bd.add_argument("--identity", type=float, default=99.5)
    bd.add_argument("--outgroup-genus", default=""); bd.add_argument("--scope", default="genus")
    bd.add_argument("--out", required=True); bd.set_defaults(func=cmd_build)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())

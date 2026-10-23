#!/usr/bin/env python3
"""tools/locus_rarity_by_genus.py -- how rare is one antiSMASH region (a locus) among the genomes of each genus?

WHY THIS EXISTS
    The M5 locus comparison of 19-20 Oct 2026 (jobs J1, J11, J12: 224 AS loci) answered "in how many genomes of each
    genus does a region carrying this locus's genes occur?" with a script outside the bundle (fixed paths, the M5's
    run-7 region-protein set). This tool carries that method into the bundle, reading the region-protein kit that
    tools/protein_pcoa_ordinate.py extract already writes, so any user can rerun it on their own antiSMASH results.

INPUT
    --kit DIR            a protein_pcoa_ordinate.py extract kit: REGION_CDS.faa and REGION_CDS_META.tsv (columns id, source,
                         genus, strain, origin, locus_tag, subtype = antiSMASH gene_kind, region_product).
    --query-strain S     the strain whose region is the locus (META strain).
    --query-region F     the locus's region file name as in META `region` (e.g. NODE_14_..._cov_19.48.region001.gbk).
    --alias TEXT         the locus alias for the identity line (e.g. "neoabyssomicin B/abyssomicin (BGC0001694)").
    --exclude S          further strains left out of the targets (repeatable).
    --genome-table TSV   optional denominators: strain, source (isolate / reference_held / SID_held), genus, and optionally
                         assembly_accession and total_bp (used to count by assembly). Without it, denominators are the kit's
                         strains (a genome with no region at all is then not counted).
    --count-by B         assembly (default) or entry: what the main count and denominator columns count. Both are always
                         reported in the *_by_assembly and *_by_entry columns.

COUNTING BY ASSEMBLY (v1.1.0; the M5 duplicate-assembly rule of 21 Oct 2026)
    A genome collection can hold one assembly several times: CP053892 and CP053892.1, a WGS id and its GCA, GCF and GCA forms,
    a complete-genome CP/AP entry and the GCA entry of the same genome, or local re-assemblies. Each strain gets an assembly
    key: its assembly_accession, else its own id when that is a GCA/GCF accession, else its own id (GCF folded to GCA, version
    dropped in every case). Then strains of one genus with identical total_bp are merged into one key. A key counts once
    in each role (public reference, SID, isolate); a key passes a threshold when any of its strains does.
    ASSEMBLY_KEYS.tsv lists every strain's key and the rule that set it. Without total_bp only the id rules apply.

METHOD (the J1 v3 method)
    Query genes: every CDS of the locus region in the kit. Core genes: those with gene_kind biosynthetic or
    biosynthetic-additional. Targets: every kit CDS except MIBiG, the query strain and --exclude strains.
    DIAMOND blastp --more-sensitive --evalue 1e-5 --id <min-identity> --query-cover <min-query-cover> --max-target-seqs 0,
    the kit FASTA read directly; thresholds applied in DIAMOND and again here. A query gene is matched in a target region
    when any protein of that region hits it at >= --min-identity (50) over >= --min-query-cover (70) of the query gene.
    Per target region: genes matched (n of N), core genes matched (n of NC), mean best identity.
    Rarity per genus: genomes with a region at >= 50 % of all genes, >= 50 % of core genes and >= 30 % of core genes,
    counted apart for public references (reference_held), SID (SID_held) and isolates; combined public + SID kept.
    Listed: the query genus, any genus with a counted genome, and any genus whose best region matches >= 25 % of genes.

OUTPUT (--out DIR, must not exist)
    ASSEMBLY_KEYS.tsv, TARGET_REGIONS.tsv, TOP5_PUBLIC_REFERENCE.tsv (SID out), TOP5_REFERENCE.tsv (public + SID), TOP3_AS.tsv,
    RARITY_BY_GENUS.tsv, QUERY_GENES.tsv, LOCUS.txt, RECEIPT.json (kit file sha256, DIAMOND version, rule, counts).

Homology only: a matched gene set is sequence similarity, not product identity or production.
Refusals (exit 2): kit files missing, the query region absent or with no CDS, DIAMOND missing, --out existing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

_LOG = logging.getLogger("locus_rarity_by_genus")   # operator messages go through logging (repo_health print_calls)

__version__ = "1.1.0"
CORE_KINDS = ("biosynthetic", "biosynthetic-additional")
ROLE = {"isolate": "AS", "reference_held": "reference", "SID_held": "SID"}


class Refusal(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_tsv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def read_fasta(path, keep=None):
    seqs, cur = {}, None
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(">"):
                cur = line[1:].split()[0]
                cur = cur if keep is None or cur in keep else None
                if cur is not None:
                    seqs[cur] = []
            elif cur is not None:
                seqs[cur].append(line)
    return {k: "".join(v) for k, v in seqs.items()}


def write_tsv(path, rows, cols):
    with open(path, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def fold_accession(acc):
    """GCF_ folded to GCA_, trailing version dropped: GCF_000001.2 -> GCA_000001, CP053892.1 -> CP053892."""
    a = acc.strip().replace("GCF_", "GCA_")
    head, dot, tail = a.rpartition(".")
    return head if dot and tail.isdigit() else a


def assembly_keys(entries):
    """entries: dicts with strain, genus and optional assembly_accession / total_bp. Returns {strain: (key, rule)}."""
    key, rule = {}, {}
    for e in entries:
        acc = (e.get("assembly_accession") or "").strip(); s = e["strain"]
        if acc:
            key[s], rule[s] = fold_accession(acc), "assembly_accession"
        elif s.startswith(("GCA_", "GCF_")):
            key[s], rule[s] = fold_accession(s), "own GCA/GCF id"
        else:
            key[s], rule[s] = "id:" + fold_accession(s), "own id"
    parent = {}
    def find(k):
        while parent.get(k, k) != k:
            k = parent[k]
        return k
    first = {}
    for e in entries:                                  # same genus + identical total length = one assembly
        bp = (e.get("total_bp") or "").strip()
        if not bp or bp == "0":
            continue
        slot, k = (e["genus"], bp), key[e["strain"]]
        if slot not in first:
            first[slot] = k; continue
        a, b = find(first[slot]), find(k)
        if a != b:
            keep, drop = sorted((a, b), key=lambda x: (x.startswith("id:"), x))
            parent[drop] = keep
    return {s: (find(k), rule[s] + ("" if find(k) == k else f"; merged with {find(k)} (identical total_bp in genus)"))
            for s, k in key.items()}


BASES = ("assembly", "entry")


def rarity_table(rows, n_genes, n_core, query_genus, totals, keys, count_by="assembly"):
    """rows: target-region dicts (role, genus, target_strain, genes_matched, core_genes_matched).
    totals: genus -> role -> set of strains (denominators). keys: strain -> assembly key."""
    def cnt(strains, basis):
        return len({keys.get(s, (s,))[0] for s in strains}) if basis == "assembly" else len(strains)
    hit = {k: defaultdict(lambda: defaultdict(set)) for k in ("all50", "core50", "core30")}
    best = defaultdict(lambda: defaultdict(float))
    for r in rows:
        g, role, who = r["genus"], r["role"], r["target_strain"]
        gm, cm = r["genes_matched"], r["core_genes_matched"]
        if gm >= n_genes / 2: hit["all50"][g][role].add(who)
        if n_core and cm >= 0.5 * n_core: hit["core50"][g][role].add(who)
        if n_core and cm >= 0.3 * n_core: hit["core30"][g][role].add(who)
        for k, v in (("all", gm / n_genes), ("core", cm / n_core if n_core else 0.0)):
            best[g][k] = max(best[g][k], v)
            if role == "reference": best[g][k + "_pub"] = max(best[g][k + "_pub"], v)
    out, f = [], (lambda x: f"{x:.3f}")
    for g in sorted(set(totals) | set(hit["all50"]) | set(hit["core30"])):
        n = {k: (len(hit[k][g]["reference"]), len(hit[k][g]["SID"]), len(hit[k][g]["AS"])) for k in hit}
        if not (any(sum(v) for v in n.values()) or g == query_genus or best[g]["all"] >= 0.25):
            continue
        row = {"genus": g, "core_genes_in_locus": n_core, "count_basis": count_by}
        for basis in BASES:                            # both bases always reported; the main columns follow --count-by
            sfx = f"_by_{basis}"
            for k, lbl in (("all50", "ge50pct_genes"), ("core50", "ge50pct_core_genes"), ("core30", "ge30pct_core_genes")):
                pub, sid = cnt(hit[k][g]["reference"], basis), cnt(hit[k][g]["SID"], basis)
                both = cnt(hit[k][g]["reference"] | hit[k][g]["SID"], basis)
                for s, v in (("public", pub), ("SID", sid), ("ref_SID", both)):
                    row[f"genomes_with_region_{lbl}_{s}{sfx}"] = v
                    if basis == count_by: row[f"genomes_with_region_{lbl}_{s}"] = v
            den = (cnt(totals[g]["reference"], basis), cnt(totals[g]["SID"], basis), cnt(totals[g]["reference"] | totals[g]["SID"], basis))
            for s, v in zip(("public_genomes", "SID_genomes", "ref_SID_genomes"), den):
                row[s + sfx] = v
                if basis == count_by: row[s] = v
        row.update(AS_strains_with_region_ge50pct=n["all50"][2], AS_strains_with_region_ge50pct_core=n["core50"][2],
                   AS_strains_with_region_ge30pct_core=n["core30"][2], other_AS_strains_in_genus=len(totals[g]["AS"]),
                   best_fraction_matched_in_genus=f(best[g]["all"]), best_fraction_matched_in_genus_public=f(best[g]["all_pub"]),
                   best_core_fraction_matched_in_genus=f(best[g]["core"]) if n_core else "",
                   best_core_fraction_matched_in_genus_public=f(best[g]["core_pub"]) if n_core else "")
        out.append(row)
    return out


RARITY_COLS = ["genus", "core_genes_in_locus"] + [f"genomes_with_region_{l}_{s}" for l in ("ge50pct_genes", "ge50pct_core_genes", "ge30pct_core_genes")
                                                   for s in ("public", "SID", "ref_SID")] + \
    ["public_genomes", "SID_genomes", "ref_SID_genomes", "AS_strains_with_region_ge50pct", "AS_strains_with_region_ge50pct_core",
     "AS_strains_with_region_ge30pct_core", "other_AS_strains_in_genus", "best_fraction_matched_in_genus",
     "best_fraction_matched_in_genus_public", "best_core_fraction_matched_in_genus", "best_core_fraction_matched_in_genus_public",
     "count_basis"] + [f"{c}_by_{b}" for b in BASES for c in
                       [f"genomes_with_region_{l}_{s}" for l in ("ge50pct_genes", "ge50pct_core_genes", "ge30pct_core_genes")
                        for s in ("public", "SID", "ref_SID")] + ["public_genomes", "SID_genomes", "ref_SID_genomes"]]
TARGET_COLS = ["target_strain", "assembly_key", "role", "genus", "target_region_file", "region_product", "genes_matched", "genes_in_locus",
               "fraction_matched", "mean_identity_pct", "core_genes_matched", "core_genes_in_locus", "core_fraction_matched"]


def run(a):
    kit = a.kit; faa, mtsv = os.path.join(kit, "REGION_CDS.faa"), os.path.join(kit, "REGION_CDS_META.tsv")
    for p in (faa, mtsv):
        if not os.path.isfile(p):
            raise Refusal(f"kit file missing: {p}")
    if os.path.exists(a.out):
        raise Refusal(f"--out exists: {a.out}")
    dmd = a.diamond or shutil.which("diamond")
    if not dmd or not os.path.isfile(dmd):
        raise Refusal("DIAMOND not found (--diamond or PATH); it is never replaced")
    meta = read_tsv(mtsv)
    by_id = {r["id"]: r for r in meta}
    query = [r for r in meta if r["strain"] == a.query_strain and r["region"] == a.query_region]
    if not query:
        raise Refusal(f"query region {a.query_strain} / {a.query_region} has no CDS in the kit")
    qgenus = query[0]["genus"]
    excluded = {a.query_strain, *a.exclude}
    seqs = read_fasta(faa, keep={r["id"] for r in query})
    qids = [r["id"] for r in query]
    core = {r["id"] for r in query if r["subtype"] in CORE_KINDS}
    n, nc = len(qids), len(core)
    os.makedirs(a.out)
    work = tempfile.mkdtemp(prefix="locus-rarity-", dir=a.out)
    qfa = os.path.join(work, "query.faa")
    with open(qfa, "w") as fh:
        fh.writelines(f">{i}\n{seqs[i]}\n" for i in qids)
    cmd = [dmd, "blastp", "-q", qfa, "-d", faa, "--more-sensitive", "--evalue", "1e-5", "--id", str(a.min_identity),
           "--query-cover", str(a.min_query_cover), "--max-target-seqs", "0", "--threads", str(a.threads), "--quiet",
           "--outfmt", "6", "qseqid", "sseqid", "pident", "qcovhsp", "bitscore"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise Refusal(f"DIAMOND failed (rc {p.returncode}): {p.stderr.strip()[:300]}")
    version = subprocess.run([dmd, "version"], capture_output=True, text=True).stdout.strip()
    best = defaultdict(dict)                                   # (strain, origin) -> query id -> best identity
    for line in p.stdout.splitlines():
        q, s, pid, qc, _ = line.split("\t")
        t = by_id.get(s)
        if t is None or t["source"] not in ROLE or t["strain"] in excluded:
            continue
        if float(pid) < a.min_identity or float(qc) < a.min_query_cover:
            continue
        k = (t["strain"], t["origin"]); best[k][q] = max(best[k].get(q, 0.0), float(pid))
    region_of = {}
    for r in meta:
        if r["source"] in ROLE:
            region_of.setdefault((r["strain"], r["origin"]), r)
    rows = []
    for (strain, origin), hits in best.items():
        r = region_of[(strain, origin)]; cm = len(core & set(hits))
        rows.append(dict(target_strain=strain, role=ROLE[r["source"]], genus=r["genus"], target_region_file=r["region"],
                         region_product=r["region_product"], genes_matched=len(hits), genes_in_locus=n,
                         fraction_matched=f"{len(hits) / n:.3f}", mean_identity_pct=f"{statistics.mean(hits.values()):.1f}",
                         core_genes_matched=cm, core_genes_in_locus=nc, core_fraction_matched=f"{cm / nc:.3f}" if nc else ""))
    rows.sort(key=lambda r: (-r["genes_matched"], -float(r["mean_identity_pct"]), r["target_strain"], r["target_region_file"]))
    totals = defaultdict(lambda: defaultdict(set))
    if a.genome_table:
        entries = [r for r in read_tsv(a.genome_table) if r["source"] in ROLE]; denom = "GENOME_TABLE"
    else:
        denom = "KIT_STRAINS"
        entries = [dict(strain=s, source=src, genus=g) for s, (src, g) in
                   {r["strain"]: (r["source"], r["genus"]) for r in meta if r["source"] in ROLE}.items()]
    known = {e["strain"] for e in entries}
    entries += [dict(strain=s, source=r["source"], genus=r["genus"]) for (s, _), r in region_of.items() if s not in known]
    keys = assembly_keys(entries)
    for e in entries:
        if e["strain"] not in excluded and e["strain"] in known: totals[e["genus"]][ROLE[e["source"]]].add(e["strain"])
    for r in rows: r["assembly_key"] = keys[r["target_strain"]][0]
    write_tsv(os.path.join(a.out, "ASSEMBLY_KEYS.tsv"),
              [dict(strain=e["strain"], role=ROLE[e["source"]], genus=e["genus"], assembly_key=keys[e["strain"]][0],
                    rule=keys[e["strain"]][1], in_denominators="yes" if e["strain"] in known and e["strain"] not in excluded else "no")
               for e in entries], ["strain", "role", "genus", "assembly_key", "rule", "in_denominators"])
    write_tsv(os.path.join(a.out, "TARGET_REGIONS.tsv"), rows, TARGET_COLS)
    write_tsv(os.path.join(a.out, "TOP5_PUBLIC_REFERENCE.tsv"), [r for r in rows if r["role"] == "reference"][:5], TARGET_COLS)
    write_tsv(os.path.join(a.out, "TOP5_REFERENCE.tsv"), [r for r in rows if r["role"] in ("reference", "SID")][:5], TARGET_COLS)
    write_tsv(os.path.join(a.out, "TOP3_AS.tsv"), [r for r in rows if r["role"] == "AS"][:3], TARGET_COLS)
    write_tsv(os.path.join(a.out, "RARITY_BY_GENUS.tsv"), rarity_table(rows, n, nc, qgenus, totals, keys, a.count_by), RARITY_COLS)
    write_tsv(os.path.join(a.out, "QUERY_GENES.tsv"),
              [dict(query_id=r["id"], locus_tag=r["locus_tag"], length_aa=len(seqs[r["id"]]), gene_kind=r["subtype"],
                    core_gene="yes" if r["id"] in core else "no") for r in query],
              ["query_id", "locus_tag", "length_aa", "gene_kind", "core_gene"])
    node = query[0]["record_id"]
    with open(os.path.join(a.out, "LOCUS.txt"), "w") as fh:
        fh.write(f"{a.query_strain} / {node} / {a.query_region} / {a.alias}\tproducts: {query[0]['region_product']}\t"
                 f"genus: {qgenus}\tgenes: {n}\tcore genes: {nc}\n")
    os.remove(qfa); os.rmdir(work)
    receipt = dict(tool="locus_rarity_by_genus", version=__version__, utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   kit={"REGION_CDS.faa": sha256(faa), "REGION_CDS_META.tsv": sha256(mtsv)},
                   genome_table=(dict(path=a.genome_table, sha256=sha256(a.genome_table)) if a.genome_table else None),
                   denominators=denom, count_by=a.count_by,
                   counted=dict(entries=sum(len(v) for g in totals.values() for v in g.values()),
                                assemblies=len({(role, keys[s][0]) for g in totals.values() for role, v in g.items() for s in v})),
                   diamond=version, query=dict(strain=a.query_strain, region=a.query_region, alias=a.alias,
                   genus=qgenus, genes=n, core_genes=nc), excluded=sorted(excluded),
                   rule=dict(min_identity=a.min_identity, min_query_cover=a.min_query_cover, evalue=1e-5, mode="--more-sensitive",
                             core_gene_kinds=list(CORE_KINDS), MIBiG="left out of targets"),
                   target_regions=len(rows))
    with open(os.path.join(a.out, "RECEIPT.json"), "w") as fh:
        json.dump(receipt, fh, indent=1)
    return receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kit", required=True); ap.add_argument("--query-strain", required=True)
    ap.add_argument("--query-region", required=True); ap.add_argument("--alias", default="")
    ap.add_argument("--exclude", action="append", default=[]); ap.add_argument("--genome-table")
    ap.add_argument("--out", required=True); ap.add_argument("--diamond"); ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--min-identity", type=float, default=50.0); ap.add_argument("--min-query-cover", type=float, default=70.0)
    ap.add_argument("--count-by", choices=BASES, default="assembly",
                    help="what the main count columns count (default assembly); both are always reported")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        r = run(a)
    except Refusal as exc:
        _LOG.error("REFUSED: %s", exc)
        return 2
    _LOG.info("%s / %s: genes %d, core %d, target regions %d -> %s", r["query"]["strain"], r["query"]["region"],
              r["query"]["genes"], r["query"]["core_genes"], r["target_regions"], a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

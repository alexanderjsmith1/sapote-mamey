#!/usr/bin/env python3
"""tools/family_rarity_by_window.py -- how many genomes of a family carry each antiSMASH region's core genes together in one window?

WHY THIS EXISTS
    The M5's thesis scans of 20-21 Oct 2026 (family rarity for 37 AS strains, against a Streptomycetaceae protein database and
    an other-families protein database) answered "how many genomes of the strain's family hold this region's core genes side
    by side?" with workspace scripts (fixed paths). This tool carries that method into the bundle, with the per-region pass
    lists and the by-assembly counting that the later recount needed (tools/locus_rarity_by_genus.py v1.1.0 rule).

INPUT
    --antismash-zip ZIP  the query strain's antiSMASH result zip (region GenBank files *.regionNNN.gbk with CDS translations
                         and gene_kind). --strain S names the strain in the identity line.
    --proteomes P        whole-proteome protein FASTA (or its DIAMOND .dmnd) of the target genomes; headers
                         ACC|contig|start|end|strand (one genome = one ACC).
    --genome-table TSV   one row per target genome: genome_acc, genus, family, and optionally assembly_accession and total_bp
                         (assembly keys as in locus_rarity_by_genus.py). Its rows are the denominators.
    --query-family F     the family whose genomes give the headline counts (e.g. Nocardiaceae). Whole-table counts are
                         always reported beside it.
    --identity-table TSV optional: contig, region (regionNNN), identity (the full four-part BGC identity). Without it the identity is
                         strain / contig / regionNNN / IDENTITY_HOLD.
    --count-by B         assembly (default) or entry, for the main count columns; both are always reported.
    --region-index N     optional: one region only (0-based, in sorted region-file order).

METHOD (the M5 family-rarity rule)
    Query: the J1 core genes of each region (gene_kind biosynthetic or biosynthetic-additional). DIAMOND blastp --more-sensitive
    --evalue 1e-5 --id 50 --query-cover 70 --max-target-seqs 0; thresholds applied again here; hits streamed, not stored.
    Window: hits on one contig with gaps <= --gap (20 kb) between consecutive hits; a genome's count is the most distinct core
    genes in any one window. Cross-break / scattered: a genome reaching 30 % of the core anywhere but not in one window.
    Per region: genomes with >= 50 % and >= 30 % of the core in one window and scattered at 30 %, in the query family and in the
    whole table; best genome. family-rare = <= 2 family genomes at >= 30 % in one window, for regions with >= 3 core genes.

OUTPUT (--out DIR, must not exist)
    FAMILY_RARITY.tsv (one row per region), PASS_GENOMES.tsv.gz (every genome reaching >= 30 % of a region's core in one window
    or anywhere: the list a later recount needs), ASSEMBLY_KEYS.tsv, RECEIPT.json (input sha256, DIAMOND version, rule, counts).

Homology only: genes found together are not the same cluster or the same product.
Refusals (exit 2): an input missing, no region file in the zip, a genome table row without genome_acc/genus/family,
DIAMOND missing (never replaced), --out existing.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from locus_rarity_by_genus import BASES, assembly_keys, read_tsv, sha256, write_tsv  # noqa: E402  (one assembly rule)

_LOG = logging.getLogger("family_rarity_by_window")   # operator messages go through logging (repo_health print_calls)

__version__ = "1.0.0"
CORE_KINDS = ("biosynthetic", "biosynthetic-additional")
REGION_RE = re.compile(r"\.region(\d+)\.gbk$")
CDS_RE = re.compile(r"\n {5}CDS {13}.*?(?=\n {5}\S|\nORIGIN)", re.S)


class Refusal(Exception):
    pass


def qualifier(key, text):
    return re.findall(rf'/{key}="([^"]*)"', text, re.S)


def read_regions(zip_path, only=None):
    """Sorted region files of an antiSMASH zip -> [dict(contig, region, products, contig_edge, genes, core=[(locus_tag, aa)])]."""
    with zipfile.ZipFile(zip_path) as z:
        names = sorted(n for n in z.namelist() if REGION_RE.search(os.path.basename(n)) and "__MACOSX" not in n
                       and not os.path.basename(n).startswith("._"))
        if not names:
            raise Refusal(f"no *.regionNNN.gbk file in {zip_path}")
        out = []
        for i, n in enumerate(names):
            if only is not None and i != only:
                continue
            t = z.read(n).decode(errors="ignore"); b = os.path.basename(n); m = REGION_RE.search(b)
            head = re.search(r"\n {5}region {10}.*?(?=\n {5}\S)", t, re.S)
            head = head.group(0) if head else ""
            genes = [((qualifier("locus_tag", c.group(0)) or ["?"])[0], re.sub(r"\s", "", (qualifier("translation", c.group(0)) or [""])[0]),
                      (qualifier("gene_kind", c.group(0)) or [""])[0]) for c in CDS_RE.finditer(t)]
            out.append(dict(index=i, contig=b[:m.start()], region=f"region{int(m.group(1)):03d}", products="+".join(qualifier("product", head)),
                            contig_edge=(qualifier("contig_edge", head) or [""])[0], genes=len(genes),
                            core=[(lt, aa) for lt, aa, k in genes if k in CORE_KINDS and aa]))
    return out


def best_window(hits, gap):
    """hits: [(contig, start, end, gene)] -> (n distinct genes, contig) of the best one-contig window."""
    by = defaultdict(list); best = (0, "")
    for c, s, e, g in hits:
        by[c].append((s, e, g))
    for c, lst in by.items():
        lst.sort(); cur, end = [], None
        for s, e, g in lst + [(None, None, None)]:
            if s is not None and (end is None or s - end <= gap):
                cur.append(g); end = max(end or 0, e); continue
            if len(set(cur)) > best[0]:
                best = (len(set(cur)), c)
            if s is not None:
                cur, end = [g], e
    return best


def run(a):
    for p in (a.antismash_zip, a.proteomes, a.genome_table) + ((a.identity_table,) if a.identity_table else ()):
        if not os.path.isfile(p):
            raise Refusal(f"input missing: {p}")
    if os.path.exists(a.out):
        raise Refusal(f"--out exists: {a.out}")
    dmd = a.diamond or shutil.which("diamond")
    if not dmd or not os.path.isfile(dmd):
        raise Refusal("DIAMOND not found (--diamond or PATH); it is never replaced")
    gt = read_tsv(a.genome_table)
    for r in gt:
        if not (r.get("genome_acc") and r.get("genus") and r.get("family")):
            raise Refusal(f"genome table row lacks genome_acc / genus / family: {r}")
    fam = {r["genome_acc"]: r["family"] for r in gt}; gen = {r["genome_acc"]: r["genus"] for r in gt}
    keys = assembly_keys([dict(strain=r["genome_acc"], genus=r["genus"], assembly_accession=r.get("assembly_accession", ""),
                               total_bp=r.get("total_bp", "")) for r in gt])
    ident = {}
    if a.identity_table:
        ident = {(r["contig"], r["region"]): r["identity"] for r in read_tsv(a.identity_table)}
    regions = read_regions(a.antismash_zip, a.region_index)
    os.makedirs(a.out)
    work = tempfile.mkdtemp(prefix="family-rarity-", dir=a.out); qf = os.path.join(work, "query.faa")
    with open(qf, "w") as fh:
        for ri, r in enumerate(regions):
            fh.writelines(f">r{ri}_g{gi}\n{aa}\n" for gi, (_, aa) in enumerate(r["core"]))
    cmd = [dmd, "blastp", "-q", qf, "-d", a.proteomes, "--more-sensitive", "--evalue", "1e-5", "--id", str(a.min_identity),
           "--query-cover", str(a.min_query_cover), "--max-target-seqs", "0", "--threads", str(a.threads), "--quiet",
           "--outfmt", "6", "qseqid", "sseqid", "pident", "qcovhsp"]
    hits = defaultdict(lambda: defaultdict(list)); unknown = set()
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as p:
        for line in p.stdout:
            q, s, pid, qc = line.rstrip("\n").split("\t")
            if float(pid) < a.min_identity or float(qc) < a.min_query_cover:
                continue
            acc, contig, st, en = s.split("|")[:4]
            if acc not in fam:
                unknown.add(acc); continue
            ri, gi = q[1:].split("_g"); hits[int(ri)][acc].append((contig, int(st), int(en), int(gi)))
        err = p.stderr.read()
    if p.returncode != 0:
        raise Refusal(f"DIAMOND failed (rc {p.returncode}): {err.strip()[:300]}")
    version = subprocess.run([dmd, "version"], capture_output=True, text=True).stdout.strip()
    os.remove(qf); os.rmdir(work)
    in_fam = {acc for acc, f in fam.items() if f == a.query_family}
    unit = lambda accs, basis: len({keys[x][0] for x in accs}) if basis == "assembly" else len(set(accs))
    rows, passed = [], []
    for ri, r in enumerate(regions):
        nc = len(r["core"]); w30, w50, any30, best = [], [], [], None
        for acc, hl in hits[ri].items():
            n, contig = best_window(hl, a.gap); anywhere = len({h[3] for h in hl})
            if n >= 0.3 * nc or anywhere >= 0.3 * nc:
                passed.append(dict(identity=None, genome_acc=acc, assembly_key=keys[acc][0], genus=gen[acc], family=fam[acc],
                                   core_genes_J1=nc, core_in_one_window=n, core_anywhere=anywhere, window_contig=contig))
            if n >= 0.3 * nc: w30.append(acc)
            if n >= 0.5 * nc: w50.append(acc)
            if anywhere >= 0.3 * nc and n < 0.3 * nc: any30.append(acc)
            if best is None or (n, anywhere, acc) > best[:3]: best = (n, anywhere, acc, contig)
        identity = ident.get((r["contig"], r["region"]), f"{a.strain} / {r['contig']} / {r['region']} / IDENTITY_HOLD")
        for pr in passed:
            if pr["identity"] is None: pr["identity"] = identity
        row = dict(identity=identity, products=r["products"], contig_edge=r["contig_edge"], genes=r["genes"], core_genes_J1=nc,
                   query_family=a.query_family, count_basis=a.count_by)
        for basis in BASES:
            sfx = f"_by_{basis}"
            vals = dict(family_genomes=unit(in_fam, basis), family_ge50pct_core_one_window=unit([x for x in w50 if x in in_fam], basis),
                        family_ge30pct_core_one_window=unit([x for x in w30 if x in in_fam], basis),
                        family_scattered_ge30pct_core_not_one_window=unit([x for x in any30 if x in in_fam and x not in w30], basis),
                        table_genomes=unit(fam, basis), table_ge50pct_core_one_window=unit(w50, basis),
                        table_ge30pct_core_one_window=unit(w30, basis))
            for k, v in vals.items():
                row[k + sfx] = v
                if basis == a.count_by: row[k] = v
        main30 = row["family_ge30pct_core_one_window"]
        row.update(family_rare=("yes" if main30 <= 2 else "no") if nc >= 3 else "n/a (fewer than 3 core genes)",
                   best_genome=best[2] if best else "", best_genome_assembly=keys[best[2]][0] if best else "",
                   best_genome_genus=gen[best[2]] if best else "", best_genome_family=fam[best[2]] if best else "",
                   best_core_in_one_window=best[0] if best else 0, best_window_contig=best[3] if best else "")
        rows.append(row)
    lead = ["identity", "products", "contig_edge", "genes", "core_genes_J1", "query_family", "count_basis", "family_genomes",
            "family_ge50pct_core_one_window", "family_ge30pct_core_one_window", "family_scattered_ge30pct_core_not_one_window",
            "family_rare", "table_genomes", "table_ge50pct_core_one_window", "table_ge30pct_core_one_window", "best_genome",
            "best_genome_assembly", "best_genome_genus", "best_genome_family", "best_core_in_one_window", "best_window_contig"]
    cols = lead + [c for c in rows[0] if c not in lead] if rows else lead
    write_tsv(os.path.join(a.out, "FAMILY_RARITY.tsv"), rows, cols)
    pcols = ["identity", "genome_acc", "assembly_key", "genus", "family", "core_genes_J1", "core_in_one_window", "core_anywhere", "window_contig"]
    with gzip.open(os.path.join(a.out, "PASS_GENOMES.tsv.gz"), "wt", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=pcols, delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(passed)
    write_tsv(os.path.join(a.out, "ASSEMBLY_KEYS.tsv"),
              [dict(genome_acc=r["genome_acc"], genus=r["genus"], family=r["family"], assembly_key=keys[r["genome_acc"]][0],
                    rule=keys[r["genome_acc"]][1]) for r in gt], ["genome_acc", "genus", "family", "assembly_key", "rule"])
    receipt = dict(tool="family_rarity_by_window", version=__version__, utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   inputs={k: dict(path=v, sha256=sha256(v)) for k, v in (("antismash_zip", a.antismash_zip), ("genome_table", a.genome_table),
                                                                          ("proteomes", a.proteomes)) + ((("identity_table", a.identity_table),) if a.identity_table else ())},
                   diamond=version, strain=a.strain, query_family=a.query_family, count_by=a.count_by,
                   counted=dict(table_entries=len(fam), table_assemblies=len({k for k, _ in keys.values()}),
                                family_entries=len(in_fam), family_assemblies=len({keys[x][0] for x in in_fam})),
                   rule=dict(min_identity=a.min_identity, min_query_cover=a.min_query_cover, evalue=1e-5, mode="--more-sensitive", gap_bp=a.gap,
                             core_gene_kinds=list(CORE_KINDS), family_rare="<= 2 family genomes at >= 30 % core in one window; >= 3 core genes"),
                   regions=len(rows), family_rare=sum(1 for r in rows if r["family_rare"] == "yes"),
                   hits_to_genomes_not_in_table=len(unknown))
    with open(os.path.join(a.out, "RECEIPT.json"), "w") as fh:
        json.dump(receipt, fh, indent=1)
    return receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--antismash-zip", required=True); ap.add_argument("--strain", required=True)
    ap.add_argument("--proteomes", required=True); ap.add_argument("--genome-table", required=True)
    ap.add_argument("--query-family", required=True); ap.add_argument("--identity-table")
    ap.add_argument("--out", required=True); ap.add_argument("--diamond"); ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--region-index", type=int); ap.add_argument("--gap", type=int, default=20000)
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
    _LOG.info("%s: %d regions, %d family-rare (%s, by %s) -> %s", r["strain"], r["regions"], r["family_rare"], r["query_family"],
              r["count_by"], a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

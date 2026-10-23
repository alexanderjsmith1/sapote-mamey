#!/usr/bin/env python3
"""tools/region_presence_survey.py -- is one antiSMASH region present in each of a set of genomes, and at what identity?

WHY THIS EXISTS
    The M5's J6 / J6B / J6C job of 21 Oct 2026 asked it for a phosphonate region of one isolate across 208 Actinomadura genomes. Two
    rules gave different answers, and both were needed: a protein search under the J1 rule (>= 50 % identity, >= 70 % cover)
    found 13 of 16 genes in A. harenae, a tblastn search of the genome sequence with no identity floor found all 15 island genes
    (one gene below 50 % identity, one short gene at the cover floor, one ORF the gene caller did not annotate). This tool
    runs both rules in one place and reports them side by side, so a reader sees which rule a number comes from.

INPUT
    Query (one of):
      --query-faa F           the query proteins, in gene order;
      --antismash-zip Z --contig C --region N [--flank K]
                              cut from the strain's antiSMASH zip: the CDS of contig C's regionNNN (from the region file) plus K
                              genes each side (from the whole-genome GenBank in the zip; default 0).
    --genomes TSV             one row per target genome: genome_acc, genus, nucleotide (genome FASTA, .gz allowed; relative paths
                              from the table's folder), and optionally assembly_accession, total_bp (assembly keys as in
                              locus_rarity_by_genus.py).
    --proteomes P             optional: protein FASTA or DIAMOND .dmnd of the same genomes, headers ACC|contig|start|end|strand.
                              Without it the protein rule is skipped and reported as not run.

METHOD
    Protein rule (J1): DIAMOND blastp --more-sensitive --evalue 1e-5 --id 50 --query-cover 70 --max-target-seqs 0; best hit per gene.
    Nucleotide rule: tblastn -evalue 1e-5 -seg no on each genome sequence; best HSP per gene (bit score), kept if it covers
    >= --tblastn-min-cover (50) % of the protein; no identity floor.
    Under each rule: genes found, identity range, and the largest window (distinct genes on one contig with gaps <= --gap, 20 kb),
    with its contig, coordinates and genes. Genomes are also counted by assembly key (ASSEMBLY_KEYS.tsv).

OUTPUT (--out DIR, must not exist)
    QUERY.faa and QUERY_GENES.tsv, SURVEY_PER_GENOME.tsv, SURVEY_PER_GENE.tsv, tblastn/<genome_acc>.tsv (raw HSPs),
    ASSEMBLY_KEYS.tsv, RECEIPT.json (input sha256, tool versions, rules, counts by entry and by assembly).

Homology only: genes found together are not the same cluster or the same product. A gene below a rule's floor is not shown absent.
Refusals (exit 2): an input missing, no query, the region or contig not in the zip, tblastn missing, DIAMOND missing when
--proteomes is given (neither is ever replaced), --out existing.
"""
from __future__ import annotations

import argparse
import gzip
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from locus_rarity_by_genus import assembly_keys, read_fasta, read_tsv, sha256, write_tsv  # noqa: E402  (one assembly rule)

_LOG = logging.getLogger("region_presence_survey")   # operator messages go through logging (repo_health print_calls)

__version__ = "1.0.0"
CDS_RE = re.compile(r"\n {5}CDS {13}(.*?)(?=\n {5}\S|\nORIGIN)", re.S)


class Refusal(Exception):
    pass


def _q(key, text):
    return re.findall(rf'/{key}="([^"]*)"', text, re.S)


def query_from_zip(zp, contig, region, flank):
    """[(query_id, locus_tag, location, in_region, aa)] for contig's regionNNN plus `flank` genes each side."""
    with zipfile.ZipFile(zp) as z:
        names = [n for n in z.namelist() if "__MACOSX" not in n]
        rname = [n for n in names if os.path.basename(n) == f"{contig}.region{region:03d}.gbk"]
        if not rname:
            raise Refusal(f"{contig}.region{region:03d}.gbk not in {zp}")
        rtags = [(_q("locus_tag", m.group(0)) or ["?"])[0] for m in CDS_RE.finditer(z.read(rname[0]).decode(errors="ignore"))]
        whole = [n for n in names if n.endswith(".gbk") and ".region" not in os.path.basename(n)]
        rec = None
        for n in whole:
            for r in z.read(n).decode(errors="ignore").split("\n//"):
                if re.search(rf"^LOCUS\s+{re.escape(contig[:16])}", r, re.M) or f"\nDEFINITION  {contig}" in r or f"\nACCESSION   {contig}" in r:
                    rec = r; break
            if rec: break
    if rec is None:
        raise Refusal(f"contig {contig} not found in a whole-genome GenBank of {zp}")
    cds = [(m.group(1).split("\n")[0].strip(), (_q("locus_tag", m.group(0)) or ["?"])[0], re.sub(r"\s", "", (_q("translation", m.group(0)) or [""])[0]))
           for m in CDS_RE.finditer(rec)]
    idx = [i for i, c in enumerate(cds) if c[1] in rtags]
    if len(idx) != len(rtags) or not idx:
        raise Refusal(f"region CDS ({len(rtags)}) not all found on contig {contig} ({len(idx)} matched)")
    sel = range(max(0, idx[0] - flank), min(len(cds), idx[-1] + flank + 1))
    return [(f"q{i + 1:03d}|{cds[i][1]}", cds[i][1], cds[i][0], "yes" if i in idx else "flank", cds[i][2]) for i in sel if cds[i][2]]


def windows(hl, gap):
    """hl: {gene: (contig, start, end, identity)} -> (n, contig, start, end, genes, identities) of the largest one-contig window."""
    by = defaultdict(list); best = (0, "", "", "", [], [])
    for g, (c, s, e, pid) in hl.items():
        by[c].append((min(s, e), max(s, e), g, pid))
    for c, lst in by.items():
        lst.sort(); cur, end = [], None
        for x in lst + [None]:
            if x is not None and (end is None or x[0] - end <= gap):
                cur.append(x); end = max(end or 0, x[1]); continue
            if len(cur) > best[0]:
                best = (len(cur), c, min(y[0] for y in cur), max(y[1] for y in cur), [y[2] for y in cur], [y[3] for y in cur])
            if x is not None:
                cur, end = [x], x[1]
    return best


def summarise(hl, gap, order):
    n, c, s, e, genes, ids = windows(hl, gap); allid = [v[3] for v in hl.values()]
    f = lambda v: f"{v:.1f}"
    return dict(genes_found=len(hl), identity_min=f(min(allid)) if allid else "", identity_mean=f(statistics.mean(allid)) if allid else "",
                identity_max=f(max(allid)) if allid else "", window_genes=n, window_contig=c, window_start=s, window_end=e,
                window_identity_min=f(min(ids)) if ids else "", window_identity_max=f(max(ids)) if ids else "",
                window_gene_list=",".join(sorted(genes, key=order.index)))


def run(a):
    if os.path.exists(a.out):
        raise Refusal(f"--out exists: {a.out}")
    for p in (a.genomes,) + tuple(x for x in (a.query_faa, a.antismash_zip, a.proteomes) if x):
        if not os.path.isfile(p):
            raise Refusal(f"input missing: {p}")
    tbn = a.tblastn or shutil.which("tblastn")
    if not tbn or not os.path.isfile(tbn):
        raise Refusal("tblastn not found (--tblastn or PATH); it is never replaced")
    dmd = None
    if a.proteomes:
        dmd = a.diamond or shutil.which("diamond")
        if not dmd or not os.path.isfile(dmd):
            raise Refusal("DIAMOND not found (--diamond or PATH) while --proteomes is given; it is never replaced")
    if a.query_faa:
        seqs = read_fasta(a.query_faa); query = [(k, k, "", "", v) for k, v in seqs.items()]
    elif a.antismash_zip and a.contig and a.region:
        query = query_from_zip(a.antismash_zip, a.contig, a.region, a.flank)
    else:
        raise Refusal("give --query-faa, or --antismash-zip with --contig and --region")
    if not query:
        raise Refusal("the query has no protein")
    order = [q[0] for q in query]
    gt = read_tsv(a.genomes); base = os.path.dirname(os.path.abspath(a.genomes))
    for r in gt:
        r["nucleotide"] = r["nucleotide"] if os.path.isabs(r["nucleotide"]) else os.path.join(base, r["nucleotide"])
        if not os.path.isfile(r["nucleotide"]):
            raise Refusal(f"genome sequence missing: {r['nucleotide']}")
    keys = assembly_keys([dict(strain=r["genome_acc"], genus=r["genus"], assembly_accession=r.get("assembly_accession", ""),
                               total_bp=r.get("total_bp", "")) for r in gt])
    os.makedirs(os.path.join(a.out, "tblastn")); work = tempfile.mkdtemp(prefix="presence-", dir=a.out)
    qf = os.path.join(a.out, "QUERY.faa")
    with open(qf, "w") as fh:
        fh.writelines(f">{q[0]}\n{q[4]}\n" for q in query)
    write_tsv(os.path.join(a.out, "QUERY_GENES.tsv"), [dict(query_id=q[0], locus_tag=q[1], location=q[2], in_region=q[3], aa_length=len(q[4])) for q in query],
              ["query_id", "locus_tag", "location", "in_region", "aa_length"])
    prot = defaultdict(dict)                                   # genome -> gene -> (contig, s, e, pid, bitscore)
    if dmd:
        cmd = [dmd, "blastp", "-q", qf, "-d", a.proteomes, "--more-sensitive", "--evalue", "1e-5", "--id", "50", "--query-cover", "70",
               "--max-target-seqs", "0", "--threads", str(a.threads), "--quiet", "--outfmt", "6", "qseqid", "sseqid", "pident", "qcovhsp", "bitscore"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise Refusal(f"DIAMOND failed (rc {p.returncode}): {p.stderr.strip()[:300]}")
        for line in p.stdout.splitlines():
            q, s, pid, qc, bs = line.split("\t")
            if float(pid) < 50 or float(qc) < 70:
                continue
            acc, c, st, en = s.split("|")[:4]
            if q not in prot[acc] or float(bs) > prot[acc][q][4]:
                prot[acc][q] = (c, int(st), int(en), float(pid), float(bs))
    nuc = defaultdict(dict)
    for r in gt:
        subj = r["nucleotide"]
        if subj.endswith(".gz"):
            subj = os.path.join(work, "genome.fna")
            with gzip.open(r["nucleotide"], "rb") as src, open(subj, "wb") as dst:
                shutil.copyfileobj(src, dst)
        cmd = [tbn, "-query", qf, "-subject", subj, "-evalue", "1e-5", "-seg", "no",
               "-outfmt", "6 qseqid sseqid pident length qlen qstart qend sstart send evalue bitscore qcovhsp"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise Refusal(f"tblastn failed on {r['genome_acc']} (rc {p.returncode}): {p.stderr.strip()[:300]}")
        with open(os.path.join(a.out, "tblastn", f"{r['genome_acc']}.tsv"), "w") as fh:
            fh.write(p.stdout)
        if subj != r["nucleotide"]:
            os.remove(subj)
        for line in p.stdout.splitlines():
            q, s, pid, ln, ql, qs, qe, ss, se, ev, bs, qc = line.split("\t")
            cur = nuc[r["genome_acc"]].get(q)
            if cur is None or float(bs) > cur[5]:
                nuc[r["genome_acc"]][q] = (s, int(ss), int(se), float(pid), float(qc), float(bs))
    os.rmdir(work)
    per = []
    for r in gt:
        acc = r["genome_acc"]
        pk = {g: v[:4] for g, v in prot.get(acc, {}).items()}
        nk = {g: v[:4] for g, v in nuc.get(acc, {}).items() if v[4] >= a.tblastn_min_cover}
        row = dict(genome_acc=acc, assembly_key=keys[acc][0], genus=r["genus"])
        for tag, d in (("protein_J1", pk), ("tblastn", nk)):
            if tag == "protein_J1" and not dmd:
                row.update({f"{tag}_{k}": "not run" for k in ("genes_found", "identity_min", "identity_mean", "identity_max", "window_genes",
                                                              "window_contig", "window_start", "window_end", "window_identity_min",
                                                              "window_identity_max", "window_gene_list")})
                continue
            row.update({f"{tag}_{k}": v for k, v in summarise(d, a.gap, order).items()})
        per.append(row)
    per.sort(key=lambda x: (-int(x["tblastn_window_genes"]), -int(x["tblastn_genes_found"]), x["genome_acc"]))
    cols = list(per[0]) if per else ["genome_acc"]
    write_tsv(os.path.join(a.out, "SURVEY_PER_GENOME.tsv"), per, cols)
    genes = []
    for q in query:
        g = q[0]; pn = [(v[g][3], k) for k, v in prot.items() if g in v]; tn = [(v[g][3], k) for k, v in nuc.items() if g in v and v[g][4] >= a.tblastn_min_cover]
        genes.append(dict(query_id=g, in_region=q[3], aa_length=len(q[4]),
                          protein_J1_genomes=len(pn) if dmd else "not run", protein_J1_best_identity=f"{max(pn)[0]:.1f}" if pn else "",
                          protein_J1_best_genome=max(pn)[1] if pn else "",
                          tblastn_genomes=len(tn), tblastn_assemblies=len({keys[k][0] for _, k in tn}),
                          tblastn_best_identity=f"{max(tn)[0]:.1f}" if tn else "", tblastn_best_genome=max(tn)[1] if tn else ""))
    write_tsv(os.path.join(a.out, "SURVEY_PER_GENE.tsv"), genes, list(genes[0]))
    write_tsv(os.path.join(a.out, "ASSEMBLY_KEYS.tsv"), [dict(genome_acc=r["genome_acc"], genus=r["genus"], assembly_key=keys[r["genome_acc"]][0],
                                                              rule=keys[r["genome_acc"]][1]) for r in gt], ["genome_acc", "genus", "assembly_key", "rule"])
    version = lambda exe, arg: subprocess.run([exe, arg], capture_output=True, text=True).stdout.strip().splitlines()[0] if exe else None
    ge = lambda k, tag: [x for x in per if str(x[f"{tag}_window_genes"]).isdigit() and int(x[f"{tag}_window_genes"]) >= k]
    receipt = dict(tool="region_presence_survey", version=__version__, utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   inputs={k: dict(path=v, sha256=sha256(v)) for k, v in (("genomes", a.genomes), ("query_faa", a.query_faa),
                                                                          ("antismash_zip", a.antismash_zip), ("proteomes", a.proteomes)) if v},
                   query=dict(proteins=len(query), contig=a.contig, region=a.region, flank=a.flank if a.antismash_zip else None),
                   tblastn=version(tbn, "-version"), diamond=version(dmd, "version"),
                   rules=dict(protein_J1="DIAMOND blastp --more-sensitive --evalue 1e-5 --id 50 --query-cover 70" if dmd else "not run",
                              tblastn=f"-evalue 1e-5 -seg no; best HSP per gene; query cover >= {a.tblastn_min_cover} %; no identity floor",
                              window_gap_bp=a.gap),
                   genomes=dict(entries=len(gt), assemblies=len({k for k, _ in keys.values()})),
                   tblastn_window_ge5=dict(entries=len(ge(5, "tblastn")), assemblies=len({x["assembly_key"] for x in ge(5, "tblastn")})))
    with open(os.path.join(a.out, "RECEIPT.json"), "w") as fh:
        json.dump(receipt, fh, indent=1)
    return receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--query-faa"); ap.add_argument("--antismash-zip"); ap.add_argument("--contig"); ap.add_argument("--region", type=int)
    ap.add_argument("--flank", type=int, default=0); ap.add_argument("--genomes", required=True); ap.add_argument("--proteomes")
    ap.add_argument("--out", required=True); ap.add_argument("--tblastn"); ap.add_argument("--diamond"); ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--gap", type=int, default=20000); ap.add_argument("--tblastn-min-cover", type=float, default=50.0)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        r = run(a)
    except Refusal as exc:
        _LOG.error("REFUSED: %s", exc)
        return 2
    _LOG.info("%d query proteins, %d genomes (%d assemblies); tblastn window >= 5 genes: %d genomes -> %s", r["query"]["proteins"],
              r["genomes"]["entries"], r["genomes"]["assemblies"], r["tblastn_window_ge5"]["entries"], a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

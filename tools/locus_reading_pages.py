#!/usr/bin/env python3
"""locus_reading_pages.py: one locus-reading page per antiSMASH region, every gene with every evidence layer.

Reads only. Writes Markdown into a new output folder: one page per BGC, one combined file per strain and a build log.
Render a page or a combined file with Tools/render_md_pdf.sh (pandoc to HTML, then headless Chrome).

  python3 tools/locus_reading_pages.py --out <new folder> --package <STRAIN>=<package dir> [--package ...]
      (--ledger <ledger.tsv[.gz]> | --ledger-dir <dir of <strain>.tsv>)
      [--gene-table-inventory <INVENTORY.tsv> --gene-table-root <dir>] [--gecco <clusters.tsv>]
      [--mibig-json <dir of <BGC>.json>] [--mibig-proteins <dir with mibig_proteins.dmnd and .tsv>]
      [--proteomes <dir of <strain>.faa> --pfam <Pfam-A.hmm> --hmmsearch <bin> --diamond <bin>]
      [--assessments <dir>] [--refs <dir>] [--strains A,B] [--bgc BGC007] [--skip STRAIN=REASON] [--threads 4]

Inputs, one source each:
  regions and identity      the strain's Mamey package *_2_inventory.csv (BGC_ID, Contig, Region, Products, Boundary,
                            Length_kb, KCB_top, KCB_proteins)
  known-cluster convergence the package's *_3_mibig_convergence.csv
  every gene's layers       a gene annotation ledger: one row per CDS with the columns in LEDGER_COLUMNS
  gene tables and maps      a gene-table inventory (one row per pair; its png column is resolved against
                            --gene-table-root) and, beside each pair's map, gap_rescue.tsv and gap_rescue_split_genes.tsv
  GECCO clusters            a table with strain, contig_full, type, start, end, average_p, relation
  MIBiG entries             MIBiG JSON records, one per BGC, for compound names, producer and recorded bioactivity
  hand assessments          <assessments>/<stem>.md, used in place of the automatic summary when present
  checked literature        <refs>/<stem>.tsv (pmid, citation, doi, reports), used when present
where <stem> is <strain>_<NODEn>_r<###>_<BGC>.

Rows shown per BGC: every CDS of the region, 3 flanking CDS on each side, and every CDS on any contig the gene table or
the split check points to (the whole contig up to 20 kb; otherwise the matched CDS and 2 on each side). Those contigs are
matched to the ledger's names on NODE_n_length_L, because some tables rewrite the coverage part of SPAdes names.
A protein the ledger never searched (L2b_bind NOT_SEARCHED, or mibig_queried "no ...") is searched for the pages, once per
strain: Pfam-A with hmmsearch --cut_ga, and MIBiG proteins with DIAMOND blastp --more-sensitive -k 25 -e 1e-5 (best bit
score). Results are cached in <out>/_page_searches/<strain>/ and marked † on the page; a cache made for a different
protein set is discarded and searched again, so a new folder may be pre-seeded with a cache. Without a proteome, Pfam file,
hmmsearch or DIAMOND, those cells read "not searched †" and the footnote says why.
Each gene-table bullet has a gene-kind line: the reference genes present in the core by MIBiG gene kind (gap_rescue.tsv
reference_gene_kind), and the biosynthetic count (core and additional), flagged when a STRONG table has fewer than half of
those in the core. A second known-cluster table counts the region's genes by the MIBiG cluster of each gene's best MIBiG
protein (ledger mibig_best_hit), because the KnownClusterBlast-based convergence table can miss clusters its database lacks.
Without a hand assessment, a page carries an automatic evidence summary: counts and calls only, no interpretation.

Rules: an output folder that already holds a build (BUILD_LOG.tsv) is refused, and so is an existing page (versions are
never overwritten); nothing is invented (a blank layer is marked ‡ or "no hit under the filters", never "none"); wording
stays at class level. A MIBiG or KnownClusterBlast match is similarity, not compound identity; a detected cluster is
capacity, not production.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
from mamey.path_safety import assert_output_outside_bundle  # noqa: E402

from mamey.logging_setup import get_logger as _get_logger

_OUT = _get_logger(__name__)

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
LEDGER_COLUMNS = ["strain", "locus_tag", "contig", "start", "end", "strand", "region", "bgc", "aa", "as_gene_function",
                  "L2b_bind", "L2b_pfam_domains", "mibig_best_hit", "mibig_gene", "mibig_identity", "mibig_queried",
                  "gene_map_rows", "card_family", "LG_gene_avg_p", "L5_status", "L5_ref", "L5_ref_is_SID", "L5_product",
                  "L5_pident", "L5_region_call", "L5_ref_region"]
CAVEAT = ("Locus reading. Every number comes from the named file. A MIBiG or KnownClusterBlast match is similarity, not "
          "compound identity; a detected cluster is capacity, not production. Judgment deferred.\n")
AUTO_HEAD = ("*Automatic evidence summary: counts and calls only. No hand assessment has been written for this locus yet; "
             "judgment deferred.*\n")
DAGGER_SEARCHED = ("† Searched for this page (the gene lies outside any antiSMASH region): Pfam-A, hmmsearch --cut_ga; MIBiG "
                   "proteins, DIAMOND blastp --more-sensitive, E ≤ 1e-5, best bit score.\n")
DOUBLE_DAGGER = "‡ Not yet searched against the reference genomes.\n"

short = lambda c: re.sub(r"_length_(\d+)_cov_([\d.]+)", lambda m: f" ({int(m.group(1)):,} bp, {float(m.group(2)):.0f}×)", c)
node_tag = lambda c: (re.match(r"(NODE_\d+)", c).group(1).replace("_", "") if c.startswith("NODE_")
                      else re.sub(r"[^A-Za-z0-9]", "", c)[:20])
clen = lambda c: int(m.group(1)) if (m := re.search(r"_length_(\d+)_", c)) else 10 ** 9


class MibigIndex:
    """Compound names, producer and recorded bioactivity per MIBiG accession, read from its JSON record."""

    def __init__(self, folder):
        self.folder = Path(folder) if folder else None
        self._cache = {}

    def __call__(self, acc):
        if acc in self._cache:
            return self._cache[acc]
        out = {"names": "?", "acts": [], "taxon": ""}
        p = self.folder / f"{acc}.json" if self.folder else None
        if p and p.exists():
            d = json.load(open(p))
            acts = []
            for x in d.get("compounds", []):
                for b in x.get("bioactivities", []):
                    n = b.get("name")
                    n = n.get("activity") if isinstance(n, dict) else n
                    acts.append(str(n) + ("" if b.get("observed", True) else " (not observed)"))
            out = {"names": "; ".join(x.get("name", "") for x in d.get("compounds", [])), "acts": sorted(set(acts)),
                   "taxon": d.get("taxonomy", {}).get("name", "")}
        self._cache[acc] = out
        return out


def ledger_by_strain(ledger, ledger_dir, cache):
    """The folder of per-strain ledger TSVs: --ledger-dir as given, or --ledger split once into `cache`."""
    if ledger_dir:
        return Path(ledger_dir)
    cache.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if str(ledger).endswith(".gz") else open
    fhs = {}
    with opener(ledger, "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            s = r["strain"]
            if s not in fhs:
                fh = open(cache / f"{s}.tsv", "w", newline="")
                w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
                w.writerow(LEDGER_COLUMNS)
                fhs[s] = (fh, w)
            fhs[s][1].writerow([r.get(k, "") for k in LEDGER_COLUMNS])
    for fh, _ in fhs.values():
        fh.close()
    return cache


def select_rows(genes_by_contig, bgc, pairs, gr_by_pair, sp_by_pair):
    """-> (rows, contig order, extra contigs): the region's CDS with 3 flanking CDS on each side, then every contig the
    gene table or split check points to (whole contig up to 20 kb; else the matched CDS and 2 on each side)."""
    region = [g for gs in genes_by_contig.values() for g in gs if g["bgc"] == bgc]
    if not region:
        return [], [], {}
    core = region[0]["contig"]
    cg = genes_by_contig[core]
    idx = [i for i, g in enumerate(cg) if g["bgc"] == bgc]
    shown = {(core, i) for i in range(max(0, idx[0] - 3), min(len(cg), idx[-1] + 4))}
    extra = defaultdict(set)
    for p in pairs:
        for r in gr_by_pair.get(p["pair"], []):
            if r.get("best_contig") and r["status"] != "MISSING_NOT_FOUND" and r["best_contig"] != core:
                extra[r["best_contig"]].add(r.get("best_locus", ""))
        for r in sp_by_pair.get(p["pair"], []):
            for k, lk in (("piece1_region_identity", "piece1_locus"), ("piece2_region_identity", "piece2_locus")):
                m = re.search(r"/ (\S+)", r.get(k, ""))
                if m and m.group(1) != core:
                    extra[m.group(1)].add(r.get(lk, ""))
    # Some tables rewrite the coverage part of SPAdes names (cov_65.032271 -> cov_65.32271). Match on NODE_n_length_L,
    # which is unique within an assembly, and use the ledger's full name from here on.
    key = lambda c: m.group(1) if (m := re.match(r"(NODE_\d+_length_\d+)_", c)) else c
    byk = {key(c): c for c in genes_by_contig}
    merged = defaultdict(set)
    for c, v in extra.items():
        if byk.get(key(c), c) != core:
            merged[byk.get(key(c), c)] |= v
    extra = merged
    for c, loci in extra.items():
        gs = genes_by_contig.get(c, [])
        if clen(c) <= 20000:
            shown |= {(c, i) for i in range(len(gs))}
        else:
            for i, g in enumerate(gs):
                if g["locus_tag"] in loci:
                    shown |= {(c, j) for j in range(max(0, i - 2), min(len(gs), i + 3))}
    order = [core] + sorted(extra)
    rows = [genes_by_contig[c][i] for c in order for i in sorted(j for cc, j in shown if cc == c)]
    return rows, order, extra


def page_search(strain, need, out, opts):
    """Pfam and MIBiG for every shown protein the ledger never searched, once per strain.
    -> (pfam hits {locus: [(start, text)]}, MIBiG best hits {locus: row}, reason the search did not run or "")."""
    pf, mb = defaultdict(list), {}
    if not need:
        return pf, mb, ""
    proteome = Path(opts.proteomes) / f"{strain}.faa" if opts.proteomes else None
    missing = [n for n, v in (("proteome", proteome and proteome.exists()), ("Pfam file", opts.pfam),
                               ("hmmsearch", opts.hmmsearch and shutil.which(opts.hmmsearch)),
                               ("DIAMOND", opts.diamond and shutil.which(opts.diamond)),
                               ("MIBiG protein set", opts.mibig_proteins)) if not v]
    if missing:
        return pf, mb, "not run: no " + ", no ".join(missing) + " given"
    ps = out / "_page_searches" / strain
    ps.mkdir(parents=True, exist_ok=True)
    faa, dt, mt = ps / "proteins.faa", ps / "pfam.domtbl", ps / "mibig.tsv"
    if faa.exists() and {ln[1:].strip() for ln in open(faa) if ln.startswith(">")} != set(need):
        for f in (faa, dt, mt):   # the protein set changed: search again (cached results are for a different set)
            f.unlink(missing_ok=True)
    if not faa.exists():
        lines, keep = [], False
        for line in open(proteome):
            if line.startswith(">"):
                head = line[1:].strip()
                tag = head.split("|")[1] if "|" in head else head.split()[0]
                keep = tag in need
                if keep:
                    lines.append(f">{tag}\n")
            elif keep:
                lines.append(line)
        faa.write_text("".join(lines))
    if not dt.exists():
        subprocess.run([opts.hmmsearch, "--cut_ga", "--cpu", str(opts.threads), "--noali", "-o", os.devnull,
                        "--domtblout", str(dt), str(opts.pfam), str(faa)], check=True)
    if not mt.exists():
        subprocess.run([opts.diamond, "blastp", "--more-sensitive", "-k", "25", "-e", "1e-5", "--threads",
                        str(opts.threads), "-q", str(faa), "-d", str(Path(opts.mibig_proteins) / "mibig_proteins.dmnd"),
                        "-o", str(mt), "-f", "6", "qseqid", "sseqid", "pident", "length", "qlen", "slen", "qcovhsp",
                        "scovhsp", "evalue", "bitscore"], check=True, capture_output=True)
    for line in open(dt):
        if not line.startswith("#") and line.strip():
            f = line.split()
            pf[f[0]].append((int(f[19]), f"{f[3]} {f[19]}-{f[20]}"))
    for line in open(mt):
        f = line.rstrip("\n").split("\t")
        if len(f) >= 10 and (f[0] not in mb or float(f[9]) > float(mb[f[0]][9])):
            mb[f[0]] = f
    return pf, mb, ""


def cells(r, pair_names, pf, mb, mnames, mibig, searched):
    """One table row for one CDS, and the marks it carries (†, ‡)."""
    flags = set()
    p = ("; ".join(f"{d.split()[1]} {d.split()[2]}" for d in r["L2b_pfam_domains"].split(" | ") if d)
         if r["L2b_pfam_domains"] else "")
    if r["L2b_bind"] == "NOT_SEARCHED":
        found = "; ".join(x for _, x in sorted(pf.get(r["locus_tag"], [])))
        p = ((found or "no domain at the gathering threshold") if searched else "not searched") + " †"
        flags.add("†")
    m = ""
    if r["mibig_best_hit"]:
        acc = r["mibig_best_hit"].split("|")[0]
        m = (f"{r['mibig_gene'] or r['mibig_best_hit'].split('|')[1]} ({mibig(acc)['names'][:40]}, {acc}) "
             f"{float(r['mibig_identity']):.0f}%")
    elif r["mibig_queried"].startswith("yes, no"):
        m = "no hit under the filters"
    elif r["mibig_queried"].startswith("no"):
        flags.add("†")
        h = mb.get(r["locus_tag"])
        if not searched:
            m = "not searched †"
        elif h:
            acc = h[1].split("|")[0]
            g = mnames.get(h[1], {})
            m = f"{g.get('name') or h[1].split('|')[1]} ({mibig(acc)['names'][:40]}, {acc}) {float(h[2]):.0f}% †"
        else:
            m = "no hit under the filters †"
    l5 = ""
    if r["L5_status"] == "hit":
        org = r["L5_ref"].split(" | ")[0].rsplit(" ", 1)[0]
        where = {"inside": "in a region", "outside": "outside regions", "edge_overlap": "at a region edge",
                 "mixed": "mixed (ties)"}.get(r["L5_region_call"], r["L5_region_call"])
        cls = re.search(r"\(([^()]*)\)$", r["L5_ref_region"]) if r["L5_ref_region"] else None
        l5 = (f"{r['L5_product']} (*{org}*{', SID' if r['L5_ref_is_SID'] == 'yes' else ''}) {float(r['L5_pident']):.0f}%, "
              f"{where}{' (' + cls.group(1) + ')' if cls else ''}")
    elif r["L5_status"] == "no_hit_under_filters":
        l5 = "no hit under the filters"
    elif r["L5_status"] == "not_queried":
        l5 = "‡"
        flags.add("‡")
    calls = [g.split(": ", 1)[1].split(" [")[0] for g in (r["gene_map_rows"] or "").split(" || ")
             if any(g.startswith(n + ":") for n in pair_names)]
    notes = [f"CARD {r['card_family']}"] if r["card_family"] else []
    if r["bgc"] in ("", "-"):
        notes.append("outside the region")
    row = (f"| {r['locus_tag']} | {r['aa']} | {r['as_gene_function'] or '–'} | {p} | {m} | {l5} | {'; '.join(calls)} | "
           f"{float(r['LG_gene_avg_p'] or 0):.2f} | {'; '.join(notes)} |")
    return row, flags


def auto_summary(rows, bgc, arow, conv, pairs, gecco):
    """Counts and calls only: no interpretation, no compound or activity claim."""
    reg = [r for r in rows if r["bgc"] == bgc]
    core = sum(1 for r in reg if r["as_gene_function"].startswith("core"))
    l5 = [r for r in reg if r["L5_status"] == "hit"]
    l5in = sum(1 for r in l5 if r["L5_region_call"] == "inside")
    orgs = defaultdict(int)
    for r in l5:
        if r["L5_region_call"] == "inside":
            orgs[r["L5_ref"].split(" | ")[0].rsplit(" ", 1)[0]] += 1
    top_org = max(orgs.items(), key=lambda x: x[1]) if orgs else None
    S = [AUTO_HEAD,
         f"- antiSMASH class {arow['Products']}; {len(reg)} genes in the region, {core} called core biosynthetic; "
         f"boundary {arow['Boundary']}."]
    if conv:
        top = conv[0]
        ties = [c for c in conv if c["distinct_query_genes"] == top["distinct_query_genes"]]
        S.append(f"- Known clusters: the most genes matched to any MIBiG cluster is {top['distinct_query_genes']} of "
                 f"{top['query_gene_count_total']} ({', '.join(sorted({c['mibig_compound'] for c in ties}))[:160]}), "
                 f"median identity {float(top['median_pct_identity']):.0f}%"
                 f"{'; ' + str(len(ties)) + ' clusters tie' if len(ties) > 1 else ''}.")
    else:
        S.append("- Known clusters: no MIBiG cluster shares genes with this region in the package's convergence table.")
    if l5:
        S.append(f"- Reference genomes: {len(l5)} of {len(reg)} region genes have a closest public protein; {l5in} of those "
                 f"lie inside an antiSMASH region of their own genome"
                 + (f"; the most frequent genome among those is *{top_org[0]}* ({top_org[1]} genes)." if top_org else "."))
    for p in pairs:
        S.append(f"- Gene table ({p['mibig']}, {p['reference_title']}): {p['in_core']} of {p['reference_genes']} reference "
                 f"genes in the core; strength {p['strength']}.")
    S.append("- GECCO: " + ("; ".join(g["relation"].replace("_", " ").lower() + " (" + g["type"] + ", p "
                                      + format(float(g["average_p"]), ".2f") + ")" for g in gecco)
                            or "no GECCO cluster on the region contig") + ".")
    return "\n".join(S) + "\n"


def gene_kind_line(p, gr, sp, bgc):
    """The gene-table pair's reference genes present in the core, by MIBiG gene kind (gap_rescue.tsv
    reference_gene_kind). A reference whose borders include housekeeping genes ("other") can reach STRONG on those alone,
    so the biosynthetic count is given too. Present in the core = status PRESENT_IN_CORE, or a CLEAR split with a piece
    in this region (a shown split counts once, as core when a piece is in the core region), as in the table's own count."""
    if not gr:
        return ""
    def piece_here(s):
        return any((m := re.search(r"/ (BGC\d+)\s*$", s.get(k, ""))) and m.group(1) == bgc
                   for k in ("piece1_region_identity", "piece2_region_identity"))
    split_core = {s["name"] for s in sp if s.get("split_call") == "CLEAR" and piece_here(s)}
    kinds = defaultdict(lambda: [0, 0])
    for x in gr:
        k = x.get("reference_gene_kind") or "unknown"
        kinds[k][1] += 1
        kinds[k][0] += x.get("status") == "PRESENT_IN_CORE" or x.get("name") in split_core
    bc = sum(kinds[k][0] for k in ("biosynthetic", "biosynthetic-additional") if k in kinds)
    bt = sum(kinds[k][1] for k in ("biosynthetic", "biosynthetic-additional") if k in kinds)
    parts = "; ".join(f"{k} {v[0]} of {v[1]}" for k, v in sorted(kinds.items()))
    return (f"  - By MIBiG gene kind, reference genes present in the core: {parts}. Biosynthetic (core and additional): "
            f"**{bc} of {bt}**" + (" — fewer than half, although the table is STRONG."
                                   if p["strength"] == "STRONG" and bt and bc / bt < 0.5 else "."))


def per_gene_clusters(rows, bgc, conv, mibig):
    """Region genes counted by the MIBiG cluster of each gene's single best MIBiG protein (ledger mibig_best_hit). The
    convergence table comes from antiSMASH's KnownClusterBlast database, which can lack clusters, so it can miss the
    per-gene best match. -> Markdown lines, or [] when no region gene has a MIBiG hit."""
    per = defaultdict(list)
    for r in rows:
        if r["bgc"] == bgc and r["mibig_best_hit"]:
            per[r["mibig_best_hit"].split("|")[0]].append(float(r["mibig_identity"]))
    if not per:
        return []
    nreg = sum(1 for r in rows if r["bgc"] == bgc)
    top = sorted(per.items(), key=lambda x: (-len(x[1]), -max(x[1])))
    L = ["## Known clusters by the per-gene MIBiG column\n\nEach region gene's single best MIBiG protein (the ledger's "
         "MIBiG column), counted by cluster. This can differ from the table above, whose source is antiSMASH's "
         "KnownClusterBlast database.\n\n| MIBiG | Compound | Region genes whose best hit is here | Identity range |\n"
         "|---|---|--:|---|"]
    for acc, ids in top[:6]:
        L.append(f"| {acc} | {mibig(acc)['names'][:60]} | {len(ids)} of {nreg} | {min(ids):.0f}–{max(ids):.0f}% |")
    if conv and top[0][0] not in {c["mibig_accession"] for c in conv}:
        L.append("\nThe top cluster here is not in the KnownClusterBlast-based table above.")
    L.append("")
    return L


def _read_tsv(path):
    return list(csv.DictReader(open(path), delimiter="\t")) if path and Path(path).exists() else []


def _pairs(opts):
    """Gene-table pairs by (strain, bgc), and each pair's gap-rescue and split-gene rows, read beside its map."""
    by, gr, sp = defaultdict(list), {}, {}
    if not opts.gene_table_inventory:
        return by, gr, sp
    root = Path(opts.gene_table_root) if opts.gene_table_root else Path(opts.gene_table_inventory).parent
    for r in _read_tsv(opts.gene_table_inventory):
        r = dict(r)
        png = Path(r.get("png", ""))
        r["_png"] = png if png.is_absolute() else root / png
        by[(r["strain"], r["bgc"])].append(r)
        gr[r["pair"]] = _read_tsv(r["_png"].parent / "gap_rescue.tsv")
        sp[r["pair"]] = _read_tsv(r["_png"].parent / "gap_rescue_split_genes.tsv")
    return by, gr, sp


def build(opts):
    out = assert_output_outside_bundle(Path(opts.out), __file__)
    if (out / "BUILD_LOG.tsv").exists() and not opts.bgc:   # a folder may be pre-seeded with a page-search cache
        raise SystemExit(f"{out} already holds a build; versions are never overwritten")
    packages = dict(x.split("=", 1) for x in opts.package)
    skips = dict(x.split("=", 1) for x in opts.skip)
    out.mkdir(parents=True, exist_ok=True)
    led = ledger_by_strain(opts.ledger, opts.ledger_dir, out / "_ledger_by_strain")
    pairs_by, gr_by_pair, sp_by_pair = _pairs(opts)
    gecco_all = _read_tsv(opts.gecco)
    mibig = MibigIndex(opts.mibig_json)
    mnames = ({r["id"]: r for r in _read_tsv(Path(opts.mibig_proteins) / "mibig_proteins.tsv")}
              if opts.mibig_proteins else {})
    strains = opts.strains.split(",") if opts.strains else sorted(packages)
    log_path = out / "BUILD_LOG.tsv"
    new_log = not log_path.exists()
    log = open(log_path, "a", newline="")
    lw = _SafeWriter(log, delimiter="\t", lineterminator="\n")
    if new_log:
        lw.writerow(["strain", "bgc", "identity", "status", "rows", "gene_table_pairs", "hand_assessment", "file"])
    built = []
    for strain in strains:
        if strain in skips:
            lw.writerow([strain, "", "", f"SKIPPED: {skips[strain]}", "", "", "", ""])
            continue
        t0 = time.time()
        pkg = Path(packages[strain])
        regions = list(csv.DictReader(open(next(pkg.glob("*_2_inventory.csv")))))
        conv_all = defaultdict(list)
        conv_file = next(pkg.glob("*_3_mibig_convergence.csv"), None)
        for r in (csv.DictReader(open(conv_file)) if conv_file else []):
            conv_all[r["bgc_id"]].append(r)
        genes = defaultdict(list)
        for r in _read_tsv(led / f"{strain}.tsv"):
            genes[r["contig"]].append(r)
        for gs in genes.values():
            gs.sort(key=lambda g: int(g["start"]))
        plan = []
        for arow in regions:
            bgc = arow["BGC_ID"]
            if opts.bgc and bgc != opts.bgc:
                continue
            pairs = pairs_by.get((strain, bgc), [])
            rows, order, _ = select_rows(genes, bgc, pairs, gr_by_pair, sp_by_pair)
            plan.append((arow, bgc, pairs, rows, order))
        need = {r["locus_tag"] for *_, rows, _ in plan for r in rows
                if r["L2b_bind"] == "NOT_SEARCHED" or r["mibig_queried"].startswith("no")}
        pf, mb, not_run = page_search(strain, need, out, opts)
        (out / strain).mkdir(exist_ok=True)
        combined = []
        for arow, bgc, pairs, rows, order in plan:
            core = arow["Contig"]
            reg = int(arow.get("Region") or 1)
            ident = f"{strain} / {core} / region{reg:03d} / {bgc}"
            stem = f"{strain}_{node_tag(core)}_r{reg:03d}_{bgc}"
            page = out / strain / f"{stem}.md"
            if page.exists():
                raise SystemExit(f"{page} exists; versions are never overwritten")
            if not rows:
                lw.writerow([strain, bgc, ident, "NO_LEDGER_ROWS", 0, len(pairs), "", ""])
                continue
            gecco = [g for g in gecco_all if g["strain"] == strain and g["contig_full"] in order]
            conv = sorted(conv_all.get(bgc, []), key=lambda r: (-int(r["distinct_query_genes"]),
                                                                -float(r["median_pct_identity"] or 0)))
            kcb = arow.get("KCB_top", "")
            L = ['<style>table{font-size:8.5pt} td,th{padding:2px 4px}</style>\n', f"# {ident}: {arow['Products']}\n",
                 CAVEAT, "## At a glance\n",
                 f"- **Region:** {ident}, {arow['Length_kb']} kb, boundary {arow['Boundary']}, antiSMASH class "
                 f"**{arow['Products']}**.",
                 (f"- **KnownClusterBlast top hit:** {kcb.split(' | ')[0]}"
                  f"{' (' + kcb.split(' | ')[1] + ')' if ' | ' in kcb else ''}, {arow.get('KCB_proteins', '')} proteins."
                  if kcb else "- **KnownClusterBlast:** no hit.")]
            for p in pairs:
                L.append(f"- **Gene table ({p['mibig']}, {p['reference_title']}):** {p['in_core']} of {p['reference_genes']} "
                         f"reference genes in the core, on {p['core_proteins']} distinct proteins; "
                         f"{p['found_clearly_elsewhere']} found clearly elsewhere; {p['found_ambiguously']} ambiguous; "
                         f"{p['not_found']} not found; {p['set_aside']} set aside. Strength **{p['strength']}**.")
                kind = gene_kind_line(p, gr_by_pair.get(p["pair"], []), sp_by_pair.get(p["pair"], []), bgc)
                if kind:
                    L.append(kind)
            if not pairs:
                L.append("- **Gene table:** none. No MIBiG cluster met the gene-table threshold.")
            for g in gecco:
                L.append(f"- **GECCO:** {g['type']} cluster on {short(g['contig_full'])}, {g['start']}–{g['end']}, average p "
                         f"{float(g['average_p']):.3f}, {g['relation'].replace('_', ' ').lower()}.")
            if not gecco:
                L.append("- **GECCO:** no GECCO cluster on these contigs.")
            L.append("")
            for p in pairs:
                L.append(f'<img src="{p["_png"]}" style="width:100%">\n')
            L.append("## Every gene, every layer\n")
            L.append("Rows: every CDS of the region, 3 flanking CDS on each side, and the contigs the gene table or split "
                     "check points to. Pfam = full Pfam-A (gathering thresholds). MIBiG best = highest-bit-score MIBiG "
                     "protein. Closest reference-genome protein = highest-bit-score protein among the reference genomes, "
                     "its GenBank product, and whether it lies in an antiSMASH region of its own genome (class in "
                     "brackets). GECCO p = per-gene probability.\n")
            L.append("| CDS | aa | antiSMASH role | Pfam domains (envelope) | MIBiG best hit | Closest reference-genome "
                     "protein | Gene-table call | GECCO p | Notes |")
            L.append("|---|--:|---|---|---|---|---|--:|---|")
            flags = set()
            for r in rows:
                line, f = cells(r, [p["pair"] for p in pairs], pf, mb, mnames, mibig, not not_run)
                L.append(line)
                flags |= f
            L.append("")
            if "†" in flags:
                L.append(DAGGER_SEARCHED if not not_run else
                         f"† Not searched for this page (the gene lies outside any antiSMASH region): page search {not_run}.\n")
            if "‡" in flags:
                L.append(DOUBLE_DAGGER)
            L.append("Contigs: " + "; ".join(short(c) for c in order) + ".\n")
            sps = [s for p in pairs for s in sp_by_pair.get(p["pair"], [])]
            if sps:
                L.append("**Split-gene checks:**\n\n| Reference gene | Call | Piece 1 | Piece 2 | Whole-gene rival |\n"
                         "|---|---|---|---|---|")
                for s in sps:
                    L.append(f"| {s['name']} | {s['split_call']} | {s['piece1_locus']} {s['piece1_identity_pct']}% | "
                             f"{s['piece2_locus']} {s['piece2_identity_pct']}% | {s.get('whole_gene_rival_locus', '')} "
                             f"{s.get('whole_gene_rival_identity_pct', '')}% |")
                L.append("\nA split is drawn only when CLEAR, and never overrides a core call.\n")
            if conv:
                L.append("## Known clusters this locus resembles\n\n| MIBiG | Compound | Producer | Genes matched | Median "
                         "identity | MIBiG bioactivity (as recorded) |\n|---|---|---|--:|--:|---|")
                for c in conv[:6]:
                    m = mibig(c["mibig_accession"])
                    L.append(f"| {c['mibig_accession']} | {c['mibig_compound'][:60]} | {m['taxon']} | "
                             f"{c['distinct_query_genes']} of {c['query_gene_count_total']} | "
                             f"{float(c['median_pct_identity'] or 0):.0f}% | {', '.join(m['acts']) or 'none recorded'} |")
                L.append("\nBackground on reference compounds, not a claim about this strain.\n")
            L += per_gene_clusters(rows, bgc, conv, mibig)
            hand = Path(opts.assessments) / f"{stem}.md" if opts.assessments else None
            L.append("## Assessment\n")
            if hand and hand.exists():
                txt, prev = [], ""
                for line in hand.read_text().strip().splitlines():
                    if line.lstrip().startswith("- ") and prev.strip() and not prev.lstrip().startswith("- "):
                        txt.append("")
                    txt.append(line)
                    prev = line
                L.append("\n".join(txt) + "\n")
            else:
                L.append(auto_summary(rows, bgc, arow, conv, pairs, gecco))
            refs = Path(opts.refs) / f"{stem}.tsv" if opts.refs else None
            if refs and refs.exists():
                L.append("## Literature (checked at PubMed)\n")
                for r in _read_tsv(refs):
                    L.append(f"- {r['citation']} doi:{r['doi']} (PMID {r['pmid']}). {r['reports']}")
                L.append("")
            L.append(f"*Built by `locus_reading_pages.py` into `{out.name}`.*\n")
            text = "\n".join(L)
            page.write_text(text)
            combined.append(text)
            built.append(page)
            lw.writerow([strain, bgc, ident, "OK", len(rows), len(pairs), "yes" if hand and hand.exists() else "no",
                         f"{strain}/{stem}.md"])
        if combined and not opts.bgc:
            (out / f"{strain}_ALL_BGCS.md").write_text('\n\n<div style="page-break-after: always"></div>\n\n'.join(combined))
        log.flush()
        _OUT.info(f"{strain}: {len(combined)} pages, {len(need)} proteins searched"
              f"{' (page search ' + not_run + ')' if not_run else ''}, {time.time() - t0:.0f} s")
    log.close()
    return built


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, help="a new output folder (refused if it already holds a build, unless --bgc adds one page)")
    ap.add_argument("--package", action="append", default=[], required=True, metavar="STRAIN=DIR",
                    help="a strain's Mamey package folder; repeat per strain")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ledger", help="gene annotation ledger, TSV or TSV.gz, one row per CDS with a strain column")
    g.add_argument("--ledger-dir", help="a folder of per-strain ledger TSVs named <strain>.tsv")
    ap.add_argument("--gene-table-inventory", help="gene-table inventory TSV (one row per pair)")
    ap.add_argument("--gene-table-root", help="folder the inventory's png paths are relative to (default: its folder)")
    ap.add_argument("--gecco", help="GECCO cluster table TSV")
    ap.add_argument("--mibig-json", help="folder of MIBiG JSON records, <BGC>.json")
    ap.add_argument("--mibig-proteins", help="folder with mibig_proteins.dmnd and mibig_proteins.tsv")
    ap.add_argument("--proteomes", help="folder of whole-proteome FASTA, <strain>.faa")
    ap.add_argument("--pfam", help="Pfam-A HMM file")
    ap.add_argument("--hmmsearch", help="hmmsearch binary")
    ap.add_argument("--diamond", help="DIAMOND binary")
    ap.add_argument("--assessments", help="folder of hand assessments, <stem>.md")
    ap.add_argument("--refs", help="folder of checked literature, <stem>.tsv")
    ap.add_argument("--strains", help="comma-separated strains to build (default: every --package)")
    ap.add_argument("--bgc", help="build one BGC only, into an existing folder (an existing page is still refused)")
    ap.add_argument("--skip", action="append", default=[], metavar="STRAIN=REASON", help="skip a strain; logged")
    ap.add_argument("--threads", type=int, default=4, help="threads for hmmsearch and DIAMOND (default 4)")
    return ap.parse_args(argv)


def main(argv=None):
    build(parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

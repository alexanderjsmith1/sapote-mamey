#!/usr/bin/env python3
"""Build a clickable explorer from protein-class PCoA outputs: click a cohort protein, see its whole BGC.

Inputs (all read only):
- a PCoA kit directory: out_<SET>/PCOA_<SET>.tsv (id, PC1, PC2, PC3, n_represented, source, group, genus, strain, subtype,
  region_product, locus_tag, origin, length), optional NEAREST_<SET>.tsv and RUN_<SET>.json;
- the region GenBank files named in the `origin` column (<strain>__<record>.regionNNN.gbk, found anywhere under --regions);
- Mamey package crosswalks (<strain>_2b_bgc_crosswalk.csv) under --packages, for BGC numbers;
- optionally: MIBiG protein hits per gene (--mibig-hits, or --mibig-dmnd to run DIAMOND), and a BLASTp store snapshot.

Identity rules:
- A BGC number comes from a package only when that package's crosswalk lists exactly the strain's region files, each with
  the same start and end. A package of another assembly or antiSMASH run (an older raw assembly, for example) numbers its
  BGCs differently and is refused; the region is then shown on identity hold with the reason.
- BLASTp rows bind to a gene the way the engine's per-strain export does (mamey.blastp_strain_db): same strain, same locus
  tag, the same positive protein length, provenance not suspect. Rows of an exact-locus admission table bind by the SHA-256
  of the protein sequence. The BGC number of a BLASTp row is never used.
- Pass a copy of a BLASTp store (sqlite3 ".backup"), never a live store that runners write to. It is opened read only.

Output (--out, which must be new or empty): index.html plus data/*.js files the page loads with script tags, so it opens
from disk and from a static host. Also bgc_membership.tsv (every cohort point and its BGC), outliers.tsv (every cohort point
with its outlier call: identity to the closest reference/MIBiG protein and isolation in the plot; see score_outliers) and,
with --resistance-prefix, resistance_genes_in_bgcs.tsv.

Claim safety: positions and hits are sequence similarity. A close reference or MIBiG protein is not the same product.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path
try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from mamey._gbk_shim import parse_genbank_text  # noqa: E402  (Biopython-free GenBank reader)

_LOG = logging.getLogger("pcoa_bgc_explorer")
TEMPLATE = Path(__file__).resolve().parent / "pcoa_bgc_explorer_template.html"
SOURCE_CODE = {"isolate": "i", "MIBiG": "m"}          # anything else starting with SID is "s", the rest are references "r"
NR = {"ncbi_nr", "ncbi_clustered_nr"}
SP = {"local_swissprot", "ebi_uniprot"}
ORIG_START = re.compile(r"Orig\. start\s*::\s*(\d+)")
ORIG_END = re.compile(r"Orig\. end\s*::\s*(\d+)")


class ExplorerRefusal(RuntimeError):
    """An input that would make the explorer misleading."""


# ---------------------------------------------------------------- inputs
def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def set_titles(names_tsv: Path | None, captions_md: Path | None) -> dict[str, str]:
    """Set id -> class name. A TSV with columns set and title (or set and amr_gene_family), and/or caption headings of the
    form '## PCOA_<SET>_<panel>' followed by '**Principal coordinates analysis of <class> from …'."""
    out: dict[str, str] = {}
    if names_tsv:
        for r in read_tsv(names_tsv):
            t = r.get("title") or r.get("amr_gene_family") or ""
            if r.get("set") and t:
                out[r["set"]] = t
    if captions_md:
        text = captions_md.read_text()
        for m in re.finditer(r"^## PCOA_(\S+?)_[A-Za-z]+\s*\n+\*\*Principal coordinates analysis of (.+?) from ", text, re.M):
            out.setdefault(m.group(1), m.group(2))
    return out


def region_index(regions: Path) -> dict[str, Path]:
    idx: dict[str, Path] = {}
    for p in sorted(regions.rglob("*.gbk")):
        if "__" in p.name and p.name not in idx:
            idx[p.name] = p
    return idx


def crosswalk_aliases(region_files: dict[str, Path], packages: list[Path], drop: set | None = None) -> tuple[dict, dict]:
    """strain -> {region file name (without the strain prefix): crosswalk row} for the one package built from the same
    antiSMASH result as the region files; strain -> hold reason otherwise. Region files in `drop` (--drop-origins) are not
    part of the analysis and are left out of the comparison, so a package built without them still matches."""
    roster: dict[str, dict[str, tuple]] = collections.defaultdict(dict)
    for name, path in region_files.items():
        if drop and name in drop:
            continue
        strain, fn = name.split("__", 1)
        head = path.read_text(errors="replace")[:20000]
        s, e = ORIG_START.search(head), ORIG_END.search(head)
        roster[strain][fn] = (s.group(1) if s else None, e.group(1) if e else None)
    cands: dict[str, list[Path]] = collections.defaultdict(list)
    for root in packages:
        for f in sorted(root.rglob("*_2b_bgc_crosswalk.csv")):
            cands[f.name.split("_2b_bgc_crosswalk")[0]].append(f)
    bound, why = {}, {}
    for strain, want in roster.items():
        good, wrong_strain = [], False
        for f in cands.get(strain, []):
            with open(f, newline="") as fh:
                rows = [r for r in csv.DictReader(fh) if r.get("source_gbk") and r.get("bgc_id")]
            # every row must name this strain: a file name alone does not make an identity record consistent
            if any((r.get("strain") or "").strip() != strain for r in rows):
                wrong_strain = True
                continue
            got = {r["source_gbk"]: r for r in rows if not (drop and f"{strain}__{r['source_gbk']}" in drop)}
            if set(got) == set(want) and all(str(got[k].get("start")) == want[k][0] and str(got[k].get("end")) == want[k][1]
                                              for k in want):
                good.append((f, got))
        numbering = {json.dumps({k: v["bgc_id"] for k, v in g.items()}, sort_keys=True) for _, g in good}
        if len(numbering) == 1:
            f, got = good[0]
            bound[strain] = {k: dict(v, _file=str(f)) for k, v in got.items()}
        else:
            why[strain] = ("package crosswalk rows name a different strain (or none) than the crosswalk file"
                           if not good and wrong_strain else
                           "no package crosswalk lists exactly these region files with the same coordinates" if not good
                           else "packages built from the same result disagree on BGC numbers")
    return bound, why


def parse_region(path: Path) -> dict:
    text = path.read_text(errors="replace")
    recs = parse_genbank_text(text)
    if len(recs) != 1:
        raise ExplorerRefusal(f"{path.name}: expected one GenBank record, found {len(recs)}")
    rec = recs[0]
    product, edge = [], None
    cds = []
    for f in rec.features:
        q = f.qualifiers
        if f.type == "region":
            product = q.get("product", [])
            edge = (q.get("contig_edge") or [None])[0]
        if f.type != "CDS":
            continue
        doms = [d.split(" (")[0] for d in q.get("sec_met_domain", [])]
        doms += [m.group(1) for d in q.get("NRPS_PKS", []) for m in [re.match(r"Domain: (\S+)", d)] if m]
        descs = []
        for g in q.get("gene_functions", []):
            d = g.split(") ", 1)[1] if ") " in g else g
            d = re.sub(r"\s*\(Score: [^)]*\)", "", d).strip()
            if d and d not in descs:
                descs.append(d)
        aa = (q.get("translation") or [""])[0].replace(" ", "")
        cds.append(dict(start=f.location.start, end=f.location.end, strand=f.location.strand,
                        locus=(q.get("locus_tag") or [""])[0], kind=(q.get("gene_kind") or [""])[0],
                        function="; ".join(descs)[:160], product=(q.get("product") or [""])[0][:80],
                        domains=";".join(dict.fromkeys(doms))[:160], aa=len(aa),
                        sha=hashlib.sha256(aa.encode()).hexdigest() if aa else ""))
    s, e = ORIG_START.search(text), ORIG_END.search(text)
    m = re.match(r"(.+)\.(region\d+)\.gbk$", path.name.split("__", 1)[1])
    return dict(file=path.name, node=m.group(1) if m else "", region=m.group(2) if m else "", product="; ".join(product),
                edge=edge, length=len(rec.seq), orig_start=s.group(1) if s else None, orig_end=e.group(1) if e else None,
                cds=cds)


def mibig_names(gbk_dir: Path | None, faa: Path | None, names_json: Path | None) -> tuple[dict, dict]:
    """'BGCnnnnnnn|i' -> gene label (i-th translated CDS of the cluster, checked against the FASTA used to build the
    database when given) and accession -> compounds."""
    labels: dict[str, str] = {}
    seqs: dict[str, str] = {}
    if faa:
        cur = None
        for line in open(faa):
            line = line.strip()
            if line.startswith(">"):
                cur = line[1:].split()[0]; seqs[cur] = ""
            elif cur:
                seqs[cur] += line
    if gbk_dir:
        for g in sorted(gbk_dir.glob("BGC*.gbk")):
            acc, i = g.stem.split(".")[0], 0
            for rec in parse_genbank_text(g.read_text(errors="replace")):
                for f in rec.features:
                    tr = f.qualifiers.get("translation")
                    if f.type != "CDS" or not tr:
                        continue
                    i += 1
                    pid = f"{acc}|{i}"
                    if seqs and seqs.get(pid) != tr[0].replace(" ", ""):
                        raise ExplorerRefusal(f"MIBiG numbering does not match the FASTA at {pid}")
                    q = f.qualifiers
                    lab = (q.get("gene") or q.get("locus_tag") or q.get("protein_id") or [""])[0]
                    prod = (q.get("product") or [""])[0]
                    labels[pid] = (lab + (": " + prod if prod and prod != lab else ""))[:90]
    comp = {}
    if names_json:
        for e in json.load(open(names_json)).get("entries", []):
            comp[e["accession"]] = ", ".join((e.get("compounds") or [])[:2])
    return labels, comp


def mibig_hits(rows: list[dict], labels: dict, comp: dict) -> dict:
    """(region file, locus) -> three best MIBiG hits by bitscore: [accession, compound, gene, pident, qcov, evalue]."""
    best = collections.defaultdict(list)
    for h in rows:
        fn, locus = h["qseqid"].rsplit("|", 1)
        acc = h["sseqid"].split("|")[0]
        best[(fn, locus)].append((float(h["bitscore"]), [acc, comp.get(acc, ""), labels.get(h["sseqid"], ""),
                                                         round(float(h["pident"]), 1), round(float(h["qcovhsp"])),
                                                         str(h["evalue"])]))
    return {k: [x for _, x in sorted(v, key=lambda t: -t[0])[:3]] for k, v in best.items()}


def read_hits_tsv(path: Path) -> list[dict]:
    """DIAMOND outfmt 6 in mamey.diamond_align column order."""
    from mamey.diamond_align import _parse_outfmt6
    return _parse_outfmt6(str(path))


def blastp_bind(store: Path, genes: dict) -> tuple[dict, dict]:
    """(strain, locus) -> {"nr": best, "sp": best}. genes: (strain, locus) -> (aa length, sequence sha256)."""
    con = sqlite3.connect(f"file:{store.resolve()}?mode=ro", uri=True)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    out: dict = collections.defaultdict(dict)
    stats = collections.Counter()

    def put(key, ch, pid, cov, org, dfn, ev, bit):
        slot = "nr" if ch in NR else "sp" if ch in SP else None
        if not slot:
            return
        cur = out[key].get(slot)
        if cur is None or (bit or 0) > cur[-1]:
            out[key][slot] = [round(pid or 0, 1), round(cov) if cov is not None else None, (org or "")[:60],
                              (dfn or "")[:110], f"{ev:.1e}" if isinstance(ev, float) else str(ev), ch, bit or 0]
    if "hits" not in tables:
        raise ExplorerRefusal(f"{store}: no hits table")
    for st, g, aa, ch, pid, cov, org, dfn, ev, bit, sus in con.execute(
            "SELECT strain, gene, aa_length, channel, pct_identity, query_coverage, subject_organism, subject_def, evalue, "
            "bitscore, provenance_suspect FROM hits"):
        key = (st, g)
        if key not in genes:
            stats["noncurrent_locus"] += 1; continue
        if not isinstance(aa, int) or aa <= 0:
            stats["zero_or_blank_aa_length"] += 1; continue
        if aa != genes[key][0]:
            stats["aa_length_mismatch"] += 1; continue
        if sus:
            stats["provenance_suspect"] += 1; continue
        stats["locus_bound"] += 1
        put(key, ch, pid, cov, org, dfn, ev, bit)
    if "clusterednr_exact_locus_admission" in tables:
        by_sha = collections.defaultdict(list)       # one protein sequence can be several current genes
        for k, v in genes.items():
            if v[1]:
                by_sha[v[1]].append(k)
        for qsha, ch, pid, cov, org, dfn, ev, bit in con.execute(
                "SELECT query_sequence_sha256, channel, pct_identity, query_coverage_pct_derived, subject_organism, "
                "subject_definition, evalue, bitscore FROM clusterednr_exact_locus_admission"):
            for key in by_sha.get(qsha, ()):
                stats["exact_sequence"] += 1
                put(key, ch, pid, cov, org, dfn, ev, bit)
    con.close()
    return {k: {s: v[:-1] for s, v in d.items()} for k, d in out.items()}, dict(stats)


# ---------------------------------------------------------------- build
def build(a) -> dict:
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise ExplorerRefusal(f"{out} is not empty; choose a new folder (delivered outputs are never overwritten)")
    kit = Path(a.kit)
    pcoa_files = sorted(kit.glob("out_*/PCOA_*.tsv"))
    if not pcoa_files:
        raise ExplorerRefusal(f"{kit}: no out_<SET>/PCOA_<SET>.tsv files")
    titles = set_titles(Path(a.set_names) if a.set_names else None, Path(a.captions) if a.captions else None)
    cohorts = {}
    if a.cohort_table:
        for r in read_tsv(Path(a.cohort_table)):
            cohorts[r["strain"]] = r.get("cohort_id", r.get("cohort", ""))
    excluded = set(a.exclude_strain or [])
    drop = {l.strip() for l in open(a.drop_origins)} if a.drop_origins else set()
    drop.discard("")
    groups = dict(g.split("=", 1) for g in (a.group or []))
    regions = region_index(Path(a.regions))
    (out / "data/sets").mkdir(parents=True); (out / "data/regions").mkdir(parents=True)

    uses = collections.defaultdict(lambda: collections.defaultdict(list))
    index, membership, outliers = [], [], []
    for f in pcoa_files:
        s = f.stem[len("PCOA_"):]
        near = {r["id"]: r for r in read_tsv(f.parent / f"NEAREST_{s}.tsv")} if (f.parent / f"NEAREST_{s}.tsv").exists() else {}
        run = json.load(open(f.parent / f"RUN_{s}.json")) if (f.parent / f"RUN_{s}.json").exists() else {}
        labels = {}
        if a.labels_dir:
            for lf in sorted(Path(a.labels_dir).glob(f"LABELS_{s}_*.tsv"))[:1]:
                for r in read_tsv(lf):
                    labels[(r.get("region_file"), r.get("locus_tag"), r.get("PC1"))] = r.get("label_text", "")
        strings, sidx, pts, dropped = [], {}, [], 0

        def S(x):
            if x not in sidx:
                sidx[x] = len(strings); strings.append(x)
            return sidx[x]
        for r in read_tsv(f):
            if r.get("origin") in drop:
                dropped += 1; continue
            src = SOURCE_CODE.get(r["source"], "s" if r["source"].startswith("SID") else "r")
            p = [round(float(r["PC1"]), 4), round(float(r["PC2"]), 4), round(float(r.get("PC3") or 0), 4), src,
                 S(r.get("genus", "")), S(r.get("strain", "")), int(r.get("n_represented") or 1), S(r.get("subtype", "")),
                 S(r.get("region_product", ""))]
            if src == "i":
                strain = r["strain"]
                cohort = "excluded" if strain in excluded else cohorts.get(strain, r.get("group", "")) or "cohort"
                n = near.get(r["id"], {})
                p += [r.get("locus_tag", ""), r.get("origin", ""), int(r.get("length") or 0), cohort,
                      float(n["nearest_pident"]) if n.get("nearest_pident") else None,
                      float(n["nearest_qcov"]) if n.get("nearest_qcov") else None,
                      n.get("nearest_strain", ""), n.get("nearest_source", ""),
                      labels.get((r.get("origin"), r.get("locus_tag"), r["PC1"]), "")]
                in_region = r.get("origin") in regions
                if in_region:
                    uses[r["origin"]][r.get("locus_tag", "")].append([s, len(pts)])
                membership.append(dict(set=s, strain=strain, cohort_id=cohort, locus_tag=r.get("locus_tag", ""),
                                       origin=r.get("origin", ""), in_region_file=in_region,
                                       nearest_pident=n.get("nearest_pident", ""), nearest_strain=n.get("nearest_strain", "")))
            pts.append(p)
        title = titles.get(s, s)
        group = next((lab for pre, lab in groups.items() if s.startswith(pre)), a.default_group)
        calls = score_outliers(pts, a.outlier_identity)
        for i, (ratio, tier) in calls.items():
            q = pts[i]
            outliers.append(dict(set=s, title=title, group=group, point=i, strain=strings[q[5]], cohort_id=q[12], locus_tag=q[9],
                                 origin=q[10], length=q[11], nearest_pident=q[13], nearest_strain=q[15], isolation=ratio,
                                 tier=tier))
        meta = dict(set=s, title=title, pct=run.get("pct_axes"), approx_id=run.get("approx_id"), strings=strings, pts=pts,
                    dropped=dropped, isolation={str(i): c[0] for i, c in calls.items()})
        _write_js(out / "data/sets" / f"{s}.js", f"sets/{s}", meta)
        index.append(dict(set=s, title=title, group=group, points=len(pts),
                          isolates=sum(1 for q in pts if q[3] == "i"),
                          shown=sum(1 for q in pts if q[3] == "i" and q[12] != "excluded")))

    used = {fn: regions[fn] for fn in uses}
    strain_regions = {n: p for n, p in regions.items() if n.split("__", 1)[0] in {k.split("__", 1)[0] for k in used}}
    aliases, holds = crosswalk_aliases(strain_regions, [Path(p) for p in (a.packages or [])], drop)

    mh = {}
    if a.mibig_hits or a.mibig_dmnd:
        labels, comp = mibig_names(Path(a.mibig_gbk_dir) if a.mibig_gbk_dir else None,
                                   Path(a.mibig_faa) if a.mibig_faa else None,
                                   Path(a.mibig_names) if a.mibig_names else None)
        if a.mibig_hits:
            rows = read_hits_tsv(Path(a.mibig_hits))
        else:
            rows = _run_mibig(used, Path(a.mibig_dmnd), out, a.threads)
        mh = mibig_hits(rows, labels, comp)

    by_strain = collections.defaultdict(dict)
    seen = collections.defaultdict(set)      # (strain, locus) -> {(aa length, sequence sha256)} across region files
    for fn, path in sorted(used.items()):
        strain = fn.split("__", 1)[0]
        reg = parse_region(path)
        row = aliases.get(strain, {}).get(fn.split("__", 1)[1])
        reg["alias"] = row["bgc_id"] if row else None
        reg["alias_source"] = row["_file"] if row else None
        reg["alias_hold"] = None if row else holds.get(strain, "region not in the package crosswalk")
        reg["sets"] = uses[fn]
        for c in reg["cds"]:
            c["mibig"] = mh.get((fn, c["locus"]), [])
            seen[(strain, c["locus"])].add((c["aa"], c["sha"]))
        by_strain[strain][fn] = reg
    # A locus tag that names two different proteins in this run cannot carry a BLASTp hit: the store binds by
    # (strain, locus, length), so either protein could own it. Hold it instead of sharing one hit.
    genes = {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}
    locus_holds = sorted(f"{st}\t{lt}" for (st, lt), v in seen.items() if len(v) > 1)
    bstats = {}
    if a.blastp_snapshot:
        bh, bstats = blastp_bind(Path(a.blastp_snapshot), genes)
        if locus_holds:
            bstats["locus_tag_conflict_held"] = len(locus_holds)
    else:
        bh = {}
    if locus_holds:
        (out / "BLASTP_LOCUS_HOLDS.tsv").write_text("strain\tlocus_tag\n" + "\n".join(locus_holds) + "\n")
    for strain, regs in by_strain.items():
        for reg in regs.values():
            reg["cds"] = [[c["start"], c["end"], c["strand"], c["locus"], c["kind"], c["function"], c["product"],
                           c["domains"], c["aa"], bh.get((strain, c["locus"]), {}), c["mibig"]] for c in reg["cds"]]
        _write_js(out / "data/regions" / f"{_safe(strain)}.js", f"regions/{strain}", regs)

    ranked = rank_outliers(outliers, by_strain)
    with open(out / "outliers.tsv", "w", newline="") as fh:
        cols = ["rank", "tier", "set", "title", "group", "strain", "cohort_id", "identity", "bgc_product", "locus_tag", "length",
                "nearest_pident", "isolation", "contig_length", "contig_coverage", "contig_flag", "nearest_strain", "origin"]
        w = _SafeDictWriter(fh, cols, delimiter="\t", extrasaction="ignore", lineterminator="\n"); w.writeheader()
        w.writerows(ranked)
    strains = sorted(by_strain, key=_natural)
    cohort_names = sorted({m["cohort_id"] for m in membership})
    _write_js(out / "data/index.js", "index", dict(
        title=a.title, sets=index, strains=strains, files={s: _safe(s) for s in strains},
        cohorts=cohort_names, show=a.show_cohort or [c for c in cohort_names if c != "excluded"][:1],
        cohort_of={s: cohorts.get(s, "") for s in strains}, excluded=sorted(excluded),
        notes=a.note or [],
        outliers=[[r["set"], r["point"], r["strain"], r["cohort_id"], r["tier"], r["nearest_pident"], r["isolation"],
                   r["identity"], r["group"], r["title"], r["locus_tag"], r["contig_flag"]] for r in ranked if r["tier"]][:a.outlier_list]))
    page = TEMPLATE.read_text().replace("__PAGE_TITLE__", _html(a.title))
    (out / "index.html").write_text(page)

    with open(out / "bgc_membership.tsv", "w", newline="") as fh:
        w = _SafeDictWriter(fh, ["set", "strain", "cohort_id", "locus_tag", "origin", "in_region_file", "identity",
                                "nearest_pident", "nearest_strain"], delimiter="\t", lineterminator="\n")
        w.writeheader()
        for m in membership:
            reg = by_strain.get(m["strain"], {}).get(m["origin"])
            ident = f'{m["strain"]} / {reg["node"]} / {reg["region"]} / {reg["alias"] or "HOLD"}' if reg else ""
            w.writerow(dict(m, identity=ident))
    if a.resistance_prefix:
        with open(out / "resistance_genes_in_bgcs.tsv", "w", newline="") as fh:
            w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
            w.writerow(["set", "family", "identity", "alias_hold", "cohort_id", "bgc_product", "contig_edge", "gene", "aa",
                        "nearest_pident", "nearest_strain", "best_mibig_gene"])
            titles_by_set = {x["set"]: x["title"] for x in index}
            for m in membership:
                reg = by_strain.get(m["strain"], {}).get(m["origin"])
                if not m["set"].startswith(a.resistance_prefix) or not reg:
                    continue
                c = next((c for c in reg["cds"] if c[3] == m["locus_tag"]), None)
                best = c[10][0] if c and c[10] else None
                w.writerow([m["set"], titles_by_set.get(m["set"], ""),
                            f'{m["strain"]} / {reg["node"]} / {reg["region"]} / {reg["alias"] or "HOLD"}',
                            reg["alias_hold"] or "", m["cohort_id"], reg["product"], reg["edge"], m["locus_tag"],
                            c[8] if c else "", m["nearest_pident"], m["nearest_strain"],
                            f"{best[3]}% {best[2]} ({best[0]} {best[1]})" if best else ""])
    summary = dict(sets=len(index), regions=sum(len(v) for v in by_strain.values()), strains=len(by_strain),
                   aliases_bound=sum(1 for v in by_strain.values() for r in v.values() if r["alias"]),
                   aliases_on_hold=sum(1 for v in by_strain.values() for r in v.values() if not r["alias"]),
                   genes=len(genes), genes_with_mibig_hit=sum(1 for v in by_strain.values() for r in v.values()
                                                              for c in r["cds"] if c[10]),
                   genes_with_blastp=sum(1 for k in genes if bh.get(k)), blastp_rows=bstats,
                   points_outside_region_files=sum(1 for m in membership if not m["in_region_file"]))
    (out / "build_receipt.json").write_text(json.dumps(dict(summary=summary, args=vars(a)), indent=1, default=str))
    return summary


def _run_mibig(used: dict, dmnd: Path, out: Path, threads: int) -> list[dict]:
    from mamey.diamond_align import search_db
    faa = out / "mibig_query_genes.faa"
    with open(faa, "w") as fh:
        for fn, path in sorted(used.items()):
            for rec in parse_genbank_text(path.read_text(errors="replace")):
                for f in rec.features:
                    tr = f.qualifiers.get("translation")
                    if f.type == "CDS" and tr:
                        fh.write(f">{fn}|{(f.qualifiers.get('locus_tag') or [''])[0]}\n{tr[0].replace(' ', '')}\n")
    res = search_db(str(faa), str(dmnd), threads=threads, sensitivity="sensitive", evalue="1e-5", max_target_seqs=5)
    if not res["ok"]:
        raise ExplorerRefusal(f"MIBiG search did not run: {res['reason']}")
    return res["hits"]


def rank_outliers(rows, by_strain):
    """Every cohort point with its call, ranked: called points first (far, then distant or isolated), lowest identity first,
    then the most isolated. Adds the four-part identity of the point's BGC where its region file was bound."""
    for r in rows:
        # contig length and coverage when the contig name carries them (SPAdes-style "_length_<n>_cov_<x>"): a call on a
        # short or low-coverage contig is more likely an assembly artifact or contamination than a novel protein
        m = re.search(r"_length_(\d+)_cov_(\d+(?:\.\d+)?)", r["origin"] or "")
        r["contig_length"] = int(m.group(1)) if m else ""
        r["contig_coverage"] = float(m.group(2)) if m else ""
        r["contig_flag"] = ("short contig" if m and int(m.group(1)) < 2000 else "") + \
            ((" + " if m and int(m.group(1)) < 2000 else "") + "low coverage" if m and float(m.group(2)) < 5 else "")
        reg = by_strain.get(r["strain"], {}).get(r["origin"])
        r["identity"] = f'{r["strain"]} / {reg["node"]} / {reg["region"]} / {reg["alias"] or "HOLD"}' if reg else ""
        r["bgc_product"] = reg["product"] if reg else ""
    def key(r):
        far = "far" in r["tier"]; called = bool(r["tier"])
        pid = r["nearest_pident"] if r["nearest_pident"] is not None else 101.0
        return (not called, not far, pid, -(r["isolation"] or 0.0))
    rows = sorted(rows, key=key)
    for k, r in enumerate(rows, 1):
        r["rank"] = k
    return rows


def score_outliers(pts, low=70.0, far=50.0):
    """Outlier calls for the cohort points of one set (indices into pts), two signals, both reported:
    - sequence: identity to the closest reference/MIBiG protein (NEAREST): below `low` is distant, below `far` is far;
    - isolation: distance in PCoA 1-3 to the nearest non-cohort point, divided by the 95th percentile of the non-cohort
      points' own nearest-neighbour distances (> 1: emptier than 95% of the background's neighbourhoods).
    Returns {point index: (isolation ratio or None, tier)}; tier is '' for points with neither signal."""
    import numpy as np
    coh = [i for i, q in enumerate(pts) if q[3] == "i"]
    bg = [i for i, q in enumerate(pts) if q[3] != "i"]
    iso = {}
    if len(bg) > 2 and coh:
        B = np.array([pts[i][:3] for i in bg], float); C = np.array([pts[i][:3] for i in coh], float)
        try:
            from scipy.spatial import cKDTree
            t = cKDTree(B); bnn = t.query(B, k=2)[0][:, 1]; dc = t.query(C, k=1)[0]
        except ImportError:
            bnn = np.array([np.sort(np.sqrt(((B - b) ** 2).sum(1)))[1] for b in B])
            dc = np.array([np.sqrt(((B - c) ** 2).sum(1)).min() for c in C])
        thr = float(np.quantile(bnn, 0.95)) or 1e-9
        iso = {i: float(d) / thr for i, d in zip(coh, dc)}
    out = {}
    for i in coh:
        pid = pts[i][13]; r = iso.get(i)
        tags = []
        if pid is not None and pid < far:
            tags.append("far in sequence")
        elif pid is not None and pid < low:
            tags.append("distant in sequence")
        if r is not None and r > 1:
            tags.append("isolated in the plot")
        out[i] = (round(r, 2) if r is not None else None, " + ".join(tags))
    return out


def _write_js(path: Path, key: str, obj) -> None:
    path.write_text("window.__PBX&&__PBX.put(" + json.dumps(key) + "," + json.dumps(obj, separators=(",", ":")) + ");\n")


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def _natural(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def _html(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kit", required=True, help="PCoA kit folder with out_<SET>/PCOA_<SET>.tsv")
    ap.add_argument("--regions", required=True, help="folder holding the region GenBank files named in the origin column")
    ap.add_argument("--out", required=True, help="new or empty output folder")
    ap.add_argument("--packages", action="append", help="folder to search for <strain>_2b_bgc_crosswalk.csv (repeatable)")
    ap.add_argument("--labels-dir", help="folder with LABELS_<SET>_*.tsv label tables")
    ap.add_argument("--set-names", help="TSV with set and title (or amr_gene_family) columns")
    ap.add_argument("--captions", help="caption markdown with '## PCOA_<SET>_<panel>' headings")
    ap.add_argument("--cohort-table", help="TSV with strain and cohort (or cohort_id) columns")
    ap.add_argument("--show-cohort", action="append", help="cohort shown when the page opens (repeatable)")
    ap.add_argument("--exclude-strain", action="append", help="strain kept out of the default view (repeatable)")
    ap.add_argument("--drop-origins", help="file listing region files whose points are dropped entirely")
    ap.add_argument("--group", action="append", help="PREFIX=Label: group sets whose id starts with PREFIX (repeatable)")
    ap.add_argument("--default-group", default="Protein classes")
    ap.add_argument("--outlier-identity", type=float, default=70.0,
                    help="best reference/MIBiG identity below which a cohort point is called distant (far: below 50)")
    ap.add_argument("--outlier-list", type=int, default=3000, help="called outliers listed in the page (all go to outliers.tsv)")
    ap.add_argument("--resistance-prefix", help="set-id prefix of resistance-gene families; writes resistance_genes_in_bgcs.tsv")
    ap.add_argument("--mibig-hits", help="precomputed DIAMOND outfmt 6 (mamey.diamond_align columns), query ids <region file>|<locus>")
    ap.add_argument("--mibig-dmnd", help="MIBiG protein DIAMOND database to search every gene against")
    ap.add_argument("--mibig-gbk-dir", help="MIBiG GenBank files, for gene names of subject ids BGCnnnnnnn|i")
    ap.add_argument("--mibig-faa", help="the FASTA the MIBiG database was built from, to check the gene numbering")
    ap.add_argument("--mibig-names", help="MIBiG index JSON with entries[].accession and compounds")
    ap.add_argument("--blastp-snapshot", help="a COPY of a BLASTp store (sqlite3 .backup); opened read only")
    ap.add_argument("--title", default="BGC Protein Explorer")
    ap.add_argument("--note", action="append", help="sentence shown in the page footer (repeatable)")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        summary = build(a)
    except ExplorerRefusal as exc:
        _LOG.error("REFUSED: %s", exc)
        return 2
    _LOG.info(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())

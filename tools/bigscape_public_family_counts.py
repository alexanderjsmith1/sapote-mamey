#!/usr/bin/env python3
"""Count BiG-SCAPE gene cluster families per isolate: with a public genome, MIBiG only, or isolate only.

Rule (unchanged from the paper-side family recount it replaces; only the inputs are arguments):
- families at the cutoff (default 0.7) that hold at least one region of a listed isolate;
- a family's product is the majority product of its members, ties broken against parked classes;
- families whose product is parked (saccharide, ectoine, terpene, fatty_acid, NAPAA) are set aside;
- otherwise: with a public genome (any member not AS- or BGC); else MIBiG only; else isolate only.
A region with no partner is its own family in the clustering table, so singletons are counted (isolate only).

Inputs: --run <genus>=<BiG-SCAPE out dir> (repeatable; the folder holding output_files/), --isolates TSV (strain, genus),
optional --edge-table TSV (strain, region, contig_edge) for the contig-edge count, optional --drop-regex for records
never to count. Outputs in --out (must not exist): PER_ISOLATE.tsv (the B04 renderer's data columns first),
FAMILIES.tsv, PER_GENUS.tsv, DROPPED.tsv, TOTALS.json. Stops with an error on any doubt instead of guessing.

Isolate records are recognised by the staged name <strain>_<region file>; one or two underscores are both read.
Counts are capacity bookkeeping: a family "with a public genome" means a partner exists in this reference panel,
not that a compound is known; "isolate only" means no partner in this reference panel.
"""
import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
try:  # CSV formula-cell guard (mamey/csv_safety.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse, collections, csv, io, json, re, sys
from pathlib import Path

PARKED = ["saccharide", "ectoine", "terpene", "fatty_acid", "napaa"]
ISO = re.compile(r"^(AS-\d+)_+(.+)$")


def parked(s):
    t = [x for x in re.split(r"[.;,+ ]+", s) if x and x.lower() != "other"]
    return bool(t) and all(any(p in x.lower() for p in PARKED) for x in t)


def kind(s):
    return "isolate" if s.startswith("AS-") else "mibig" if s.startswith("BGC") else "public"


def read_tsv(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_text()), delimiter="\t"))


def run_files(genus, out, cutoff):
    c = f"{cutoff:g}"
    root = Path(out) / "output_files"
    if not root.is_dir():
        sys.exit(f"STOP {genus}: no output_files/ in {out}")
    runs = sorted(p for p in root.iterdir() if p.is_dir() and p.name.endswith(f"_c{c}"))
    if len(runs) != 1:
        sys.exit(f"STOP {genus}: expected exactly one *_c{c} run folder in {root}, found {[p.name for p in runs]}")
    clust = sorted(runs[0].glob(f"*/*_clustering_c{c}.tsv"))
    ann = runs[0] / "record_annotations.tsv"
    if not clust or not ann.is_file():
        sys.exit(f"STOP {genus}: no clustering tables or record_annotations.tsv in {runs[0]}")
    return runs[0], clust, ann


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="append", required=True, help="<genus>=<BiG-SCAPE out dir>")
    ap.add_argument("--isolates", required=True, help="TSV with columns strain, genus")
    ap.add_argument("--cutoff", type=float, default=0.7)
    ap.add_argument("--edge-table", help="TSV with strain, region (file stem), contig_edge")
    ap.add_argument("--drop-regex", help="records (GBK names) never counted, e.g. a ruled-out assembly part")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        sys.exit(f"STOP: {out} exists; use a new folder")
    isolates = {r["strain"]: r["genus"] for r in read_tsv(a.isolates)}
    runs = dict(x.split("=", 1) for x in a.run)
    drop = re.compile(a.drop_regex) if a.drop_regex else None
    edge = {}
    if a.edge_table:
        for r in read_tsv(a.edge_table):
            edge[(r["strain"], r["region"].replace(".gbk", ""))] = r["contig_edge"] in ("1", "True", "true")
    gt_all = collections.Counter(); per_iso = {s: collections.Counter() for s in isolates}
    famrows, runrows, dropped, noedge = [], [], [], set()
    for genus, path in runs.items():
        run_dir, clust, ann_path = run_files(genus, path, a.cutoff)
        ann = {r["GBK"]: r for r in read_tsv(ann_path)}
        families = collections.defaultdict(set)
        for n in clust:
            binlabel = n.parent.name
            for r in read_tsv(n):
                if r.get("Record_Type", "region") != "region":
                    continue
                g = r["GBK"]
                if drop and drop.match(g):
                    dropped.append(dict(genus=genus, record=g, family=r["Family"])); continue
                families[(binlabel, r["Family"])].add(g)
        present = set(); gt = collections.Counter()
        for (binlabel, fam), members in families.items():
            mine = sorted(x for x in members if ISO.match(x) and ISO.match(x).group(1) in isolates)
            if not mine:
                continue
            products = collections.Counter((ann.get(x, {}).get("Class") or ann.get(x, {}).get("Category") or "?") for x in members)
            dom = sorted(products, key=lambda x: (-products[x], parked(x), x))[0]
            nk = collections.Counter(kind(x) for x in members)
            group = "parked" if parked(dom) else "c_with_public" if nk["public"] else "b_mibig_no_public" if nk["mibig"] else "a_isolate_only"
            gt[group] += 1
            edges = []
            for x in mine:
                s, rest = ISO.match(x).groups(); present.add(s)
                e = edge.get((s, rest))
                if e is None:
                    noedge.add(x)
                edges.append(bool(e))
            if group == "a_isolate_only" and a.edge_table and all(edges):
                gt["a_on_contig_edge"] += 1
            if group != "parked" and nk["mibig"]:
                gt["nonparked_mibig_linked"] += 1
            for s in sorted({ISO.match(x).group(1) for x in mine}):
                per_iso[s][group] += 1
            mib = sorted({x.split(".")[0] for x in members if kind(x) == "mibig"})
            famrows.append(dict(genus=genus, class_bin=binlabel, family=fam, group=group, majority_product=dom, n_isolate_regions=len(mine),
                                n_public_regions=nk["public"], n_mibig=nk["mibig"], mibig=";".join(mib), isolate_regions=";".join(mine),
                                all_isolate_regions_contig_edge=all(edges) if a.edge_table else ""))
        missing = sorted(s for s, g in isolates.items() if g == genus and s not in present)
        if missing:
            sys.exit(f"STOP {genus}: isolates with no region in any family of {run_dir.name}: {missing}")
        for k, v in gt.items():
            gt_all[k] += v
        runrows.append(dict(genus=genus, source=str(run_dir), isolates_present=";".join(sorted(present)),
                            **{k: gt[k] for k in ["a_isolate_only", "a_on_contig_edge", "b_mibig_no_public", "c_with_public", "parked"]}))
    absent = sorted(s for s, g in isolates.items() if g not in runs)
    if absent:
        sys.exit(f"STOP: isolates whose genus has no --run: {absent}")
    isorows = []
    for s, c in sorted(per_iso.items()):
        npk = c["a_isolate_only"] + c["b_mibig_no_public"] + c["c_with_public"]
        isorows.append(dict(strain=s, genus=isolates[s], families=npk, in_public=c["c_with_public"],
                            not_in_public=c["a_isolate_only"] + c["b_mibig_no_public"], a_isolate_only=c["a_isolate_only"],
                            b_mibig_no_public=c["b_mibig_no_public"], parked=c["parked"]))
    tot = dict(cutoff=a.cutoff, a_isolate_only=gt_all["a_isolate_only"], b_mibig_no_public=gt_all["b_mibig_no_public"],
               c_with_public=gt_all["c_with_public"], parked_families=gt_all["parked"], nonparked_mibig_linked=gt_all["nonparked_mibig_linked"])
    if a.edge_table:
        tot["a_on_contig_edge"] = gt_all["a_on_contig_edge"]; tot["regions_without_edge_flag"] = len(noedge)
    tot["isolate_family_memberships"] = sum(r["families"] for r in isorows)
    tot["no_public_isolate_family_memberships"] = sum(r["not_in_public"] for r in isorows)
    tot["records_dropped"] = len(dropped)
    out.mkdir(parents=True)
    for name, rows in [("FAMILIES.tsv", famrows), ("PER_GENUS.tsv", runrows), ("PER_ISOLATE.tsv", isorows),
                       ("DROPPED.tsv", dropped or [dict(genus="", record="", family="")])]:
        with open(out / name, "w", newline="") as fh:
            w = _SafeDictWriter(fh, list(rows[0]), delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(rows)
    (out / "TOTALS.json").write_text(json.dumps(tot, indent=1) + "\n")
    emit(json.dumps(tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""bigscape_family_verdicts — region-accurate family verdicts from a finished BiG-SCAPE 2 database.

A family is MIBiG-matched only when a MIBiG cluster is an actual member of that family at the cutoff; a family is
"query-private" only when every member is a query record. Layers are read from the staged file names, which is
why the staging convention matters (see docs/BIGSCAPE_COHORT_WALKTHROUGH.md):

  query      file name matches --query-regex (default `^([A-Za-z]+-\\d+)_`, the strain-prefixed staging form)
  MIBiG      `BGC…` file name
  <LAYER>    file name starts with a --layer-prefix (default SID_, TYPE_) — the prefix without `_` is the layer name
  REF        `<genome stem>__<region file>` (double underscore) — any other reference genome

Verdict per query-containing family: QUERY_PRIVATE_REFERENCE_DARK (only query members), QUERY_PRIVATE_MIBIG_MATCHED
(query + MIBiG, no other layer), QUERY_MIBIG_AND_REF, QUERY_SHARED_REFERENCE (query + layer, no MIBiG).

Also written: `<out>.placement.tsv` — per-cutoff denominators (region records total, records with a family row,
singleton records), because BiG-SCAPE 2 writes family rows only for records inside a connected component at that
cutoff; "private" is private among PLACED records and must be captured with its denominator.

Provenance and class-level only. Private-in-this-run is relative to this reference set; it is not structure,
activity or novelty. Judgment deferred.
"""
from __future__ import annotations
import argparse, collections, csv, os, re, sqlite3, sys
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run outside an editable install
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from _console import emit
except ImportError:  # bare-script run outside the bundle
    emit = print


def classify(basename, query_rx, prefixes):
    """(layer, query strain or None) for one staged file name."""
    if re.match(r"^BGC\d+", basename):
        return "MIBiG", None
    for pre in prefixes:
        if basename.startswith(pre):
            return pre.rstrip("_"), None
    m = query_rx.match(basename)
    if m:
        return "query", m.group(1)
    if "__" in basename:
        return "REF", None
    return "REF", None


def verdict(layers, strains):
    if not strains:
        return "NO_QUERY"
    others = {k for k in layers if k not in ("query", "MIBiG")}
    if "MIBiG" in layers:
        return "QUERY_MIBIG_AND_REF" if others else "QUERY_PRIVATE_MIBIG_MATCHED"
    return "QUERY_SHARED_REFERENCE" if others else "QUERY_PRIVATE_REFERENCE_DARK"


def family_runs(con):
    """Run ids present in the family table, oldest first; None when the table has no run_id column."""
    cols = {row[1] for row in con.execute("pragma table_info(family)")}
    if "run_id" not in cols:
        return None
    return [r for (r,) in con.execute("select distinct run_id from family where run_id is not null order by run_id")]


def build(db_path, cutoff, query_rx, prefixes, run_id=None):
    """A BiG-SCAPE 2 database reused for a later run (the documented way to add genomes) keeps every run's families.
    Families are read from one run only: run_id when given, else the latest run. Reading all runs counts each family
    once per run."""
    con = sqlite3.connect(db_path)
    runs = family_runs(con)
    if runs is None:
        if run_id is not None:
            raise SystemExit("RUN_ID_UNAVAILABLE: this database's family table has no run_id column")
        run_sql, run_arg = "", ()
    else:
        if run_id is None:
            run_id = runs[-1] if runs else None
        elif run_id not in runs:
            raise SystemExit(f"RUN_ID_NOT_FOUND: run {run_id} is not in this database (runs: {runs})")
        run_sql, run_arg = " and f.run_id=?", (run_id,)
    rec = {rid: (os.path.basename(path), prod or "") for rid, path, prod in
           con.execute("select r.id, g.path, r.product from bgc_record r join gbk g on g.id=r.gbk_id where r.record_type='region'")}
    fam = collections.defaultdict(list)
    for fid, rid in con.execute("select f.id, bf.record_id from family f join bgc_record_family bf on bf.family_id=f.id where abs(f.cutoff-?)<1e-6" + run_sql, (cutoff,) + run_arg):
        if rid in rec:
            fam[fid].append(rid)
    placement = []
    for (cut,) in con.execute("select distinct cutoff from family f where 1=1" + run_sql + " order by cutoff", run_arg):
        placed = con.execute("select count(distinct bf.record_id) from bgc_record_family bf join family f on f.id=bf.family_id join bgc_record r on r.id=bf.record_id where abs(f.cutoff-?)<1e-6 and r.record_type='region'" + run_sql, (cut,) + run_arg).fetchone()[0]
        placement.append({"cutoff": cut, "region_records": len(rec), "records_with_family_row": placed, "singleton_records": len(rec) - placed})
    con.close()
    rows = []
    for fid, rids in fam.items():
        layers = collections.Counter(); strains = set(); prods = set(); mibig = set()
        for rid in rids:
            base, prod = rec[rid]
            layer, strain = classify(base, query_rx, prefixes)
            layers[layer] += 1
            if layer == "query":
                strains.add(strain); prods.add(prod)
            elif layer == "MIBiG":
                mibig.add(re.sub(r"\.gbk$", "", base))
        if not strains:
            continue
        rows.append({"family_id": fid, "cutoff": cutoff, "n_members": len(rids), "n_query_records": layers["query"], "n_query_strains": len(strains),
                     "query_strains": ";".join(sorted(strains)), "query_products": ";".join(sorted(p for p in prods if p)),
                     "layer_counts": ";".join(f"{k}={v}" for k, v in sorted(layers.items()) if k not in ("query",)),
                     "n_mibig": len(mibig), "mibig_ids": ";".join(sorted(mibig)[:6]), "verdict": verdict(layers, strains),
                     "cross_strain": "yes" if len(strains) >= 2 else "no (same-strain members only)"})
    rows.sort(key=lambda r: (r["verdict"], -r["n_query_strains"], -r["n_members"]))
    build.last_run = (run_id, runs)
    return rows, placement


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("db"); ap.add_argument("out", help="output TSV; the placement table goes to <out>.placement.tsv")
    ap.add_argument("--cutoff", type=float, default=0.3)
    ap.add_argument("--query-regex", default=r"^([A-Za-z]+-\d+)_")
    ap.add_argument("--layer-prefix", action="append", default=None, help="reference-layer file prefix (default SID_, TYPE_)")
    ap.add_argument("--run-id", type=int, default=None,
                    help="BiG-SCAPE run to read (default: the latest run in the database); a reused database holds every run's families")
    a = ap.parse_args(argv)
    prefixes = tuple(a.layer_prefix) if a.layer_prefix else ("SID_", "TYPE_")
    rows, placement = build(a.db, a.cutoff, re.compile(a.query_regex), prefixes, run_id=a.run_id)
    used, runs = build.last_run
    if runs is not None:
        emit(f"run {used} of {len(runs)} run(s) in the database {runs}" + ("" if a.run_id is not None or len(runs) < 2 else "; the latest run is used, pass --run-id to choose"))
    fields = ["family_id", "cutoff", "n_members", "n_query_records", "n_query_strains", "query_strains", "query_products", "layer_counts", "n_mibig", "mibig_ids", "verdict", "cross_strain"]
    with open(a.out, "w", encoding="utf-8", newline="") as h:
        w = _SafeDictWriter(h, fieldnames=fields, delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(rows)
    with open(a.out + ".placement.tsv", "w", encoding="utf-8", newline="") as h:
        w = _SafeDictWriter(h, fieldnames=["cutoff", "region_records", "records_with_family_row", "singleton_records"], delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(placement)
    cnt = collections.Counter(r["verdict"] for r in rows)
    emit(f"cutoff {a.cutoff:g}: {len(rows)} query-containing families; " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    for p in placement:
        emit(f"placement cutoff {p['cutoff']:g}: {p['records_with_family_row']} of {p['region_records']} region records have a family row ({p['singleton_records']} singletons)")
    emit(f"written: {a.out} and {a.out}.placement.tsv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

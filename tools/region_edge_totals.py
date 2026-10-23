#!/usr/bin/env python3
"""Regions per genome on a contig edge: the right-hand panel of the BGC classes-per-genome figure (B02).

Each antiSMASH result ZIP is read with the engine's own region intake (mamey.parsers.parse_bgcs_from_zip), which gives
every region the Mamey edge status: "Full-contig" when the region covers at least 95% of its contig, "Edge" when it lies
within 5 kb of a linear contig end, otherwise "Interior". A region counts as on a contig edge when it is Edge or
Full-contig; this is the measure of the Mamey package inventories, not antiSMASH's own contig_edge flag. The mamey
version is recorded so that one engine for every genome can be checked. With --region-table, each genome's region
count must equal the one-strictness region table, so the edge panel and the class counts describe the same regions.
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
try:  # CSV formula-cell guard (mamey/csv_safety.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from mamey import __version__ as MAMEY_VERSION
from mamey.parsers import parse_bgcs_from_zip

ON_EDGE = ("Edge", "Full-contig")
RULE = ("a region is on a contig edge when it covers at least 95% of its contig (Full-contig) or lies within 5 kb of "
        "a linear contig end (Edge); mamey.parsers._edge_status")
COLUMNS = ["strain", "genus", "regions", "contig_edge", "pct_edge"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_tsv(path, required):
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def edge_counts(zip_path):
    bgcs = parse_bgcs_from_zip(zip_path)
    statuses = [b.edge_status for b in bgcs]
    return len(statuses), sum(s in ON_EDGE for s in statuses), {s: statuses.count(s) for s in sorted(set(statuses))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--as-plot-data",type=Path,help="also write the public_genome_families two-part adapter TSV")
    ap.add_argument("--zips", nargs="+", type=Path, required=True)
    ap.add_argument("--genomes", required=True, type=Path, help="TSV: strain, genus (one row per ZIP)")
    ap.add_argument("--region-table", type=Path, help="tools/region_table_one_setting.py output to cross-check region counts")
    ap.add_argument("--out", required=True, type=Path, help="new TSV; <out>_RUN_INFO.json is written beside it")
    a = ap.parse_args(argv)
    info_path = a.out.with_name(a.out.stem + "_RUN_INFO.json")
    for p in (a.out, info_path, *([a.as_plot_data] if a.as_plot_data else [])):
        if p.exists():
            raise FileExistsError(f"refusing to overwrite {p}")
    genus = {r["strain"]: r["genus"] for r in read_tsv(a.genomes, ["strain", "genus"])}
    zips = {Path(z).name[:-4] if Path(z).name.lower().endswith(".zip") else Path(z).name: Path(z) for z in a.zips}
    if set(zips) != set(genus) or len(zips) != len(a.zips):
        raise ValueError(f"ZIPs and genome table name different strains: {sorted(set(zips) ^ set(genus))}")
    table_counts = None
    if a.region_table:
        table_counts = {}
        for r in read_tsv(a.region_table, ["strain", "region_file"]):
            table_counts[r["strain"]] = table_counts.get(r["strain"], 0) + 1
    rows, statuses, problems = [], {}, []
    for s in sorted(zips):
        n, edge, by_status = edge_counts(zips[s])
        statuses[s] = by_status
        if table_counts is not None and table_counts.get(s) != n:
            problems.append(f"{s}: engine reads {n} regions, region table has {table_counts.get(s)}")
        rows.append(dict(strain=s, genus=genus[s], regions=n, contig_edge=edge, pct_edge=round(100 * edge / n) if n else 0))
    if problems:
        sys.stderr.write("REGION_EDGE_TOTALS_REFUSED:\n  " + "\n  ".join(problems) + "\n")
        return 2
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    if a.as_plot_data:
        from tools.edge_plot_data import convert
        from tools._figure_route_common import write_table
        write_table(a.as_plot_data,convert(rows,[{'strain':s,'genus':genus[s]} for s in sorted(genus)]),
                    ['strain','genus','families','in_public','not_in_public'])
    info_path.write_text(json.dumps({
        "plot_data": {"path":str(a.as_plot_data.resolve()),"sha256":sha(a.as_plot_data)} if a.as_plot_data else None,
        "tool": "region_edge_totals", "mamey_version": MAMEY_VERSION, "rule": RULE, "on_edge_statuses": list(ON_EDGE),
        "region_table": str(a.region_table.resolve()) if a.region_table else None,
        "region_table_sha256": sha(a.region_table) if a.region_table else None,
        "zips": {s: {"path": str(zips[s].resolve()), "sha256": sha(zips[s])} for s in sorted(zips)},
        "edge_status_counts": statuses}, indent=2) + "\n")
    sys.stdout.write(f"{len(rows)} genomes, mamey {MAMEY_VERSION} -> {a.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

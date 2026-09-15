#!/usr/bin/env python3
"""Read-only validator for a 16S SQLite store: reports the two data-defect classes filed in
TREES_432_16S_database_provenance_and_genus_string_defects so the database can be regenerated.

  1. GENOME_JOINED_METADATA — record.metadata_source starts with 'genome' (genome_type_material,
     genome_any): host / isolation_source / geo_loc_name / country were copied from a genome
     assembly that merely shares the species name. They are not the 16S record's own and must
     be treated as empty by every consumer. Also counted: rows carrying metadata with NO
     metadata_source at all (provenance unknown), and a store with no metadata_source column.
  2. CONCATENATED_GENUS — record.genus is a known genus with its epithet glued on
     ('Streptomyceszaomyceticus'); per-genus filters then drop the record from its own genus.
     Detection is the rule in phylo_16s_build_db.split_concatenated_genus; each finding is
     cross-checked against the record's own definition (first word).

The database is opened read-only (SQLite URI mode=ro); nothing is written unless --out-dir is
given, and then only new TSV/JSON report files there. Exit status: 0 when no defect of either
class is present, 1 when any is, 2 on a usage/IO problem. A 'genus repair' or a blanked metadata
column is a regeneration step for the database owner, not something this tool performs.

Usage:
  python3 tools/phylo_16s_validate_db.py --db "16S Database/rrna16s.sqlite" [--out-dir DIR] [--top N]
"""
from __future__ import annotations
import argparse
import csv
import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
import sqlite3
import sys
from collections import Counter
from contextlib import closing
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phylo_16s_build_db import split_concatenated_genus, known_binomials  # noqa: E402

META_COLS = ("host", "isolation_source", "geo_loc_name", "country")


def open_ro(path):
    p = Path(path).resolve(strict=True)
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    if not con.execute("PRAGMA table_info(record)").fetchall():
        con.close()
        raise ValueError("16S record schema is missing")
    return con


def _columns(con):
    return {row[1] for row in con.execute("PRAGMA table_info(record)")}


def genome_joined(con):
    """Class 1 findings. Returns (summary dict, rows list)."""
    cols = _columns(con)
    present = [c for c in META_COLS if c in cols]
    nonempty = " OR ".join(f"NULLIF({c},'') IS NOT NULL" for c in present) or "0"
    summary = {"metadata_source_column_present": "metadata_source" in cols,
               "rows_with_metadata": con.execute(
                   f"SELECT count(*) FROM record WHERE {nonempty}").fetchone()[0]}
    if "metadata_source" not in cols:
        summary.update(genome_joined_rows=None, provenance_unknown_rows=summary["rows_with_metadata"],
                       by_source=[])
        return summary, []
    rows = [dict(zip(("acc_base", "acc_version", "source", "binomial", "metadata_source",
                      *present), r)) for r in con.execute(
        "SELECT acc_base, acc_version, source, binomial, metadata_source, " + ", ".join(present) +
        " FROM record WHERE metadata_source LIKE 'genome%' ORDER BY source, binomial, acc_base")]
    summary["genome_joined_rows"] = len(rows)
    summary["by_source"] = [dict(source=s, metadata_source=m, n=n) for s, m, n in con.execute(
        "SELECT source, metadata_source, count(*) FROM record WHERE metadata_source LIKE 'genome%' "
        "GROUP BY 1,2 ORDER BY 3 DESC")]
    summary["provenance_unknown_rows"] = con.execute(
        f"SELECT count(*) FROM record WHERE ({nonempty}) AND NULLIF(metadata_source,'') IS NULL"
    ).fetchone()[0]
    summary["metadata_source_values"] = [dict(metadata_source=m, n=n) for m, n in con.execute(
        "SELECT CASE WHEN metadata_source LIKE 'biosample_by_strain:%' THEN 'biosample_by_strain:*' "
        "WHEN metadata_source LIKE 'primary_INSDC:%' THEN 'primary_INSDC:*' "
        "WHEN metadata_source LIKE 'record_source_feature:%' THEN 'record_source_feature:*' "
        "ELSE COALESCE(metadata_source,'<NULL>') END, count(*) FROM record "
        "WHERE " + nonempty + " GROUP BY 1 ORDER BY 2 DESC")]
    return summary, rows


def concatenated_genus(con):
    """Class 2 findings. Returns (summary dict, rows list) — one row per distinct glued string."""
    counts = {g: n for g, n in con.execute(
        "SELECT genus, count(*) FROM record WHERE genus != '' AND genus IS NOT NULL GROUP BY genus")}
    binoms = known_binomials(con)
    findings = {}
    for g in counts:
        split_g, ep = split_concatenated_genus(g, counts)
        if ep:
            findings[g] = (split_g, ep)
    rows = []
    agree = Counter()
    by_source = Counter()
    for g, (split_g, ep) in findings.items():
        recs = con.execute("SELECT acc_base, source, definition FROM record WHERE genus=? "
                           "ORDER BY acc_base", (g,)).fetchall()
        n_agree = sum(1 for _, _, d in recs if (d or "").split()[:1] == [split_g])
        bk = f"{split_g} {ep}" in binoms
        status = "CORROBORATED" if (n_agree or bk) else "REVIEW_NEEDED"
        for _, s, _ in recs:
            by_source[s] += 1
        agree["definition_agrees"] += n_agree
        agree["definition_disagrees"] += len(recs) - n_agree
        agree[status] += 1
        agree[status + "_records"] += len(recs)
        rows.append(dict(genus_as_stored=g, split_genus=split_g, epithet=ep, n_records=len(recs),
                         n_definition_agrees=n_agree, binomial_known=bk, status=status,
                         example_acc=recs[0][0] if recs else ""))
    rows.sort(key=lambda r: (r["status"] != "CORROBORATED", -r["n_records"], r["genus_as_stored"]))
    total = con.execute("SELECT count(*) FROM record").fetchone()[0]
    affected = sum(r["n_records"] for r in rows)
    summary = dict(distinct_genus_strings=len(counts), concatenated_strings=len(rows),
                   affected_records=affected, total_records=total,
                   affected_pct=round(100.0 * affected / total, 2) if total else 0.0,
                   corroborated_strings=agree["CORROBORATED"],
                   corroborated_records=agree["CORROBORATED_records"],
                   review_needed_strings=agree["REVIEW_NEEDED"],
                   review_needed_records=agree["REVIEW_NEEDED_records"],
                   definition_agrees=agree["definition_agrees"],
                   definition_disagrees=agree["definition_disagrees"],
                   by_source=[dict(source=s, n=n) for s, n in by_source.most_common()])
    return summary, rows


def validate(db_path):
    with closing(open_ro(db_path)) as con:
        g_sum, g_rows = genome_joined(con)
        c_sum, c_rows = concatenated_genus(con)
    defects = bool(g_rows) or bool(g_sum.get("provenance_unknown_rows")) \
        or bool(c_sum["corroborated_strings"]) or not g_sum["metadata_source_column_present"]
    return dict(database=str(Path(db_path).resolve()), genome_joined=g_sum,
                concatenated_genus=c_sum, defects_present=defects), g_rows, c_rows


def render_markdown(report, c_rows, top=15):
    g, c = report["genome_joined"], report["concatenated_genus"]
    out = [f"# 16S store validation — {report['database']}", ""]
    out += ["## Class 1 — metadata joined from a genome of the same species",
            f"- metadata_source column present: {g['metadata_source_column_present']}",
            f"- rows carrying any host/isolation_source/geo_loc_name/country: {g['rows_with_metadata']}",
            f"- rows whose metadata_source starts with 'genome': {g.get('genome_joined_rows')}"]
    for b in g.get("by_source", []):
        out.append(f"  - {b['source']} / {b['metadata_source']}: {b['n']}")
    out.append(f"- rows carrying metadata with NO metadata_source (provenance unknown): "
               f"{g.get('provenance_unknown_rows')}")
    if g.get("metadata_source_values"):
        out.append("- metadata_source values over rows carrying metadata:")
        out += [f"  - {v['metadata_source']}: {v['n']}" for v in g["metadata_source_values"]]
    out += ["", "## Class 2 — concatenated binomial in record.genus",
            f"- distinct genus strings: {c['distinct_genus_strings']}",
            f"- candidate glued strings: {c['concatenated_strings']} covering {c['affected_records']} "
            f"of {c['total_records']} records ({c['affected_pct']}%)",
            f"  - CORROBORATED (definition starts with the split genus, or the binomial is already stored): "
            f"{c['corroborated_strings']} strings / {c['corroborated_records']} records — the defect",
            f"  - REVIEW_NEEDED (frequency rule only; may be a real taxon such as Nostocoides): "
            f"{c['review_needed_strings']} strings / {c['review_needed_records']} records — not counted as defects",
            f"- records whose definition first word agrees with the split genus: {c['definition_agrees']}; "
            f"disagrees: {c['definition_disagrees']}"]
    for b in c["by_source"]:
        out.append(f"  - source {b['source']}: {b['n']}")
    if c_rows:
        out += ["", "| genus as stored | split | epithet | records | definition agrees | binomial known | status | example |",
                "|---|---|---|---|---|---|---|---|"]
        out += [f"| {r['genus_as_stored']} | {r['split_genus']} | {r['epithet']} | {r['n_records']} | "
                f"{r['n_definition_agrees']} | {r['binomial_known']} | {r['status']} | {r['example_acc']} |"
                for r in c_rows[:top]]
        if len(c_rows) > top:
            out.append(f"| … {len(c_rows) - top} more in the TSV | | | | | | | |")
        review = [r for r in c_rows if r["status"] == "REVIEW_NEEDED"]
        if review:
            out += ["", "REVIEW_NEEDED strings (full list): " + ", ".join(r["genus_as_stored"] for r in review)]
    out += ["", f"**defects_present: {report['defects_present']}**"]
    return "\n".join(out) + "\n"


def write_reports(out_dir, report, g_rows, c_rows):
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, rows in (("16s_validate_genome_joined.tsv", g_rows),
                       ("16s_validate_concatenated_genus.tsv", c_rows)):
        p = d / name
        with p.open("x", newline="") as h:
            if rows:
                w = _SafeDictWriter(h, fieldnames=list(rows[0]), delimiter="\t")
                w.writeheader(); w.writerows(rows)
            else:
                h.write("no findings\n")
        paths[name] = str(p)
    p = d / "16s_validate_report.json"
    with p.open("x") as h:
        json.dump(report, h, indent=2, sort_keys=True)
    paths["16s_validate_report.json"] = str(p)
    p = d / "16s_validate_report.md"
    with p.open("x") as h:
        h.write(render_markdown(report, c_rows))
    paths["16s_validate_report.md"] = str(p)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(allow_abbrev=False, description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="16S SQLite store (opened read-only)")
    ap.add_argument("--out-dir", help="write TSV/JSON/MD reports here (new files only)")
    ap.add_argument("--top", type=int, default=15, help="rows shown in the markdown table")
    a = ap.parse_args(argv)
    try:
        report, g_rows, c_rows = validate(a.db)
    except (FileNotFoundError, ValueError, sqlite3.Error) as exc:
        sys.stderr.write(f"phylo_16s_validate_db: {exc}\n")
        return 2
    sys.stdout.write(render_markdown(report, c_rows, a.top))
    if a.out_dir:
        paths = write_reports(a.out_dir, report, g_rows, c_rows)
        sys.stdout.write("\n".join(f"wrote {p}" for p in paths.values()) + "\n")
    return 1 if report["defects_present"] else 0


if __name__ == "__main__":
    sys.exit(main())

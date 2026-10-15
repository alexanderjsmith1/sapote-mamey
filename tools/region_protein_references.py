#!/usr/bin/env python3
"""Input table of the region protein figure (B03, region_protein_by_genus): isolates plus public genomes of each genus.

Public genomes come from a classified region-protein table (batch 26 format: genome_key, role, genus, strictness,
aa, regions, source). The filters are the bee and moss Fig. 3B rules: role "reference" (public genomes; isolate and
SID rows are never references), loose antiSMASH runs, whole genomes (at least 10 regions), and one copy per genome
(the same accession base, or the same amino-acid and region totals, keeps only the first in genome_key order). The
duplicate check spans the genera requested, as in the paper builder, so the genus list is part of the result and is
recorded. Isolate rows come from tools/region_protein_totals.py with a strain -> genus table.

--comparators adds named public genomes as role "comparator" rows (labelled points, no box), e.g. the nearest genera
of an isolate placed only to family. They are taken as given (one row each: strain, genus, name, strain_label,
amino_acids, missing_CDS_lengths, open, source), are not filtered by the reference rules, and are recorded with their
source in RUN_INFO.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

try:  # CSV formula-cell guard (mamey/csv_safety.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

RULES = {"role": "reference", "strictness": "loose", "min_regions": 10,
         "one_copy": "same accession base or same (aa, regions) keeps the first in genome_key order"}
BASE = re.compile(r"(GC[AF]_\d{9}|[A-Z]{1,6}_?\d{5,})")
COLUMNS = ["strain", "genus", "amino_acids", "missing_CDS_lengths", "role"]
COMPARATOR_COLUMNS = ["name", "strain_label", "open"]
COMPARATOR_REQUIRED = ["strain", "genus", "name", "strain_label", "amino_acids", "missing_CDS_lengths", "open", "source"]


def accession_base(text):
    m = BASE.search(text)
    return re.sub(r"^GC[AF]_", "GCX_", m.group(1)).replace("_", "") if m else ""


def read_tsv(path, required):
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path}: empty table")
    return rows


def select_references(rows, genera):
    keep = {g: [] for g in genera}
    excluded = []
    seen_acc, seen_val = set(), set()
    for r in sorted(rows, key=lambda r: r["genome_key"]):
        if r["role"] != RULES["role"] or r["genus"] not in keep:
            continue
        if r["strictness"] != RULES["strictness"]:
            excluded.append((r["genome_key"], r["genus"], "not loose"))
            continue
        if int(r["regions"]) < RULES["min_regions"]:
            excluded.append((r["genome_key"], r["genus"], "not a whole genome (fewer than 10 regions)"))
            continue
        acc, val = accession_base(r["genome_key"]) or accession_base(r["source"]), (r["aa"], r["regions"])
        if (acc and acc in seen_acc) or val in seen_val:
            excluded.append((r["genome_key"], r["genus"], "duplicate copy"))
            continue
        seen_acc.add(acc)
        seen_val.add(val)
        keep[r["genus"]].append(r)
    return keep, excluded


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--classified", required=True, type=Path, help="batch-26-format classified region-protein table")
    ap.add_argument("--isolate-genera", required=True, type=Path, help="TSV: strain, genus (one row per isolate)")
    ap.add_argument("--isolate-totals", required=True, type=Path, help="TSV from tools/region_protein_totals.py")
    ap.add_argument("--comparators", type=Path, default=None, help="TSV of named comparator genomes: "
                    + ", ".join(COMPARATOR_REQUIRED))
    ap.add_argument("--out", required=True, type=Path, help="new B03 input TSV; RUN_INFO and EXCLUDED are written beside it")
    a = ap.parse_args(argv)
    run_info, excl_path = a.out.with_name(a.out.stem + "_RUN_INFO.json"), a.out.with_name(a.out.stem + "_EXCLUDED.tsv")
    for p in (a.out, run_info, excl_path):
        if p.exists():
            raise FileExistsError(f"refusing to overwrite {p}")
    classified = read_tsv(a.classified, ["genome_key", "role", "genus", "strictness", "aa", "regions", "source"])
    iso_genus = {r["strain"]: r["genus"].strip() for r in read_tsv(a.isolate_genera, ["strain", "genus"])}
    totals = {r["strain"]: r for r in read_tsv(a.isolate_totals, ["strain", "amino_acids", "missing_CDS_lengths"])}
    if set(iso_genus) != set(totals):
        raise ValueError(f"isolate genus and totals tables name different strains: {sorted(set(iso_genus) ^ set(totals))}")
    genera = sorted(set(iso_genus.values()))
    keep, excluded = select_references(classified, genera)
    out = [dict(strain=s, genus=iso_genus[s], amino_acids=totals[s]["amino_acids"],
                missing_CDS_lengths=totals[s]["missing_CDS_lengths"], role="isolate") for s in sorted(iso_genus)]
    # the classified table records no missing-CDS count for public genomes; 0 is written, as in the bee and moss inputs
    out += [dict(strain=r["genome_key"], genus=g, amino_acids=r["aa"], missing_CDS_lengths="0", role="reference")
            for g in genera for r in keep[g]]
    comparators = read_tsv(a.comparators, COMPARATOR_REQUIRED) if a.comparators else []
    taken = {r["strain"] for r in out}
    for r in comparators:
        if r["strain"] in taken:
            raise ValueError(f"comparator {r['strain']} is already an isolate or reference row")
        if r["open"] not in ("yes", "no"):
            raise ValueError(f"comparator {r['strain']}: open must be yes or no")
        taken.add(r["strain"])
    out += [dict(strain=r["strain"], genus=r["genus"], amino_acids=r["amino_acids"],
                 missing_CDS_lengths=r["missing_CDS_lengths"], role="comparator", name=r["name"],
                 strain_label=r["strain_label"], open=r["open"]) for r in comparators]
    cols = COLUMNS + (COMPARATOR_COLUMNS if comparators else [])
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n", restval="")
        w.writeheader()
        w.writerows(out)
    with excl_path.open("w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["genome_key", "genus", "reason"])
        w.writerows(excluded)
    run_info.write_text(json.dumps({
        "tool": "region_protein_references", "classified_table": str(a.classified.resolve()),
        "classified_sha256": sha(a.classified), "isolate_totals_sha256": sha(a.isolate_totals),
        "isolate_genera_sha256": sha(a.isolate_genera), "rules": RULES, "genera": genera,
        "references_per_genus": {g: len(keep[g]) for g in genera},
        "isolates_per_genus": {g: sum(v == g for v in iso_genus.values()) for g in genera},
        "excluded": len(excluded),
        "comparators": [{k: r[k] for k in ("strain", "genus", "amino_acids", "open", "source")} for r in comparators],
        "comparators_sha256": sha(a.comparators) if a.comparators else None,
        "public_genome_missing_CDS_lengths": "not recorded in the classified table; written as 0"}, indent=2) + "\n")
    sys.stdout.write("references per genus: " + ", ".join(f"{g} {len(keep[g])}" for g in genera) + f" -> {a.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

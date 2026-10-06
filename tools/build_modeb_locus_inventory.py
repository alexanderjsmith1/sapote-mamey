#!/usr/bin/env python3
"""Export translated CDS from one explicitly selected whole-assembly GenBank.

This is an offline source reader, not a search or a rescue adjudicator.
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path



if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def export(source, member, package, strain, out):
    source, package, out = Path(source).resolve(), Path(package).resolve(), Path(out).resolve()
    table = package / (strain + "_cds_table.csv")
    aliases = {}
    with table.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["strain"] != strain:
                raise ValueError("CDS table contains another strain")
            key = (row["contig"], row["locus_tag"])
            aliases.setdefault(key, []).append(row)
    from mamey.modeb_locus_scope import assembly_cds
    genes, member_hash = assembly_cds(source, member)
    seen = {(g["contig"], g["locus_tag"]) for g in genes}
    for g in genes:
        ids = []
        for row in aliases.get((g["contig"], g["locus_tag"]), []):
            if tuple(g[k] for k in ("start_1based", "end_1based", "strand", "aa_length")) != tuple(
                    int(row[k]) for k in ("start", "end", "strand", "length_aa")):
                raise ValueError("canonical CDS disagrees with package coordinates or length: " + g["locus_tag"])
            ids.append(" / ".join((strain, g["contig"], row["region"], row["bgc_id"])))
        g["identities"] = sorted(set(ids)) or [f"{strain} / {g['contig']} / no antiSMASH region / no BGC alias"]
    if not genes or set(aliases) - seen:
        raise ValueError("whole-assembly member does not contain every package CDS")
    result = dict(schema="modeb_locus_inventory_v1", strain=strain,
                  assembly_source={"path": str(source), "sha256": sha(source), "gbk_member": member,
                                   "gbk_sha256": member_hash},
                  package_cds_source={"path": str(table), "sha256": sha(table)},
                  genes=sorted(genes, key=lambda g: (g["contig"], g["start_1based"], g["locus_tag"])))
    if out in (source, table) or (out.exists() and any(out.samefile(path) for path in (source, table))):
        raise ValueError("output may not overwrite an input or inode alias")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"inventory": str(out), "sha256": sha(out), "translated_CDS": len(genes)}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    p.add_argument("--gbk-member")
    p.add_argument("--package", required=True)
    p.add_argument("--strain", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    export(a.input, a.gbk_member, a.package, a.strain, a.out)


if __name__ == "__main__":
    main()

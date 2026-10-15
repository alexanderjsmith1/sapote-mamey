#!/usr/bin/env python3
"""Class summary for the BGC class figures (B01 bgc_class_groups, B02): regions carrying each antiSMASH class, how many
of those regions are hybrids, and how many genomes carry the class, per group.

Input: the region table from tools/region_table_one_setting.py (one detection strictness; columns strain, region_file,
products). A region with several products counts once for each class and is a hybrid. Display names and families
are the bee and moss paper rules (owner, 24 Sep): capitalised names without underscores or hyphen codes; saccharide is
its own family so the figures can park it. No biological inference; counts are of the supplied regions only.
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

try:  # CSV formula-cell guard (mamey/csv_safety.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

NAMES = {"T1PKS": "Type I PKS", "T2PKS": "Type II PKS", "T3PKS": "Type III PKS", "HR-T2PKS": "Highly reducing type II PKS",
         "transAT-PKS": "Trans-AT PKS", "transAT-PKS-like": "Trans-AT PKS-like", "PKS-like": "PKS-like", "hglE-KS": "HglE-type KS",
         "NRPS": "NRPS", "NRPS-like": "NRPS-like", "NRP-metallophore": "NRP metallophore", "NI-siderophore": "NRPS-independent siderophore",
         "RiPP-like": "RiPP-like", "RRE-containing": "RRE-containing RiPP", "lassopeptide": "Lassopeptide",
         "azole-containing-RiPP": "Azole-containing RiPP", "thioamide-NRP": "Thioamide NRP", "fatty_acid": "Fatty acid",
         "NAPAA": "NAPAA", "aminopolycarboxylic-acid": "Aminopolycarboxylic acid", "hydrogen-cyanide": "Hydrogen cyanide",
         "redox-cofactor": "Redox cofactor", "terpene-precursor": "Terpene precursor", "LAP": "Linear azol(in)e peptide",
         "other": "Unclassified (antiSMASH 'other')", "amglyccycl": "Aminoglycoside/aminocyclitol", "2dos": "2-Deoxystreptamine",
         "blactam": "β-lactam", "NAGGN": "N-acetylglutaminylglutamine amide", "CDPS": "Cyclodipeptide synthase (CDPS)",
         "thioamitides": "Thioamitide", "azoxy-crosslink": "Azoxy crosslink", "cyclic-lactone-autoinducer": "Cyclic lactone autoinducer"}
FAMILIES = [("PKS", ("PKS", "hglE")), ("NRPS", ("NRPS", "NRP")),
            ("RiPP", ("lanthipeptide", "lasso", "RiPP", "RRE", "thiopeptide", "sactipeptide", "triceptide", "ranthipeptide", "LAP",
                      "linaridin", "lipolanthine", "bottromycin", "proteusin", "cyanobactin", "thioamitide", "guanidinotide",
                      "epipeptide", "crocagin", "microviridin", "lanthidin", "spliceotide")),
            ("Terpene", ("terpene",))]
PARKED = {"saccharide"}   # its own family; the genome class figures do not draw it
COLUMNS = ["group", "antismash_class", "display", "family", "regions", "hybrid_regions", "genomes"]
GENOME_COLUMNS = ["strain", "genus", "display", "family", "count"]


def display(cls):
    if cls in NAMES:
        return NAMES[cls]
    if cls.startswith("lanthipeptide-class-"):
        return "Lanthipeptide (class " + cls.split("-")[-1].upper() + ")"
    text = cls.replace("_", " ").replace("-", " ")
    return text[:1].upper() + text[1:]


def family(cls):
    if cls in PARKED:
        return "Saccharide"
    for fam, keys in FAMILIES:
        if any(k.lower() in cls.lower() for k in keys):
            return fam
    return "Other classes"


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


def summarise(regions, groups=None):
    strains = {r["strain"] for r in regions}
    if groups is not None:
        if set(groups) != strains:
            raise ValueError(f"group table and region table name different strains: "
                             f"only in groups {sorted(set(groups) - strains)}, only in regions {sorted(strains - set(groups))}")
    reg, hyb, gen = collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(set)
    seen = set()
    for r in regions:
        key = (r["strain"], r["region_file"])
        if key in seen:
            raise ValueError(f"duplicate region {key}")
        seen.add(key)
        classes = sorted({p.strip() for p in r["products"].split(";") if p.strip()})
        if not classes:
            raise ValueError(f"region without a product: {key}")
        grp = groups[r["strain"]] if groups is not None else "All"
        for cls in classes:
            reg[(grp, cls)].add(key)
            gen[(grp, cls)].add(r["strain"])
            if len(classes) > 1:
                hyb[(grp, cls)].add(key)
    order = sorted(reg, key=lambda k: (k[0], -len(reg[k]), k[1]))
    return [dict(group=g, antismash_class=c, display=display(c), family=family(c), regions=len(reg[(g, c)]),
                 hybrid_regions=len(hyb[(g, c)]), genomes=len(gen[(g, c)])) for g, c in order]


def per_genome(regions, genus, min_genomes):
    """Complete class-by-genome matrix for B02 (bgc_classes_per_genome): regions of each class in each genome, explicit
    zeros, saccharide left out, and only classes found in at least min_genomes genomes (the bee and moss S5 rules)."""
    strains = {r["strain"] for r in regions}
    if set(genus) != strains:
        raise ValueError(f"genome table and region table name different strains: {sorted(set(genus) ^ strains)}")
    count, carriers = {}, {}
    for r in regions:
        for cls in sorted({p.strip() for p in r["products"].split(";") if p.strip()}):
            if family(cls) == "Saccharide":
                continue
            count[(r["strain"], cls)] = count.get((r["strain"], cls), 0) + 1
            carriers.setdefault(cls, set()).add(r["strain"])
    shown = sorted((c for c in carriers if len(carriers[c]) >= min_genomes), key=lambda c: (family(c), display(c).lower()))
    names = [display(c) for c in shown]
    if len(set(names)) != len(names):
        raise ValueError("two classes share one display name")
    return [dict(strain=s, genus=genus[s], display=display(c), family=family(c), count=count.get((s, c), 0))
            for s in sorted(strains) for c in shown]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--regions", required=True, type=Path, help="region table from tools/region_table_one_setting.py")
    ap.add_argument("--groups", type=Path, help="optional TSV: strain, group (every strain in the region table, no others)")
    ap.add_argument("--out", required=True, type=Path, help="new class-summary TSV")
    ap.add_argument("--per-genome", type=Path, help="TSV: strain, genus; write instead the complete class-by-genome matrix for B02")
    ap.add_argument("--min-genomes", type=int, default=3, help="--per-genome: classes found in fewer genomes are left out (default 3)")
    a = ap.parse_args(argv)
    if a.out.exists():
        raise FileExistsError(f"refusing to overwrite {a.out}")
    regions = read_tsv(a.regions, ["strain", "region_file", "products"])
    if a.per_genome:
        rows = read_tsv(a.per_genome, ["strain", "genus"])
        genus = {r["strain"]: r["genus"].strip() for r in rows}
        if len(genus) != len(rows) or a.min_genomes < 1:
            raise ValueError("--per-genome needs one row per strain and --min-genomes of at least 1")
        out = per_genome(regions, genus, a.min_genomes)
        with a.out.open("w", newline="", encoding="utf-8") as fh:
            w = _SafeDictWriter(fh, fieldnames=GENOME_COLUMNS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(out)
        sys.stdout.write(f"{len(genus)} genomes x {len(out) // max(1, len(genus))} classes -> {a.out}\n")
        return 0
    groups = None
    if a.groups:
        rows = read_tsv(a.groups, ["strain", "group"])
        groups = {r["strain"]: r["group"].strip() for r in rows}
        if len(groups) != len(rows) or not all(groups.values()):
            raise ValueError("group table needs one non-empty group per strain")
    out = summarise(regions, groups)
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    sys.stdout.write(f"{len({r['strain'] for r in regions})} genomes, {len(regions)} regions, {len(out)} class rows -> {a.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

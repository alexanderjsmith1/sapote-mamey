#!/usr/bin/env python3
"""bigscape_input_decontam_guard.py — refuse BiG-SCAPE input regions that sit on contigs a decontamination removed.

Why: a BiG-SCAPE run once used a strain's antiSMASH result from before its decontamination, so some input regions sat
on removed contaminant contigs, and families that looked unique were contaminant DNA. The cleaned FASTA and a
removed-contig manifest existed; nothing compared the run's inputs with them.

Input:
  --regions DIR       folder of region GBKs as staged for BiG-SCAPE (names like <STRAIN>_<contig>.regionNNN.gbk)
  --removed STRAIN=TSV  (repeatable) a decontamination manifest whose first column is the removed contig name
                        (e.g. <strain>/decontam_<date>/<strain>_removed_contigs.tsv), or
                        clade_decontam.py's <clade>_contig_bins.tsv (keep == 0 rows); see removed_contig_ids()
  --authority-glob    optional glob of *_ASSEMBLY_AUTHORITY.md files; strains named there without a --removed manifest are
                      reported as "authority file present, no manifest given".
Matching: the contig name is read from the GBK file name after "<STRAIN>_" and before ".regionNNN"; SPAdes names are
compared on NODE_<n>_length_<L> so a trimmed coverage suffix still matches.
Exit 0 when no staged region sits on a removed contig; 4 otherwise (list printed).
"""
from __future__ import annotations
import argparse, csv, glob, re, sys
from pathlib import Path

NODE = re.compile(r"(NODE_\d+_length_\d+)")


def key(contig: str) -> str:
    m = NODE.search(contig)
    return m.group(1) if m else contig


HEADER_FIRST = {"contig", "record", "record_id"}


def removed_contig_ids(path) -> set[str]:
    """Removed contig ids from a decontamination manifest, as written. The one reader for every
    tool that takes a removed-contig list (this guard, bigscape_prep and region_table_one_setting).

    Two shapes are accepted: a plain list (first column = removed contig, optional header row), or
    the bundle's own ``deliverable_tools/clade_decontam.py`` ``<clade>_contig_bins.tsv``, which
    lists EVERY contig with a ``keep`` column; only ``keep == 0`` rows are removed there. A table
    with an ``assignment`` column and no ``keep`` column also lists every contig, so it is refused
    rather than read as all-removed. Bin rows with blank ids or unknown keep values are refused."""
    with open(path, encoding="utf-8", errors="replace", newline="") as h:
        rows = [(n, r) for n, r in enumerate(csv.reader(h, delimiter="\t"), 1)
                if r and any(c.strip() for c in r) and not r[0].strip().startswith("#")]
    if not rows:
        return set()
    header = [c.strip().casefold() for c in rows[0][1]]
    if header[0] not in HEADER_FIRST:
        return {r[0].strip() for _, r in rows if r[0].strip()}
    if "keep" in header:
        k = header.index("keep")
        removed = set()
        for n, r in rows[1:]:
            if not r[0].strip() or len(r) <= k:
                raise ValueError(f"{path}: bin table row {n} needs a contig and keep value")
            keep = r[k].strip().casefold()
            if keep not in ("0", "false", "1", "true"):
                raise ValueError(f"{path}: bin table row {n} has invalid keep value {r[k]!r}")
            if keep in ("0", "false"):
                removed.add(r[0].strip())
        return removed
    if "assignment" in header:
        raise ValueError(f"{path}: a contig bin table without a keep column lists every contig; "
                         "pass the removed-contig list, or a bin table with a keep column")
    return {r[0].strip() for _, r in rows[1:] if r[0].strip()}


def load_removed(spec: str) -> tuple[str, set[str]]:
    """STRAIN=TSV -> (strain, removed contigs compared on NODE_<n>_length_<L>)."""
    strain, path = spec.split("=", 1)
    return strain, {key(c) for c in removed_contig_ids(path)}


def check(regions: Path, removed: dict[str, set[str]]) -> list[tuple[str, str]]:
    hits = []
    for g in sorted(regions.glob("*.gbk")):
        for strain, contigs in removed.items():
            pre = f"{strain}_"
            if g.name.startswith(pre):
                contig = re.sub(r"\.region\d+\.gbk$", "", g.name[len(pre):])
                if key(contig) in contigs:
                    hits.append((strain, g.name))
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--regions", required=True, type=Path)
    ap.add_argument("--removed", action="append", required=True,
                    help="at least one STRAIN=removed-contig manifest is required")
    ap.add_argument("--authority-glob")
    a = ap.parse_args(argv)
    if not a.regions.is_dir():
        ap.error("--regions must be an existing directory")
    staged_regions = sorted(a.regions.glob("*.gbk"))
    if not staged_regions:
        ap.error("--regions contains no staged GBK files")
    try:
        removed = dict(load_removed(s) for s in a.removed)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    missing_authority = []
    if a.authority_glob:
        for f in glob.glob(a.authority_glob):
            s = Path(f).name.split("_ASSEMBLY_AUTHORITY")[0].lstrip("_")
            staged = any(p.name.startswith(f"{s}_") for p in staged_regions)
            if staged and s not in removed:
                print(f"MISSING_REMOVED_MANIFEST\t{s}\t{f}")
                missing_authority.append(s)
    hits = check(a.regions, removed)
    for s, n in hits:
        print(f"CONTAMINANT_REGION_STAGED\t{s}\t{n}")
    per = {s: sum(1 for x, _ in hits if x == s) for s in removed}
    for s, n in per.items():
        total = sum(1 for p in a.regions.glob(f"{s}_*.gbk"))
        print(f"{s}: {n} of {total} staged regions on removed contigs")
    return 4 if hits or missing_authority else 0


if __name__ == "__main__":
    sys.exit(main())

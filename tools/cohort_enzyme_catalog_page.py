#!/usr/bin/env python3
"""One self-contained, searchable HTML page from a cohort enzyme catalog and its family context.

Inputs (one folder, or two with --context):
  - tools/cohort_enzyme_catalog.py output: ENZYME_FAMILY_SUMMARY.tsv, SPECIFIC_GROUPS.tsv, SPECIFIC_MEMBERS.tsv, RUN_INFO.json
  - tools/enzyme_family_context.py output: FAMILY_CONTEXT.tsv, GENE_MIBIG_BEST.tsv

The page has two tabs:
  - specific enzymes across strains: SPECIFIC_GROUPS rows found in at least --min-strains strains (default 2), and by
    default only groups whose category is biosynthetic (mamey.domain_reference.BIOSYNTHETIC_CATEGORIES); --all-categories
    keeps every category. Each group opens to its family context and its member genes (identity, length, % identity to
    the centroid, BLASTp top-10 mean, rank-1 hit, best MIBiG gene hit, region products).
  - all enzyme families: every FAMILY_CONTEXT row with its reaction text, domains, region classes and MIBiG clusters.
The page uses no network resources (system fonts; data embedded). Its size grows with the cohort; the 44-genome run
was about 2.7 MB.
CLAIM SAFETY: carried into the page text; a group is sequence similarity and a MIBiG hit is gene similarity.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
BUNDLE = TOOLS.parent
for _p in (str(BUNDLE), str(TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import argparse
import csv
import html
import json
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

from cohort_enzyme_catalog import CatalogError, StagedOutputs  # noqa: E402

TOOL = "enzyme_catalog_page"
TEMPLATE = BUNDLE / "mamey" / "data" / "enzyme_context" / "enzyme_catalog_page.html"


def _f(x):
    return float(x) if x not in ("", None) else None


def _read(path: Path) -> list[dict]:
    if not path.is_file():
        raise CatalogError(f"{path} not found")
    return list(csv.DictReader(open(path, newline=""), delimiter="\t"))


PLACEHOLDERS = frozenset({"", "na", "n/a", "nan", "none", "null", "unknown", "?", "-"})
SLOTS = ("TITLE", "FOOTER", "DATA", "FAMS")


def fill_template(template: str, values: dict[str, str]) -> str:
    """Fill __TITLE__, __FOOTER__, __DATA__, __FAMS__ in one pass, so a slot name inside inserted data is never
    replaced again. The template must hold each slot the expected number of times and no other __NAME__ token."""
    found = Counter(re.findall(r"__([A-Z]+)__", template))
    if set(found) != set(SLOTS) or found["DATA"] != 1 or found["FAMS"] != 1:
        raise CatalogError(f"page template slots are {dict(found)}; expected TITLE, FOOTER, DATA once, FAMS once")
    return re.sub(r"__(TITLE|FOOTER|DATA|FAMS)__", lambda m: values[m.group(1)], template)

def build(catalog: Path, out_html: Path, context: Path | None = None, title: str = "Cohort enzyme groups",
          min_strains: int = 2, all_categories: bool = False) -> dict:
    context = context or catalog
    if out_html.parent.is_dir():
        StagedOutputs(out_html.parent, [out_html.name])  # refuses an existing page, link or symlink before any work
    summ = {r["family"]: r for r in _read(catalog / "ENZYME_FAMILY_SUMMARY.tsv")}
    groups = _read(catalog / "SPECIFIC_GROUPS.tsv")
    members = _read(catalog / "SPECIFIC_MEMBERS.tsv")
    fams_ctx = _read(context / "FAMILY_CONTEXT.tsv")
    mib = {r["gene_identity"]: r for r in _read(context / "GENE_MIBIG_BEST.tsv")}
    info = json.loads((catalog / "RUN_INFO.json").read_text()) if (catalog / "RUN_INFO.json").is_file() else {}
    fams = {}
    for r in fams_ctx:
        s = summ.get(r["family"], {})
        fams[r["family"]] = [r["category"], int(r["genes"]), int(r["genomes"]), r["ec_class"], r["reaction_or_function"],
                             r["usual_role"], r["reaction_source"], r["main_domains"], r["region_product_classes"],
                             r["mibig_compounds"], _f(s.get("median_blastp")) if s.get("median_blastp") else "",
                             s.get("share_below_70", "")]
    keep = [g for g in groups if int(g["strains"]) >= min_strains and (all_categories or g["biosynthetic"] == "True")]
    ids = {g["group"] for g in keep}
    rows = defaultdict(list)
    for r in members:
        if r["group"] not in ids:
            continue
        p = r["gene_identity"].split(" / ")
        if len(p) != 5 or any(x.strip().lower() in PLACEHOLDERS for x in p):
            raise CatalogError(f"identity hold: gene_identity must be strain / contig / region / BGC / locus with no "
                               f"empty or placeholder part: {r['gene_identity']!r}")
        h = mib.get(r["gene_identity"])
        rows[r["group"]].append(p + [int(r["aa_length"] or 0), _f(r["pct_id_to_centroid"]), _f(r["blastp_top10_mean"]),
                                     r["top_hit_organism"], r["top_hit_acc"], _f(r["top_hit_pct"]),
                                     1 if r["is_centroid"] == "True" else 0, r["products"],
                                     h["mibig_compound"] if h else "", _f(h["pct_identity"]) if h else None,
                                     (f"{h['mibig_accession']}, {h['mibig_organism']}" if h.get("mibig_organism")
                                      else h["mibig_accession"]) if h else ""])
    data = []
    for g in keep:
        ms = rows[g["group"]]
        agg = defaultdict(list)
        for m in ms:
            if m[13]:
                agg[(m[13], m[15])].append(m[14])
        gm = "; ".join(f"{c} [{a}] {len(x)} genes, median {st.median(x):.0f}%"
                       for (c, a), x in sorted(agg.items(), key=lambda x: (-len(x[1]), x[0]))[:5])
        data.append([g["group"], g["family"], g["category"], int(g["strains"]), int(g["members"]), _f(g["median_blastp"]), ms, gm])
    spec = info.get("specific", {})
    footer = (f"{len(data):,} groups and {sum(len(d[6]) for d in data):,} gene rows: "
              f"{'all categories' if all_categories else 'the biosynthetic-category groups'} found in {min_strains} or more "
              f"of the {info.get('genomes', '?')} genomes. Groups are DIAMOND clusters of the pooled region proteins "
              f"(settings: <code>{html.escape(str(spec.get('clusters', {}).get('settings', 'not recorded')))}</code>). "
              f"Families are the antiSMASH smCOG or domain call; categories are the Sapote-Mamey domain dictionary. "
              f"Each gene is shown as strain / contig / region / BGC alias / locus tag. The families tab lists all "
              f"{len(fams):,} families; all groups are in <code>SPECIFIC_GROUPS.tsv</code>.")
    enc = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    page = fill_template(TEMPLATE.read_text(), dict(TITLE=html.escape(title), FOOTER=footer, DATA=enc(data), FAMS=enc(fams)))
    out_html.parent.mkdir(parents=True, exist_ok=True)
    staged = StagedOutputs(out_html.parent, [out_html.name])
    try:
        (staged / out_html.name).write_text(page)
        staged.commit()
    except BaseException:
        staged.abort()
        raise
    return dict(tool=TOOL, groups=len(data), gene_rows=sum(len(d[6]) for d in data), families=len(fams),
                bytes=out_html.stat().st_size, out=str(out_html))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cohort_enzyme_catalog_page.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--catalog", type=Path, required=True, help="tools/cohort_enzyme_catalog.py output folder (run with --clusters)")
    p.add_argument("--context", type=Path, help="tools/enzyme_family_context.py output folder (default: --catalog)")
    p.add_argument("--out", type=Path, required=True, help="HTML file to write (must not exist)")
    p.add_argument("--title", default="Cohort enzyme groups")
    p.add_argument("--min-strains", type=int, default=2)
    p.add_argument("--all-categories", action="store_true", help="also list non-biosynthetic groups")
    a = p.parse_args(argv)
    try:
        if a.min_strains < 1:
            raise CatalogError("--min-strains must be 1 or more")
        build(a.catalog, a.out, a.context, a.title, a.min_strains, a.all_categories)
    except CatalogError as e:
        p.error(f"REFUSED: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

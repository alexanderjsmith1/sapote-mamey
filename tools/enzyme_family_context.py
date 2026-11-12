#!/usr/bin/env python3
"""Enzyme family context for a cohort enzyme catalog (tools/cohort_enzyme_catalog.py output).

For each family in ENZYME_GENES.tsv it writes two kinds of context, kept in separate columns:

What the family does. This is reference text, not evidence about the cohort's genes.
  - smCOG families: mamey/data/enzyme_context/smcog_reference.tsv (general reaction, usual role, EC class when the
    family maps to one). Every row there has citation_status citation_needed: it is general enzymology, not checked
    against a cited source.
  - domain families: the bundle's curated one-liner (mamey.domain_reference.CURATED) when there is one; else the DESC
    line for that name in a Pfam-A HMM file given with --pfam-hmm; else the antiSMASH description recorded in the
    packages' <strain>_3_antismash_hmm.csv; else blank.
  The source of each text is in reaction_source.

Which products the family sits with. This is evidence from the packages, for the cohort's genes.
  - region_product_classes: the antiSMASH product classes of the regions holding the family's genes, with gene counts.
  - mibig_compounds: each gene's best per-gene KnownClusterBlast hit (highest blast_score in
    <strain>_3_mibig_per_gene.csv, matched on strain, BGC alias and locus tag, so a locus tag reused in another region
    never lends its hit; a missing file, rows without a score and rows with no bgc_id are counted per strain in
    mibig_input_gaps; an empty value means no saved hit in the available input, not a negative search); the top MIBiG entries among the family's genes, with gene counts and median %
    identity. A hit means the gene resembles a gene of that MIBiG cluster, not that the strain makes the compound.
    With --mibig-index (a MIBiG reference index JSON whose entries carry accession and taxonomy.name, such as the
    MIBiG 4.0 bacterial index), each MIBiG entry is shown with its source organism, and GENE_MIBIG_BEST.tsv gains
    mibig_organism. Accessions missing from the index are shown without an organism.

Counting: each gene has its own category (ENZYME_GENES.tsv). A family's `category` is the commonest category among its
genes, `genes` counts all its genes, and `genes_by_category` gives the split; sum genes by category from ENZYME_GENES.tsv
or ENZYME_CATEGORY_SUMMARY.tsv, not from this file.

Writes FAMILY_CONTEXT.tsv, GENE_MIBIG_BEST.tsv (one row per gene with a hit) and CONTEXT_RUN_INFO.json.
CLAIM SAFETY: reference text describes enzyme families in general; MIBiG similarity is not compound identity.
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
import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

from cohort_enzyme_catalog import CatalogError, StagedOutputs, read_genomes, sha256, write_tsv  # noqa: E402
from mamey.domain_reference import CURATED  # noqa: E402

TOOL = "enzyme_family_context"
SMCOG_REFERENCE = BUNDLE / "mamey" / "data" / "enzyme_context" / "smcog_reference.tsv"


def load_smcog_reference(path: Path = SMCOG_REFERENCE) -> dict[str, dict]:
    rows = list(csv.DictReader(open(path, newline=""), delimiter="\t"))
    need = {"smcog_id", "ec_class", "reaction_or_function", "usual_role", "citation_status"}
    if not rows or not need <= set(rows[0]):
        raise CatalogError(f"{path}: needs columns {sorted(need)}")
    return {r["smcog_id"]: r for r in rows}


def load_pfam_desc(path: Path | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if path is None:
        return out
    if not path.is_file():
        raise CatalogError(f"--pfam-hmm not found: {path}")
    name = None
    with open(path, errors="replace") as fh:
        for ln in fh:
            if ln.startswith("NAME "):
                name = ln[5:].strip()
            elif ln.startswith("DESC ") and name:
                out[name] = ln[5:].strip()
                name = None
    return out


def load_mibig_organisms(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    if not path.is_file():
        raise CatalogError(f"--mibig-index not found: {path}")
    data = json.loads(path.read_text())
    entries = data.get("entries", []) if isinstance(data, dict) else data
    out = {}
    for e in entries:
        acc = str(e.get("accession", "")).split(".")[0]
        name = ((e.get("taxonomy") or {}).get("name") or "").strip()
        if acc and name:
            out[acc] = name
    if not out:
        raise CatalogError(f"{path}: no entries with accession and taxonomy.name")
    return out


def load_package_evidence(genomes: list[dict]) -> tuple[dict[str, str], dict[tuple[str, str, str], tuple], dict]:
    """Pfam/antiSMASH domain descriptions, and the best MIBiG hit per (strain, BGC alias, query gene). A hit is
    bound to a catalog gene only through the same BGC alias, so a reused locus tag in another region never lends its
    hit. A missing file, rows without a usable score and rows with no bgc_id are counted per strain (input gaps), so an
    empty MIBiG column is never read as a completed negative search."""
    asdesc: dict[str, str] = {}
    best: dict[tuple[str, str, str], tuple] = {}
    gaps: dict[str, Counter] = defaultdict(Counter)
    for g in genomes:
        s, pkg = g["strain"], g["_gc"].parent
        h = pkg / f"{s}_3_antismash_hmm.csv"
        if h.is_file():
            for r in csv.DictReader(open(h, newline="")):
                if r.get("description") and r.get("domain_name"):
                    asdesc.setdefault(r["domain_name"], r["description"])
        m = pkg / f"{s}_3_mibig_per_gene.csv"
        if not m.is_file():
            gaps[s]["missing_file"] += 1
        else:
            for r in csv.DictReader(open(m, newline="")):
                try:
                    score = float(r["blast_score"])
                    pid = float(r["pct_identity"])
                except (KeyError, TypeError, ValueError):
                    gaps[s]["rows_without_score"] += 1
                    continue
                if not (math.isfinite(score) and math.isfinite(pid) and 0 <= pid <= 100):
                    gaps[s]["rows_with_nonfinite_or_out_of_range_score"] += 1  # held: cannot be ranked or shown
                    continue
                bgc, tag = (r.get("bgc_id") or "").strip(), (r.get("query_gene") or "").strip()
                if not bgc or not tag:
                    gaps[s]["rows_without_bgc_id"] += 1  # a hit that names no BGC cannot be bound to one region's gene
                    continue
                k = (s, bgc, tag)
                if k not in best or score > best[k][0]:
                    best[k] = (score, r.get("mibig_accession", ""), r.get("mibig_compound", ""), pid,
                               r.get("pct_coverage", ""))
    return asdesc, best, gaps


CONTEXT_OUTPUTS = ("FAMILY_CONTEXT.tsv", "GENE_MIBIG_BEST.tsv", "CONTEXT_RUN_INFO.json")


def gene_key(r: dict) -> tuple[str, str, str]:
    """(strain, BGC alias, locus tag) from a catalog gene's identity strain / contig / region / BGC / locus."""
    p = r["gene_identity"].split(" / ")
    if len(p) != 5 or not all(x.strip() for x in p):
        raise CatalogError(f"gene_identity is not strain / contig / region / BGC / locus: {r['gene_identity']!r}")
    return p[0], p[3], p[4]


def build(catalog_dir: Path, genomes_tsv: Path, root: Path, out: Path | None = None, pfam_hmm: Path | None = None,
          smcog_reference: Path = SMCOG_REFERENCE, top: int = 6, mibig_index: Path | None = None) -> dict:
    out = out or catalog_dir
    genes_tsv = catalog_dir / "ENZYME_GENES.tsv"
    if not genes_tsv.is_file():
        raise CatalogError(f"{genes_tsv} not found; run tools/cohort_enzyme_catalog.py first")
    if out.is_dir():
        StagedOutputs(out, CONTEXT_OUTPUTS)  # refuses an existing output, link or symlink before any work
    genes = list(csv.DictReader(open(genes_tsv, newline=""), delimiter="\t"))
    genomes = read_genomes(genomes_tsv, root)
    run_strains = {g["strain"] for g in genomes}
    extra = sorted({r["strain"] for r in genes} - run_strains)
    if extra:
        raise CatalogError(f"{genes_tsv} has strains not in {genomes_tsv}: {', '.join(extra[:5])}")
    smref = load_smcog_reference(smcog_reference)
    pfam = load_pfam_desc(pfam_hmm)
    asdesc, mib, gaps = load_package_evidence(genomes)
    org = load_mibig_organisms(mibig_index)
    tag = lambda acc: f"{acc}, {org[acc.split('.')[0]]}" if acc.split(".")[0] in org else acc

    def describe(dom: str) -> tuple[str, str]:
        if dom in CURATED:
            return CURATED[dom][1], "bundle domain dictionary"
        if dom in pfam:
            return pfam[dom], "Pfam-A DESC"
        if dom in asdesc:
            return asdesc[dom], "antiSMASH description"
        return "", ""

    # A MIBiG row names strain, BGC alias and locus tag, not the contig. If that key belongs to catalog genes on more
    # than one contig/region, the hit cannot be bound to one of them: hold it for all of them.
    places = defaultdict(set)
    for r in genes:
        p = r["gene_identity"].split(" / ")
        places[gene_key(r)].add((p[1], p[2]) if len(p) == 5 else r["gene_identity"])
    shared = sorted(k for k, v in places.items() if len(v) > 1 and k in mib)
    for k in shared:
        gaps[k[0]]["hits_held_key_on_several_regions"] += 1
        del mib[k]
    gene_hits, byfam = [], defaultdict(list)
    for r in genes:
        byfam[r["family"]].append(r)
        h = mib.get(gene_key(r))
        if h:
            gene_hits.append(dict(gene_identity=r["gene_identity"], family=r["family"], mibig_accession=h[1],
                                  mibig_compound=h[2], mibig_organism=org.get(h[1].split(".")[0], ""),
                                  pct_identity=h[3], pct_coverage=h[4], blast_score=h[0]))
    rows = []
    for fam, v in byfam.items():
        cats = Counter(r["category"] for r in v)
        cat = cats.most_common(1)[0][0]
        doms = Counter(d for r in v for d in r["domains"].split(";") if d)
        if fam.startswith("SMCOG"):
            ref = smref.get(fam.split(":")[0], {})
            what, role, ec = ref.get("reaction_or_function", ""), ref.get("usual_role", ""), ref.get("ec_class", "")
            src = f"smCOG reference ({ref['citation_status']})" if ref else ""
        else:
            (what, src), role, ec = describe(fam), "", ""
        prod = Counter(p.strip() for r in v for p in r["products"].replace(";", ",").split(",") if p.strip())
        hits = defaultdict(list)
        for r in v:
            h = mib.get(gene_key(r))
            if h:
                hits[(h[2], h[1])].append(h[3])
        ranked = sorted(hits.items(), key=lambda x: (-len(x[1]), x[0]))[:top]
        rows.append(dict(family=fam, category=cat, genes=len(v),
                         genes_by_category="; ".join(f"{k} {n}" for k, n in cats.most_common()),
                         genomes=len({r["strain"] for r in v}), ec_class=ec,
                         reaction_or_function=what, usual_role=role, reaction_source=src,
                         main_domains="; ".join(f"{d} ({n}): {describe(d)[0]}" if describe(d)[0] else f"{d} ({n})"
                                                for d, n in doms.most_common(3)),
                         region_product_classes="; ".join(f"{p} {n}" for p, n in prod.most_common(top)),
                         genes_with_mibig_hit=sum(len(x) for x in hits.values()),
                         mibig_compounds="; ".join(f"{c} [{tag(a)}] {len(x)} genes, median {st.median(x):.0f}%"
                                                   for (c, a), x in ranked)))
    rows.sort(key=lambda r: (-r["genes"], r["family"]))
    out.mkdir(parents=True, exist_ok=True)
    staged = StagedOutputs(out, CONTEXT_OUTPUTS)
    smcog_ids = {f.split(":")[0] for f in byfam if f.startswith("SMCOG")}
    info = dict(tool=TOOL, mibig_input_gaps={k: dict(v) for k, v in sorted(gaps.items())}, families=len(rows), with_reaction_text=sum(1 for r in rows if r["reaction_or_function"]),
                by_source=dict(Counter(r["reaction_source"] or "none" for r in rows)),
                smcog_ids_without_reference=sorted(smcog_ids - set(smref)),
                genes_with_mibig_hit=len(gene_hits), pfam_names_loaded=len(pfam), mibig_organisms_loaded=len(org),
                inputs=dict(catalog_genes=dict(path=str(genes_tsv), sha256=sha256(genes_tsv)),
                            smcog_reference=dict(path=str(smcog_reference), sha256=sha256(smcog_reference)),
                            pfam_hmm=str(pfam_hmm) if pfam_hmm else None,
                            mibig_index=dict(path=str(mibig_index), sha256=sha256(mibig_index)) if mibig_index else None))
    try:
        write_tsv(staged / "FAMILY_CONTEXT.tsv", rows)
        write_tsv(staged / "GENE_MIBIG_BEST.tsv", gene_hits)
        (staged / "CONTEXT_RUN_INFO.json").write_text(json.dumps(info, indent=1) + "\n")
        staged.commit()
    except BaseException:
        staged.abort()
        raise
    return info


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="enzyme_family_context.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--catalog", type=Path, required=True, help="output folder of tools/cohort_enzyme_catalog.py")
    p.add_argument("--genomes", type=Path, required=True, help="the genomes TSV used for the catalog")
    p.add_argument("--root", type=Path, required=True, help="folder the genomes TSV paths are relative to")
    p.add_argument("--out", type=Path, help="output folder (default: the catalog folder)")
    p.add_argument("--pfam-hmm", type=Path, help="Pfam-A.hmm for domain descriptions (e.g. the BiG-SCAPE copy)")
    p.add_argument("--mibig-index", type=Path, help="MIBiG reference index JSON (entries with accession, taxonomy.name)")
    a = p.parse_args(argv)
    try:
        build(a.catalog, a.genomes, a.root, a.out, a.pfam_hmm, mibig_index=a.mibig_index)
    except CatalogError as e:
        p.error(f"REFUSED: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

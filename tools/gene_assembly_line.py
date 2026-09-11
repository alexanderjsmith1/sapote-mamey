#!/usr/bin/env python3
"""gene_assembly_line.py -- reliable PER-GENE NRPS/PKS assembly-line parser for antiSMASH region GBKs.

THE core of the gene-level workflow. Region-level domain sums are unreliable (antiSMASH merges adjacent
clusters into one region on good contigs -> inflated; fragments them on poor contigs -> deflated). This
counts modules PER GENE from the true nrpspksdomains annotations. Three rules that make it correct, each
learned the hard way:
  1. Parse ONLY /domain_id="nrpspksdomains_<gene>_<domain>" features. The /aSDomain="Condensation" string
     ALSO appears in redundant PFAM_domain (clusterhmmer) features and in detection-rule text -- counting
     those inflates every number. Use domain_id.
  2. Condensation domains are subtyped (Condensation_LCL/_DCL/_Dual/_Starter, Heterocyclization). Sum the
     family, don't match "Condensation" exactly (that returns 0).
  3. PKS carrier domains are annotated PKS_PP as well as ACP / PP-binding. Completeness checks must accept
     all three or they wrongly report zero complete PKS.

gene = the ctg\\d+_\\d+ prefix of the domain_id (fixed format, unambiguous split from the domain name).

CLI:
  python gene_assembly_line.py REGION.gbk               # list assembly-line genes
  python gene_assembly_line.py --dir input_gbks/ --out gene_catalog.tsv   # cohort catalog
Importable: parse_genes(gbk), gene_modules(domlist), catalog_region(gbk).
Stdlib only.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, re, csv, collections
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

GENE_DOM = re.compile(r'/domain_id="nrpspksdomains_(ctg\d+_\d+)_(.+?)\.\d+"')


def parse_genes(gbk_path):
    """{gene_id: [domain, ...]} from nrpspksdomains annotations only (PFAM duplicates excluded)."""
    with open(gbk_path, encoding="utf-8", errors="ignore") as fh:
        t = fh.read()
    genes = collections.defaultdict(list)
    for m in GENE_DOM.finditer(t):
        genes[m.group(1)].append(m.group(2))
    return genes


def gene_modules(doms):
    """(C, KS, A, AT, carrier, TE) module/domain counts for one gene's domain list.

    C sums all Condensation subtypes + Heterocyclization; carrier accepts PCP|ACP|PKS_PP|PP-binding."""
    c = collections.Counter(doms)
    C = sum(v for k, v in c.items() if k.startswith("Condensation") or k == "Heterocyclization")
    KS = c.get("PKS_KS", 0)
    A = sum(v for k, v in c.items() if k.startswith("AMP-binding"))
    AT = c.get("PKS_AT", 0)
    carrier = c.get("PCP", 0) + c.get("ACP", 0) + c.get("PKS_PP", 0) + c.get("PP-binding", 0)
    TE = c.get("Thioesterase", 0)
    return C, KS, A, AT, carrier, TE


def catalog_region(gbk_path):
    """List of assembly-line gene rows for a region GBK."""
    base = os.path.basename(gbk_path)
    node = re.search(r"(NODE_\d+_length_\d+)", base) or re.search(r"([\w.]+)\.region", base)
    reg = re.search(r"(region\d+)", base)
    loc = f"{node.group(1)}.{reg.group(1)}" if (node and reg) else base
    rows = []
    for gene, doms in parse_genes(gbk_path).items():
        C, KS, A, AT, carrier, TE = gene_modules(doms)
        mod = max(C, KS)
        if mod < 1:
            continue
        kind = "NRPS" if C >= KS else "PKS"
        complete = (KS >= 1 and AT >= 1 and carrier >= 1) if kind == "PKS" \
            else (C >= 1 and A >= 1 and carrier >= 1)
        rows.append(dict(node_region=loc, gene=gene, kind=kind, modules=mod,
                         condensation=C, KS=KS, TE=TE, complete=complete))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gbk", nargs="?")
    ap.add_argument("--dir", help="directory of region GBKs -> full catalog")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = []
    if a.dir:
        for f in sorted(os.listdir(a.dir)):
            if f.endswith(".gbk") and not os.path.basename(f).upper().startswith("BGC"):
                strain = f.split("_")[0]
                for r in catalog_region(os.path.join(a.dir, f)):
                    rows.append({"strain": strain, **r})
    elif a.gbk:
        rows = catalog_region(a.gbk)
    else:
        ap.error("give a GBK or --dir")
    if a.out:
        cols = list(rows[0].keys()) if rows else ["strain", "node_region", "gene", "kind", "modules"]
        with open(a.out, "w", newline="") as fh:
            w = _SafeDictWriter(fh, fieldnames=cols, delimiter="\t"); w.writeheader(); w.writerows(rows)
        emit(f"wrote {a.out}: {len(rows)} assembly-line genes")
    else:
        for r in sorted(rows, key=lambda x: -x["modules"])[:40]:
            emit(f"  {r.get('strain',''):8} {r['gene']:11} {r['modules']:2}-mod {r['kind']:4} "
                  f"{'complete' if r['complete'] else 'partial'} {r['node_region']}")


if __name__ == "__main__":
    main()

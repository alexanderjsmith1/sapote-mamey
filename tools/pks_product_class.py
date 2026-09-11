#!/usr/bin/env python3
"""pks_product_class.py -- predict polyketide product class from per-module reductive loops.

Each PKS module's reductive domains set the oxidation state of that ketide unit:
  KS+AT+ACP only           -> keto     (unreduced -> aromatic ring precursor)
  + KR                     -> hydroxyl
  + KR+DH                  -> enoyl    (C=C double bond)
  + KR+DH+ER               -> saturated (methylene)
Product-class heuristic: mostly-keto -> aromatic (T2PKS/anthracycline-like); many enoyl -> POLYENE
(conjugated, antifungal-type e.g. candicidin/nystatin); mostly-saturated -> reduced macrolide/polyether.
AT extender specificity (malonyl vs methylmalonyl) sets methyl branching. Capacity-level.

CLI: python pks_product_class.py REGION.gbk [--gene ctgN_M]
Stdlib only.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, re, collections

GENE_DOM = re.compile(r'/domain_id="nrpspksdomains_(ctg\d+_\d+)_(.+?)\.\d+"')


def gene_domain_order(gbk_path, gene=None):
    with open(gbk_path, encoding="utf-8", errors="ignore") as fh:
        t = fh.read()
    genes = collections.defaultdict(list)
    for m in GENE_DOM.finditer(t):
        genes[m.group(1)].append(m.group(2))
    return genes if gene is None else {gene: genes.get(gene, [])}


def module_states(order):
    mods, cur = [], []
    for d in order:
        if d == "PKS_KS" and cur:
            mods.append(cur); cur = [d]
        else:
            cur.append(d)
    if cur:
        mods.append(cur)
    states = []
    for m in mods:
        if "PKS_ER" in m:
            states.append("saturated")
        elif "PKS_DH" in m:
            states.append("enoyl")
        elif "PKS_KR" in m:
            states.append("hydroxyl")
        elif "PKS_KS" in m:
            states.append("keto")
    return states


def classify(states):
    if not states:
        return "not a PKS assembly line"
    keto, enoyl, sat = states.count("keto"), states.count("enoyl"), states.count("saturated")
    if keto >= len(states) * 0.6:
        return "aromatic polyketide (T2PKS/anthracycline-like)"
    if enoyl >= 2 and sat <= enoyl:
        return "POLYENE (conjugated, antifungal-type)"
    if sat >= len(states) * 0.5:
        return "reduced (macrolide/polyether-like)"
    return "partially reduced (mixed)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gbk")
    ap.add_argument("--gene")
    a = ap.parse_args()
    for gene, order in gene_domain_order(a.gbk, a.gene).items():
        if "PKS_KS" not in order:
            continue
        states = module_states(order)
        emit(f"{gene}: {classify(states)}", f"  modules: {'-'.join(states)}", sep="\n")


if __name__ == "__main__":
    main()

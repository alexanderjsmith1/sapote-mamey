#!/usr/bin/env python3
"""nrps_substrate.py -- predicted peptides + antibiotic-class signatures from A-domain substrates.

antiSMASH annotates each NRPS adenylation domain with /specificity="substrate consensus: <aa>". Read in
gene order these give a predicted peptide backbone; the nonproteinogenic residues map onto antibiotic
classes. Capacity-level: these are model predictions, NOT experimental structures.

Signatures (nonproteinogenic building blocks):
  siderophore (Fe-piracy):  diOH-Bz, OH-Orn, Fo-OH-Orn, Ac-OH-Orn, Orn
  glycopeptide (vancomycin): Hpg, Dhpg, bOH-Tyr   (confirm with P450 + halogenase + glycosyltransferase)
  lipopeptide (polymyxin):   Dab, Dhb             (confirm with cyclizing TE + lipo-starter)

CLI: python nrps_substrate.py REGION.gbk        # peptides + signature for one region
     python nrps_substrate.py --dir gbks/ --out substrate_census.tsv
Stdlib only.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, re, collections

PROTEINOGENIC = set("Ala Arg Asn Asp Cys Gln Glu Gly His Ile Leu Lys Met Phe Pro Ser Thr Trp Tyr Val".split())
SIG = {
    "siderophore": {"diOH-Bz", "OH-Orn", "Fo-OH-Orn", "Ac-OH-Orn", "Orn"},
    "glycopeptide": {"Hpg", "Dhpg", "bOH-Tyr", "3,5-DHPG"},
    "lipopeptide": {"Dab", "Dhb", "Dht"},
}


def gene_substrates(gbk_path):
    """{gene: [substrate, ...]} in file order, from nrpspksdomains AMP-binding /specificity."""
    with open(gbk_path, encoding="utf-8", errors="ignore") as fh:
        t = fh.read()
    genes = collections.defaultdict(list)
    for b in re.split(r"\n     (?=\S)", t):
        if "nrpspksdomains" not in b or "AMP-binding" not in b:
            continue
        did = re.search(r'/domain_id="nrpspksdomains_(ctg\d+_\d+)_AMP-binding', b)
        spec = re.search(r'/specificity="substrate consensus: ([^"]+)"', b)
        if did:
            genes[did.group(1)].append(spec.group(1) if spec else "X")
    return genes


def region_signature(gbk_path):
    subs = [s for seq in gene_substrates(gbk_path).values() for s in seq]
    sset = set(subs)
    sig = {k: sum(1 for s in subs if s in m) for k, m in SIG.items()}
    # confirm glycopeptide/lipopeptide with tailoring markers
    with open(gbk_path, encoding="utf-8", errors="ignore") as fh:
        t = fh.read().lower()
    conf = {}
    # v9.7.374 fix: "confirmed" here is derived purely from A-domain substrate-consensus counts
    # plus antiSMASH-annotation keyword co-occurrence (P450/halogenase/glycosyltransferase text
    # hits) -- homology/annotation-level evidence, never an experimental structure, contradicting
    # this module's own docstring ("Capacity-level: these are model predictions, NOT experimental
    # structures") and the project-wide claim-safety convention. This string is not cosmetic: the
    # consumer (tools/gene_modeb_enrichment.py, whose OWN docstring enforces "Capacity language
    # only... never 'produces'") embeds it verbatim into real Mode-B card text as "Signature:
    # capacity consistent with a glycopeptide (confirmed (...))." -- the hedge directly undercut by
    # "confirmed" in the same sentence. Reworded to match the sibling lipopeptide line's existing,
    # correctly-hedged "candidate" framing, with "strong" only reflecting the two corroborating
    # markers here (P450 AND halogenase/GT) vs. lipopeptide's one (cyclizing TE) -- a confidence
    # distinction, not an identity claim.
    if sig["glycopeptide"] >= 3 and "p450" in t and ("halogenase" in t or "glycosyl" in t):
        conf["glycopeptide"] = "strong candidate (P450 crosslinking + halogenase/GT present)"
    if sig["lipopeptide"] >= 1 and t.count("thioesterase") >= 1:
        conf["lipopeptide"] = "candidate (Dab + cyclizing TE)"
    return subs, sig, conf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gbk", nargs="?")
    ap.add_argument("--dir")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.gbk:
        genes = gene_substrates(a.gbk)
        subs, sig, conf = region_signature(a.gbk)
        emit(f"predicted residues (gene order): {' - '.join(subs)}", f"nonproteinogenic: {[s for s in subs if s not in PROTEINOGENIC and s != 'X']}", f"signatures: { {k: v for k, v in sig.items() if v} }", sep="\n")
        for k, v in conf.items():
            emit(f"  {k}: {v}")
    elif a.dir:
        census = collections.Counter()
        for f in os.listdir(a.dir):
            if f.endswith(".gbk") and not os.path.basename(f).upper().startswith("BGC"):
                for seq in gene_substrates(os.path.join(a.dir, f)).values():
                    census.update(seq)
        out = a.out or "substrate_census.tsv"
        with open(out, "w") as fh:
            fh.write("substrate\tcount\tnonproteinogenic\n")
            for s, n in census.most_common():
                fh.write(f"{s}\t{n}\t{'no' if s in PROTEINOGENIC or s == 'X' else 'yes'}\n")
        emit(f"wrote {out}: {len(census)} substrate types")
    else:
        ap.error("give a GBK or --dir")


if __name__ == "__main__":
    main()

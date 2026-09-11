#!/usr/bin/env python3
"""build_pfam_desc_map — extract Pfam NAME->{acc,desc} from a local Pfam-A.hmm into pfam_desc_map.json.
Drop the output next to a domain_prevalence_ranking.json (same OUT dir) and domain_prevalence_widget.py will
auto-enrich clusterhmmer families with plain-English descriptions. Uses the registered local asset
(BigSCAPE/Pfam-A.hmm); do NOT re-download it (see OFFICIAL_DATA/ASSET_REGISTRY.tsv).

Usage:
  python3 tools/build_pfam_desc_map.py --hmm <Pfam-A.hmm> --out <dir> [--labels <labels.txt>]
"""
import argparse, json, os, sys

def extract(hmm, keep=None):
    name=acc=desc=None; found={}
    with open(hmm, errors="replace") as f:
        for line in f:
            if line.startswith("NAME "): name=line[5:].strip()
            elif line.startswith("ACC "): acc=line[4:].strip()
            elif line.startswith("DESC "): desc=line[5:].strip()
            elif line.startswith("//"):
                if name and (keep is None or name in keep) and name not in found:
                    found[name]={"acc":acc,"desc":desc}
                name=acc=desc=None
    return found

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--hmm", required=True, help="path to Pfam-A.hmm (registered asset; do not re-download)")
    ap.add_argument("--out", required=True, help="dir to write pfam_desc_map.json into")
    ap.add_argument("--labels", default=None, help="optional newline label list to restrict the map")
    a=ap.parse_args()
    if not os.path.exists(a.hmm):
        sys.exit(f"Pfam-A.hmm not found: {a.hmm}")
    keep=None
    if a.labels and os.path.exists(a.labels):
        keep={x.strip() for x in open(a.labels) if x.strip()}
    m=extract(a.hmm, keep)
    os.makedirs(a.out, exist_ok=True)
    outp=os.path.join(a.out,"pfam_desc_map.json")
    json.dump(m, open(outp,"w"))
    print(f"wrote {len(m)} Pfam descriptions -> {outp}")

if __name__=="__main__":
    main()

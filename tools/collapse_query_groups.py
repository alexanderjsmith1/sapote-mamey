#!/usr/bin/env python3
"""collapse_query_groups.py <pruned.nwk> <annotation.tsv> <out_prefix>

A 100-query placement tree is a supplement figure, not a main-text one. Most queries share a
nearest reference, so the readable version collapses each set of queries sitting on the same
nearest reference into ONE tip labelled with the group size and its host breakdown.

Grouping rule: for every query tip, its nearest reference tip by patristic distance in the SUPPLIED
tree. Queries with the same nearest reference form one group. One representative tip is kept (the
lowest AS number, so the choice is deterministic and reproducible); the rest are pruned. The label
records every member, so nothing is hidden -- e.g. "query +2 (Bombus 3)".

Writes <out_prefix>_pruned.nwk, <out_prefix>_ggtree_annotation.tsv (same columns as the producer)
and <out_prefix>_groups.tsv, the full membership table so any collapsed tip can be expanded back.

Claim-safety: grouping is by nearest reference in a 16S tree; it is a NEIGHBOURHOOD grouping, not a
claim that the grouped strains are the same species or the same strain. Judgment deferred.
"""
import sys, csv, re, collections
from Bio import Phylo

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _console import emit

def main():
    nwk, ann_p, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    ann = {r["tip"]: r for r in csv.DictReader(open(ann_p), delimiter="\t")}
    t = Phylo.read(nwk, "newick")
    tips = t.get_terminals()
    q = [x for x in tips if ann.get(x.name, {}).get("kind") == "query"]
    refs = [x for x in tips if ann.get(x.name, {}).get("kind") == "reference"
            and "outgroup" not in (x.name or "").lower()]

    def asnum(n):
        m = re.search(r"(\d+)", n or "")
        return int(m.group(1)) if m else 10**9

    groups = collections.defaultdict(list)
    for qq in q:
        nearest = min(refs, key=lambda r: (t.distance(qq, r), r.name or ""))
        groups[nearest.name].append(qq)

    keep, drop, rows = {}, [], []
    for refname, members in groups.items():
        members.sort(key=lambda x: asnum(ann[x.name].get("as_id") or x.name))
        rep = members[0]
        keep[rep.name] = members
        drop += members[1:]
        for m in members:
            rows.append((refname, ann[m.name].get("as_id", m.name), ann[m.name].get("host", ""),
                         ann[m.name].get("accession", ""), "representative" if m is rep else "collapsed"))

    for x in drop:
        try:
            t.prune(x)
        except Exception as _exc:  # overlapping groups can leave a tip already pruned; record, don't hide
            sys.stderr.write(f"[collapse] prune skipped {x!r}: {type(_exc).__name__}\n")
    Phylo.write(t, outp + "_pruned.nwk", "newick")

    hdr = ["tip", "kind", "as_id", "host", "region", "accession", "validation",
           "label_withloc", "label_noloc", "ref_label", "origin"]
    with open(outp + "_ggtree_annotation.tsv", "w") as out:
        out.write("\t".join(hdr) + "\n")
        for x in t.get_terminals():
            r = dict(ann.get(x.name, {"tip": x.name, "kind": "reference"}))
            if r.get("kind") == "query" and x.name in keep:
                mem = keep[x.name]
                hosts = collections.Counter(ann[m.name].get("host", "") or "host not recorded" for m in mem)
                # A group of one is just a strain: "query (Bombus sp.)", not "query (Bombus sp. 1)".
                if len(mem) == 1:
                    hs = next(iter(hosts))
                else:
                    hs = ", ".join(f"{h} {n}" for h, n in sorted(hosts.items(), key=lambda kv: (-kv[1], kv[0])))
                aid = r.get("as_id", x.name)
                extra = f" +{len(mem)-1}" if len(mem) > 1 else ""
                lab = f"{aid}{extra} ({hs})"
                r["label_noloc"] = lab; r["label_withloc"] = lab
            out.write("\t".join((r.get(k, "") or "") for k in hdr) + "\n")

    with open(outp + "_groups.tsv", "w") as out:
        out.write("nearest_reference\tas_id\thost\taccession\trole\n")
        for a in sorted(rows, key=lambda z: (z[0], asnum(z[1]))):
            out.write("\t".join(a) + "\n")

    emit(f"[collapse] {len(q)} queries -> {len(groups)} groups on {len(groups)} distinct nearest "
          f"references; {len(drop)} query tips collapsed; tree now {len(t.get_terminals())} tips "
          f"-> {outp}_pruned.nwk")


if __name__ == "__main__":
    main()

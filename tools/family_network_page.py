"""Promoted family-network layout on an explicitly bound membership table.

TSV: family, owner, owner_kind (isolate/public/MIBiG), products. Each row is one
region membership at the declared cutoff. Repeated rows are meaningful regions.
This display does not infer strain ownership from names, query another run, or
refit families. Parked-class and singleton display rules match the source route.
"""
import argparse, math, re, sys
from collections import defaultdict, Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools._figure_route_common import table,write_table,output_dir,receipt,save
from mamey.figure_theme import apply_theme
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import networkx as nx
PARK = {"saccharide", "ectoine", "terpene", "fatty_acid", "NAPAA", "terpene-precursor"}
CLASS_COL = {"NRPS": "#3a78b5", "PKS": "#d9532c", "NRPS–PKS hybrid": "#8a5bb8", "Siderophore": "#2e9e5b", "RiPP": "#e0a526", "Other": "#9a9a9a"}
PKS = {"T1PKS", "T2PKS", "T3PKS", "transAT-PKS", "transAT-PKS-like", "PKS-like", "hglE-KS", "HR-T2PKS", "arylpolyene", "enediyne"}
NRP = {"NRPS", "NRPS-like", "thioamide-NRP", "isocyanide-nrp"}
RIPP = {"lanthipeptide-class-i", "lanthipeptide-class-ii", "lanthipeptide-class-iii", "lanthipeptide-class-iv", "lanthipeptide-class-v", "lassopeptide",
        "thiopeptide", "sactipeptide", "RiPP-like", "RRE-containing", "ranthipeptide", "triceptide", "linaridin", "LAP", "bottromycin", "crocagin", "redox-cofactor",
        "cyanobactin", "epipeptide", "guanidinotides", "proteusin", "spliceotide", "methanobactin", "darobactin", "lipolanthine", "glycocin"}


def bgc_class(prods):
    p = set(prods)
    if p & {"NRP-metallophore", "NI-siderophore"}: return "Siderophore"
    pk, nr = bool(p & PKS), bool(p & NRP)
    if pk and nr: return "NRPS–PKS hybrid"
    if nr: return "NRPS"
    if pk: return "PKS"
    if p & RIPP: return "RiPP"
    return "Other"



def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--members',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cutoff',type=float,required=True);ap.add_argument('--width',type=float,default=7)
    ap.add_argument('--seed',type=int,default=3);a=ap.parse_args(argv)
    if not math.isfinite(a.cutoff) or not 0<=a.cutoff<=1 or not math.isfinite(a.width) or a.width<3.5:
        raise ValueError('invalid cutoff/width')
    members=table(a.members,['family','owner','owner_kind','products'])
    rec={};fam=defaultdict(list);isolate_ids=set();owner_kinds={}
    for i,r in enumerate(members):
        if r['owner_kind'] not in ('isolate','public','MIBiG') or not r['owner'].strip() or not r['family'].strip():
            raise ValueError('invalid membership record')
        if r['owner'] in owner_kinds and owner_kinds[r['owner']]!=r['owner_kind']:
            raise ValueError('owner has contradictory kinds')
        owner_kinds[r['owner']]=r['owner_kind']
        owner=r['owner'] if r['owner_kind']=='isolate' else ('MIBiG' if r['owner_kind']=='MIBiG' else 'public:'+r['owner'])
        if r['owner_kind']=='isolate':isolate_ids.add(owner)
        rec[i]=(owner,[p for p in re.split(r'[.;]',r['products']) if p]);fam[r['family']].append(i)
    iso=sorted(isolate_ids)
    if not iso:raise ValueError('no isolate memberships')
    out=output_dir(a.out)
    apply_theme(plt,profile='manuscript')
    plt.rcParams.update({'font.family':'Arial','font.size':8,'figure.facecolor':'white','savefig.facecolor':'white'})
    G = nx.Graph(); drawn = []; singles = Counter(); parked = 0
    for fid, rids in fam.items():
        owners = [rec[r][0] for r in rids]
        bee = sorted({o for o in owners if o in iso})
        if not bee: continue
        prods = [p for r in rids if rec[r][0] in iso for p in rec[r][1] if p]
        if prods and set(prods) <= PARK: parked += 1; continue
        pub = {o for o in owners if o.startswith("public:")}; mib = sum(o == "MIBiG" for o in owners)
        if len(pub) == 0 and mib == 0 and len(bee) == 1 and len(rids) == 1:
            singles[bee[0]] += 1; continue
        c = bgc_class(prods); node = f"F{fid}"
        G.add_node(node, kind="family", cls=c, pub=len(pub), mib=mib, bee_only=(len(pub) == 0 and mib == 0))
        for b in bee: G.add_edge(b, node)
        drawn.append(dict(family=fid, cls=c, bee_isolates=";".join(bee), public_genomes=len(pub), mibig_members=mib, isolate_regions=sum(o in iso for o in owners),
                          products=";".join(sorted(set(prods)))))
    for s in iso: G.add_node(s, kind="isolate")
    # layout: isolates spread on a ring, families placed by a spring model around them
    ring = {s: (math.cos(2 * math.pi * i / len(iso)) * 1.0, math.sin(2 * math.pi * i / len(iso)) * 1.0) for i, s in enumerate(iso)}
    pos = nx.spring_layout(G, pos=ring, fixed=iso if len(iso) > 1 else None, k=0.18, iterations=400, seed=a.seed)
    w = a.width; h = w * 0.78
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_axis_off()
    for u, v in G.edges(): ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]], color="#c9c9c9", lw=0.45, zorder=1)
    fams = [n for n in G if G.nodes[n]["kind"] == "family"]
    size = lambda n: (34 if G.nodes[n]["bee_only"] else 12) + 26 * math.sqrt(G.nodes[n]["pub"])
    for n in fams:
        d = G.nodes[n]
        if d["bee_only"]:   # no public genome and no MIBiG: hollow, in the class colour
            ax.scatter(*pos[n], s=size(n), facecolors="white", edgecolors=CLASS_COL[d["cls"]], linewidths=1.8, zorder=3)
        else:
            ax.scatter(*pos[n], s=size(n), c=CLASS_COL[d["cls"]], edgecolors="white", linewidths=0.4, zorder=3)
        if d["mib"]: ax.scatter(*pos[n], s=size(n) + 28, facecolors="none", edgecolors="black", linewidths=0.6, zorder=2)
    for s in iso:
        ax.scatter(*pos[s], s=150, marker="D", c="white", edgecolors="#b2182b", linewidths=1.6, zorder=4)
        ax.annotate(s, pos[s], xytext=(0, 9), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#b2182b", zorder=5)
        if singles[s]:
            ax.annotate(f"+{singles[s]} isolate-only", pos[s], xytext=(0, -10), textcoords="offset points", ha="center", va="top", fontsize=8, color="#444", zorder=5)
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    ax.set_xlim(min(xs) - 0.25, max(xs) + 0.25); ax.set_ylim(min(ys) - 0.25, max(ys) + 0.25)
    h1 = [Line2D([], [], ls="", marker="o", ms=6, mfc=c, mec="white", label=k) for k, c in CLASS_COL.items()]
    h2 = [Line2D([], [], ls="", marker="D", ms=6, mfc="white", mec="#b2182b", mew=1.4, label="bee isolate"),
          Line2D([], [], ls="", marker="o", ms=6.5, mfc="white", mec="#777777", mew=1.6, label="bee isolates only (no public genome)"),
          Line2D([], [], ls="", marker="o", ms=9, mfc="none", mec="black", mew=0.6, label="includes a MIBiG cluster")]
    for n_pub in (1, 10, 40):
        h2.append(Line2D([], [], ls="", marker="o", ms=math.sqrt(12 + 26 * math.sqrt(n_pub)), mfc="#bbbbbb", mec="white", label=f"{n_pub} public genome{'s' if n_pub > 1 else ''}"))
    ax.legend(handles=h1 + h2, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=5, fontsize=8, frameon=False, handletextpad=0.3, columnspacing=1.0)
    fig.tight_layout()
    save(fig,out/'family_network','family_network_page')
    plt.close(fig)
    columns=['family','cls','bee_isolates','public_genomes','mibig_members','isolate_regions','products']
    write_table(out/'DRAWN.tsv',sorted(drawn,key=lambda r:(-r['public_genomes'],r['family'])),columns)
    receipt(out,'family_network_page',[a.members,Path(__file__)],
            {'cutoff':a.cutoff,'seed':a.seed,'singletons_omitted':dict(singles),'parked_families':parked,
             'membership_scope':'explicit input rows; no database run auto-selection'})
    return 0

if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""gene_topology.py — antiSMASH-style gene-arrow topology figures from antiSMASH region GBKs.

Renders each region as a CDS-arrow track (arrow direction = strand), coloured by biosynthetic role,
with contig-edge truncation markers. Multiple GBKs can be stacked to visualise a split-pathway
reconstruction across contigs. Data-only PNG + a companion CSV of the gene table. Extraction-layer:
reads only GBK coordinates + antiSMASH gene_functions; no judgment, no identity claims.

Usage:
  python tools/gene_topology.py --gbk A.region001.gbk B.region002.gbk \
      --title "ST-EXAMPLE bottromycin split" --out fig_topology --split
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, re
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Patch
import matplotlib.patheffects as pe
try:
    from Bio import SeqIO  # type: ignore
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
    from mamey._gbk_shim import parse_genbank_text as _pgbt
    class _ShimSeqIO:
        @staticmethod
        def parse(handle, fmt):
            if hasattr(handle, 'read'):
                text = handle.read()
            else:
                with open(handle) as _fh:
                    text = _fh.read()
            return iter(_pgbt(text))
    SeqIO = _ShimSeqIO()

COLORS = {"core":"#810e15","additional":"#f4a460","regulatory":"#2e8b57",
          "transport":"#4682b4","other":"#bfbfbf"}
ROLE_LABELS = [("core","Biosynthetic core"),("additional","Biosynthetic additional"),
               ("regulatory","Regulatory"),("transport","Transport"),("other","Other")]
# domain keyword -> (role, short label)
KW = [("ycao",("core","YcaO")),("tigr03975",("core","B-protein")),("bottromycin: both",("core","botH")),
      ("rre-containing",("core","RRE")),("bottromycin_methyltransferase_rre",("core","RRE-MT")),
      ("lanthipeptide",("core","LanBC")),("indsynth",("core","IndSynth")),("nikj",("core","NikJ")),
      ("radical_sam",("additional","rSAM")),("p450",("additional","P450")),
      ("methyltransf",("additional","MT")),("beta-lactam",("additional","β-lact")),
      ("peptidase_m17",("additional","M17")),("adh_short",("additional","SDR")),
      ("biosynthetic-additional",("additional","")),("tetr",("regulatory","TetR")),
      ("regulat",("regulatory","")),("transport",("transport",""))]

def classify(gene_functions):
    txt = " ".join(gene_functions).lower()
    # most specific first: a named bottromycin gene ("bottromycin: botH") beats the generic RRE/B-protein
    if re.search(r"bottromycin:\s*both\b", txt):
        return "core","botH"
    if "ycao" in txt:           return "core","YcaO"
    if "tigr03975" in txt:      return "core","B-protein"
    if "bottromycin_methyltransferase_rre" in txt or "rre-containing" in txt:
        return "core","RRE"
    if "indsynth" in txt:       return "core","IndSynth"
    if "lanthipeptide" in txt:  return "core","LanBC"
    if "radical_sam" in txt:    return "additional","rSAM"
    if re.search(r"(?<![a-z0-9])p450(?![a-z0-9])", txt):  # v9.7.115: bounded token, not bare substring (was matching 'comp450X')
        return "additional","P450"
    if "beta-lactam" in txt:    return "additional","β-lact"
    if "peptidase_m17" in txt:  return "additional","M17"
    if "adh_short" in txt:      return "additional","SDR"
    if "methyltransf" in txt:   return "additional","MT"
    if "tetr" in txt or "regulat" in txt: return "regulatory","TetR" if "tetr" in txt else ""
    if "transport" in txt:      return "transport",""
    if "biosynthetic-additional" in txt: return "additional",""
    if "biosynthetic (rule-based" in txt: return "core",""
    return "other",""

def load_region(fp):
    rec = next(SeqIO.parse(fp, "genbank"))
    genes=[]
    for feat in rec.features:
        if feat.type!="CDS": continue
        q=feat.qualifiers; gf=q.get("gene_functions",[])
        role,lab = classify(gf)
        genes.append({"locus":q.get("locus_tag",["?"])[0],
                      "start":int(feat.location.start),"end":int(feat.location.end),
                      "strand":1 if feat.location.strand==1 else -1,"role":role,"label":lab})
    name = re.sub(r"\.region\d+\.gbk$","",os.path.basename(fp))
    m = re.search(r"(NODE_\d+|[A-Z]{2,}_?\w*\d+\.\d+|\w+)_length_(\d+)", name)
    node = m.group(1) if m else name[:24]
    clen = int(m.group(2)) if (m and m.lastindex>=2) else len(rec.seq)
    return {"node":node,"region_len":len(rec.seq),"contig_len":clen,"genes":genes}

def render(regions, title, out, split=False, subtitle="", caption=None):
    n=len(regions)
    fig,ax=plt.subplots(figsize=(13.5, 1.2+2.0*n))
    TRACK=1.0
    ys=[1.0+ (n-1-i)*1.3 for i in range(n)]
    for reg,y in zip(regions,ys):
        glen=reg["region_len"]; sc=TRACK/glen
        ax.plot([0,TRACK],[y,y],color="#d0d0d0",lw=2,zorder=1)
        ax.text(0,y+0.27,reg["node"],fontsize=12.5,fontweight="bold",color="#1A2F4A")
        ax.text(0,y+0.16,f'{reg["region_len"]:,} bp region',fontsize=9,color="#555")
        for g in reg["genes"]:
            x1=g["start"]*sc; x2=g["end"]*sc; head=min(0.012,max(x2-x1,0.004)*0.5)
            if g["strand"]>0: xs=[x1,x2-head,x2,x2-head,x1]; ys2=[y-.05,y-.05,y,y+.05,y+.05]
            else: xs=[x2,x1+head,x1,x1+head,x2]; ys2=[y-.05,y-.05,y,y+.05,y+.05]
            ax.add_patch(Polygon(list(zip(xs,ys2)),closed=True,facecolor=COLORS[g["role"]],
                                 edgecolor="#333",lw=0.6,zorder=3))
            if g["label"]:
                cx=(x1+x2)/2
                ax.text(cx,y+0.085,g["label"],fontsize=8.5,fontweight="bold",ha="center",color="#222",
                        path_effects=[pe.withStroke(linewidth=2,foreground="white")])
                ax.text(cx,y-0.105,g["locus"],fontsize=6.5,ha="center",color="#777")
        # truncation jags where a gene touches a contig end
        for g in reg["genes"]:
            if g["start"]<=5: _jag(ax,0,y)
            if g["end"]>=reg["region_len"]-5: _jag(ax,TRACK,y)
    if split and n==2:
        ax.annotate("",xy=(TRACK,ys[1]+0.06),xytext=(TRACK,ys[0]-0.06),
                    arrowprops=dict(arrowstyle="-",color="#aaa",lw=1.3,ls=(0,(4,3)),
                                    connectionstyle="arc3,rad=-0.5"))
        ax.text(TRACK+0.05,(ys[0]+ys[1])/2,"same\noperon?",fontsize=8.5,color="#999",style="italic",va="center")
    ax.set_title(title,fontsize=14,fontweight="bold",color="#1A2F4A",loc="left",pad=16)
    if subtitle: ax.text(0,max(ys)+0.62,subtitle,fontsize=9,color="#333")
    handles=[Patch(facecolor=COLORS[r],edgecolor="#333",label=l) for r,l in ROLE_LABELS]
    ax.legend(handles=handles,loc="lower left",bbox_to_anchor=(0,-0.06),ncol=5,fontsize=8.5,frameon=False)
    import textwrap
    cap = caption or ("Gene arrows are CDS coloured by biosynthetic role; arrow direction indicates strand. "
        "Jagged marks denote contig-edge truncation. Drawn directly from antiSMASH region GBK coordinates. "
        "Capacity-level and class-level only; known-cluster BLAST indicates similarity, not product identity; "
        "identifiers are pinned to NODE/locus_tag, not run-local BGC numbers.")
    wrapped="\n".join(textwrap.wrap(cap,width=150))
    ax.text(0,min(ys)-0.52,wrapped,fontsize=8,color="#222",va="top",linespacing=1.4)
    ax.set_xlim(-0.03,1.22); ax.set_ylim(min(ys)-1.15,max(ys)+0.8); ax.axis("off")
    plt.tight_layout(); plt.savefig(out+".png",dpi=150,bbox_inches="tight",facecolor="white"); plt.close()
    with open(out+"_data.csv","w",newline="") as fh:
        w=_SafeWriter(fh); w.writerow(["node","locus","start","end","strand","role","label"])
        for reg in regions:
            for g in reg["genes"]:
                w.writerow([reg["node"],g["locus"],g["start"],g["end"],
                            "+" if g["strand"]>0 else "-",g["role"],g["label"]])
    return out+".png"

def _jag(ax,x,y):
    xs=[x+(0.006 if k%2 else -0.006) for k in range(5)]; ys=[y-0.07+k*0.035 for k in range(5)]
    ax.plot(xs,ys,color="#810e15",lw=1.6,zorder=4)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--gbk",nargs="+",required=True)
    ap.add_argument("--title",default="Gene topology")
    ap.add_argument("--subtitle",default="")
    ap.add_argument("--out",default="gene_topology")
    ap.add_argument("--split",action="store_true",help="draw a 'same operon?' connector (2 regions)")
    ap.add_argument("--caption",default=None,help="figure caption text")
    a=ap.parse_args()
    regions=[load_region(f) for f in a.gbk]
    p=render(regions,a.title,a.out,split=a.split,subtitle=a.subtitle,caption=a.caption)
    emit("wrote",p,"and",a.out+"_data.csv")

if __name__=="__main__": main()

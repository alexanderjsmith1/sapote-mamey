#!/usr/bin/env python3
"""cluster_alignment.py - reference-aligned homolog figures for split-pathway BGCs.

Renders the antiSMASH "known cluster comparison" view: one or two query fragments drawn
above/below a MIBiG reference cluster, with connector lines linking each query gene to its
homologous reference gene, coloured by % identity. This is the view that lets a reader
inspect *which* reference genes each fragment covers - the discriminator for a genuine
split (fragments tile complementary reference genes) versus an artifact.

Pure extraction layer: parses antiSMASH knownclusterblast/*.txt (per-gene BLAST tables) plus
the region GBKs for query-gene roles. No identity claims beyond what BLAST reports; the split
is rendered as a hypothesis (dashed framing in the caption), not asserted as a contig join.

Usage:
  python tools/cluster_alignment.py \
      --kcb knownclusterblast/NODE_69..._c1.txt knownclusterblast/NODE_28..._c2.txt \
      --gbk NODE_69...region001.gbk NODE_28...region002.gbk \
      --ref BGC0000469 --ref-label "bottromycin A2" \
      --title "ST-EXAMPLE bottromycin - fragments vs reference" --out fig_alignment

Emits <out>.png + <out>_data.csv (query_gene, ref_gene, identity, score, coverage, fragment).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, re, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Patch
from matplotlib.lines import Line2D
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

# query-gene role/label from antiSMASH gene_functions in the region GBK
def classify(gf):
    txt=" ".join(gf).lower()
    if re.search(r"bottromycin:\s*both",txt): return "core","botH"
    if "ycao" in txt: return "core","YcaO"
    if "tigr03975" in txt: return "core","B-protein"
    if "bottromycin_methyltransferase_rre" in txt or "rre-containing" in txt: return "core","RRE-MT"
    if "indsynth" in txt or "stap" in txt: return "core","IndSynth"
    if "lanthipeptide" in txt: return "core","LanBC"
    if "radical_sam" in txt: return "additional","rSAM"
    if "p450" in txt or "p-450" in txt: return "additional","P450"
    if "beta-lactam" in txt: return "additional","b-lact"
    if "peptidase_m17" in txt: return "additional","M17"
    if "adh_short" in txt: return "additional","SDR"
    if "halogenase" in txt or "tryptophan" in txt: return "additional","Halo"
    if "methyltransf" in txt: return "additional","MT"
    if "tetr" in txt: return "regulatory","TetR"
    if "regulat" in txt: return "regulatory",""
    if "transport" in txt: return "transport",""
    if "biosynthetic-additional" in txt: return "additional",""
    if "biosynthetic (rule-based" in txt: return "core",""
    return "other",""

def gbk_roles(fp):
    rec=next(SeqIO.parse(fp,"genbank"))
    roles={}
    for feat in rec.features:
        if feat.type!="CDS": continue
        loc=feat.qualifiers.get("locus_tag",["?"])[0]
        roles[loc]=classify(feat.qualifiers.get("gene_functions",[]))
    return roles

def parse_blocks(fp):
    """Parse an antiSMASH clusterblast/knownclusterblast txt into:
       (ordered query loci, {ref_acc: {name, type, hits:[{q,s,id,score,cov,eval}]}}).
       Captures EVERY reference block, not just the top hit."""
    qgenes=[]; refs={}
    if not fp or not os.path.exists(fp): return qgenes, refs
    txt=open(fp).read()
    qm=re.search(r"query cluster:\n(.*?)\n\n",txt,re.S)
    if qm:
        for line in qm.group(1).strip().split("\n"):
            p=line.split("\t")
            if len(p)>=4: qgenes.append(p[0])
    name={}
    sh=re.search(r"Significant hits:\s*\n(.*?)\n\n",txt,re.S)
    if sh:
        for line in sh.group(1).strip().split("\n"):
            m=re.match(r"\d+\.\s+(\S+)\t(.+)",line)
            if m: name[m.group(1)]=m.group(2)
    for b in re.split(r"\n>>\n",txt):
        head=re.match(r"\s*\d+\.\s+(\S+)",b)
        if not head: continue
        acc=head.group(1); typ=""
        tm=re.search(r"Type:\s*(.+)",b)
        if tm: typ=tm.group(1).strip()
        hits=[]
        hm=re.search(r"e-value\):\n(.*?)(?:\n\n|\Z)",b,re.S)
        if hm:
            for line in hm.group(1).strip().split("\n"):
                p=line.split("\t")
                if len(p)>=5 and not p[0].startswith(">"):
                    try: hits.append({"q":p[0],"s":p[1],"id":int(p[2]),"score":int(p[3]),
                                      "cov":float(p[4]),"eval":p[5] if len(p)>5 else ""})
                    except (ValueError, IndexError): pass
        if hits: refs[acc]={"name":name.get(acc,""),"type":typ,"hits":hits}
    return qgenes, refs

def collect_hits(kcb_fp, cb_fp, ref, class_override=None):
    """CONTIG-RESCUE aggregation: parse BOTH knownclusterblast and clusterblast, ALL references.
       Returns (ordered query loci, best-per-gene hits to the named MIBiG `ref`,
                support summary dict). The figure draws against `ref`, but support counts
                every reference (MIBiG + genome neighbour) whose class matches, so the
                rescue is not hostage to a single top-ranked hit.
       class_override: when the reference's own Type/name doesn't carry the chemical class
                (e.g. AT2433 is typed 'other:other'), the caller supplies the class token
                (e.g. 'indolocarbazole') plus any corroborating compound names to count."""
    qgenes, kref = parse_blocks(kcb_fp)
    _,      cref = parse_blocks(cb_fp)
    # primary alignment: best per-gene hit to the chosen MIBiG reference (prefix match)
    best={}
    for acc,d in kref.items():
        if acc.startswith(ref):
            for h in d["hits"]:
                if h["q"] not in best or h["score"]>best[h["q"]]["score"]: best[h["q"]]=h
    # support: how many references (across BOTH methods) corroborate the class for each gene
    # class token taken from the chosen ref's type, else from the MIBiG ref name
    ref_type=""
    for acc,d in kref.items():
        if acc.startswith(ref): ref_type=(d["type"] or d["name"]); break
    cls_token=""
    # families whose member compound-names should also corroborate the class
    FAMILY_NAMES={"indolocarbazole":("at2433","staurosporine","rebeccamycin","loonamycin",
                                     "violacein","arcyriaflavin","k252","staur"),
                  "enediyne":("calicheamicin","maduropeptin","dynemicin","esperamicin"),
                  "glycopeptide":("vancomycin","balhimycin","teicoplanin","enduracidin")}
    SPECIFIC=("bottromycin","indolocarbazole","lanthipeptide","enediyne","glycopeptide",
              "lassopeptide","thiopeptide","lipopeptide","spirotetronate","ranthipeptide",
              "nucleoside","phosphonate","staurosporine","rebeccamycin")
    GENERIC=("ripp","nrps","t1pks","pks")
    low=ref_type.lower()
    if class_override:                 # caller-supplied class (refs don't carry it)
        cls_token=class_override.lower()
    if not cls_token:
        for tok in SPECIFIC:           # specific class names win
            if tok in low: cls_token=tok; break
    if not cls_token:                  # fall back to the MIBiG ref NAME
        for acc,d in kref.items():
            if acc.startswith(ref):
                nm=d["name"].lower()
                for tok in SPECIFIC:
                    if tok in nm: cls_token=tok; break
            if cls_token: break
    if not cls_token:
        for tok in GENERIC:
            if tok in low: cls_token=tok; break
    # corroboration match set = the class token + any family compound names
    match_terms={cls_token} if cls_token else set()
    match_terms|=set(FAMILY_NAMES.get(cls_token,()))
    support={"kcb_refs":len(kref),"cb_refs":len(cref),"class_token":cls_token,
             "kcb_class_refs":0,"cb_class_refs":0,"per_gene_support":{}}
    allrefs=[("kcb",kref),("cb",cref)]
    for method,refd in allrefs:
        for acc,d in refd.items():
            blob=(d["name"]+" "+d["type"]).lower()
            if match_terms and any(t in blob for t in match_terms):
                support[f"{method}_class_refs"]+=1
                for h in d["hits"]:
                    support["per_gene_support"].setdefault(h["q"],set()).add(acc)
    # freeze per-gene support to counts
    support["per_gene_support"]={k:len(v) for k,v in support["per_gene_support"].items()}
    return qgenes, best, support

def id_color(idn):
    return "#2e8b57" if idn>=70 else ("#9aa84a" if idn>=50 else "#cc8844")

GENE_H=0.05
def draw_gene(ax,x,y,w,role,lab,below=False):
    ax.add_patch(Polygon([(x-w/2,y-GENE_H),(x+w/2-0.008,y-GENE_H),(x+w/2,y),
                          (x+w/2-0.008,y+GENE_H),(x-w/2,y+GENE_H)],
                 closed=True,facecolor=COLORS.get(role,"#bfbfbf"),edgecolor="#333",lw=0.5,zorder=3))
    if lab:
        yy=y-0.092 if below else y+0.075
        ax.text(x,yy,lab,fontsize=7.5,ha="center",fontweight="bold",
                path_effects=[pe.withStroke(linewidth=2,foreground="white")])

def _wrap_label(text, width=42):
    """Wrap a long track title to at most 2 lines so a right-aligned margin label
    doesn't extend too far left. Keeps short labels on one line. (PATCH-006)"""
    import textwrap
    if len(text) <= width:
        return text
    lines = textwrap.wrap(text, width=width, max_lines=2, placeholder=" …")
    return "\n".join(lines)


def render(frags, ref_subjects, ref_role, ref_id, ref_label, title, subtitle, out, caption=None):
    """frags = list of dicts: {name, sub, genes(ordered loci), roles{loci:(role,lab)}, hits{loci:hit}, side}"""
    fig,ax=plt.subplots(figsize=(14,7.0))
    y_ref=1.6
    y_top=2.9; y_bot=0.3
    TRACK=1.0
    # reference track
    rpos={}
    rn=len(ref_subjects); rgw=TRACK/max(rn,1)*0.82
    for i,s in enumerate(ref_subjects): rpos[s]=(i+0.5)/rn*TRACK
    ax.plot([0,TRACK],[y_ref,y_ref],color="#d0d0d0",lw=1.5,zorder=1)
    _lbl_ref = _wrap_label(f"{ref_id} - {ref_label} (MIBiG reference)")
    ax.text(-0.02,y_ref+0.16,_lbl_ref,fontsize=10,fontweight="bold",color="#1A2F4A",ha="right",va="center")
    ax.text(-0.02,y_ref-0.12,f"{rn} genes - reference operon",fontsize=7.5,color="#555",ha="right",va="center")
    for s in ref_subjects:
        role,lab=ref_role.get(s,("other",""))
        draw_gene(ax,rpos[s],y_ref,rgw,role,lab)
    # fragment tracks
    for frag in frags:
        y=y_top if frag["side"]=="top" else y_bot
        below=(frag["side"]=="bottom")
        # SYNTENY-AWARE ORDERING: place each query gene near its reference homolog's x position
        # (barycenter heuristic) so connector lines run mostly vertical and complementary tiling
        # is visually obvious. Genes with no ref hit keep their genomic-order position as a tiebreak.
        genomic=frag["genes"]
        gidx={loc:i for i,loc in enumerate(genomic)}
        def sort_key(loc):
            h=frag["hits"].get(loc)
            if h and h["s"] in rpos:
                return (rpos[h["s"]], gidx.get(loc,0))   # primary: ref homolog x; tiebreak: genomic order
            return (gidx.get(loc,0)/max(len(genomic),1), gidx.get(loc,0))  # unhit genes: keep genomic spread
        ordered = sorted(genomic, key=sort_key) if frag.get("synteny",True) else genomic
        gn=len(ordered); gw=TRACK/max(gn,1)*0.82
        fpos={loc:(i+0.5)/gn*TRACK for i,loc in enumerate(ordered)}
        ax.plot([0,TRACK],[y,y],color="#d0d0d0",lw=1.5,zorder=1)
        _lbl_frag = _wrap_label(frag["name"])
        ax.text(-0.02,y+0.16,_lbl_frag,fontsize=10,fontweight="bold",color="#1A2F4A",ha="right",va="center")
        ax.text(-0.02,y-0.12,frag["sub"],fontsize=7.5,color="#555",ha="right",va="center")
        for loc in ordered:
            role,lab=frag["roles"].get(loc,("other",""))
            draw_gene(ax,fpos[loc],y,gw,role,lab,below=below)
        # connectors
        for loc,h in frag["hits"].items():
            if loc in fpos and h["s"] in rpos:
                y0=y-GENE_H if frag["side"]=="top" else y+GENE_H
                y1=y_ref+GENE_H if frag["side"]=="top" else y_ref-GENE_H
                ax.plot([fpos[loc],rpos[h["s"]]],[y0,y1],color=id_color(h["id"]),
                        lw=1.0+h["id"]/60,alpha=0.55,zorder=2)
    ax.set_title(title,fontsize=14,fontweight="bold",color="#1A2F4A",loc="left",pad=14)
    if subtitle: ax.text(0,3.45,subtitle,fontsize=9,color="#333")
    role_h=[Patch(facecolor=COLORS[r],edgecolor="#333",label=l) for r,l in
            [("core","Biosynthetic core"),("additional","Additional/tailoring"),
             ("regulatory","Regulatory"),("other","Other")]]
    id_h=[Line2D([0],[0],color="#2e8b57",lw=2,label="\u226570% identity"),
          Line2D([0],[0],color="#9aa84a",lw=2,label="50-69%"),
          Line2D([0],[0],color="#cc8844",lw=2,label="<50%")]
    leg1=ax.legend(handles=role_h,loc="lower left",bbox_to_anchor=(0,-0.10),ncol=4,fontsize=8,frameon=False)
    ax.add_artist(leg1)
    ax.legend(handles=id_h,loc="lower right",bbox_to_anchor=(1,-0.10),ncol=3,fontsize=8,frameon=False,title="homolog identity")
    # Figure caption (readable dark text, wrapped). Caller-supplied via `caption`, else a sensible default.
    import textwrap
    cap = caption or (
        f"Figure. Reference-aligned homolog view for the {ref_label} reconstruction. "
        f"Query fragment(s) are drawn above and below the MIBiG reference cluster {ref_id}; each connector links "
        f"a fragment gene to its homologous reference gene (antiSMASH knownclusterblast + clusterblast), coloured "
        f"by % amino-acid identity. Genes are synteny-ordered so that complementary tiling of the reference operon "
        f"by the two fragments \u2014 the signature of one pathway split across contigs \u2014 reads left-to-right. "
        f"Claims are capacity-level and class-level; a split is a reconstruction hypothesis, not a contig join, and "
        f"KCB indicates similarity, not product identity.")
    wrapped="\n".join(textwrap.wrap(cap, width=165))
    ax.text(-0.60,-0.42,wrapped,fontsize=8,color="#222",va="top",ha="left",linespacing=1.4)
    ax.set_xlim(-0.62,1.05); ax.set_ylim(-0.95,3.65); ax.axis("off")
    # PATCH-006: track labels moved into the left margin (right-aligned, ending at x=-0.02)
    # so connector lines — which originate at the first gene center (x>=0.06) and fan
    # rightward — no longer cross the track titles; long titles wrap to <=2 lines via
    # _wrap_label so right-aligned text doesn't run off the left edge. tight_layout()/
    # bbox_inches="tight" re-derive the axes extent from content each call, which with
    # variable-length labels shrinks the axes and squeezes the two fixed-size bottom
    # legends until they overlap. Fixed margins keep axes width — and legend spacing —
    # stable regardless of label text length.
    fig.subplots_adjust(left=0.30, right=0.97, top=0.90, bottom=0.16)
    plt.savefig(out+".png",dpi=150,facecolor="white"); plt.close()
    # CSV
    with atomic_open(out+"_data.csv", newline="") as fh:
        w=_SafeWriter(fh); w.writerow(["fragment","query_gene","ref_gene","identity_pct","blast_score","coverage_pct"])
        for frag in frags:
            for loc,h in frag["hits"].items():
                w.writerow([frag["name"],loc,h["s"],h["id"],h["score"],f'{h["cov"]:.0f}'])
    return out+".png"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--kcb",nargs="+",required=True,help="knownclusterblast txt per fragment")
    ap.add_argument("--cb",nargs="*",default=None,help="clusterblast txt per fragment (genome neighbours); optional but recommended for contig rescue")
    ap.add_argument("--gbk",nargs="+",required=True,help="region GBK per fragment (same order as --kcb)")
    ap.add_argument("--ref",required=True,help="reference accession prefix, e.g. BGC0000469")
    ap.add_argument("--ref-label",default="reference")
    ap.add_argument("--class-token",default=None,help="explicit chemical class when refs don't carry it (e.g. indolocarbazole, since AT2433 is typed 'other:other')")
    ap.add_argument("--frag-names",nargs="+",help="display names per fragment")
    ap.add_argument("--frag-subs",nargs="+",help="subtitle per fragment")
    ap.add_argument("--title",default="Fragments vs reference cluster")
    ap.add_argument("--subtitle",default="")
    ap.add_argument("--no-synteny",action="store_true",help="disable synteny-aware gene ordering (use raw genomic order)")
    ap.add_argument("--caption",default=None,help="figure caption text (printed below the legend)")
    ap.add_argument("--out",default="cluster_alignment")
    a=ap.parse_args()
    assert len(a.kcb)==len(a.gbk), "need one --gbk per --kcb"
    cb_list = a.cb if a.cb else [None]*len(a.kcb)
    if a.cb: assert len(a.cb)==len(a.kcb), "need one --cb per --kcb (or omit --cb entirely)"
    frags=[]; ref_subjects=[]; support_all={}
    for i,(kcb,gbk) in enumerate(zip(a.kcb,a.gbk)):
        genes,best,support=collect_hits(kcb, cb_list[i], a.ref, class_override=a.class_token)
        roles=gbk_roles(gbk)
        ordered=[g for g in genes if g in roles] or genes
        name=(a.frag_names[i] if a.frag_names else f"Fragment {i+1}")
        # default subtitle now reports the multi-source support, not a genus
        defsub=(f"{len(best)} genes -> {a.ref} · class corroborated by "
                f"{support['kcb_class_refs']} MIBiG + {support['cb_class_refs']} genome refs")
        frags.append({"name":name,"sub":(a.frag_subs[i] if a.frag_subs else defsub),
                      "genes":ordered,"roles":roles,"hits":best,
                      "side":"top" if i==0 else "bottom","synteny":(not a.no_synteny)})
        support_all[name]=support
        for h in best.values(): ref_subjects.append(h["s"])
    def acc_num(s):
        m=re.search(r"(\d+)(?:\.\d+)?$",s); return int(m.group(1)) if m else 99999
    ref_subjects=sorted(set(ref_subjects),key=acc_num)
    ref_role={s:("other","") for s in ref_subjects}
    p=render(frags,ref_subjects,ref_role,a.ref,a.ref_label,a.title,a.subtitle,a.out,caption=a.caption)
    # write support summary alongside the per-gene CSV
    with atomic_open(a.out+"_support.csv", newline="") as fh:
        w=_SafeWriter(fh)
        w.writerow(["fragment","class_token","kcb_refs_total","cb_refs_total","kcb_class_refs","cb_class_refs"])
        for nm,s in support_all.items():
            w.writerow([nm,s["class_token"],s["kcb_refs"],s["cb_refs"],s["kcb_class_refs"],s["cb_class_refs"]])
    emit("wrote",p,",",a.out+"_data.csv,",a.out+"_support.csv")

if __name__=="__main__": main()

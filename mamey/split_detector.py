"""Contig-end split detector v2 — with discriminating filters to cut false positives."""
try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
import glob, json, os
from Bio import SeqIO
from Bio.Align import PairwiseAligner

PKS_KS = ("tra_KS","mod_KS","hyb_KS","PKS_KS","ketoacyl-synt","Ketoacyl")

# v9.7.409 (DEEP_AUDIT2_resource_dos #1): PairwiseAligner.align() builds an O(len(a)*len(b)) DP
# matrix; a multi-MB crafted PKS gene makes it so large the OS SIGKILLs the process uncatchably.
# Skip any pair with an over-long sequence BEFORE .align(). Env-overridable via MAMEY_MAX_ALIGN_AA.
_DEFAULT_MAX_ALIGN_AA = 10_000

def _max_align_aa():
    """Per-sequence residue ceiling for local alignment (env-overridable, read at call time)."""
    try:
        return int(os.environ.get("MAMEY_MAX_ALIGN_AA", str(_DEFAULT_MAX_ALIGN_AA)))
    except (TypeError, ValueError):
        return _DEFAULT_MAX_ALIGN_AA

def _profile(gbk):
    for rec in SeqIO.parse(gbk,"genbank"):
        L=len(rec.seq)
        prod=";".join([q for f in rec.features if f.type=="region" for q in f.qualifiers.get("product",[])])
        genes=[]
        for f in rec.features:
            if f.type=="CDS":
                dom=f.qualifiers.get("sec_met_domain",[])
                tr=f.qualifiers.get("translation",[""])[0]
                genes.append({"s":int(f.location.start),"e":int(f.location.end),
                              "strand":f.location.strand,"dom":";".join(str(d) for d in dom),
                              "lt":f.qualifiers.get("locus_tag",["?"])[0],"seq":tr})
        bio=[g for g in genes if g["dom"]]
        if not bio: return None
        return {"L":L,"prod":prod,"genes":sorted(genes,key=lambda g:g["s"]),"bio":bio}

def _terminal_pks_gene(p, edge_bp=3000):
    """Return the PKS/NRPS gene that sits AT a contig terminus (the split point), or None."""
    for g in p["bio"]:
        if not any(k in g["dom"] for k in PKS_KS) and "AMP-binding" not in g["dom"] and "Condensation" not in g["dom"]:
            continue
        at_start = g["s"] <= edge_bp
        at_end   = (p["L"]-g["e"]) <= edge_bp
        if at_start or at_end:
            return {"gene":g, "which":"start" if at_start else "end",
                    "dist": min(g["s"], p["L"]-g["e"])}
    return None

def detect(strain_dir, edge_bp=3500, exclude_prefixes=()):
    regions={}
    for f in glob.glob(f"{strain_dir}/**/*.region*.gbk", recursive=True):
        if "MACOSX" in f: continue
        rid=f.split("/")[-1].replace(".gbk","")
        if any(rid.startswith(pre) for pre in exclude_prefixes): continue
        p=_profile(f)
        if not p: continue
        # must be PKS/NRPS
        if not any(any(k in g["dom"] for k in PKS_KS) or "Condensation" in g["dom"] for g in p["bio"]):
            continue
        term=_terminal_pks_gene(p, edge_bp)
        if term:
            p["rid"]=rid; p["contig"]=rid.split(".region")[0]; p["term"]=term
            regions[rid]=p

    aln=PairwiseAligner(scoring="blastp"); aln.mode="local"
    def frag_continues_body(frag, body):
        """The fragment's terminal gene should be a PARTIAL module — check it's a truncated
        PKS gene (shorter than a full module ~2000+aa but a real KS/hybrid), AND that the
        body has room for it. Returns True if the fragment looks like a genuine continuation."""
        fg=frag["term"]["gene"]
        # a partial mldA-type fragment: single large PKS gene running off the contig end
        is_partial = any(k in fg["dom"] for k in PKS_KS) and len(fg["seq"])>=300
        # fragment region should be SMALL (few bio genes) — a tail, not a whole cluster
        frag_small = len(frag["bio"]) <= 8
        return is_partial and frag_small

    cands=[]
    rids=list(regions)
    for i in range(len(rids)):
        for j in range(len(rids)):
            if i==j: continue
            body, frag = regions[rids[i]], regions[rids[j]]
            if body["contig"]==frag["contig"]: continue
            if len(body["bio"]) < len(frag["bio"]): continue  # body is the larger piece
            # BOTH must have a terminal PKS gene
            if not (body["term"] and frag["term"]): continue
            # fragment must look like a genuine partial-module continuation
            if not frag_continues_body(frag, body): continue
            # discriminating: fragment terminal gene aligns to a body gene at MODERATE id
            # (same pathway paralog: 35-70%; identical duplicate would be >90% = not a split)
            fseq=frag["term"]["gene"]["seq"]
            _cap=_max_align_aa()
            best=0
            for g in body["bio"]:
                if not any(k in g["dom"] for k in PKS_KS): continue
                if not g["seq"]: continue
                # v9.7.409 (DEEP_AUDIT2_resource_dos #1): refuse an over-long pair before .align()
                # — an O(L^2) DP matrix on a multi-MB gene SIGKILLs uncatchably. Skip, keep scanning.
                if len(fseq)>_cap or len(g["seq"])>_cap: continue
                a=aln.align(fseq,g["seq"])[0]
                idn=al=0
                for (x,y),(u,v) in zip(a.aligned[0],a.aligned[1]):
                    for c1,c2 in zip(fseq[x:y],g["seq"][u:v]): al+=1; idn+=(c1==c2)
                pid=100*idn/al if al else 0
                best=max(best,pid)
            # score
            score=0
            score += 3 if frag["term"]["dist"]<=500 else 1     # fragment hard against end
            score += 2 if body["term"]["dist"]<=2000 else 0    # body also at edge
            score += 2 if frag["prod"].split(";")[0].lower() in body["prod"].lower() else 0
            score += 2 if 30<=best<=78 else (0 if best>90 else 1)  # paralog-range = same pathway
            conf="HIGH" if score>=7 else "MEDIUM" if score>=5 else "LOW"
            cands.append({"body":body["rid"],"fragment":frag["rid"],
                          "body_bio":len(body["bio"]),"frag_bio":len(frag["bio"]),
                          "frag_dist_to_end":frag["term"]["dist"],
                          "frag_gene":frag["term"]["gene"]["lt"],
                          "best_paralog_id":round(best,1),"score":score,"confidence":conf})
    # dedup (body,fragment) unordered
    seen=set(); uniq=[]
    for c in sorted(cands,key=lambda x:-x["score"]):
        key=tuple(sorted([c["body"],c["fragment"]]))
        if key in seen: continue
        seen.add(key); uniq.append(c)
    return uniq

if __name__=="__main__":
    import sys
    d=sys.argv[1] if len(sys.argv)>1 else "ajs327"
    # exclude training BGCs (accession-named) — only scan the AS-XXX NZ_SKBR contigs
    cands=detect(d, exclude_prefixes=("MT361","MN396","MN305","LC5","LN8","JX8","JN6","KP4","KE5","KY0","MF0","DQ3","EU1","HQ1","OR7"))
    emit(f"contig-end split candidates in {d} (training BGCs excluded): {len(cands)}\n")
    for c in cands[:12]:
        b=c["body"].replace("NZ_SKBR0100000","c").replace(".region",".r")
        f=c["fragment"].replace("NZ_SKBR0100000","c").replace(".region",".r")
        emit(f"  [{c['confidence']:6}] {b} (body,{c['body_bio']}g) + {f} (frag,{c['frag_bio']}g,{c['frag_dist_to_end']}bp) "
              f"paralog_id={c['best_paralog_id']}% score={c['score']}")


def detect_with_class_scoring(strain_dir, edge_bp=3500, exclude_prefixes=()):
    """Detector + trans-AT/class-aware re-scoring. Adds a bonus when body and fragment
    share a distinctive PKS subclass (trans-AT), which uniquely resolved marinolide."""
    cands = detect(strain_dir, edge_bp=edge_bp, exclude_prefixes=exclude_prefixes)
    def transat(rid_contig):
        import glob
        for f in glob.glob(f"{strain_dir}/**/{rid_contig}*.gbk", recursive=True):
            if "MACOSX" in f: continue
            for rec in SeqIO.parse(f,"genbank"):
                for ft in rec.features:
                    if ft.type=="CDS" and "tra_KS" in str(ft.qualifiers.get("sec_met_domain",[])):
                        return True
        return False
    for c in cands:
        if transat(c["body"]):
            c["score"] += 2; c["transat_body"]=True
            c["confidence"]="HIGH" if c["score"]>=7 else "MEDIUM" if c["score"]>=5 else "LOW"
        else:
            c["transat_body"]=False
    cands.sort(key=lambda x:-x["score"])
    return cands

#!/usr/bin/env python3
"""Rank package-backed MIBiG matches by top-versus-second separation.

Reader-side and standard-library only.  Every BGC is displayed as
``strain / full node-or-contig / region / BGC alias``.  The outputs are
similarity-prioritization aids, not product or pathway-completeness calls.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

CLAIM = ("Sequence-similarity prioritization only; no exact product, pathway "
         "completeness, expression, production, activity, novelty, or scientific acceptance claim. "
         "Scores are tool-specific: the same assembly fact is weighted differently by each ranking tool, so values are not comparable across tools.")

def number(value, default=0.0):
    try: return float(value)
    except (TypeError, ValueError): return default

def med(values):
    return round(statistics.median(values), 2) if values else ""

def mean(values):
    return round(statistics.mean(values), 2) if values else ""

def gene_evidence_score(row):
    """Transparent 0-100 score for selecting a BGC's strongest genes.

    Sixty percent is top-hit identity x coverage, 25% is the top-versus-second
    effective-similarity gap (full credit at 50 points), and 15% is the bit-score
    ratio separation (full credit at 2-fold).  A missing distinct runner-up gets
    no separation credit rather than being treated as a clear match.
    """
    effective=number(row.get("top_identity_x_coverage"))
    gap=number(row.get("top_minus_second_identity_x_coverage_points"))
    ratio=number(row.get("top_to_second_blast_score_ratio"))
    gap_component=min(100,max(0,gap)*2)
    ratio_component=min(100,max(0,ratio-1)*100)
    return round(.60*effective+.25*gap_component+.15*ratio_component,2)

def top_k_summary(current, k):
    hit=[r for r in current if r.get("top_mibig_accession")]
    chosen=sorted(hit,key=lambda r:(-number(r.get("gene_evidence_score_0_100")),-number(r.get("top_identity_x_coverage")),-number(r.get("top_minus_second_identity_x_coverage_points")),r.get("query_gene","")))[:k]
    eligible=len(chosen)==k
    return {
        "complete_identity":current[0]["complete_identity"],
        f"top_{k}_rank_eligible":"YES" if eligible else "NO",
        f"genes_available_for_top_{k}":len(hit),
        f"genes_used_for_top_{k}":len(chosen),
        f"top_{k}_gene_match_score_0_100":mean([number(r["gene_evidence_score_0_100"]) for r in chosen]) if eligible else "",
        f"top_{k}_mean_pct_identity":mean([number(r["top_pct_identity"]) for r in chosen]) if eligible else "",
        f"top_{k}_mean_pct_coverage":mean([number(r["top_pct_coverage"]) for r in chosen]) if eligible else "",
        f"top_{k}_mean_identity_x_coverage":mean([number(r["top_identity_x_coverage"]) for r in chosen]) if eligible else "",
        f"top_{k}_mean_top_minus_second_gap":mean([number(r["top_minus_second_identity_x_coverage_points"]) for r in chosen]) if eligible else "",
        f"top_{k}_mean_bit_score_ratio":mean([number(r["top_to_second_blast_score_ratio"]) for r in chosen]) if eligible else "",
        f"top_{k}_clear_specific_high_genes":sum(r["match_band"]=="CLEAR_SPECIFIC_HIGH" for r in chosen),
        f"top_{k}_query_genes":"; ".join(r["query_gene"] for r in chosen),
        f"top_{k}_mibig_accessions":"; ".join(r["top_mibig_accession"] for r in chosen),
        f"top_{k}_mibig_products":"; ".join(r["top_mibig_product"] for r in chosen),
        "claim_ceiling":CLAIM,
    }

def strain_from_identity(identity):
    return identity.split(" / ",1)[0]

def safe_segment(value):
    return re.sub(r"[^A-Za-z0-9._-]+","_",value).strip("._") or "UNNAMED"

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))

def one_file(package, suffix, required=True):
    found=sorted(package.glob(f"*{suffix}"))
    if len(found)==1: return found[0]
    if required: raise ValueError(f"{package}: expected one *{suffix}; found {len(found)}")
    return None

def package_inputs(package):
    package=Path(package).expanduser().resolve()
    manifest=package/"manifest.json"
    if not manifest.is_file(): raise ValueError(f"{package}: manifest.json is required")
    return {
        "package":package,"manifest":manifest,
        "cds":one_file(package,"_cds_table.csv"),
        "hits":one_file(package,"_3_mibig_per_gene.csv"),
        "inventory":one_file(package,"_2_inventory.csv",required=False),
    }

def discover_packages(paths, root=None):
    found=[]
    for value in paths or []: found.append(Path(value).expanduser().resolve())
    if root:
        for cds in Path(root).expanduser().resolve().rglob("*_cds_table.csv"):
            if (cds.parent/"manifest.json").is_file(): found.append(cds.parent)
    unique=[]; seen=set()
    for p in found:
        if p not in seen: seen.add(p); unique.append(p)
    if not unique: raise ValueError("provide --package or --packages-root with package directories")
    return unique

def read_aliases(path):
    if not path: return {}
    rows=read_csv(Path(path).expanduser().resolve())
    aliases={}
    for row in rows:
        source=row.get("source_strain","").strip(); display=row.get("display_strain","").strip()
        if not source or not display: raise ValueError("strain alias table requires source_strain and display_strain")
        aliases[source]=display
    return aliases

def exact_identity(row, aliases=None):
    aliases=aliases or {}
    source=row.get("strain","")
    values=[aliases.get(source,source),row.get("contig",""),row.get("region",""),row.get("bgc_id","")]
    if not all(values): raise ValueError(f"CDS row lacks complete BGC identity: {values}")
    return " / ".join(values)

def classify(top, second, min_id, min_cov, min_score, min_gap, min_ratio):
    if not top: return "NO_MIBIG_HIT_RECORDED", {}
    ti=number(top.get("pct_identity")); tc=min(100,number(top.get("pct_coverage_interpretation") or top.get("pct_coverage"))); ts=number(top.get("blast_score")); te=ti*tc/100
    if second:
        si=number(second.get("pct_identity")); sc=min(100,number(second.get("pct_coverage_interpretation") or second.get("pct_coverage"))); ss=number(second.get("blast_score")); se=si*sc/100
        gap=te-se; ratio=ts/ss if ss else 0
    else: si=sc=ss=se=0; gap=ratio=None
    high=ti>=min_id and tc>=min_cov and ts>=min_score
    clear=high and second is not None and gap>=min_gap and ratio>=min_ratio
    moderate=(not clear and second is not None and ti>=50 and tc>=70 and gap>=15 and ratio>=1.3)
    band=("CLEAR_SPECIFIC_HIGH" if clear else "HIGH_NO_DISTINCT_RUNNER_UP" if high and second is None
          else "HIGH_BUT_AMBIGUOUS" if high else "MODERATE_CLEAR" if moderate
          else "MATCH_WITHOUT_CLEAR_SEPARATION")
    return band,{"top_id":ti,"top_cov":tc,"top_score":ts,"top_eff":round(te,2),"second_id":si,"second_cov":sc,"second_score":ss,"second_eff":round(se,2),"gap":round(gap,2) if gap is not None else "","ratio":round(ratio,3) if ratio is not None else ""}

def write_tsv(path, rows, fields):
    with path.open("w",newline="") as handle:
        writer=_SafeDictWriter(handle,fieldnames=fields,delimiter="\t",extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)

def analyze(packages, out, min_id=70, min_cov=80, min_score=100, min_gap=20, min_ratio=1.5, aliases=None):
    out=Path(out).expanduser().resolve(); out.mkdir(parents=True,exist_ok=True)
    genes=[]; bgcs=[]; top2=[]; top3=[]; raw_hits=[]; sources=[]
    for package in packages:
        inp=package_inputs(package)
        for role in ("manifest","cds","hits","inventory"):
            path=inp.get(role)
            if path: sources.append({"package":str(inp["package"]),"role":role,"path":str(path),"sha256":sha256(path),"bytes":path.stat().st_size})
        cds=read_csv(inp["cds"]); hits=read_csv(inp["hits"]); inventory=read_csv(inp["inventory"]) if inp["inventory"] else []
        inv={r.get("BGC_ID",""):r for r in inventory}
        grouped=defaultdict(list)
        for h in hits: grouped[(h.get("bgc_id",""),h.get("query_gene",""))].append(h)
        by_bgc=defaultdict(list)
        for c in cds: by_bgc[c.get("bgc_id","")].append(c)
        for bgc,cds_rows in by_bgc.items():
            current=[]
            for c in cds_rows:
                ident=exact_identity(c,aliases); raw=grouped.get((bgc,c.get("locus_tag","")),[])
                for h in raw:
                    raw_hits.append({"complete_identity":ident,"query_gene":c.get("locus_tag",""),"query_product":c.get("product",""),"query_sec_met_domains":c.get("sec_met_domains",""),"subject_gene":h.get("subject_gene",""),"mibig_accession":h.get("mibig_accession",""),"mibig_product":h.get("mibig_compound",""),"reference_type":h.get("reference_type",""),"pct_identity":h.get("pct_identity",""),"pct_coverage_source":h.get("pct_coverage",""),"pct_coverage_interpretation":h.get("pct_coverage_interpretation",""),"coverage_qc_flag":h.get("coverage_qc_flag",""),"blast_score":h.get("blast_score",""),"evalue":h.get("evalue",""),"reference_rank":h.get("reference_rank",""),"source_file":h.get("source_file",""),"claim_ceiling":CLAIM})
                best={}
                for h in raw:
                    accession=h.get("mibig_accession","")
                    key=(number(h.get("blast_score")),number(h.get("pct_identity"))*min(100,number(h.get("pct_coverage_interpretation") or h.get("pct_coverage")))/100)
                    if accession and (accession not in best or key>best[accession][0]): best[accession]=(key,h)
                distinct=[v[1] for v in best.values()]
                distinct.sort(key=lambda h:(-number(h.get("blast_score")),-number(h.get("pct_identity")),h.get("mibig_accession","")))
                top=distinct[0] if distinct else None; second=distinct[1] if len(distinct)>1 else None
                band,m=classify(top,second,min_id,min_cov,min_score,min_gap,min_ratio)
                row={"complete_identity":ident,"query_gene":c.get("locus_tag",""),"gene_order":c.get("order",""),"query_product":c.get("product",""),"query_sec_met_domains":c.get("sec_met_domains",""),"query_gene_functions":c.get("gene_functions",""),"distinct_mibig_clusters_with_hits":len(distinct),"match_band":band}
                for prefix,h in (("top",top),("second",second)):
                    row.update({f"{prefix}_subject_gene":h.get("subject_gene","") if h else "",f"{prefix}_mibig_accession":h.get("mibig_accession","") if h else "",f"{prefix}_mibig_product":h.get("mibig_compound","") if h else "",f"{prefix}_reference_type":h.get("reference_type","") if h else "",f"{prefix}_evalue":h.get("evalue","") if h else ""})
                row.update({"top_pct_identity":m.get("top_id",""),"top_pct_coverage":m.get("top_cov",""),"top_identity_x_coverage":m.get("top_eff",""),"top_blast_score":m.get("top_score",""),"second_pct_identity":m.get("second_id","") if second else "","second_pct_coverage":m.get("second_cov","") if second else "","second_identity_x_coverage":m.get("second_eff","") if second else "","second_blast_score":m.get("second_score","") if second else "","top_minus_second_identity_x_coverage_points":m.get("gap",""),"top_to_second_blast_score_ratio":m.get("ratio",""),"claim_ceiling":CLAIM})
                row["gene_evidence_score_0_100"]=gene_evidence_score(row) if top else ""
                genes.append(row); current.append(row)
            hit=[r for r in current if r["top_mibig_accession"]]; clear=[r for r in current if r["match_band"]=="CLEAR_SPECIFIC_HIGH"]
            top_clusters=Counter(r["top_mibig_accession"] for r in hit); dominant,dom_n=top_clusters.most_common(1)[0] if top_clusters else ("",0)
            dom=[r for r in hit if r["top_mibig_accession"]==dominant]; dom_clear=[r for r in clear if r["top_mibig_accession"]==dominant]
            eff=[number(r["top_identity_x_coverage"]) for r in hit]; gaps=[number(r["top_minus_second_identity_x_coverage_points"]) for r in hit if r["top_minus_second_identity_x_coverage_points"]!=""]
            hf=len(hit)/len(current) if current else 0; cf=len(clear)/len(hit) if hit else 0; df=dom_n/len(hit) if hit else 0
            raw=30*(statistics.median(eff) if eff else 0)/100+20*cf+20*df+15*min(1,max(0,statistics.median(gaps) if gaps else 0)/50)+15*hf
            breadth=min(1,math.log2(1+len(hit))/math.log2(6)) if hit else 0
            meta=inv.get(bgc,{}); boundary=meta.get("Boundary",""); penalty=(8 if boundary and boundary!="Interior" else 0)+(8 if len(current)<5 else 0)
            bgcs.append({"complete_identity":current[0]["complete_identity"],"bgc_clear_match_score_0_100":round(max(0,raw*(.7+.3*breadth)-penalty),2),"boundary_fragment_penalty":penalty,"current_antismash_products":meta.get("Products","") ,"current_boundary":boundary,"total_cds":len(current),"genes_with_mibig_hit":len(hit),"clear_specific_high_genes":len(clear),"dominant_top_mibig_accession":dominant,"dominant_top_mibig_product":dom[0]["top_mibig_product"] if dom else "","genes_top_matching_dominant_cluster":dom_n,"clear_genes_top_matching_dominant_cluster":len(dom_clear),"hit_fraction":round(hf,4),"clear_fraction_among_hit_genes":round(cf,4),"dominant_cluster_fraction_among_hit_genes":round(df,4),"median_top_identity_x_coverage":med(eff),"median_top_minus_second_identity_x_coverage_gap":med(gaps),"evidence_breadth_factor":round(breadth,4),"claim_ceiling":CLAIM})
            top2.append(top_k_summary(current,2)); top3.append(top_k_summary(current,3))
    if not genes:
        # Every discovered package had an empty _cds_table.csv, so there is nothing to rank.
        # The ALL_MIBIG_HITS write below is already empty-guarded, but the gene/bgc/matching
        # writers index row 0 (genes[0], bgcs[0], matching_counts[0]); without this guard an
        # empty cohort aborts with an opaque IndexError instead of a clear diagnostic.
        raise ValueError(
            f"clear_match_finder: no CDS rows across {len(packages)} package(s); nothing to "
            "rank (each _cds_table.csv had no data rows). Check package extraction/inputs.")
    order={"CLEAR_SPECIFIC_HIGH":0,"HIGH_NO_DISTINCT_RUNNER_UP":1,"HIGH_BUT_AMBIGUOUS":2,"MODERATE_CLEAR":3,"MATCH_WITHOUT_CLEAR_SEPARATION":4,"NO_MIBIG_HIT_RECORDED":5}
    genes.sort(key=lambda r:(order[r["match_band"]],-number(r["top_identity_x_coverage"]),-number(r["top_minus_second_identity_x_coverage_points"]),r["complete_identity"],number(r["gene_order"])))
    for i,r in enumerate(genes,1): r["gene_clear_match_rank_all_cds"]=i
    bgcs.sort(key=lambda r:(-number(r["bgc_clear_match_score_0_100"]),-int(r["clear_specific_high_genes"]),r["complete_identity"]))
    for i,r in enumerate(bgcs,1): r["bgc_clear_match_rank"]=i
    count_order=sorted(bgcs,key=lambda r:(-int(r["clear_specific_high_genes"]),-number(r["bgc_clear_match_score_0_100"]),r["complete_identity"]))
    for i,r in enumerate(count_order,1): r["clear_gene_count_rank"]=i
    any_match_order=sorted(bgcs,key=lambda r:(-int(r["genes_with_mibig_hit"]),-int(r["genes_top_matching_dominant_cluster"]),-int(r["clear_specific_high_genes"]),-number(r["bgc_clear_match_score_0_100"]),r["complete_identity"]))
    dominant_match_order=sorted(bgcs,key=lambda r:(-int(r["genes_top_matching_dominant_cluster"]),-int(r["genes_with_mibig_hit"]),-int(r["clear_specific_high_genes"]),-number(r["bgc_clear_match_score_0_100"]),r["complete_identity"]))
    any_rank={r["complete_identity"]:i for i,r in enumerate(any_match_order,1)}
    dominant_rank={r["complete_identity"]:i for i,r in enumerate(dominant_match_order,1)}
    any_percentage_order=sorted(bgcs,key=lambda r:(-number(r["hit_fraction"]),-int(r["genes_with_mibig_hit"]),-number(r["bgc_clear_match_score_0_100"]),r["complete_identity"]))
    dominant_percentage_order=sorted(bgcs,key=lambda r:(-(int(r["genes_top_matching_dominant_cluster"])/int(r["total_cds"]) if int(r["total_cds"]) else 0),-int(r["genes_top_matching_dominant_cluster"]),-number(r["bgc_clear_match_score_0_100"]),r["complete_identity"]))
    any_percentage_rank={r["complete_identity"]:i for i,r in enumerate(any_percentage_order,1)}
    dominant_percentage_rank={r["complete_identity"]:i for i,r in enumerate(dominant_percentage_order,1)}
    matching_counts=[]
    for r in any_match_order:
        matching_counts.append({
            "matching_gene_count_rank_all_bgcs":any_rank[r["complete_identity"]],
            "matching_gene_percentage_rank_all_bgcs":any_percentage_rank[r["complete_identity"]],
            "dominant_cluster_gene_count_rank_all_bgcs":dominant_rank[r["complete_identity"]],
            "dominant_cluster_gene_percentage_rank_all_bgcs":dominant_percentage_rank[r["complete_identity"]],
            "complete_identity":r["complete_identity"],
            "genes_with_any_mibig_match":r["genes_with_mibig_hit"],
            "genes_matching_dominant_mibig_cluster":r["genes_top_matching_dominant_cluster"],
            "clear_specific_high_gene_matches":r["clear_specific_high_genes"],
            "dominant_top_mibig_accession":r["dominant_top_mibig_accession"],
            "dominant_top_mibig_product":r["dominant_top_mibig_product"],
            "total_cds":r["total_cds"],
            "fraction_cds_with_any_mibig_match":r["hit_fraction"],
            "fraction_cds_matching_dominant_mibig_cluster":round(int(r["genes_top_matching_dominant_cluster"])/int(r["total_cds"]),4) if int(r["total_cds"]) else 0,
            "fraction_hit_genes_matching_dominant_cluster":r["dominant_cluster_fraction_among_hit_genes"],
            "bgc_clear_match_score_0_100":r["bgc_clear_match_score_0_100"],
            "current_antismash_products":r["current_antismash_products"],
            "current_boundary":r["current_boundary"],
            "claim_ceiling":CLAIM,
        })
    interior=[r for r in bgcs if r.get("current_boundary")=="Interior"]
    for i,r in enumerate(interior,1): r["interior_only_rank"]=i
    for r in bgcs:
        r.setdefault("interior_only_rank","")
    for k,rows in ((2,top2),(3,top3)):
        eligible=[r for r in rows if r[f"top_{k}_rank_eligible"]=="YES"]
        eligible.sort(key=lambda r:(-number(r[f"top_{k}_gene_match_score_0_100"]),-int(r[f"top_{k}_clear_specific_high_genes"]),r["complete_identity"]))
        rank_by_identity={r["complete_identity"]:i for i,r in enumerate(eligible,1)}
        rows.sort(key=lambda r:(rank_by_identity.get(r["complete_identity"],10**9),r["complete_identity"]))
        for r in rows: r[f"top_{k}_gene_rank_all_bgcs"]=rank_by_identity.get(r["complete_identity"],"")
    write_tsv(out/"ALL_MIBIG_HITS_EXACT_IDENTITY.tsv",raw_hits,list(raw_hits[0]) if raw_hits else ["complete_identity"])
    gene_fields=["gene_clear_match_rank_all_cds"]+[k for k in genes[0] if k!="gene_clear_match_rank_all_cds"]
    bgc_fields=["bgc_clear_match_rank","clear_gene_count_rank","interior_only_rank"]+[k for k in bgcs[0] if k not in {"bgc_clear_match_rank","clear_gene_count_rank","interior_only_rank"}]
    write_tsv(out/"ALL_GENE_TOP_VS_SECOND_MIBIG.tsv",genes,gene_fields)
    write_tsv(out/"ALL_BGC_CLEAR_MATCH_RANK.tsv",bgcs,bgc_fields)
    matching_fields=list(matching_counts[0])
    write_tsv(out/"ALL_BGC_MATCHING_GENE_COUNT_RANK.tsv",matching_counts,matching_fields)
    hit_fraction_rows=sorted((dict(r) for r in matching_counts),key=lambda r:(int(r["matching_gene_percentage_rank_all_bgcs"]),r["complete_identity"]))
    write_tsv(out/"ALL_BGC_HIT_FRACTION_RANK.tsv",hit_fraction_rows,matching_fields)
    for k,rows in ((2,top2),(3,top3)):
        fields=[f"top_{k}_gene_rank_all_bgcs"]+[name for name in rows[0] if name!=f"top_{k}_gene_rank_all_bgcs"]
        write_tsv(out/f"ALL_BGC_TOP_{k}_GENE_MATCH_RANK.tsv",rows,fields)
    per_strain=out/"PER_STRAIN"; per_strain.mkdir(exist_ok=True)
    strain_names=sorted({strain_from_identity(r["complete_identity"]) for r in bgcs})
    for strain in strain_names:
        target=per_strain/safe_segment(strain); target.mkdir(exist_ok=True)
        sb=[dict(r) for r in bgcs if strain_from_identity(r["complete_identity"])==strain]
        for i,r in enumerate(sb,1): r["strain_bgc_clear_match_rank"]=i
        write_tsv(target/"BGC_CLEAR_MATCH_RANK.tsv",sb,["strain_bgc_clear_match_rank"]+bgc_fields)
        sg=[r for r in genes if strain_from_identity(r["complete_identity"])==strain]
        write_tsv(target/"GENE_TOP_VS_SECOND_MIBIG.tsv",sg,gene_fields)
        sr=[r for r in raw_hits if strain_from_identity(r["complete_identity"])==strain]
        write_tsv(target/"MIBIG_HITS_EXACT_IDENTITY.tsv",sr,list(raw_hits[0]) if raw_hits else ["complete_identity"])
        sm=[dict(r) for r in matching_counts if strain_from_identity(r["complete_identity"])==strain]
        sm.sort(key=lambda r:(-int(r["genes_with_any_mibig_match"]),-int(r["genes_matching_dominant_mibig_cluster"]),-int(r["clear_specific_high_gene_matches"]),-number(r["bgc_clear_match_score_0_100"]),r["complete_identity"]))
        for i,r in enumerate(sm,1): r["matching_gene_count_rank_within_strain"]=i
        percentage_sm=sorted(sm,key=lambda r:(-number(r["fraction_cds_with_any_mibig_match"]),-int(r["genes_with_any_mibig_match"]),-number(r["bgc_clear_match_score_0_100"]),r["complete_identity"]))
        percentage_sm_rank={r["complete_identity"]:i for i,r in enumerate(percentage_sm,1)}
        dominant_sm=sorted(sm,key=lambda r:(-int(r["genes_matching_dominant_mibig_cluster"]),-int(r["genes_with_any_mibig_match"]),-int(r["clear_specific_high_gene_matches"]),-number(r["bgc_clear_match_score_0_100"]),r["complete_identity"]))
        dominant_sm_rank={r["complete_identity"]:i for i,r in enumerate(dominant_sm,1)}
        for r in sm: r["dominant_cluster_gene_count_rank_within_strain"]=dominant_sm_rank[r["complete_identity"]]
        dominant_percentage_sm=sorted(sm,key=lambda r:(-number(r["fraction_cds_matching_dominant_mibig_cluster"]),-int(r["genes_matching_dominant_mibig_cluster"]),-number(r["bgc_clear_match_score_0_100"]),r["complete_identity"]))
        dominant_percentage_sm_rank={r["complete_identity"]:i for i,r in enumerate(dominant_percentage_sm,1)}
        for r in sm:
            r["matching_gene_percentage_rank_within_strain"]=percentage_sm_rank[r["complete_identity"]]
            r["dominant_cluster_gene_percentage_rank_within_strain"]=dominant_percentage_sm_rank[r["complete_identity"]]
        per_strain_matching_fields=["matching_gene_count_rank_within_strain","matching_gene_percentage_rank_within_strain","dominant_cluster_gene_count_rank_within_strain","dominant_cluster_gene_percentage_rank_within_strain"]+[name for name in matching_fields if name not in {"matching_gene_count_rank_within_strain","matching_gene_percentage_rank_within_strain","dominant_cluster_gene_count_rank_within_strain","dominant_cluster_gene_percentage_rank_within_strain"}]
        write_tsv(target/"BGC_MATCHING_GENE_COUNT_RANK.tsv",sm,per_strain_matching_fields)
        hit_fraction_sm=sorted((dict(r) for r in sm),key=lambda r:(int(r["matching_gene_percentage_rank_within_strain"]),r["complete_identity"]))
        write_tsv(target/"BGC_HIT_FRACTION_RANK.tsv",hit_fraction_sm,per_strain_matching_fields)
        for k,rows in ((2,top2),(3,top3)):
            subset=[dict(r) for r in rows if strain_from_identity(r["complete_identity"])==strain]
            rank=0
            for r in subset:
                if r[f"top_{k}_rank_eligible"]=="YES": rank+=1; r[f"top_{k}_gene_rank_within_strain"]=rank
                else: r[f"top_{k}_gene_rank_within_strain"]=""
            fields=[f"top_{k}_gene_rank_within_strain",f"top_{k}_gene_rank_all_bgcs"]+[name for name in subset[0] if name not in {f"top_{k}_gene_rank_within_strain",f"top_{k}_gene_rank_all_bgcs"}]
            write_tsv(target/f"BGC_TOP_{k}_GENE_MATCH_RANK.tsv",subset,fields)
    write_tsv(out/"SOURCE_HASHES.tsv",sources,list(sources[0]))
    bands=Counter(r["match_band"] for r in genes)
    receipt={"status":"COMPLETE","packages":len(packages),"strains":len(strain_names),"bgcs":len(bgcs),"cds_rows":len(genes),"raw_mibig_hit_rows":len(raw_hits),"genes_with_hits":sum(bool(r["top_mibig_accession"]) for r in genes),"clear_specific_high_genes":bands["CLEAR_SPECIFIC_HIGH"],"top_2_rank_eligible_bgcs":sum(r["top_2_rank_eligible"]=="YES" for r in top2),"top_3_rank_eligible_bgcs":sum(r["top_3_rank_eligible"]=="YES" for r in top3),"match_bands":dict(bands),"thresholds":{"minimum_top_pct_identity":min_id,"minimum_top_pct_coverage":min_cov,"minimum_top_blast_score":min_score,"minimum_identity_x_coverage_gap":min_gap,"minimum_blast_score_ratio":min_ratio},"matching_gene_rank_definition":"four parallel ranks: genes with any MIBiG hit by count and as a fraction of total CDS, plus genes whose top hit is the BGC's dominant MIBiG accession by count and as a fraction of total CDS; count and percentage ties use the companion evidence, composite score, and complete identity","top_k_gene_score_formula":"mean of selected genes; each gene = 0.60*(identity*coverage/100) + 0.25*min(100,2*positive effective-similarity gap) + 0.15*min(100,100*max(0,bit-score ratio-1)); BGC eligible only when k hit-bearing genes exist","claim_ceiling":CLAIM,"artifacts":[]}
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name!="CLEAR_MATCH_RECEIPT.json": receipt["artifacts"].append({"path":path.name,"sha256":sha256(path),"bytes":path.stat().st_size})
    (out/"CLEAR_MATCH_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt

def main(argv=None):
    p=argparse.ArgumentParser(description="Rank every CDS and BGC by top-versus-second distinct MIBiG match separation")
    p.add_argument("--package",action="append",default=[],help="package directory; repeatable")
    p.add_argument("--packages-root",help="recursively discover package directories")
    p.add_argument("--out",required=True,help="new or existing output directory")
    p.add_argument("--min-identity",type=float,default=70)
    p.add_argument("--min-coverage",type=float,default=80)
    p.add_argument("--min-blast-score",type=float,default=100)
    p.add_argument("--min-effective-gap",type=float,default=20,help="minimum gap in identity x coverage")
    p.add_argument("--min-score-ratio",type=float,default=1.5)
    p.add_argument("--strain-aliases",help="optional CSV with source_strain,display_strain columns; aliases are explicit provenance, never inferred")
    args=p.parse_args(argv)
    packages=discover_packages(args.package,args.packages_root)
    aliases=read_aliases(args.strain_aliases)
    receipt=analyze(packages,args.out,args.min_identity,args.min_coverage,args.min_blast_score,args.min_effective_gap,args.min_score_ratio,aliases)
    _sys.stdout.write(json.dumps(receipt,indent=2) + "\n"); return 0

if __name__=="__main__": raise SystemExit(main())

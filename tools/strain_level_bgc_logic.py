#!/usr/bin/env python3
"""Build readable per-strain BGC product-logic reports from the CP050 workup."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

CLAIM = ("Strain-level prioritization and pathway-family hypotheses only; scores do not prove "
         "an exact product, complete pathway, expression, production, activity, novelty, "
         "physical linkage, or scientific acceptance.")

RELATION_MODIFIERS = {
    "ARCHITECTURE_CORROBORATES_REFERENCE": 8.0,
    "ARCHITECTURE_SUPPORT_PRESENT": 4.0,
    "ARCHITECTURE_EXTENDS_WEAK_REFERENCE": 2.0,
    "ARCHITECTURE_ONLY_NO_REFERENCE_MATCH": 1.0,
    "ARCHITECTURE_UNRESOLVED_REFERENCE_DOMINANT": -3.0,
    "REFERENCE_MATCH_ARCHITECTURE_UNRESOLVED": -5.0,
    "ARCHITECTURE_REFERENCE_DISCORDANT": -12.0,
    "BOTH_CHANNELS_UNRESOLVED": -15.0,
}
BOUNDARY_PENALTIES = {"Interior": 0.0, "Edge": 4.0, "Full-contig": 8.0}
# The workup already reports these when no dominant reference was selected. A BGC with no
# reference cannot have sparse support for one, so the reference-derived penalties below
# must not fire; RELATION_MODIFIERS is the channel that already prices these states.
NO_REFERENCE_RELATIONS = {"ARCHITECTURE_ONLY_NO_REFERENCE_MATCH", "BOTH_CHANNELS_UNRESOLVED"}


def read_tsv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_tsv(path, rows, fields=None):
    rows=list(rows); fields=fields or (list(rows[0]) if rows else [])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w=_SafeDictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def number(value, default=0.0):
    try: return float(value)
    except (TypeError, ValueError): return default


def integer(value): return int(number(value))


def present(row, key):
    """True when the row actually carries a usable value for key.

    A missing column, an absent key and an empty cell all mean the upstream
    comparison did not report a result. That is not the same as a reported zero.
    """
    value=row.get(key)
    return value is not None and str(value).strip()!=""


def reference_evidence_state(row):
    """Say whether the dominant-reference comparison produced a usable result.

    Missing evidence is not a negative result, so the caller must be able to
    tell the two apart before it penalises anything. Three situations otherwise
    collapse into an identical all-zero row: a reference was compared and matched
    almost nothing, no reference was ever selected, and the upstream columns are
    absent entirely.
    """
    relation=(row.get("functional_reference_relation") or "").strip()
    if relation in NO_REFERENCE_RELATIONS: return "NO_REFERENCE_SELECTED"
    matches=present(row,"genes_matching_dominant_reference")
    total=present(row,"total_cds")
    if matches and total: return "REFERENCE_EVALUATED"
    if matches and not total: return "REFERENCE_DENOMINATOR_MISSING"
    if total and not matches: return "REFERENCE_SUPPORT_NOT_EVALUATED"
    return "REFERENCE_NOT_EVALUATED"


def strain_of(identity):
    parts=identity.split(" / ")
    if len(parts)!=4 or not all(parts): raise ValueError(f"incomplete BGC identity: {identity}")
    return parts[0]


def generic_assembly_line(row):
    text=" ".join([row.get("current_antismash_products", ""), row.get("architecture_first_pathway_type", "")]).lower()
    return bool(re.search(r"\bpks\b|t1pks|t2pks|t3pks|nrps|polyketide|hybrid", text))


def product_label(row):
    arch=row.get("architecture_first_pathway_type", "") or "unknown"
    ref=row.get("dominant_mibig_product", "")
    relation=row.get("functional_reference_relation", "")
    products=row.get("current_antismash_products", "")
    if relation=="ARCHITECTURE_REFERENCE_DISCORDANT":
        return f"{arch} capacity; conflict with {ref or 'selected reference'}"
    if relation=="ARCHITECTURE_CORROBORATES_REFERENCE" and ref:
        return f"{ref}-like family (architecture corroborated)"
    if relation in {"REFERENCE_MATCH_ARCHITECTURE_UNRESOLVED","ARCHITECTURE_UNRESOLVED_REFERENCE_DOMINANT"} and ref:
        return f"{ref}-like family (reference-led; architecture unresolved)"
    if arch and arch!="unknown" and ref:
        return f"{arch} capacity; {ref}-like comparison"
    if arch and arch!="unknown":
        return f"{arch} capacity (architecture-only)"
    if ref:
        return f"{ref}-like reference signal"
    return f"{products or 'unresolved BGC'} (unresolved family)"


def comparison_family(row):
    """Return the narrowest architecture-led key suitable for cross-strain review."""
    arch=(row.get("architecture_first_pathway_type") or "").strip()
    if arch and arch.lower() not in {"unknown","unresolved"}: return arch
    products=(row.get("current_antismash_products") or "").strip()
    return products or "unresolved BGC"


def score_row(row):
    score=number(row.get("standalone_biological_evidence_score_0_100"))
    score+=RELATION_MODIFIERS.get(row.get("functional_reference_relation", ""), 0.0)
    boundary=row.get("boundary", "")
    score-=BOUNDARY_PENALTIES.get(boundary, 0.0)
    tier=row.get("evidence_tier", "")
    if tier.startswith("A_"): score+=6.0
    elif tier.startswith("B_SUPPORTED_PARTIAL"): score+=3.0
    evidence_state=reference_evidence_state(row)
    matches=integer(row.get("genes_matching_dominant_reference"))
    total=integer(row.get("total_cds"))
    # An absent denominator used to become max(1, 0) == 1, which turned "5 matched"
    # into a 500% hit fraction and silently suppressed the low-fraction control.
    match_fraction=(matches/total) if total>0 else None
    generic=generic_assembly_line(row)
    flags=[]
    extra=0.0
    if generic and boundary=="Full-contig":
        extra+=12.0; flags.append("GENERIC_ASSEMBLY_LINE_FULL_CONTIG")
    elif generic and boundary=="Edge":
        extra+=6.0; flags.append("GENERIC_ASSEMBLY_LINE_EDGE")
    # Only penalise sparse reference support when the comparison actually reported one.
    evaluated=evidence_state=="REFERENCE_EVALUATED"
    if generic and evaluated and matches<4:
        extra+=6.0; flags.append("SPARSE_REFERENCE_GENE_SUPPORT")
    if generic and evaluated and match_fraction is not None and match_fraction<0.15:
        extra+=4.0; flags.append("LOW_REFERENCE_HIT_FRACTION")
    if generic and evidence_state!="REFERENCE_EVALUATED":
        flags.append(evidence_state)
    fragment_flag="; ".join(flags) if flags else "NO_EXTRA_FRAGMENT_PENALTY"
    score=max(0.0,min(100.0,score-extra))
    if score>=70 and row.get("functional_reference_relation") not in {"ARCHITECTURE_REFERENCE_DISCORDANT","BOTH_CHANNELS_UNRESOLVED"}:
        band="P1_STRONG_FAMILY_HYPOTHESIS"
    elif score>=50: band="P2_SUPPORTED_FAMILY_HYPOTHESIS"
    elif score>=30: band="P3_PROVISIONAL_CAPACITY"
    else: band="P4_FRAGMENT_OR_WEAK_SIGNAL"
    return score,band,fragment_flag,match_fraction


def safe_name(value): return re.sub(r"[^A-Za-z0-9._-]+","_",value)


ROLE_COLORS={"core":"#C0392B","precursor":"#D6A321","maturation":"#7D4EA3","tailoring":"#D97822","transport":"#2878A5","regulatory":"#37825B","resistance":"#B33B74","other":"#9AA5A8"}


def load_coordinates(package_list):
    if not package_list: return {}
    packages=[]
    with Path(package_list).open(encoding="utf-8") as f:
        packages=[Path(x.strip()).expanduser().resolve() for x in f if x.strip() and not x.startswith("#")]
    out={}
    for package in packages:
        hits=sorted(package.glob("*_cds_table.csv"))
        if len(hits)!=1: raise ValueError(f"{package}: expected one *_cds_table.csv; found {len(hits)}")
        with hits[0].open(newline="",encoding="utf-8-sig",errors="replace") as f:
            for r in csv.DictReader(f):
                key=(r.get("strain",""),r.get("bgc_id",""),r.get("locus_tag",""))
                if not all(key): raise ValueError(f"{hits[0]}: incomplete CDS coordinate key")
                out[key]={k:r.get(k,"") for k in ("start","end","strand","length_bp","contig","region")}
    return out


def svg_escape(value): return html.escape(str(value),quote=True)


def write_locus_map(path, identity, genes):
    ordered=sorted(genes,key=lambda g:integer(g.get("gene_order")))
    coords=[(integer(g.get("start")),integer(g.get("end"))) for g in ordered if g.get("start") and g.get("end")]
    real=bool(coords) and len(coords)==len(ordered)
    if real:
        lo=min(a for a,b in coords); hi=max(b for a,b in coords); span=max(1,hi-lo)
    else:
        lo=0; span=max(1,sum(max(30,integer(g.get("aa_length"))*3) for g in ordered))
    width=1200; left=35; usable=1130; y=52; h=32; xcursor=0
    shapes=[]; labels=[]
    for i,g in enumerate(ordered):
        if real:
            a=integer(g.get("start")); b=integer(g.get("end")); x=left+(min(a,b)-lo)/span*usable; w=max(5,abs(b-a)/span*usable)
        else:
            bp=max(30,integer(g.get("aa_length"))*3); x=left+xcursor/span*usable; w=max(5,bp/span*usable); xcursor+=bp
        role=g.get("primary_functional_role","other"); color=ROLE_COLORS.get(role,ROLE_COLORS["other"]); strand=str(g.get("strand",1))
        tip=min(9,w/3)
        if strand.startswith("-"):
            pts=f"{x+w},{y} {x+tip},{y} {x},{y+h/2} {x+tip},{y+h} {x+w},{y+h}"
        else:
            pts=f"{x},{y} {x+w-tip},{y} {x+w},{y+h/2} {x+w-tip},{y+h} {x},{y+h}"
        title=f"{g.get('query_gene','')} | {role} | {g.get('aa_length','')} aa | {g.get('product_annotation','')}"
        shapes.append(f'<polygon points="{pts}" fill="{color}" stroke="#ffffff" stroke-width="1"><title>{svg_escape(title)}</title></polygon>')
        show=len(ordered)<=24 or role!="other" or g.get("dominant_reference_gene_match")=="YES"
        if show:
            labels.append(f'<text x="{x+w/2:.1f}" y="{y+h+15}" font-size="9" text-anchor="middle" transform="rotate(35 {x+w/2:.1f},{y+h+15})">{svg_escape(g.get("query_gene",""))}</text>')
    legend=[]; lx=35
    for role,color in ROLE_COLORS.items():
        legend.append(f'<rect x="{lx}" y="117" width="12" height="12" fill="{color}"/><text x="{lx+16}" y="127" font-size="10">{role}</text>');lx+=105
    subtitle="genomic-coordinate map" if real else "gene-order schematic scaled by protein length"
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 145" role="img" aria-label="{svg_escape(identity)} locus map"><rect width="1200" height="145" fill="#ffffff"/><text x="35" y="20" font-family="sans-serif" font-size="13" font-weight="bold">{svg_escape(identity)}</text><text x="35" y="38" font-family="sans-serif" font-size="10" fill="#52656a">{subtitle}; arrows show strand; hover for protein details</text>{''.join(shapes)}{''.join(labels)}{''.join(legend)}</svg>'''
    Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(svg,encoding="utf-8")


def protein_table_html(genes):
    ordered=sorted(genes,key=lambda g:integer(g.get("gene_order")))
    if not ordered:return '<p class="small">No gene ledger rows were supplied.</p>'
    return '<table><tr><th>Order</th><th>Protein</th><th>Coordinates</th><th>aa</th><th>Role</th><th>Function and domains</th><th>Dominant-reference homology</th></tr>'+''.join(f'<tr><td>{html.escape(g.get("gene_order",""))}</td><td>{html.escape(g.get("query_gene",""))}</td><td>{html.escape(g.get("start",""))}-{html.escape(g.get("end",""))} ({html.escape(g.get("strand",""))})</td><td>{html.escape(g.get("aa_length",""))}</td><td>{html.escape(g.get("primary_functional_role",""))}</td><td>{html.escape(g.get("product_annotation","") or g.get("gene_functions",""))}<br><span class="small">{html.escape(g.get("sec_met_domains",""))}</span></td><td>{html.escape(g.get("matched_subject_gene","") or "no dominant-reference match")}<br><span class="small">ID {html.escape(g.get("matched_pct_identity","") or "-")}%; coverage {html.escape(g.get("matched_pct_coverage","") or "-")}%</span></td></tr>' for g in ordered)+'</table>'


def md_escape(value): return str(value or "").replace("|","\\|").replace("\n"," ")


def protein_table_md(genes):
    out=["| Order | Protein | Coordinates | aa | Role | Function and domains | Dominant-reference homology |","|---:|---|---|---:|---|---|---|"]
    for g in sorted(genes,key=lambda x:integer(x.get("gene_order"))):
        hom=(g.get("matched_subject_gene") or "no dominant-reference match")
        if g.get("matched_pct_identity"):hom+=f"; ID {g['matched_pct_identity']}%; coverage {g.get('matched_pct_coverage','-')}%"
        func="; ".join(x for x in [g.get("product_annotation",""),g.get("sec_met_domains","")] if x)
        out.append("| "+" | ".join(md_escape(x) for x in [g.get("gene_order",""),g.get("query_gene",""),f"{g.get('start','')}-{g.get('end','')} ({g.get('strand','')})",g.get("aa_length",""),g.get("primary_functional_role",""),func,hom])+" |")
    return "\n".join(out)


def style():
    return """body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#f5f2e9;color:#183137}main{max-width:1180px;margin:auto;padding:42px 26px 70px}h1{font-size:38px;margin:0 0 8px}h2{margin-top:34px}.sub{font-size:18px;line-height:1.5;max-width:900px}.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:24px 0}.metric{background:white;padding:15px;border-top:5px solid #087b7a;box-shadow:0 2px 12px #0001}.metric b{display:block;font-size:25px;color:#075d60}.panel{background:white;padding:18px;margin:14px 0;box-shadow:0 2px 12px #0001}.p1{border-left:6px solid #167647}.p2{border-left:6px solid #2b7a9b}.p3{border-left:6px solid #d49a1f}.p4{border-left:6px solid #9b5d55}.linkedunit{background:#e7f2ef;border:2px solid #167647;padding:18px;margin:20px 0}.linkedunit h3{margin:0;color:#135f43}.unitgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.identity{font-weight:700;color:#075d60;overflow-wrap:anywhere}.tags{display:flex;gap:7px;flex-wrap:wrap;margin:9px 0}.tag{background:#e7efee;border-radius:14px;padding:4px 9px;font-size:12px}.warn{color:#8a3f27;font-weight:650}.score{font-size:24px;font-weight:750;float:right}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.card{background:white;padding:15px;text-decoration:none;color:inherit;border-left:4px solid #d49a1f;box-shadow:0 2px 10px #0001}.card strong{display:block}.small{font-size:13px;color:#52656a}table{width:100%;border-collapse:collapse;background:white}th,td{padding:9px;border-bottom:1px solid #d6dddd;text-align:left;vertical-align:top}th{background:#174658;color:white}a{color:#076c70}@media(max-width:800px){.metrics,.grid,.unitgrid{grid-template-columns:1fr}.score{float:none}}"""


def bgc_panel(row, genes):
    band=row["strain_product_evidence_band"]
    css="p1" if band.startswith("P1") else "p2" if band.startswith("P2") else "p3" if band.startswith("P3") else "p4"
    warning="" if row["fragment_genericity_flag"]=="NO_EXTRA_FRAGMENT_PENALTY" else f'<p class="warn">Fragment/genericity control: {html.escape(row["fragment_genericity_flag"])}</p>'
    unmatched=[g for g in genes if g.get("functional_logic_without_dominant_match")=="YES"]
    gene_html="<p class=\"small\">No annotation-supported unmatched functional genes recorded.</p>"
    if unmatched:
        gene_html='<details><summary><b>Annotation-supported genes outside the dominant reference</b> ('+str(len(unmatched))+')</summary><table><tr><th>Gene</th><th>Role</th><th>Logic</th><th>Annotation</th><th>Any MIBiG match</th></tr>'+''.join(f'<tr><td>{html.escape(g.get("query_gene",""))}</td><td>{html.escape(g.get("primary_functional_role",""))}</td><td>{html.escape(g.get("functional_logic_tags",""))}</td><td>{html.escape(g.get("product_annotation",""))}</td><td>{html.escape(g.get("any_mibig_gene_match",""))}</td></tr>' for g in unmatched[:20])+'</table></details>'
    map_rel=row.get("locus_map_relpath","")
    map_html=f'<img src="{html.escape(map_rel)}" alt="{html.escape(row["complete_identity"])} locus map" style="width:100%;background:white">' if map_rel else ""
    return f'''<section class="panel {css}"><span class="score">{html.escape(row['strain_product_logic_score_0_100'])}</span><div class="identity">{html.escape(row['complete_identity'])}</div><h3>{html.escape(row['potential_product_family_hypothesis'])}</h3><div class="tags"><span class="tag">{html.escape(band)}</span><span class="tag">boundary {html.escape(row['boundary'])}</span><span class="tag">{html.escape(row['functional_reference_relation'])}</span><span class="tag">{html.escape(row['evidence_tier'])}</span></div>{warning}<p>{html.escape(row['functional_logic_summary'])}</p><p><b>Direct support:</b> {html.escape(row['genes_matching_dominant_reference'])}/{html.escape(row['total_cds'])} genes match the dominant reference; {html.escape(row['functional_genes_without_any_mibig_match'])} functional genes have no admitted MIBiG match.</p><p><b>Architecture:</b> {html.escape(row['architecture_first_pathway_type'])} ({html.escape(row['architecture_first_confidence'])}). <b>RG-GMCI:</b> {html.escape(row['rggmci_confidence'] or 'none')} {html.escape(row['rggmci_partner_identity'])}</p>{map_html}{gene_html}<details><summary><b>All proteins, sizes, functions, domains, and homology</b> ({len(genes)})</summary>{protein_table_html(genes)}</details><p class="small">Highest-information question: {html.escape(row['decisive_review_question'])}</p></section>'''


def top_units(srows, genes_by_bgc, limit=10):
    """Render ranked loci while co-locating every admitted HIGH RG-GMCI pair."""
    by_identity={r["complete_identity"]:r for r in srows}; seen=set(); units=[]
    for r in srows:
        if r["complete_identity"] in seen: continue
        partner=by_identity.get(r.get("rggmci_partner_identity", ""))
        is_high=r.get("rggmci_confidence", "").startswith("HIGH")
        if is_high and partner and partner["complete_identity"] not in seen:
            seen.update([r["complete_identity"],partner["complete_identity"]])
            units.append('<section class="linkedunit"><h3>HIGH RG-GMCI rescue unit</h3><p>These two complete-identity loci are displayed together because the admitted RG-GMCI evidence supports a complementary or truncation-rescue interpretation. Assess the pair as one reconstruction candidate while retaining the physical-linkage claim ceiling.</p><div class="unitgrid">'+bgc_panel(r,genes_by_bgc.get(r["complete_identity"],[]))+bgc_panel(partner,genes_by_bgc.get(partner["complete_identity"],[]))+'</div></section>')
        else:
            seen.add(r["complete_identity"]); units.append(bgc_panel(r,genes_by_bgc.get(r["complete_identity"],[])))
        if len(units)>=limit: break
    return "".join(units)


def top_unit_rows(srows, limit=10):
    by_identity={r["complete_identity"]:r for r in srows};seen=set();units=[]
    for r in srows:
        if r["complete_identity"] in seen:continue
        partner=by_identity.get(r.get("rggmci_partner_identity",""))
        if r.get("rggmci_confidence","").startswith("HIGH") and partner and partner["complete_identity"] not in seen:
            seen.update([r["complete_identity"],partner["complete_identity"]]);units.append([r,partner])
        else:seen.add(r["complete_identity"]);units.append([r])
        if len(units)>=limit:break
    return units


def build(bgc_path, out, gene_path=None, package_list=None):
    rows=read_tsv(bgc_path); out=Path(out).resolve(); out.mkdir(parents=True,exist_ok=True)
    genes=read_tsv(gene_path) if gene_path else [];coordinates=load_coordinates(package_list)
    for g in genes:g.update(coordinates.get((g.get("strain",""),g.get("bgc_alias",""),g.get("query_gene","")),{}))
    genes_by_bgc=defaultdict(list)
    for g in genes: genes_by_bgc[g.get("complete_identity","")].append(g)
    enhanced=[]; by_strain=defaultdict(list)
    for r in rows:
        strain=strain_of(r["complete_identity"]); score,band,flag,frac=score_row(r)
        x=dict(r); x.update({"strain":strain,"potential_product_family_hypothesis":product_label(r),"strain_product_logic_score_0_100":f"{score:.2f}","strain_product_evidence_band":band,"fragment_genericity_flag":flag,"dominant_reference_hit_fraction":("" if frac is None else f"{frac:.4f}"),"strain_logic_reference_evidence_state":reference_evidence_state(r),"strain_product_rank":"","claim_ceiling":CLAIM})
        enhanced.append(x); by_strain[strain].append(x)
    for strain,srows in by_strain.items():
        srows.sort(key=lambda x:(-number(x["strain_product_logic_score_0_100"]),integer(x.get("definitive_rank_within_strain")),x["complete_identity"]))
        for i,r in enumerate(srows,1): r["strain_product_rank"]=str(i)
    enhanced.sort(key=lambda x:(x["strain"],integer(x["strain_product_rank"])))
    comparison_groups=defaultdict(list)
    for r in enhanced: comparison_groups[comparison_family(r)].append(r)
    comparison_rows=[]; comparison_by_strain=defaultdict(list)
    for family,members in comparison_groups.items():
        strains=sorted({r["strain"] for r in members},key=lambda x:integer(x.split("-")[-1]))
        if len(strains)<2: continue
        best=max(members,key=lambda x:number(x["strain_product_logic_score_0_100"]))
        row={"comparison_family":family,"locus_count":str(len(members)),"strain_count":str(len(strains)),"strains":"; ".join(strains),"best_score":best["strain_product_logic_score_0_100"],"median_score":f"{statistics.median(number(r['strain_product_logic_score_0_100']) for r in members):.2f}","interior_loci":str(sum(r.get("boundary")=="Interior" for r in members)),"boundary_limited_loci":str(sum(r.get("boundary")!="Interior" for r in members)),"best_complete_identity":best["complete_identity"],"member_complete_identities":"; ".join(r["complete_identity"] for r in sorted(members,key=lambda x:-number(x["strain_product_logic_score_0_100"]))),"claim_ceiling":CLAIM}
        comparison_rows.append(row)
        for strain in strains:comparison_by_strain[strain].append(row)
    comparison_rows.sort(key=lambda r:(-number(r["best_score"]),-integer(r["strain_count"]),r["comparison_family"]))
    write_tsv(out/"CROSS_STRAIN_BGC_COMPARISON.tsv",comparison_rows)
    cmp_md=["# Cross Strain BGC Architecture Comparison","",f"{len(comparison_rows)} architecture-led groups occur in at least two of the 42 package-backed AS strains. The family key comes from the architecture-first assignment when available, then the current antiSMASH product label. It is a comparison key, not an exact product call.","","| Architecture-led comparison family | Loci | Strains | Best score | Median score | Interior | Boundary limited | Best complete identity |","|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in comparison_rows:cmp_md.append("| "+" | ".join(md_escape(r[k]) for k in ("comparison_family","locus_count","strain_count","best_score","median_score","interior_loci","boundary_limited_loci","best_complete_identity"))+" |")
    cmp_md += ["","## Claim ceiling","",CLAIM,""]
    (out/"CROSS_STRAIN_BGC_COMPARISON.md").write_text("\n".join(cmp_md),encoding="utf-8")
    fields=["strain","strain_product_rank","strain_product_logic_score_0_100","strain_product_evidence_band","potential_product_family_hypothesis","fragment_genericity_flag","dominant_reference_hit_fraction","strain_logic_reference_evidence_state"]+[k for k in rows[0] if k not in {"claim_ceiling"}]+["claim_ceiling"]
    write_tsv(out/"ALL_BGC_STRAIN_PRODUCT_LOGIC.tsv",enhanced,fields)
    strain_summary=[]; family_summary=[]
    for strain,srows in sorted(by_strain.items()):
        counts=Counter(r["strain_product_evidence_band"] for r in srows); bounds=Counter(r["boundary"] for r in srows)
        linked=[]; seen=set()
        for r in srows:
            if r.get("rggmci_confidence","").startswith("HIGH") and r.get("rggmci_partner_identity"):
                pair=tuple(sorted([r["complete_identity"],r["rggmci_partner_identity"]]))
                if pair not in seen: seen.add(pair); linked.append(pair)
        top=srows[:10]
        report_dir=out/"PER_STRAIN"/safe_name(strain); report_dir.mkdir(parents=True,exist_ok=True)
        write_tsv(report_dir/"BGC_PRODUCT_LOGIC.tsv",srows,fields)
        units=top_unit_rows(srows)
        for unit in units:
            for r in unit:
                name=safe_name(r["complete_identity"])+".svg";write_locus_map(report_dir/"LOCUS_MAPS"/name,r["complete_identity"],genes_by_bgc.get(r["complete_identity"],[]));r["locus_map_relpath"]="LOCUS_MAPS/"+name
        fam=defaultdict(list)
        for r in srows: fam[r["potential_product_family_hypothesis"]].append(r)
        for label,frs in sorted(fam.items(),key=lambda kv:-max(number(x["strain_product_logic_score_0_100"]) for x in kv[1])):
            best=max(frs,key=lambda x:number(x["strain_product_logic_score_0_100"]))
            family_summary.append({"strain":strain,"potential_product_family_hypothesis":label,"locus_count":len(frs),"best_score":best["strain_product_logic_score_0_100"],"best_complete_identity":best["complete_identity"],"best_evidence_band":best["strain_product_evidence_band"],"boundary_limited_loci":sum(r["boundary"]!="Interior" for r in frs),"claim_ceiling":CLAIM})
        metrics=f'''<div class="metrics"><div class="metric"><b>{len(srows)}</b>BGCs</div><div class="metric"><b>{counts['P1_STRONG_FAMILY_HYPOTHESIS']}</b>P1</div><div class="metric"><b>{counts['P2_SUPPORTED_FAMILY_HYPOTHESIS']}</b>P2</div><div class="metric"><b>{bounds['Full-contig']+bounds['Edge']}</b>boundary limited</div><div class="metric"><b>{len(linked)}</b>HIGH linked pairs</div></div>'''
        linked_html='<p>No HIGH RG-GMCI pair in the admitted workup.</p>' if not linked else '<ul>'+''.join(f'<li>{html.escape(a)} ↔ {html.escape(b)}</li>' for a,b in linked)+'</ul>'
        strain_cmp=sorted(comparison_by_strain.get(strain,[]),key=lambda r:-number(r["best_score"]))[:15]
        cmp_html='<p>No architecture-led group from this strain occurs in another package-backed strain.</p>' if not strain_cmp else '<table><tr><th>Comparison family</th><th>Loci</th><th>Strains</th><th>Best score</th><th>Best locus</th></tr>'+''.join(f'<tr><td>{html.escape(r["comparison_family"])}</td><td>{r["locus_count"]}</td><td>{html.escape(r["strains"])}</td><td>{r["best_score"]}</td><td>{html.escape(r["best_complete_identity"])}</td></tr>' for r in strain_cmp)+'</table><p><a href="../../CROSS_STRAIN_BGC_COMPARISON.md">Open the complete cross-strain comparison</a></p>'
        report=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(strain)} BGC Product Logic</title><style>{style()}</style></head><body><main><p><a href="../../INDEX.html">← all strains</a></p><h1>{html.escape(strain)} strain-level BGC logic</h1><p class="sub">Potential pathway-family and product-family hypotheses ranked within this strain. Full-contig and edge-limited generic assembly-line fragments receive explicit penalties. Every locus retains its complete identity and underlying evidence channels. HIGH RG-GMCI rescue partners are co-located as one review unit.</p>{metrics}<h2>Top potential pathway or product families</h2>{top_units(srows,genes_by_bgc)}<h2>Cross-strain architecture comparison</h2>{cmp_html}<h2>HIGH RG-GMCI fragment pairs</h2>{linked_html}<h2>All loci</h2><table><tr><th>Rank</th><th>Score</th><th>Complete identity</th><th>Hypothesis</th><th>Control</th></tr>{''.join(f'<tr><td>{r["strain_product_rank"]}</td><td>{r["strain_product_logic_score_0_100"]}</td><td>{html.escape(r["complete_identity"])}</td><td>{html.escape(r["potential_product_family_hypothesis"])}</td><td>{html.escape(r["fragment_genericity_flag"])}</td></tr>' for r in srows)}</table><h2>Claim ceiling</h2><p>{CLAIM}</p></main></body></html>'''
        (report_dir/"REPORT.html").write_text(report,encoding="utf-8")
        md=[f"# {strain} Strain Level BGC Logic","",f"Potential pathway-family and product-family hypotheses ranked within {strain}. HIGH RG-GMCI rescue partners are co-located as one review unit.","",f"- BGCs: {len(srows)}",f"- P1 strong family hypotheses: {counts['P1_STRONG_FAMILY_HYPOTHESIS']}",f"- P2 supported family hypotheses: {counts['P2_SUPPORTED_FAMILY_HYPOTHESIS']}",f"- Boundary-limited loci: {bounds['Full-contig']+bounds['Edge']}",f"- HIGH RG-GMCI pairs: {len(linked)}",""]
        for n,unit in enumerate(units,1):
            if len(unit)==2:md += [f"## Review Unit {n} HIGH RG-GMCI Rescue","",f"The following loci are assessed together as a complementary or truncation-rescue candidate. This does not establish physical linkage.",""]
            else:md += [f"## Review Unit {n}",""]
            for r in unit:
                gs=genes_by_bgc.get(r["complete_identity"],[]);md += [f"### {r['complete_identity']}","",f"**Score:** {r['strain_product_logic_score_0_100']}  ",f"**Band:** {r['strain_product_evidence_band']}  ",f"**Hypothesis:** {r['potential_product_family_hypothesis']}  ",f"**Boundary:** {r['boundary']}  ",f"**Architecture/reference relationship:** {r['functional_reference_relation']}  ",f"**Fragment control:** {r['fragment_genericity_flag']}  ","",r['functional_logic_summary'],"",f"![Locus map]({r['locus_map_relpath']})","","#### Proteins","",protein_table_md(gs),"",f"**Highest-information question:** {r['decisive_review_question']}",""]
        md += ["## Cross Strain Architecture Comparison",""]
        if not strain_cmp:md += ["No architecture-led group from this strain occurs in another package-backed strain.",""]
        else:
            md += ["| Comparison family | Loci | Strains | Best score | Best complete identity |","|---|---:|---|---:|---|"]
            for r in strain_cmp:md.append("| "+" | ".join(md_escape(r[k]) for k in ("comparison_family","locus_count","strains","best_score","best_complete_identity"))+" |")
            md += ["","See [`CROSS_STRAIN_BGC_COMPARISON.md`](../../CROSS_STRAIN_BGC_COMPARISON.md) for all groups.",""]
        md += ["## Claim ceiling","",CLAIM,""]
        (report_dir/"REPORT.md").write_text("\n".join(md),encoding="utf-8")
        strain_summary.append({"strain":strain,"bgc_count":len(srows),"p1_strong_family_hypotheses":counts["P1_STRONG_FAMILY_HYPOTHESIS"],"p2_supported_family_hypotheses":counts["P2_SUPPORTED_FAMILY_HYPOTHESIS"],"p3_provisional_capacity":counts["P3_PROVISIONAL_CAPACITY"],"p4_fragment_or_weak_signal":counts["P4_FRAGMENT_OR_WEAK_SIGNAL"],"interior_loci":bounds["Interior"],"edge_loci":bounds["Edge"],"full_contig_loci":bounds["Full-contig"],"generic_fragment_flags":sum(r["fragment_genericity_flag"]!="NO_EXTRA_FRAGMENT_PENALTY" for r in srows),"high_rggmci_pairs":len(linked),"top_complete_identity":top[0]["complete_identity"],"top_hypothesis":top[0]["potential_product_family_hypothesis"],"top_score":top[0]["strain_product_logic_score_0_100"],"report_path":str(report_dir/"REPORT.html"),"claim_ceiling":CLAIM})
    write_tsv(out/"STRAIN_LEVEL_SUMMARY.tsv",strain_summary)
    write_tsv(out/"STRAIN_PRODUCT_FAMILY_SUMMARY.tsv",family_summary)
    cards=''.join(f'<a class="card" href="PER_STRAIN/{safe_name(r["strain"])}/REPORT.html"><strong>{html.escape(r["strain"])}</strong><span>{r["bgc_count"]} BGCs · P1 {r["p1_strong_family_hypotheses"]} · P2 {r["p2_supported_family_hypotheses"]} · {r["generic_fragment_flags"]} fragment controls</span><span class="small">Top: {html.escape(r["top_hypothesis"])}</span></a>' for r in strain_summary)
    index=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>All AS Strain-Level BGC Logic</title><style>{style()}</style></head><body><main><h1>All AS strain-level BGC logic</h1><p class="sub">Readable strain reports built from 2,409 complete-identity loci. The product-logic score combines the existing biological evidence score with architecture/reference concordance, boundary controls, and explicit extra penalties for generic PKS or NRPS fragments.</p><div class="metrics"><div class="metric"><b>{len(strain_summary)}</b>strains</div><div class="metric"><b>{len(enhanced)}</b>BGCs</div><div class="metric"><b>{sum(r['p1_strong_family_hypotheses'] for r in strain_summary)}</b>P1 hypotheses</div><div class="metric"><b>{sum(r['p2_supported_family_hypotheses'] for r in strain_summary)}</b>P2 hypotheses</div><div class="metric"><b>{sum(r['generic_fragment_flags'] for r in strain_summary)}</b>fragment controls</div></div><p><a href="CROSS_STRAIN_BGC_COMPARISON.md"><b>Open the cross-strain architecture comparison</b></a> ({len(comparison_rows)} groups present in at least two strains).</p><h2>Browse strains</h2><div class="grid">{cards}</div><h2>Interpretation</h2><p>A score ranks review priority within a strain. Named references remain like-family hypotheses. Architecture-only candidates remain class-level capacity hypotheses. Generic assembly-line fragments on Edge or Full-contig regions are penalized and visibly flagged.</p><p>{CLAIM}</p></main></body></html>'''
    (out/"INDEX.html").write_text(index,encoding="utf-8")
    receipt={"status":"PASS","strains":len(strain_summary),"bgcs":len(enhanced),"genes":len(genes),"markdown_reports":len(strain_summary),"locus_maps":sum(len(top_unit_rows(v)) + sum(len(u)-1 for u in top_unit_rows(v)) for v in by_strain.values()),"cross_strain_groups":len(comparison_rows),"p1":sum(r["p1_strong_family_hypotheses"] for r in strain_summary),"p2":sum(r["p2_supported_family_hypotheses"] for r in strain_summary),"generic_fragment_controls":sum(r["generic_fragment_flags"] for r in strain_summary),"input":str(Path(bgc_path).resolve()),"input_sha256":hashlib.sha256(Path(bgc_path).read_bytes()).hexdigest(),"gene_input":str(Path(gene_path).resolve()) if gene_path else "","gene_input_sha256":hashlib.sha256(Path(gene_path).read_bytes()).hexdigest() if gene_path else "","package_list":str(Path(package_list).resolve()) if package_list else "","package_list_sha256":hashlib.sha256(Path(package_list).read_bytes()).hexdigest() if package_list else "","claim_ceiling":CLAIM}
    (out/"RECEIPT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bgc-workup",required=True); p.add_argument("--gene-ledger"); p.add_argument("--package-list"); p.add_argument("--out",required=True)
    a=p.parse_args(); sys.stdout.write(json.dumps(build(a.bgc_workup,a.out,a.gene_ledger,a.package_list),indent=2) + "\n")


if __name__=="__main__": main()

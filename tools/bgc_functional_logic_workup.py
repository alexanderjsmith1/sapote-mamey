#!/usr/bin/env python3
"""Explain definitive BGC ranks with KCB-blind functional architecture.

The tool preserves direct MIBiG/ClusterBlast matches while separately exposing
unmatched genes whose antiSMASH functions and domains supply core, maturation,
tailoring, transport, regulatory, resistance, or precursor logic.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import os as _os, sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    from mamey.clusterblast_genes import _role_of
    from mamey.architecture_first import architecture_first_assessment
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    from mamey.clusterblast_genes import _role_of
    from mamey.architecture_first import architecture_first_assessment

CLAIM = ("Functional-architecture and reference-similarity workup only; annotations indicate "
         "biosynthetic capacity and pathway logic, not exact product, complete pathway, "
         "expression, production, activity, novelty, physical linkage, or scientific acceptance.")

LOGIC_PATTERNS = (
    ("precursor", (r"precursor", r"leader peptide", r"core peptide", r"bottromycin.*peptide")),
    ("maturation_cyclization", (r"ycao", r"lanc", r"lant_dehydr", r"cyclase", r"cyclization", r"thiopeptide", r"lasso")),
    ("maturation_proteolysis", (r"peptidase", r"protease", r"m16b", r"subtilisin", r"pitrilysin")),
    ("tailoring_methylation", (r"methyltransferase", r"methylation", r"tigr03975")),
    ("tailoring_oxidation", (r"p450", r"oxygenase", r"oxidase", r"oxidoreductase", r"dehydrogenase", r"reductase", r"oxidation")),
    ("tailoring_glycosylation", (r"glycosyltransferase", r"glycos_transf", r"udpgt", r"mgt family")),
    ("tailoring_halogenation", (r"halogenase", r"halogenation")),
    ("tailoring_sugar", (r"degt_dnrj_eryc1", r"rml[abcd]", r"nucleotide.?sugar", r"aminotransferase")),
    ("assembly_line_nrps", (r"amp-binding", r"condensation", r"nrps", r"pp-binding", r"pcp")),
    ("assembly_line_pks", (r"pks_ks", r"ketoacyl", r"acyltransferase", r"t1pks", r"t2pks", r"t3pks", r"ketosynthase")),
    ("core_indolocarbazole", (r"indsynth", r"indolocarbazole", r"sta[dop]", r"reb[cdop]")),
    ("core_siderophore", (r"iuca_iucc", r"siderophore", r"iron.*chelat")),
    ("core_terpene", (r"terpene", r"phytoene", r"squalene", r"polyprenyl")),
    ("core_other", (r"biosynthetic \(rule-based-clusters\)", r"\bbiosynthetic\b")),
    ("transport", (r"transporter", r"permease", r"efflux", r"abc_tran", r"major facilitator", r"\bmfs\b")),
    ("regulatory", (r"regulator", r"response_reg", r"transcription", r"\bsarp\b", r"\btetr\b", r"\bluxr\b", r"\bmarr\b")),
    ("resistance", (r"resistance", r"immunity", r"self-protection")),
)


def number(value, default=0.0):
    try: return float(value)
    except (TypeError, ValueError): return default


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()


def read_rows(path):
    path=Path(path); delim="\t" if path.suffix.lower()==".tsv" else ","
    with path.open(newline="",errors="replace") as f: return list(csv.DictReader(f,delimiter=delim))


def write_tsv(path, rows, fields=None):
    rows=list(rows); fields=fields or (list(rows[0]) if rows else [])
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open("w",newline="") as f:
        w=_SafeDictWriter(f,fieldnames=fields,delimiter="\t",extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def one_file(package, suffix):
    hits=sorted(Path(package).glob(f"*{suffix}"))
    if len(hits)!=1: raise ValueError(f"{package}: expected one *{suffix}; found {len(hits)}")
    return hits[0]


def package_inputs(package):
    package=Path(package).resolve()
    manifest=package/"manifest.json"
    if not manifest.is_file(): raise ValueError(f"{package}: manifest.json required")
    return {"package":package,"manifest":manifest,"cds":one_file(package,"_cds_table.csv"),
            "hits":one_file(package,"_3_mibig_per_gene.csv"),"inventory":one_file(package,"_2_inventory.csv")}


def discover_packages(values, package_list=None, root=None):
    found=[Path(v).expanduser().resolve() for v in values or []]
    if package_list:
        with Path(package_list).open() as f:
            found.extend(Path(line.strip()).expanduser().resolve() for line in f if line.strip() and not line.startswith("#"))
    if root:
        for p in Path(root).expanduser().resolve().rglob("*_cds_table.csv"):
            if (p.parent/"manifest.json").is_file(): found.append(p.parent)
    unique=[]; seen=set()
    for p in found:
        if p not in seen: seen.add(p); unique.append(p)
    if not unique: raise ValueError("provide --package, --package-list, or --packages-root")
    return unique


def read_aliases(path):
    if not path: return {}
    out={}
    for r in read_rows(path):
        if not r.get("source_strain") or not r.get("display_strain"): raise ValueError("alias table requires source_strain,display_strain")
        out[r["source_strain"]]=r["display_strain"]
    return out


def norm_accession(value): return re.sub(r"\.\d+$","",(value or "").strip())


def gene_kind(row):
    text=(row.get("gene_functions") or row.get("product") or "").lower()
    if "biosynthetic-additional" in text: return "biosynthetic-additional"
    for kind in ("biosynthetic","transport","regulatory","resistance","other"):
        if re.search(rf"\b{kind}\b",text): return kind
    return ""


def logic_tags(row):
    blob=" ".join([row.get("product","") or "",row.get("gene_functions","") or "",row.get("sec_met_domains","") or ""]).lower()
    tags=[]
    for label,patterns in LOGIC_PATTERNS:
        if any(re.search(p,blob,re.I) for p in patterns): tags.append(label)
    return tags


def primary_role(row, tags):
    blob=" ".join([row.get("product","") or "",row.get("gene_functions","") or "",row.get("sec_met_domains","") or ""])
    broad=_role_of(gene_kind(row),blob)
    if "precursor" in tags: return "precursor"
    if any(t.startswith("maturation_") for t in tags): return "maturation"
    if any(t.startswith("tailoring_") for t in tags): return "tailoring"
    if any(t.startswith("assembly_line_") or (t.startswith("core_") and t!="core_other") for t in tags): return "core"
    if "resistance" in tags: return "resistance"
    if broad in {"core","tailoring","transport","regulatory"}: return broad
    return "other"


def identity(strain,row):
    vals=[strain,row.get("contig",""),row.get("region",""),row.get("bgc_id","")]
    if not all(vals): raise ValueError(f"incomplete BGC identity: {vals}")
    return " / ".join(vals)


def relation_label(arch_type, arch_conf, concordance, reference, unmatched_logic):
    if concordance=="concordant":
        return "ARCHITECTURE_CORROBORATES_REFERENCE"
    if concordance=="discordant":
        return "ARCHITECTURE_REFERENCE_DISCORDANT"
    if concordance=="architecture_defers":
        return "ARCHITECTURE_UNRESOLVED_REFERENCE_DOMINANT"
    if arch_type!="unknown" and reference:
        return "ARCHITECTURE_EXTENDS_WEAK_REFERENCE" if unmatched_logic else "ARCHITECTURE_SUPPORT_PRESENT"
    if arch_type!="unknown" and not reference:
        return "ARCHITECTURE_ONLY_NO_REFERENCE_MATCH"
    if reference:
        return "REFERENCE_MATCH_ARCHITECTURE_UNRESOLVED"
    return "BOTH_CHANNELS_UNRESOLVED"


def analyze(packages, definitive_rank, out, aliases=None):
    aliases=aliases or {}; out=Path(out).expanduser().resolve(); out.mkdir(parents=True,exist_ok=True)
    ranks={r["complete_identity"]:r for r in read_rows(definitive_rank)}
    genes_out=[]; bgcs_out=[]; sources=[]; source_strains=[]
    for package in packages:
        inp=package_inputs(package); cds=read_rows(inp["cds"]); hits=read_rows(inp["hits"]); inventory=read_rows(inp["inventory"])
        if not cds: raise ValueError(f"{package}: empty CDS table")
        source_strains.append(cds[0].get("strain",""))
        strain=aliases.get(source_strains[-1],source_strains[-1])
        for role in ("manifest","cds","hits","inventory"):
            p=inp[role]; sources.append({"package":str(package),"role":role,"path":str(p),"sha256":sha256(p),"bytes":p.stat().st_size})
        by_bgc=defaultdict(list); hits_by=defaultdict(list)
        for r in cds: by_bgc[r.get("bgc_id","")].append(r)
        for r in hits: hits_by[(r.get("bgc_id",""),r.get("query_gene",""))].append(r)
        inv={r.get("BGC_ID",""):r for r in inventory}
        for bgc,rows in by_bgc.items():
            ident=identity(strain,rows[0]); rank=ranks.get(ident)
            if not rank: raise ValueError(f"definitive rank missing {ident}")
            dominant=norm_accession(rank.get("dominant_mibig_accession"))
            role_counts=Counter(); unmatched_counts=Counter(); no_hit_counts=Counter(); tag_counts=Counter(); current=[]
            unmatched_ids=defaultdict(list); no_hit_ids=defaultdict(list)
            for r in sorted(rows,key=lambda x:number(x.get("order"))):
                tags=logic_tags(r); role=primary_role(r,tags); role_counts[role]+=1; tag_counts.update(tags)
                ghits=hits_by.get((bgc,r.get("locus_tag","")),[])
                domhits=[h for h in ghits if norm_accession(h.get("mibig_accession"))==dominant]
                any_match=bool(ghits); dom_match=bool(domhits)
                if not dom_match and role!="other":
                    unmatched_counts[role]+=1; unmatched_ids[role].append(r.get("locus_tag",""))
                if not any_match and role!="other":
                    no_hit_counts[role]+=1; no_hit_ids[role].append(r.get("locus_tag",""))
                best=max(domhits,key=lambda h:number(h.get("blast_score"))) if domhits else None
                grow={
                    "complete_identity":ident,"definitive_rank_all_bgcs":rank.get("definitive_rank_all_bgcs",""),
                    "strain":strain,"bgc_alias":bgc,"gene_order":r.get("order",""),
                    "query_gene":r.get("locus_tag",""),"aa_length":r.get("length_aa",""),"primary_functional_role":role,
                    "functional_logic_tags":"; ".join(tags),"gene_kind":gene_kind(r),"product_annotation":r.get("product",""),
                    "sec_met_domains":r.get("sec_met_domains",""),"gene_functions":r.get("gene_functions",""),
                    "any_mibig_gene_match":"YES" if any_match else "NO","dominant_reference_gene_match":"YES" if dom_match else "NO",
                    "dominant_mibig_accession":dominant,"matched_subject_gene":best.get("subject_gene","") if best else "",
                    "matched_pct_identity":best.get("pct_identity","") if best else "","matched_pct_coverage":best.get("pct_coverage_interpretation",best.get("pct_coverage","")) if best else "",
                    "functional_logic_without_dominant_match":"YES" if (not dom_match and role!="other") else "NO","claim_ceiling":CLAIM,
                }
                genes_out.append(grow); current.append(grow)
            # KCB-blind architecture uses antiSMASH domain/function text, but no hit data.
            arch_genes=[]
            for r in rows:
                augmented="; ".join(filter(None,[r.get("sec_met_domains",""),r.get("product",""),r.get("gene_functions","")]))
                arch_genes.append({"locus_tag":r.get("locus_tag",""),"aa_length":r.get("length_aa",0),"sec_met_domains":augmented})
            arch,concord,assignment=architecture_first_assessment(
                arch_genes,boundary_status=inv.get(bgc,{}).get("Boundary","") or "Interior",
                kcb_compound=rank.get("dominant_mibig_product",""),
                kcb_n_genes=int(number(rank.get("matched_gene_pairs"))),kcb_mibig_class="")
            unmatched_total=sum(unmatched_counts.values())
            no_hit_total=sum(no_hit_counts.values())
            relation=relation_label(arch.pathway_type.value,arch.confidence,concord.concordance.value,dominant,unmatched_total)
            unmatched_breakdown=", ".join(f"{k}={v}" for k,v in sorted(unmatched_counts.items()) if v) or "none"
            no_hit_breakdown=", ".join(f"{k}={v}" for k,v in sorted(no_hit_counts.items()) if v) or "none"
            functional_summary=(f"KCB-blind architecture: {arch.pathway_type.value} ({arch.confidence}). "
                                f"Dominant-reference matches: {sum(g['dominant_reference_gene_match']=='YES' for g in current)}/{len(rows)} CDS. "
                                f"Functional genes outside the dominant reference: {unmatched_total} ({unmatched_breakdown}). "
                                f"Functional genes with no admitted MIBiG match: {no_hit_total} ({no_hit_breakdown}). "
                                f"Channel relationship: {relation}.")
            if relation=="ARCHITECTURE_REFERENCE_DISCORDANT":
                review_question="Which exact domain-bearing genes drive the architecture/reference conflict, and does gene order support the architecture-first class?"
            elif relation in {"ARCHITECTURE_EXTENDS_WEAK_REFERENCE","ARCHITECTURE_SUPPORT_PRESENT"}:
                review_question="Do the unmatched functional genes form a coherent missing core, maturation, or tailoring arm, and is that arm boundary-complete?"
            elif relation=="ARCHITECTURE_ONLY_NO_REFERENCE_MATCH":
                review_question="Can profile-HMM, curated ortholog, or synteny evidence bind the architecture-only genes to a characterized pathway family?"
            elif "UNRESOLVED" in relation:
                review_question="Which unclassified or weakly annotated genes require profile-HMM or manual domain review to resolve the local architecture?"
            else:
                review_question="Does the corroborated architecture recover the expected essential core and boundary-complete gene order, and what experiment distinguishes exact products?"
            logic_density=sum(role_counts[x] for x in ("core","precursor","maturation","tailoring","transport","regulatory","resistance"))/max(1,len(rows))
            bgcs_out.append({
                "complete_identity":ident,"definitive_rank_all_bgcs":rank.get("definitive_rank_all_bgcs",""),
                "definitive_rank_within_strain":rank.get("definitive_rank_within_strain",""),"evidence_tier":rank.get("evidence_tier",""),
                "standalone_biological_evidence_score_0_100":rank.get("standalone_biological_evidence_score_0_100",""),
                "review_priority_score_0_100":rank.get("review_priority_score_0_100",""),"current_antismash_products":rank.get("current_antismash_products",""),
                "boundary":rank.get("boundary",""),"dominant_mibig_accession":dominant,"dominant_mibig_product":rank.get("dominant_mibig_product",""),
                "architecture_first_pathway_type":arch.pathway_type.value,"architecture_first_confidence":arch.confidence,
                "architecture_first_raw_confidence":arch.confidence_raw,"architecture_reasoning":arch.reasoning,
                "architecture_diagnostic_markers":"; ".join(arch.diagnostic_markers),"architecture_reference_concordance":concord.concordance.value,
                "concordance_conflict_detail":concord.conflict_detail,"final_architecture_assignment":assignment.product_class,
                "final_assignment_source":assignment.source,"final_assignment_confidence":assignment.confidence,
                "functional_reference_relation":relation,"total_cds":len(rows),"genes_with_any_mibig_match":sum(g["any_mibig_gene_match"]=="YES" for g in current),
                "genes_matching_dominant_reference":sum(g["dominant_reference_gene_match"]=="YES" for g in current),
                "functional_genes_without_dominant_match":unmatched_total,"functional_logic_density":round(logic_density,4),
                "functional_genes_without_any_mibig_match":no_hit_total,
                "core_genes":role_counts["core"],"precursor_genes":role_counts["precursor"],"maturation_genes":role_counts["maturation"],
                "tailoring_genes":role_counts["tailoring"],"transport_genes":role_counts["transport"],"regulatory_genes":role_counts["regulatory"],
                "resistance_genes":role_counts["resistance"],"other_genes":role_counts["other"],
                "unmatched_core_genes":unmatched_counts["core"],"unmatched_precursor_genes":unmatched_counts["precursor"],
                "unmatched_maturation_genes":unmatched_counts["maturation"],"unmatched_tailoring_genes":unmatched_counts["tailoring"],
                "unmatched_transport_genes":unmatched_counts["transport"],"unmatched_regulatory_genes":unmatched_counts["regulatory"],
                "unmatched_resistance_genes":unmatched_counts["resistance"],
                "no_mibig_hit_core_genes":no_hit_counts["core"],"no_mibig_hit_precursor_genes":no_hit_counts["precursor"],
                "no_mibig_hit_maturation_genes":no_hit_counts["maturation"],"no_mibig_hit_tailoring_genes":no_hit_counts["tailoring"],
                "no_mibig_hit_transport_genes":no_hit_counts["transport"],"no_mibig_hit_regulatory_genes":no_hit_counts["regulatory"],
                "no_mibig_hit_resistance_genes":no_hit_counts["resistance"],
                "unmatched_core_gene_ids":"; ".join(unmatched_ids["core"]),"unmatched_precursor_gene_ids":"; ".join(unmatched_ids["precursor"]),
                "unmatched_maturation_gene_ids":"; ".join(unmatched_ids["maturation"]),"unmatched_tailoring_gene_ids":"; ".join(unmatched_ids["tailoring"]),
                "unmatched_transport_gene_ids":"; ".join(unmatched_ids["transport"]),"unmatched_regulatory_gene_ids":"; ".join(unmatched_ids["regulatory"]),
                "unmatched_resistance_gene_ids":"; ".join(unmatched_ids["resistance"]),
                "no_mibig_hit_functional_gene_ids":"; ".join(g for role in sorted(no_hit_ids) for g in no_hit_ids[role]),
                "functional_logic_summary":functional_summary,"decisive_review_question":review_question,
                "functional_logic_tags":"; ".join(sorted(tag_counts)),"rggmci_partner_identity":rank.get("rggmci_partner_identity",""),
                "rggmci_confidence":rank.get("rggmci_confidence",""),"rggmci_subject_tiling_verdict":rank.get("rggmci_subject_tiling_verdict",""),
                "claim_ceiling":CLAIM,
            })
    duplicates=sorted({s for s in source_strains if source_strains.count(s)>1})
    if duplicates: raise ValueError("multiple packages for source strain(s): "+", ".join(duplicates))
    if len(bgcs_out)!=len(ranks): raise ValueError(f"coverage mismatch: workup {len(bgcs_out)} vs rank {len(ranks)}")
    bgcs_out.sort(key=lambda r:number(r["definitive_rank_all_bgcs"]))
    genes_out.sort(key=lambda r:(number(r.get("definitive_rank_all_bgcs",10**9)),r["complete_identity"],number(r["gene_order"])))
    nondominant=[r for r in genes_out if r["functional_logic_without_dominant_match"]=="YES"]
    unmatched=[r for r in nondominant if r["any_mibig_gene_match"]=="NO"]
    summary=[]
    for relation,count in sorted(Counter(r["functional_reference_relation"] for r in bgcs_out).items(),key=lambda x:(-x[1],x[0])):
        subset=[r for r in bgcs_out if r["functional_reference_relation"]==relation]
        summary.append({"functional_reference_relation":relation,"bgc_count":count,"strain_count":len({r["complete_identity"].split(" / ",1)[0] for r in subset}),
                        "functional_genes_without_dominant_match":sum(int(r["functional_genes_without_dominant_match"]) for r in subset),"claim_ceiling":CLAIM})
    write_tsv(out/"ALL_BGC_FUNCTIONAL_LOGIC_WORKUP.tsv",bgcs_out)
    write_tsv(out/"ALL_GENE_FUNCTIONAL_EVIDENCE.tsv",genes_out)
    write_tsv(out/"NO_MIBIG_MATCH_FUNCTIONAL_GENES.tsv",unmatched)
    write_tsv(out/"NONDOMINANT_REFERENCE_FUNCTIONAL_GENES.tsv",nondominant)
    write_tsv(out/"FUNCTIONAL_REFERENCE_RELATION_SUMMARY.tsv",summary)
    write_tsv(out/"SOURCE_HASHES.tsv",sources)
    for strain in sorted({r["complete_identity"].split(" / ",1)[0] for r in bgcs_out}):
        folder=out/"PER_STRAIN"/re.sub(r"[^A-Za-z0-9._-]+","_",strain)
        write_tsv(folder/"BGC_FUNCTIONAL_LOGIC_WORKUP.tsv",[r for r in bgcs_out if r["complete_identity"].startswith(strain+" / ")])
        write_tsv(folder/"GENE_FUNCTIONAL_EVIDENCE.tsv",[r for r in genes_out if r["strain"]==strain])
        write_tsv(folder/"NO_MIBIG_MATCH_FUNCTIONAL_GENES.tsv",[r for r in unmatched if r["strain"]==strain])
        write_tsv(folder/"NONDOMINANT_REFERENCE_FUNCTIONAL_GENES.tsv",[r for r in nondominant if r["strain"]==strain])
    receipt={"schema":"bgc-functional-logic-workup-v1","status":"COMPLETE","packages":len(packages),"strains":len(set(source_strains)),
             "bgcs":len(bgcs_out),"genes":len(genes_out),"functional_genes_without_any_mibig_match":len(unmatched),
             "functional_genes_without_dominant_reference_match":len(nondominant),
             "relations":dict(Counter(r["functional_reference_relation"] for r in bgcs_out)),"claim_ceiling":CLAIM}
    (out/"RECEIPT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return receipt


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package",action="append",default=[]); p.add_argument("--package-list"); p.add_argument("--packages-root")
    p.add_argument("--definitive-rank",required=True); p.add_argument("--strain-aliases"); p.add_argument("--out",required=True)
    return p


def main(argv=None):
    a=parser().parse_args(argv)
    receipt=analyze(discover_packages(a.package,a.package_list,a.packages_root),a.definitive_rank,a.out,read_aliases(a.strain_aliases))
    _sys.stdout.write(json.dumps(receipt,sort_keys=True) + "\n"); return 0


if __name__=="__main__": raise SystemExit(main())

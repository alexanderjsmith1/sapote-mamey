"""
Rare-motif BGC detection — cross-strain.

The main discovery mode: rather than detecting known capability classes, flag BGCs
carrying domains that are RARE across the strain set. A motif in 1-2 BGCs genome-wide
is more likely to mark novel/interesting chemistry than one in 50.

    ranked = rare_motif_scan(strain_dirs, rarity_threshold=2)
    -> list of (region, [rare domains]) ranked by count of rare motifs.

Also supports "important motif" mode: supply a watchlist of high-value domains
(phosphonate, enediyne, azoxy, lasso RRE, etc.) and flag any BGC carrying them
regardless of frequency.
"""
import glob
from Bio import SeqIO
from collections import defaultdict

# Curated high-value motifs (rare + bioactively interesting) — the "important" watchlist
IMPORTANT_MOTIFS = {
    "phosphonates": "phosphonate (fosfomycin-class)",
    "phosphonates-like": "phosphonate (fosfomycin-class)",
    "PEP_mutase": "phosphonate (fosfomycin-class)",
    "vlmB": "azoxy crosslink (valanimycin-type)",
    "azdO": "azoxy crosslink (valanimycin-type)",
    "Cyanobactin_D_RRE": "azole RiPP (thiopeptide-adjacent)",
    "Goadsporin_CD_RRE": "azole RiPP (thiopeptide-adjacent)",
    "NHLP_CD_RRE": "azole RiPP (thiopeptide-adjacent)",
    "TIGR03604": "azole RiPP (thiopeptide-adjacent)",
    "Stand_Alone_Lasso_RRE": "lasso peptide",
    "Lasso_Lariat": "lasso peptide",
    "ene_KS": "enediyne warhead PKSE",
    "DHQ_synthase": "aminocyclitol (acarbose-class)",
    "t2ks": "type-II aromatic PKS",
    "t2clf": "type-II aromatic PKS",
    "pgm_amidino": "guanidine RiPP",
    "pgm1": "guanidine RiPP",
    "AurF": "nitro/aureothin-type",
}

def _region_domains(gbk):
    doms=set(); prod=None
    for rec in SeqIO.parse(gbk,"genbank"):
        for ft in rec.features:
            if ft.type=="region": prod=";".join(ft.qualifiers.get("product",[]))
            if ft.type=="CDS":
                for d in ft.qualifiers.get("sec_met_domain",[]):
                    doms.add(str(d).split(" ")[0])
    return doms, prod

def rare_motif_scan(strain_dirs, rarity_threshold=2):
    domain_count=defaultdict(int); region_domains={}; region_meta={}
    for sd in strain_dirs:
        sname=sd.rstrip("/").split("/")[-1]
        for f in glob.glob(f"{sd}/**/*.region*.gbk", recursive=True):
            if "MACOSX" in f: continue
            rid=f"{sname}:{f.split('/')[-1].replace('.gbk','')}"
            doms,prod=_region_domains(f)
            region_domains[rid]=doms; region_meta[rid]=prod
            for d in doms: domain_count[d]+=1
    rare={d for d,n in domain_count.items() if n<=rarity_threshold}
    ranked=[]
    for rid,doms in region_domains.items():
        rare_here=sorted(doms & rare)
        important_here=sorted(doms & set(IMPORTANT_MOTIFS))
        if rare_here or important_here:
            ranked.append({"region":rid,"product":region_meta[rid],
                           "rare_motifs":rare_here,"important_motifs":important_here,
                           "score":len(rare_here)+2*len(important_here)})
    ranked.sort(key=lambda x:-x["score"])
    return ranked, dict(domain_count)

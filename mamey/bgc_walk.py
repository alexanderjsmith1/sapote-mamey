"""
BGC domain walk — ordered HMM readout along a biosynthetic gene cluster.

For each gene in a BGC (in genomic order), lists every HMM hit in domain order,
revealing the assembly-line architecture and — critically — RARE or unexpected
domains that flag interesting chemistry. This is the per-BGC view; cluster-level
gate counts discard the ordering that makes a domain interesting.

Usage:
    genes, hits = bgc_walk("region.gbk", hmm_file="scanner_pfam_150.hmm")
    render_walk(genes, hits)                 # text
    walk_svg(genes, hits, "out.svg")         # visual track
"""
import pyhmmer
from pyhmmer.easel import Alphabet, TextSequence, DigitalSequenceBlock
from Bio import SeqIO
abc=Alphabet.amino()

def bgc_walk(gbk, hmm_file):
    rec=next(SeqIO.parse(gbk,"genbank"))
    genes=[]
    for f in rec.features:
        if f.type=="CDS":
            tr=f.qualifiers.get("translation",[""])[0]
            if tr:
                genes.append({"lt":f.qualifiers.get("locus_tag",["?"])[0],
                    "start":int(f.location.start),"end":int(f.location.end),
                    "strand":f.location.strand,"seq":tr,
                    "as_dom":[str(d).split(" ")[0] for d in f.qualifiers.get("sec_met_domain",[])]})
    genes.sort(key=lambda g:g["start"])
    seqs=[TextSequence(name=g["lt"].encode(),sequence=g["seq"]).digitize(abc) for g in genes]
    block=DigitalSequenceBlock(abc,seqs)
    hits_by_gene={}
    with pyhmmer.plan7.HMMFile(hmm_file) as hf:
        for hmm in hf:
            nm=hmm.name.decode() if isinstance(hmm.name,bytes) else hmm.name
            for th in pyhmmer.hmmer.hmmsearch([hmm],block,cpus=4,bit_cutoffs="gathering"):
                for h in th:
                    if h.included:
                        gid=h.name.decode() if isinstance(h.name,bytes) else h.name
                        for dom in h.domains:
                            if dom.included:
                                hits_by_gene.setdefault(gid,[]).append(
                                    (dom.alignment.target_from, nm, round(dom.score,1)))
    for gid in hits_by_gene: hits_by_gene[gid].sort()
    return genes, hits_by_gene

def render_walk(genes, hits, rare_domains=None):
    rare_domains=rare_domains or set()
    lines=[]
    for g in genes:
        hh=hits.get(g["lt"],[])
        if not hh: continue
        parts=[]
        for pos,nm,sc in hh:
            tag=f"*{nm}*" if nm in rare_domains else nm
            parts.append(tag)
        lines.append(f"{g['lt']:14} ({len(g['seq']):4}aa)[{g['strand']:+d}]  "+" -> ".join(parts))
    return "\n".join(lines)

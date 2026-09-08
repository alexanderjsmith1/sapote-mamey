"""Real pyHMMER scanner engine: builds HMMs from discriminating domains, searches proteomes."""
import pyhmmer, glob, json
from pyhmmer.easel import Alphabet, TextSequence, DigitalSequenceBlock, TextMSA, DigitalMSA
from pyhmmer.plan7 import Builder, Background
from Bio import SeqIO
abc = Alphabet.amino()

def proteome(strain_dir):
    """Extract all CDS proteins from a strain's antiSMASH region gbks."""
    seqs=[]
    for f in glob.glob(f"{strain_dir}/**/*.region*.gbk", recursive=True):
        if "MACOSX" in f: continue
        contig=f.split("/")[-1].split(".region")[0]
        for rec in SeqIO.parse(f,"genbank"):
            for feat in rec.features:
                if feat.type=="CDS":
                    tr=feat.qualifiers.get("translation",[""])[0]
                    lt=feat.qualifiers.get("locus_tag",["?"])[0]
                    if tr and len(tr)>=40:
                        name=f"{contig}|{lt}".encode()
                        seqs.append(TextSequence(name=name, sequence=tr).digitize(abc))
    return DigitalSequenceBlock(abc, seqs)

def collect_domain_seqs(strain_dirs, domain_key, max_seqs=15):
    """Gather protein seqs where antiSMASH flagged a given sec_met domain — training set for an HMM."""
    hits=[]
    for sd in strain_dirs:
        for f in glob.glob(f"{sd}/**/*.region*.gbk", recursive=True):
            if "MACOSX" in f: continue
            for rec in SeqIO.parse(f,"genbank"):
                for feat in rec.features:
                    if feat.type=="CDS":
                        dm=str(feat.qualifiers.get("sec_met_domain",[]))
                        if domain_key in dm:
                            tr=feat.qualifiers.get("translation",[""])[0]
                            if tr and len(tr)>=40: hits.append(tr)
        if len(hits)>=max_seqs: break
    return hits[:max_seqs]

def build_hmm_from_seqs(seqs, name):
    """Build an HMM from unaligned seqs via single-sequence builder (or MSA if multiple)."""
    builder=Builder(abc); bg=Background(abc)
    if len(seqs)==1:
        ts=TextSequence(name=name.encode(), sequence=seqs[0]).digitize(abc)
        hmm,_,_=builder.build(ts, bg)
        return hmm
    # align with pyfamsa then build
    from pyfamsa import Aligner, Sequence
    aln=Aligner(guide_tree="upgma").align([Sequence(f"s{i}".encode(), s.encode()) for i,s in enumerate(seqs)])
    msa=TextMSA(name=name.encode(), sequences=[TextSequence(name=f"s{i}".encode(), sequence=s.sequence.decode() if isinstance(s.sequence,bytes) else s.sequence) for i,s in enumerate(aln)])
    hmm,_,_=builder.build_msa(msa.digitize(abc), bg)
    return hmm

if __name__=="__main__":
    print("pyHMMER scanner engine loaded")

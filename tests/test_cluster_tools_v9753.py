"""Tests for the gene_topology.py and cluster_alignment.py figure tools (v9.7.53).

Uses synthetic antiSMASH-style fixtures (no unpublished data) so the tests are
hermetic and leak-safe. Verifies: knownclusterblast+clusterblast parsing, the
multi-source contig-rescue aggregation (all references, both methods, not just the
top hit), class-token resolution incl. the explicit override, and that each tool
emits its PNG + CSV deliverables.
"""
import os, csv, json, subprocess, sys, tempfile, importlib.util
import pytest

HERE=os.path.dirname(__file__)
ROOT=os.path.dirname(HERE)
TOOLS=os.path.join(ROOT,"tools")

def _load(modname, path):
    spec=importlib.util.spec_from_file_location(modname, path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

# ---- synthetic fixtures ----
KCB = """ClusterBlast scores for NODE_1_length_9000_cov_50.0

Table of genes, locations, strands and annotations of query cluster:
ctg1_1\t2\t900\t-\t\t
ctg1_2\t950\t1800\t-\t\t
ctg1_3\t1850\t2700\t-\t\t


Significant hits: 
1. BGC0000469.6\tbottromycin A2
2. BGC0001157.6\tbottromycin A2


Details:

>>
1. BGC0000469.6
Source: bottromycin A2
Type: ribosomal:RiPP:Bottromycin
Number of proteins with BLAST hits to this cluster: 3
Cumulative BLAST score: 1500.0

Table of genes, locations, strands and annotations of subject cluster:

Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg1_1\tAFV25484.1\t78\t980\t99.0\t0.0
ctg1_2\tAFV25483.1\t77\t549\t100.0\t2e-197
ctg1_3\tAFV25482.1\t59\t440\t104.0\t2e-153



>>
2. BGC0001157.6
Source: bottromycin A2
Type: ribosomal:RiPP:Bottromycin
Number of proteins with BLAST hits to this cluster: 2
Cumulative BLAST score: 900.0

Table of genes, locations, strands and annotations of subject cluster:

Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg1_1\tSCAB_1\t70\t400\t97.0\t1e-140
ctg1_2\tSCAB_2\t74\t500\t93.0\t1e-160
"""

CB = """ClusterBlast scores for NODE_1_length_9000_cov_50.0

Table of genes, locations, strands and annotations of query cluster:
ctg1_1\t2\t900\t-\t\t


Significant hits: 
1. NZ_KB913030\tStreptomyces purpureus KA281, bottromycin region


Details:

>>
1. NZ_KB913030
Source: Streptomyces purpureus KA281
Type: bottromycin
Number of proteins with BLAST hits to this cluster: 1
Cumulative BLAST score: 400.0

Table of genes, locations, strands and annotations of subject cluster:

Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg1_1\tSpur_1\t68\t410\t98.0\t1e-141
"""

def _write(d, name, txt):
    p=os.path.join(d,name); open(p,"w").write(txt); return p

def test_cluster_alignment_parses_all_refs_both_methods(tmp_path):
    ca=_load("cluster_alignment", os.path.join(TOOLS,"cluster_alignment.py"))
    d=str(tmp_path)
    kcb=_write(d,"kcb.txt",KCB); cb=_write(d,"cb.txt",CB)
    genes,best,support = ca.collect_hits(kcb, cb, "BGC0000469")
    # best per-gene hits to the named MIBiG ref (3 genes)
    assert set(best.keys())=={"ctg1_1","ctg1_2","ctg1_3"}
    assert best["ctg1_1"]["s"]=="AFV25484.1" and best["ctg1_1"]["id"]==78
    # multi-source: BOTH methods counted, all refs (not just the top hit)
    assert support["kcb_refs"]==2          # two MIBiG blocks parsed
    assert support["cb_refs"]==1           # one genome-neighbour block parsed
    assert support["class_token"]=="bottromycin"   # specific class beats generic 'ripp'
    assert support["kcb_class_refs"]==2 and support["cb_class_refs"]==1

def test_class_token_override(tmp_path):
    ca=_load("cluster_alignment", os.path.join(TOOLS,"cluster_alignment.py"))
    d=str(tmp_path)
    # a ref whose Type is uninformative ('other:other') needs the override
    kcb=KCB.replace("ribosomal:RiPP:Bottromycin","other:other").replace("bottromycin A2","AT2433-A1")
    kp=_write(d,"k2.txt",kcb)
    genes,best,support = ca.collect_hits(kp, None, "BGC0000469", class_override="indolocarbazole")
    assert support["class_token"]=="indolocarbazole"

def test_cluster_alignment_emits_outputs(tmp_path):
    d=str(tmp_path)
    kcb=_write(d,"kcb.txt",KCB); cb=_write(d,"cb.txt",CB)
    # minimal GBK for role lookup
    gbk=_write(d,"r.gbk",_MINI_GBK)
    out=os.path.join(d,"fig")
    r=subprocess.run([sys.executable, os.path.join(TOOLS,"cluster_alignment.py"),
        "--kcb",kcb,"--cb",cb,"--gbk",gbk,"--ref","BGC0000469","--ref-label","bottromycin A2",
        "--out",out], capture_output=True, text=True)
    assert r.returncode==0, r.stderr
    assert os.path.exists(out+".png")
    assert os.path.exists(out+"_data.csv")
    assert os.path.exists(out+"_support.csv")
    rows=list(csv.DictReader(open(out+"_data.csv")))
    assert any(row["ref_gene"]=="AFV25484.1" for row in rows)

def test_gene_topology_emits_outputs(tmp_path):
    d=str(tmp_path)
    gbk=_write(d,"r.gbk",_MINI_GBK)
    out=os.path.join(d,"topo")
    r=subprocess.run([sys.executable, os.path.join(TOOLS,"gene_topology.py"),
        "--gbk",gbk,"--title","t","--out",out], capture_output=True, text=True)
    assert r.returncode==0, r.stderr
    assert os.path.exists(out+".png")
    assert os.path.exists(out+"_data.csv")

_MINI_GBK = """LOCUS       NODE_1                  9000 bp    DNA     linear   BCT 01-JAN-2026
FEATURES             Location/Qualifiers
     source          1..9000
     CDS             complement(2..900)
                     /locus_tag="ctg1_1"
                     /gene_functions="biosynthetic (rule-based-clusters) RiPP-like: YcaO"
     CDS             complement(950..1800)
                     /locus_tag="ctg1_2"
                     /gene_functions="biosynthetic-additional (rule-based-clusters) p450"
     CDS             complement(1850..2700)
                     /locus_tag="ctg1_3"
                     /gene_functions="regulatory (smcogs) SMCOG1215: TetR"
ORIGIN
//
"""


def test_figures_split_selection_logic():
    """figures_split must: require HIGH confidence, same MIBiG anchor, non-ubiquitous class."""
    import importlib.util
    spec=importlib.util.spec_from_file_location("figures_split",
        os.path.join(ROOT,"mamey","figures_split.py"))
    fs=importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
    # _mibig_class extracts accession + class
    acc,cls=fs._mibig_class("BGC0000469.6 | bottromycin A2 | knownclusterblast #1")
    assert acc=="BGC0000469" and cls=="bottromycin"
    # ubiquitous classes are excluded from auto-figuring
    assert "ectoine" in fs.UBIQUITOUS and "siderophore" in fs.UBIQUITOUS
    assert "saccharide" in fs.UBIQUITOUS and "lanthipeptide" in fs.UBIQUITOUS
    assert "bottromycin" not in fs.UBIQUITOUS and "indolocarbazole" not in fs.UBIQUITOUS
    # _stem normalises a contig name to its NODE id
    assert fs._stem("NODE_69_length_9799_cov_77.372660")=="NODE_69"
    # _find_raw_run returns None when no co-located run with region GBKs exists
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        assert fs._find_raw_run(d) is None


def test_topology_scan_inverted_block(tmp_path):
    """topology_scan must detect the +/-/+ INVERTED_BLOCK pattern, flag unannotated genes,
       detect TTA codons and contig-edge truncation, and export bare proteins to FASTA."""
    import importlib.util, csv
    spec=importlib.util.spec_from_file_location("topology_scan",
        os.path.join(TOOLS,"topology_scan.py"))
    ts=importlib.util.module_from_spec(spec); spec.loader.exec_module(ts)
    # classify_runs: tripartite same-flank/-opposite-core/same-flank = INVERTED_BLOCK
    kind,pat,runs = ts.classify_runs([1,1,-1,-1,-1,1])
    assert kind=="INVERTED_BLOCK" and pat=="+x2/-x3/+x1"
    assert ts.classify_runs([1,1,1])[0]=="CO_DIRECTIONAL"
    assert ts.classify_runs([1,1,-1])[0]=="SINGLE_FLIP"
    assert ts.classify_runs([1,-1,1,-1])[0]=="COMPLEX"
    # has_tta: a TTA leucine codon on the coding strand
    assert ts.has_tta("ATGTTATAA", 1) is True
    assert ts.has_tta("ATGAAATAA", 1) is False
    # has_tta is defensive: undefined/empty sequence -> False (not a crash)
    assert ts.has_tta("", 1) is False

    # end-to-end on a synthetic inverted-block GBK
    gbk=os.path.join(str(tmp_path),"inv.gbk")
    open(gbk,"w").write(_INV_GBK)
    out=os.path.join(str(tmp_path),"scan")
    import subprocess, sys
    r=subprocess.run([sys.executable, os.path.join(TOOLS,"topology_scan.py"),
        "--gbk",gbk,"--out",out], capture_output=True, text=True)
    assert r.returncode==0, r.stderr
    assert os.path.exists(out+"_topology.csv")
    assert os.path.exists(out+"_unannotated.faa")
    summ=json.load(open(out+"_summary.json"))
    assert summ[0]["topology"]=="INVERTED_BLOCK"
    assert "ctgX_2" in summ[0]["unannotated_loci"]   # the bare gene
    # bare protein exported
    faa=open(out+"_unannotated.faa").read()
    assert ">ctgX_2" in faa

_INV_GBK = """LOCUS       NODEX                   3000 bp    DNA     linear   BCT 01-JAN-2026
FEATURES             Location/Qualifiers
     source          1..3000
     CDS             100..600
                     /locus_tag="ctgX_1"
                     /gene_functions="biosynthetic (rule-based-clusters) nucleoside: truD"
     CDS             700..1100
                     /locus_tag="ctgX_2"
                     /translation="MKLPVTTAAR"
     CDS             complement(1200..1700)
                     /locus_tag="ctgX_3"
                     /translation="MAAGGGTTLL"
     CDS             complement(1800..2300)
                     /locus_tag="ctgX_4"
                     /gene_functions="biosynthetic-additional (smcogs) SMCOG1001: SDR"
     CDS             2400..2900
                     /locus_tag="ctgX_5"
                     /gene_functions="regulatory (smcogs) SMCOG1215: TetR"
ORIGIN
//
"""

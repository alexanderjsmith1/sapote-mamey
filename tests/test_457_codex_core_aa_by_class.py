import csv,json,subprocess,sys,zipfile
from tools._figure_route_common import ROOT

def test_core_gene_lengths_and_empty_class_rows(tmp_path):
    gbk="""
LOCUS       SYN_contig              90 bp    DNA     linear   BCT 01-JAN-2000
FEATURES             Location/Qualifiers
     region          1..90
                     /product="NRPS"
                     /contig_edge="False"
     CDS             1..9
                     /gene_kind="biosynthetic"
                     /locus_tag="SYN_gene"
                     /gene_functions="biosynthetic (rule-based-clusters) NRPS"
                     /translation="MKK"
ORIGIN
        1 atgaaaaaa
//
"""
    z=tmp_path/'SYN_A.zip'
    with zipfile.ZipFile(z,'w') as f:f.writestr('SYN_contig.region001.gbk',gbk)
    g=tmp_path/'genomes.tsv';g.write_text('strain\tgenus\tzip\nSYN_A\tSynthetic\tSYN_A.zip\n')
    i=tmp_path/'identities.tsv';i.write_text('strain\tregion_file\tcontig\tregion\tbgc_alias\nSYN_A\tSYN_contig.region001.gbk\tSYN_contig\tregion001\tBGC001\n')
    out=tmp_path/'out'
    subprocess.run([sys.executable,str(ROOT/'tools/core_aa_by_class.py'),'--genomes',str(g),'--identity-map',str(i),'--out',str(out)],check=True,timeout=120)
    rows=list(csv.DictReader((out/'CORE_AA_BY_CLASS_GENES.tsv').open(),delimiter='\t'))
    assert len(rows)==1 and rows[0]['aa_length']=='3' and rows[0]['contig']=='SYN_contig'
    summary=list(csv.DictReader((out/'CORE_AA_BY_CLASS_SUMMARY.tsv').open(),delimiter='\t'))
    assert len(summary)==5 and any(r['core_genes']=='0' for r in summary)

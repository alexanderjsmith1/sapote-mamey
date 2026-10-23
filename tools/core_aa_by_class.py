"""Promoted core aa extractor; complete identity required for every region."""
import csv, hashlib, re, statistics, sys, zipfile
from pathlib import Path
import argparse
bundle=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(bundle))
from tools._figure_route_common import bind,table,unique,write_table,receipt,output_dir
p=argparse.ArgumentParser(description='Core biosynthetic protein aa by its own antiSMASH rule classes')
p.add_argument('--genomes',type=Path,required=True,help='TSV: strain,genus,zip')
p.add_argument('--identity-map',type=Path,required=True,help='TSV: strain,region_file,contig,region,bgc_alias')
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
genomes=table(a.genomes,['strain','genus','zip']);unique(genomes,'strain')
identity_rows=table(a.identity_map,['strain','region_file','contig','region','bgc_alias'])
identity={}
from mamey.figure_theme import exact_locus_identity
for r in identity_rows:
    key=(r['strain'],r['region_file'])
    if key in identity:raise ValueError('duplicate identity mapping')
    identity[key]=(r,exact_locus_identity(r['strain'],r['contig'],r['region'],r['bgc_alias']))
bind([a.genomes,a.identity_map,Path(__file__)]+[(a.genomes.resolve().parent/r['zip']).resolve() for r in genomes])
out=output_dir(a.out)
sys.path.insert(0, str(bundle)); sys.path.insert(0, str(bundle / "tools"))
from region_table_one_setting import PRODUCT, REGION_BLOCK, REGION_GBK  # noqa: E402
from blastp_identity_figures import gene_classes, CLASSES  # noqa: E402
CDS_BLOCK = re.compile(r"\n {5}CDS {13}.*?(?=\n {5}\S|\nORIGIN)", re.S)
def q(block, key):
    m = re.search(r'/' + key + r'="([^"]*)"', block, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
genes, summary, inputs = [], [], []
for record in genomes:
    strain,genus=record['strain'],record['genus']
    zp=(a.genomes.resolve().parent/record['zip']).resolve()
    inputs.append((strain, zp, hashlib.sha256(Path(zp).read_bytes()).hexdigest()))
    with zipfile.ZipFile(zp) as zf:
        for name in sorted(zf.namelist()):
            if not REGION_GBK.search(name):
                continue
            key=(strain,Path(name).name)
            if key not in identity:raise ValueError('missing four-part identity: '+str(key))
            bound,locus=identity[key]
            text = zf.read(name).decode(errors="strict")
            blk = REGION_BLOCK.search(text)
            prods = sorted(set(PRODUCT.findall(blk.group(0) if blk else "")))
            edge = "true" if blk and 'contig_edge="True"' in blk.group(0) else "false"
            for c in CDS_BLOCK.finditer(text):
                b = c.group(0)
                if q(b, "gene_kind") != "biosynthetic":
                    continue
                tr = re.sub(r"\s+", "", q(b, "translation"))
                ks = sorted(gene_classes(q(b, "gene_functions")) or {"Other"})
                for k in ks:
                    genes.append(dict(strain=strain, genus=genus, contig=bound["contig"], region=bound["region"], bgc_alias=bound["bgc_alias"], region_file=Path(name).name, region_products=";".join(prods),
                                      contig_edge=edge, locus_tag=q(b, "locus_tag"), bgc_class=k, classes_of_gene=";".join(ks),
                                      aa_length=len(tr) if tr else "", saccharide_only_region="true" if prods == ["saccharide"] else "false"))
for record in genomes:
    strain,genus=record["strain"],record["genus"]
    for k in CLASSES:
        rows = [g for g in genes if g["strain"] == strain and g["bgc_class"] == k and g["aa_length"] != ""]
        L = [g["aa_length"] for g in rows]
        summary.append(dict(strain=strain, genus=genus, bgc_class=k, core_genes=len(L), core_aa_total=sum(L),
                            core_aa_median=statistics.median(L) if L else "", regions_with_class=len({g["region_file"] for g in rows}),
                            core_genes_on_edge_regions=sum(g["contig_edge"] == "true" for g in rows)))
gene_columns=['strain','genus','contig','region','bgc_alias','region_file','region_products','contig_edge','locus_tag','bgc_class','classes_of_gene','aa_length','saccharide_only_region']
summary_columns=['strain','genus','bgc_class','core_genes','core_aa_total','core_aa_median','regions_with_class','core_genes_on_edge_regions']
write_table(out/'CORE_AA_BY_CLASS_GENES.tsv',genes,gene_columns)
write_table(out/'CORE_AA_BY_CLASS_SUMMARY.tsv',summary,summary_columns)
receipt(out,'core_aa_by_class',[a.genomes,a.identity_map,bundle/'tools/region_table_one_setting.py',bundle/'tools/blastp_identity_figures.py',Path(__file__)]+[Path(p) for _,p,_ in inputs],
        {'class_rule':'gene own antiSMASH rule hits; multiclass counted in each class',
         'core_rule':'CDS gene_kind=biosynthetic','length':'translation amino acids; absent translation stays missing'},figures=False)

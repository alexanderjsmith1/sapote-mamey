"""Smoke test for tools/domain_prevalence.py — synthetic census+gbk fixtures, no external data."""
import sqlite3, json, os, sys, tempfile, importlib.util
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # bundle root
TOOL=os.path.join(HERE,"tools","domain_prevalence.py")

def _load():
    spec=importlib.util.spec_from_file_location("domain_prevalence",TOOL)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def _census(p):
    c=sqlite3.connect(p)
    c.execute("create table attempt(id,strain,state,elapsed_seconds,detail)")
    c.executemany("insert into attempt values(?,?,?,?,?)",[(1,"AS-1","COMPLETE",0,""),(2,"AS-2","COMPLETE",0,"")])
    c.execute("create table locus(locus_key,strain,full_node,region,bgc_alias,exact_identity,source_member,source_member_sha256,region_start_1based,region_end_1based,region_nt,cds_count,roster_sha256,products_json,prior_index_state)")
    c.executemany("insert into locus(locus_key,strain,exact_identity) values(?,?,?)",[("L1","AS-1","AS-1 / n / r / BGC1"),("L2","AS-2","AS-2 / n / r / BGC2")])
    c.commit(); c.close()

def _gbk(p):
    c=sqlite3.connect(p)
    c.execute("create table gene(locus_key,gene_order,locus_tag,protein_sha256,protein_length,cds_start,cds_end,strand,source_location,source_qualifiers_zlib,feature_count,result_state)")
    c.executemany("insert into gene(locus_key,locus_tag,protein_sha256) values(?,?,?)",[("L1","g1","sha_a"),("L2","g1","sha_b")])
    c.execute("create table feature(locus_key,feature_order,feature_type,source_location,parts_json,source_qualifiers_zlib,explicit_gene_tags_json,binding_state,holds_json)")
    c.executemany("insert into feature(locus_key,feature_order,feature_type,explicit_gene_tags_json,binding_state,holds_json) values(?,?,?,?,?,?)",
       [("L1",1,"PFAM_domain",'["g1"]',"SOURCE_SEQUENCE_AND_GEOMETRY_BOUND",None),
        ("L2",1,"PFAM_domain",'["g1"]',"SOURCE_SEQUENCE_AND_GEOMETRY_BOUND",None),
        ("L2",2,"aSDomain",'["g1"]',"HELD_SOURCE_RECORD_PRESERVED",'["hold"]')])
    c.execute("create table domain_summary(locus_key,feature_order,domain_label,source_tool,source_database_version,source_domain_id,protein_start_raw,protein_end_raw,evalue_raw,score_raw)")
    c.executemany("insert into domain_summary(locus_key,feature_order,domain_label,source_tool) values(?,?,?,?)",
       [("L1",1,"CommonDom","clusterhmmer"),("L2",1,"CommonDom","clusterhmmer"),("L2",2,"RareDom","nrps_pks_domains")])
    c.commit(); c.close()

def test_prevalence_counts_and_held():
    m=_load()
    d=tempfile.mkdtemp(); cen=os.path.join(d,"c.sqlite"); gbk=os.path.join(d,"g.sqlite"); out=os.path.join(d,"out")
    _census(cen); _gbk(gbk)
    class A: pass
    a=A(); a.census=cen; a.gbk_domains=gbk; a.out=out; a.nr=a.cnr=a.sp=None
    a.host_tsv=None; a.host_strain_col="strain"; a.host_source_col="source"; a.host_class_col=None
    a.exclude=None; a.host_override=None; a.rare_loci_max=5
    m.build(a)
    r=json.load(open(os.path.join(out,"domain_prevalence_ranking.json")))
    labels={row["domain_label"]:row for row in r["rows"]}
    assert r["scope"]["strains"]==2
    assert labels["CommonDom"]["strains"]==2 and labels["CommonDom"]["loci"]==2   # in both strains
    assert "RareDom" not in labels                                                 # held feature not counted as bound
    assert len(r["held"])==1 and r["held"][0]["domain_label"]=="RareDom"           # preserved separately
    assert labels["CommonDom"]["biosynthetic_relevance"]=="tailoring_or_pfam"

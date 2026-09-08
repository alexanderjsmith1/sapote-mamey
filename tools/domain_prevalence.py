#!/usr/bin/env python3
"""domain_prevalence.py — cohort-wide domain-prevalence + host-filterable widget/figures (v9.7.413).

PORTABLE: all inputs are arguments; no hardcoded paths. Existing-evidence analysis over antiSMASH
gene-census + gbk-domains SQLite candidates, with optional nr/ClusteredNR/Swiss-Prot evidence states.
Namespaces kept separate by source_tool; gene membership via explicit_gene_tags_json (never protein
length); domain copies deduped within a gene, genes within a locus. Rarity, biosynthetic relevance
and evidence are SEPARATE axes. Absent saved annotation != absent biological domain; similarity !=
functional proof; judgment deferred.

  python3 tools/domain_prevalence.py --census C.sqlite --gbk-domains G.sqlite --out DIR \
      [--nr NR.sqlite --cnr CNR.sqlite --sp SP.sqlite] [--host-tsv H.tsv --host-strain-col strain \
       --host-source-col source] [--exclude STRAIN_ID ...] [--host-override STRAIN_ID=ant ...] [--widget]
Emits: <out>/domain_prevalence__v0.1.0.sqlite, domain_prevalence_ranking.json,
       (with --widget) domain_prevalence_widget.html + figure_top20_*.svg, and an AUDIT_RECEIPT.json.
"""
from __future__ import annotations
import argparse, sqlite3, json, csv, hashlib, os, sys, time, collections, html

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<16),b''): h.update(b)
    return h.hexdigest()
def ro(p): return sqlite3.connect(f"file:{p}?mode=ro",uri=True)

def classify(src):
    s=(src or "").lower()
    if "wasp" in s and "bee or wasp" not in s: return "wasp"
    if "bee or wasp" in s: return "bee_or_wasp"
    if any(t in s for t in ("bombus","apis","apidae","andrena","bee")): return "bee"
    if "ant" in s or "atta" in s: return "ant"
    if "moss" in s: return "moss"
    if "mushroom" in s or "fung" in s: return "fungus_assoc"
    return "other" if s.strip() else "unknown"

def build(a):
    t0=time.time(); os.makedirs(a.out,exist_ok=True)
    g=ro(a.gbk_domains); c=ro(a.census)
    strains=sorted(r[0] for r in c.execute("select strain from attempt"))
    exclude=set(a.exclude or []); strains=[s for s in strains if s not in exclude]
    locus_strain=dict(c.execute("select locus_key,strain from locus"))
    prot={(lk,tag):psha for lk,tag,psha in g.execute("select locus_key,locus_tag,protein_sha256 from gene")}
    lid=dict(c.execute("select locus_key,exact_identity from locus"))
    # host map
    hostmap={s:"unknown" for s in strains}
    if a.host_tsv:
        for r in csv.DictReader(open(a.host_tsv),delimiter="\t"):
            s=r.get(a.host_strain_col)
            if s in hostmap:
                hc=classify(r.get(a.host_source_col)) if a.host_source_col else (r.get(a.host_class_col) or "unknown")
                if hc!="unknown": hostmap[s]=hc
    for ov in (a.host_override or []):
        k,_,v=ov.partition("="); hostmap[k]=v if k in hostmap else hostmap.get(k)
    # evidence maps
    def evmap(dbf,expr):
        if not dbf: return {}
        conn=ro(dbf); m={(lk,tag):st for lk,tag,st in conn.execute(expr)}; conn.close(); return m
    NR=evmap(a.nr,"select b.locus_key,b.locus_tag,p.availability_state from binding b join protein p using(query_sha256)")
    CNR=evmap(a.cnr,"select b.locus_key,b.locus_tag,p.availability_state from binding b join protein p using(query_sha256)")
    SP=evmap(a.sp,"select b.locus_key,b.locus_tag,p.state from binding b join protein p using(query_sha256)")
    def bucket(v): return "hit" if v=="VERIFIED_HITS" else "nohit" if v=="VERIFIED_NO_HIT" else "mixed" if v=="VERIFIED_MIXED_OUTCOMES" else "missing"
    NSt=len(strains); SIDX={s:i for i,s in enumerate(sorted(strains))}
    BIOSYN={"nrps_pks_domains","antismash"}
    A=lambda: {"feat":0,"genes":set(),"seqs":set(),"loci":set(),"strains":set(),"byh":collections.defaultdict(lambda:{"genes":set(),"loci":set(),"strains":set()})}
    D=collections.defaultdict(A); held=[]
    q=("select s.locus_key,s.source_tool,s.domain_label,f.feature_type,f.explicit_gene_tags_json,f.binding_state,f.holds_json "
       "from domain_summary s join feature f using(locus_key,feature_order)")
    for lk,tool,label,ftype,tags,bs,holds in g.execute(q):
        st=locus_strain.get(lk)
        if st not in hostmap: continue
        if bs!="SOURCE_SEQUENCE_AND_GEOMETRY_BOUND":
            held.append({"locus_key":lk,"strain":st,"source_tool":tool,"domain_label":label,"binding_state":bs,"holds":holds}); continue
        a2=D[(tool,ftype,label)]; a2["feat"]+=1
        try: gl=json.loads(tags) if tags else []
        except Exception: gl=[]
        hc=hostmap[st]
        for gt in (gl if isinstance(gl,list) else [gl]):
            a2["genes"].add((lk,gt)); a2["loci"].add(lk); a2["strains"].add(st)
            ps=prot.get((lk,gt));
            if ps: a2["seqs"].add(ps)
            a2["byh"][hc]["genes"].add((lk,gt)); a2["byh"][hc]["loci"].add(lk); a2["byh"][hc]["strains"].add(st)
    def tally(genes,mp): 
        b=collections.Counter(bucket(mp.get(gk)) for gk in genes) if mp else collections.Counter()
        return {"hit":b.get("hit",0),"nohit":b.get("nohit",0),"missing":b.get("missing",0),"mixed":b.get("mixed",0)}
    rows=[]
    for (tool,ftype,label),x in D.items():
        rows.append({"source_tool":tool,"feature_type":ftype,"domain_label":label,"feature_occurrences":x["feat"],
            "distinct_genes":len(x["genes"]),"distinct_seq_hashes":len(x["seqs"]),"loci":len(x["loci"]),"strains":len(x["strains"]),
            "strain_prevalence":round(len(x["strains"])/NSt,4) if NSt else 0,
            "biosynthetic_relevance":("core" if tool in BIOSYN else "tailoring_or_pfam" if tool=="clusterhmmer" else "other"),
            "by_host":{h:{"strains":len(v["strains"]),"loci":len(v["loci"]),"genes":len(v["genes"])} for h,v in x["byh"].items()},
            "evidence":{ch:tally(x["genes"],mp) for ch,mp in (("nr",NR),("cnr",CNR),("sp",SP))},
            "strain_idx":sorted(SIDX[s] for s in x["strains"]),
            "loci_list":([lid.get(lk,lk) for lk in sorted(x["loci"])] if len(x["loci"])<=a.rare_loci_max else [])})
    rows.sort(key=lambda r:(r["strains"],r["loci"],-r["feature_occurrences"]))
    # SQLite
    outdb=os.path.join(a.out,"domain_prevalence__v0.1.0.sqlite")
    if os.path.exists(outdb): os.remove(outdb)
    o=sqlite3.connect(outdb); o.execute("create table metadata(key text,value text)")
    o.executemany("insert into metadata values(?,?)",[("schema_version","domain_prevalence/0.1.0"),
      ("built_utc",time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())),("denominator_strains",str(NSt)),
      ("census_sha256",sha256(a.census)),("gbk_domains_sha256",sha256(a.gbk_domains)),
      ("excluded",",".join(sorted(exclude))),("held_feature_count",str(len(held))),
      ("rarity_formula","distinct strains asc, then loci asc, then feature_occurrences desc; rarity/relevance/evidence SEPARATE"),
      ("claim_safety","class-level; absent annotation != absent biology; similarity != function; judgment deferred")])
    o.execute("create table domain_prevalence(source_tool,feature_type,domain_label,feature_occurrences int,distinct_genes int,distinct_seq_hashes int,loci int,strains int,strain_prevalence real,biosynthetic_relevance)")
    o.executemany("insert into domain_prevalence values(?,?,?,?,?,?,?,?,?,?)",[(r["source_tool"],r["feature_type"],r["domain_label"],r["feature_occurrences"],r["distinct_genes"],r["distinct_seq_hashes"],r["loci"],r["strains"],r["strain_prevalence"],r["biosynthetic_relevance"]) for r in rows])
    o.execute("create table host_breakdown(source_tool,domain_label,host_class,strains int,loci int,genes int)")
    o.executemany("insert into host_breakdown values(?,?,?,?,?,?)",[(r["source_tool"],r["domain_label"],h,d["strains"],d["loci"],d["genes"]) for r in rows for h,d in r["by_host"].items()])
    o.execute("create table evidence_state(source_tool,domain_label,channel,hit int,nohit int,missing int,mixed int)")
    o.executemany("insert into evidence_state values(?,?,?,?,?,?,?)",[(r["source_tool"],r["domain_label"],ch,e["hit"],e["nohit"],e["missing"],e["mixed"]) for r in rows for ch,e in r["evidence"].items()])
    o.execute("create table held_feature(locus_key,strain,source_tool,domain_label,binding_state,holds)")
    o.executemany("insert into held_feature values(?,?,?,?,?,?)",[(h["locus_key"],h["strain"],h["source_tool"],h["domain_label"],h["binding_state"],str(h["holds"])) for h in held])
    o.execute("create table strain_host(strain,host_class)"); o.executemany("insert into strain_host values(?,?)",[(s,hostmap[s]) for s in strains])
    o.commit(); o.close()
    _scope_loci=len({lk for lk,st in locus_strain.items() if st in hostmap})
    _scope_genes=sum(1 for (lk,tag) in prot if locus_strain.get(lk) in hostmap)
    json.dump({"scope":{"strains":NSt,"loci":_scope_loci,"genes":_scope_genes},"host_distribution":dict(collections.Counter(hostmap.values())),
        "namespaces":dict(collections.Counter(r["source_tool"] for r in rows)),"total_distinct_families":len(rows),
        "strains_sorted":sorted(strains),"strain_host":{s:hostmap[s] for s in strains},"rows":rows,"held":held,
        "source":{"census_sha256":sha256(a.census),"gbk_domains_sha256":sha256(a.gbk_domains)}},
        open(os.path.join(a.out,"domain_prevalence_ranking.json"),"w"),indent=1)
    receipt={"scope_strains":NSt,"distinct_families":len(rows),"held":len(held),"host_distribution":dict(collections.Counter(hostmap.values())),
        "evidence_channels":[c for c,f in (("nr",a.nr),("cnr",a.cnr),("sp",a.sp)) if f],"elapsed_s":round(time.time()-t0,2),
        "token_counter":"UNAVAILABLE_NO_LIVE_TASK_TOKEN_COUNTER"}
    json.dump(receipt,open(os.path.join(a.out,"AUDIT_RECEIPT.json"),"w"),indent=1)
    print(f"domain_prevalence: {len(rows)} families, {NSt} strains, {len(held)} held -> {a.out}")
    return rows,strains,hostmap

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--census",required=True); p.add_argument("--gbk-domains",required=True); p.add_argument("--out",required=True)
    p.add_argument("--nr"); p.add_argument("--cnr"); p.add_argument("--sp")
    p.add_argument("--host-tsv"); p.add_argument("--host-strain-col",default="strain"); p.add_argument("--host-source-col",default="source"); p.add_argument("--host-class-col")
    p.add_argument("--exclude",nargs="*"); p.add_argument("--host-override",nargs="*"); p.add_argument("--rare-loci-max",type=int,default=5)
    p.add_argument("--widget",action="store_true")
    a=p.parse_args(argv)
    build(a)
    if a.widget:
        import subprocess
        wtool=os.path.join(os.path.dirname(os.path.abspath(__file__)),"domain_prevalence_widget.py")
        r=subprocess.run([sys.executable,wtool,a.out],capture_output=True,text=True)
        if r.returncode!=0: sys.stderr.write(f"WARN: widget step failed: {r.stderr[:300]}\n")
        else: print("  widget + figures written")
    return 0

if __name__=="__main__": raise SystemExit(main())

#!/usr/bin/env python3
"""scan_prevalence.py (v9.7.413) — cohort prevalence for mamey keyword-scan DBs (resistance/regulator/
transporter/chitinase/...). Reads gene.groups_json hits; emits the SAME ranking-JSON shape as
domain_prevalence so tools/domain_prevalence_widget.py renders it unchanged. Portable; read-only inputs.
Class-level; absent annotation != absent biology; similarity != function; judgment deferred."""
from __future__ import annotations
import argparse, sqlite3, json, csv, os, sys, time, collections, hashlib, re
def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<16),b''): h.update(b)
    return h.hexdigest()
def ro(p): return sqlite3.connect(f"file:{p}?mode=ro",uri=True)
_WORD=re.compile(r"[a-z]+")
def classify(src):
    # whole words: "plant", "Antarctic", "halotolerant" are not ants; "beetle" is not a bee
    s=(src or "").lower(); w=_WORD.findall(s)
    if "bee or wasp" in s: return "bee_or_wasp"
    if any(x in ("wasp","wasps") or x.endswith("wasp") for x in w): return "wasp"
    if any(x in ("bombus","apis","apidae","andrena") or x.endswith(("bee","bees"))
           or (x.startswith("bee") and not x.startswith(("beet","beech","beef"))) for x in w): return "bee"
    if any(x in ("ant","ants","atta") for x in w): return "ant"
    if any(x.startswith("moss") for x in w): return "moss"
    if any(x.startswith(("mushroom","fung")) for x in w): return "fungus_assoc"
    return "other" if s.strip() else "unknown"
def build(a):
    t0=time.time(); os.makedirs(a.out,exist_ok=True); db=ro(a.scan_db)
    strains=sorted(r[0] for r in db.execute("select distinct strain from source"))
    exclude=set(a.exclude or []); strains=[s for s in strains if s not in exclude]
    locus_strain=dict(db.execute("select locus_key,strain from locus"))
    prot={(lk,tag):psha for lk,tag,psha in db.execute("select locus_key,locus_tag,protein_sha256 from gene")}
    lid=dict(db.execute("select locus_key,exact_identity from locus"))
    hostmap={s:"unknown" for s in strains}
    if a.host_tsv:
        for r in csv.DictReader(open(a.host_tsv),delimiter="\t"):
            s=r.get(a.host_strain_col)
            if s in hostmap:
                hc=classify(r.get(a.host_source_col))
                if hc!="unknown": hostmap[s]=hc
    for ov in (a.host_override or []):
        k,_,v=ov.partition("=")
        if k in hostmap: hostmap[k]=v
    NSt=len(strains); SIDX={s:i for i,s in enumerate(sorted(strains))}
    A=lambda:{"genes":set(),"loci":set(),"strains":set(),"seqs":set(),"byh":collections.defaultdict(lambda:{"genes":set(),"loci":set(),"strains":set()})}
    D=collections.defaultdict(A)
    for lk,tag,psha,gj in db.execute("select locus_key,locus_tag,protein_sha256,groups_json from gene"):
        st=locus_strain.get(lk)
        if st not in hostmap or not gj or gj in ("[]","{}",""): continue
        try: obj=json.loads(gj)
        except Exception: continue
        groups=obj if isinstance(obj,list) else list(obj.keys()) if isinstance(obj,dict) else []
        hc=hostmap[st]
        for grp in groups:
            grp=str(grp); x=D[grp]
            x["genes"].add((lk,tag)); x["loci"].add(lk); x["strains"].add(st)
            if psha: x["seqs"].add(psha)
            x["byh"][hc]["genes"].add((lk,tag)); x["byh"][hc]["loci"].add(lk); x["byh"][hc]["strains"].add(st)
    ns=a.dataset_name
    rows=[]
    for grp,x in D.items():
        rows.append({"source_tool":ns,"feature_type":ns,"domain_label":grp,"feature_occurrences":len(x["genes"]),
            "distinct_genes":len(x["genes"]),"distinct_seq_hashes":len(x["seqs"]),"loci":len(x["loci"]),"strains":len(x["strains"]),
            "strain_prevalence":round(len(x["strains"])/NSt,4) if NSt else 0,"biosynthetic_relevance":"scan",
            "by_host":{h:{"strains":len(v["strains"]),"loci":len(v["loci"]),"genes":len(v["genes"])} for h,v in x["byh"].items()},
            "evidence":{ch:{"hit":0,"nohit":0,"missing":0,"mixed":0} for ch in ("nr","cnr","sp")},
            "strain_idx":sorted(SIDX[s] for s in x["strains"]),
            "loci_list":([lid.get(lk,lk) for lk in sorted(x["loci"])] if len(x["loci"])<=a.rare_loci_max else [])})
    rows.sort(key=lambda r:(r["strains"],r["loci"],-r["feature_occurrences"]))
    loci_scope=len({lk for lk,st in locus_strain.items() if st in hostmap})
    genes_scope=sum(1 for (lk,tag) in prot if locus_strain.get(lk) in hostmap)
    json.dump({"scope":{"strains":NSt,"loci":loci_scope,"genes":genes_scope},
        "host_distribution":dict(collections.Counter(hostmap.values())),
        "namespaces":{ns:len(rows)},"total_distinct_families":len(rows),
        "strains_sorted":sorted(strains),"strain_host":{s:hostmap[s] for s in strains},"rows":rows,"held":[],
        "source":{"scan_db_sha256":sha256(a.scan_db),"dataset":ns}},
        open(os.path.join(a.out,"domain_prevalence_ranking.json"),"w"),indent=1)
    # The widget footer points to AUDIT_RECEIPT.json, so write it with domain_prevalence's keys.
    # A keyword scan has no nr/cnr/sp evidence channels: the list is empty, not omitted.
    with open(os.path.join(a.out,"AUDIT_RECEIPT.json"),"w") as fh:
        json.dump({"scope_strains":NSt,"distinct_families":len(rows),"held":0,
            "host_distribution":dict(collections.Counter(hostmap.values())),"evidence_channels":[],
            "elapsed_s":round(time.time()-t0,2),"token_counter":"UNAVAILABLE_NO_LIVE_TASK_TOKEN_COUNTER",
            "source":{"scan_db_sha256":sha256(a.scan_db),"dataset":ns}},fh,indent=1)
    print(f"scan_prevalence[{ns}]: {len(rows)} groups, {NSt} strains, {sum(r['feature_occurrences'] for r in rows)} gene-hits -> {a.out}")
    return rows
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--scan-db",required=True); p.add_argument("--dataset-name",required=True); p.add_argument("--out",required=True)
    p.add_argument("--host-tsv"); p.add_argument("--host-strain-col",default="strain"); p.add_argument("--host-source-col",default="source")
    p.add_argument("--exclude",nargs="*"); p.add_argument("--host-override",nargs="*"); p.add_argument("--rare-loci-max",type=int,default=5); p.add_argument("--widget",action="store_true")
    a=p.parse_args(argv); build(a)
    if a.widget:
        import subprocess
        w=os.path.join(os.path.dirname(os.path.abspath(__file__)),"domain_prevalence_widget.py")
        r=subprocess.run([sys.executable,w,a.out],capture_output=True,text=True)
        if r.returncode!=0:
            sys.stderr.write(f"FAIL: widget step failed (tables were written): {r.stderr[:200]}\n")
            return 3   # --widget was asked for and not delivered
        print("  widget + figures written")
    return 0
if __name__=="__main__": raise SystemExit(main())

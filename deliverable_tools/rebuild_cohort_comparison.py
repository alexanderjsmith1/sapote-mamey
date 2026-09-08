#!/usr/bin/env python3
"""rebuild_as_sid_comparison.py — AS vs SID compound comparison over the FULL SID set:
25 SID from the gene master + 64 SID from the extracted supplement = 89 SID vs 46 AS.
Per-gene KnownClusterBlast (MIBiG) is the common currency. Homology/capacity only."""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import csv, collections, statistics as st
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os
ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()); OUT=f"{ROOT}/sapote_deliverables"
GM=f"{ROOT}/strain_data/ClusterBlast_Gene_Master/CLUSTERBLAST_GENE_MASTER.csv"
SUP=f"{OUT}/SID_clusterblast_supplement.csv"

comp=collections.defaultdict(lambda:{"AS":set(),"SID":set(),"as_pid":[],"sid_pid":[]})
asx,sidx=set(),set()
# gene master (AS + 25 SID), per-gene rows
for r in csv.DictReader(open(GM)):
    s=r["strain"]; ch="AS" if s.startswith("AS-") else ("SID" if s.startswith("SID") else None)
    if not ch: continue
    (asx if ch=="AS" else sidx).add(s)
    c=r.get("bgc_compound","").strip()
    if not c: continue
    try: pid=float(r.get("pct_identity") or 0)
    except: pid=0
    comp[c][ch].add(s); (comp[c]["as_pid"] if ch=="AS" else comp[c]["sid_pid"]).append(pid)
# supplement (64 SID), per (strain,compound) rows w/ median pid
for r in csv.DictReader(open(SUP)):
    s=r["strain"]; sidx.add(s); c=r["compound"].strip()
    if not c: continue
    comp[c]["SID"].add(s)
    try: comp[c]["sid_pid"].append(float(r["median_pid"]))
    except: pass

nAS,nSID=len(asx),len(sidx)
rows=[]
for c,e in comp.items():
    a,si=len(e["AS"]),len(e["SID"])
    rows.append({"compound":c,"as":a,"sid":si,"tot":a+si,
        "as_med":round(st.median(e["as_pid"]),1) if e["as_pid"] else None,
        "sid_med":round(st.median(e["sid_pid"]),1) if e["sid_pid"] else None,
        "cls":"shared" if a and si else ("AS-only" if a else "SID-only")})
rows.sort(key=lambda r:-r["tot"])
shared=[r for r in rows if r["cls"]=="shared"]; aonly=[r for r in rows if r["cls"]=="AS-only"]; sonly=[r for r in rows if r["cls"]=="SID-only"]

with open(f"{OUT}/AS_vs_SID_clusterblast_comparison.csv","w",newline="") as f:
    w=_SafeWriter(f); w.writerow(["mibig_compound","class","AS_strains","SID_strains","total","AS_median_pid","SID_median_pid"])
    for r in rows: w.writerow([r["compound"],r["cls"],r["as"],r["sid"],r["tot"],r["as_med"],r["sid_med"]])

def tbl(rs,n=15):
    L=["| MIBiG compound | AS | SID | AS med%id | SID med%id |","|---|--:|--:|--:|--:|"]
    for r in rs[:n]: L.append(f"| {r['compound'][:40]} | {r['as']}/{nAS} | {r['sid']}/{nSID} | {r['as_med'] if r['as_med'] is not None else '—'} | {r['sid_med'] if r['sid_med'] is not None else '—'} |")
    return L
L=["# AS vs SID — per-gene ClusterBlast comparison (MIBiG anchors)","",
   f"*Common currency = per-gene KnownClusterBlast (both cohorts; SID has no nr). "
   f"**{nAS} AS strains vs {nSID} SID strains** (25 from gene master + 64 extracted from completed antiSMASH results), "
   f"over {len(rows):,} MIBiG compound anchors. Generated 2026-08-03.*","",
   "> Homology & capacity only. A shared anchor = both cohorts carry genes homologous to that reference cluster "
   "(similar biosynthetic capacity), NOT the same product, never an activity claim. Counts = strains-with-≥1-gene-hit / cohort size.","",
   f"**Summary:** {len(shared):,} shared · {len(aonly):,} AS-only · {len(sonly):,} SID-only.","",
   "## Most widely shared (both cohorts)",""]+tbl(shared)+["","## Top AS-enriched (AS ≫ SID)",""]
ae=sorted([r for r in rows if r["as"]>=3 and r["as"]>3*max(1,r["sid"])],key=lambda r:-r["as"])
L+=tbl(ae,12)+["","## Top SID-enriched (SID ≫ AS)",""]
se=sorted([r for r in rows if r["sid"]>=4 and r["sid"]>3*max(1,r["as"])],key=lambda r:-r["sid"])
L+=tbl(se,12)+["","*Interpretation guard: a cohort-recurrent anchor is a comparative-genome-mining lead, not evidence either cohort produces the named compound.*"]
open(f"{OUT}/AS_vs_SID_clusterblast_comparison.md","w").write("\n".join(L))
emit(f"AS {nAS} vs SID {nSID} | {len(rows)} anchors | shared {len(shared)} AS-only {len(aonly)} SID-only {len(sonly)}", "top SID-enriched:", sep="\n")
for r in se[:6]: emit(f"  {r['compound'][:40]:<42} AS {r['as']} SID {r['sid']}")

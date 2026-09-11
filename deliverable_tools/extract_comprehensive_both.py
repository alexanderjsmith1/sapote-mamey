#!/usr/bin/env python3
"""extract_comprehensive_both.py — parse KnownClusterBlast (MIBiG) the SAME way for BOTH
cohorts from their completed antiSMASH JSONs, so AS vs SID is apples-to-apples. Read-only.
Emits per-(cohort,strain,compound) median/max %id + reference genus of the hit."""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import csv, glob, io, json, os, re, zipfile, collections, statistics as st
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os


# v9.7.417 IMPORT SAFETY. Everything below this line used to run at MODULE IMPORT: this file
# has no `__main__` guard and its top level is a script, so `import extract_comprehensive_both`
# wrote real deliverables into $SAPOTE_WORKSPACE_ROOT as a side effect. Any tree-walking
# tool that imports rather than parses would have triggered it. The body below is UNCHANGED
# and only indented under the guard, so running this file as a script behaves exactly as
# before, and importing it now does nothing. Checked by AST equality against the pre-patch
# body, statement for statement, and by importing the module and asserting no file appears.
if __name__ == "__main__":   # v9.7.417 import safety — see tests/test_tools_import_safe_v97250.py
    ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
    OUT=f"{ROOT}/sapote_deliverables/COMPREHENSIVE_clusterblast_both.csv"

    def zjson(zf):
        for n in zf.namelist():
            if n.endswith(".json") and "/input/" not in n and not n.startswith("input"):
                return n
        return None

    def parse(zpath):
        """compound -> (pids, ref_genera Counter)"""
        zf=zipfile.ZipFile(zpath); jn=zjson(zf)
        if not jn: return {}
        d=json.load(io.TextIOWrapper(zf.open(jn), encoding="utf-8"))
        comp=collections.defaultdict(lambda:[[],collections.Counter()])
        for rec in d.get("records",[]):
            kc=rec.get("modules",{}).get("antismash.modules.clusterblast",{}).get("knowncluster")
            if not kc: continue
            for res in kc.get("results",[]):
                for ref,score in res.get("ranking",[]):
                    c=(ref.get("description") or "").strip()
                    if not c: continue
                    for pr in score.get("pairings",[]):
                        if isinstance(pr,list) and len(pr)>=3:
                            h=pr[2]
                            try: comp[c][0].append(float(h.get("perc_ident")))
                            except: pass
                            gc=(h.get("genecluster") or h.get("full_name") or "")
                            mg=re.search(r"\b([A-Z][a-z]+)(?:_| )", gc)
        return comp

    targets=[]
    for z in glob.glob(f"{ROOT}/strain_data/*/antiSMASH/*.zip"):
        m=re.search(r"(AS-\d+)", z); 
        if m: targets.append(("AS", m.group(1), z))
    for z in glob.glob(f"{ROOT}/SID strains/antismash_inputs_renamed/*.zip"):
        m=re.match(r"(SID\d+)", os.path.basename(z))
        if m: targets.append(("SID", m.group(1), z))
    # dedupe strains (first zip wins)
    seen=set(); rows=[]
    uniq=[]
    for ch,s,z in targets:
        if s in seen: continue
        seen.add(s); uniq.append((ch,s,z))
    for i,(ch,s,z) in enumerate(uniq,1):
        try:
            comp=parse(z)
            for c,(pids,_g) in comp.items():
                if pids: rows.append({"cohort":ch,"strain":s,"compound":c,"n_genes":len(pids),
                                      "median_pid":round(st.median(pids),1),"max_pid":round(max(pids),1)})
            emit(f"  [{i}/{len(uniq)}] {ch} {s}: {len(comp)} anchors", flush=True)
        except Exception as e:
            emit(f"  {ch} {s}: ERROR {e}", flush=True)
    with open(OUT,"w",newline="") as f:
        w=_SafeDictWriter(f, fieldnames=["cohort","strain","compound","n_genes","median_pid","max_pid"]); w.writeheader(); w.writerows(rows)
    nas=len({r['strain'] for r in rows if r['cohort']=='AS'}); nsid=len({r['strain'] for r in rows if r['cohort']=='SID'})
    emit(f"COMPREHENSIVE_DONE: AS {nas} + SID {nsid} strains, {len(rows)} rows -> {OUT}", flush=True)

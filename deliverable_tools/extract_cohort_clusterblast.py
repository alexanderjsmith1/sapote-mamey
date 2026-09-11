#!/usr/bin/env python3
"""extract_sid_clusterblast.py — parse per-gene KnownClusterBlast (MIBiG) from the
ALREADY-COMPLETED antiSMASH result JSONs in SID strains/antismash_inputs_renamed/*.zip.
No antiSMASH run — read-only extraction. Emits a compact per-(strain,compound) supplement
so the 64 not-yet-in-gene-master SID strains can join the AS-vs-SID comparison.
"""
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
# has no `__main__` guard and its top level is a script, so `import extract_cohort_clusterblast`
# wrote real deliverables into $SAPOTE_WORKSPACE_ROOT as a side effect. Any tree-walking
# tool that imports rather than parses would have triggered it. The body below is UNCHANGED
# and only indented under the guard, so running this file as a script behaves exactly as
# before, and importing it now does nothing. Checked by AST equality against the pre-patch
# body, statement for statement, and by importing the module and asserting no file appears.
if __name__ == "__main__":   # v9.7.417 import safety — see tests/test_tools_import_safe_v97250.py
    ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
    OUT=f"{ROOT}/sapote_deliverables/SID_clusterblast_supplement.csv"

    have=set()
    for r in csv.DictReader(open(f"{ROOT}/strain_data/ClusterBlast_Gene_Master/CLUSTERBLAST_GENE_MASTER.csv")):
        if r["strain"].startswith("SID"): have.add(r["strain"])

    zips={}
    for z in glob.glob(f"{ROOT}/SID strains/antismash_inputs_renamed/*.zip"):
        m=re.match(r"(SID\d+)", os.path.basename(z))
        if m and m.group(1) not in have: zips[m.group(1)]=z

    rows=[]
    for i,(sid,z) in enumerate(sorted(zips.items()),1):
        try:
            zf=zipfile.ZipFile(z)
            jn=[n for n in zf.namelist() if n.endswith(".json") and "/input/" not in n and not n.startswith("input")]
            if not jn: emit(f"  {sid}: no json", flush=True); continue
            d=json.load(io.TextIOWrapper(zf.open(jn[0]), encoding="utf-8"))
            per_comp=collections.defaultdict(list)   # compound -> [pid,...]
            for rec in d.get("records", []):
                kc=rec.get("modules",{}).get("antismash.modules.clusterblast",{}).get("knowncluster")
                if not kc: continue
                for res in kc.get("results", []):
                    for ref,score in res.get("ranking", []):
                        comp=(ref.get("description") or "").strip()
                        if not comp: continue
                        for pr in score.get("pairings", []):
                            if isinstance(pr,list) and len(pr)>=3:
                                try: per_comp[comp].append(float(pr[2].get("perc_ident")))
                                except (TypeError,ValueError): pass
            for comp,pids in per_comp.items():
                if pids:
                    rows.append({"strain":sid,"compound":comp,"n_genes":len(pids),
                                 "median_pid":round(st.median(pids),1),"max_pid":round(max(pids),1)})
            emit(f"  [{i}/{len(zips)}] {sid}: {len(per_comp)} compound anchors", flush=True)
        except Exception as e:
            emit(f"  {sid}: ERROR {e}", flush=True)

    with open(OUT,"w",newline="") as f:
        w=_SafeDictWriter(f, fieldnames=["strain","compound","n_genes","median_pid","max_pid"])
        w.writeheader(); w.writerows(rows)
    emit(f"SID_SUPPLEMENT_DONE: {len(zips)} strains, {len(rows)} (strain,compound) rows -> {OUT}", flush=True)

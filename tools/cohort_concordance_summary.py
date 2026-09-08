#!/usr/bin/env python3
"""cohort_concordance_summary.py — run the fragment-concordance scorer across a multi-strain ledger
and summarise the nearest MIBiG neighbour per fragment, grouped by strain, with the CURATED-ADJUDICATED
vs MIBIG-AUTO reference split.

Input: a reference_panel_ledger.py CSV spanning several strains (its `source_file` column names the
strain). Output: a per-fragment detail CSV and a per-strain summary CSV.

Claim-safe: scores are architectural similarity, not identity or production. MIBIG-AUTO neighbours
carry no marker credit; only CURATED-ADJUDICATED references contribute the marker axis.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, sys, collections, statistics
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_open
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fragment_concordance_scorer as fcs

def _strain(s: str) -> str:
    b = os.path.basename(s or "?")
    for suf in ("_copy.zip", ".zip", "_copy"):
        if b.endswith(suf): b = b[:-len(suf)]
    return b

def main(argv=None) -> int:
    _D = Path(fcs.__file__).resolve().parent.parent / "mamey" / "data" / "mibig"
    ap = argparse.ArgumentParser(description="Cohort-level MIBiG concordance summary from a multi-strain ledger.")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--mibig-index", default=str(_D / "mibig_reference_index.bacterial.json"))
    ap.add_argument("--adjudications", default=str(_D / "adjudications.json"))
    ap.add_argument("--include-fungal", action="store_true")
    ap.add_argument("--mibig-status", default=None, help="comma list of mibig_status to keep (e.g. active)")
    ap.add_argument("--out-prefix", default="cohort_concordance")
    a = ap.parse_args(argv)

    keep = {x.strip() for x in a.mibig_status.split(",")} if a.mibig_status else None
    panel = fcs.load_mibig_space(a.mibig_index, a.adjudications, keep)
    if a.include_fungal:
        fp = _D / "mibig_reference_index.fungal.json"
        if fp.exists(): panel += fcs.load_mibig_space(str(fp), a.adjudications, keep)

    rows = list(csv.DictReader(open(a.ledger, encoding="utf-8")))
    detail = []; by = collections.defaultdict(list)
    for r in rows:
        obs = fcs.obs_signature({"id": r.get("bgc_id"), "region": r.get("obs_region_type", ""),
                                 "pks_ks": r.get("obs_pks_ks") or None, "nrps_c": r.get("obs_nrps_c") or None,
                                 "nrps_a": r.get("obs_nrps_a") or None, "size_kb": r.get("obs_size_kb") or None,
                                 "markers": r.get("cmp_t43_markers") or r.get("cmp_t43") or ""})
        res = fcs.best_match(obs, panel)
        res["strain"] = _strain(r.get("source_file")); res["contig"] = r.get("contig")
        detail.append(res); by[res["strain"]].append(res)

    summ = []
    for st, frs in sorted(by.items()):
        tiers = collections.Counter(f["tier"] for f in frs)
        rt = collections.Counter(f["reference_tier"] for f in frs)
        comps = collections.Counter(f["best_compound"] for f in frs)
        summ.append({"strain": st, "n_fragments": len(frs),
                     "STRONG": tiers.get("STRONG", 0), "MODERATE": tiers.get("MODERATE", 0),
                     "WEAK": tiers.get("WEAK", 0), "NONE": tiers.get("NONE", 0),
                     "curated_adjudicated": rt.get("CURATED-ADJUDICATED", 0), "mibig_auto": rt.get("MIBIG-AUTO", 0),
                     "mean_score": round(statistics.mean(f["score"] for f in frs), 3),
                     "top_neighbours": "; ".join(f"{c}({n})" for c, n in comps.most_common(3))})

    dcols = ["strain", "id", "contig", "best_compound", "best_accession", "reference_tier", "score", "tier"]
    with atomic_open(a.out_prefix + "_detail.csv", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=dcols, extrasaction="ignore"); w.writeheader()
        for d in detail: w.writerow(d)
    scols = ["strain", "n_fragments", "STRONG", "MODERATE", "WEAK", "NONE",
             "curated_adjudicated", "mibig_auto", "mean_score", "top_neighbours"]
    with atomic_open(a.out_prefix + "_summary.csv", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=scols); w.writeheader()
        for s in summ: w.writerow(s)

    emit(f"  {len(detail)} fragments across {len(by)} strains -> {a.out_prefix}_summary.csv / _detail.csv")
    for s in summ:
        emit(f"  {s['strain']:16} n={s['n_fragments']:3} STRONG={s['STRONG']:3} curated={s['curated_adjudicated']:3} "
              f"auto={s['mibig_auto']:3} mean={s['mean_score']} | {s['top_neighbours']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

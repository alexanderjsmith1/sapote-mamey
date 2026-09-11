#!/usr/bin/env python3
"""bioassay_to_activity_channel — emit MEASURED fraction-screen data as Sapote-Mamey
`bioactivity_metadata_v1` objects (docs/BIOACTIVITY_METADATA_CONTRACT.md), one per strain, for
`mamey_run.py run --bioactivity-json <json>`. STRAIN-LEVEL, EXTRACT-LEVEL ONLY: inhibition%/tiers go in
free-form assays[]; no BGC is credited; capacity != production; the engine treats it as score-neutral context.

Usage:
  python3 bioassay_to_activity_channel.py --recon <fraction_concentration_response_48h.csv> --out <dir> \
      [--strain AS-XXX] [--min-hit 50.0] [--validate <path-to-sealed-mamey-tree>]
"""
import argparse, csv, json, os, sys, importlib.util
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CREDIBLE = {"STRONG_DOSE_CONSISTENT", "SUPPORTED_MULTI_CONCENTRATION_HIT"}

# Screening-not-validated caveat carried on every emitted object (preliminary single-replicate 384-well data).
SCREEN_WARNINGS = [
    "PRELIMINARY_SINGLE_REPLICATE_SCREEN: 384-well fraction screen with no biological replication; "
    "dose-response inversions and single-concentration spikes are expected assay artifacts, not validated activity.",
    "EXTRACT_LEVEL_ONLY: whole-fraction (2-10+ metabolite mixture) strain-level observation; "
    "not attributed to any BGC; capacity is not production; judgment deferred.",
]

def fnum(x):
    try: return float(x)
    except Exception: return None

def build(recon, only=None, min_hit=50.0):
    per = {}  # strain -> organism -> best row
    with open(recon) as f:
        for r in csv.DictReader(f):
            s = (r.get("strain_id") or "").strip()
            if not s or (only and s != only): continue
            org = (r.get("organism") or "").strip()
            mx = fnum(r.get("max_inhibition_raw"))
            if org == "" or mx is None: continue
            cur = per.setdefault(s, {}).get(org)
            if cur is None or mx > cur["_mx"]:
                per[s][org] = {
                    "_mx": mx,
                    "assay": "fraction_screen_multidose_48h",
                    "target": org,
                    "best_inhibition_pct": round(mx, 1),
                    "inhibition_15ugml": (round(fnum(r.get("inhibition_15ug_ml")),1) if fnum(r.get("inhibition_15ug_ml")) is not None else None),
                    "doses_ugml": [120, 60, 30, 15],
                    "dose_inhibition_pct": [round(fnum(r.get(k)),1) if fnum(r.get(k)) is not None else None
                                            for k in ("inhibition_120ug_ml","inhibition_60ug_ml","inhibition_30ug_ml","inhibition_15ug_ml")],
                    "screening_tier": (r.get("screening_pattern") or "").strip(),
                    "best_fraction_sample": (r.get("fraction_sample_key") or "").strip(),
                    "doses_at_or_above_50pct": r.get("concentrations_at_or_above_50pct"),
                    "spearman_dose_response": fnum(r.get("spearman_concentration_response")),
                }
    objs = {}
    for s, orgs in per.items():
        assays = []
        for org, a in sorted(orgs.items(), key=lambda kv: -kv[1]["_mx"]):
            a = {k: v for k, v in a.items() if not k.startswith("_")}
            assays.append(a)
        credible = any(a["screening_tier"] in CREDIBLE and (a["best_inhibition_pct"] or 0) >= min_hit for a in assays)
        objs[s] = {
            "schema_version": "bioactivity_metadata_v1",
            "metadata_state": "MEASURED_POSITIVE" if credible else "MEASURED_NEGATIVE",
            "observation_state": "POSITIVE" if credible else "NEGATIVE",
            "usage_scope": "PRODUCTION",
            "assays": assays,
            "compound_linkage": "NOT_ESTABLISHED",
            "receipt_locator": "fraction_concentration_response_48h.csv",
            "warnings": list(SCREEN_WARNINGS),
        }
    return objs

def build_af_dossier(recon, min_hit=50.0, only=None):
    """Emit the af-dossier --activity-table shape: strain,anti_Candida,anti_MRSA,host,genus (measured calls)."""
    import csv as _csv
    agg = {}
    with open(recon) as f:
        for r in _csv.DictReader(f):
            s = (r.get("strain_id") or "").strip()
            if not s or (only and s != only): continue
            org = (r.get("organism") or "").strip().lower()
            mx = fnum(r.get("max_inhibition_raw"))
            tier = (r.get("screening_pattern") or "").strip()
            d = agg.setdefault(s, {"cand": "not_tested", "mrsa": "not_tested",
                                    "host": (r.get("host") or "").strip(),
                                    "genus": (r.get("genus_16s") or "").strip()})
            if not d["host"] and (r.get("host") or "").strip(): d["host"] = r.get("host").strip()
            if not d["genus"] and (r.get("genus_16s") or "").strip(): d["genus"] = r.get("genus_16s").strip()
            if mx is not None:
                credible = tier in CREDIBLE and mx >= min_hit
                for needle, key in (("candida", "cand"), ("mrsa", "mrsa")):
                    if needle in org:
                        if credible:
                            d[key] = "positive"
                        elif d[key] != "positive":
                            d[key] = "negative"
    rows = []
    for s in sorted(agg):
        d = agg[s]
        rows.append({"strain": s,
                     "anti_Candida": d["cand"],
                     "anti_MRSA": d["mrsa"],
                     "host": d["host"], "genus": d["genus"]})
    return rows


def validate(objs, sealed_tree):
    spec = importlib.util.spec_from_file_location(
        "bam", os.path.join(sealed_tree, "mamey", "bioactivity_metadata.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    ok = bad = 0; first_err = None
    for s, o in objs.items():
        try:
            m.normalize_bioactivity(o); ok += 1
        except Exception as e:
            bad += 1; first_err = first_err or f"{s}: {e}"
    return ok, bad, first_err

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recon", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strain", default=None)
    ap.add_argument("--min-hit", type=float, default=50.0)
    ap.add_argument("--validate", default=None, help="path to a sealed mamey tree to run normalize_bioactivity")
    ap.add_argument("--af-dossier-csv", default=None, help="also write the af-dossier --activity-table CSV here (strain,anti_Candida,anti_MRSA,host,genus)")
    a = ap.parse_args()
    objs = build(a.recon, a.strain, a.min_hit)
    os.makedirs(a.out, exist_ok=True)
    manifest = []
    for s, o in sorted(objs.items()):
        p = os.path.join(a.out, f"{s}_bioactivity_metadata.json")
        json.dump(o, open(p, "w"), indent=2)
        manifest.append({"strain": s, "state": o["metadata_state"], "n_assays": len(o["assays"]), "file": os.path.basename(p)})
    json.dump({"n_strains": len(objs), "min_hit": a.min_hit,
               "n_positive": sum(1 for o in objs.values() if o["metadata_state"]=="MEASURED_POSITIVE"),
               "records": manifest}, open(os.path.join(a.out, "MANIFEST.json"), "w"), indent=2)
    print(f"wrote {len(objs)} per-strain bioactivity_metadata_v1 objects -> {a.out}")
    if a.af_dossier_csv:
        import csv as _csv
        rows = build_af_dossier(a.recon, a.min_hit, a.strain)
        with open(a.af_dossier_csv, "w", newline="") as f:
            from mamey.csv_safety import SafeDictWriter
            w = SafeDictWriter(f, fieldnames=["strain","anti_Candida","anti_MRSA","host","genus"])
            w.writeheader()
            for r in rows: w.writerow(r)
        print(f"wrote af-dossier activity-table ({len(rows)} strains) -> {a.af_dossier_csv}")
    if a.validate:
        ok, bad, err = validate(objs, a.validate)
        print(f"validate against sealed engine: {ok} admitted, {bad} refused" + (f" (first: {err})" if err else ""))
        sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()

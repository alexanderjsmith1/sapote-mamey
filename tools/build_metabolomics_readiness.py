#!/usr/bin/env python3
"""build_metabolomics_readiness.py — deterministic writer for the Metabolomics Readiness (MR) deliverable.

Promotes docs/modules/DELIVERABLE_MetabolomicsReadiness.md from PROMPT_BACKED to SCHEMA_BACKED. For each BGC it
maps the broad compound class (from manifest products / closest-product) to the analytics defaults an analyst
needs before LC-MS/HRMS/fractionation: MW range, ionization mode, UV/detection handle, polarity, extraction
route, and dereplication target. Broad-class only and claim-safe — no exact masses, no compound identity.
Skip-not-fake: a class with no mapped default is emitted as 'class-default: unavailable', never invented.

Inputs (Mamey package):
  manifest.json -> bgcs[].{products, closest_candidate_kcb_product, product_claim_ceiling}

Outputs:
  <strain>_Metabolomics_Readiness.csv   +   <strain>_Metabolomics_Readiness.xlsx (sheet 'Metabolomics_Readiness')

Usage:
  python tools/build_metabolomics_readiness.py --package-dir <pkg> --out-dir <dir>
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, json, os
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

from _wbio import atomic_save


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# broad class -> analytics defaults. Claim-safe, class-level expectations only (not compound identities).
# polarity 'polar' rows carry the polar-compound caveat (reversed-phase LC-MS under-recovers them).
CLASS_DEFAULTS = {
    "nrps":         dict(mw="800-1600 Da", ion="ESI+ / ESI-", uv="weak end-absorbance; MS-led", polarity="medium", extraction="n-BuOH or EtOAc partition", derep="GNPS molecular networking; antiSMASH NP atlas"),
    "pks":          dict(mw="300-900 Da", ion="ESI+ / APCI+", uv="200-280 nm (chromophore-dependent)", polarity="medium-nonpolar", extraction="EtOAc partition", derep="GNPS; Dictionary of Natural Products"),
    "transat-pks":  dict(mw="600-1400 Da", ion="ESI+", uv="polyene 320-420 nm if conjugated", polarity="medium", extraction="EtOAc / n-BuOH", derep="GNPS; trans-AT PKS database (TransATor)"),
    "ripp":         dict(mw="1000-3000 Da", ion="ESI+ multiply-charged", uv="weak; MS/MS-led", polarity="polar (CAVEAT: RP under-recovery)", extraction="aqueous MeOH; SPE C18", derep="RiPPMiner; MS/MS fragment ladders"),
    "lanthipeptide":dict(mw="2000-4000 Da", ion="ESI+ multiply-charged", uv="weak", polarity="polar (CAVEAT)", extraction="aqueous MeOH; SPE", derep="RiPPMiner; dehydration mass ladders"),
    "terpene":      dict(mw="200-500 Da", ion="EI / APCI+ / GC-MS", uv="often UV-silent", polarity="nonpolar", extraction="hexane / EtOAc; consider GC-MS", derep="GC-MS NIST; terpene MS libraries"),
    "siderophore":  dict(mw="400-1000 Da", ion="ESI+; Fe-complex isotope pattern", uv="200-220 nm; CAS assay handle", polarity="polar (CAVEAT: RP under-recovery)", extraction="aqueous; XAD resin; CAS-guided", derep="Fe-isotope pattern; siderophore MS databases"),
    "glycopeptide": dict(mw="1400-2200 Da", ion="ESI+ multiply-charged", uv="280 nm (aromatic side chains)", polarity="medium-polar", extraction="aqueous MeOH; SPE", derep="GNPS; glycopeptide reference set"),
    "saccharide":   dict(mw="variable", ion="ESI+/-; consider derivatization", uv="weak (no chromophore)", polarity="polar (CAVEAT: RP under-recovery; consider HILIC)", extraction="aqueous; HILIC-LC", derep="GNPS; sugar MS libraries"),
    "betalactone":  dict(mw="200-500 Da", ion="ESI+/-", uv="weak", polarity="medium", extraction="EtOAc partition", derep="GNPS"),
    "arylpolyene":  dict(mw="500-900 Da", ion="ESI+/APCI", uv="strong 400-460 nm (conjugation)", polarity="nonpolar", extraction="EtOAc; light-protected", derep="UV-Vis signature; GNPS"),
    "nucleoside":   dict(mw="250-600 Da", ion="ESI+", uv="254-270 nm (base)", polarity="polar (CAVEAT)", extraction="aqueous MeOH; HILIC", derep="GNPS; nucleoside libraries"),
    "phosphonate":  dict(mw="150-500 Da", ion="ESI- (phosphonate)", uv="weak", polarity="polar (CAVEAT: 31P-NMR gate before any compound claim)", extraction="aqueous; ion-pair LC", derep="31P-NMR; phosphonate MS"),
    "enediyne":     dict(mw="600-1500 Da (warhead labile)", ion="ESI+ (handle gently)", uv="320-340 nm (chromophore)", polarity="medium", extraction="cold, light-protected EtOAc", derep="UV chromophore; cytotoxicity-guided"),
}

def base_class(products, closest):
    products = " ".join(products) if isinstance(products, list) else (products or "")
    closest = " ".join(closest) if isinstance(closest, list) else (closest or "")
    p = (products + " " + closest).lower()
    for k in ["transat", "enediyne", "phosphonate", "glycopeptide", "lanthi", "ripp", "siderophore",
              "arylpolyene", "nucleoside", "betalactone", "terpene", "saccharide", "nrps",
              "t1pks", "t2pks", "t3pks", "pks"]:
        if k in p:
            return {"transat": "transat-pks", "lanthi": "lanthipeptide",
                    "t1pks": "pks", "t2pks": "pks", "t3pks": "pks"}.get(k, k)
    return None


def locator(b):
    contig = b.get("contig") or b.get("node_id") or "?"
    reg = b.get("region_number") or b.get("antismash_region") or "?"
    return f"{b['bgc_id']} ({contig} · region{reg})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    mf = glob.glob(os.path.join(a.package_dir, "manifest.json"))
    if not mf:
        raise SystemExit("manifest.json not found in package dir")
    d = _read_json(mf[0])
    strain = d.get("strain_id") or "STRAIN"
    os.makedirs(a.out_dir, exist_ok=True)

    rows = []
    for b in d.get("bgcs", []):
        cls = base_class(b.get("products"), b.get("closest_candidate_kcb_product"))
        df = CLASS_DEFAULTS.get(cls)
        if df:
            rows.append({"locator": locator(b), "bgc_id": b["bgc_id"], "class": cls,
                         "MW_range": df["mw"], "ionization": df["ion"], "UV_handle": df["uv"],
                         "polarity": df["polarity"], "extraction_route": df["extraction"],
                         "dereplication_target": df["derep"],
                         "claim_ceiling": b.get("product_claim_ceiling") or "class-level only"})
        else:
            rows.append({"locator": locator(b), "bgc_id": b["bgc_id"], "class": (cls or b.get("products") or "unclassified"),
                         "MW_range": "class-default: unavailable", "ionization": "", "UV_handle": "",
                         "polarity": "", "extraction_route": "", "dereplication_target": "",
                         "claim_ceiling": b.get("product_claim_ceiling") or "class-level only"})

    csv_path = os.path.join(a.out_dir, f"{strain}_Metabolomics_Readiness.csv")
    # Empty-safe write (v9.7.114): a package with zero BGCs must write a valid header-only CSV,
    # not crash on rows[0].keys().
    _FIELDS = ["locator", "bgc_id", "class", "MW_range", "ionization", "UV_handle",
               "polarity", "extraction_route", "dereplication_target", "claim_ceiling"]
    fieldnames = list(rows[0].keys()) if rows else _FIELDS
    _tmp = csv_path + ".tmp"
    with open(_tmp, "w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
    os.replace(_tmp, csv_path)
    try:
        import openpyxl
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Metabolomics_Readiness"
        ws.append(fieldnames)
        for r in rows: ws.append([(", ".join(v) if isinstance(v,list) else v) for v in (r[k] for k in fieldnames)])
        xlsx_path = os.path.join(a.out_dir, f"{strain}_Metabolomics_Readiness.xlsx"); atomic_save(wb, xlsx_path)
    except Exception as e:
        xlsx_path = f"(xlsx skipped: {e})"

    mapped = sum(1 for r in rows if r["MW_range"] != "class-default: unavailable")
    caveat = sum(1 for r in rows if "CAVEAT" in (r["polarity"] or ""))
    emit(f"{strain}: {len(rows)} BGCs -> {mapped} class-mapped, {caveat} carry polar-compound caveat", f"  csv: {csv_path}\n  xlsx: {xlsx_path}", sep="\n")


if __name__ == "__main__":
    main()

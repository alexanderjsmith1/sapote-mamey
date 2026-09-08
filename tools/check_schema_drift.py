#!/usr/bin/env python3
"""check_schema_drift.py  (candidate patch G1)

Detect schema / engine-version drift across a set of Mamey sources **before** they are merged. Fail-closed:
exits non-zero the moment two sources disagree on schema version or manifest key signature, so a divergent
source can't be silently concatenated into the hub.

  python tools/check_schema_drift.py --packages run1/package run2/package ...
  python tools/check_schema_drift.py --manifests a/manifest.json b/manifest.json [--expect 9.7.24]

Drift dimensions checked:
  1. workflow_version  — the bundle schema each source was produced under.
  2. manifest key signature — the set of top-level manifest keys (a new/removed key = schema change).
  3. workbook sheet-code set — if a per-strain workbook is present beside the manifest.

This is a PRE-MERGE gate, mirroring the standing rule: normalize every source to one canonical schema
first; never naively concatenate divergent-schema tables.
"""
import argparse
import glob
import json
import os
import re
import sys


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)



def _load_manifest(path):
    if os.path.isdir(path):
        path = os.path.join(path, "manifest.json")
    return _read_json(path), path


def _sheet_codes(manifest_path):
    pkg = os.path.dirname(manifest_path)
    wbs = glob.glob(os.path.join(pkg, "*_5_workbook.xlsx"))
    if not wbs:
        return None
    try:
        import openpyxl
        wb = openpyxl.load_workbook(wbs[0], read_only=True)
        codes = tuple(sorted(wb.sheetnames))
        wb.close()
        return codes
    except Exception:
        return None


# An accession token is what makes a KCB claim traceable (MIBiG / GenBank / RefSeq).
ACCESSION = re.compile(r'\b(BGC\d{6,7}|GC[AF]_\d+|N[ZCT]_[A-Z0-9]+|[A-Z]{1,2}\d{5,8})\b')


def _records(manifest_path, manifest):
    """Return (records, degraded).

    records = [(bgc_id, kcb_top_str), ...] from *_records.json (the more-authoritative, complete
    source) when present and parseable; otherwise from the manifest's own (possibly thinner)
    "bgcs" list.

    degraded = False normally, or (records_json_path, error_str) when a *_records.json file was
    found but could NOT be read/parsed. BC2-SD-01 (v9.7.395): this case used to `except Exception:
    pass` and silently fall back to manifest.bgcs with zero signal. A corrupted/truncated
    records.json — the richer source, more likely to hold the full BGC set — degraded checks #4
    (primary-key uniqueness) and #5 (KCB provenance) below to whatever subset the thinner manifest
    happened to carry, and this fail-closed pre-merge gate (its own docstring: "exits non-zero the
    moment two sources disagree") reported a clean "no drift — safe to merge" over data it never
    actually examined. Reproduced: a manifest.bgcs with one clean record alongside a corrupted
    records.json that (if parsed) would have surfaced a genuine un-provenanced KCB claim → the
    tool exited 0."""
    pkg = os.path.dirname(manifest_path)
    rj = glob.glob(os.path.join(pkg, "*_records.json"))
    if rj:
        try:
            recs = _read_json(rj[0]).get("records", [])
            return [(r.get("bgc_id"), str(r.get("kcb_top") or "")) for r in recs], False
        except Exception as e:
            fallback = [(b.get("bgc_id"), str(b.get("kcb_top") or "")) for b in manifest.get("bgcs", [])]
            return fallback, (rj[0], f"{type(e).__name__}: {e}")
    return [(b.get("bgc_id"), str(b.get("kcb_top") or "")) for b in manifest.get("bgcs", [])], False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packages", nargs="*", default=[])
    ap.add_argument("--manifests", nargs="*", default=[])
    ap.add_argument("--expect", default=None, help="canonical workflow_version to require (e.g. 9.7.24)")
    a = ap.parse_args()

    sources = list(a.packages) + list(a.manifests)
    if len(sources) < 1:
        sys.exit("nothing to check: pass --packages or --manifests")

    rows = []
    for s in sources:
        try:
            man, mpath = _load_manifest(s)
        except Exception as e:
            rows.append({"src": s, "error": str(e)})
            continue
        records, records_degraded = _records(mpath, man)
        rows.append({
            "src": os.path.basename(os.path.dirname(mpath)) or mpath,
            "strain": man.get("strain_id", "?"),
            "workflow_version": man.get("workflow_version", "MISSING"),
            "key_sig": tuple(sorted(man.keys())),
            "sheets": _sheet_codes(mpath),
            "records": records,
            "records_degraded": records_degraded,
        })

    sys.stdout.write((f"# Schema-drift check — {len(rows)} source(s)\n") + "\n")
    errs = [r for r in rows if "error" in r]
    for r in errs:
        sys.stdout.write((f"  ✗ UNREADABLE  {r['src']}: {r['error']}") + "\n")
    good = [r for r in rows if "error" not in r]

    drift = bool(errs)

    # 0. records.json integrity — BC2-SD-01 (v9.7.395): a source whose *_records.json exists but
    # failed to parse fell back to manifest.bgcs (possibly incomplete) with no signal; the
    # primary-key-uniqueness (#4) and KCB-provenance (#5) checks below then silently examine a
    # degraded data set. Surfaced here and forced fail-closed, matching this gate's own stated
    # design ("Fail-closed: exits non-zero the moment two sources disagree").
    degraded = [r for r in good if r["records_degraded"]]
    if degraded:
        drift = True
        sys.stdout.write(("## records.json integrity") + "\n")
        for r in degraded:
            rj_path, err = r["records_degraded"]
            sys.stdout.write((f"  ✗ UNREADABLE {os.path.basename(rj_path)} for {r['strain']}: {err}") + "\n")
            sys.stdout.write((f"    fell back to manifest.bgcs — primary-key-uniqueness and KCB-provenance "
                  f"checks below may be INCOMPLETE for this source") + "\n")
        sys.stdout.write("\n")

    # 1. workflow_version
    versions = {}
    for r in good:
        versions.setdefault(r["workflow_version"], []).append(r["strain"])
    sys.stdout.write(("\n## workflow_version") + "\n")
    for v, strains in sorted(versions.items()):
        sys.stdout.write((f"  {v:12} ← {len(strains)} source(s): {', '.join(strains[:8])}") + "\n")
    if len(versions) > 1:
        drift = True
        sys.stdout.write(("  ⚠ VERSION DRIFT — sources span multiple schema versions.") + "\n")
    if a.expect:
        off = [v for v in versions if v != a.expect]
        if off:
            drift = True
            sys.stdout.write((f"  ⚠ EXPECTED {a.expect} — but found {', '.join(off)}.") + "\n")

    # 2. manifest key signature
    sigs = {}
    for r in good:
        sigs.setdefault(r["key_sig"], []).append(r["strain"])
    sys.stdout.write(("\n## manifest key signature") + "\n")
    if not sigs:
        sys.stdout.write(("  (no readable sources)") + "\n")
    elif len(sigs) > 1:
        drift = True
        base = max(sigs, key=lambda k: len(sigs[k]))  # majority signature
        sys.stdout.write((f"  ⚠ KEY-SIGNATURE DRIFT — {len(sigs)} distinct signatures.") + "\n")
        for sig, strains in sigs.items():
            if sig == base:
                continue
            missing = set(base) - set(sig)
            extra = set(sig) - set(base)
            sys.stdout.write((f"   {', '.join(strains[:5])}: "
                  f"missing={sorted(missing) or '—'} extra={sorted(extra) or '—'}") + "\n")
    else:
        sys.stdout.write((f"  ok — all {len(good)} sources share one signature ({len(next(iter(sigs)))} keys).") + "\n")

    # 3. workbook sheet codes
    sheetsets = {}
    for r in good:
        if r["sheets"] is not None:
            sheetsets.setdefault(r["sheets"], []).append(r["strain"])
    if len(sheetsets) > 1:
        drift = True
        sys.stdout.write(("\n## workbook sheet-codes\n  ⚠ SHEET-SET DRIFT across workbooks.") + "\n")
        base = max(sheetsets, key=lambda k: len(sheetsets[k]))
        for ss, strains in sheetsets.items():
            if ss == base:
                continue
            sys.stdout.write((f"   {', '.join(strains[:5])}: Δ={sorted(set(base) ^ set(ss))}") + "\n")

    # 4. primary-key uniqueness — global strain:BGC_ID must be unique across all sources
    sys.stdout.write(("\n## primary-key uniqueness (strain:BGC_ID)") + "\n")
    seen, dups = {}, []
    total_keys = 0
    for r in good:
        for bgc_id, _ in r["records"]:
            if not bgc_id:
                continue
            total_keys += 1
            key = f"{r['strain']}:{bgc_id}"
            if key in seen:
                dups.append(key)
            seen[key] = seen.get(key, 0) + 1
    if dups:
        drift = True
        sys.stdout.write((f"  ⚠ KEY COLLISION — {len(dups)} duplicate strain:BGC_ID key(s): "
              f"{', '.join(sorted(set(dups))[:8])}") + "\n")
    else:
        sys.stdout.write((f"  ok — {total_keys} keys across {len(good)} source(s), all unique.") + "\n")

    # 5. KCB provenance — every non-empty KCB claim must carry a traceable accession token
    sys.stdout.write(("\n## KCB provenance") + "\n")
    unprov = []
    kcb_claims = 0
    for r in good:
        for bgc_id, kcb in r["records"]:
            if kcb.strip():
                kcb_claims += 1
                if not ACCESSION.search(kcb):
                    unprov.append(f"{r['strain']}:{bgc_id} → '{kcb[:40]}'")
    if unprov:
        drift = True
        sys.stdout.write((f"  ⚠ UN-PROVENANCED KCB — {len(unprov)}/{kcb_claims} claim(s) lack an accession token:") + "\n")
        for u in unprov[:8]:
            sys.stdout.write((f"    {u}") + "\n")
    else:
        sys.stdout.write((f"  ok — all {kcb_claims} KCB claim(s) carry a traceable accession.") + "\n")

    sys.stdout.write(("\n" + ("✗ DRIFT DETECTED — do NOT merge until normalized to one schema."
                  if drift else "✓ no drift — sources are schema-aligned; safe to merge.")) + "\n")
    sys.exit(1 if drift else 0)


if __name__ == "__main__":
    main()

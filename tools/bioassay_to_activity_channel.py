#!/usr/bin/env python3
"""bioassay_to_activity_channel — emit MEASURED fraction-screen data as Sapote-Mamey
`bioactivity_metadata_v1` objects (docs/BIOACTIVITY_METADATA_CONTRACT.md), one per strain, for
`mamey_run.py run --bioactivity-json <json>`. STRAIN-LEVEL, EXTRACT-LEVEL ONLY: inhibition%/tiers go in
free-form assays[]; no BGC is credited; capacity != production; the engine treats it as score-neutral context.

Usage:
  python3 bioassay_to_activity_channel.py --recon <fraction_concentration_response_48h.csv> --out <dir> \
      [--strain AS-XXX] [--min-hit 50.0] [--validate <path-to-sealed-mamey-tree>]
"""
import argparse, csv, json, os, sys, importlib.util, math, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.path_safety import safe_label, contained_output_path

CREDIBLE = {"STRONG_DOSE_CONSISTENT", "SUPPORTED_MULTI_CONCENTRATION_HIT"}

# Screening-not-validated caveat carried on every emitted object (preliminary single-replicate 384-well data).
SCREEN_WARNINGS = [
    "PRELIMINARY_SINGLE_REPLICATE_SCREEN: 384-well fraction screen with no biological replication; "
    "dose-response inversions and single-concentration spikes are expected assay artifacts, not validated activity.",
    "EXTRACT_LEVEL_ONLY: whole-fraction (2-10+ metabolite mixture) strain-level observation; "
    "not attributed to any BGC; capacity is not production; judgment deferred.",
]

def fnum(x):
    try:
        value = float(x)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _read_evidence(recon, only=None):
    rows = []
    with open(recon, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"strain_id", "organism", "screening_pattern", "max_inhibition_raw"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("screening input lacks required evidence columns")
        for row in reader:
            if None in row:
                raise ValueError("screening row has more fields than its declared header")
            sid = (row.get("strain_id") or "").strip()
            target = (row.get("organism") or "").strip()
            if not sid or not target:
                raise ValueError("screening evidence row lacks strain or target identity")
            if not only or sid == only:
                rows.append(dict(row, strain_id=sid, organism=target))
    return rows


def _adjudicate(rows, min_hit):
    """One conservative screening-state rule shared by both exports.

    A credible qualifying observation survives artifact rows. A negative requires
    every supplied target row to support a below-threshold observation. Unsupported
    or unparseable evidence remains UNKNOWN; no missing value becomes a negative.
    """
    if not math.isfinite(min_hit) or min_hit < 0:
        raise ValueError("min_hit must be finite and nonnegative")
    states = []
    for row in rows:
        value = fnum(row.get("max_inhibition_raw"))
        tier = (row.get("screening_pattern") or "").strip()
        if value is None:
            states.append("UNKNOWN")
        elif tier in CREDIBLE:
            states.append("POSITIVE" if value >= min_hit else "NEGATIVE")
        elif tier == "NO_50PCT_OBSERVATION" and value < min_hit:
            states.append("NEGATIVE")
        else:
            states.append("UNKNOWN")
    if "POSITIVE" in states:
        return "POSITIVE"
    if states and all(state == "NEGATIVE" for state in states):
        return "NEGATIVE"
    return "UNKNOWN"


def build(recon, only=None, min_hit=50.0):
    _adjudicate([], min_hit)
    source_rows = _read_evidence(recon, only)
    canonical_source = json.dumps(sorted(source_rows, key=lambda r: json.dumps(r, sort_keys=True)), sort_keys=True)
    source_locator = "screen-evidence-sha256/" + hashlib.sha256(canonical_source.encode()).hexdigest()
    per = {}
    for row in source_rows:
        per.setdefault(row["strain_id"], {}).setdefault(row["organism"].casefold(), []).append(row)
    objs = {}
    for sid, targets in sorted(per.items()):
        assays = []
        all_rows = []
        for target, rows in sorted(targets.items()):
            state = _adjudicate(rows, min_hit)
            # Choose display evidence independently from adjudication; prefer a
            # credible row, then its value, and break equal ties on source fields.
            ordered = sorted(rows, key=lambda row: (
                (row.get("screening_pattern") or "").strip() in CREDIBLE,
                fnum(row.get("max_inhibition_raw")) if fnum(row.get("max_inhibition_raw")) is not None else -math.inf,
                json.dumps(row, sort_keys=True)), reverse=True)
            row = ordered[0]
            mx = fnum(row.get("max_inhibition_raw"))
            assays.append({
                "assay": "fraction_screen_multidose_48h",
                "target": min(r["organism"] for r in rows),
                "screening_observation_state": state,
                "best_inhibition_pct": round(mx, 1) if mx is not None else None,
                "inhibition_15ugml": fnum(row.get("inhibition_15ug_ml")),
                "doses_ugml": [120, 60, 30, 15],
                "dose_inhibition_pct": [fnum(row.get(key)) for key in
                    ("inhibition_120ug_ml", "inhibition_60ug_ml", "inhibition_30ug_ml", "inhibition_15ug_ml")],
                "screening_tier": (row.get("screening_pattern") or "").strip(),
                "best_fraction_sample": (row.get("fraction_sample_key") or "").strip(),
                "doses_at_or_above_50pct": row.get("concentrations_at_or_above_50pct"),
                "spearman_dose_response": fnum(row.get("spearman_concentration_response")),
                "source_rows": sorted(rows, key=lambda item: json.dumps(item, sort_keys=True)),
            })
            all_rows.extend(rows)
        state = _adjudicate(all_rows, min_hit)
        objs[sid] = {
            "schema_version": "bioactivity_metadata_v1",
            "metadata_state": {"POSITIVE": "MEASURED_POSITIVE", "NEGATIVE": "MEASURED_NEGATIVE", "UNKNOWN": "SUPPLIED_UNKNOWN"}[state],
            "observation_state": state,
            "usage_scope": "PRODUCTION",
            "assays": assays,
            "compound_linkage": "NOT_ESTABLISHED",
            "receipt_locator": source_locator,
            "warnings": list(SCREEN_WARNINGS),
        }
    return objs


def build_af_dossier(recon, min_hit=50.0, only=None):
    """Export the same screening ruling; unknown evidence stays explicit."""
    _adjudicate([], min_hit)
    per = {}
    for row in _read_evidence(recon, only):
        per.setdefault(row["strain_id"], []).append(row)
    output = []
    for sid, rows in sorted(per.items()):
        values = {}
        for needle, field in (("candida", "anti_Candida"), ("mrsa", "anti_MRSA")):
            target_rows = [row for row in rows if needle in row["organism"].casefold()]
            values[field] = _adjudicate(target_rows, min_hit).lower() if target_rows else "not_tested"
        for source, field in (("host", "host"), ("genus_16s", "genus")):
            admitted = {(row.get(source) or "").strip() for row in rows if (row.get(source) or "").strip()}
            values[field] = next(iter(admitted)) if len(admitted) == 1 else ""
        output.append(dict(strain=sid, **values))
    return output


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

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--recon", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strain", default=None)
    ap.add_argument("--min-hit", type=float, default=50.0)
    ap.add_argument("--validate", default=None, help="path to a sealed mamey tree to run normalize_bioactivity")
    ap.add_argument("--af-dossier-csv", default=None, help="also write the af-dossier --activity-table CSV here (strain,anti_Candida,anti_MRSA,host,genus)")
    a = ap.parse_args(argv)
    try:
        source_before = hashlib.sha256(Path(a.recon).read_bytes()).hexdigest()
        objs = build(a.recon, a.strain, a.min_hit)
        af_rows = build_af_dossier(a.recon, a.min_hit, a.strain) if a.af_dossier_csv else None
        if hashlib.sha256(Path(a.recon).read_bytes()).hexdigest() != source_before:
            raise ValueError("source changed during evidence admission")
        normalized = set()
        outputs = {}
        for sid in objs:
            safe_label(sid, field="strain_id")
            if (Path(a.out) / f"{sid}_bioactivity_metadata.json").is_symlink():
                raise ValueError("output destination must not be a symlink")
            key = sid.casefold()
            if key in normalized:
                raise ValueError("case-normalized strain output collision")
            normalized.add(key)
            outputs[sid] = contained_output_path(a.out, sid, "_bioactivity_metadata.json")
        all_paths = [*outputs.values(), Path(a.out).resolve() / "MANIFEST.json"]
        if a.af_dossier_csv:
            if not Path(a.af_dossier_csv).parent.is_dir():
                raise ValueError("dossier output parent must exist before evidence publication")
            if Path(a.af_dossier_csv).is_symlink():
                raise ValueError("dossier destination must not be a symlink")
            all_paths.append(Path(a.af_dossier_csv).resolve())
        if len(set(all_paths)) != len(all_paths):
            raise ValueError("output destinations collide")
        for path in all_paths:
            if path.exists() or path.is_symlink() or path == Path(a.recon).resolve():
                raise ValueError("output already exists or aliases the source; use fresh destinations")
    except ValueError as exc:
        ap.error(str(exc))
    # Validate and serialize every artifact before the first final file write.
    if a.validate:
        ok, bad, err = validate(objs, a.validate)
        if bad:
            ap.error(f"bioactivity validation refused {bad} object(s): {err}")
    payloads = {}
    manifest = []
    for sid, obj in sorted(objs.items()):
        payloads[outputs[sid]] = (json.dumps(obj, indent=2, allow_nan=False) + "\n").encode()
        manifest.append({"strain": sid, "state": obj["metadata_state"], "n_assays": len(obj["assays"]), "file": outputs[sid].name})
    payloads[Path(a.out).resolve() / "MANIFEST.json"] = (json.dumps({
        "n_strains": len(objs), "min_hit": a.min_hit, "source_sha256": source_before,
        "n_positive": sum(obj["metadata_state"] == "MEASURED_POSITIVE" for obj in objs.values()),
        "records": manifest}, indent=2, allow_nan=False) + "\n").encode()
    if a.af_dossier_csv:
        import io
        from mamey.csv_safety import SafeDictWriter
        buffer = io.StringIO(newline="")
        writer = SafeDictWriter(buffer, fieldnames=["strain", "anti_Candida", "anti_MRSA", "host", "genus"])
        writer.writeheader()
        writer.writerows(af_rows)
        payloads[Path(a.af_dossier_csv).resolve()] = buffer.getvalue().encode()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    from mamey.output_transaction import publish_payloads
    publish_payloads(payloads)
    print(f"wrote {len(objs)} per-strain bioactivity_metadata_v1 objects -> {a.out}")
    if a.af_dossier_csv:
        print(f"wrote af-dossier activity-table ({len(af_rows)} strains) -> {a.af_dossier_csv}")
    return 0

if __name__ == "__main__":
    main()

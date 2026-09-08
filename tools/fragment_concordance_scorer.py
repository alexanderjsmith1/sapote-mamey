#!/usr/bin/env python3
"""
fragment_concordance_scorer.py — score a strain's observed BGC fragments against the reference panel.

The consumer the reference panel feeds. For each observed fragment (a BGC, possibly a split-cluster
fragment) it computes architectural concordance against each panel reference's architecture_signature
and reports the best match + a tier.

CLAIM-SAFE. Concordance is a SIMILARITY signal over architecture shape — region tokens, domain
counts (KS / NRPS-C / NRPS-A), the diagnostic marker set, and size. It is NOT identity, NOT a
production claim, and not KCB. T43 markers are [E-signal]. Marker credit uses each reference's
ADJUDICATED expected_marker_set; references whose scanned marker is PENDING contribute no marker
credit (we do not reward matching an unconfirmed marker). Weights/thresholds are a documented
heuristic rubric, not a calibrated probability.

Input (one of):
  --observed obs.json : [{"id","region","pks_ks","nrps_c","nrps_a","markers":[...],"size_kb","edge"}, ...]
  --ledger ledger.csv : reference_panel_ledger.py output (obs_region_type/obs_pks_ks/.../cmp_t43_markers)
Output: per-fragment best match (+ top-N) as CSV.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, json, sys, os
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
from statistics import mean

W = {"region": 0.30, "markers": 0.30, "domains": 0.25, "size": 0.15}
TIERS = [(0.75, "STRONG"), (0.50, "MODERATE"), (0.30, "WEAK"), (0.0, "NONE")]
CLAIM_SAFE = ("Architectural concordance = similarity over region/domain-shape/marker-set/size; "
              "NOT identity or production. T43 markers [E-signal]. References to a pending marker give no marker credit.")

def _tokens(region) -> set:
    if not region: return set()
    return {t.strip().lower() for t in str(region).replace(",", ";").split(";") if t.strip()}

def _jaccard(a: set, b: set) -> float:
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def _count_sim(o, r) -> float:
    if o is None or r is None: return 0.5            # neutral when a count is unknown
    o, r = int(o), int(r)
    if o == 0 and r == 0: return 1.0
    return 1.0 - min(1.0, abs(o - r) / max(1, o, r))

def _marker_concordance(obs: set, ref: set) -> float:
    if not ref:                                       # reference asserts no diagnostic markers
        return 1.0 if not obs else 0.4                # obs-with-markers is a partial mismatch, not zero
    return len(obs & ref) / len(ref)                  # fraction of the reference's markers observed

def _marker_status(entry: dict) -> str:
    note = (entry.get("marker_divergence_note") or "")
    if note.startswith("RESOLVED"): return "RESOLVED"
    if note.startswith("PENDING"): return "PENDING"
    return entry.get("marker_set_source") or "none"

def ref_signature(entry: dict) -> dict:
    a = entry.get("architecture_signature") or {}
    size = a.get("size_kb") or entry.get("found_size_kb") or entry.get("expected_size_kb")
    status = _marker_status(entry)
    markers = set(entry.get("expected_marker_set") or [])
    # Claim-safety: pending/unadjudicated marker references contribute no marker credit.
    # They can still match on region/domain/size shape, but not on expected_marker_set.
    if str(status).upper().startswith("PENDING"):
        markers = set()
    return {
        "compound": entry.get("compound") or entry.get("name"),
        "region": _tokens(a.get("region", "")),
        "pks_ks": a.get("pks_ks"), "nrps_c": a.get("nrps_c"), "nrps_a": a.get("nrps_a"),
        "size_kb": size,
        "markers": markers,   # adjudicated truth only; pending marker refs get no marker credit
        "marker_status": status,
        "reference_tier": entry.get("reference_tier", "CURATED-PANEL"),
        "provenance": entry.get("provenance", "curated"),
        "accession": entry.get("mibig_accession") or entry.get("accession"),
    }

def obs_signature(row: dict) -> dict:
    mk = row.get("markers")
    if isinstance(mk, str): mk = [m.strip() for m in mk.replace(",", ";").split(";") if m.strip()]
    mk = [m.strip().split("_")[0] for m in (mk or []) if m.strip().upper().startswith("T43")]  # normalize T43-HAL_halogenase -> T43-HAL
    return {
        "id": row.get("id") or row.get("bgc_uid") or row.get("bgc_id") or "?",
        "region": _tokens(row.get("region", "")),
        "pks_ks": row.get("pks_ks"), "nrps_c": row.get("nrps_c"), "nrps_a": row.get("nrps_a"),
        "size_kb": row.get("size_kb"),
        "markers": set(mk or []),
    }

def score_concordance(obs: dict, ref: dict) -> dict:
    rj = _jaccard(obs["region"], ref["region"])
    mk = _marker_concordance(obs["markers"], ref["markers"])
    dom = mean([_count_sim(obs["pks_ks"], ref["pks_ks"]),
                _count_sim(obs["nrps_c"], ref["nrps_c"]),
                _count_sim(obs["nrps_a"], ref["nrps_a"])])
    if obs["size_kb"] and ref["size_kb"]:
        o, r = float(obs["size_kb"]), float(ref["size_kb"]); sz = min(o, r) / max(o, r)
    else:
        sz = 0.5
    score = round(W["region"]*rj + W["markers"]*mk + W["domains"]*dom + W["size"]*sz, 3)
    tier = next(name for thr, name in TIERS if score >= thr)
    return {"score": score, "tier": tier, "region_jaccard": round(rj, 3),
            "marker_concordance": round(mk, 3), "domain_concordance": round(dom, 3),
            "size_concordance": round(sz, 3)}

def best_match(obs: dict, panel: list, top: int = 3) -> dict:
    scored = []
    for ref in panel:
        s = score_concordance(obs, ref)
        scored.append((s["score"], ref, s))
    if not scored:
        return {"id": obs["id"], "best_compound": "NO_PANEL", "best_accession": None,
                "reference_tier": None, "ref_marker_status": "none",
                "score": 0.0, "tier": "NONE", "region_jaccard": 0.0,
                "marker_concordance": 0.0, "domain_concordance": 0.0,
                "size_concordance": 0.0, "top_matches": ""}
    scored.sort(key=lambda x: x[0], reverse=True)
    bs, bref, bsc = scored[0]
    return {"id": obs["id"], "best_compound": bref["compound"], "best_accession": bref.get("accession"),
            "reference_tier": bref.get("reference_tier"), "ref_marker_status": bref["marker_status"], **bsc,
            "top_matches": "; ".join(f"{r['compound']}:{sc:.2f}" for sc, r, _ in scored[:top])}

def mibig_ref_signature(ae: dict) -> dict:
    a = ae.get("architecture_signature") or {}
    comps = ae.get("compounds") or []
    adjud = ae.get("reference_tier") == "CURATED-ADJUDICATED"
    return {
        "compound": (comps[0] if comps else ae.get("accession")),
        "region": _tokens(a.get("region", "")),
        "pks_ks": a.get("pks_ks"), "nrps_c": a.get("nrps_c"), "nrps_a": a.get("nrps_a"),
        "size_kb": a.get("size_kb"),
        "markers": set(ae.get("expected_marker_set") or []),
        "marker_status": "ADJUDICATED" if adjud else "AUTO",
        "reference_tier": ae.get("reference_tier", "MIBIG-AUTO"),
        "provenance": ae.get("provenance", "MIBiG-4.0-auto"),
        "accession": ae.get("accession"),
        "domain_of_life": (ae.get("taxonomy") or {}).get("domain_of_life"),
    }

def load_mibig_space(index_path, adj_path=None, status_keep=None) -> list:
    """MIBiG index -> adjudicated reference space (curated judgment overlaid by accession).
    status_keep: optional set of mibig_status values to retain (e.g. {"active"})."""
    from mamey.adjudication import load_adjudications, adjudicate
    idx = json.loads(Path(index_path).read_text(encoding="utf-8"))
    by = load_adjudications(adj_path) if (adj_path and Path(adj_path).exists()) else {}
    entries = idx.get("entries", [])
    if status_keep:
        entries = [e for e in entries if e.get("mibig_status") in status_keep]
    return [mibig_ref_signature(adjudicate(e, by)) for e in entries if (e.get("architecture_signature") or {}).get("region")]

def load_panel(library_path: Path) -> list:
    d = json.loads(library_path.read_text(encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("entries", d.get("references", []))
    return [ref_signature(e) for e in items if e.get("architecture_signature")]

def _rows_from_ledger(p: Path) -> list:
    out = []
    for r in csv.DictReader(p.open(encoding="utf-8")):
        mk = r.get("cmp_t43_markers") or r.get("obs_t43_markers") or r.get("cmp_t43") or ""
        out.append({"id": r.get("bgc_uid") or r.get("bgc_id") or r.get("id"),
                    "region": r.get("obs_region_type", ""), "pks_ks": r.get("obs_pks_ks") or None,
                    "nrps_c": r.get("obs_nrps_c") or None, "nrps_a": r.get("obs_nrps_a") or None,
                    "size_kb": r.get("obs_size_kb") or None, "markers": mk, "edge": r.get("obs_edge_status")})
    return out

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Score observed BGC fragments against the reference panel.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--observed", help="JSON list of observed fragment signatures")
    g.add_argument("--ledger", help="reference_panel_ledger.py CSV (obs_* columns)")
    ap.add_argument("--library", default=str(Path(__file__).resolve().parent.parent / "mamey" / "data" / "reference_bgc_library.json"))
    _D = Path(__file__).resolve().parent.parent / "mamey" / "data" / "mibig"
    ap.add_argument("--mibig-index", nargs="?", const=str(_D / "mibig_reference_index.bacterial.json"),
                    help="use the MIBiG base (adjudicated) as the reference space; bare flag = bundled bacterial cut")
    ap.add_argument("--adjudications", default=str(_D / "adjudications.json"))
    ap.add_argument("--include-fungal", action="store_true", help="also score against the fungal (Eukaryota) MIBiG cut")
    ap.add_argument("--mibig-status", default=None, help="comma list of mibig_status values to keep (e.g. active); default all")
    ap.add_argument("--top", type=int, default=3); ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.mibig_index:
        keep = {x.strip() for x in a.mibig_status.split(",")} if a.mibig_status else None
        panel = load_mibig_space(a.mibig_index, a.adjudications, keep)
        if a.include_fungal:
            fp = _D / "mibig_reference_index.fungal.json"
            if fp.exists(): panel += load_mibig_space(str(fp), a.adjudications, keep)
    else:
        panel = load_panel(Path(a.library))
    if a.observed:
        rows = json.loads(Path(a.observed).read_text(encoding="utf-8"))
    else:
        rows = _rows_from_ledger(Path(a.ledger))
    results = [best_match(obs_signature(r), panel, a.top) for r in rows]
    cols = ["id", "best_compound", "best_accession", "reference_tier", "score", "tier",
            "region_jaccard", "marker_concordance", "domain_concordance", "size_concordance",
            "ref_marker_status", "top_matches"]
    # Build in memory, then atomic-write (file) or stream to stdout — a killed file write never
    # leaves a half-written CSV (v9.7.115).
    import io as _io
    _buf = _io.StringIO()
    _buf.write(f"# {CLAIM_SAFE}\n")
    w = _SafeDictWriter(_buf, fieldnames=cols, extrasaction="ignore"); w.writeheader()
    for r in results: w.writerow(r)
    if a.out:
        atomic_write_text(a.out, _buf.getvalue())
        emit(f"  wrote {len(results)} fragment concordance rows -> {a.out}")
    else:
        sys.stdout.write(_buf.getvalue())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

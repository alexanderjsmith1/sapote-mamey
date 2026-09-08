"""mamey/nrps_predictions.py — recover antiSMASH NRPS prediction data the pipeline drops.

Patch G (Tier 1). antiSMASH computes, and stores in the run JSON, three things the engine
currently ignores:

  1. per-A-domain substrate calls (nrpys / Stachelhaus aa10 signature + best-match substrate +
     score, plus a physiochemical_class fallback) together with antiSMASH's separate consensus
     call. These streams can agree, one can be uninformative, or they can conflict; conflicts are
     preserved rather than silently resolved in favor of one predictor;
  2. the assembled `region_predictions.polymer` (ordered monomers, D-configuration marked) and its
     `smiles`;
  3. the candidate-cluster `kind` + protocluster count per region — antiSMASH's own "this region is
     >=2 BGCs" (over-merge) signal.

Covers both NRPS A-domains (Stachelhaus amino-acid call) and PKS cis-AT domains (Minowa extender-unit
call: malonyl/methylmalonyl/… -CoA) — the latter matters for PKS-heavy taxa (Streptomyces). PKS
confidence is read from the top1-vs-top2 Minowa *margin* (absolute Minowa scores are not comparable
across domains).

KNOWN LIMITATION: trans-AT PKS, where the AT sits on a separate protein and the extender comes from
`nrps_pks.consensus_transat` rather than a per-module PKS_AT domain, is NOT yet captured. It was empty
in the strains tested (AS-XXX, AS-XXX) so a fix could not be validated against real data; deferred
until a strain with populated `consensus_transat` is available.

This module reads the predictions straight from the antiSMASH JSON, so it is independent of
`--json-evidence` mode (these are small per-region summaries, not the large evidence arrays that flag
guards). It is claim-safe: A-domain/AT calls are antiSMASH-inferred specificity (similarity-level),
never product identity; polymers/SMILES are predictions, not isolated structures.

Wire-in: call `write_nrps_prediction_csvs(records, package_dir, strain_id)` from the package builder
after the JSON records are loaded (see the diff in AS-XXX_PATCH_G_diff.md).
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter  # v9.7.409 export-injection: CSV formula-cell guard
except ImportError:  # module loaded by file path without a parent package (tests do this)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter
import json
import os
import re
from typing import Any


_ADOM_RE = re.compile(r"nrpspksdomains_(?P<locus>.+?)_(?P<dom>AMP-binding|A-OX)\.(?P<num>\d+)$")
_AT_RE = re.compile(r"nrpspksdomains_(?P<locus>.+?)_PKS_AT\.(?P<num>\d+)$")


def _stachelhaus_call(nrpys: dict) -> tuple[str, float | None, str, list[str]]:
    """Return (substrate, score, physiochemical_class, physiochemical_substrates).

    substrate is the best Stachelhaus match (resolves GBK `X`); score is aa10_score (0..1).
    Falls back to '' substrate when no match, but still returns the physiochemical bracket.
    """
    sub, score = "", None
    matches = nrpys.get("stachelhaus_matches") or []
    if matches:
        m0 = matches[0]
        subs = m0.get("substrates") or []
        if subs:
            sub = subs[0].get("short") or subs[0].get("long") or ""
        score = m0.get("aa10_score")
    pc = nrpys.get("physiochemical_class") or {}
    pc_name = pc.get("name", "")
    pc_subs = [s.get("short", "") for s in (pc.get("substrates") or [])][:6]
    return sub, score, pc_name, pc_subs


def _confidence(score: float | None) -> str:
    """NRPS Stachelhaus aa10_score is 0..1."""
    if score is None:
        return "none"
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "moderate"
    return "low"


_UNINFORMATIVE_SUBSTRATES = {"", "-", "?", "N/A", "NA", "NONE", "UNKNOWN", "X"}


def _informative_substrate(value: Any) -> bool:
    """True when an NRPS substrate call is more informative than an unknown sentinel."""
    return str(value or "").strip().upper() not in _UNINFORMATIVE_SUBSTRATES


def _nrps_agreement_state(consensus: Any, stachelhaus: Any) -> tuple[str, str]:
    """Classify the relationship between two antiSMASH NRPS substrate streams.

    Both calls remain similarity-level predictions.  The disposition controls reporting only;
    it never chooses a biological monomer identity.
    """
    consensus_value = str(consensus or "").strip()
    stachelhaus_value = str(stachelhaus or "").strip()
    has_consensus = _informative_substrate(consensus_value)
    has_stachelhaus = _informative_substrate(stachelhaus_value)
    if has_consensus and has_stachelhaus:
        if consensus_value.casefold() == stachelhaus_value.casefold():
            return "SUBSTRATE_PREDICTION_CONCORDANT", "CONCORDANT_SIMILARITY_LEVEL_CALL"
        return "SUBSTRATE_PREDICTION_CONFLICT", "RETAIN_BOTH_CALLS_SUBSTRATE_UNRESOLVED"
    if has_stachelhaus:
        return "STACHELHAUS_RESOLVES_UNINFORMATIVE_CONSENSUS", "STACHELHAUS_ONLY_SIMILARITY_LEVEL_CALL"
    if has_consensus:
        return "CONSENSUS_ONLY_STACHELHAUS_UNRESOLVED", "CONSENSUS_ONLY_SIMILARITY_LEVEL_CALL"
    return "BOTH_SUBSTRATE_PREDICTIONS_UNINFORMATIVE", "SUBSTRATE_UNRESOLVED"


def _at_call(pred: dict) -> tuple[str, float | None, float | None, str, list[str]]:
    """PKS AT extender-unit call. Returns (extender, top_score, margin, signature_extender, top3_alts).

    minowa_at.predictions is a ranked list of [name, score] in raw Minowa units (NOT 0..100 — they
    vary by domain and can exceed 100), so confidence is read from the top1-vs-top2 *margin*, not the
    absolute score. The ATSignature 'signature' method gives a separate best extender (usually mal/mmal).
    """
    ext, score, margin = "", None, None
    alts: list[str] = []
    minowa = (pred.get("minowa_at") or {}).get("predictions") or []
    if minowa:
        ext = minowa[0][0] if minowa[0] else ""
        try:
            score = float(minowa[0][1])
            if len(minowa) > 1:
                margin = score - float(minowa[1][1])
        except Exception:
            score = margin = None
        alts = [f"{p[0]}({round(float(p[1]),1)})" for p in minowa[:3] if p and len(p) >= 2]
    sig = ""
    sig_preds = (pred.get("signature") or {}).get("predictions") or {}
    if isinstance(sig_preds, dict) and sig_preds:
        sig = sorted(sig_preds.items(), key=lambda kv: -(kv[1][2] if isinstance(kv[1], list) and len(kv[1]) > 2 else 0))[0][0]
    return ext, score, margin, sig, alts


def _at_confidence(margin: float | None) -> str:
    """PKS AT confidence from the top1-vs-top2 Minowa margin (a clear winner vs an ambiguous call)."""
    if margin is None:
        return "none"
    if margin >= 40:
        return "high"
    if margin >= 15:
        return "moderate"
    if margin >= 5:
        return "low"
    return "ambiguous"


def extract_adomain_rows(records: list[dict]) -> list[dict]:
    """One row per substrate-selecting domain across all records:
      - NRPS A-domains (AMP-binding / A-OX): Stachelhaus amino-acid call (resolves GBK `X`);
      - PKS AT-domains (PKS_AT): Minowa extender-unit call (malonyl/methylmalonyl/… -CoA).
    Unified schema; `domain_class` distinguishes them. Extenders and amino acids share the
    `substrate` column deliberately so the polymer can be read straight down the table.
    """
    rows: list[dict] = []
    for rec in records:
        rid = rec.get("id") or rec.get("name") or ""
        npks = (rec.get("modules") or {}).get("antismash.modules.nrps_pks") or {}
        consensus = npks.get("consensus") or {}
        dp = npks.get("domain_predictions") or {}
        for dom_id, pred in dp.items():
            ma = _ADOM_RE.match(dom_id)
            mt = _AT_RE.match(dom_id)
            if ma:
                nrpys = pred.get("nrpys") or {}
                sub, score, pc_name, pc_subs = _stachelhaus_call(nrpys)
                consensus_sub = str(consensus.get(dom_id) or "").strip()
                agreement_state, disposition = _nrps_agreement_state(consensus_sub, sub)
                rows.append({
                    "record_id": rid,
                    "locus_tag": ma.group("locus"),
                    "domain_id": dom_id,
                    "domain_class": "NRPS_A",
                    "domain_number": int(ma.group("num")),
                    "signature": nrpys.get("aa10", ""),
                    "substrate": sub,                       # backward-compatible Stachelhaus field
                    "consensus_substrate": consensus_sub,
                    "stachelhaus_substrate": sub,
                    "prediction_agreement_state": agreement_state,
                    "prediction_disposition": disposition,
                    "score": "" if score is None else round(float(score), 3),
                    "confidence": _confidence(score),
                    "class_or_alternatives": pc_name + ((" | " + "|".join(pc_subs)) if pc_subs else ""),
                    "method": "antiSMASH nrps_pks/nrpys Stachelhaus (inferred; similarity-level)",
                })
            elif mt:
                ext, score, margin, sig, alts = _at_call(pred)
                rows.append({
                    "record_id": rid,
                    "locus_tag": mt.group("locus"),
                    "domain_id": dom_id,
                    "domain_class": "PKS_AT",
                    "domain_number": int(mt.group("num")),
                    "signature": sig,                        # ATSignature extender (usually mal/mmal)
                    "substrate": ext,                        # top Minowa extender-CoA
                    "consensus_substrate": "",
                    "stachelhaus_substrate": "",
                    "prediction_agreement_state": "NOT_APPLICABLE_NRPS_CONFLICT_CHECK",
                    "prediction_disposition": "MINOWA_AT_SIGNATURE_SIMILARITY_LEVEL",
                    "score": "" if score is None else round(float(score), 1),
                    "confidence": _at_confidence(margin),    # from top1-vs-top2 margin, not absolute score
                    "class_or_alternatives": "|".join(alts),  # top-3 Minowa extenders w/ scores
                    "method": "antiSMASH nrps_pks/minowa_at + ATSignature (inferred; similarity-level)",
                })
    return rows


def extract_region_polymers(records: list[dict]) -> list[dict]:
    """One row per predicted region polymer: assembled monomers (D-config), SMILES, over-merge flag."""
    rows: list[dict] = []
    for rec in records:
        rid = rec.get("id") or rec.get("name") or ""
        npks = (rec.get("modules") or {}).get("antismash.modules.nrps_pks") or {}
        rp = npks.get("region_predictions") or {}
        # candidate-cluster kind + protocluster count live under record 'areas'
        areas = rec.get("areas") or []
        for region_no, preds in rp.items():
            area = areas[int(region_no) - 1] if str(region_no).isdigit() and len(areas) >= int(region_no) else {}
            n_proto = len(area.get("protoclusters") or {}) if isinstance(area.get("protoclusters"), (dict, list)) else 0
            cands = area.get("candidates") or []
            kinds = sorted({c.get("kind", "") for c in cands if c.get("kind")})
            over_merge = bool(n_proto >= 2 or any(k in ("neighbouring", "interleaved", "chemical_hybrid") for k in kinds))
            for p in (preds or []):
                rows.append({
                    "record_id": rid,
                    "region_number": region_no,
                    "sc_number": p.get("sc_number", ""),
                    "predicted_polymer": p.get("polymer", ""),   # ordered monomers, D- marked, '+' splits protoclusters
                    "predicted_smiles": p.get("smiles", ""),
                    "docking_used": p.get("docking_used", ""),
                    "n_protoclusters": n_proto,
                    "candidate_kind": "|".join(kinds),
                    "over_merge_flag": "YES (region likely >=2 BGCs; split before product claims)" if over_merge else "no",
                })
    return rows


def _load_records(records_or_json: Any) -> list[dict]:
    """Accept: a parsed antiSMASH dict, a list of records, a path to the run JSON, or a path to the
    antiSMASH ZIP (the top-level *.json is loaded from it). ZIP support lets the wire-in be a
    one-liner: write_nrps_prediction_csvs(input_zip, package_dir, strain_id)."""
    if isinstance(records_or_json, dict):
        return records_or_json.get("records", [])
    if isinstance(records_or_json, (str, os.PathLike)):
        p = str(records_or_json)
        if p.lower().endswith(".zip"):
            import zipfile
            from .ziputil import regular_file_names
            with zipfile.ZipFile(p) as zf:
                # the antiSMASH run JSON is the top-level .json (largest, not a KCB sidecar)
                cands = [n for n in regular_file_names(zf)
                         if n.lower().endswith(".json") and "/" not in n.strip("/")]
                if not cands:
                    return []
                target = max(cands, key=lambda n: zf.getinfo(n).file_size)
                with zf.open(target) as fh:
                    return (json.load(fh) or {}).get("records", [])
        with open(p, encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("records", [])
    return list(records_or_json or [])


def write_nrps_prediction_csvs(records_or_json: Any, outdir: str, strain_id: str) -> dict:
    """Emit <strain>_nrps_prediction.csv and <strain>_predicted_polymers.csv. Returns a small receipt."""
    records = _load_records(records_or_json)
    adom = extract_adomain_rows(records)
    poly = extract_region_polymers(records)
    os.makedirs(outdir, exist_ok=True)
    p1 = os.path.join(outdir, f"{strain_id}_nrps_prediction.csv")
    p2 = os.path.join(outdir, f"{strain_id}_predicted_polymers.csv")
    if adom:
        _p1_tmp = p1 + ".tmp"
        with open(_p1_tmp, "w", newline="", encoding="utf-8") as fh:
            w = _SafeDictWriter(fh, fieldnames=list(adom[0].keys())); w.writeheader(); w.writerows(adom)
        os.replace(_p1_tmp, p1)
    if poly:
        _p2_tmp = p2 + ".tmp"
        with open(_p2_tmp, "w", newline="", encoding="utf-8") as fh:
            w = _SafeDictWriter(fh, fieldnames=list(poly[0].keys())); w.writeheader(); w.writerows(poly)
        os.replace(_p2_tmp, p2)
    return {
        "substrate_rows": len(adom),
        "nrps_a_rows": sum(1 for r in adom if r["domain_class"] == "NRPS_A"),
        "pks_at_rows": sum(1 for r in adom if r["domain_class"] == "PKS_AT"),
        "region_polymer_rows": len(poly),
        "over_merged_regions": len({(r["record_id"], r["region_number"]) for r in poly
                                    if r["over_merge_flag"].startswith("YES")}),
        "nrps_prediction_csv": p1 if adom else None,
        "predicted_polymers_csv": p2 if poly else None,
    }

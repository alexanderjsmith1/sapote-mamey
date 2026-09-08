"""deep_data.py — gene-level deep-data extraction + Mode B verdict scaffold (v9.7.46, B-9/F-10).

The gene-by-gene Mode B deep dive (tools/build_modeb_deepdive.py) needs three banked inputs that the
standard run did not emit, so it degraded to verdict-less placeholder cards:
  * deep_data.json   — bgc_profile (domain counts) + active_sites + class_pred (+ domain_hits)
  * gene_data.json   — domain_arch + substrates + ripp
  * modeb_verdicts.csv — per-BGC status (CONFIRM / DOWNGRADE / DROP)

This module is the single source of truth for that extraction. The two extractors are ported verbatim
from the cohort-bank tool (tools/build_deep_data.py now imports them from here), and `build_deep_data_files`
emits the per-run package copies from the package's own Project_Memory_Snapshot.json + AntiSMASH_Evidence_
Parse.json (both already written by the run). `modeb_verdict_rows` produces a DETERMINISTIC first-pass
verdict that the Sapote judgment layer refines; it never claims to be the final gene-by-gene call.
"""
import json
import glob
import os


def _loadj(p):   # B1: context-managed json load (no leaked handle); +utf-8 (B2)
    with open(p, encoding="utf-8") as _f:
        return json.load(_f)


PROFILE_DOMAINS = ["NRPS_A", "NRPS_C", "NRPS_T_PCP", "PKS_KS", "PKS_AT", "PKS_KR", "PKS_DH", "PKS_ER",
                   "TE_release", "Transporter", "Regulator", "Oxidoreductase"]
TIER1_DOMAINS = {"PKS_KS", "NRPS_A", "NRPS_C", "PKS_AT"}
# classes whose anchor implies a core-biosynthesis assembly line (used by the verdict scaffold).
_CORE_BIOSYN_CLASSES = ("nrps", "pks", "polyketide", "nonribosomal", "hybrid")


def extract_profiles(sid, snap):
    """bgc_profile / domain_arch / domain_hits from a package's source_scans (ported verbatim)."""
    ss = snap['source_scans']
    da = ss.get('domain_architecture', {}).get('per_bgc', {}) or {}
    rt = ss.get('resistance_tiers', {}).get('per_bgc', {}) or {}
    bt = ss.get('blda_tta', {}).get('per_bgc', {}) or {}
    um = ss.get('umed', {}).get('per_bgc', {}) or {}
    cc = ss.get('cctt', {}).get('bgc_coupling', {}) or {}
    profiles = []; archs = []; hits = []
    for bgc_id, dinfo in da.items():
        dc = dinfo.get('domain_counts', {}) or {}
        prof = {"sid": sid, "bgc_id": bgc_id,
                "tta_codons": bt.get(bgc_id, {}).get('tta_codons', 0),
                "tta_cds": bt.get(bgc_id, {}).get('tta_cds', 0),
                "resistance_tier": rt.get(bgc_id, {}).get('tier', 'NULL_NO_SOURCE_DERIVED_RESISTANCE'),
                "umed_verdict": um.get(bgc_id, {}).get('verdict', 'NOT_MATURATION_GATED'),
                "cctt_triggers": ','.join(cc.get(bgc_id, [])),
                "total_domains": sum(dc.values())}
        for d in PROFILE_DOMAINS:
            prof[d] = dc.get(d, 0)
        profiles.append(prof)
        archs.append({"sid": sid, "bgc_id": bgc_id, "architecture": str(dinfo)})
        for dm in dinfo.get('domains', []):
            hits.append({"sid": sid, "region_key": dm.get('contig'),
                         "locus": f"{dm.get('contig')}:{dm.get('start')}", "domain": dm.get('domain'),
                         "pfam": dm.get('domain'), "evalue": dm.get('evalue'), "bitscore": dm.get('bitscore'),
                         "tier1": dm.get('domain') in TIER1_DOMAINS})
    return profiles, archs, hits


def extract_finer(sid, snap, evidence):
    """active_sites / class_pred / substrates / ripp. `evidence` is the parsed AntiSMASH_Evidence_Parse
    dict (bounded/full runs carry it; offline runs return empties). Ported from the cohort-bank tool."""
    act = []; cls = []; subs = []; ripp = []
    e = evidence or {}
    for rk, items in (e.get('by_region', {}) or {}).items():
        contig = rk.rsplit('_c', 1)[0]
        for it in (items if isinstance(items, list) else []):
            if not isinstance(it, dict):
                continue
            for d in it.get('domains', []) if isinstance(it.get('domains'), list) else []:
                if d.get('active_site_calls'):
                    act.append({"sid": sid, "contig": contig, "locus": d.get('locus'),
                                "domain_id": d.get('domain_id'), "active_site_calls": d.get('active_site_calls')})
                for fld in ('substrate', 'specificity', 'consensus', 'monomer'):
                    if d.get(fld):
                        subs.append({"sid": sid, "contig": contig, "locus": d.get('locus'),
                                     "domain_id": d.get('domain_id'), "field": fld, "substrate": d.get(fld)})
            if it.get('predicted_products') or it.get('protocluster'):
                cls.append({"sid": sid, "contig": contig, "module": it.get('module'),
                            "protocluster": it.get('protocluster'), "predicted_products": it.get('predicted_products')})
            for rp in it.get('ripp_cores', []) if isinstance(it.get('ripp_cores'), list) else []:
                ripp.append({"sid": sid, "contig": contig, "family": rp.get('family'), "locus": rp.get('locus'),
                             "motif_index": rp.get('motif_index'), "core": rp.get('core')})
    # finer-fix: bounded/full runs write these to the evidence parse's TOP-LEVEL arrays, not by_region.
    if not subs:
        for r in (e.get('nrps_pks_consensus') or []):
            sub = r.get('consensus_substrate')
            if not sub:
                continue
            subs.append({"sid": sid, "contig": r.get('record_id'), "locus": r.get('locus_tag'),
                         "domain_id": r.get('domain_id'), "field": r.get('prediction_field', 'consensus'),
                         "substrate": sub, "provenance": "GBK/JSON"})
    if not act:
        for r in (e.get('active_site_pairings') or []):
            calls = r.get('active_site_calls')
            if not calls:
                continue
            act.append({"sid": sid, "contig": r.get('record_id'), "locus": r.get('locus_tag'),
                        "domain_id": r.get('domain_id'),
                        "active_site_calls": "; ".join(calls) if isinstance(calls, list) else calls,
                        "provenance": "GBK/JSON"})
    if not cls:
        for r in (e.get('product_class_predictions') or []):
            pred = r.get('product_classes') or r.get('products') or []
            cls.append({"sid": sid, "contig": r.get('record_id'), "module": r.get('module'),
                        "protocluster": r.get('protocluster_id'),
                        "predicted_products": "; ".join(pred) if isinstance(pred, list) else pred,
                        "provenance": "GBK/JSON"})
    if not ripp:
        for r in (e.get('ripp_cores') or []):
            core = r.get('core') or r.get('core_sequence')
            if not core:
                continue
            ripp.append({"sid": sid, "contig": r.get('record_id'),
                         "family": r.get('ripp_family') or r.get('family'),
                         "locus": r.get('locus_tag') or r.get('locus'),
                         "motif_index": r.get('motif_index', 0), "core": core, "provenance": "antismash-json"})
    return act, cls, subs, ripp


def build_deep_data_files(package_dir, sid):
    """Emit deep_data.json + gene_data.json into the package from its own snapshot + evidence parse.
    Returns a small dict of counts. Degrades gracefully (writes empties) if inputs are absent."""
    package_dir = str(package_dir)

    def _load(pattern):
        fs = glob.glob(os.path.join(package_dir, pattern))
        if not fs:
            return {}
        try:
            return _loadj(fs[0])
        except Exception:
            return {}

    snap = _load(f"{sid}_Project_Memory_Snapshot.json") or _load("*Project_Memory_Snapshot.json")
    # v9.7.400: the snapshot may be an alias stub pointing at manifest.json (see mamey/snapshot_alias.py).
    if isinstance(snap, dict) and snap.get("alias_of") and "source_scans" not in snap:
        snap = _load("manifest.json") or snap
    evidence = _load(f"{sid}_AntiSMASH_Evidence_Parse.json") or _load("*AntiSMASH_Evidence_Parse.json")
    profiles = archs = hits = []
    if isinstance(snap, dict) and 'source_scans' in snap:
        profiles, archs, hits = extract_profiles(sid, snap)
    act, cls, subs, ripp = extract_finer(sid, snap if isinstance(snap, dict) else {}, evidence)
    deep = {"bgc_profile": profiles, "domain_hits": hits, "active_sites": act, "class_pred": cls}
    gene = {"domain_arch": archs, "substrates": subs, "ripp": ripp, "tfbs": {}}
    # v9.7.185 P13: persist Other_domain diagnostics so classifier gaps are visible in the package.
    try:
        _da = (snap.get("source_scans", {}) if isinstance(snap, dict) else {}).get("domain_architecture", {})
        if not _da and isinstance(snap, dict):
            _da = snap.get("domain_architecture", {})
        gene["other_domain_breakdown"] = _da.get("other_domain_breakdown", {})
        gene["misfiled_core_tokens"] = _da.get("misfiled_core_tokens", {})
    except Exception:
        gene["other_domain_breakdown"] = {}
        gene["misfiled_core_tokens"] = {}
    import os as _os
    _dp = os.path.join(package_dir, "deep_data.json")
    _gp = os.path.join(package_dir, "gene_data.json")
    _dt = _dp + ".tmp"; _gt = _gp + ".tmp"
    with open(_dt, "w") as f: json.dump(deep, f)
    with open(_gt, "w") as f: json.dump(gene, f)
    _os.replace(_dt, _dp); _os.replace(_gt, _gp)
    return {"bgc_profile": len(profiles), "active_sites": len(act), "class_pred": len(cls),
            "substrates": len(subs), "ripp": len(ripp)}


def modeb_verdict_rows(strain, triage, misanchored_ids=frozenset()):
    """Deterministic first-pass Mode B verdicts (a SCAFFOLD the Sapote layer refines, not the final call).

    DROP      = anchor's biosynthetic class not supported at the locus: primary-metabolism / housekeeping
                core (the framework saying no).
    DOWNGRADE = real locus, reclassified out of the lead set: a standing-rule class exclusion
                (saccharide / NAPAA / hglE), or a mis-anchor (KCB anchor lacks its class diagnostic).
    CONFIRM   = no exclusion fired; gene/anchor logic is not contradicted at the deterministic level.
    """
    rows = []
    for t in triage:
        bid = getattr(t, "bgc_id", "")
        sr = getattr(t, "standing_rule_flag", "") or ""
        pm = getattr(t, "primary_metabolism_flag", False)
        cls = getattr(t, "architecture_capacity", "") or ""
        if pm:
            status, note = "DROP", "primary-metabolism / housekeeping core — anchor biosynthetic class not supported"
        elif sr:
            status, note = "DOWNGRADE", f"standing-rule class exclusion ({sr}) — real locus, excluded from the lead set"
        elif bid in misanchored_ids:
            status, note = "DOWNGRADE", "mis-anchor — KCB anchor lacks its class diagnostic gene"
        else:
            status, note = "CONFIRM", "no exclusion flag; anchor/gene logic not contradicted (deterministic scaffold; Sapote refines)"
        rows.append({"strain": strain, "bgc": bid, "status": status, "modeb_class": cls, "note": note})
    return rows


MODEB_VERDICT_HEADERS = ["strain", "bgc", "status", "modeb_class", "note"]

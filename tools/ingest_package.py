#!/usr/bin/env python3
"""ingest_package.py — map a Mamey package into the cohort banked-JSON entries.

The cohort master workbook is built (build_master.py) from five banked JSON files. This tool
converts a single Mamey package's **Project_Memory_Snapshot.json** (the canonical structured
aggregation) into the banked entry for that strain, so a newly-extracted genome folds into the
cohort with one command — the missing pipeline link between `mamey run` and the master build.

Scope (core, validated): bgc_data (strain record + per-BGC rows), gene_data.scan_agg + tfbs,
rggmci_full, tigrfam, modeb_verdicts (per-package modeb_verdicts.csv, gold mode only — BC2-408:
merged into the cohort-level <banked_dir>/modeb_verdicts.csv that tools/build_modeb_deepdive.py,
tools/generate_bgc_atlas.py, tools/build_thesis_vignettes.py, tools/build_subset_panel.py,
tools/lead_board.py and tools/build_lead_tiers.py all read; before BC2-408 nothing ever wrote that
cohort-level file, so those six tools silently — or, in build_lead_tiers.py's case pre-.408,
fatally — got no verdicts on any bank built purely from this tool). Detail per-BGC lists
(substrates/active_sites/domain_hits/class_pred/bgc_profile/domain_arch) are emitted when present
in the snapshot, else left for build_master to treat as "not yet computed".

Usage:
  python tools/ingest_package.py --package <pkg_dir> --ww WWGP00000000 [--banked-dir /data/mamey-local] [--merge]
  python tools/ingest_package.py --validate <SID> --package <pkg_dir> --banked-dir /data/mamey-local   # self-check
"""
import argparse, contextlib, csv, json, os, sys, shutil
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


CAP = 1000  # ranked_pairs / conf cap used when the cohort was banked


def load(p, default=None):
    # v9.7.173: first-init safety. On a fresh --banked-dir the core stores don't exist yet;
    # return the caller-supplied empty shape (or {}) instead of raising FileNotFoundError, so
    # `ingest_package --merge` works against an empty bank without pre-seeding JSON stubs.
    if not os.path.exists(p):
        return {} if default is None else default
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    # v9.7.400: a Project_Memory_Snapshot may be an alias STUB pointing at manifest.json
    # (the pre-.400 snapshot duplicated the whole manifest; see mamey/snapshot_alias.py).
    if (isinstance(d, dict) and d.get("alias_of") and "source_scans" not in d
            and "Project_Memory_Snapshot" in os.path.basename(str(p))):
        mp = os.path.join(os.path.dirname(str(p)) or ".", str(d["alias_of"]))
        if os.path.isfile(mp):
            with open(mp, encoding="utf-8") as fh:
                return json.load(fh)
    return d


def atomic_dump(obj, path, indent=None):
    """Write JSON to ``path`` crash-safely: serialize to a sibling .tmp, then
    os.replace() it into place. os.replace is atomic on POSIX, so a reader/other
    writer never sees a half-written or truncated file. Mirrors the .tmp+replace
    pattern in tools/_wbio.atomic_save (which is openpyxl-specific and can't take
    a JSON object directly)."""
    path = str(path)
    tmp = _private_tmp(path)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=indent)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):  # stage cleanup is best-effort; the original error wins
            os.unlink(tmp)
        raise
    return path


def _private_tmp(path: str) -> str:
    """v9.7.410 hostile audit: the stage file used to be the FIXED name ``<path>.tmp``, so two
    processes banking into the same cohort dir raced on it — one ``os.replace`` found the stage
    already moved by the other (``FileNotFoundError``) and that merge died half-way. A unique
    sibling stage (same directory, so ``os.replace`` stays atomic) removes the collision; the
    read-modify-write itself is serialised by the lock in :func:`merge`."""
    import tempfile
    d, name = os.path.split(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=d or ".")
    os.close(fd)
    return tmp


def atomic_write_csv(rows, path, fieldnames):
    """Write ``rows`` to ``path`` as CSV crash-safely: serialize to a sibling .tmp, then
    os.replace() it into place (POSIX-atomic, mirrors atomic_dump's identical pattern above —
    every other store this tool merges is JSON; modeb_verdicts.csv, BC2-408, is the first CSV
    output here, so it gets its own writer rather than overloading atomic_dump's json.dump)."""
    path = str(path)
    tmp = _private_tmp(path)
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            w = _SafeDictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in fieldnames})
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):  # stage cleanup is best-effort; the original error wins
            os.unlink(tmp)
        raise
    return path


def _modeb_verdict_headers():
    """Fieldnames for modeb_verdicts.csv, sourced from the engine's own MODEB_VERDICT_HEADERS
    (mamey/deep_data.py) so this merge step can't drift from what mamey/cli.py::_write_package
    actually writes per-package. Mirrors the _diagnostic_tigrfam_ids() import-with-fallback idiom
    already established in this file (below)."""
    try:
        import sys as _s
        _s.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from mamey.deep_data import MODEB_VERDICT_HEADERS
        return list(MODEB_VERDICT_HEADERS)
    except Exception:
        # fallback — keep in sync with mamey/deep_data.MODEB_VERDICT_HEADERS
        return ["strain", "bgc", "status", "modeb_class", "note"]


def _snapshot_bak(paths):
    """Copy each existing file to a sibling .bak before a multi-file merge begins,
    so an exception partway through the merge is recoverable. Best-effort: a missing
    source is skipped (a first-time bank has no prior file to snapshot)."""
    import warnings
    for p in paths:
        if os.path.exists(p):
            try:
                shutil.copy2(p, p + ".bak")
            except OSError as e:
                warnings.warn(
                    f"ingest_package: backup of {p} failed ({e}) — "
                    f"merge proceeding without pre-merge snapshot"
                )


def find_snapshot(pkg):
    for f in os.listdir(pkg):
        if f.endswith("_Project_Memory_Snapshot.json"):
            return os.path.join(pkg, f)
    raise SystemExit("no Project_Memory_Snapshot.json in package")


def norm_kcb_file(s):
    return (s or "").replace("source_locator_evidence/", "")


def _diagnostic_tigrfam_ids():
    """The TIGRFAM accessions ingest should count, sourced from the engine's
    DIAGNOSTIC_TIGRFAM so the ingest path can't re-collapse to a stale 4-ID
    panel (the v9.6.15 tigr8 fix; this was its second instance)."""
    try:
        import sys as _s
        _s.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from mamey.antismash_evidence import DIAGNOSTIC_TIGRFAM
        return list(DIAGNOSTIC_TIGRFAM)
    except Exception:
        # fallback — keep in sync with mamey/antismash_evidence.DIAGNOSTIC_TIGRFAM
        return ['TIGR01454', 'TIGR03604', 'TIGR03828', 'TIGR04186',
                'TIGR04462', 'TIGR04460', 'TIGR03550', 'TIGR03551', 'TIGR03620',
                'TIGR04363', 'TIGR04364', 'TIGR01181', 'TIGR02353']


def build_tigrfam(pkg):
    import glob
    PANEL = _diagnostic_tigrfam_ids()
    evs = glob.glob(os.path.join(pkg, '*_AntiSMASH_Evidence_Parse.json'))
    if not evs:
        return {"module": None, "present": {}, "surfaced": 0, "gbk": 0}
    ev = load(evs[0]); g = ev.get('gbk_pfam_hits', {})
    counts = {t: 0 for t in PANEL}; total = 0
    for region, hits in (g.items() if isinstance(g, dict) else []):
        if isinstance(hits, list):
            total += len(hits)
            for h in hits:
                hs = json.dumps(h)
                for t in PANEL:
                    if t in hs:
                        counts[t] += 1
    present = {t: c for t, c in counts.items() if c}
    return {"module": total, "present": present, "surfaced": len(present), "gbk": len(present)}


def infer_cohort(sid, tax, source=""):
    # B-10: consult the B-1 cohort resolver first so WGS-accession-labelled SID strains (e.g. --strain
    # WWGG00000000, organism "Streptomyces sp. SID-XXX") bank as SID, matching the run's resolution,
    # instead of falling through to REF on the bare ID prefix. OTHER keeps the bank's finer TYPE/REF split.
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    try:
        from mamey.cohort_resolver import resolve_cohort
    except ImportError:
        resolve_cohort = None
    if resolve_cohort is not None:
        r = resolve_cohort(sid, tax or "")
        if r["cohort"] in ("AS", "SID"):
            return r["cohort"]
        # Resolver OTHER deliberately falls through to the bank's finer TYPE/REF split.
        # Execution failures propagate: silently treating a broken resolver as an
        # unavailable optional import can reclassify a strain without evidence.
    blob = f"{tax or ''} {source or ''}".lower()
    if any(k in blob for k in ("type strain", "atcc", "nrrl", "dsm", "jcm", "nbrc")): return "TYPE"
    if str(sid).upper().startswith("AS"): return "AS"
    if str(sid).upper().startswith("SID"): return "SID"
    return "REF"

def build_entry(snap, ww, pkg_dir=None, cohort=None, accession=""):
    sid = snap["strain_id"]
    tax = snap.get("taxonomy") or snap.get("display_name")
    a = snap["assembly"]; bc = snap["bgc_counts"]; ss = snap["source_scans"]

    # --- bgc_data.strains[sid] ---
    cohort = cohort or infer_cohort(sid, tax)
    strain = {
        "organism": tax, "ww": ww, "cohort": cohort, "gca": accession or None,
        "contigs": a["contigs"], "n50": a["n50"], "genome_bp": a["genome_bp"],
        "gc_pct": round(a["gc_pct"], 2), "largest_contig": a["largest_contig"],
        "raw_bgcs": bc["raw"], "corrected_bgcs": bc["corrected"],
        "edge_dist": {"Interior": bc["interior"], "Full-contig": bc["full_contig"], "Edge": bc["edge"]},
    }

    # --- bgc_data.bgcs[] ---
    bgcs = []
    for b in snap["bgcs"]:
        bgcs.append({
            "sid": sid, "organism": tax, "bgc_id": b["bgc_id"],
            "region": f"region{int(b['region_number']):03d}", "contig": b["contig"],
            "products": ";".join(b.get("products") or []),
            "edge_status": b["edge_status"],
            "length_kb": round((b["end"] - b["start"]) / 1000, 1),
            "kcb_top": b.get("kcb_top"), "kcb_cumulative": b.get("kcb_cumulative"),
            "kcb_rank": str(b.get("kcb_hit_rank") or ""),
            "closest_kcb_product": b.get("closest_candidate_kcb_product"),
            "closest_mibig": b.get("closest_mibig_accession"),
            "kcb_provenance": b.get("closest_product_provenance"),
            "source_kcb_file": norm_kcb_file(b.get("source_kcb_file")),
            "riq": b.get("riq_label") or "",
        })

    # --- gene_data.scan_agg[sid] ---
    def csum(scan):  # sum of a source_scans[scan].counts dict
        return int(sum((ss.get(scan, {}).get("counts") or {}).values()))
    # NOTE: the cohort's banked scan_agg leaves resistance_T1/T2 at 0 across all 18 strains
    # (source-derived tier data lives in the package's resistance_tiers, not in scan_agg).
    # SID-XXX follows that convention for cross-strain consistency.
    scan_agg = {
        "CCTT_triggers": csum("cctt"),
        "CGAD_chitinase": csum("chitinase"),
        "bldA_TTA_BGCs": len(ss.get("blda_tta", {}).get("per_bgc") or {}),
        "resistance_T1": 0,
        "resistance_T2": 0,
        "FLBR_grade": ss.get("flbr", {}).get("flbr_grade"),
        "FLBR_megasynth": ss.get("flbr", {}).get("genome_wide_megasynthase_like_count"),
        "UMED": csum("umed"),
        "EFLS_pairs": ss.get("efls", {}).get("candidate_pair_count"),
        "QS_signals": ss.get("qs_signals", {}).get("qs_signal_count"),
        "NAPAA": ss.get("qs_signals", {}).get("napaa_count"),
        "glyco_arms": ss.get("glycosylation_arms", {}).get("candidate_count"),
        "TFBS_total": ss.get("tfbs", {}).get("total_hits"),
        "RGGMCI": "PENDING_NOT_RUN",
        "cds_count": None, "domain_count": None,  # not in snapshot; build_master tolerates None
    }

    # --- gene_data.tfbs[sid] ---
    tfbs = dict(ss.get("tfbs", {}).get("counts") or {})

    # --- rggmci_full[sid] ---
    rg = ss.get("rggmci", {})
    # v9.7.400: the manifest may embed a channel-alias stub; the full object lives in the
    # standalone {sid}_4A_RGGMCI_full.json (see mamey/scan_channel_alias.py). Fail-open.
    if isinstance(rg, dict) and rg.get("alias_of") and "ranked_pairs" not in rg and pkg_dir:
        _rgp = os.path.join(str(pkg_dir), str(rg["alias_of"]))
        if os.path.isfile(_rgp):
            try:
                with open(_rgp, encoding="utf-8") as _fh:
                    rg = json.load(_fh)
            except (OSError, json.JSONDecodeError) as exc:
                import warnings
                warnings.warn(
                    f"ingest_package: RG-GMCI alias could not be read; "
                    f"preserving explicit unreadable state ({exc})",
                    RuntimeWarning,
                )
                rg = {"status": "UNREADABLE_ALIAS"}
    ranked = rg.get("ranked_pairs") or []
    # AUDIT_374: the engine (mamey/rggmci.py::compute_rggmci) reports three confidence
    # tiers per strain (high_pairs, moderate_pairs, and an implicit LOW remainder — see
    # pairs_total/high_pairs/moderate_pairs in its return dict), but this conf block previously
    # only ever wrote the HIGH_RG_GMCI_RESCUE key. Every ingested strain's banked MODERATE/LOW
    # counts silently read as 0 downstream (tools/build_master.py's D1_RGGMCI_All_Strains sheet
    # reads conf.get('MODERATE_RG_GMCI_CANDIDATE',0) / conf.get('LOW_SHARED_REFERENCE_SIGNAL',0)),
    # even when real MODERATE/LOW pairs existed. Use the engine's own un-truncated totals (not
    # ranked_pairs, which the engine caps and only backfills HIGH overflow into) so a >1000-pair
    # strain still reports accurate MODERATE/LOW counts.
    _hi = rg.get("high_pairs", 0) or 0
    _mo = rg.get("moderate_pairs", 0) or 0
    _tot = rg.get("pairs_total", 0) or 0
    _lo = max(_tot - _hi - _mo, 0)
    rggmci_full = {
        "status": rg.get("status"),
        "ref_record_count": rg.get("reference_record_count"),
        "clusterblast_txt_files": rg.get("clusterblast_txt_file_count"),
        "ref_map_status": rg.get("reference_map_status"),
        "parse_errors": rg.get("reference_parse_error_count"),
        "n_pairs": min(len(ranked), CAP) if ranked else rg.get("pairs_total"),
        "n_evidence": len(rg.get("evidence_rows") or []),
        "conf": {
            "HIGH_RG_GMCI_RESCUE": min(_hi, CAP),
            "MODERATE_RG_GMCI_CANDIDATE": min(_mo, CAP),
            "LOW_SHARED_REFERENCE_SIGNAL": min(_lo, CAP),
        },
        "ranked_pairs": ranked[:CAP],
    }

    # --- tigrfam[sid] (curated panel from gbk_pfam_hits) ---
    tigrfam = build_tigrfam(pkg_dir) if pkg_dir else {"module": None, "present": {}, "surfaced": 0, "gbk": 0}

    # --- tfbs_coupling[sid] (per-BGC regulator-family coupling) ---
    # F10: the engine already computes this (source_scans.regulators.bgc_coupling,
    # {bgc_id: [families]}) and asdict() serialises it into the snapshot — ingest
    # previously never lifted it, so every new strain was absent from
    # tfbs_coupling.json and lead_board left all its CONFIRMs at Class B. We
    # write the sid key ALWAYS (even when empty) so an assessed-but-unregulated
    # strain is distinguishable from a never-assessed one.
    coupling = dict((ss.get("regulators", {}) or {}).get("bgc_coupling", {}) or {})
    # A2: per-BGC resistance/self-protection coupling. The engine already computes this
    # (source_scans.resistance.bgc_coupling, {bgc_id: [families]}) and asdict() serialises it
    # into the snapshot, but ingest never lifted it — so build_lead_tiers' self-protection axis
    # saw nothing for newly-ingested strains and never promoted target-directed leads. Same
    # lift pattern and always-write-the-key contract as F10 (coupling).
    resistance_coupling = dict((ss.get("resistance", {}) or {}).get("bgc_coupling", {}) or {})

    # --- modeb_verdicts (BC2-408) ---
    # modeb_verdicts.csv is a per-PACKAGE file (mamey/cli.py::_write_package, gold mode only) —
    # unlike everything else built above it does NOT come from the snapshot, so it is read
    # straight off pkg_dir here. Every row's own 'strain' field already equals sid (the package
    # only ever covers one strain), so no per-row filtering is needed on this side of the merge.
    modeb_verdicts = []
    if pkg_dir:
        _mv_path = os.path.join(str(pkg_dir), "modeb_verdicts.csv")
        if os.path.isfile(_mv_path):
            with open(_mv_path, encoding="utf-8") as _mvf:
                modeb_verdicts = list(csv.DictReader(_mvf))

    return {"sid": sid, "strain": strain, "bgcs": bgcs, "scan_agg": scan_agg,
            "tfbs": tfbs, "rggmci_full": rggmci_full, "tigrfam": tigrfam,
            "coupling": coupling, "resistance_coupling": resistance_coupling,
            "modeb_verdicts": modeb_verdicts}


def strain_fingerprint(bgcs):
    """v9.7.49 dedup gate: a stat fingerprint of a strain's BGC set. Two strains with the same BGC count
    and the same per-BGC (products, length, edge_status) multiset are almost certainly the same genome —
    a mislabelled or duplicate upload (the ST-956 == ST-678 (identical-fingerprint mislabel) case)."""
    import hashlib
    sig = sorted((b.get("products", ""), round(float(b.get("length_kb") or 0), 1), b.get("edge_status", ""))
                 for b in bgcs)
    return (len(bgcs), hashlib.sha1(repr(sig).encode("utf-8")).hexdigest()[:12])


def find_duplicate(entry_bgcs, bgc_json, self_sid):
    """Return the banked sid whose BGC fingerprint matches entry_bgcs (a different strain), else None.
    Same-sid re-banks are not duplicates (they are updates)."""
    fp = strain_fingerprint(entry_bgcs)
    if fp[0] == 0:
        return None
    for other in bgc_json.get("strains", {}):
        if other == self_sid:
            continue
        ob = [b for b in bgc_json.get("bgcs", []) if b.get("sid") == other]
        if ob and strain_fingerprint(ob) == fp:
            return other
    return None


def merge(entry, banked_dir, allow_dup=False):
    """Bank one package into the cohort stores, serialised across processes.

    v9.7.410 hostile audit: the eight-file merge is a read-modify-write with no lock. Two `bank`
    invocations into the same cohort dir interleaved so that the second reader loaded a
    pre-first-write store and its rewrite dropped the first process's rows (reproduced: one
    strain's modeb_verdicts rows lost, the other process dead in os.replace). A BLOCKING exclusive
    advisory lock on ``<banked_dir>/.ingest.lock`` makes the second banker wait its turn instead
    — same idiom as mamey/cli.py::_acquire_package_lock, but blocking, because a cohort bank is a
    queue, not a conflict. Non-POSIX hosts (no fcntl) keep the old behaviour.
    """
    try:
        import fcntl as _fcntl
    except ImportError:  # pragma: no cover - non-POSIX
        return _merge_unlocked(entry, banked_dir, allow_dup)
    os.makedirs(str(banked_dir), exist_ok=True)
    with open(os.path.join(str(banked_dir), ".ingest.lock"), "a+") as lock_fh:
        _fcntl.flock(lock_fh.fileno(), _fcntl.LOCK_EX)
        try:
            return _merge_unlocked(entry, banked_dir, allow_dup)
        finally:
            _fcntl.flock(lock_fh.fileno(), _fcntl.LOCK_UN)


def _merge_unlocked(entry, banked_dir, allow_dup=False):
    sid = entry["sid"]
    # Snapshot every banked file this merge may touch BEFORE writing any of them, so a
    # failure partway through the 8-file write is recoverable from the .bak siblings.
    _snapshot_bak([
        f"{banked_dir}/bgc_data.json",
        f"{banked_dir}/gene_data.json",
        f"{banked_dir}/rggmci_full.json",
        f"{banked_dir}/tigrfam.json",
        f"{banked_dir}/tfbs_coupling.json",
        f"{banked_dir}/resistance_coupling.json",
        f"{banked_dir}/strains.json",
        f"{banked_dir}/modeb_verdicts.csv",
    ])
    bgc = load(f"{banked_dir}/bgc_data.json", {"strains": {}, "bgcs": []})
    # v9.7.49 dedup gate: refuse a different-SID fingerprint collision unless explicitly allowed
    dup = find_duplicate(entry["bgcs"], bgc, sid)
    if dup is not None:
        msg = (f"[dedup-gate] {sid} has an identical BGC fingerprint to banked {dup} "
               f"(n_bgc={len(entry['bgcs'])}) — likely a mislabelled or duplicate upload.")
        if not allow_dup:
            raise SystemExit(msg + " Re-run with --allow-dup to bank anyway.")
        sys.stdout.write((msg + " (allowed via --allow-dup)") + "\n")
    bgc["strains"][sid] = entry["strain"]
    bgc["bgcs"] = [b for b in bgc["bgcs"] if b["sid"] != sid] + entry["bgcs"]
    atomic_dump(bgc, f"{banked_dir}/bgc_data.json")
    gene = load(f"{banked_dir}/gene_data.json", {"scan_agg": {}, "tfbs": {}})
    gene["scan_agg"][sid] = entry["scan_agg"]; gene["tfbs"][sid] = entry["tfbs"]
    atomic_dump(gene, f"{banked_dir}/gene_data.json")
    rg = load(f"{banked_dir}/rggmci_full.json"); rg[sid] = entry["rggmci_full"]
    atomic_dump(rg, f"{banked_dir}/rggmci_full.json")
    tg = load(f"{banked_dir}/tigrfam.json"); tg[sid] = entry["tigrfam"]
    atomic_dump(tg, f"{banked_dir}/tigrfam.json")
    # F10: per-BGC regulator coupling -> tfbs_coupling.json (lead_board reads this
    # for Class A/C; absence silently pins CONFIRMs at Class B). Always write the
    # sid key, even when {} (assessed-empty != never-assessed).
    cp_path = f"{banked_dir}/tfbs_coupling.json"
    cp = load(cp_path) if os.path.exists(cp_path) else {}
    cp[sid] = entry.get("coupling", {})
    atomic_dump(cp, cp_path)
    # A2: per-BGC resistance coupling -> resistance_coupling.json (build_lead_tiers reads this
    # for the self-protection / target-directed Class-A axis). Always write the sid key.
    rcp_path = f"{banked_dir}/resistance_coupling.json"
    rcp = load(rcp_path) if os.path.exists(rcp_path) else {}
    rcp[sid] = entry.get("resistance_coupling", {})
    atomic_dump(rcp, rcp_path)
    # BC2-408: modeb_verdicts.csv is written per-PACKAGE by mamey/cli.py::_write_package (gold
    # mode only) but nothing merged those per-strain rows into a cohort-level
    # <banked_dir>/modeb_verdicts.csv — six downstream tools (build_modeb_deepdive.py,
    # generate_bgc_atlas.py, build_thesis_vignettes.py, build_subset_panel.py, lead_board.py,
    # build_lead_tiers.py) all read exactly that cohort path and silently (or, in
    # build_lead_tiers.py pre-.408, fatally) got nothing on any bank built purely via this
    # command. Same per-strain replace-on-reingest pattern as bgc_data.json/tfbs_coupling.json
    # above: drop this sid's existing rows (if any), append this package's rows.
    mv_path = f"{banked_dir}/modeb_verdicts.csv"
    mv_headers = _modeb_verdict_headers()
    _existing_mv = []
    if os.path.exists(mv_path):
        with open(mv_path, encoding="utf-8") as _mvf:
            _existing_mv = list(csv.DictReader(_mvf))
    _new_mv = entry.get("modeb_verdicts") or []
    _merged_mv = [r for r in _existing_mv if r.get("strain") != sid] + _new_mv
    atomic_write_csv(_merged_mv, mv_path, mv_headers)
    # update the strains.json registry so GCA/cohort reach A2_Strain_Registry (provenance)
    sp = f"{banked_dir}/strains.json"
    if os.path.exists(sp):
        reg = load(sp); st = entry["strain"]
        row = {"sid": sid, "ww": st.get("ww", ""), "gca": st.get("gca"),
               "samn": st.get("samn", ""),
               "cohort": st.get("cohort"), "organism": st.get("organism")}
        if isinstance(reg, list):
            reg = [r for r in reg if r.get("sid") != sid] + [row]
        elif isinstance(reg, dict):
            reg[sid] = row
        atomic_dump(reg, sp)
    sys.stdout.write((f"merged {sid}: strain (cohort={entry['strain'].get('cohort')}, gca={entry['strain'].get('gca')}) "
          f"+ {len(entry['bgcs'])} bgcs + scan_agg + tfbs + rggmci_full + tigrfam "
          f"+ coupling({sum(1 for v in entry.get('coupling',{}).values() if v)} BGCs regulated) "
          f"+ modeb_verdicts({len(_new_mv)} rows{'' if _new_mv else ', gold mode only — none in this package'}) "
          f"+ registry") + "\n")


def validate(sid, pkg, banked_dir):
    snap = load(find_snapshot(pkg))  # pkg is the package dir
    ww = load(f"{banked_dir}/bgc_data.json")["strains"].get(sid, {}).get("ww", "")
    e = build_entry(snap, ww, pkg)
    bgc = load(f"{banked_dir}/bgc_data.json"); gene = load(f"{banked_dir}/gene_data.json")
    bk_strain = bgc["strains"][sid]; bk_scan = gene["scan_agg"][sid]
    bk_bgcs = [b for b in bgc["bgcs"] if b["sid"] == sid]
    sys.stdout.write((f"=== validate ingest vs banked {sid} ===") + "\n")
    sys.stdout.write((f"strain rec match: {e['strain']==bk_strain}") + "\n")
    if e["strain"] != bk_strain:
        for k in e["strain"]:
            if e["strain"][k] != bk_strain.get(k):
                sys.stdout.write((f"   DIFF {k}: ingest={e['strain'][k]} banked={bk_strain.get(k)}") + "\n")
    sys.stdout.write((f"bgc count: ingest={len(e['bgcs'])} banked={len(bk_bgcs)}") + "\n")
    sys.stdout.write(("scan_agg field-by-field:") + "\n")
    for k in bk_scan:
        ig = e["scan_agg"].get(k); ok = (ig == bk_scan[k])
        sys.stdout.write((f"   {'OK ' if ok else 'DIFF'} {k}: ingest={ig} banked={bk_scan[k]}") + "\n")


def _schema_gate(package, banked_dir, force=False):
    """Mandatory pre-merge schema gate (patch G1). Refuse to bank a package whose schema/engine version
    diverges from the cohort the bank was established at — so divergent-schema sources can't be silently
    concatenated. The first strain establishes the cohort version; later strains must match (or --force)."""
    import os as _os
    import sys as _sys
    import glob as _glob
    mans = _glob.glob(os.path.join(package, "manifest.json")) or _glob.glob(os.path.join(package, "*manifest.json"))
    incoming = "UNKNOWN"
    if mans:
        try:
            incoming = str(_read_json(mans[0]).get("workflow_version") or "UNKNOWN")
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(
                f"SCHEMA GATE: cannot read manifest {mans[0]!r} ({exc}); "
                "a malformed manifest cannot be forced as UNKNOWN schema."
            ) from exc
    if incoming == "UNKNOWN" and not force:
        sys.stdout.write(("✗ SCHEMA GATE: incoming package does not declare workflow_version; refusing to establish or match UNKNOWN schema. Use --force-schema only after manual alignment.") + "\n")
        _sys.exit(2)
    marker = _os.path.join(banked_dir, "SCHEMA_VERSION")
    if _os.path.exists(marker):
        with open(marker, encoding="utf-8") as _mf:            # INGEST-P01: with-block + encoding
            banked = _mf.read().strip()
        if banked != incoming:
            msg = (f"✗ SCHEMA GATE: incoming package is schema v{incoming}, but this cohort is banked at "
                   f"v{banked}.\n  Divergent-schema sources must be normalized before merge — refusing.")
            if not force:
                sys.stdout.write((msg + "  (override with --force-schema once you've confirmed alignment.)") + "\n")
                _sys.exit(2)
            sys.stdout.write((msg + "  [--force-schema set — proceeding under operator override.]") + "\n")
    else:
        # INGEST-P01: create the bank dir if missing so the gate works off the build server
        # (default banked_dir was the hardcoded /data/mamey-local, which crashed elsewhere).
        try:
            _os.makedirs(banked_dir, exist_ok=True)
        except OSError as _e:
            sys.stdout.write((f"✗ SCHEMA GATE: cannot create banked-dir {banked_dir!r} ({_e}); "
                  f"pass a writable --banked-dir.") + "\n")
            _sys.exit(2)
        with open(marker, "w", encoding="utf-8") as _mf:        # INGEST-P01: with-block + encoding
            _mf.write(incoming)
        sys.stdout.write((f"  schema gate: cohort schema established at v{incoming}") + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package"); ap.add_argument("--ww", default="")
    ap.add_argument("--banked-dir", default="/data/mamey-local")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--allow-dup", action="store_true", help="bank even if a duplicate fingerprint is found")
    ap.add_argument("--validate", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--cohort", choices=["SID","AS","REF","TYPE"], default=None,
                    help="cohort tag for the strain; inferred from taxonomy if omitted")
    ap.add_argument("--accession", default="", help="GCA/assembly accession for provenance")
    ap.add_argument("--source", default="", help="free-text source hint for cohort inference")
    ap.add_argument("--force-schema", action="store_true",
                    help="override the mandatory pre-merge schema-drift gate (operator confirms alignment)")
    a = ap.parse_args()
    if a.validate:
        validate(a.validate, a.package, a.banked_dir); return
    snap = load(find_snapshot(a.package))
    cohort = a.cohort or infer_cohort(snap.get("strain_id",""), snap.get("taxonomy") or snap.get("display_name",""), a.source)
    e = build_entry(snap, a.ww, a.package, cohort=cohort, accession=a.accession)
    sys.stdout.write((f"built entry for {e['sid']}: {len(e['bgcs'])} bgcs; scan_agg EFLS={e['scan_agg']['EFLS_pairs']} "
          f"FLBR_megasynth={e['scan_agg']['FLBR_megasynth']} CCTT={e['scan_agg']['CCTT_triggers']}") + "\n")
    if a.out:
        atomic_dump(e, a.out, indent=2); sys.stdout.write((str("wrote") + " " + str(a.out)) + "\n")
    if a.merge:
        _schema_gate(a.package, a.banked_dir, force=a.force_schema)  # G1: hard pre-condition
        merge(e, a.banked_dir, allow_dup=a.allow_dup)


if __name__ == "__main__":
    main()

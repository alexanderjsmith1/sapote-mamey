"""Build the scan_status dict consumed by MameyRun and written to manifest.json.

Scan states (v1.2 §6):
  PASS            — completed; ≥1 trigger fired
  NULL            — completed; no trigger
  NOT_APPLICABLE  — does not apply by design
  DEFERRED        — will run in subsequent batch (not used in runnable)
  FAILED          — could not complete
"""
from __future__ import annotations
from .models import SourceScanBundle


def run_external_scan_pack(source_scans: SourceScanBundle,
                            antismash_evidence: dict,
                            taxonomy: str = "",
                            gbk_pfam_hits: dict | None = None) -> dict:
    """Convert SourceScanBundle into the ten-scan state list for the manifest."""

    ss = source_scans

    def _state(scan_dict: dict, name: str) -> tuple[str, str, str]:
        status = scan_dict.get("status", "FAILED")
        counts = scan_dict.get("counts", {})
        n_hits  = sum(v for v in counts.values() if isinstance(v, (int, float))) if counts else 0
        coupling = scan_dict.get("bgc_coupling", {})
        n_coupled = len(coupling) if coupling else 0

        if "PENDING" in status or "PLACEHOLDER" in status:
            state = "DEFERRED"
            detail = status
        elif n_hits > 0 or n_coupled > 0:
            state = "PASS"
            detail = f"{n_hits} hits; {n_coupled} BGCs coupled"
        else:
            state = "NULL"
            detail = "no triggers"

        return (name, state, detail)

    # KCB / RiQ
    kcb_status = antismash_evidence.get("status", "")
    kcb_regions = len(antismash_evidence.get("by_region", {}))
    kcb_loose   = len(antismash_evidence.get("loose_hits", []))
    kcb_state   = "PASS" if (kcb_regions + kcb_loose) > 0 else "NULL"
    kcb_detail  = f"{kcb_regions} regions parsed; {kcb_loose} loose hits"

    # FLBR
    flbr = ss.flbr
    flbr_grade = flbr.get("flbr_grade", "")
    flbr_state = "PASS" if flbr_grade in ("STRONG", "WEAK") else "NULL"
    flbr_detail = f"{flbr_grade} — {flbr.get('flbr_flag', 'no flag')}" if flbr_grade else "no megasynthase fragment set"

    # CCTT
    cctt_counts = ss.cctt.get("counts", {})
    cctt_bgcs = ss.cctt.get("trigger_bgc_counts", {})
    n_cctt = sum(v for v in cctt_counts.values() if isinstance(v, (int, float)))
    cctt_state  = "PASS" if n_cctt > 0 else "NULL"
    # counts are HITS (gene-level); BGC count is how many distinct clusters carry the trigger — show both
    cctt_detail = ", ".join(f"{k}: {v} hits/{cctt_bgcs.get(k, 0)} BGC" for k, v in cctt_counts.items() if v) or "no triggers"

    # CGAD
    chitin_counts = ss.chitinase.get("counts", {})
    n_chitin = sum(v for v in chitin_counts.values() if isinstance(v, (int, float)))
    cgad_state  = "PASS" if n_chitin > 0 else "NULL"
    cgad_detail = ", ".join(f"{k}:{v}" for k, v in chitin_counts.items() if v) or "no hits"

    # UMED
    umed_maturation = ss.umed.get("per_bgc", {})
    n_gap = sum(1 for v in umed_maturation.values()
                if isinstance(v, dict) and "GAP" in v.get("verdict", ""))
    umed_state  = "PASS" if umed_maturation else "NULL"
    umed_detail = f"{n_gap} lanthipeptide GAP regions" if n_gap else "no maturation gaps"

    # EFLS
    # `candidate_pairs` is a capped, retained list; `candidate_pair_count` is the full total.
    # Legacy payloads may lack the total, so report that it is unavailable instead of treating
    # the listed length as a verified total.
    pairs = ss.efls.get("candidate_pairs", []) or []
    n_pairs = ss.efls.get("candidate_pair_count")
    n_listed = len(pairs)
    if n_pairs is None:
        efls_state = "PASS" if n_listed else "NULL"
        efls_detail = f"total candidate pairs unavailable (legacy); {n_listed} listed"
    else:
        efls_state = "PASS" if n_pairs else "NULL"
        efls_detail = f"{n_pairs} candidate pairs total; {n_listed} listed"


    # RG-GMCI — mandatory pre-triage split-linkage pass
    rg = getattr(ss, "rggmci", {}) or {}
    rg_status = rg.get("status", "FAILED")
    if rg_status == "PASS":
        rg_state = "PASS"
        rg_detail = f"{rg.get('pairs_total', 0)} pairs; {rg.get('high_pairs', 0)} high; {rg.get('moderate_pairs', 0)} moderate; {rg.get('reference_record_count', 0)} reference records"
    elif rg_status == "NULL_NO_RGGMCI_PAIRS":
        rg_state = "NULL"
        rg_detail = f"completed; no pairs; {rg.get('reference_record_count', 0)} reference records"
    else:
        rg_state = "FAILED" if "PENDING" not in rg_status else "DEFERRED"
        rg_detail = rg_status or "RG-GMCI missing"

    # Resistance
    res_counts = ss.resistance.get("counts", {})
    n_res = sum(v for v in res_counts.values() if isinstance(v, (int, float)))
    tier1_bgcs = [bgc for bgc, v in ss.resistance_tiers.get("per_bgc", {}).items()
                  if isinstance(v, dict) and "T1" in v.get("tier", "")]
    res_state  = "PASS" if n_res > 0 or tier1_bgcs else "NULL"
    res_detail = f"{n_res} total hits; {len(tier1_bgcs)} T1 BGCs"

    # bldA / TTA — NOT_APPLICABLE outside actinomycetes. The bldA-dependent translational
    # control mechanism is specific to Streptomyces and close actinomycete relatives; on a
    # non-actinomycete (a Firmicute, a Gram-negative, a fungus) TTA codons are GC-content
    # noise, not a developmental signal.
    # v9.7.86 P-9: the prior condition (`not is_streptomyces and not tta_per_bgc`) made the
    # NOT_APPLICABLE branch unreachable — any GC-poor non-actinomycete (e.g. Melissococcus,
    # a Firmicute) ALWAYS has TTA-bearing BGCs, so tta_per_bgc was never empty and the genome
    # fell through to a false T4 report. The decision must key on the ORGANISM's actino-status,
    # not on whether TTA codons happen to be present.
    from .cohort_resolver import actino_status as _actino_status
    _tax = taxonomy or ""
    is_streptomyces = any(k in _tax.lower() for k in
                          ("streptomyces", "saccharopolyspora", "streptosporangium",
                           "micromonospora", "streptoverticillium"))
    _astat = _actino_status(_tax)
    # actinomycete (or a known Streptomyces relative) -> bldA applies; non-actinomycete ->
    # NOT_APPLICABLE; unknown genus -> apply but the intake issue_log already flags it for review.
    _blda_applies = is_streptomyces or (_astat == "actinomycete") or (_astat == "unknown")
    tta_per_bgc = ss.blda_tta.get("per_bgc", {})
    if not _blda_applies:
        blda_state  = "NOT_APPLICABLE"
        blda_detail = (f"bldA/TTA gating is specific to actinomycetes; "
                       f"{_tax or 'genus not confirmed'} is non-actinomycete — TTA counts are "
                       f"GC-content noise, not a developmental signal")
    else:
        t4_bgcs = [bgc for bgc, v in tta_per_bgc.items()
                   if isinstance(v, dict) and v.get("bldA_tier") == "T4"]
        blda_state  = "PASS" if tta_per_bgc else "NULL"
        blda_detail = f"{len(tta_per_bgc)} BGCs assessed; {len(t4_bgcs)} T4"

    # TFBS
    tfbs_total = ss.tfbs.get("total_hits", 0)
    tfbs_state  = "PASS" if tfbs_total > 0 else "NULL"
    # v9.7.374 fix: `f"{tfbs_total} motif hits; " + ", ".join(...) or "no hits"` -- the leading
    # f-string is always truthy (even at tfbs_total==0: "0 motif hits; "), so `or "no hits"` was
    # unreachable dead code and a zero-hit genome rendered the malformed trailing "0 motif hits; "
    # (dangling "; " with nothing after it) into manifest.json's scan_status detail instead of the
    # intended "no hits", the same unparenthesized-`or`-after-concatenation bug class already found
    # this session in tools/scan_cctt_class_compat.py's TOTAL-line swallow.
    if tfbs_total > 0:
        tfbs_detail = f"{tfbs_total} motif hits; " + ", ".join(
            f"{k}:{v}" for k, v in ss.tfbs.get("counts", {}).items() if v
        )
    else:
        tfbs_detail = "no hits"

    # PHO-CLUSTER flag: T43-PHO >= 5 HITS in one genome is a strong phosphonate signal. Whether it is a
    # phosphonate-rich strain or one dedicated locus depends on how many BGCs carry it (bgc_counts), not the
    # hit count — so the two are reported separately and the BGC spread drives the wording.
    pho_hits = cctt_counts.get("T43-PHO_phosphonate", 0)
    pho_bgcs = cctt_bgcs.get("T43-PHO_phosphonate", 0)
    pho_cluster_flag = pho_hits >= 5

    scans = [
        ("KCB_sweep",       kcb_state,   kcb_detail),
        ("RG_GMCI",         rg_state,    rg_detail),
        ("FLBR",            flbr_state,  flbr_detail),
        ("CCTT",            cctt_state,  cctt_detail),
        ("CGAD",            cgad_state,  cgad_detail),
        ("UMED",            umed_state,  umed_detail),
        ("EFLS",            efls_state,  efls_detail),
        ("resistance",      res_state,   res_detail),
        ("bldA_TTA",        blda_state,  blda_detail),
        ("TFBS",            tfbs_state,  tfbs_detail),
    ]
    if pho_cluster_flag:
        _spread = (f"single dedicated phosphonate locus ({pho_hits} hits in 1 BGC)" if pho_bgcs <= 1
                   else f"phosphonate-rich strain ({pho_hits} hits across {pho_bgcs} BGCs)")
        scans.append(("PHO_CLUSTER", "PASS",
                       f"T43-PHO {pho_hits} hits / {pho_bgcs} BGC(s) — {_spread}; "
                       "C-P bond biosynthetic capacity; "
                       "31P-NMR metabolomics + FomA/FomB BLASTP recommended"))

    # GBK sec_met_domain Pfam extraction status
    n_gbk_regions = len(gbk_pfam_hits) if gbk_pfam_hits else 0
    n_tier1 = sum(1 for hits in (gbk_pfam_hits or {}).values()
                  for h in hits if h.get("tier1_diagnostic"))
    if gbk_pfam_hits:
        asd_status = "COMPLETED_GBK_PFAM_EXTRACTED"
        asd_reason = (f"sec_met_domain Pfam/domain hits extracted from {n_gbk_regions} GBK region files "
                      f"({n_tier1} tier-1 diagnostic hits). antiSMASH pre-computed HMMER results surfaced "
                      f"without external HMMER re-run.")
    else:
        asd_status = "COMPLETED_SOURCE_DERIVED"
        asd_reason = ("Parsed antiSMASH GBK/JSON/TXT annotations; GBK sec_met_domain Pfam extraction "
                      "not run (GBK files not available or extraction skipped).")

    evidence_channels = {
        "antiSMASH_source_domains": {"status": asd_status, "reason": asd_reason,
                                      "gbk_regions_with_pfam": n_gbk_regions,
                                      "tier1_diagnostic_hits": n_tier1,
                                      "claim_safety": "antiSMASH pre-computed HMMER; bitscores and E-values from antiSMASH internal run."},
        "motif_scans": {"status": "COMPLETED_SOURCE_DERIVED", "reason": "Keyword/motif scans over source annotations/CDS features; confirm important claims externally."},
        "custom_marker_hmmer": {"status": "NEEDS_HMMER_DOMTBLOUT", "reason": "Provide protein FASTA plus mamey_markers.hmm and hmmscan --domtblout output. Release 2 scope."},
        "diamond_bulk_homology": {"status": "NEEDS_DIAMOND_TSV", "reason": "Provide protein FASTA and run DIAMOND blastp against a reference database. Framework present; database not yet connected."},
        "manual_blastp_top_leads": {"status": "MANUAL_BLASTP_OPTIONAL", "reason": "Run only for selected top proteins; do not use remote NCBI BLASTP for bulk annotation."},
    }
    return {"scans": scans, "evidence_channels": evidence_channels}

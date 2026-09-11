#!/usr/bin/env python3
"""build_first_pass_scans.py — render the eight genome-wide First-Pass Scans into one cohesive
pre-triage page from a Mamey package, WITHOUT re-scanning.

The eight scans already run on every `mamey run` inside `run_source_scans` and are serialized to the
package `manifest.json` (`source_scans` + manifest-level summaries). This tool reads that JSON and renders
the v8.9.3-style First-Pass-Scans page (one section per scan, each with a claim ceiling). It does NOT
recompute anything and never invents values — every number is read straight from the manifest.

Usage:
    python3 tools/build_first_pass_scans.py --package <pkg_dir> --out first_pass_scans.md
    python3 tools/build_first_pass_scans.py --manifest <path/to/manifest.json> --out -    # stdout

The eight scans: KCB sweep · Hallucination-trap/claim-calibration · FLBR megasynthase census ·
UMED maturation · CCTT trigger scan · CGAD chitin/GH18/LPMO · Resistance · bldA/TTA tiering.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open


def _load_manifest(args) -> dict:
    path = args.manifest
    if not path and args.package:
        cand = [os.path.join(args.package, "manifest.json"),
                os.path.join(args.package, "package", "manifest.json")]
        path = next((p for p in cand if os.path.exists(p)), None)
        if not path:
            # search one level down
            for root, _dirs, files in os.walk(args.package):
                if "manifest.json" in files:
                    path = os.path.join(root, "manifest.json"); break
    if not path or not os.path.exists(path):
        sys.exit("ERROR: manifest.json not found. Pass --manifest <path> or --package <dir> "
                 "(a Mamey package containing manifest.json).")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _n_proteins(b: dict) -> int | None:
    v = b.get("kcb_protein_hits")
    if isinstance(v, int):
        return v
    if isinstance(v, list):
        return len(v)
    return None


def _kcb_sweep(m: dict) -> str:
    """Scan 1 — KCB anchors + truncation-inflation AND composite-aggregation flags.

    Two de-inflation signals now surface ON THE ROW (F4): truncation-thin (≤3 protein hits) and composite
    (cumulative score aggregated across ≥2 merged single-protoclusters — not one cluster, see §3b)."""
    rows = []
    for b in m.get("bgcs", []):
        cum = b.get("kcb_cumulative")
        if cum in (None, "", 0):
            continue
        npr = _n_proteins(b)
        thin = (npr is not None and npr <= 3)
        composite = bool(b.get("composite_region"))
        n_proto = b.get("single_protocluster_count")
        if thin and composite:
            flag = f"**THIN+COMPOSITE** (≤3 hits; aggregates {n_proto} protoclusters — §3b)"
        elif composite:
            flag = f"**COMPOSITE** (aggregates {n_proto} protoclusters — §3b; not one cluster)"
        elif thin:
            flag = "**INFLATED**"
        else:
            flag = ""
        anchor = (b.get("kcb_top") or "").split(" | ")[0][:46]
        rows.append((float(cum), b.get("bgc_id", "?"), anchor, npr, flag))
    rows.sort(reverse=True)
    out = ["### 1 · KCB Sweep",
           "_KCB is similarity, not identity. ≤3 protein hits = truncation-inflated; COMPOSITE = score "
           "aggregated across merged protoclusters (§3b). Both mean: not a single-cluster lead._", "",
           "| BGC | anchor | cum_score | n_proteins | inflated |",
           "|---|---|---|---|---|"]
    for cum, bid, anchor, npr, flag in rows[:15]:
        out.append(f"| {bid} | {anchor or '—'} | {cum:.0f} | {npr if npr is not None else '?'} | "
                   f"{flag} |")
    if not rows:
        out.append("| _no KCB anchors recorded_ |  |  |  |  |")
    return "\n".join(out)


def _hallucination(m: dict) -> str:
    """Scan 2 — hallucination-trap / claim-calibration audit (labels as hypotheses)."""
    traps = m.get("hallucination_traps_triggered") or []
    out = ["### 2 · Hallucination-Trap / Claim-Calibration",
           "_Every product label is a hypothesis; Lead Priority and Claim Confidence are scored "
           "separately. Active traps:_", ""]
    if not traps:
        out.append("_No traps triggered for this strain (no label/evidence conflicts surfaced)._")
    else:
        out.append("| trap | BGC | label | resolution |")
        out.append("|---|---|---|---|")
        for t in traps:
            if isinstance(t, dict):
                out.append(f"| {t.get('trap_id','')} | {t.get('bgc','')} | {t.get('label','')} | "
                           f"{t.get('resolution','')} |")
            else:
                out.append(f"| {t} |  |  |  |")
    return "\n".join(out)


def _flbr(ss: dict) -> str:
    """Scan 3 — FLBR / LMPKS megasynthase census."""
    f = ss.get("flbr", {})
    counts = f.get("counts", {})
    out = ["### 3 · FLBR / LMPKS Megasynthase Census",
           f"_Genome-wide KS-like count: **{f.get('genome_wide_ks_like_count', '?')}** · "
           f"grade: **{f.get('flbr_grade', '?')}**. Very-Poor assembly demotes STRONG→WEAK except "
           f"modules bracketed by docking domains on both sides. Physical linkage of split subunits is "
           f"unproven — candidate co-locus, long-read required._", ""]
    if counts:
        out.append("| domain class | count |")
        out.append("|---|---|")
        for k, v in counts.items():
            out.append(f"| {k} | {v} |")
    cs = f.get("claim_safety")
    if cs:
        out.append(f"\n_Claim ceiling: {cs}_")
    # rescue-readiness signal (genome-level contig-rescue triage)
    if "rescue_readiness" in f:
        out.append(f"\n**Rescue readiness: {f.get('rescue_readiness')}** "
                   f"(priority score {f.get('rescue_priority_score')}). "
                   f"orphan-KS (Tier 1) = {f.get('orphan_megasynthase_count')}, "
                   f"AT-only (Tier 2) = {f.get('orphan_at_ambiguous_count')}, "
                   f"fragmented-megasynthase BGCs = {f.get('fragmented_megasynthase_count')}, "
                   f"interior fraction = {f.get('assembly_interior_fraction')}. "
                   f"_High orphan-KS + fragmented-megasynthase on a sub-Good assembly = reassembly/long-read "
                   f"would likely rejoin megasynthase fragments. Heuristic triage aid, not a per-cluster claim._")
    orphan = f.get("orphan_megasynthase_candidates") or []
    if orphan:
        out.append(f"\n_Orphan-contig **megasynthase candidates** (Tier 1 — KS active-site motif, "
                   f"annotation-independent; the fragments the annotation scan misses), with per-orphan "
                   f"rescue work-order. Motif-derived, NOT confirmed domains:_")
        out.append("\n| contig | locus | length_aa | motifs | linkage | nearest fragmented BGC | gap (bp) |")
        out.append("|---|---|---|---|---|---|---|")
        for o in orphan[:15]:
            nb = o.get("nearest_fragmented_bgc")
            gap = o.get("gap_estimate_bp")
            link = o.get("linkage", "")
            if link == "cross_contig":
                nb = "cross-contig: " + ",".join(o.get("candidate_partner_bgcs", [])[:6] or ["—"])
                gap = "—"
            out.append(f"| {o.get('contig','')} | {o.get('locus_tag','')} | {o.get('length_aa','')} | "
                       f"{','.join(o.get('motifs', []))} | {link} | {nb if nb is not None else '—'} | "
                       f"{gap if gap is not None else '—'} |")
        lcs = f.get("orphan_linkage_claim_safety")
        if lcs:
            out.append(f"\n_{lcs}_")
    else:
        out.append("\n_Orphan-contig megasynthase candidates (Tier 1, KS-bearing): none._")
    at_only = f.get("orphan_at_hydrolase_ambiguous") or []
    if at_only:
        out.append(f"\n_Tier 2 — **AT-only / α-β-hydrolase-ambiguous** ({len(at_only)} CDS). GHSxG is the "
                   f"hydrolase nucleophile elbow (esterase/thioesterase/lipase); **not** megasynthase "
                   f"evidence — listed for completeness only, not as leads._")
    ocs = f.get("orphan_megasynthase_claim_safety")
    if ocs:
        out.append(f"\n_{ocs}_")
    return "\n".join(out)


def _umed(ss: dict) -> str:
    """Scan 4 — unclustered maturation-enzyme detection."""
    u = ss.get("umed", {})
    counts = u.get("counts", {})
    per = u.get("per_bgc", {})
    flagged = [(b, d) for b, d in per.items()
               if isinstance(d, dict) and (d.get("needs_maturation") or d.get("maturation_gap"))]
    out = ["### 4 · UMED — Unclustered Maturation-Enzyme Detection",
           "_Maturation enzymes (proteases/dehydratases/RREs) located genome-wide, including outside the "
           "called BGC. Specificity unverified; a maturation gap is flagged, not a null claim._", ""]
    if counts:
        out.append("| maturation family | genome-wide count |")
        out.append("|---|---|")
        for k, v in counts.items():
            out.append(f"| {k} | {v} |")
    if flagged:
        out.append(f"\n_Regions flagged needing maturation / with a maturation gap: "
                   f"{', '.join(b for b, _ in flagged[:20])}_")
    cs = u.get("claim_safety")
    if cs:
        out.append(f"\n_Claim ceiling: {cs}_")
    return "\n".join(out)


def _cctt(ss: dict) -> str:
    """Scan 5 — cryptic-class / tailoring trigger scan."""
    c = ss.get("cctt", {})
    counts = {k: v for k, v in (c.get("counts", {}) or {}).items() if v}
    coupling = c.get("bgc_coupling", {}) or {}
    out = ["### 5 · CCTT — Cryptic-Class / Tailoring Trigger Scan",
           "_T43-* triggers fire on diagnostic genes. Bitscore floor = 150 (below = annotation-only). "
           "Bonuses bounded, non-stacking (≤ +2); they route extraction/dereplication and override "
           "low-KCB deprioritization. T43-ENE fires only on a real enediyne domain._", ""]
    if counts:
        out.append("| trigger | genome-wide hits |")
        out.append("|---|---|")
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
            out.append(f"| {k} | {v} |")
    if coupling:
        out.append("\n_Per-BGC firing:_ " + "; ".join(
            f"{b}→{','.join(t)}" for b, t in list(coupling.items())[:20] if t))
    return "\n".join(out)


def _cgad(ss: dict) -> str:
    """Scan 6 — chitin/glycan-active defense."""
    ch = ss.get("chitinase", {})
    counts = ch.get("counts", {})
    out = ["### 6 · CGAD — Chitin/Glycan-Active Defense",
           "_Genome-wide GH18/GH19 chitinase + AA10/LPMO scan (annotation/motif-derived). Secreted GH18 "
           "candidates require **HMMER PF00704 confirmation**; a true null is not claimable from a "
           "motif-only scan — record HMMER confirmation as a named missingness item._", ""]
    if counts:
        out.append("| family | count |")
        out.append("|---|---|")
        for k, v in counts.items():
            out.append(f"| {k} | {v} |")
    gh18 = counts.get("GH18", 0)
    lpmo = counts.get("AA10_LPMO", 0)
    out.append(f"\n_Ecology read: secreted chitinases (degrade existing chitin) + any nucleoside "
               f"chitin-synthase-inhibitor BGC (block new synthesis) = a two-pronged anti-chitin strategy. "
               f"GH18={gh18}, LPMO={lpmo}._")
    return "\n".join(out)


def _resistance(m: dict, ss: dict) -> str:
    """Scan 7 — resistance gene confirmation."""
    rs = m.get("resistance_gene_summary", {}) or {}
    counts = rs.get("counts", {})
    tiers = (ss.get("resistance_tiers", {}) or {}).get("tier_counts", {})
    out = ["### 7 · Resistance Gene Confirmation",
           "_Genome-wide self-protection scan (APH/AAC, VanHAX, Erm, CalC). HGT guard: an integrase-"
           "flanked resistance island concordant with a producer cluster is required before treating a "
           "resistance gene as class confirmation. APH defaults to Tier-3 background/polarity routing, "
           "not class confirmation._", ""]
    if counts:
        out.append("| resistance family | count |")
        out.append("|---|---|")
        for k, v in counts.items():
            out.append(f"| {k} | {v} |")
    if tiers:
        out.append("\n_Resistance tiers:_ " + ", ".join(f"{k}={v}" for k, v in tiers.items()))
    return "\n".join(out)


def _blda(ss: dict) -> str:
    """Scan 8 — bldA / TTA codon scan."""
    b = ss.get("blda_tta", {})
    per = b.get("per_bgc", {}) or {}
    tier_dist: dict[str, int] = {}
    flagged = []
    for bid, d in per.items():
        if not isinstance(d, dict):
            continue
        t = d.get("bldA_tier", "?")
        tier_dist[t] = tier_dist.get(t, 0) + 1
        if t not in ("T1",):
            flagged.append((bid, t, d.get("tta_codons", 0)))
    out = ["### 8 · bldA / TTA Codon Scan",
           "_Rare-leucine TTA codons per BGC → bldA accessibility tier. T1 (zero TTA) = constitutive "
           "accessibility; higher tiers are bldA-gated / culture-condition-dependent expression._", ""]
    if tier_dist:
        out.append("_Tier distribution:_ " + ", ".join(
            f"{t}={n}" for t, n in sorted(tier_dist.items())))
    if flagged:
        flagged.sort(key=lambda x: -x[2])
        out.append("\n| BGC | bldA_tier | TTA_codons |")
        out.append("|---|---|---|")
        for bid, t, n in flagged[:20]:
            out.append(f"| {bid} | {t} | {n} |")
    else:
        out.append("\n_All BGCs at T1 (zero TTA) — constitutive accessibility genome-wide._")
    return "\n".join(out)


def _composite_regions(m: dict) -> str:
    """De-inflated breakdown of composite regions (≥3 single protoclusters merged by antiSMASH)."""
    comps = [b for b in m.get("bgcs", []) if b.get("composite_region")]
    out = ["### 3b · Composite-Region Breakdown",
           "_antiSMASH merged ≥3 `/kind=\"single\"` protoclusters into one region: its `Products` string is a "
           "merge of distinct single-class clusters (not one hybrid) and its KCB/CCTT/lead score aggregate "
           "across all of them. Per-protocluster products below; the region aggregate should NOT be read as a "
           "single-cluster lead. (Protocluster spans routinely overlap, so single-owner KCB/CCTT attribution "
           "is not forced.)_", ""]
    if not comps:
        out.append("_No composite regions in this genome._")
        return "\n".join(out)
    for b in comps:
        merged = "; ".join(b.get("products", [])[:8])
        out.append(f"**{b.get('bgc_id')}** ({b.get('antismash_region','')}, "
                   f"{b.get('single_protocluster_count')}× single) — merged string: `{merged}`")
        pcs = b.get("protocluster_breakdown") or []
        if pcs:
            out.append("\n| protocluster | product | region-local span |")
            out.append("|---|---|---|")
            for p in pcs:
                out.append(f"| {p.get('protocluster_number')} | {p.get('product')} | "
                           f"{p.get('rel_start')}–{p.get('rel_end')} |")
            out.append("")
    return "\n".join(out)


def render(m: dict) -> str:
    ss = m.get("source_scans", {}) or {}
    strain = m.get("display_name") or m.get("strain_id", "strain")
    ver = m.get("workflow_version", "")
    header = [f"# First-Pass Scans — {strain}",
              f"_Engine {ver}. Eight genome-wide scans, computed pre-triage by `run_source_scans` and read "
              f"here from `manifest.json` (no re-scan). Each carries a claim ceiling; all values are "
              f"source-derived._", ""]
    sections = [_kcb_sweep(m), _hallucination(m), _flbr(ss), _composite_regions(m), _umed(ss),
                _cctt(ss), _cgad(ss), _resistance(m, ss), _blda(ss)]
    return "\n".join(header) + "\n\n" + "\n\n".join(sections) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Render the First-Pass Scans page from a Mamey package.")
    ap.add_argument("--package", help="package directory containing manifest.json")
    ap.add_argument("--manifest", help="path to manifest.json (overrides --package)")
    ap.add_argument("--out", default="-", help="output markdown path, or '-' for stdout")
    args = ap.parse_args()
    m = _load_manifest(args)
    md = render(m)
    if args.out == "-":
        sys.stdout.write(md)
    else:
        with atomic_open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        emit(f"wrote {args.out} ({len(md)} chars)")


if __name__ == "__main__":
    main()

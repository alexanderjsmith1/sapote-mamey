#!/usr/bin/env python3
"""arts_ingest.py — ARTS2 → per-BGC self-resistance signal (lead M7, validated against an admitted result fixture).

ARTS (Antibiotic Resistant Target Seeker) flags core/housekeeping genes that are duplicated, BGC-proximal,
phylogenetic outliers, or known-resistance targets. The Sapote-relevant signal is a core gene that is BOTH
**duplicated AND BGC-proximal** (a resistant target-copy sitting in a cluster) — the classic self-resistance
model, and exactly the SMK-RES-001 marker (TIER_2_CLASS_SUPPORTING).

CLAIM DISCIPLINE (hard): this is a **LEAD-PRIORITY** signal, never claim-confidence and never a phenotype.
Output language is "self-resistance evidence consistent with a bioactive-target hypothesis." ARTS models are
similarity, not identity. Provenance: store-backed (ARTS2 output tables). BGCs cited by node·region.

Parses the four ARTS tables (bgctable, coretable, duptable, knownhits) and maps ARTS clusters to antiSMASH
regions by node+region. No hand-rolled format: reads the real ARTS2 TSV/JSON schema.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import csv, json, os, re, ast, collections
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

# ARTS cluster id "cluster-18_1" -> (NODE/scaffold 18, region 1)
_CLUST_RE = re.compile(r"cluster-(\w+?)_(\d+)$")


def _flagged(v):
    return str(v).strip() not in ("", "-", "0", "False", "No", "None", "nan")


def load_arts(arts_dir):
    T = os.path.join(arts_dir, "tables")
    def tsv(name):
        with open(os.path.join(T, name), encoding="utf-8") as fh:
            rows = list(csv.reader(fh, delimiter="\t"))
        hdr = [c.lstrip("#").strip() for c in rows[0]]
        return hdr, [dict(zip(hdr, r)) for r in rows[1:]]

    _, bgc = tsv("bgctable.tsv")
    _, core = tsv("coretable.tsv")
    _, dup = tsv("duptable.tsv")
    _, known = tsv("knownhits.tsv")

    # duplicated core-gene models (duptable is keyed by Core_gene model id: TIGRxxxx / PFxxxx)
    dup_models = {r["Core_gene"].strip(): float(r.get("Count") or 0) for r in dup}
    # coretable multi-criteria flags, keyed by Core_gene model
    core_flags = {}
    for r in core:
        crit = {k: _flagged(r.get(k, "")) for k in ("Duplication", "BGC_Proximity", "Phylogeny", "Known_target")}
        core_flags[r["Core_gene"].strip()] = {"desc": r.get("Description", ""), "func": r.get("Function", ""),
                                              "crit": crit, "n_crit": sum(crit.values())}
    return bgc, core_flags, dup_models, known


def analyze(arts_dir, strain="UNSPECIFIED", assembly_tier=None):
    bgc, core_flags, dup_models, known = load_arts(arts_dir)

    # --- B1 assembly-quality guard -------------------------------------------------
    # ARTS's duplication + BGC-proximity criterion is assembly-sensitive: a fragmented
    # assembly both splits/duplicates core genes artefactually and blurs which BGC a
    # resistance gene is "proximal" to. Two independent signals downgrade confidence:
    #   (1) the Mamey assembly tier is POOR/VERY_POOR (passed in), and
    #   (2) an implausibly high genome-wide duplication fraction (e.g. AS-XXX ~80%).
    n_core = len(core_flags) or 1
    n_dup_core = sum(1 for v in core_flags.values() if v["crit"].get("Duplication"))
    dup_fraction = n_dup_core / n_core
    tier = (assembly_tier or "").upper().replace("-", "_")
    tier_poor = tier in ("POOR", "VERY_POOR")
    implausible_dup = dup_fraction > 0.5
    bgc_proximity_low_conf = tier_poor or implausible_dup
    _reasons = []
    if tier_poor:
        _reasons.append(f"assembly tier {tier}")
    if implausible_dup:
        _reasons.append(f"implausible duplication fraction {dup_fraction:.0%} (>50% — assembly-inflated)")
    guard_reason = "; ".join(_reasons) if _reasons else ""
    # -------------------------------------------------------------------------------

    per_bgc = []
    for row in bgc:
        cl = row["Cluster"].strip()
        m = _CLUST_RE.match(cl)
        node = f"NODE_{m.group(1)}" if m else cl
        region = f"region{int(m.group(2)):03d}" if m else "?"
        try:
            hits = ast.literal_eval(row["Genelist"]) if row.get("Genelist") else []
        except Exception:
            hits = []
        # each hit: [gene_id, model, start, end, Core/DUF, description, function]
        core_hits = [h for h in hits if len(h) > 4 and h[4] == "Core"]
        # self-resistance leads = Core hits whose model is ALSO duplicated (dup + BGC-proximal by construction)
        dup_prox = []
        for h in core_hits:
            model = str(h[1]).strip()
            if model in dup_models or (model in core_flags and core_flags[model]["crit"]["Duplication"]):
                dup_prox.append({"model": model, "desc": (h[5] if len(h) > 5 else ""),
                                 "dup_count": dup_models.get(model)})
        multi_crit = [h for h in core_hits if str(h[1]).strip() in core_flags
                      and core_flags[str(h[1]).strip()]["n_crit"] >= 2]
        lead = bool(dup_prox)   # duplicated-AND-proximal = the self-resistance lead-priority flag
        per_bgc.append({
            "strain": strain, "node": node, "region": region, "arts_cluster": cl,
            "type": row.get("Type", ""), "location": row.get("Location", ""),
            "core_hits": int(row.get("Core hits") or len(core_hits)),
            "dup_proximal_core_genes": "; ".join(f"{d['model']}({d['desc'][:40]})" for d in dup_prox),
            "n_dup_proximal": len(dup_prox),
            "n_multi_criteria": len(multi_crit),
            "self_resistance_lead": lead,
            # B1: BGC-proximity confidence — 'low' when the assembly guard fires, else 'standard'
            "lead_confidence": ("low" if bgc_proximity_low_conf else "standard") if lead else "",
        })
    # genome-wide resistome (knownhits) — NOT per-BGC unless proximal (checked separately)
    resistome = collections.Counter(r["Description"].strip() for r in known)
    summary = {
        "strain": strain,
        "n_bgc_with_arts_hits": len(per_bgc),
        "n_self_resistance_leads": sum(1 for b in per_bgc if b["self_resistance_lead"]),
        "n_dup_and_proximal_total": sum(b["n_dup_proximal"] for b in per_bgc),
        "n_multi_criteria_core_genes": sum(1 for v in core_flags.values() if v["n_crit"] >= 2),
        "resistome_models": dict(resistome.most_common(12)),
        "n_knownhits": len(known),
        # B1 assembly-quality guard
        "assembly_tier": tier or "UNKNOWN",
        "dup_fraction": round(dup_fraction, 3),
        "bgc_proximity_confidence": "low" if bgc_proximity_low_conf else "standard",
        "guard_reason": guard_reason,
    }
    return per_bgc, summary


def write_outputs(per_bgc, summary, out_csv, out_md):
    cols = ["strain", "node", "region", "arts_cluster", "type", "location", "core_hits",
            "n_dup_proximal", "dup_proximal_core_genes", "n_multi_criteria", "self_resistance_lead",
            "lead_confidence"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = _SafeDictWriter(f, fieldnames=cols); w.writeheader()
        for b in sorted(per_bgc, key=lambda x: (-x["n_dup_proximal"], x["node"])):
            w.writerow({k: b[k] for k in cols})
    leads = [b for b in per_bgc if b["self_resistance_lead"]]
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(f"# ARTS2 self-resistance signal — {summary['strain']} (lead-priority, not claim-confidence)\n\n")
        f.write("*Store-backed (ARTS2 tables). ARTS models = similarity, not identity. A duplicated + BGC-proximal "
                "core gene is self-resistance **evidence consistent with a bioactive-target hypothesis** — it raises "
                "LEAD PRIORITY, never claim confidence, and is not a per-BGC phenotype. BGCs cited node·region.*\n\n")
        if summary.get("bgc_proximity_confidence") == "low":
            f.write(f"> ⚠️ **Assembly-quality guard (B1): BGC-proximity assignments are LOW-CONFIDENCE for {summary['strain']}** "
                    f"— {summary['guard_reason']}. On a fragmented assembly the duplication + BGC-proximity criterion "
                    f"is unreliable: gene-level known-resistance-model hits still stand, but *which BGC* a duplicated core "
                    f"gene sits next to is not trustworthy. Treat every lead below as a gene-level flag to review, not a "
                    f"BGC-assigned self-resistance call.\n\n")
        else:
            f.write(f"- Assembly-quality guard (B1): BGC-proximity confidence **standard** "
                    f"(tier {summary.get('assembly_tier','UNKNOWN')}, duplication fraction {summary.get('dup_fraction')}).\n")
        f.write(f"- {summary['n_bgc_with_arts_hits']} BGCs carry ARTS core-gene hits; "
                f"**{summary['n_self_resistance_leads']}** are self-resistance leads "
                f"({summary['n_dup_and_proximal_total']} duplicated-and-proximal core genes total).\n")
        f.write(f"- {summary['n_multi_criteria_core_genes']} core genes hit ≥2 ARTS criteria genome-wide.\n")
        f.write(f"- Genome resistome (knownhits, NOT BGC-proximal here — general, not per-BGC leads): "
                + ", ".join(f"{k}×{v}" for k, v in list(summary['resistome_models'].items())[:8]) + f" ({summary['n_knownhits']} total).\n\n")
        f.write("## Self-resistance leads (duplicated + BGC-proximal core gene)\n\n")
        f.write("> **Review prompt, not verdict.** ARTS's duplicated+proximal signal over-fires on genes that are the\n"
                "> BGC's *own* machinery rather than a resistant target-copy — e.g. sugar-biosynthesis genes (`rmlA`,\n"
                "> `dTDP-glucose 4,6-dehydratase`) inside a glycosylated/oligosaccharide BGC are intrinsic, not\n"
                "> self-resistance. A genuine self-resistance lead is a duplicated *target* of the product's chemistry\n"
                "> (e.g. a duplicated ribosomal/gyrase/cell-wall gene by a matching BGC). Judge each below on that basis.\n\n")
        for b in sorted(leads, key=lambda x: -x["n_dup_proximal"]):
            intrinsic = bool(re.search(r"rmlA|dTDP|glucose|thymidylyl|sugar|glycosyl", b["dup_proximal_core_genes"], re.I))
            tag = " _(likely BGC-intrinsic — sugar/tailoring machinery, discount)_" if intrinsic else ""
            f.write(f"- **{b['strain']} {b['node']}·{b['region']}** ({b['type']}): "
                    f"{b['n_dup_proximal']} duplicated-proximal core gene(s) — {b['dup_proximal_core_genes']}."
                    f"{tag}\n")
        _strain = per_bgc[0]["strain"] if per_bgc else "this strain"
        f.write(f"\n*M7 v1 — mapped by node·region to antiSMASH; relate to Mamey BGC IDs when the {_strain} sealed "
                "package is available. Not a CLI verb yet; capability-gated on an ARTS2 output being attached.*\n")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Ingest an ARTS2 result into a per-BGC self-resistance signal.")
    ap.add_argument("--arts-dir", required=True, help="unzipped ARTS2 result dir (contains tables/)")
    ap.add_argument("--strain", required=True, help="strain ID this ARTS2 result belongs to (no default — "
                     "a silently wrong strain label was a prior footgun)")
    ap.add_argument("--out-csv", default="ARTS_self_resistance.csv")
    ap.add_argument("--out-md", default="ARTS_self_resistance.md")
    ap.add_argument("--assembly-tier", default=None,
                    help="Mamey assembly tier for this strain (GOOD/MODERATE/POOR/VERY_POOR). "
                         "POOR/VERY_POOR marks BGC-proximity assignments low-confidence (B1 guard). "
                         "The guard also fires automatically on an implausible genome-wide duplication fraction.")
    a = ap.parse_args(argv)
    per_bgc, summary = analyze(a.arts_dir, a.strain, assembly_tier=a.assembly_tier)
    write_outputs(per_bgc, summary, a.out_csv, a.out_md)
    emit(f"{summary['strain']}: {summary['n_bgc_with_arts_hits']} BGCs w/ ARTS hits, "
          f"{summary['n_self_resistance_leads']} self-resistance leads, "
          f"{summary['n_dup_and_proximal_total']} dup+proximal core genes, {summary['n_knownhits']} resistome models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""strain_bigscape_report.py -- per-strain BiG-SCAPE report as a standard Sapote-Mamey deliverable.

Produces a single strain's cross-strain / MIBiG-anchored biosynthetic report in the bundle's
markdown deliverable voice, from the PORTABLE derived TSVs (no 400 MB DB): the per-BGC annotation,
and optionally the antimicrobial-capacity, novel-family, and strain-pair-sharing tables. Because it
reads the small exports, it runs anywhere the AS_analysis_export bundle goes.

Sections (always): Overview; Assembly quality (fragmentation, read the counts with this); BGC class
distribution; MIBiG anchors (antifungal / ionophore flagged); Novel families; Biosynthetic
neighbours; Caveats. All capacity-level, node.region-located, provenance-tagged. Filename carries
the strain ID (bundle convention). No compound-production or per-BGC bioactivity claims are emitted.

Usage:
  python strain_bigscape_report.py --strain AS-XXX \
      --per-bgc per_strain_BGC_annotation_51.tsv \
      [--antimicrobial antimicrobial_capacity_by_strain_51.tsv] \
      [--novel novel_antimicrobial_targets_51.tsv] \
      [--sharing strain_pair_shared_BGCs_51.tsv] \
      [--genus Actinophytocola --habitat attine] \
      [--out AS-XXX_bigscape_report.md]

Stdlib only. Builder tool; no gate row.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, re, os, collections, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.bigscape_namespace import NamespaceError, load_membership_tsv, public_error
from mamey.missing_values import optional_float, optional_text

ANTIFUNGAL = ["selvamicin", "filipin", "azalomycin", "pentamycin", "candicidin", "nystatin",
              "niphimycin", "faeriefungin", "frontalamide", "clifednamide", "combamide", "antimycin"]
POLYETHER = ["nigericin", "salinomycin", "monensin", "lasalocid"]
OVERBROAD = ["platensimycin"]  # cohort-wide conserved anchors; low confidence


def read_tsv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def col(row, *names):
    low = {k.lower(): k for k in row}
    for n in names:
        if n in low:
            return row[low[n]]
    return ""


def contig_len(locator):
    m = re.search(r"length_(\d+)", locator or "")
    return int(m.group(1)) if m else None


def median_value(values):
    """Conventional median: the middle value, or the mean of the two middle values for an even count."""
    ordered = sorted(values)
    if not ordered:
        return None
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def flag_compound(comp):
    c = (comp or "").lower()
    if any(x in c for x in ANTIFUNGAL):
        return "antifungal"
    if any(x in c for x in POLYETHER):
        return "ionophore"
    if any(x in c for x in OVERBROAD):
        return "over-broad"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strain", required=True)
    ap.add_argument("--per-bgc", required=True)
    ap.add_argument("--antimicrobial", help="antimicrobial_capacity_by_strain TSV (adds a capacity section)")
    ap.add_argument("--novel")
    ap.add_argument("--sharing")
    ap.add_argument("--integrated", help="antismash_bigscape_integrated TSV (adds domain architecture + notable BGCs)")
    ap.add_argument("--uniqueness", help="strain_uniqueness TSV (adds a strain-uniqueness section)")
    ap.add_argument("--genus", default="")
    ap.add_argument("--habitat", default="")
    ap.add_argument("--out")
    a = ap.parse_args()

    S = a.strain
    rows = [r for r in read_tsv(a.per_bgc) if col(r, "strain", "strain_id") == S]
    if not rows:
        raise SystemExit(f"no BGCs for {S} in {a.per_bgc}")

    genus = a.genus
    habitat = a.habitat
    # per-row fields
    bgcs = []
    for r in rows:
        loc = col(r, "locator", "node_region", "node.region")
        cls = col(r, "antismash_class", "class", "product")
        status = col(r, "family_status", "bigscape_status", "status")
        anchors = col(r, "mibig_family_anchors", "bigscape_family_anchors", "anchors")
        nearest = col(r, "nearest_mibig", "nearest")
        dist = col(r, "nearest_distance", "distance")
        bgcs.append(dict(loc=loc, cls=cls, status=status, anchors=anchors, nearest=nearest, dist=dist))

    n = len(bgcs)
    known = [b for b in bgcs if b["status"].upper() == "KNOWN"]
    # NOVEL counts only rows whose status says NOVEL. A blank, held or unknown status is not novelty.
    novel_n = sum(1 for b in bgcs if b["status"].upper() == "NOVEL")
    unresolved_n = n - len(known) - novel_n
    cls_counts = collections.Counter(b["cls"] or "?" for b in bgcs)
    lens = sorted(x for x in (contig_len(b["loc"]) for b in bgcs) if x)
    frag = sum(1 for x in lens if x < 15000)

    # MIBiG anchors (nearest compound per known BGC), flagged
    # A KNOWN label is the input table's claim. A KNOWN row that names no nearest reference, or gives
    # no distance, is listed with an explicit "not given" cell and counted as unresolved, never shown
    # as an observed anchor with blank cells.
    anchor_rows = []
    unresolved_known = 0
    for b in known:
        comp = optional_text(b["nearest"])
        dist_v = optional_float(b["dist"])
        if comp is None or dist_v is None:
            unresolved_known += 1
        m = re.search(r"\(([^)]+)\)", comp or "")
        name = (m.group(1) if m else comp) if comp is not None else None
        anchor_rows.append((name, flag_compound(name), b["cls"], dist_v, b["loc"]))
    anchor_rows.sort(key=lambda r: (r[0] is None or r[3] is None, r[1] == "", r[3] if r[3] is not None else 0.0))

    L = []
    L.append(f"# Strain report — {S}")
    meta_bits = " · ".join(x for x in [genus, habitat, "BiG-SCAPE GCF vs MIBiG 4.0", "capacity-level"] if x)
    L.append(f"_{meta_bits}_\n")
    L.append("## Overview")
    L.append(f"{S} has **{n} BGC regions** in the supplied per-BGC table — {len(known)} labeled KNOWN "
             f"(the table says the family holds a MIBiG member), {novel_n} labeled NOVEL (the table says the "
             f"family holds no MIBiG member)"
             + (f", {unresolved_n} have no family status" if unresolved_n else "") + ". These labels are "
             "read from the input as given; this tool does not check family membership, the reference set "
             "or the run and cutoff. The dominant "
             f"class is {cls_counts.most_common(1)[0][0]} ({cls_counts.most_common(1)[0][1]} regions).\n")

    L.append("## Assembly quality — read the counts with this")
    if lens:
        med = median_value(lens)
        med_s = f"{med:,.0f}" if float(med).is_integer() else f"{med:,.1f}"
        L.append(f"BGC-bearing contigs span {min(lens):,}–{max(lens):,} bp (median {med_s}, one value per "
                 f"region row); "
                 f"**{frag} of {len(lens)} BGC regions sit on contigs under 15 kb**. Large modular clusters "
                 f"(PKS/NRPS) are often split across contigs, each called a separate region, so the {n}-BGC "
                 f"count can overcount distinct complete clusters. Treat per-region hits as fragments until a "
                 f"contiguous assembly confirms the cluster.\n")
    else:
        L.append("Contig lengths were not parseable from the locators; interpret the BGC count cautiously.\n")

    L.append("## BGC class distribution")
    # BC2_399 fix: the "always show PKS/NRPS/RiPP-family classes regardless of count" exception
    # compared the raw `antismash_class` TSV value against these three literals case-sensitively.
    # Real antiSMASH classes are lowercase for several of them ("nrps", "t1pks", ...), confirmed
    # against mamey/class_architecture.py::_REAL_CLASSES and this round's sibling case-
    # insensitivity fixes for the identical field -- a real, scientifically important class
    # occurring exactly once (k == 1) was silently omitted from this report section, its own
    # documented intent notwithstanding.
    for c, k in cls_counts.most_common():
        if k >= 2 or any(z in c.upper() for z in ("PKS", "NRPS", "RIPP")):
            L.append(f"- {c}: {k}")
    L.append("")

    # --- antimicrobial capacity section (from the per-strain antimicrobial TSV) ---
    if a.antimicrobial and os.path.exists(a.antimicrobial):
        for r in read_tsv(a.antimicrobial):
            if col(r, "strain", "strain_id") == S:
                af = col(r, "antifungal_candida_anchors", "antifungal_candida")
                ab = col(r, "antibacterial_mrsa_anchors", "antibacterial_mrsa")
                si = col(r, "siderophore_anchors", "siderophore")
                if af or ab or si:
                    L.append("## Antimicrobial capacity (vs MRSA / Candida targets)")
                    L.append("Capacity-level anchors; bioactivity metadata is optional strain-level context, not a per-BGC phenotype.\n")
                    if af:
                        L.append(f"- **Antifungal (Candida-relevant):** {af}")
                    if ab:
                        L.append(f"- **Antibacterial (MRSA-relevant):** {ab}")
                    if si:
                        L.append(f"- **Siderophore (iron competition):** {si}")
                    L.append("")
                break

    # --- load antiSMASH domain architecture per BGC (for anchors + notable clusters) ---
    dom_by_loc = {}
    if a.integrated and os.path.exists(a.integrated):
        for r in read_tsv(a.integrated):
            if col(r, "strain", "strain_id") == S:
                dom_by_loc[col(r, "locator", "node_region")] = col(r, "antismash_domains", "domains")

    L.append("## MIBiG anchors")
    L.append("Nearest MIBiG cluster named in the input for each KNOWN BGC, with the BiG-SCAPE distance as "
             "given (0 = most similar, 1 = least similar in that run's metric and cutoff). A distance is a "
             "similarity score; distance 0 does not show identical sequences or the same product. "
             "Antifungal ≈ Candida-relevant; ionophore = polyether; over-broad = de-prioritise.\n")
    if unresolved_known:
        L.append(f"**{unresolved_known} of {len(known)} KNOWN rows give no nearest MIBiG reference or no "
                 "distance in the input.** Their reference is unresolved; they are listed as \"not given\", "
                 "not as anchors.\n")
    L.append("| nearest MIBiG | type | class | dist | node.region | antiSMASH domains |")
    L.append("|---|---|---|---|---|---|")
    for name, fl, cls, dist, loc in anchor_rows[:25]:
        loc_s = loc if len(loc) < 42 else loc[:40] + "…"
        dom = (dom_by_loc.get(loc, "") or "")[:60]
        name_s = name if name is not None else "not given"
        dist_s = f"{dist:g}" if dist is not None else "not given"
        L.append(f"| {name_s} | {fl or '—'} | {cls} | {dist_s} | {loc_s} | {dom} |")
    L.append("")

    # --- notable BGCs: complete PKS/NRPS assembly lines, confidence-tiered by the 15 kb floor ---
    if dom_by_loc:
        def is_complete(dom):
            d = dom or ""
            pks = "PKS_KS" in d and "PKS_AT" in d and ("ACP" in d or "PP-binding" in d)
            nrps = "Condensation" in d and "AMP-binding" in d and "PCP" in d
            return pks or nrps
        def tier(loc, dom):
            L = contig_len(loc) or 0
            if is_complete(dom) and L >= 15000:
                return "very likely"
            if L >= 15000:
                return "likely"
            return "fragment"
        notable = [(b["loc"], b["cls"], b["status"], dom_by_loc.get(b["loc"], ""),
                    tier(b["loc"], dom_by_loc.get(b["loc"], "")))
                   for b in bgcs if is_complete(dom_by_loc.get(b["loc"], ""))]
        # order very likely first
        rank = {"very likely": 0, "likely": 1, "fragment": 2}
        notable.sort(key=lambda x: rank.get(x[4], 3))
        if notable:
            vln = sum(1 for x in notable if x[4] == "very likely")
            L.append("## Notable BGCs (intact assembly lines)")
            L.append(f"{len(notable)} of {S}'s BGCs carry a complete core assembly line "
                     "(PKS: KS+AT+ACP; NRPS: C+A+PCP); "
                     f"**{vln} are 'very likely' real** (complete core on a ≥15 kb contig). Confidence floor "
                     "= 15 kb: below it a complete-looking core is treated as a fragment, not a cluster.\n")
            L.append("| node.region | class | status | confidence | assembly-line domains |")
            L.append("|---|---|---|---|---|")
            for loc, cls, status, dom, tr in notable[:20]:
                loc_s = loc if len(loc) < 40 else loc[:38] + "…"
                L.append(f"| {loc_s} | {cls} | {status} | {tr} | {dom[:60]} |")
            L.append("")

    if a.novel and os.path.exists(a.novel):
        nv = []
        for r in load_membership_tsv(a.novel, key_fields=("qualified_family_id",)):
            strains = col(r, "strains", "as_strains")
            if S in strains.split(","):
                nv.append((col(r, "family_id", "family"), r["qualified_family_id"], col(r, "class"),
                           col(r, "n_strains", "n_strains_total"),
                           col(r, "assembly_line_architecture", "architecture")))
        if nv:
            L.append("## Families with no MIBiG member")
            L.append(f"{S} participates in {len(nv)} antimicrobial-class families with no MIBiG member. "
                     "Family membership is similarity to other regions, not evidence of a new compound; "
                     "regions with complete assembly lines are the ones to inspect first.\n")
            L.append("| family | class | # strains | architecture |")
            L.append("|---|---|---|---|")
            for fid, qualified, cls, ns, arch in nv[:15]:
                arch_s = (arch or "")[:60]
                L.append(f"| {fid} (`{qualified}`) | {cls} | {ns} | {arch_s} |")
            L.append("")

    if a.sharing and os.path.exists(a.sharing):
        nbr = []
        for r in read_tsv(a.sharing):
            av = col(r, "strain_a"); bv = col(r, "strain_b")
            sh = col(r, "shared_gcf_families", "shared")
            if av == S:
                nbr.append((bv, sh))
            elif bv == S:
                nbr.append((av, sh))
        nbr.sort(key=lambda x: -int(x[1] or 0))
        if nbr:
            L.append("## Biosynthetic neighbours")
            L.append("Strains sharing the most GCF families with " + S + " (closest biosynthetic relatives):\n")
            for s, sh in nbr[:8]:
                L.append(f"- {s}: {sh} shared families")
            L.append("")

    if a.uniqueness and os.path.exists(a.uniqueness):
        for r in read_tsv(a.uniqueness):
            if col(r, "strain", "strain_id") == S:
                tot = col(r, "total_family_bgcs", "total")
                uniq = col(r, "unique_bgcs", "unique")
                shared = col(r, "shared_bgcs", "shared")
                excl = col(r, "strain_exclusive_families", "sole_families")
                try:
                    pct = round(100 * int(uniq) / max(1, int(tot)))
                except (ValueError, TypeError):
                    pct = "?"
                L.append("## Uniqueness")
                L.append(f"Of {S}'s {tot} family-assigned BGCs, **{uniq} are strain-unique** ({pct}%) — they "
                         f"fall in {excl} GCF families that no other cohort strain occupies; the remaining "
                         f"{shared} are shared. A high strain-unique fraction means much of this strain's "
                         "biosynthetic families are not shared with any other cohort strain. That is a family-level "
                         "observation, not a novelty claim, and some of it reflects assembly-driven family splits.\n")
                break

    L.append("## Caveats")
    L.append("- Capacity-level: anchors are GCF domain-architecture similarity, not compound identity or "
             "production. Bioactivity metadata is optional context; no per-BGC phenotype is claimed.")
    L.append("- Fragmentation inflates BGC/class counts and splits real clusters; confirm distinct clusters "
             "against a contiguous assembly before quantitative claims.")
    L.append("- Over-broad anchors (e.g. platensimycin) are cohort-wide and low-confidence; NAPAA excluded "
             "from comparative claims.")
    L.append(f"\n_{S} strain report · anchored cohort · capacity-level; per-BGC confirmation required._")

    out = a.out or f"{S}_bigscape_report.md"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    emit(f"wrote {out}: {n} BGCs ({len(known)} known / {novel_n} novel / {unresolved_n} no status), {len(anchor_rows) - unresolved_known} anchors"
         + (f", {unresolved_known} KNOWN without a reference" if unresolved_known else ""))


if __name__ == "__main__":
    try:
        main()
    except NamespaceError as error:
        # v9.7.405: sys.stderr.write, not print() — a typed-refusal diagnostic, and the
        # print ratchet is at ceiling. Registering these front doors as EXCLUDED files
        # would have dropped their PRE-EXISTING prints from the count too: a lower
        # measure without paying anything.
        sys.stderr.write(public_error(error) + "\n")
        sys.exit(2)

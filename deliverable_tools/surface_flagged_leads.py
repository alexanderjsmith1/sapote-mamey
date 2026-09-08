#!/usr/bin/env python3
"""surface_flagged_leads.py — surface two review groups out of the whole-BGC majority read.

Reads `whole_bgc_majority_read_cohort.csv` (from whole_bgc_majority_read.py) and produces two
curated, claim-safe lists the Developer or User asked to review (2026-08-05):

  GROUP A — PROMISCUOUS_ONLY  (genome-level review)
    The MIBiG anchor rests only on promiscuous PKS/NRPS scaffold genes (KS/AT/KR/ACP/PCP/A-domain),
    so the family label is unreliable. These deserve a GENOME-level look: a fragmented locus
    (boundary = Edge / Full-contig) can often be reconstructed from a related, better-assembled
    strain. We flag fragmentation and list near-identical sibling strains (potential reconstruction
    donors) from the QC identical-protein pairs.

  GROUP B — LOW_ID but COHERENT  (candidate divergent family members)
    LOW_ID (median <55%) AND NOT SHIFTING_BESTHIT — i.e. the whole (or most) of the anchored genes
    consistently resemble ONE characterized family, just at low identity. A coherent low-identity
    locus is the classic shape of a candidate DIVERGENT member / analog of that family. We separate
    specialized-metabolite families (leads) from ubiquitous/housekeeping ones (ectoine, geosmin,
    terpene) which are conserved primary-ish metabolism, not drug leads.

Claim-safety: everything is class-level capacity. Similarity != identity; a divergent anchor is a
novelty HYPOTHESIS, not a verified novel compound; fragmentation flags an assembly caveat, not a
biological one. Judgment deferred.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, collections, os
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path
try:
    from mamey.canonical_write_guard import guard_canonical_write
except ImportError:  # bare-script run: bundle root is one level up
    import os as _g_os, sys as _g_sys
    _g_sys.path.insert(0, _g_os.path.dirname(_g_os.path.dirname(_g_os.path.abspath(__file__))))
    from mamey.canonical_write_guard import guard_canonical_write

ROOT = Path(os.environ.get("MAMEY_DATA_ROOT", os.getcwd()))
OUTDIR = ROOT / "strain_data" / "flagged_lead_surfacing_2026-08-05"
COHORT = ROOT / "strain_data" / "whole_bgc_majority_read_2026-08-05" / "whole_bgc_majority_read_cohort.csv"
QC = ROOT / "strain_data" / "_QC_strain_identity" / "AS_AS_identical_bgc_pairs.tsv"

# Ubiquitous / housekeeping-ish families: a low-id hit here means "divergent conserved metabolism",
# not a specialized-metabolite novelty lead. Substring match on the anchor compound, case-insensitive.
UBIQUITOUS = ("ectoine", "geosmin", "2-methylisoborneol", "methylisoborneol", "hopene", "hopanoid",
              "carotenoid", "isorenieratene", "desferrioxamine", "terpene")
FRAGMENTED = ("Edge", "Full-contig")

def sibling_donors() -> dict[str, set[str]]:
    """strain -> set of near-identical sibling strains (from QC identical-protein pairs)."""
    m: dict[str, set[str]] = collections.defaultdict(set)
    if not QC.is_file():
        return m
    with QC.open() as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            a, b = r.get("strainA", ""), r.get("strainB", "")
            if a and b:
                m[a].add(b); m[b].add(a)
    return m

def is_ubiquitous(compound: str) -> bool:
    c = (compound or "").lower()
    return any(u in c for u in UBIQUITOUS)

def main() -> int:
    # v9.7.412 (BC2): --out, mirroring the sibling `majority-read` tool. Without it this command
    # had NO way to redirect its output and rewrote the canonical dated deliverable in place on
    # every run — and `<MAMEY_DATA_ROOT>/strain_data` is a symlink to the workspace's canonical
    # home, so "just seeing what it does" silently overwrote real data. Default is unchanged.
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="output directory (default: the canonical "
                                  "<MAMEY_DATA_ROOT>/strain_data/flagged_lead_surfacing_2026-08-05, "
                                  "which is overwritten in place)")
    ap.add_argument("--force", "--in-place", dest="force", action="store_true",
                    help="allow overwriting an existing canonical dated deliverable")
    a = ap.parse_args()
    outdir = Path(a.out) if a.out else OUTDIR

    outdir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(COHORT.open()))
    donors = sibling_donors()

    def flags(r): return set(x for x in r["flags"].split(",") if x)

    promisc = [r for r in rows if "PROMISCUOUS_ONLY" in flags(r)]
    lowid_coh = [r for r in rows if "LOW_ID" in flags(r) and "SHIFTING_BESTHIT" not in flags(r)
                 and int(r["hit_genes"]) > 0]

    # sort: fragmented first (reconstruction candidates), then by strain/bgc
    def frag_rank(r): return 0 if r.get("boundary") in FRAGMENTED else 1
    promisc.sort(key=lambda r: (frag_rank(r), r["strain"], r["bgc_id"]))
    # low-id coherent: specialized leads first, then by share desc, id asc (most divergent)
    lowid_coh.sort(key=lambda r: (is_ubiquitous(r["anchor_compound"]),
                                  -float(r["query_gene_share"]), float(r["median_pct_identity"] or 99)))

    # ---- write combined CSV ----
    csv_path = outdir / "flagged_lead_surfacing.csv"
    # v9.7.413 (BC2): refuse to silently replace an existing canonical dated deliverable.
    for _p in (csv_path, outdir / "FLAGGED_LEAD_SURFACING.md"):
        guard_canonical_write(_p, force=a.force)
    with csv_path.open("w", newline="") as fh:
        w = _SafeWriter(fh)
        w.writerow(["group", "strain", "bgc_id", "products", "boundary", "hit_genes", "total_genes",
                    "query_gene_share", "median_pct_identity", "anchor_compound", "class_concordance",
                    "anchor_gene_types", "sibling_donors", "family_class", "review_note"])
        for r in promisc:
            frag = r.get("boundary") in FRAGMENTED
            sib = ";".join(sorted(donors.get(r["strain"], set())))
            note = ("fragmented locus -> reconstruct from a better-assembled sibling" if frag and sib
                    else "fragmented locus -> needs better assembly" if frag
                    else "promiscuous-only anchor -> confirm at genome level")
            w.writerow(["A_PROMISCUOUS_ONLY", r["strain"], r["bgc_id"], r["products"], r["boundary"],
                        r["hit_genes"], r["total_genes"], r["query_gene_share"], r["median_pct_identity"],
                        r["anchor_compound"], r["class_concordance"], r["anchor_gene_types"], sib,
                        "", note])
        for r in lowid_coh:
            fam = "ubiquitous/housekeeping" if is_ubiquitous(r["anchor_compound"]) else "specialized"
            note = ("coherent low-id divergent member (candidate analog)" if fam == "specialized"
                    else "divergent conserved metabolism (not a drug lead)")
            w.writerow(["B_LOWID_COHERENT", r["strain"], r["bgc_id"], r["products"], r["boundary"],
                        r["hit_genes"], r["total_genes"], r["query_gene_share"], r["median_pct_identity"],
                        r["anchor_compound"], r["class_concordance"], r["anchor_gene_types"], "", fam, note])

    # ---- markdown ----
    md = []
    md.append("# Flagged-lead surfacing — PROMISCUOUS_ONLY + coherent LOW_ID\n")
    md.append("*Built 2026-08-05 (the roster lane) from `whole_bgc_majority_read_cohort.csv`. "
              "Class-level capacity hypotheses; similarity != identity; judgment deferred.*\n")

    frag_prom = [r for r in promisc if r.get("boundary") in FRAGMENTED]
    md.append(f"\n## Group A — PROMISCUOUS_ONLY ({len(promisc)} BGCs) — genome-level review\n")
    md.append("The named family rests only on promiscuous scaffold genes (KS/AT/KR/ACP/PCP/A-domain), "
              "which recur across unrelated clusters — so the label cannot be trusted without a "
              f"genome-level look. **{len(frag_prom)} sit on a fragmented locus (Edge / Full-contig)** "
              "and are reconstruction candidates: a related, better-assembled sibling strain may carry "
              "the intact locus.\n")
    md.append("| strain | BGC | products | boundary | anchor (scaffold genes) | share | id | sibling donors | note |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for r in promisc[:60]:
        sib = ", ".join(sorted(donors.get(r["strain"], set()))) or "—"
        md.append(f"| {r['strain']} | {r['bgc_id']} | {r['products'][:20]} | {r['boundary']} | "
                  f"{r['anchor_compound'][:18]} ({r['anchor_gene_types'][:34]}) | {r['query_gene_share']} | "
                  f"{r['median_pct_identity']}% | {sib} | {'frag→reconstruct' if r.get('boundary') in FRAGMENTED else 'confirm'} |")
    if len(promisc) > 60:
        md.append(f"\n*(+{len(promisc)-60} more in the CSV)*")

    spec = [r for r in lowid_coh if not is_ubiquitous(r["anchor_compound"])]
    ubiq = [r for r in lowid_coh if is_ubiquitous(r["anchor_compound"])]
    subst = [r for r in spec if float(r["query_gene_share"]) >= 0.25]
    interior_spec = [r for r in spec if r["boundary"] == "Interior"]
    frag_spec = [r for r in spec if r["boundary"] in FRAGMENTED]
    md.append(f"\n## Group B — coherent LOW_ID ({len(lowid_coh)} BGCs) — candidate divergent family members\n")
    md.append(f"LOW_ID (<55%) AND consistent across the anchored genes (not shifting). "
              f"**{len(spec)} hit specialized-metabolite families**, {len(ubiq)} hit "
              "ubiquitous/housekeeping families (ectoine/geosmin/terpene — divergent conserved "
              "metabolism, not drug leads).\n")
    md.append("> **Read the `boundary` column carefully.** A high share here is usually an ARTIFACT of "
              "truncation: a `Full-contig`/`Edge` locus that reads `2/2 genes (share 1.0)` is a chopped "
              f"fragment, not a complete coherent cluster. **{len(frag_spec)} of the {len(spec)} "
              f"specialized hits are fragmented** (share=1.0 endopyrrole/rhizomide/enduracidin etc. are "
              "truncated) → they are ALSO reconstruction candidates (see Group A). The "
              f"**{len(interior_spec)} on complete Interior loci** carry only 2–3 divergent genes each "
              "(low share) — a genuine but weak per-locus novelty signal to review individually. A "
              "clean 'complete locus, many genes, uniformly low identity' divergent member is RARE in "
              "this cohort.\n")
    md.append("### Specialized-family divergent hits (share desc — remember fragmented=truncated)\n")
    md.append("| strain | BGC | products | anchor family | hit/total | share | id | boundary |")
    md.append("|---|---|---|---|---|---|---|---|")
    for r in sorted(spec, key=lambda r: -float(r["query_gene_share"])):
        md.append(f"| {r['strain']} | {r['bgc_id']} | {r['products'][:18]} | {r['anchor_compound'][:24]} | "
                  f"{r['hit_genes']}/{r['total_genes']} | {r['query_gene_share']} | {r['median_pct_identity']}% | {r['boundary']} |")
    md.append(f"\n*Ubiquitous/housekeeping coherent-LOW_ID ({len(ubiq)} BGCs, mostly ectoine) listed in the CSV.*\n")
    md.append("\n**Claim-safety.** A coherent low-identity anchor is a novelty HYPOTHESIS (a candidate "
              "divergent member of the named family), never a verified novel compound or an activity "
              "claim. Fragmentation is an assembly caveat. Judgment deferred.\n")

    (outdir / "FLAGGED_LEAD_SURFACING.md").write_text("\n".join(md), encoding="utf-8")
    emit(f"GROUP A PROMISCUOUS_ONLY : {len(promisc)}  ({len(frag_prom)} fragmented → reconstruction candidates)")
    emit(f"GROUP B LOW_ID coherent  : {len(lowid_coh)}  ({len(spec)} specialized / {len(ubiq)} ubiquitous; "
          f"{len(subst)} specialized+substantial)")
    emit(f"  -> {outdir/'FLAGGED_LEAD_SURFACING.md'}", f"  -> {csv_path}", sep="\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

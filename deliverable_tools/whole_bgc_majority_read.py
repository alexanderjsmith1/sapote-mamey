#!/usr/bin/env python3
"""whole_bgc_majority_read.py — read a MIBiG family call across the WHOLE BGC, not the 2 genes.

THE DEFECT THIS FIXES
---------------------
A report labeled AS-XXX BGC059 "KNOWN -> tetrachlorizine". In truth only 2 of the BGC's 17 genes
hit the tetrachlorizine MIBiG cluster -- and both are PROMISCUOUS PKS-core genes (a ketoacyl-synthase
KS and a PP-binding/ACP carrier) at 46-50% identity. The other 15 genes are fatty-acid / primary
metabolism (fabH, malonyl-CoA:ACP transacylase, ...). A couple of promiscuous scaffold genes
resembling genes from a characterized cluster is a CLASS-LEVEL anchor at most -- never "= that
compound." The family call was biased by a 2-gene minority.

WHAT THIS TOOL DOES (the "whole-BGC majority read")
---------------------------------------------------
For every BGC it joins the three CANONICAL per-BGC tables (NOT thesis_capture) and asks:
  * How many of the BGC's TRUE genes hit MIBiG at all?  (query_gene_share = hit_genes / total_genes)
  * Do the per-gene best-hits AGREE on one compound, or does the closest match SHIFT gene to gene?
  * Are the anchor-supporting genes only PROMISCUOUS scaffold (KS/AT/KR/ACP/PP-binding/PCP/A-domain),
    which recur across unrelated clusters and cannot by themselves name a product?
Then it emits an honest, claim-safe one-liner and flags:
  MINORITY_ANCHOR       query_gene_share < 0.25 (default)
  PROMISCUOUS_ONLY      every anchor-supporting gene is a promiscuous scaffold domain
  SHIFTING_BESTHIT      the anchor compound is not the plurality best-hit across hitting genes
  LOW_ID                median identity < 55%
A call flagged MINORITY_ANCHOR or PROMISCUOUS_ONLY must be written as class-level SIMILARITY with its
denominator, never as a product identity.

CANONICAL SOURCES (per strain, under gene_layer_working_2026-07-31/runs/<strain>/package/):
  <strain>_gene_by_gene_all_bgcs.csv  -> TRUE gene roster + sec_met_domains (denominator + gene type)
  <strain>_3_mibig_per_gene.csv       -> per-gene MIBiG best-hit + %identity  (join: query_gene==locus_tag)
  <strain>_3_mibig_convergence.csv    -> rolled-up family call (query_gene_share, tier, class_concordance)

Raw per-gene reader => honors mamey.exclusions.raw_analysis_excluded() == {AS-XXX, AS-XXX}.

Usage:
  whole_bgc_majority_read.py --strain AS-XXX --bgc BGC059          # single BGC, verbose proof
  whole_bgc_majority_read.py --strain AS-XXX                        # one strain, all BGCs
  whole_bgc_majority_read.py --cohort --out DIR                     # every strain -> CSV + summary
"""
from __future__ import annotations

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, sys
from collections import Counter
from pathlib import Path

try:
    from mamey.canonical_write_guard import guard_canonical_write
except ImportError:  # bare-script run: bundle root is one level up
    import os as _g_os, sys as _g_sys
    _g_sys.path.insert(0, _g_os.path.dirname(_g_os.path.dirname(_g_os.path.abspath(__file__))))
    from mamey.canonical_write_guard import guard_canonical_write

ROOT = Path(os.environ.get("MAMEY_DATA_ROOT", os.getcwd()))
RUNS = ROOT / "strain_data" / "gene_layer_working_2026-07-31" / "runs"

# --- exclusion SSOT (raw per-gene reader -> raw_analysis_excluded) ---------------------------------
def _excluded() -> set[str]:
    for tree in sorted(ROOT.glob("sapote-mamey-v*-CODE-*"), reverse=True):
        try:
            sys.path.insert(0, str(tree))
            from mamey.exclusions import raw_analysis_excluded  # type: ignore
            return set(raw_analysis_excluded())
        except Exception:
            continue
        finally:
            if str(tree) in sys.path:
                sys.path.remove(str(tree))
    raise RuntimeError(
        "cohort exclusions are governed data and are not shipped in the code tier: "
        "install the mamey package, or set MAMEY_OFFICIAL_DATA to a directory "
        "containing exclusions.json"
    )

EXCLUDE = _excluded() | {"AS-000_CONSDARK"}

# Promiscuous scaffold domains: PKS/NRPS core carriers + condensing/reducing enzymes that recur across
# chemically unrelated clusters, so a hit on one of these alone cannot name a product. Substrings are
# matched case-insensitively against the gene_by_gene sec_met_domains field.
PROMISCUOUS = ("pks_ks", "ketoacyl-synt", "ketoacyl_synt", "pp-binding", "acp", "acyl_transf",
               "pks_at", "pksi-at", "pks_kr", "ketoreduct", "amp-binding", "a-domain",
               "adenylation", "condensation", "pcp", "thiolase")
STRONG_FRAC = 0.25   # < this share of the BGC's genes => MINORITY_ANCHOR
STRONG_ID = 55.0     # median identity < this => LOW_ID

def _pkg(strain: str) -> Path:
    return RUNS / strain / "package"

def _read_csv(p: Path) -> list[dict]:
    if not p.is_file():
        return []
    with p.open(encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))

def _is_promiscuous(domains: str) -> bool:
    d = (domains or "").lower()
    return any(tok in d for tok in PROMISCUOUS)

def analyze_strain(strain: str) -> list[dict]:
    pkg = _pkg(strain)
    roster = _read_csv(pkg / f"{strain}_gene_by_gene_all_bgcs.csv")
    pergene = _read_csv(pkg / f"{strain}_3_mibig_per_gene.csv")
    conv = {r["bgc_id"]: r for r in _read_csv(pkg / f"{strain}_3_mibig_convergence.csv")}
    if not roster:
        return []
    # roster: bgc -> {locus_tag: sec_met_domains}, and total gene count
    genes_by_bgc: dict[str, dict[str, str]] = {}
    products: dict[str, str] = {}
    for r in roster:
        b = r.get("bgc_id", "")
        if not b:
            continue
        genes_by_bgc.setdefault(b, {})[r.get("locus_tag", "")] = r.get("sec_met_domains", "")
        products.setdefault(b, r.get("bgc_products", "") or r.get("product_qualifier", ""))
    # per-gene hits: bgc -> list of (query_gene, compound, ref_type, pct_id)
    hits_by_bgc: dict[str, list[tuple]] = {}
    for r in pergene:
        b = r.get("bgc_id", "")
        if not b:
            continue
        try:
            pid = float(r.get("pct_identity") or 0)
        except ValueError:
            pid = 0.0
        hits_by_bgc.setdefault(b, []).append(
            (r.get("query_gene", ""), r.get("mibig_compound", ""), r.get("reference_type", ""), pid))

    out = []
    for bgc, genes in sorted(genes_by_bgc.items()):
        total = len(genes)
        hits = hits_by_bgc.get(bgc, [])
        hit_genes = sorted({h[0] for h in hits})
        n_hit = len(hit_genes)
        share = (n_hit / total) if total else 0.0
        cv = conv.get(bgc, {})
        # anchor compound: prefer the rolled-up convergence call, else the plurality per-gene compound
        anchor = cv.get("mibig_compound", "") or (
            Counter(h[1] for h in hits).most_common(1)[0][0] if hits else "")
        # per-gene best-hit compound distribution (does the closest match SHIFT across the BGC?)
        comp_counts = Counter(h[1] for h in hits)
        plurality = comp_counts.most_common(1)[0][0] if comp_counts else ""
        shifting = bool(comp_counts) and (anchor != plurality or len(comp_counts) > 1)
        # anchor-supporting genes and whether they are ALL promiscuous scaffold
        anchor_genes = [h for h in hits if h[1] == anchor] or hits
        anchor_gene_types = []
        promisc_flags = []
        for qg, comp, rtype, pid in anchor_genes:
            dom = genes.get(qg, "")
            promisc_flags.append(_is_promiscuous(dom))
            short = (dom.split(";")[0].strip() or rtype or "?")[:22]
            anchor_gene_types.append(f"{qg}:{short}@{pid:.0f}%")
        promiscuous_only = bool(promisc_flags) and all(promisc_flags)
        try:
            med_id = float(cv.get("median_pct_identity") or 0)
        except ValueError:
            med_id = 0.0
        if not med_id and anchor_genes:
            med_id = sorted(h[3] for h in anchor_genes)[len(anchor_genes)//2]

        flags = []
        if n_hit and share < STRONG_FRAC:
            flags.append("MINORITY_ANCHOR")
        if promiscuous_only and n_hit:
            flags.append("PROMISCUOUS_ONLY")
        if shifting:
            flags.append("SHIFTING_BESTHIT")
        if med_id and med_id < STRONG_ID:
            flags.append("LOW_ID")

        if n_hit == 0:
            verdict, honest = "NO_MIBIG_ANCHOR", "no MIBiG per-gene hit; reference-dark / uncharacterised"
        elif "MINORITY_ANCHOR" in flags or "PROMISCUOUS_ONLY" in flags:
            why = []
            if "MINORITY_ANCHOR" in flags:
                why.append(f"{n_hit}/{total} genes")
            if "PROMISCUOUS_ONLY" in flags:
                why.append("promiscuous scaffold only")
            verdict = "FLAGGED_MINORITY"
            honest = (f"weak anchor ({', '.join(why)}; {'/'.join(t for t in anchor_gene_types[:4])}"
                      f" -> {anchor} family SIMILARITY at ~{med_id:.0f}% id); not a product call")
        elif share >= STRONG_FRAC and not promiscuous_only and med_id >= STRONG_ID:
            verdict = "STRONG_FAMILY_ANCHOR"
            honest = (f"family anchor: {n_hit}/{total} genes -> {anchor} family (~{med_id:.0f}% id); "
                      f"class-level capacity, not a product identity")
        else:
            verdict = "PARTIAL_ANCHOR"
            honest = (f"partial anchor ({n_hit}/{total} genes -> {anchor} family, ~{med_id:.0f}% id); "
                      f"class-level, not a product call")

        out.append({
            "strain": strain, "bgc_id": bgc, "products": products.get(bgc, ""),
            "boundary": cv.get("boundary", ""),
            "total_genes": total, "hit_genes": n_hit,
            "query_gene_share": f"{share:.3f}",
            "anchor_compound": anchor,
            "besthit_distribution": "; ".join(f"{c}:{n}" for c, n in comp_counts.most_common()),
            "anchor_gene_types": " | ".join(anchor_gene_types[:6]),
            "promiscuous_only": promiscuous_only,
            "median_pct_identity": f"{med_id:.0f}" if med_id else "",
            "convergence_tier": cv.get("convergence_tier", ""),
            "class_concordance": cv.get("class_concordance", ""),
            "flags": ",".join(flags),
            "verdict": verdict,
            "honest_line": honest,
        })
    return out

FIELDS = ["strain", "bgc_id", "products", "boundary", "total_genes", "hit_genes", "query_gene_share",
          "anchor_compound", "besthit_distribution", "anchor_gene_types", "promiscuous_only",
          "median_pct_identity", "convergence_tier", "class_concordance", "flags", "verdict",
          "honest_line"]

def annotate_convergence(strain: str, outdir: Path | None = None, force: bool = False) -> Path | None:
    """Write a NON-DESTRUCTIVE annotated sibling of <strain>_3_mibig_convergence.csv with two extra
    columns joined from the whole-BGC majority read: `promiscuous_anchor_only` and
    `majority_read_flag` (STRONG/PARTIAL/FLAGGED_MINORITY/NONE). The sealed convergence file is never
    modified. This is the reader-side form of the proposed engine convergence annotation."""
    conv_path = _pkg(strain) / f"{strain}_3_mibig_convergence.csv"
    if not conv_path.is_file():
        return None
    recs = {r["bgc_id"]: r for r in analyze_strain(strain)}
    verdict_short = {"STRONG_FAMILY_ANCHOR": "STRONG", "PARTIAL_ANCHOR": "PARTIAL",
                     "FLAGGED_MINORITY": "FLAGGED_MINORITY", "NO_MIBIG_ANCHOR": "NONE"}
    rows = _read_csv(conv_path)
    if not rows:
        return None
    out_fields = list(rows[0].keys()) + ["promiscuous_anchor_only", "majority_read_flag"]
    outdir = outdir or conv_path.parent
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / f"{strain}_3_mibig_convergence_annotated.csv"
    # v9.7.415: the annotated CSV is a non-destructive SIBLING of the source, but a second run
    # replaces its own prior output in place; guard that too. force is threaded from the caller.
    guard_canonical_write(out_path, force=force)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=out_fields)
        w.writeheader()
        for r in rows:
            rec = recs.get(r.get("bgc_id", ""))
            r = dict(r)
            r["promiscuous_anchor_only"] = str(rec["promiscuous_only"]).lower() if rec else ""
            r["majority_read_flag"] = verdict_short.get(rec["verdict"], "") if rec else ""
            w.writerow(r)
    return out_path


def print_bgc(rec: dict) -> None:
    emit(f"\n=== {rec['strain']} {rec['bgc_id']}  ({rec['products']}) ===")
    emit(f"  genes with a MIBiG hit : {rec['hit_genes']} / {rec['total_genes']}  "
          f"(share {rec['query_gene_share']})")
    emit(f"  anchor compound        : {rec['anchor_compound']}  "
          f"[tier {rec['convergence_tier']}, concordance {rec['class_concordance']}]")
    emit(f"  best-hit distribution  : {rec['besthit_distribution'] or '(none)'}", f"  anchor-supporting genes: {rec['anchor_gene_types'] or '(none)'}", f"  promiscuous-only       : {rec['promiscuous_only']}   median id: {rec['median_pct_identity']}%", f"  FLAGS                  : {rec['flags'] or '(none)'}", f"  VERDICT                : {rec['verdict']}", f"  honest read            : {rec['honest_line']}", sep="\n")

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strain")
    ap.add_argument("--bgc")
    ap.add_argument("--cohort", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--force", "--in-place", dest="force", action="store_true",
                    help="allow overwriting an existing canonical dated deliverable")
    ap.add_argument("--annotate-convergence", action="store_true",
                    help="write NON-DESTRUCTIVE annotated sibling(s) of _3_mibig_convergence.csv "
                         "(+promiscuous_anchor_only, +majority_read_flag)")
    a = ap.parse_args()

    if a.annotate_convergence:
        outdir = Path(a.out) if a.out else None
        if a.cohort:
            strains = sorted(p.name for p in RUNS.iterdir()
                             if p.is_dir() and p.name.startswith(("AS-", "AJS-", "SID")) and p.name not in EXCLUDE)
        elif a.strain:
            strains = [a.strain]
        else:
            ap.error("--annotate-convergence needs --strain or --cohort")
        n = 0
        for s in strains:
            if s in EXCLUDE:
                continue
            p = annotate_convergence(s, outdir, force=getattr(a, "force", False))
            if p:
                n += 1
        emit(f"annotated convergence written for {n} strain(s)"
              + (f" -> {outdir}" if outdir else " (as siblings next to each source file)"))
        return 0

    if a.cohort:
        strains = sorted(p.name for p in RUNS.iterdir()
                         if p.is_dir() and p.name.startswith(("AS-", "AJS-", "SID")) and p.name not in EXCLUDE)
        allrecs = []
        for s in strains:
            allrecs += analyze_strain(s)
        outdir = Path(a.out) if a.out else (ROOT / "strain_data" /
                 f"whole_bgc_majority_read_2026-08-05")
        outdir.mkdir(parents=True, exist_ok=True)
        csv_path = outdir / "whole_bgc_majority_read_cohort.csv"
        # v9.7.415: refuse to silently replace an existing canonical dated deliverable. The default
        # outdir is ROOT/strain_data/whole_bgc_majority_read_2026-08-05 -- strain_data is the SYMLINK
        # to the canonical home and that folder matches DATED_DIR_RE, so an exploratory run with no
        # --out overwrote a real deliverable in place. Its two siblings (surface-leads,
        # modeb-compile) were wired at .413; this one, the first prefix named in the guard's own
        # docstring, was missed.
        guard_canonical_write(csv_path, force=getattr(a, "force", False))
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            w = _SafeDictWriter(fh, fieldnames=FIELDS); w.writeheader()
            for r in allrecs:
                w.writerow(r)
        flagged = [r for r in allrecs if r["verdict"] == "FLAGGED_MINORITY"]
        strong = [r for r in allrecs if r["verdict"] == "STRONG_FAMILY_ANCHOR"]
        emit(f"cohort: {len(strains)} strains, {len(allrecs)} BGCs  "
              f"(excluded {sorted(EXCLUDE)})")
        emit(f"  STRONG_FAMILY_ANCHOR : {len(strong)}", f"  PARTIAL_ANCHOR       : {sum(1 for r in allrecs if r['verdict']=='PARTIAL_ANCHOR')}", f"  FLAGGED_MINORITY     : {len(flagged)}  (minority/promiscuous -> must be class-level)", f"  NO_MIBIG_ANCHOR      : {sum(1 for r in allrecs if r['verdict']=='NO_MIBIG_ANCHOR')}", f"  -> {csv_path}", sep="\n")
        return 0

    if not a.strain:
        ap.error("give --strain (optionally --bgc) or --cohort")
    if a.strain in EXCLUDE:
        emit(f"{a.strain} is in the raw-analysis exclusion set {sorted(EXCLUDE)} — skipped.")
        return 0
    recs = analyze_strain(a.strain)
    if a.bgc:
        recs = [r for r in recs if r["bgc_id"] == a.bgc]
        if not recs:
            emit(f"no BGC {a.bgc} in {a.strain}"); return 1
    for r in recs:
        print_bgc(r)
    return 0

if __name__ == "__main__":
    sys.exit(main())

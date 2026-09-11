#!/usr/bin/env python3
"""realistic_bgc_count.py — distinct-loci BGC count (advisory report).

antiSMASH's raw region count over-states the number of *distinct biosynthetic clusters* two
ways: (1) it emits regions with no real biosynthetic machinery (context-only fragments), and
(2) it splits one biological pathway across two contigs (counted twice). This tool computes a
grounded count that counts each real cluster ONCE, entirely from a sealed Mamey package.

TWO DIFFERENT CORRECTED DENOMINATORS EXIST — they measure different things; DO NOT compare them
as if interchangeable (v9.7.409, audit AUDIT_scoring_tiers.md F2 / handle
``realistic_count_two_denominators``):

  * DISTINCT-LOCI count (this tool's ``Realistic_count``): drop context-only/junk regions, then
    merge HIGH-confidence RG-GMCI split-pathway pairs. An *integer* count of distinct biosynthetic
    loci. It ignores boundary/fragmentation.
  * BOUNDARY-WEIGHTED corrected count (``Corrected_count_bw`` here; the SSOT number used in every
    figure, the cohort HTML, the cross-strain workbook, and ``docs/EXTERNAL_VALIDATION.md``):
    ``Interior*1 + Edge*1/2 + Full-contig*1/4`` over ALL regions. A *fractional* fragmentation
    discount. Canonical constant: ``tools/build_cohort_html.py:BOUNDARY_WEIGHT`` (kept in sync
    here as ``BOUNDARY_WEIGHT``; ``tests/test_realistic_bgc_count.py`` asserts the two are equal).

For one strain these two answers differ (e.g. RB68: 53 distinct-loci vs 59.5 boundary-weighted) —
that is expected: a fragmentation discount is not a loci merge. This tool now emits BOTH side by
side so neither is mistaken for "the" corrected count. ``build_cohort_html.py`` produces only the
boundary-weighted number; see its header cross-reference.

  raw_regions        = antiSMASH regions in the package (one per BGC row)
  REAL               = a region with genuine biosynthetic machinery OR a recognised class:
                         (n_core + n_tailoring + n_resistance) >= 1  OR
                         antiSMASH gave it a named biosynthetic class (not bare other/saccharide)
  marginal_dropped   = context-only regions (no machinery, no recognised class) — not counted
  merged_away        = REAL regions collapsed because a HIGH-confidence RG-GMCI split-pathway
                       pair links them (one biological BGC across two contigs)
  realistic_count    = DISTINCT-LOCI: connected components of REAL regions after HIGH RG-GMCI merge
  corrected_count_bw = BOUNDARY-WEIGHTED corrected count over ALL regions (Rule A; matches
                       build_cohort_html.py) — a different, fractional denominator

Role counts come from the banked ``*_gene_by_gene_all_bgcs.csv`` ``gene_function_inference``
column; the merge uses ``*_4A_RGGMCI_ranked_pairs.csv`` rows whose confidence contains HIGH.

CLAIM SAFETY (mandatory): these are class-level counts of annotation *roles*, boundary status,
and homology-guided linkage — NOT a product, activity, or nucleotide-level joining claim. Both
denominators are class-level; neither asserts a compound. The raw count is not "wrong" (it counts
regions); one column counts distinct biosynthetic loci, the other applies a fragmentation
discount. RG-GMCI merge is homology-guided shared-reference linkage, not contig joining. Advisory
/ reporting only — ranks nothing, moves no tier. Fragment (Edge/short) regions are surfaced, never
silently excluded: a fragment with biosynthetic machinery still counts as REAL.

Usage:
  python tools/realistic_bgc_count.py --package runs/AS-XXX/package
  python tools/realistic_bgc_count.py --package pkgA --package pkgB --out /tmp/rc
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import glob
import json
import os
import sys

# gene_function_inference tokens -> the three machinery buckets
_CORE = {"core biosynthetic"}
_TAILORING = {"tailoring / modification", "glycosylation / sugar", "chain release / TE",
              "maturation / proteolysis"}
_RESISTANCE = {"self-resistance / export"}

# antiSMASH class strings that carry no biosynthetic substance on their own
_JUNK_CLASS = {"", "other", "saccharide", "cf_putative", "cf_saccharide"}

# v9.7.409 (audit F2 / realistic_count_two_denominators): the boundary-weighted "corrected count"
# (Rule A) is the SSOT denominator surfaced in figures / cohort HTML / EXTERNAL_VALIDATION. It is a
# DIFFERENT metric from Realistic_count (distinct-loci merge) and is emitted here alongside it so a
# reader never mistakes one for the other. This table MUST stay byte-equal to
# tools/build_cohort_html.py:BOUNDARY_WEIGHT — tests/test_realistic_bgc_count.py asserts equality.
BOUNDARY_WEIGHT = {"Interior": 1.0, "Edge": 0.5, "Full-contig": 0.25}


def _find_one(package_dir: str, suffix: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(package_dir, f"*{suffix}")))
    return hits[0] if hits else None


def _read_regions(package_dir: str) -> dict[str, dict]:
    """BGC_ID -> {products, length_kb, boundary} from the inventory."""
    inv = _find_one(package_dir, "_2_inventory.csv")
    regions: dict[str, dict] = {}
    if not inv:
        return regions
    with open(inv, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            bid = (r.get("BGC_ID") or "").strip()
            if not bid:
                continue
            try:
                lkb = float(r.get("Length_kb") or 0)
            except ValueError:
                lkb = 0.0
            regions[bid] = {"products": r.get("Products", ""), "length_kb": lkb,
                            "boundary": r.get("Boundary", "")}
    return regions


def _role_counts(package_dir: str) -> dict[str, dict]:
    """BGC_ID -> {n_core, n_tailoring, n_resistance} from gene_function_inference."""
    gbg = _find_one(package_dir, "_gene_by_gene_all_bgcs.csv")
    counts: dict[str, dict] = {}
    if not gbg:
        return counts
    with open(gbg, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            bid = (r.get("bgc_id") or "").strip()
            if not bid:
                continue
            c = counts.setdefault(bid, {"n_core": 0, "n_tailoring": 0, "n_resistance": 0})
            role = (r.get("gene_function_inference") or "").strip()
            rtier = (r.get("resistance_tier") or "")
            if role in _CORE:
                c["n_core"] += 1
            elif role in _TAILORING:
                c["n_tailoring"] += 1
            elif role in _RESISTANCE or rtier.startswith(("T1", "T2")):
                c["n_resistance"] += 1
    return counts


def _high_rggmci_pairs(package_dir: str) -> list[tuple[str, str]]:
    rp = _find_one(package_dir, "_4A_RGGMCI_ranked_pairs.csv")
    pairs: list[tuple[str, str]] = []
    if not rp:
        return pairs
    with open(rp, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            conf = (r.get("rggmci_confidence") or "").upper()
            if "HIGH" not in conf:
                continue
            a, b = (r.get("bgc_a") or "").strip(), (r.get("bgc_b") or "").strip()
            if a and b:
                pairs.append((a, b))
    return pairs


class _UF:
    def __init__(self, items):
        self.p = {x: x for x in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        if a in self.p and b in self.p:
            self.p[self.find(a)] = self.find(b)


def _strain_of(package_dir: str) -> str:
    mp = _find_one(package_dir, "manifest.json")
    if mp:
        try:
            m = json.load(open(mp, encoding="utf-8"))
            for k in ("strain_id", "strain", "Strain"):
                if m.get(k):
                    return str(m[k])
        except (ValueError, OSError):
            pass
    inv = _find_one(package_dir, "_2_inventory.csv")
    if inv:
        base = os.path.basename(inv)
        return base.split("_2_inventory.csv")[0]
    return os.path.basename(os.path.normpath(package_dir))


def _is_real(products: str, rc: dict) -> bool:
    has_machinery = (rc.get("n_core", 0) + rc.get("n_tailoring", 0) + rc.get("n_resistance", 0)) >= 1
    # v9.7.374 fix: Products is a ";"-delimited multi-value field (e.g. "other; saccharide",
    # "fatty_acid; other") -- the whole-string membership test below only ever matched
    # _JUNK_CLASS on a SINGLE-token label. A region whose antiSMASH class is a compound of
    # two-or-more junk-only tokens (e.g. "other; saccharide") never equals any single entry
    # in _JUNK_CLASS, so `recognised` was True even with zero core/tailoring/resistance genes --
    # live-reproduced against this tool's own _is_real(): _is_real("other; saccharide", {}) was
    # True (should be False, no machinery + no real class). Confirmed present in real sealed
    # output: runs/AS-XXX/package/AS-XXX_2_inventory.csv BGC048 carries exactly this label.
    # Splitting on ";" and requiring at least one non-junk token restores the tool's own stated
    # contract ("REAL = ... OR antiSMASH gave it a named biosynthetic class, not bare
    # other/saccharide") for compound labels, while leaving every single-token and mixed
    # real+junk case (e.g. "nrps; other") unchanged.
    toks = [t.strip().lower() for t in (products or "").split(";")]
    recognised = any(t and t not in _JUNK_CLASS for t in toks)
    return has_machinery or recognised


def score_package(package_dir: str) -> dict:
    regions = _read_regions(package_dir)
    roles = _role_counts(package_dir)
    raw = len(regions)
    real_ids = {bid for bid, meta in regions.items()
                if _is_real(meta["products"], roles.get(bid, {}))}
    marginal = raw - len(real_ids)
    uf = _UF(real_ids)
    merges = 0
    for a, b in _high_rggmci_pairs(package_dir):
        if a in real_ids and b in real_ids and uf.find(a) != uf.find(b):
            uf.union(a, b)
            merges += 1
    components = len({uf.find(x) for x in real_ids})
    merged_away = len(real_ids) - components
    # Rule A — boundary-weighted corrected count over ALL regions (same formula & constant as
    # build_cohort_html.py). A DIFFERENT denominator from Realistic_count; emitted side by side so
    # the 59.5-vs-53 gap is explicit, never a surprise (audit F2). Rows whose Boundary is not one of
    # Interior/Edge/Full-contig contribute 0.0, matching build_cohort_html's `counts` filter.
    corrected_bw = round(
        sum(BOUNDARY_WEIGHT.get(meta.get("boundary", ""), 0.0) for meta in regions.values()), 2)
    return {
        "Strain": _strain_of(package_dir), "Raw_regions": raw, "Realistic_count": components,
        "Corrected_count_bw": corrected_bw,
        "Merged_away": merged_away, "Marginal_dropped": marginal,
        "Inflation_pct": round(100 * (raw - components) / max(raw, 1)),
        "n_high_rggmci_merges": merges,
    }


FIELDS = ["Strain", "Raw_regions", "Realistic_count", "Corrected_count_bw", "Merged_away",
          "Marginal_dropped", "Inflation_pct", "n_high_rggmci_merges"]


def _reader_out_dir(out, package_dir, suffix):
    """v9.7.409 (AUDIT_cli_code_bugs #5): a read-only reader must never write INSIDE the package
    it reads — an untracked file there makes `mamey validate` fail checksum_integrity. Default
    output to a SIBLING dir OUTSIDE the package; refuse an explicit --out that resolves inside it
    (mirrors mamey/activity_predictions.resolve_output_dir). Raises ValueError on an inside path."""
    pkg = os.path.abspath(package_dir)
    target = os.path.abspath(out) if out else os.path.join(
        os.path.dirname(pkg), os.path.basename(pkg) + suffix)
    if target == pkg or (target + os.sep).startswith(pkg + os.sep):
        raise ValueError(f"reader output must be OUTSIDE the sealed package ({pkg}); "
                         f"pass --out <a directory outside the package>")
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Realistic (corrected-denominator) BGC count — advisory report")
    ap.add_argument("--package", action="append", required=True,
                    help="sealed Mamey package directory (repeatable)")
    ap.add_argument("--out", default=None, help="output dir (default: first package dir)")
    a = ap.parse_args(argv)
    for pkg in a.package:
        if not os.path.isdir(pkg):
            ap.error(f"not a directory: {pkg}")
    rows = [score_package(p) for p in a.package]
    rows.sort(key=lambda r: -r["Inflation_pct"])
    try:
        out_dir = _reader_out_dir(a.out, a.package[0], "_realistic_count")
    except ValueError as _e:
        ap.error(str(_e))
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "realistic_bgc_count.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    tot_raw = sum(r["Raw_regions"] for r in rows)
    tot_real = sum(r["Realistic_count"] for r in rows)
    tot_bw = round(sum(r["Corrected_count_bw"] for r in rows), 2)
    summary = {
        "n_packages": len(rows), "total_raw_regions": tot_raw, "total_realistic_count": tot_real,
        "total_corrected_count_bw": tot_bw,
        "cohort_inflation_pct": round(100 * (tot_raw - tot_real) / max(tot_raw, 1)),
        "denominator_note": ("TWO different corrected denominators, not interchangeable: "
                             "Realistic_count = distinct biosynthetic loci (drop junk + HIGH RG-GMCI "
                             "merge, integer); Corrected_count_bw = boundary-weighted fragmentation "
                             "discount over all regions (Interior*1 + Edge*1/2 + Full-contig*1/4, "
                             "fractional; the SSOT number in figures / cohort HTML / "
                             "EXTERNAL_VALIDATION). They may differ for one strain by design."),
        "claim_safety": ("Class-level counts of annotation roles, boundary status + homology-guided "
                         "RG-GMCI linkage. Not a product/activity claim; not nucleotide-level contig "
                         "joining. Advisory."),
    }
    with open(os.path.join(out_dir, "realistic_bgc_count_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    emit(f"{len(rows)} package(s) · raw {tot_raw} -> distinct-loci {tot_real} "
          f"(-{summary['cohort_inflation_pct']}% overall) · boundary-weighted corrected {tot_bw} "
          f"(different denominator) -> {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

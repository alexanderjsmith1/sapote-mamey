#!/usr/bin/env python3
"""build_novelty_shortlist.py — composite (multi-signal) novelty shortlist (advisory report).

The engine already carries several *independent* novelty signals but no single view that
intersects them. This tool composites them into one ranked candidate table, read entirely
from sealed Mamey package(s):

  (a) KCB-dark            — inventory KCB_top is empty (no KnownClusterBlast/MIBiG anchor)
  (b) low recognizability — best per-gene MIBiG recognizable_gene_share is low (or no
                            convergence row at all): the locus is dark *per gene*, not just
                            at the whole-cluster level
  (c) RG-GMCI linkage     — the region participates in an RG-GMCI split-pathway pair
                            (surfaced as a distinctiveness signal, never used to merge here)
  (d) cohort-unique domain— (multi-package runs) carries a biosynthetic domain seen in only
                            one package of the set

Fragments (<10 kb) are FLAGGED and down-weighted, never excluded — the fragment-surfacing
principle: a tiny orphan core still appears, it just doesn't top the list on novelty alone.

CLAIM SAFETY (mandatory): every signal is a novelty *prior*, not proof of a new compound or of
any activity. KCB/MIBiG absence = "no similar reference cluster indexed", not "novel chemistry".
Recognizability is a per-gene homology share, not function. This is an advisory shortlist
(a report of priors); it ranks candidates for human attention and moves no published tier.

Usage:
  python tools/build_novelty_shortlist.py --package runs/AS-XXX/package
  python tools/build_novelty_shortlist.py --package pkgA --package pkgB --out /tmp/nov
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
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open

from mamey.domain_reference import BIOSYNTHETIC_CATEGORIES, categorize

FRAGMENT_KB = 10.0
LOW_RECOG = 0.25  # best recognizable_gene_share below this = per-gene dark


def _find_one(package_dir: str, suffix: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(package_dir, f"*{suffix}")))
    return hits[0] if hits else None


def _strain_of(package_dir: str) -> str:
    inv = _find_one(package_dir, "_2_inventory.csv")
    if inv:
        return os.path.basename(inv).split("_2_inventory.csv")[0]
    return os.path.basename(os.path.normpath(package_dir))


def _inventory(package_dir: str) -> dict[str, dict]:
    inv = _find_one(package_dir, "_2_inventory.csv")
    out: dict[str, dict] = {}
    if not inv:
        return out
    with open(inv, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            bid = (r.get("BGC_ID") or "").strip()
            if bid:
                out[bid] = r
    return out


def _triage(package_dir: str) -> dict[str, dict]:
    t = _find_one(package_dir, "_4_triage_board.csv")
    out: dict[str, dict] = {}
    if not t:
        return out
    with open(t, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            bid = (r.get("BGC_ID") or "").strip()
            if bid:
                out[bid] = r
    return out


def _best_recognizability(package_dir: str) -> dict[str, float]:
    c = _find_one(package_dir, "_3_mibig_convergence.csv")
    best: dict[str, float] = {}
    if not c:
        return best
    with open(c, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            bid = (r.get("bgc_id") or "").strip()
            if not bid:
                continue
            try:
                v = float(r.get("recognizable_gene_share") or 0)
            except ValueError:
                v = 0.0
            best[bid] = max(best.get(bid, 0.0), v)
    return best


def _biosyn_domains_by_pkg(package_dir: str) -> dict[str, set]:
    """BGC_ID -> set(biosynthetic domain names) for this package."""
    d = _find_one(package_dir, "_domains.csv")
    out: dict[str, set] = defaultdict(set)
    if not d:
        return out
    with open(d, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            dom = (r.get("domain") or "").strip()
            bid = (r.get("bgc_id") or "").strip()
            if not dom or not bid:
                continue
            cat, _ = categorize(dom)
            if cat in BIOSYNTHETIC_CATEGORIES:
                out[bid].add(dom)
    return out


def build(package_dirs: list[str]) -> list[dict]:
    # cohort-unique biosynthetic domains: domain -> set(packages carrying it)
    dom_pkgs: dict[str, set] = defaultdict(set)
    pkg_domains: dict[str, dict[str, set]] = {}
    for pkg in package_dirs:
        bd = _biosyn_domains_by_pkg(pkg)
        pkg_domains[pkg] = bd
        for bid, doms in bd.items():
            for dom in doms:
                dom_pkgs[dom].add(pkg)
    unique_domains = {dom for dom, pk in dom_pkgs.items() if len(pk) == 1} if len(package_dirs) > 1 else set()

    rows = []
    for pkg in package_dirs:
        strain = _strain_of(pkg)
        inv = _inventory(pkg)
        tri = _triage(pkg)
        recog = _best_recognizability(pkg)
        bd = pkg_domains[pkg]
        for bid, ir in inv.items():
            tr = tri.get(bid, {})
            no_kcb = not (ir.get("KCB_top") or "").strip()
            best_recog = recog.get(bid)
            low_recog = (best_recog is None) or (best_recog < LOW_RECOG)
            rggmci = bool((tr.get("RGGMCI_support") or "").strip())
            rare = sorted(d for d in bd.get(bid, set()) if d in unique_domains)
            try:
                lkb = float(ir.get("Length_kb") or 0)
            except ValueError:
                lkb = 0.0
            fragment = 0 < lkb < FRAGMENT_KB
            try:
                novelty = float(tr.get("Novelty_auto") or 0)
            except ValueError:
                novelty = 0.0
            score = (2.0 * no_kcb + 1.5 * low_recog + 1.0 * rggmci + min(len(rare), 3)
                     + novelty / 25.0 - (1.0 if fragment else 0.0))
            rows.append({
                "strain": strain, "bgc_id": bid, "products": ir.get("Products", ""),
                "length_kb": round(lkb, 1), "novelty_prior": novelty,
                "lead_tier": tr.get("Lead_tier_auto", ""),
                "kcb_dark": int(no_kcb),
                "best_recognizable_gene_share": ("" if best_recog is None else round(best_recog, 3)),
                "low_recognizability": int(low_recog),
                "rggmci_linked": int(rggmci),
                "n_cohort_unique_domains": len(rare),
                "cohort_unique_domains": ";".join(rare)[:100],
                "fragment_surfaced": int(fragment),
                "novelty_score": round(score, 2),
            })
    rows.sort(key=lambda r: -r["novelty_score"])
    return rows


FIELDS = ["rank", "strain", "bgc_id", "products", "length_kb", "novelty_prior", "lead_tier",
          "kcb_dark", "best_recognizable_gene_share", "low_recognizability", "rggmci_linked",
          "n_cohort_unique_domains", "cohort_unique_domains", "fragment_surfaced", "novelty_score"]


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
    ap = argparse.ArgumentParser(description="Composite multi-signal novelty shortlist — advisory report")
    ap.add_argument("--package", action="append", required=True,
                    help="sealed Mamey package directory (repeatable; >1 enables cohort-unique-domain signal)")
    ap.add_argument("--out", default=None, help="output dir (default: first package dir)")
    ap.add_argument("--top", type=int, default=30, help="rows in the .md preview (default 30)")
    a = ap.parse_args(argv)
    for pkg in a.package:
        if not os.path.isdir(pkg):
            ap.error(f"not a directory: {pkg}")
    rows = build(a.package)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    try:
        out_dir = _reader_out_dir(a.out, a.package[0], "_novelty_shortlist")
    except ValueError as _e:
        ap.error(str(_e))
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "novelty_shortlist.csv")
    with atomic_open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with atomic_open(os.path.join(out_dir, "novelty_shortlist.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Novelty shortlist — {len(rows)} BGCs across {len(a.package)} package(s)\n\n")
        fh.write("Ranked by a composite of independent novelty **priors**: KCB/MIBiG-dark, low "
                 "per-gene recognizability, RG-GMCI split-pathway linkage, cohort-unique "
                 "biosynthetic domains (fragments <10 kb surfaced but down-weighted). "
                 "**All signals are priors, not proof of new chemistry or any activity.**\n\n")
        fh.write("| # | strain · BGC | class | kb | score | KCB-dark | low-recog | RG-GMCI | frag |\n")
        fh.write("|---:|---|---|---:|---:|:---:|:---:|:---:|:---:|\n")
        for r in rows[:a.top]:
            fh.write(f"| {r['rank']} | {r['strain']} · {r['bgc_id']} | "
                     f"{(r['products'] or '—')[:22]} | {r['length_kb']} | {r['novelty_score']} | "
                     f"{'✓' if r['kcb_dark'] else ''} | {'✓' if r['low_recognizability'] else ''} | "
                     f"{'✓' if r['rggmci_linked'] else ''} | {'✓' if r['fragment_surfaced'] else ''} |\n")
    top = rows[0] if rows else None
    emit(f"{len(rows)} BGCs scored -> {csv_path}"
          + (f"; top: {top['strain']} {top['bgc_id']} ({top['novelty_score']})" if top else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

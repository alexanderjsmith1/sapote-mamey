#!/usr/bin/env python3
"""rggmci_cohort_rollup.py — cross-strain RG-GMCI ranked rollup + confidence tiering (v9.7.117).

THE GAP THIS FILLS
------------------
The engine computes full per-strain RG-GMCI during `run` (each package ships
<SID>_4A_RGGMCI_ranked_pairs.csv with the subject-tiling verdict, terminus-truncation rescue, and
hub-degree guards — all correct). `build_reconstruction.py` reconstructs splits per strain. What was
missing is a CROSS-STRAIN aggregator that pools every strain's ranked pairs and ranks the whole
cohort's rescues by GENUINENESS, not raw score.

Why genuineness, not score: raw-score ranking puts an OVERLAPPING_PARALOG pair (shared machinery,
not a split) at the top. The subject-tiling verdict is the real signal —
  * COMPLEMENTARY_SPLIT          → genuine (two arms of one cluster, disjoint reference tiling)
  * TERMINUS_TRUNCATION_SPLIT    → genuine (severed-arm rescue at a contig terminus)
  * OVERLAPPING_PARALOG          → EXCLUDED (shared paralogous machinery, not a split)
  * MIXED_SUBJECT_SIGNAL         → manual-review queue
  * INSUFFICIENT_SUBJECT_DATA    → not rankable (no subject tiling to judge)
plus terminus_override_note promotions (severed_arm / CORROBORATED_terminus_truncation).

On top of the genuineness rank, a confidence tier (CONFIRMABLE / LIKELY / NEEDS-REVIEW) driven by
disjoint-ref count, shared-subject count, the DISTANT_ON_REFERENCE caution, and core-fraction —
because most tiling-genuine splits still carry homology cautions and that must be surfaced honestly.

CLAIM-SAFETY
------------
RG-GMCI is homology-guided shared-reference linkage, NOT nucleotide-level contig joining. The rollup
carries each pair's interpretation_guard through and never asserts a physical join. Capacity-level.

OUTPUT
------
A genuineness-ranked rescue board (markdown) + a sign-off-ready evidence CSV (per-pair: verdict,
confidence tier, disjoint/shared subject tally, core fractions, contig/node refs per fragment).

USAGE
-----
    python tools/rggmci_cohort_rollup.py --packages <dir> --out-prefix <path>
The packages dir is scanned for */*_4A_RGGMCI_ranked_pairs.csv (one per strain).
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
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open, atomic_write_text

# subject-tiling verdicts that are genuine splits (ranked), excluded, or review-queued.
_GENUINE = {"COMPLEMENTARY_SPLIT", "TERMINUS_TRUNCATION_SPLIT"}
_EXCLUDED = {"OVERLAPPING_PARALOG"}
_REVIEW = {"MIXED_SUBJECT_SIGNAL"}
# verdict rank for ordering (genuine first, then review, then the rest)
_VERDICT_RANK = {
    "COMPLEMENTARY_SPLIT": 0,
    "TERMINUS_TRUNCATION_SPLIT": 1,
    "MIXED_SUBJECT_SIGNAL": 2,
    "INSUFFICIENT_SUBJECT_DATA": 3,
    "OVERLAPPING_PARALOG": 4,
}

# terminus_override_note values that PROMOTE an otherwise-insufficient/mixed pair to genuine.
_PROMOTING_NOTES = ("severed_arm", "CORROBORATED_terminus_truncation")


def _is_high(conf: str) -> bool:
    """A HIGH RG-GMCI pair (the cohort 'HIGH' set the spec's counts are over).

    Anchored on the engine's actual HIGH confidence token, which is the prefix 'HIGH_RG_GMCI' (the
    full value is 'HIGH_RG_GMCI_RESCUE'). Prefix-anchoring avoids the substring-containment bug class:
    a bare `'HIGH' in conf` would false-match 'NOT_HIGH_CONFIDENCE' / 'HIGHLY_UNCERTAIN', and a naive
    token match can't tell negation from assertion. Matching the real emitted prefix is unambiguous.
    The legacy bare 'HIGH' confidence (older packages) is also accepted via exact match.
    """
    c = (conf or "").upper().strip()
    return c.startswith("HIGH_RG_GMCI") or c == "HIGH"


def _to_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def effective_verdict(row: dict) -> str:
    """The subject-tiling verdict, with terminus_override_note promotions applied.

    A pair tagged INSUFFICIENT_SUBJECT_DATA or MIXED_SUBJECT_SIGNAL but carrying a severed-arm /
    corroborated terminus override is promoted to TERMINUS_TRUNCATION_SPLIT (genuine), matching the
    engine's own terminus-rescue semantics.
    """
    verdict = (row.get("subject_tiling_verdict") or "").strip()
    note = (row.get("terminus_override_note") or "").strip()
    if note and any(p in note for p in _PROMOTING_NOTES):
        if verdict not in _GENUINE:
            return "TERMINUS_TRUNCATION_SPLIT"
    return verdict or "INSUFFICIENT_SUBJECT_DATA"


def confidence_tier(row: dict) -> str:
    """CONFIRMABLE / LIKELY / NEEDS-REVIEW for a genuine split.

    Driven by: disjoint-ref count (independent reference support for the two arms), shared-subject
    count (overlap that weakens the split call), the DISTANT_ON_REFERENCE caution, and core fraction
    (both arms carrying core machinery strengthens the call). Deliberately conservative — most
    tiling-genuine splits still carry homology cautions and land in LIKELY/REVIEW, not CONFIRMABLE.
    """
    disjoint = _to_int(row.get("complementary_disjoint_refs"))
    shared = _to_int(row.get("n_shared_subjects"))
    guard = (row.get("interpretation_guard") or "").upper()
    a_core = _to_float(row.get("a_core_fraction"))
    b_core = _to_float(row.get("b_core_fraction"))
    distant = "DISTANT" in guard

    # CONFIRMABLE: strong independent disjoint support, little shared overlap, no distance caution,
    # and both arms carry meaningful core machinery.
    if disjoint >= 3 and shared <= 2 and not distant and min(a_core, b_core) >= 0.15:
        return "CONFIRMABLE"
    # NEEDS-REVIEW: weak disjoint support, heavy shared overlap, or a distance caution.
    if disjoint <= 1 or shared >= 5 or distant:
        return "NEEDS-REVIEW"
    return "LIKELY"


def load_ranked_pairs(packages_dir: str | Path) -> list[dict]:
    """Pool every strain's ranked_pairs CSV. Each row is tagged with its strain (from the filename).

    v9.7.117 (Bug Hunt): the recursive glob would DOUBLE-COUNT a strain that has a stale copy of its
    ranked_pairs in a nested subdir (e.g. a `_savework/` or backup folder — a real layout in this
    project). Double-counting silently inflates every cohort total. Fix: keep at most ONE file per
    strain ID, preferring the shallowest path (the live package, not a nested backup), and explicitly
    skipping backup/scratch dirs.
    """
    _SKIP_DIRS = ("_savework", "_backup", "backup", ".bak", "_archive", "_old", "scratch")
    pat = os.path.join(str(packages_dir), "**", "*_4A_RGGMCI_ranked_pairs.csv")
    # collect candidates per strain, with their path depth (for shallowest-wins)
    by_strain: dict[str, str] = {}
    for fp in sorted(glob.glob(pat, recursive=True)):
        parts = Path(fp).parts
        if any(seg in _SKIP_DIRS for seg in parts):
            continue
        sid = os.path.basename(fp).split("_4A_RGGMCI_ranked_pairs.csv")[0]
        depth = len(parts)
        prev = by_strain.get(sid)
        if prev is None or depth < len(Path(prev).parts):
            by_strain[sid] = fp
    pooled = []
    for sid, fp in sorted(by_strain.items()):
        try:
            with open(fp, newline="") as fh:
                for r in csv.DictReader(fh):
                    r["_strain"] = sid
                    pooled.append(r)
        except (OSError, csv.Error):
            continue
    return pooled


def rollup(packages_dir: str | Path) -> dict:
    """Pool, filter to HIGH, classify by genuineness, tier by confidence. Returns a summary dict."""
    pooled = load_ranked_pairs(packages_dir)
    high = [r for r in pooled if _is_high(r.get("rggmci_confidence"))]

    genuine, excluded, review = [], [], []
    for r in high:
        v = effective_verdict(r)
        if v in _GENUINE:
            r["_effective_verdict"] = v
            r["_confidence_tier"] = confidence_tier(r)
            genuine.append(r)
        elif v in _EXCLUDED:
            excluded.append(r)
        elif v in _REVIEW:
            review.append(r)
        # INSUFFICIENT_SUBJECT_DATA: neither genuine nor excluded nor review — not rankable

    # rank genuine by (verdict rank, confidence tier, score desc)
    _tier_rank = {"CONFIRMABLE": 0, "LIKELY": 1, "NEEDS-REVIEW": 2}
    genuine.sort(key=lambda r: (_VERDICT_RANK.get(r["_effective_verdict"], 9),
                                _tier_rank.get(r["_confidence_tier"], 9),
                                -_to_float(r.get("rggmci_score"))))

    comp = sum(1 for r in genuine if r["_effective_verdict"] == "COMPLEMENTARY_SPLIT")
    term = sum(1 for r in genuine if r["_effective_verdict"] == "TERMINUS_TRUNCATION_SPLIT")
    tiers = Counter(r["_confidence_tier"] for r in genuine)

    return {
        "n_pooled": len(pooled),
        "n_high": len(high),
        "n_genuine": len(genuine),
        "n_complementary": comp,
        "n_terminus": term,
        "n_excluded_paralog": len(excluded),
        "n_review": len(review),
        "tiers": dict(tiers),
        "genuine": genuine,
        "review": review,
    }


def write_board(summary: dict, out_prefix: str) -> tuple[str, str]:
    """Emit the genuineness-ranked board (md) + the sign-off evidence table (csv)."""
    md = []
    md.append("# RG-GMCI cohort rescue board (genuineness-ranked)")
    md.append("")
    md.append(f"Pooled {summary['n_pooled']} ranked pairs across the cohort; {summary['n_high']} HIGH. "
              f"Ranked by subject-tiling verdict (genuineness), not raw score.")
    md.append("")
    md.append(f"**{summary['n_genuine']} genuine splits** = {summary['n_complementary']} complementary "
              f"+ {summary['n_terminus']} terminus. "
              f"{summary['n_excluded_paralog']} overlapping-paralog excluded (shared machinery, not a "
              f"split). {summary['n_review']} mixed → manual-review queue.")
    md.append("")
    t = summary["tiers"]
    md.append(f"Confidence tiering of the genuine splits: {t.get('CONFIRMABLE',0)} CONFIRMABLE / "
              f"{t.get('LIKELY',0)} LIKELY / {t.get('NEEDS-REVIEW',0)} NEEDS-REVIEW. "
              f"(Most tiling-genuine splits still carry homology cautions — this is honest, not a "
              f"defect.)")
    md.append("")
    md.append("RG-GMCI is homology-guided shared-reference linkage, not nucleotide-level contig "
              "joining. Each pair below is a capacity-level reconstruction hypothesis cited with "
              "contig/node, never an asserted physical join.")
    md.append("")
    md.append("## Genuine splits (ranked)")
    md.append("")
    for i, r in enumerate(summary["genuine"], 1):
        v = "complementary" if r["_effective_verdict"] == "COMPLEMENTARY_SPLIT" else "terminus"
        md.append(f"{i}. **{r['_strain']} {r.get('pair','')}** — {v} split, {r['_confidence_tier']} "
                  f"(score {r.get('rggmci_score','')}, disjoint-refs "
                  f"{r.get('complementary_disjoint_refs','?')}, shared-subjects "
                  f"{r.get('n_shared_subjects','?')})")
        md.append(f"   - {r.get('bgc_a','')} [{r.get('contig_a','')}] {r.get('products_a','')} "
                  f"({r.get('edge_a','')})")
        md.append(f"   - {r.get('bgc_b','')} [{r.get('contig_b','')}] {r.get('products_b','')} "
                  f"({r.get('edge_b','')})")
    md_text = "\n".join(md) + "\n"

    # evidence CSV
    cols = ["rank", "strain", "pair", "verdict", "confidence_tier", "rggmci_score",
            "complementary_disjoint_refs", "n_shared_subjects", "a_core_fraction", "b_core_fraction",
            "bgc_a", "contig_a", "products_a", "edge_a",
            "bgc_b", "contig_b", "products_b", "edge_b", "interpretation_guard"]
    _parent = os.path.dirname(out_prefix)
    if _parent:
        os.makedirs(_parent, exist_ok=True)
    csv_path = out_prefix + "_evidence.csv"
    with atomic_open(csv_path, newline="") as fh:
        w = _SafeWriter(fh)
        w.writerow(cols)
        for i, r in enumerate(summary["genuine"], 1):
            w.writerow([i, r["_strain"], r.get("pair", ""), r["_effective_verdict"],
                        r["_confidence_tier"], r.get("rggmci_score", ""),
                        r.get("complementary_disjoint_refs", ""), r.get("n_shared_subjects", ""),
                        r.get("a_core_fraction", ""), r.get("b_core_fraction", ""),
                        r.get("bgc_a", ""), r.get("contig_a", ""), r.get("products_a", ""),
                        r.get("edge_a", ""), r.get("bgc_b", ""), r.get("contig_b", ""),
                        r.get("products_b", ""), r.get("edge_b", ""),
                        r.get("interpretation_guard", "")])
    md_path = out_prefix + "_board.md"
    atomic_write_text(md_path, md_text)
    return md_path, csv_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="RG-GMCI cohort ranked rollup + confidence tiering.")
    ap.add_argument("--packages", required=True, help="dir scanned for */*_4A_RGGMCI_ranked_pairs.csv")
    ap.add_argument("--out-prefix", required=True)
    a = ap.parse_args(argv)
    summary = rollup(a.packages)
    if summary["n_pooled"] == 0:
        emit(f"no ranked_pairs CSVs found under {a.packages}", file=sys.stderr)
        return 1
    md_path, csv_path = write_board(summary, a.out_prefix)
    emit(f"RG-GMCI cohort rollup: {summary['n_high']} HIGH -> {summary['n_genuine']} genuine "
          f"({summary['n_complementary']} complementary + {summary['n_terminus']} terminus), "
          f"{summary['n_excluded_paralog']} paralog excluded, {summary['n_review']} review")
    emit(f"  tiers: {summary['tiers']}", f"  -> {md_path}", f"  -> {csv_path}", sep="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""rggmci_pair_locus_map.py — a locus map for each RG-GMCI fragment pair.

RG-GMCI links two contig-edge fragments when they hit complementary parts of the same reference clusters
(<strain>_4A_RGGMCI_ranked_pairs.csv in a Mamey package). This tool draws that link the way the gap-rescue screen draws
its finds (tools/gap_rescue_locus_map.py):
- on top, the shared MIBiG reference cluster;
- below, fragment A's contig end, a link marker, then fragment B's contig end;
- ribbons from each reference gene to its match, shaded by protein identity.

Which pairs:
- --pair BGC050:BGC054 (repeatable); or --top N, the N best-scoring MODERATE or HIGH pairs;
- both fragments must touch a contig end (Edge or Full-contig). RG-GMCI pairs edge fragments only, so an interior
  fragment is refused, never drawn;
- each fragment needs its full identity (strain / contig / region / BGC alias) from the antiSMASH ZIP. An identity
  hold is refused;
- the reference is the first MIBiG cluster in the pair's best_sources whose GenBank file is in --mibig-dir. A pair
  supported only by non-MIBiG ClusterBlast loci is refused: no local GenBank to draw.

Outputs, per pair: <out>/<A>_<B>_vs_<MIBiG>/rggmci_pair_map.png and .pdf, rggmci_pair_map.tsv (the reference gene table),
rggmci_pair_receipt.json; plus <out>/RGGMCI_PAIR_MAPS.tsv, one row per requested pair, drawn or refused with the reason.

Claim-safety: the link is homology-guided linkage between two contig ends, not a joined sequence, a closed gap or one
proven pathway. Similarity to a MIBiG cluster is not product identity.

CLI:
  python tools/rggmci_pair_locus_map.py --zip <antiSMASH.zip> --label <strain> \\
         --pairs <package>/<strain>_4A_RGGMCI_ranked_pairs.csv (--pair BGC050:BGC054 ... | --top 10) \\
         --mibig-dir <MIBiG gbk dir> [--mibig-names mibig_reference_index.json] --out <dir> [--threads 4]
"""
from __future__ import annotations

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import gap_directed_rescue as gdr  # noqa: E402
from _console import emit  # noqa: E402
from gap_rescue_locus_map import draw_locus_map  # noqa: E402

import argparse  # noqa: E402
import csv  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

EDGE_OK = {"Edge", "Full-contig"}
DRAWABLE = ("MODERATE", "HIGH")
TABLE = ["reference_gene", "name", "product", "status", "best_locus", "best_contig", "best_identity_pct", "on_fragment",
         "fragment_b_locus", "fragment_b_identity_pct"]


def load_pairs(path) -> list[dict]:
    return list(csv.DictReader(open(path, newline="", encoding="utf-8")))


def find_pair(rows: list[dict], a: str, b: str) -> dict | None:
    for r in rows:
        if {r["bgc_a"], r["bgc_b"]} == {a, b}:
            return r
    return None


def select(rows: list[dict], wanted: list[tuple[str, str]], top: int) -> list[tuple[str, str, dict | None, str]]:
    """-> [(A, B, pair row or None, refusal reason or "")]: the pairs to draw, and the refusals with their reason."""
    out = []
    if wanted:
        for a, b in wanted:
            r = find_pair(rows, a, b)
            out.append((a, b, r, "" if r else "pair not in the RG-GMCI table"))
    else:
        ok = [r for r in rows if r.get("rggmci_confidence", "").startswith(DRAWABLE)
              and r.get("edge_a") in EDGE_OK and r.get("edge_b") in EDGE_OK]
        ok.sort(key=lambda r: -float(r.get("rggmci_score") or 0))
        out = [(r["bgc_a"], r["bgc_b"], r, "") for r in ok[:top]]
    checked = []
    for a, b, r, why in out:
        if r and not why:
            bad = [f"{x} is {e}" for x, e in ((r["bgc_a"], r["edge_a"]), (r["bgc_b"], r["edge_b"])) if e not in EDGE_OK]
            if bad:
                why = "interior fragment (RG-GMCI pairs contig-edge fragments only): " + "; ".join(bad)
        checked.append((a, b, r, why))
    return checked


def mibig_reference(pair: dict, mibig_dir: Path) -> Path | None:
    """The first MIBiG cluster in best_sources (ranked by RG-GMCI) whose GenBank file is on disk."""
    for acc in re.findall(r"BGC\d{7}", pair.get("best_sources", "")):
        for p in (mibig_dir / f"{acc}.gbk", mibig_dir / f"{acc}.gb"):
            if p.exists():
                return p
    return None


LINK_WORD = {"the same part of the reference: overlap, not complement": "same genes in both, not a rescue",
             "partly overlapping": "partly overlapping",
             "one fragment holds none of this reference's genes": "one side has no match"}


def drawn_rule(r: dict) -> bool:
    return r.get("reciprocal_best") is True or str(r.get("reciprocal_best")) == "True"


def overlap(in_a: set, in_b: set) -> str:
    """How the two fragments cover the reference: complementary parts support one split pathway; the same part repeated
    reads as paralogous loci."""
    if not in_a or not in_b:
        return "one fragment holds none of this reference's genes"
    both = in_a & in_b
    if not both:
        return "complementary parts of the reference"
    if len(both) >= min(len(in_a), len(in_b)):
        return "the same part of the reference: overlap, not complement"
    return "partly overlapping"


def region_by_alias(regions: list[dict], alias: str) -> dict | None:
    hits = [r for r in regions if r["identity"].split(" / ")[-1] == alias]
    return hits[0] if len(hits) == 1 else None


def draw_pair(label, prots, regions, a, b, pair, reference, names, out_root, threads, sensitivity, hits_cache):
    ra, rb = region_by_alias(regions, a), region_by_alias(regions, b)
    for alias, r in ((a, ra), (b, rb)):
        if r is None or r["identity"].endswith("IDENTITY_HOLD"):
            return None, f"identity hold: {alias} has no single bound strain / contig / region / alias record"
    if ra["contig"] == rb["contig"]:
        return None, "both fragments on one contig: a related-loci question, not a contig-end link"
    ref, _ = gdr.load_reference(reference)
    acc = reference.stem.split(".")[0]
    if acc not in hits_cache:
        hits_cache[acc] = gdr.run_diamond(ref, prots, threads, None if sensitivity == "default" else sensitivity)
    hits = hits_cache[acc]
    rows, _ = gdr.search(ref, prots, regions, hits, ra)
    rows_b, _ = gdr.search(ref, prots, regions, hits, rb)   # the same reference, searched from fragment B's side
    # counted by the rule the map draws by (in the region and a reciprocal best match), so the footnote and the
    # ribbons agree: one long PKS protein that weakly matches two reference genes counts once, for its best one
    in_a = {k for k, r in enumerate(rows) if r.get("status") == "PRESENT_IN_CORE" and drawn_rule(r)}
    in_b = {k for k, r in enumerate(rows_b) if r.get("status") == "PRESENT_IN_CORE" and drawn_rule(r)}
    both = in_a & in_b
    splits, _ = gdr.split_genes(ref, prots, regions, hits)
    out = out_root / f"{a}_{b}_vs_{acc}"
    out.mkdir(parents=True, exist_ok=True)
    name = names.get(acc, "")
    reading = overlap(in_a, in_b)
    rescue = reading == "complementary parts of the reference"
    note = (f"RG-GMCI pair {a} + {b}: score {pair.get('rggmci_score', '')}, {pair.get('rggmci_confidence', '')}; "
            f"shared reference {acc}; reference genes in A {len(in_a)}, in B {len(in_b)}, in both {len(both)} "
            f"({reading}). "
            + ("Homology-guided linkage between two contig ends, not a joined sequence." if rescue else
               "Not a rescue: the fragments do not hold complementary parts of this reference."))
    res = draw_locus_map(reference, rows, splits, prots, regions, ra, label, name, out / "rggmci_pair_map.png",
                         out / "rggmci_pair_map.pdf", partner=rb, pair_note=note, partner_rows=rows_b,
                         link_label="RG-GMCI link" if rescue else "RG-GMCI pair: " + LINK_WORD.get(reading, reading),
                         link_colour="#6D28D9" if rescue else "#6B7280")
    on = {ra["contig"]: "A", rb["contig"]: "B"}
    with open(out / "rggmci_pair_map.tsv", "w", newline="") as fh:
        w = gdr.SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(TABLE)
        for k, (g, r) in enumerate(zip(ref, rows)):
            p = prots.get(r.get("best_protein") or "")
            pb = prots.get(rows_b[k].get("best_protein") or "") if k in in_b else None
            w.writerow([g["id"], g["name"], g["product"], r.get("status", ""), p["tag"] if p else "",
                        p["contig"] if p else "", r.get("best_identity_pct", ""), on.get(p["contig"], "") if p else "",
                        pb["tag"] if pb else "", rows_b[k].get("best_identity_pct", "") if pb else ""])
    receipt = {"tool": "rggmci_pair_locus_map", "label": label, "fragment_a": ra["identity"], "fragment_b": rb["identity"],
               "reference": reference.name, "reference_name": name, "rggmci_score": pair.get("rggmci_score"),
               "rggmci_confidence": pair.get("rggmci_confidence"), "reference_genes": len(rows),
               "reference_genes_in_fragment_a": len(in_a), "reference_genes_in_fragment_b": len(in_b),
               "reference_genes_in_both": len(both), "reading": reading, "complementary": rescue,
               "link_drawn": res["link_drawn"], "contigs_drawn": res["contigs_drawn"],
               "non_claims": ["homology is similarity, not product identity",
                              "an RG-GMCI link is homology-guided linkage between contig ends, not a joined sequence",
                              "a drawn pair is a candidate for review, not one proven pathway"]}
    (out / "rggmci_pair_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt, ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rggmci_pair_locus_map", description=__doc__.split("\n\n")[0])
    ap.add_argument("--zip", required=True, type=Path)
    ap.add_argument("--label", required=True)
    ap.add_argument("--pairs", required=True, type=Path, help="<strain>_4A_RGGMCI_ranked_pairs.csv")
    ap.add_argument("--pair", action="append", default=[], help="BGCxxx:BGCyyy (repeatable)")
    ap.add_argument("--top", type=int, default=10, help="without --pair: the N best MODERATE/HIGH edge pairs")
    ap.add_argument("--mibig-dir", required=True, type=Path)
    ap.add_argument("--mibig-names", default=None)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--sensitivity", default=gdr.SENSITIVITY_DEFAULT)
    args = ap.parse_args(argv)
    gdr.assert_output_outside_bundle(args.out, __file__)
    wanted = []
    for p in args.pair:
        if ":" not in p:
            ap.error(f"--pair takes BGCxxx:BGCyyy, got {p!r}")
        wanted.append(tuple(p.split(":", 1)))
    plan = select(load_pairs(args.pairs), wanted, args.top)
    prots, regions = gdr.load_genome(args.zip, args.label)
    args.out.mkdir(parents=True, exist_ok=True)
    cache, index = {}, []
    names = gdr.load_mibig_names(args.mibig_names)
    for a, b, pair, why in plan:
        ref = None
        if not why:
            ref = mibig_reference(pair, args.mibig_dir)
            if ref is None:
                why = "no shared MIBiG reference on disk (supported only by non-MIBiG ClusterBlast loci)"
        rec = None
        if not why:
            try:
                rec, why = draw_pair(args.label, prots, regions, a, b, pair, ref, names, args.out, args.threads,
                                     args.sensitivity, cache)
            except Exception as exc:  # one pair that cannot be drawn never stops the others; its reason is kept
                rec, why = None, f"drawing failed: {type(exc).__name__}: {exc}"
        index.append([a, b, pair.get("rggmci_score", "") if pair else "", pair.get("rggmci_confidence", "") if pair else "",
                      ref.stem if ref else "", "drawn" if rec else "refused", why or (rec["reading"] if rec else ""),
                      rec["fragment_a"] if rec else "", rec["fragment_b"] if rec else ""])
        emit(f"{args.label} {a} + {b}: " + ("drawn" if rec else f"refused ({why})"))
    with open(args.out / "RGGMCI_PAIR_MAPS.tsv", "w", newline="") as fh:
        w = gdr.SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["bgc_a", "bgc_b", "rggmci_score", "rggmci_confidence", "reference", "result", "reading_or_reason",
                    "fragment_a", "fragment_b"])
        w.writerows(index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""query_support_table.py <placement_dir> <refpkg_dir> <out.tsv>

Emits the per-query supplementary table a methods/taxonomy paper needs and that the lane was not
producing: for every placed query, its 16S coverage in the reference coordinate frame, the best-edge
likelihood weight ratio (LWR), how much mass sits on the best edge versus the top three, the fitted
pendant length, and its nearest named reference with the patristic distance.

Why it matters: LWR is per-query placement support and is NOT the reference backbone's bootstrap.
A query with a low best-edge LWR has its placement mass spread over several branches -- the
NEIGHBOURHOOD is the result, not the single edge. Reporting the figure without this table lets a
reader over-read a tip position. Judgment deferred.
"""
import sys, os, json, csv, re

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _console import emit
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mamey.csv_safety import SafeWriter

def main():
    pd, rp, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    j = json.load(open(os.path.join(pd, "epa_result.jplace")))
    f = j["fields"]; ei, li, pi = f.index("edge_num"), f.index("like_weight_ratio"), f.index("pendant_length")

    # query alignment occupancy in the reference coordinate frame
    def load(p):
        d, cur = {}, None
        for ln in open(p):
            if ln.startswith(">"): cur = ln[1:].strip().split()[0]; d[cur] = ""
            else: d[cur] += ln.strip()
        return d
    qa = load(os.path.join(pd, "query.aligned.fasta"))
    ncol = len(next(iter(qa.values()))) if qa else 0

    def _key(q):
        """Join key for query ids. jplace names are PER-16S-COPY (`query copy`) while the neighborhoods
        table is STRAIN-level (`query strain`), and the two files disagree on `-` vs `_`. Matching them by
        exact string silently produced a blank nearest_reference for every query in most runs -- a
        join that fails without erroring is worse than one that crashes, so normalise both sides."""
        m = re.match(r"\s*(AS|SID)[-_ ]?(\d+)", (q or ""), re.I)
        if m:
            return f"{m.group(1).upper()}-{int(m.group(2))}"
        # not an AS/SID id (e.g. a reference tip mis-classified as a query): key on the raw string so
        # it can never collide with a real strain.
        return re.sub(r"\s+", " ", (q or "").strip()).upper()

    near = {}
    for fn in sorted(os.listdir(pd)):
        # runs carry _neighborhoods.tsv, but also _neighborhoods_VALIDATED.tsv / _FULL.tsv / _top3.tsv
        if "_neighborhoods" in fn and fn.endswith(".tsv"):
            for r in csv.DictReader(open(os.path.join(pd, fn)), delimiter="\t"):
                k = _key(r.get("as_query", ""))
                if k and k not in near:
                    near[k] = (r.get("nearest_type_strain", ""), r.get("patristic_dist", ""))

    rows = []
    for p in j["placements"]:
        ps = sorted(p["p"], key=lambda r: -r[li])
        best = ps[0]
        top3 = sum(r[li] for r in ps[:3])
        for nm in p["n"]:
            seq = qa.get(nm, "")
            occ = sum(1 for c in seq if c not in "-.Nn")
            # EPA-ng emits 0.105360516 (= -ln 0.9) as a DEFAULT pendant when it does not optimise one.
            # A tip carrying it has a drawn branch length that is a placeholder, not an estimate, and
            # must not be read as "this query hangs this far off the backbone".
            default_pendant = abs(best[pi] - 0.105360516) < 1e-6
            rows.append([nm, ncol, occ, f"{100*occ/ncol:.1f}" if ncol else "",
                         f"{best[li]:.4f}", f"{top3:.4f}", len(ps), f"{best[pi]:.6f}",
                         "YES" if default_pendant else "no",
                         near.get(_key(nm), ("", ""))[0][:70], near.get(_key(nm), ("", ""))[1]])

    rows.sort(key=lambda r: float(r[4]))
    with open(outp, "w", newline="") as fh:
        w = SafeWriter(fh, delimiter="\t")
        w.writerow(["query", "ref_alignment_columns", "query_nongap_positions", "coverage_pct",
                    "best_edge_LWR", "top3_LWR_sum", "n_edges_with_mass", "pendant_length",
                    "pendant_is_epang_default", "nearest_reference", "patristic_distance"])
        w.writerows(rows)
    lw = sorted(float(r[4]) for r in rows)
    emit(f"[support] {len(rows)} queries -> {outp}")
    emit(f"  best-edge LWR: min={lw[0]:.3f} median={lw[len(lw)//2]:.3f} max={lw[-1]:.3f}; "
          f"{sum(1 for x in lw if x < 0.5)} of {len(lw)} below 0.5 (mass spread over several edges)")
    nd = sum(1 for r in rows if r[8] == "YES")
    if nd: emit(f"  {nd} of {len(rows)} queries carry EPA-ng's DEFAULT pendant length (0.105360516): "
                 f"their drawn branch length is a placeholder, not an estimate")
    nn = sum(1 for r in rows if r[9])
    emit(f"  nearest reference named for {nn} of {len(rows)} queries"
          + ("" if nn == len(rows) else "  <-- check the neighborhoods file join"))
    cov = sorted(float(r[3]) for r in rows if r[3])
    if cov: emit(f"  coverage: min={cov[0]:.1f}% median={cov[len(cov)//2]:.1f}% max={cov[-1]:.1f}%")


if __name__ == "__main__":
    main()

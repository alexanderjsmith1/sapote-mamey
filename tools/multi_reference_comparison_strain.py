#!/usr/bin/env python3
"""Draw the multi-reference comparison for every BGC of one strain, with one DIAMOND search for the whole strain.

A BGC with a gap-rescue folder (<BGC>_vs_<ref>) gets its SUPPORTED partner contigs; every other antiSMASH region is
drawn alone. Writes OUTDIR/<BGC>/ (comparison.png/.pdf/.svg, caption.txt, references.tsv, pairs.tsv, receipt.json),
OUTDIR/MULTI_REFERENCE.tsv (one row per BGC: references drawn, the top one, or why none) and OUTDIR/<label>_review.pdf
(one page per figure, in BGC order).

Usage: python tools/multi_reference_comparison_strain.py --zip Z --label AS-n [--rescue-root DIR] --mibig-db D.dmnd
         --mibig-dir GBK_DIR [--mibig-names INDEX.json] [--gene-labels T.tsv] [--top 4] --out OUTDIR
"""
import argparse, csv, re, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gap_directed_rescue as gdr  # noqa: E402
import multi_reference_comparison as mrc  # noqa: E402
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from _console import emit  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    for a in ("--zip", "--label", "--mibig-db", "--mibig-dir", "--out"):
        ap.add_argument(a, required=True)
    for a in ("--rescue-root", "--mibig-names", "--gene-labels"):
        ap.add_argument(a)
    ap.add_argument("--top", type=int, default=4)
    ap.add_argument("--ribbons-only", action="store_true",
                    help="only add ribbon figures (<BGC>/ribbon/) to an existing run; the multi-reference figures are not redrawn")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    genome = gdr.load_genome(Path(a.zip), a.label)
    prots, regions = genome
    rescues = {}
    if a.rescue_root and Path(a.rescue_root).is_dir():
        for f in Path(a.rescue_root).iterdir():
            if f.is_dir() and "_vs_" in f.name and (f / "gap_rescue.tsv").exists():
                rescues[f.name.split("_vs_")[0]] = f
    aliases = [r["identity"].split(" / ")[-1] for r in regions]
    loci = [(b, rescues.get(b)) for b in sorted({x for x in aliases if re.fullmatch(r"BGC\d+", x)})]
    # one search: every protein any locus can draw
    want = set()
    for b, rs in loci:
        for _, qs in mrc.locus(prots, regions, rs, a.label, b):
            want.update(qs)
    with tempfile.TemporaryDirectory() as td:
        qf = Path(td, "strain.faa")
        qf.write_text("".join(f">{q}\n{prots[q]['aa']}\n" for q in sorted(want)))
        res = mrc.rc.search_mibig(str(qf), a.mibig_db, threads=4, sensitivity="ultra-sensitive", max_target_seqs=500)
    if not res.get("ok"):
        sys.exit(f"search failed: {res.get('reason')}")
    emit(f"{a.label}: {len(loci)} BGCs, {len(want)} proteins, {len(res['hits'])} hits", flush=True)
    rows, pages = [], []
    # one figure per pathway: a BGC whose locus (its segments: each contig with its region) is contained in another BGC's
    # larger multi-contig locus is drawn once, under that larger locus (equal loci: the lower BGC number). The pointing BGC
    # gets SAME_LOCUS_AS.txt; the drawn one gets ALSO_BGCS.txt, so the deck can point between them.
    segs = {b: frozenset(h for h, qs in mrc.locus(prots, regions, rs, a.label, b) if qs) for b, rs in loci}
    num = lambda b: int(re.sub(r"\D", "", b))
    canon = {}
    for b, _ in loci:
        sup = [c for c, _ in loci if c != b and len(segs[c]) > 1 and segs[b] <= segs[c] and (segs[b] != segs[c] or num(c) < num(b))]
        if sup:
            canon[b] = max(sup, key=lambda c: (len(segs[c]), -num(c)))
    for b, c in canon.items():  # follow a chain to its top
        while c in canon:
            c = canon[c]
        canon[b] = c
    for b, rs in loci:
        (out / b).mkdir(parents=True, exist_ok=True)
        if b in canon:
            c = canon[b]
            (out / b / "SAME_LOCUS_AS.txt").write_text(c + "\n")
            (out / c).mkdir(parents=True, exist_ok=True)
            with open(out / c / "ALSO_BGCS.txt", "a") as fh:
                fh.write(b + "\n")
            rows.append((b, "yes" if rs else "no", 0, "", "", f"part of {c}'s locus (drawn once, under {c})"))
            emit(b, rows[-1][-1], flush=True)
            continue
        try:
            m = mrc.build(a.zip, a.label, rs, a.mibig_db, a.mibig_dir, a.mibig_names, a.gene_labels, a.top, genome=genome,
                          bgc=b, hits=res["hits"])
            # a ribbon view of the top match, when the deck's existing ribbon slide (the gap-rescue reference) shows another
            rescue_ref = rs.name.split("_vs_")[1] if rs else ""
            if m["refs"] and m["refs"][0]["accession"] != rescue_ref and not (out / b / "ribbon" / "render" / "comparison.png").exists():
                try:
                    emit(b, "ribbon:", mrc.ribbon_top(m, out / b), flush=True)
                except Exception as e:  # recorded, not fatal
                    emit(b, f"ribbon FAILED: {str(e)[:160]}", flush=True)
            if a.ribbons_only:
                continue
            if not m["refs"]:
                rows.append((b, "yes" if rs else "no", 0, "", "", "no MIBiG cluster matches two or more locus genes"))
                continue
            for band in (1.0, 1.3, 1.6, 1.9, 2.3):
                try:
                    mrc.draw(m, out / b, label_band=band)
                    break
                except ValueError as e:
                    if "title band" not in str(e):
                        raise
            mrc.write(m, out / b)
            t = m["refs"][0]
            rows.append((b, "yes" if rs else "no", len(m["refs"]), f"{t['accession']} {t['compound']}", len(t["pairs"]), "drawn"))
            pages.append(out / b / "comparison.png")
        except Exception as e:  # one BGC's failure is recorded, not fatal
            rows.append((b, "yes" if rs else "no", 0, "", "", f"FAILED: {str(e)[:160]}"))
        emit(b, rows[-1][-1], flush=True)
    with open(out / "MULTI_REFERENCE.tsv", "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["bgc", "gap_rescue_partners", "references_drawn", "top_reference", "top_locus_genes_matched", "status"])
        w.writerows(rows)
    if pages:
        from PIL import Image
        ims = [Image.open(p).convert("RGB") for p in pages]
        ims[0].save(out / f"{a.label}_review.pdf", save_all=True, append_images=ims[1:], resolution=150)
    emit(f"done: {sum(1 for r in rows if r[-1] == 'drawn')} drawn of {len(rows)}")


if __name__ == "__main__":
    main()

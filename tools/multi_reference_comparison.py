#!/usr/bin/env python3
"""One AS locus against its best reference loci (MIBiG clusters, or reference-genome antiSMASH regions), KnownClusterBlast style: the locus on the top row, each reference on
its own row below, genes colored by correspondence, no ribbons.

The locus is the antiSMASH region plus the partner contigs its gap rescue SUPPORTED (the same contigs the single
reference comparison draws), each contig a separate segment on one row, never joined. A partner contig contributes its
own antiSMASH region when it has one, else a window 3 kb either side of its rescued genes.

Every locus protein is searched once against the local MIBiG protein database, or a database built from the region
GenBank files (DIAMOND, ultra-sensitive). A hit counts
at mamey.ref_completion's discovery thresholds (identity and query coverage). Within each reference cluster, pairs are
taken one-to-one by bitscore. Clusters are ranked by distinct locus genes matched, then summed bitscore; the top N are
drawn. A reference much longer than the locus is shown from its first to its last matched gene, plus two genes each side.

Usage: python tools/multi_reference_comparison.py --zip Z --label AS-n (--rescue DIR/<BGC>_vs_<ref> | --bgc BGCnnn)
         (--mibig-db D.dmnd --mibig-dir GBK_DIR | --ref-gbk-dir REGION_GBKS)
         [--mibig-names INDEX.json] [--gene-labels T.tsv] [--top 4] --out OUTDIR
Writes OUTDIR/references.tsv, pairs.tsv, receipt.json and comparison.png/.pdf/.svg.
Similarity only: a matched gene is a best protein hit, not orthology, function or product.
"""
import argparse, colorsys, csv, json, math, re, statistics, sys, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import gap_directed_rescue as gdr  # noqa: E402
import rescue_locus_comparison as rlc  # noqa: E402
from mamey import ref_completion as rc  # noqa: E402
from mamey.figures import locus_comparison as lc  # noqa: E402
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from _console import emit  # noqa: E402


def locus(prots, regions, rescue, label, bgc=None):
    """[(segment heading, [protein ids])]: the region first, then up to two SUPPORTED partner contigs (none without a
    gap-rescue folder)."""
    bgc = bgc or rescue.name.split("_vs_")[0]
    reg = next(r for r in regions if r["identity"].endswith(f"/ {bgc}"))
    by_tag = {p["tag"]: q for q, p in prots.items()}
    within = lambda c, lo, hi: sorted((q for q, p in prots.items() if p["contig"] == c and p["start"] >= lo and p["end"] <= hi),
                                      key=lambda q: prots[q]["start"])
    node = lambda c: c.split("_length")[0]
    segs = [(f"{node(reg['contig'])} · {bgc}", within(reg["contig"], reg["start"], reg["end"]))]
    part = {}
    rows = csv.DictReader(open(rescue / "gap_rescue.tsv"), delimiter="\t") if rescue and (rescue / "gap_rescue.tsv").exists() else []
    for r in rows:
        if r["status"] == "MISSING_FOUND_CLEAR" and r.get("partner_verdict") == "SUPPORTED" and r["best_locus"] in by_tag:
            q = by_tag[r["best_locus"]]
            part.setdefault(prots[q]["contig"], set()).add(q)
    for contig, qs in sorted(part.items(), key=lambda kv: -len(kv[1]))[:2]:
        if contig == reg["contig"]:
            continue
        own = [x for x in regions if x["contig"] == contig]
        if own:
            x = own[0]
            segs.append((f"{node(contig)} · {x['identity'].split(' / ')[3]}", within(contig, x["start"], x["end"])))
        else:
            lo = min(prots[q]["start"] for q in qs) - 3000
            hi = max(prots[q]["end"] for q in qs) + 3000
            segs.append((f"{node(contig)} · no region", within(contig, lo, hi)))
    return segs


def compound_keys(name):
    """The names one compound goes by, lowercased: 'X (ABBR)', 'X' and 'ABBR' are one compound (MIBiG writes
    ethylenediaminesuccinic acid hydroxyarginine three ways). A bracketed word counts as an abbreviation only when it
    is one word holding a letter."""
    n = " ".join(name.replace(" and others", "").lower().split())
    keys = {n}
    base = " ".join(re.sub(r"\([^()]*\)", " ", n).split())
    if base:
        keys.add(base)
    keys |= {x for x in re.findall(r"\(([^()\s]+)\)", n) if len(x) >= 2 and re.search(r"[a-z]", x)}
    if " " not in n and len(n) >= 2:  # a bare abbreviation is itself a key
        keys.add(n)
    return keys


def rank_references(hits, top):
    """{accession: [(query id, reference index, pident, bitscore)]} one-to-one by bitscore, top N by genes then bitscore."""
    per = {}
    for h in hits:
        if float(h["pident"]) < rc.DISCOVERY_MIN_ID or float(h["qcovhsp"]) < rc.DISCOVERY_MIN_COV:
            continue
        acc, i = h["sseqid"].split("|")[:2]
        per.setdefault(acc, []).append((h["qseqid"], int(i), float(h["pident"]), float(h["bitscore"])))
    out = {}
    for acc, hs in per.items():
        uq, ur, pairs = set(), set(), []
        for q, i, p, b in sorted(hs, key=lambda x: -x[3]):
            if q not in uq and i not in ur:
                uq.add(q); ur.add(i); pairs.append((q, i, p, b))
        out[acc] = pairs
    ranked = sorted(out.items(), key=lambda kv: (-len(kv[1]), -sum(x[3] for x in kv[1]), kv[0]))
    return [(a, p) for a, p in ranked if len(p) >= rc.DISCOVERY_MIN_PROTEINS]


def colors(n):
    """n distinct colors in locus order; past the house palette, hues step by the golden angle with alternating
    lightness so neighbouring genes never share a shade."""
    if n <= len(lc.PALETTE):
        return list(lc.PALETTE[:n])
    return ['#%02x%02x%02x' % tuple(round(c * 255) for c in colorsys.hsv_to_rgb((i * .618034) % 1, (.70, .50, .85)[i % 3],
                                                                                   (.78, .62, .90)[i % 3])) for i in range(n)]


def organism(gbk):
    """The ORGANISM line of a GenBank file ('' when absent)."""
    for line in open(gbk, errors="replace"):
        if line.startswith("  ORGANISM"):
            return line.split("ORGANISM", 1)[1].strip()
        if line.startswith("FEATURES"):
            break
    return ""


def region_db(gbk_dir, work):
    """A DIAMOND database of every CDS in a folder of reference-genome antiSMASH region GenBank files, ids
    '<file stem>|<gene index>' as gap_directed_rescue.load_reference numbers them."""
    import subprocess
    faa = Path(work, "regions.faa")
    with open(faa, "w") as fh:
        for g in sorted(Path(gbk_dir).glob("*.gbk")):
            for x in gdr.load_reference(g)[0]:
                fh.write(f">{g.stem}|{x['i']}\n{x['aa']}\n")
    subprocess.run(["diamond", "makedb", "--in", str(faa), "--db", str(Path(work, "regions")), "--quiet"], check=True)
    return Path(work, "regions.dmnd")


def build(zip_path, label, rescue, mibig_db, mibig_dir, mibig_names=None, gene_labels=None, top=6, genome=None,
          ref_gbk_dir=None, bgc=None, hits=None, min_fraction=0.0):
    """mibig_db/mibig_dir: the MIBiG protein database and GenBank folder. With ref_gbk_dir, the references are that
    folder's antiSMASH region GenBank files instead (one row per organism)."""
    prots, regions = genome or gdr.load_genome(Path(zip_path), label)
    segs = locus(prots, regions, rescue, label, bgc)
    qids = [q for _, qs in segs for q in qs]
    import tempfile
    if hits is not None:  # one search shared by every locus of the strain (strain driver)
        res = {"ok": True, "hits": [h for h in hits if h["qseqid"] in set(qids)]}
    else:
        with tempfile.TemporaryDirectory() as td:
            if ref_gbk_dir:
                mibig_db, mibig_dir = region_db(ref_gbk_dir, td), Path(ref_gbk_dir)
            qf = Path(td, "locus.faa")
            qf.write_text("".join(f">{q}\n{prots[q]['aa']}\n" for q in qids))
            res = rc.search_mibig(str(qf), str(mibig_db), threads=4, sensitivity="ultra-sensitive", max_target_seqs=500)
    if not res.get("ok"):
        raise RuntimeError(f"reference search failed: {res.get('reason')}")
    refs, seen = [], []  # seen: (names, other accessions) per compound drawn
    span = sum(max(prots[q]["end"] for q in qs) - prots[qs[0]]["start"] for _, qs in segs)
    skipped = []
    for acc, pairs in rank_references(res["hits"], top):  # one row per compound (organism): the best entry, others noted
        gbk = Path(mibig_dir) / f"{acc}.gbk"
        if rc._locus_kb(gbk) > rc.DISCOVERY_MAX_KB:  # a whole-genome or very long entry, as in reference discovery
            skipped.append((acc, f"longer than {rc.DISCOVERY_MAX_KB:.0f} kb"))
            continue
        g = {x["i"]: x for x in gdr.load_reference(gbk)[0]}
        hit_span = max(g[i]["end"] for _, i, *_ in pairs) - min(g[i]["start"] for _, i, *_ in pairs)
        if hit_span > max(3 * span, 60000):  # matches scattered across the entry are not one cluster's match
            skipped.append((acc, f"matched genes spread over {hit_span / 1000:.0f} kb"))
            continue
        if not any(prots[q].get("kind") in rc.BIOSYNTHETIC_KINDS for q, *_ in pairs):  # the discovery rule: transport or
            skipped.append((acc, "no biosynthetic locus gene among the matches"))           # regulator matches alone don't count
            continue
        keys = compound_keys(organism(Path(mibig_dir) / f"{acc}.gbk") if ref_gbk_dir else rlc.compound_name(acc, mibig_names) or acc)
        known = next((grp for grp in seen if grp[0] & keys), None)
        if known is not None:  # the group takes this entry's names too, so 'X', 'X (ABBR)' and 'ABBR' chain together
            known[0].update(keys)
            known[1].append(acc)
            continue
        if min_fraction and refs and len(pairs) < min_fraction * len(refs[0][1]):  # optional; off by default (overmerged regions)
            skipped.append((acc, f"{len(pairs)} genes, under {min_fraction:.0%} of the top match ({len(refs[0][1])})"))
            continue
        if len(refs) < top:
            seen.append((set(keys), []))
            refs.append((acc, pairs, seen[-1][1]))
    names = {}
    if gene_labels and Path(gene_labels).exists():
        names = {r["locus_tag"]: r.get("short_label", "") for r in csv.DictReader(open(gene_labels), delimiter="\t")}
    out_refs = []
    for acc, pairs, also in refs:
        genes, desc = gdr.load_reference(Path(mibig_dir) / f"{acc}.gbk")
        name = organism(Path(mibig_dir) / f"{acc}.gbk") if ref_gbk_dir else rlc.compound_name(acc, mibig_names)
        import re as _re
        m_acc = (_re.search(r"(?<![A-Za-z])([A-Z]{1,2}\d{5,8}|[A-Z]{4,6}\d{8,10})(?:\.\d+)?", acc)  # an INSD accession, not a
                 or _re.search(r"([A-Z]{1,6}_?\d{5,}(?:\.\d+)?)", acc)) if ref_gbk_dir else None    # strain designation
        out_refs.append({"accession": acc, "display_id": m_acc.group(1) if m_acc else acc, "compound": name, "description": desc, "also": also,
                         "genes": genes, "pairs": pairs, "gbk": str((Path(mibig_dir) / f"{acc}.gbk").resolve())})
    return {"label": label, "bgc": bgc or rescue.name.split("_vs_")[0], "segments": segs, "regions": regions,
            "zip": str(zip_path),
            "source": "reference-genome antiSMASH regions" if ref_gbk_dir else "MIBiG 4.0 clusters", "prots": prots, "names": names,
            "refs": out_refs, "skipped": skipped, "min_fraction": min_fraction, "n_hits": len(res["hits"]), "sources": [zip_path] + ([] if ref_gbk_dir else [mibig_db])
            + ([rescue / "gap_rescue.tsv"] if rescue and (rescue / "gap_rescue.tsv").exists() else [])}


def draw(m, out, width_in=16.0, label_band=1.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrow
    prots, segs, refs = m["prots"], m["segments"], m["refs"]
    matched = [q for q in (q for _, qs in segs for q in qs) if any(q == p[0] for r in refs for p in r["pairs"])]
    col = dict(zip(matched, colors(len(matched))))
    # Orientation. The region contig is drawn as it is. The best reference faces the region (bitscore-weighted strand
    # agreement on the region's matches); each partner contig is then turned to agree with that reference, and every
    # other reference faces the locus as drawn. Contig order and joins stay unknown; only directions are chosen.
    seg_of = {q: k for k, (_, qs) in enumerate(segs) for q in qs}
    def vote(pairs, qstrand, ref_g):
        w = sum(b * (1 if qstrand(q) == ref_g[i]["strand"] else -1) for q, i, _, b in pairs)
        return 1 if w >= 0 else -1
    so = [1] * len(segs)
    if refs:
        g1 = {x["i"]: x for x in refs[0]["genes"]}
        core_pairs = [x for x in refs[0]["pairs"] if seg_of[x[0]] == 0] or refs[0]["pairs"]
        o1 = vote(core_pairs, lambda q: prots[q]["strand"], g1)
        for k in range(1, len(segs)):
            pk = [x for x in refs[0]["pairs"] if seg_of[x[0]] == k]
            if pk:
                so[k] = vote(pk, lambda q: o1 * prots[q]["strand"], g1)
    m["segment_orientation"] = so
    # query row: contigs side by side, a gap between them
    span_total = sum(prots[qs[-1]]["end"] - prots[qs[0]]["start"] for _, qs in segs)
    gap = max(1500, span_total * .04)
    qx, segx, x = {}, [], 0.0
    for k, (head, qs) in enumerate(segs):
        a0, b0 = prots[qs[0]]["start"], max(prots[q]["end"] for q in qs)
        for q in qs:
            p = prots[q]
            s0, e0 = (p["start"] - a0, p["end"] - a0) if so[k] > 0 else (b0 - p["end"], b0 - p["start"])
            qx[q] = (x + s0, x + e0, so[k] * p["strand"])
        e = x + b0 - a0
        segx.append((head + ("\nreversed" if so[k] < 0 else ""), x, e)); x = e + gap
    qspan = x - gap
    rows = []
    for r in refs:
        g = {x["i"]: x for x in r["genes"]}
        pr = r["pairs"]
        o = vote(pr, lambda q: qx[q][2], g)
        genes = r["genes"]
        cropped = False
        if max(x["end"] for x in genes) - min(x["start"] for x in genes) > 1.5 * qspan:
            idx = [k for k, x in enumerate(genes) if x["i"] in {i for _, i, *_ in pr}]
            genes = genes[max(0, min(idx) - 2):max(idx) + 3]
            cropped = True
        mid = lambda x: o * (x["start"] + x["end"]) / 2
        off = statistics.median((qx[q][0] + qx[q][1]) / 2 - mid(g[i]) for q, i, *_ in pr)
        place = {x["i"]: (min(o * x["start"], o * x["end"]) + off, max(o * x["start"], o * x["end"]) + off, o * x["strand"]) for x in genes}
        grp = {i: q for q, i, *_ in pr}
        rows.append((r, place, grp, cropped))
    lo = min([0.0] + [a for _, pl, _, _ in rows for a, _, _ in pl.values()])
    hi = max([qspan] + [b for _, pl, _, _ in rows for _, b, _ in pl.values()])
    n_locus = sum(len(qs) for _, qs in segs)
    pitch = 1.0
    sb = 10 ** math.floor(math.log10(max((hi - lo) / 1000 / 6, .1)))
    sb = m["scale_kb"] = next(k * sb for k in (5, 2, 1) if k * sb <= (hi - lo) / 1000 / 5)
    cap = textwrap.fill(caption(m, rows, segx), 175)
    n_cap = cap.count("\n") + 1
    if not any(m["names"].get(prots[q]["tag"]) for q in qx):  # no gene labels to clear: no empty band under the title
        label_band = .25
    band = {"title": .5, "labels": label_band, "rows": .85 * (len(rows) + 1), "caption": .17 * n_cap + .35}
    H = sum(band.values())
    fig = plt.figure(figsize=(width_in, H))
    ax = fig.add_axes([0.25, band["caption"] / H, 0.66, band["rows"] / H])
    ax.set_xlim((lo - (hi - lo) * .01) / 1000, (hi + (hi - lo) * .01) / 1000)
    ys = [0.0] + [-(k + 1) * pitch for k in range(len(rows))]
    ax.set_ylim(ys[-1] - .5, .5)
    ax.axis("off")
    hl = (hi - lo) / 1000 * .009

    def arrow(s, e, st, yy, c):
        s, e = s / 1000, e / 1000
        ax.add_patch(FancyArrow(s if st > 0 else e, yy, (e - s) * st, 0, width=.16, head_width=.30,
                                head_length=min((e - s) * .35, hl), length_includes_head=True, facecolor=c,
                                edgecolor="#405664", lw=.6, zorder=3))
    seg_labels = []
    for head, a, b in segx:
        ax.plot([a / 1000, b / 1000], [0, 0], color="#a8b5bc", lw=.8, zorder=1)
        seg_labels.append(ax.text((a + b) / 2000, -.24, head, ha="center", va="top", fontsize=8.5, color="#2b2b2b", linespacing=1.1))
    labs = []
    for q, (s, e, st) in qx.items():
        arrow(s, e, st, 0, col.get(q, "#d6dcdf"))
        t = (m["names"].get(prots[q]["tag"]) or "")[:28]
        if t:
            labs.append((q in col, ax.annotate(t, ((s + e) / 2000, 0), xytext=(0, 9), textcoords="offset points", ha="left",
                                               va="bottom", fontsize=9, rotation=40, rotation_mode="anchor", zorder=4)))
    for (r, place, grp, cropped), yy in zip(rows, ys[1:]):
        xs = [v for v in place.values()]
        ax.plot([min(a for a, _, _ in xs) / 1000, max(b for _, b, _ in xs) / 1000], [yy, yy], color="#a8b5bc", lw=.8, zorder=1)
        for i, (s, e, st) in place.items():
            arrow(s, e, st, yy, col.get(grp.get(i), "#d6dcdf"))
    fig.canvas.draw()
    rnd = fig.canvas.get_renderer()
    for k in range(1, len(seg_labels)):  # a contig name that would touch its neighbour drops one line
        if seg_labels[k].get_window_extent(rnd).overlaps(seg_labels[k - 1].get_window_extent(rnd)):
            x, y = seg_labels[k].get_position()
            seg_labels[k].set_position((x, y - .20))
    kept = []
    for pri, lab in sorted(labs, key=lambda x: (not x[0], ax.transData.transform(x[1].xy)[0])):
        poly = lc._label_polygon(lab, rnd)
        if any(lc._polygons_overlap(poly, k) for k in kept):
            lab.set_visible(False)
        else:
            kept.append(poly)
    # headings in the left column, level with their rows
    def heading(yy, bold, sub):
        yf = fig.transFigure.inverted().transform(ax.transData.transform((0, yy)))[1]
        # at most two lines each, so a heading never reaches the next row; a long one steps down a font size before
        # anything is cut (references.tsv keeps every name whole)
        def fit(text, size, width, small, wide):
            return (size, textwrap.fill(text, width)) if len(textwrap.wrap(text, width)) <= 2 else \
                   (small, textwrap.fill(text, wide, max_lines=2, placeholder=" …"))
        bs, bt = fit(bold, 11, 32, 9.5, 38)
        ss, st = fit(sub, 9.5, 42, 8.5, 48)
        fig.text(.235, yf + .004, bt, ha="right", va="bottom", fontsize=bs, weight="bold", color="#163344")
        fig.text(.235, yf - .004, st, ha="right", va="top", fontsize=ss, color="#2b2b2b")
    heading(0, f"{m['label']} {m['bgc']} locus", (f"{len(segs)} contigs, drawn side by side; " if len(segs) > 1 else "") + f"{n_locus} genes")
    for (r, place, grp, cropped), yy in zip(rows, ys[1:]):
        ids = [p for _, _, p, _ in r["pairs"]]
        nm = (r["compound"] or r["description"]).strip()
        nm = nm if len(nm) <= 60 else nm[:59].rstrip(" ,-(") + "…"  # a very long chemical name is cut; references.tsv keeps it whole
        heading(yy, f"{nm} · {r['display_id']}" if m["source"] != "MIBiG 4.0 clusters" else f"{r['accession']}: {nm}", f"{len(r['pairs'])} of {n_locus} locus genes, median {statistics.median(ids):.0f}% identity"
                + ("; genes around the matches" if cropped else "")
                + (f"; also {', '.join(r['also'])} (same {'compound' if m['source'].startswith('MIBiG') else 'organism'})" if r["also"] else ""))
    fig.text(.02, 1 - .12 / H, f"{m['label']} {m['bgc']}: best {'MIBiG' if m['source'].startswith('MIBiG') else 'reference-genome'} matches", fontsize=17, weight="bold", color="#163344", va="top")
    fig.text(.02, (band["caption"] - .12) / H, cap, fontsize=10, va="top", ha="left", color="black", linespacing=1.35)
    # scale bar
    x0 = lo / 1000
    ax.plot([x0, x0 + sb], [ys[-1] - .42] * 2, color="#172f40", lw=1.5)
    ax.text(x0 + sb / 2, ys[-1] - .47, f"{sb:g} kb", ha="center", va="top", fontsize=9)
    # rotated labels must clear the title band; text outside the figure is an error
    fig.canvas.draw()
    top_px = max([l.get_window_extent(rnd).y1 for _, l in labs if l.get_visible()] + [0])
    if top_px > fig.bbox.height * (1 - band["title"] / H):
        raise ValueError("gene labels run into the title band; raise band['labels']")
    for t in fig.texts + ax.texts:
        bb = t.get_window_extent(rnd)
        if t.get_text().strip() and (bb.x0 < 0 or bb.y0 < 0 or bb.x1 > fig.bbox.width or bb.y1 > fig.bbox.height):
            raise ValueError(f"text outside the figure: {t.get_text()[:40]!r}")
    # every pair of overlapping texts (headings, contig labels, title, caption; rotated gene labels are already kept
    # apart above) goes into the receipt, so a slide check reads it instead of looking for it
    m["text_overlaps"] = text_overlaps(fig.texts + ax.texts, rnd, skip=[l for _, l in labs])
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out / f"comparison.{ext}", dpi=180)
    # the slide copy: no title and no caption (the slide carries both), cropped to the drawing
    for t in fig.texts:
        if t.get_text() in (cap,) or t.get_text().endswith("matches") and t.get_fontsize() >= 17:
            t.set_visible(False)
    fig.savefig(out / "slide.png", dpi=180, bbox_inches="tight", pad_inches=.15)
    plt.close(fig)
    (out / "caption.txt").write_text(caption(m, rows, segx) + "\n")
    return col


def text_overlaps(texts, renderer, skip=()):
    """Pairs of visible texts whose drawn boxes overlap by more than a pixel, each named by its first 40 characters."""
    skip = {id(t) for t in skip}
    boxes = [(t.get_text().split("\n")[0][:40], t.get_window_extent(renderer)) for t in texts
             if t.get_visible() and t.get_text().strip() and id(t) not in skip]
    return [[a, b] for i, (a, ba) in enumerate(boxes) for b, bb in boxes[i + 1:]
            if ba.x0 < bb.x1 - 1 and bb.x0 < ba.x1 - 1 and ba.y0 < bb.y1 - 1 and bb.y0 < ba.y1 - 1]


def caption(m, rows, segx):
    """The formal figure caption, also written to caption.txt for the slide."""
    segs, refs = m["segments"], m["refs"]
    node = lambda h: h.split(" · ")[0]
    if len(segs) > 1:
        others = [node(h) for h, _ in segs[1:]]
        top = (f"Top row: the {m['label']} {m['bgc']} locus, made of the antiSMASH region on {node(segs[0][0])} and the "
               f"{len(others)} contig{'s' if len(others) > 1 else ''} the gap rescue linked to it ({', '.join(others)}), drawn side by side. "
               "Their order and joins are not known, and the gaps between them are not to scale.")
        if any(o < 0 for o in m.get("segment_orientation", [])):
            top += " Contigs marked reversed are drawn as reverse complements, so that they face the top-ranked cluster."
    else:
        top = f"Top row: the {m['label']} {m['bgc']} antiSMASH region on {node(segs[0][0])}."
    cropped = [r.get("display_id", r["accession"]) for r, *_, c in rows if c]
    also = sum(len(r["also"]) for r in refs)
    sb = m.get("scale_kb")
    unit = "compound" if m["source"].startswith("MIBiG") else "organism"
    best = (f"its {len(refs)} best-matching {m['source']}" if len(refs) > 1
            else f"its best-matching {m['source'][:-1]}")  # "its 1 best-matching … regions" read wrong
    return (f"{m['label']} {m['bgc']} compared with {best}. {top} "
            f"Rows below: {m['source']} ranked by the number of locus genes they match, then by summed bitscore"
            + (f", with one row per {unit} (other entries for the same {unit} are named in the row label)" if also else "") + ". "
            f"Genes of the same color are matched protein pairs (DIAMOND blastp, ultra-sensitive; at least "
            f"{rc.DISCOVERY_MIN_ID:.0f}% identity over at least {rc.DISCOVERY_MIN_COV:.0f}% of the {m['label']} protein; one pair per gene "
            "within each cluster)."
            + (f" Only references matching at least {m['min_fraction']:.0%} as many locus genes as the top match are drawn."
               if m.get("min_fraction") else "")
            + " Gray genes have no match in that row. Each row label gives the number of matched locus genes "
            "and their median identity."
            + (f" Clusters much longer than the locus ({', '.join(cropped)}) are shown from the first to the last matched gene, "
               "plus two genes each side." if cropped else "")
            + (f" Scale bar: {sb:g} kb." if sb else ""))


def ribbon_top(m, out):
    """The locus against its top-ranked reference with ribbons (mamey.figures.locus_comparison, the deck's existing ribbon
    style), for the deck slide after the multi-reference one: the region track on top, the reference in the middle row,
    partner contigs (segments with matches) level on the bottom row. Pairs are this tool's one-to-one best hits. Returns
    the view used (rescue_locus_comparison.render_with_fallback), or None when no region gene matches."""
    if not m["refs"]:
        return None
    r = m["refs"][0]
    prots, segs = m["prots"], m["segments"]
    g = {x["i"]: x for x in r["genes"]}
    seg_of = {q: k for k, (_, qs) in enumerate(segs) for q in qs}
    pairs = r["pairs"]
    if not any(seg_of[q] == 0 for q, *_ in pairs):
        return None
    grp = {q: f"G{i}" for q, i, *_ in pairs}
    names = m.get("names") or {}
    def as_gene(q):
        p = prots[q]
        return {"id": p["tag"], "label": (names.get(p["tag"]) or "")[:32], "start": p["start"], "end": p["end"],
                "strand": p["strand"], "aa_sha256": rlc.aa_hash(p["aa"]), "group": grp.get(q, "")}
    def identity(qs):
        c = prots[qs[0]]["contig"]
        reg = next((x["identity"].split(" / ") for x in m["regions"] if x["contig"] == c), None)
        return ({"strain": m["label"], "contig": c, "region": reg[2], "bgc": reg[3]} if reg else
                {"strain": m["label"], "contig": c, "region": "no antiSMASH region", "bgc": "no BGC alias"})
    tracks = []
    for k, (head, qs) in enumerate(segs):
        if k and not any(seg_of[q] == k for q, *_ in pairs):
            continue
        ident = identity(qs)
        t = {"id": "core" if k == 0 else f"p{len(tracks)}", "kind": "bgc", "identity": ident, "orientation": 1,
             "label": f"{m['label']} {m['bgc']}" if k == 0 else f"{m['label']} {qs and prots[qs[0]]['contig'].split('_length')[0]} (another contig)",
             "genes": [as_gene(q) for q in qs]}
        best = max((x for x in pairs if seg_of[x[0]] == k), key=lambda x: x[3])
        t["anchor_gene"] = prots[best[0]]["tag"]
        tracks.append(t)
    core = tracks[0]
    core_pairs = [x for x in pairs if seg_of[x[0]] == 0]
    o = 1 if sum(b * (1 if prots[q]["strand"] == g[i]["strand"] else -1) for q, i, _, b in core_pairs) >= 0 else -1
    used = {f"G{i}" for _, i, *_ in pairs}
    ref = {"id": "ref", "kind": "reference", "orientation": o,
           "label": f"MIBiG {r['accession']}" + (f": {r['compound']}" if r["compound"] else ""),
           "identity": {"accession": r["accession"], "description": r["description"] if len(r["description"]) <= 80 else r["description"][:77].rstrip(" ,") + "..."},
           "genes": [{"id": x["id"], "label": rlc.short_gene_name(x["name"]), "start": x["start"], "end": x["end"], "strand": x["strand"],
                      "aa_sha256": rlc.aa_hash(x["aa"]), "group": f"G{x['i']}" if f"G{x['i']}" in used else ""} for x in r["genes"]]}
    ref["anchor_gene"] = g[max(core_pairs, key=lambda x: x[3])[1]]["id"]
    links = []
    tid = {}
    for t in tracks:
        for x in t["genes"]:
            tid[x["id"]] = t["id"]
    for t in tracks[1:]:  # a partner contig faces the reference as its own genes agree
        tp = [x for x in pairs if tid[prots[x[0]]["tag"]] == t["id"]]
        t["orientation"] = 1 if sum(b * (1 if prots[q]["strand"] * o == g[i]["strand"] else -1) for q, i, _, b in tp) >= 0 else -1
    for q, i, pid, b in pairs:
        links.append({"a": [tid[prots[q]["tag"]], prots[q]["tag"]], "b": ["ref", g[i]["id"]],
                      "evidence": "multi-reference best hit (DIAMOND blastp, ultra-sensitive)", "identity_pct": round(float(pid), 1)})
    tracks = [core, ref] + tracks[1:]
    rlc.level_partners(tracks, ref)
    rlc.sides(tracks, links)
    wide = {2: (13, 9), 3: (17, 10.5), 4: (19, 11)}[min(len(tracks), 4)]
    spec = {"schema": "locus-comparison-v1", "synthetic": False,
            "title": f"{m['label']} {m['bgc']} and {ref['label'][6:70]}",
            "display": {"label_rotation": 40, "font_size": wide[1], "width_in": wide[0], "axis_zero_track": "ref",
                        "axis_label": "kb along the MIBiG reference locus (0 = its first gene as drawn); same scale on every track"},
            "sources": [{"path": str(Path(m["zip"]).resolve()), "sha256": rlc.sha_file(m["zip"])},
                        {"path": r["gbk"], "sha256": rlc.sha_file(r["gbk"])}],
            "tracks": tracks, "links": links}
    return rlc.render_with_fallback(spec, Path(out) / "ribbon")


def write(m, out):
    out.mkdir(parents=True, exist_ok=True)
    prots = m["prots"]
    n_locus = sum(len(qs) for _, qs in m["segments"])
    with open(out / "references.tsv", "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["rank", "accession", "name", "locus_genes_matched", "locus_genes", "median_identity_pct", "bitscore_sum", "reference_genes", "same_compound_entries"])
        for k, r in enumerate(m["refs"], 1):
            w.writerow([k, r["accession"], r["compound"], len(r["pairs"]), n_locus,
                        f"{statistics.median(p for _, _, p, _ in r['pairs']):.1f}", f"{sum(b for *_, b in r['pairs']):.0f}", len(r["genes"]), ";".join(r["also"])])
    with open(out / "pairs.tsv", "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["accession", "locus_tag", "contig", "reference_gene_index", "reference_gene_name", "identity_pct", "bitscore"])
        for r in m["refs"]:
            g = {x["i"]: x for x in r["genes"]}
            for q, i, p, b in r["pairs"]:
                w.writerow([r["accession"], prots[q]["tag"], prots[q]["contig"], i, g[i]["name"], f"{p:.1f}", f"{b:.0f}"])
    rec = {"schema": "multi-reference-comparison-v1", "label": m["label"], "bgc": m["bgc"],
           "segments": [{"heading": h, "contig": prots[qs[0]]["contig"], "drawn_orientation": o, "genes": [prots[q]["tag"] for q in qs]}
                        for (h, qs), o in zip(m["segments"], m.get("segment_orientation", [1] * len(m["segments"])))],
           "thresholds": {"min_identity_pct": rc.DISCOVERY_MIN_ID, "min_query_coverage_pct": rc.DISCOVERY_MIN_COV,
                          "min_genes": rc.DISCOVERY_MIN_PROTEINS, "search": "DIAMOND blastp ultra-sensitive, max-target-seqs 500"},
           "diamond_hits": m["n_hits"], "text_overlaps": m.get("text_overlaps", []),
           "skipped_references": [{"accession": x, "why": w} for x, w in m.get("skipped", [])],
           "sources": [{"path": str(Path(p).resolve()), "sha256": rlc.sha_file(p)} for p in m["sources"]]
           + [{"path": r["gbk"], "sha256": rlc.sha_file(r["gbk"])} for r in m["refs"]]}
    (out / "receipt.json").write_text(json.dumps(rec, indent=1) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for a in ("--zip", "--label", "--out"):
        ap.add_argument(a, required=True)
    ap.add_argument("--rescue", help="<BGC>_vs_<ref> gap-rescue folder: adds its SUPPORTED partner contigs")
    ap.add_argument("--bgc", help="the BGC alias, when there is no gap-rescue folder")
    ap.add_argument("--mibig-db", help="MIBiG protein DIAMOND database (.dmnd)")
    ap.add_argument("--mibig-dir", help="MIBiG GenBank folder")
    ap.add_argument("--ref-gbk-dir", help="reference-genome antiSMASH region GenBank files, in place of MIBiG")
    ap.add_argument("--mibig-names")
    ap.add_argument("--gene-labels")
    ap.add_argument("--top", type=int, default=4)
    a = ap.parse_args()
    m = build(a.zip, a.label, Path(a.rescue) if a.rescue else None, a.mibig_db, a.mibig_dir, a.mibig_names, a.gene_labels,
              a.top, ref_gbk_dir=a.ref_gbk_dir, bgc=a.bgc)
    if not m["refs"]:
        sys.exit("no reference matches two or more locus genes")
    for band in (1.0, 1.3, 1.6, 1.9, 2.3):  # the smallest label band the rotated labels fit
        try:
            draw(m, Path(a.out), label_band=band)
            break
        except ValueError as e:
            if "title band" not in str(e):
                raise
    write(m, Path(a.out))
    emit(f"{len(m['refs'])} references drawn")

"""gap_rescue_locus_map.py — the clinker-style figure for tools/gap_directed_rescue.py.

Two rows. Top: the reference cluster, gene names above, matched genes coloured. Bottom: the genome, starting with the core
region's contig, then the contig holding the other piece of any CLEAR split gene (a red gap marker between the two pieces),
then contigs carrying a clear match to a named cluster gene, each cut to the part that carries it. Ribbons join each
reference gene to its match, shaded by protein identity; matched genes share the reference gene's colour, and each is
labelled below with its match and identity.

Which contigs are drawn:
- always the core contig and the contigs holding the pieces of a CLEAR split gene;
- otherwise a contig only when it carries a reciprocal-best clear match to a named cluster gene: a primary contig at 50%
  identity or more, a secondary contig at 35-50%. Secondary contigs are drawn after the primary ones and marked as such;
  real clusters with low homology to MIBiG sit in this range.
  A MIBiG entry names its cluster genes (valA, asuD3 ...) and leaves flanking genes under accession numbers (integrases,
  transposases, unknowns), so accession-named genes do not pull a contig into the figure. When fewer than three reference
  genes carry names, every gene counts as a cluster gene.
- never a contig whose find the partner checks call PARALOG_FAMILY or HOUSEKEEPING_CONTEXT; a lone find that passes
  them is drawn with the label "single-gene find";
- at most five such contigs, primary before secondary, best-matching first. Every other find stays in gap_rescue.tsv,
  and the footnote says how many were not drawn.

Claim-safety: homology is similarity, not product identity. A gap marker is two pieces of one reference protein at facing
contig ends, not a joined sequence.
"""
from __future__ import annotations

import re
import statistics

PRIMARY_MIN_ID, SECONDARY_MIN_ID = 50.0, 35.0
EXCLUDED_VERDICTS = {"PARALOG_FAMILY", "HOUSEKEEPING_CONTEXT"}
MAX_EXTRA = 5
SPLIT_GAP_KB, CUT_GAP_KB = 0.6, 1.8
GREY, LINE = "#D5D9DF", "#6B7280"
PAL = ["#56B4E9", "#D55E00", "#CC79A7", "#8FBC5A", "#009E73", "#F0E442", "#E69F00", "#0072B2", "#B07AA1", "#9C755F",
       "#76B7B2", "#EDC948", "#FF9DA7", "#59A14F", "#4E79A7", "#F28E2B", "#E15759", "#BAB0AC"]
ACCESSION = re.compile(r"^([A-Z]{1,6}_?\d{3,}(\.\d+)?|orf\d+[a-z]?)$")
ORF = re.compile(r"^orf\d+[a-z]?$", re.I)
MOBILE = re.compile(r"transposase|integrase|excisionase|excisonase|recombinase|resolvase|insertion element|insertion sequence", re.I)
BIOSYNTHETIC = {"biosynthetic", "biosynthetic-additional"}
H = 0.32


def _true(v) -> bool:
    return v is True or str(v) == "True"


def reference_genes(gbk_path) -> tuple[list[dict], float]:
    """Reference CDSs in record order (kb from the record start) and the record length in kb."""
    try:
        from Bio import SeqIO
    except ImportError as exc:
        raise RuntimeError("the locus map needs the optional Biopython package to read the reference GenBank file") from exc
    rec = next(SeqIO.parse(str(gbk_path), "genbank"))
    cds = sorted([c for c in rec.features if c.type == "CDS" and "translation" in c.qualifiers],
                 key=lambda c: int(c.location.start))
    out = []
    for i, c in enumerate(cds, 1):
        q = c.qualifiers
        out.append({"i": i, "name": (q.get("gene") or q.get("locus_tag") or q.get("protein_id") or [f"g{i}"])[0],
                    "product": q.get("product", [""])[0], "kind": q.get("gene_kind", [""])[0],
                    "s": int(c.location.start) / 1000,
                    "e": int(c.location.end) / 1000, "strand": c.location.strand or 1})
    return out, len(rec.seq) / 1000


def named(g: dict) -> bool:
    """A curated gene name (valC, asuD3, polH), not an accession, a locus tag or an orf number."""
    return not (ACCESSION.match(g["name"]) or ORF.match(g["name"]))


def cluster_genes(ref: list[dict]) -> set[int]:
    """Reference genes that may pull a contig into the figure: named genes; when a reference names fewer than three,
    the genes antiSMASH calls biosynthetic; never a mobile-element gene."""
    keep = {k for k, g in enumerate(ref) if named(g)}
    if len(keep) < 3:
        keep = {k for k, g in enumerate(ref) if g.get("kind") in BIOSYNTHETIC}
    if len(keep) < 3:
        keep = set(range(len(ref)))
    return {k for k in keep if not MOBILE.search(ref[k].get("product") or "")}


def short(g: dict) -> str:
    """A gene's label: its name with a capital (ValC), or a short product when the name is only an accession."""
    if named(g):
        return g["name"][:1].upper() + g["name"][1:]
    p = re.sub(r"\s+(protein|family protein)$", "", g["product"] or "", flags=re.I)
    return (p[:20] + "…") if len(p) > 21 else (p or g["name"])


def choose(ref, rows, splits, prots, core_contig):
    """-> (matches [(ref index, protein id, identity)], split info {ref index: (pid1, pid2, id1, id2)},
    ordered contig list, number of clear finds not drawn, secondary contigs)."""
    cluster = cluster_genes(ref)
    tag_to_pid = {p["tag"]: pid for pid, p in prots.items()}
    found, verdict = [], {}
    for k, r in enumerate(rows):
        if r.get("partner_verdict") in EXCLUDED_VERDICTS:
            continue  # a housekeeping gene or a paralog-family member never pulls a contig in (partner checks)
        if r.get("status") in ("PRESENT_IN_CORE", "MISSING_FOUND_CLEAR") and _true(r.get("reciprocal_best")):
            pid = r.get("best_protein") if r.get("best_protein") in prots else tag_to_pid.get(r.get("best_locus"))
            if pid:
                found.append((k, pid, float(r["best_identity_pct"])))
                verdict[pid] = r.get("partner_verdict") or ""
    split_info = {}
    for s in splits:
        if s.get("split_call") != "CLEAR":
            continue
        k = int(s["reference_gene"]) - 1
        p1, p2 = tag_to_pid.get(s["piece1_locus"]), tag_to_pid.get(s["piece2_locus"])
        if p1 and p2:
            split_info[k] = (p1, p2, float(s["piece1_identity_pct"]), float(s["piece2_identity_pct"]))
    found = [m for m in found if m[0] not in split_info]
    for k, (p1, p2, i1, i2) in split_info.items():
        found += [(k, p1, i1), (k, p2, i2)]
    fixed = [core_contig]
    for p1, p2, _, _ in split_info.values():
        for pid in (p1, p2):
            if prots[pid]["contig"] not in fixed:
                fixed.append(prots[pid]["contig"])
    best_by_contig = {}
    for k, pid, ident in found:
        c = prots[pid]["contig"]
        if c not in fixed and k in cluster and ident >= SECONDARY_MIN_ID:
            best_by_contig[c] = max(best_by_contig.get(c, 0), ident)
    extra = sorted(best_by_contig, key=lambda c: (best_by_contig[c] < PRIMARY_MIN_ID, -best_by_contig[c]))[:MAX_EXTRA]
    secondary = {c for c in extra if best_by_contig[c] < PRIMARY_MIN_ID}
    shown = set(fixed) | set(extra)
    drawn = [m for m in found if prots[m[1]]["contig"] in shown and
             (prots[m[1]]["contig"] in fixed or (m[0] in cluster and m[2] >= SECONDARY_MIN_ID))]
    not_drawn = len({(k, pid) for k, pid, _ in found} - {(k, pid) for k, pid, _ in drawn})
    ref_mid = lambda c: statistics.median((ref[k]["s"] + ref[k]["e"]) / 2 for k, pid, _ in drawn if prots[pid]["contig"] == c)
    order = fixed + sorted(extra, key=ref_mid)
    return drawn, split_info, order, not_drawn, secondary


def _arrow(ax, x0, x1, y, strand, fc):
    from matplotlib.patches import Polygon
    hd = min(0.5, (x1 - x0) * 0.35); h = H / 2
    pts = ([(x0, y - h), (x1 - hd, y - h), (x1, y), (x1 - hd, y + h), (x0, y + h)] if strand >= 0 else
           [(x1, y - h), (x0 + hd, y - h), (x0, y), (x0 + hd, y + h), (x1, y + h)])
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec="#333333", lw=0.6, zorder=3))


def draw_locus_map(ref_gbk, rows, splits, prots, regions, core, label, ref_name, out_png, out_pdf=None, pdf_pages=None):
    """rows, splits: gap_directed_rescue tables (dicts; strings or typed). prots, regions, core: its genome structures."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.patches import Polygon

    import logging
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"]
    ref, ref_len = reference_genes(ref_gbk)
    core_contig = core["contig"]
    drawn, split_info, order, not_drawn, secondary = choose(ref, rows, splits, prots, core_contig)
    verdict_of = {r.get("best_protein"): r.get("partner_verdict") for r in rows if r.get("best_protein")}
    single_gene = {c for c in order[1:] if c not in {prots[p]["contig"] for s in split_info.values() for p in s[:2]}
                   and all(verdict_of.get(pid) == "SINGLE_GENE" for k, pid, _ in drawn if prots[pid]["contig"] == c)}
    by_contig = {c: [m for m in drawn if prots[m[1]]["contig"] == c] for c in order}
    L = {c: next((p["contig_len"] for p in prots.values() if p["contig"] == c), 0) for c in order}
    seg = []
    for c in order:
        ms = by_contig[c]
        if c == core_contig:
            lo, hi = core["start"], core["end"]
            for _, pid, _ in ms:
                lo, hi = min(lo, prots[pid]["start"]), max(hi, prots[pid]["end"])
        else:
            lo = min(prots[pid]["start"] for _, pid, _ in ms); hi = max(prots[pid]["end"] for _, pid, _ in ms)
        lo, hi = (0, L[c]) if L[c] <= 12000 else (max(0, lo - 2500), min(L[c], hi + 2500))
        mids = [((prots[pid]["start"] + prots[pid]["end"]) / 2, (ref[k]["s"] + ref[k]["e"]) / 2) for k, pid, _ in ms]
        if len({a for a, _ in mids}) >= 2 and len({b for _, b in mids}) >= 2:
            flip = statistics.correlation([a for a, _ in mids], [b for _, b in mids]) < 0
        elif ms:
            k, pid, _ = ms[0]; flip = (prots[pid]["strand"] >= 0) != (ref[k]["strand"] >= 0)
        else:
            flip = False
        seg.append({"contig": c, "lo": lo, "hi": hi, "L": L[c], "flip": flip})
    # the two pieces of a split gene face each other across the gap
    pair_of = {}
    for k, (p1, p2, _, _) in split_info.items():
        a, b = prots[p1]["contig"], prots[p2]["contig"]
        ia = next(i for i, s in enumerate(seg) if s["contig"] == a); ib = next(i for i, s in enumerate(seg) if s["contig"] == b)
        if abs(ia - ib) != 1:
            continue
        pair_of[(min(ia, ib), max(ia, ib))] = k
        for i, pid, want_right in ((min(ia, ib), p1 if ia < ib else p2, True), (max(ia, ib), p2 if ia < ib else p1, False)):
            s = seg[i]; mid = (prots[pid]["start"] + prots[pid]["end"]) / 2
            if ((s["hi"] - mid < mid - s["lo"]) != s["flip"]) != want_right:
                s["flip"] = not s["flip"]
    x, xpos = 0.0, {}
    for i, s in enumerate(seg):
        if i:
            x += SPLIT_GAP_KB if (i - 1, i) in pair_of else CUT_GAP_KB
        s["x0"], s["w"] = x, (s["hi"] - s["lo"]) / 1000
        x += s["w"]
        for pid, p in prots.items():
            if p["contig"] == s["contig"] and p["end"] > s["lo"] and p["start"] < s["hi"]:
                a, b = (max(p["start"], s["lo"]) - s["lo"]) / 1000, (min(p["end"], s["hi"]) - s["lo"]) / 1000
                if s["flip"]:
                    a, b = s["w"] - b, s["w"] - a
                xpos[pid] = (s["x0"] + a, s["x0"] + b, -p["strand"] if s["flip"] else p["strand"])
    end = x
    ks = sorted({k for k, _, _ in drawn})
    colour = {k: PAL[j % len(PAL)] for j, k in enumerate(ks)}
    if drawn:
        v0 = min(ref[k]["s"] for k in ks); v1 = max(ref[k]["e"] for k in ks)
        m0 = min(xpos[pid][0] for _, pid, _ in drawn); m1 = max(xpos[pid][1] for _, pid, _ in drawn)
        off = (v0 + v1) / 2 - (m0 + m1) / 2
    else:
        off = 0.0
    off = max(off, -min(0.0, min(s["x0"] for s in seg)))
    xmin, xmax = min(0.0, off) - 0.6, max(ref_len, end + off) + 0.6
    Y_V, Y_A = 2.3, 0.0
    fig, ax = plt.subplots(figsize=(13.5, 6.2))
    ax.set_xlim(xmin, xmax); ax.set_ylim(-3.6, 3.7); ax.axis("off")
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    cmap = LinearSegmentedColormap.from_list("id", ["#EEF1F5", "#1F4E79"]); norm = Normalize(30, 100)
    for k, pid, ident in drawn:
        a, b, _ = xpos[pid]; g = ref[k]
        ax.add_patch(Polygon([(g["s"], Y_V - H / 2), (g["e"], Y_V - H / 2), (b + off, Y_A + H / 2), (a + off, Y_A + H / 2)],
                             closed=True, fc=cmap(norm(ident)), ec="none", alpha=0.85, zorder=1))
    ax.plot([0, ref_len], [Y_V, Y_V], color=LINE, lw=0.8, zorder=2)
    levels: list[list[tuple[float, float]]] = []
    for k, g in enumerate(ref):
        _arrow(ax, g["s"], g["e"], Y_V, g["strand"], colour.get(k, GREY))
        if not (named(g) or k in colour):
            continue
        mx = (g["s"] + g["e"]) / 2
        t = ax.text(mx, Y_V + H / 2 + 0.07, short(g) if k in colour else g["name"], ha="center", va="bottom", fontsize=7.5,
                    style="italic" if named(g) else "normal", weight="bold" if k in colour else "normal",
                    color="#111827" if k in colour else "#6B7280")
        bb = t.get_window_extent(rend).transformed(inv)
        pad = 0.15
        for lvl in range(6):
            if lvl == len(levels):
                levels.append([])
            if all(bb.x1 + pad < a or bb.x0 - pad > b for a, b in levels[lvl]):
                break
        levels[lvl].append((bb.x0, bb.x1))
        t.set_position((mx, Y_V + H / 2 + 0.07 + 0.22 * lvl))
    top = Y_V + H / 2 + 0.07 + 0.22 * max(1, len(levels)) + 0.35
    acc = str(ref_gbk).replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
    head = (f"{ref_name[:1].upper() + ref_name[1:]} cluster (MIBiG {acc}, {ref_len:.1f} kb)" if ref_name
            else f"Reference cluster {acc} ({ref_len:.1f} kb)")
    ax.text(0, top, head, fontsize=9, weight="bold", va="bottom")
    for i, s in enumerate(seg):
        a, b = s["x0"] + off, s["x0"] + s["w"] + off
        ax.plot([a, b], [Y_A, Y_A], color=LINE, lw=0.8, zorder=2)
        if i and (i - 1, i) in pair_of:
            ax.text(a - SPLIT_GAP_KB / 2, Y_A, "//", ha="center", va="center", fontsize=10, color="#B91C1C",
                    weight="bold", zorder=4)
            ax.text(a - SPLIT_GAP_KB / 2, Y_A + H / 2 + 0.12, "gap", ha="center", va="bottom", fontsize=7, color="#B91C1C")
        elif i:
            ax.text(a - CUT_GAP_KB / 2, Y_A, "//", ha="center", va="center", fontsize=10, color=LINE, zorder=4)
    for pid, (a, b, st) in xpos.items():
        k = next((k for k, q, _ in drawn if q == pid), None)
        _arrow(ax, a + off, b + off, Y_A, st, colour.get(k, GREY) if k is not None else GREY)
    # labels at 60 degrees are parallel lines: keep their anchors far enough apart that neighbours cannot touch
    line_px = 7 * fig.dpi / 72 * 1.3
    min_dx = abs(inv.transform((line_px / 0.866, 0))[0] - inv.transform((0, 0))[0])
    lows, done, last = [], set(), None
    for k, pid, ident in sorted(drawn, key=lambda m: xpos[m[1]][0]):
        a, b, _ = xpos[pid]
        if k in split_info:
            if k in done:
                continue
            done.add(k)
            p1, p2, i1, i2 = split_info[k]
            lx = sum((xpos[p][0] + xpos[p][1]) / 2 for p in (p1, p2)) / 2
            lab = f"{short(ref[k])}-like, split {i1:.0f}% | {i2:.0f}%"
        else:
            lx, lab = (a + b) / 2, f"{short(ref[k])}-like {ident:.0f}%"
        if last is not None and lx < last + min_dx:
            lx = last + min_dx
        last = lx
        t = ax.text(lx + off, Y_A - H / 2 - 0.08, lab, ha="right", va="top", fontsize=7, rotation=60,
                    rotation_mode="anchor", color="#111827")
        lows.append(t.get_window_extent(rend).transformed(inv).y0)
    ylab = min(lows + [Y_A - 0.5]) - 0.2
    seg_labels = []
    for s in seg:
        a, b = s["x0"] + off, s["x0"] + s["w"] + off
        node = re.match(r"(NODE_\d+)", s["contig"]); node = node.group(1) if node else s["contig"][:18]
        regs = [r for r in regions if r["contig"] == s["contig"] and r["end"] > s["lo"] and r["start"] < s["hi"]]
        alias = ", ".join(r["identity"].split(" / ")[-1] for r in regs if len(r["identity"].split(" / ")) == 4)
        extra = ", ".join(t for t in ("reversed" if s["flip"] else "", "part" if s["hi"] - s["lo"] < s["L"] else "") if t)
        who = "core, " + core["identity"].split(" / ")[-1] if s["contig"] == core_contig else (alias or "no antiSMASH region")
        if s["contig"] in secondary:
            who += "\nsecondary (35-50%)"
        if s["contig"] in single_gene:
            who += "\nsingle-gene find"
        t = ax.text((a + b) / 2, ylab, f"{node}{' (' + extra + ')' if extra else ''}\n{who}", ha="center", va="top",
                    fontsize=7.2, color="#374151", linespacing=1.3)
        bb = t.get_window_extent(rend).transformed(inv)
        seg_labels.append((t, bb.x0, bb.x1, bb.y1 - bb.y0, (a + b) / 2))
    step = max((h for *_, h, _ in seg_labels), default=0.5) + 0.12
    placed = []
    for t, x0, x1, h, cx in seg_labels:  # a label that would touch its neighbour drops one level
        lvl = 0
        while any(l == lvl and not (x1 + 0.3 < p0 or x0 - 0.3 > p1) for p0, p1, l in placed):
            lvl += 1
        placed.append((x0, x1, lvl))
        t.set_position((cx, ylab - lvl * step))
    ax.text(xmin + 0.1, Y_A + 0.62, label, fontsize=9, weight="bold", va="center")
    n_core = sum(1 for r in rows if r.get("status") == "PRESENT_IN_CORE")
    n_clear = sum(1 for r in rows if r.get("status") == "MISSING_FOUND_CLEAR")
    note = f"{n_core} of {len(rows)} reference genes in {core['identity']}; {n_clear} found clearly elsewhere"
    set_aside = sum(1 for r in rows if r.get("partner_verdict") in EXCLUDED_VERDICTS)
    if set_aside:
        note += f"; {set_aside} set aside by partner checks (housekeeping or paralog family)"
    if not_drawn:
        note += (f"; {not_drawn} more not drawn (flanking or unnamed reference genes, under {SECONDARY_MIN_ID:.0f}% identity, "
                 f"or beyond {MAX_EXTRA} contigs; see gap_rescue.tsv)")
    ybot = ylab - (max((l for *_, l in placed), default=0) + 1) * step - 0.05
    ax.text(xmin + 0.1, ybot, note, fontsize=6.8, color="#4B5563", va="top")
    ybar = ybot - 0.55
    ax.plot([xmax - 5.6, xmax - 0.6], [ybar, ybar], color="#111827", lw=1.2)
    ax.text(xmax - 3.1, ybar - 0.07, "5 kb", ha="center", va="top", fontsize=7.5)
    ax.set_ylim(ybar - 0.75, top + 0.5)
    cax = ax.inset_axes([xmin + 0.1, ybar - 0.07, 0.2 * (xmax - xmin), 0.14], transform=ax.transData)
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal")
    cb.set_label("Protein identity (%)", fontsize=7.5, labelpad=2); cb.ax.tick_params(labelsize=7)
    fig.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white")
    if out_pdf:
        fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
    if pdf_pages is not None:
        pdf_pages.savefig(fig, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {"contigs_drawn": [s["contig"] for s in seg], "not_drawn": not_drawn}

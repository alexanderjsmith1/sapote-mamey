#!/usr/bin/env python3
"""gap_directed_rescue.py — what a core region's reference cluster has and the core lacks, looked for across the genome.

Reader-side and NON-SCORING. Start from one antiSMASH region (the core) and a reference cluster GenBank file (usually
MIBiG). Every reference protein is compared with every protein of the genome, not only those inside antiSMASH regions:
the missing part of a pathway split by the assembly often sits on a short contig antiSMASH did not flag, because it
holds tailoring genes and no core gene.

For each reference gene:
- PRESENT_IN_CORE: its best match inside the core region reaches 30% identity over 50% of the reference protein.
- MISSING_FOUND_CLEAR: missing from the core, and the genome's best match elsewhere beats the next candidate's
  bitscore by 20% or more (or has no rival) at >= 35% identity. Paralog families (halogenases, glycosyltransferases,
  methyltransferases) give several candidates; only a clear margin picks one.
- MISSING_FOUND_AMBIGUOUS, MISSING_NOT_FOUND.

Partners are other contigs carrying >= 2 clear finds. A partner is reported CONCENTRATED when the two leading partners
hold >= 60% of all clear finds (a missing piece puts the genes in one or two places; paralogs scatter them), and
SPLIT_PLAUSIBLE when the core runs to a contig end, or the partner contig is under 30 kb, or its region touches a
contig end. Reference genes are split by the reference's own antiSMASH gene_kind: only biosynthetic and
biosynthetic-additional finds count toward "biosynthetic clear finds" (some MIBiG entries carry flanking housekeeping
genes).

Outputs: gap_rescue.tsv (one row per reference gene), gap_rescue_partners.tsv, gap_rescue_receipt.json and
gap_rescue.png: the reference in the middle, each contig above or below it (the side where its ribbons cross no other
contig), contig ends as heavy bars, matched genes numbered by reference gene, and the full gene table beneath.

Claim-safety: homology is similarity, not product identity; a rescue candidate joins no contigs. A fragmented assembly
is never joined with full confidence.

CLI:
  python tools/gap_directed_rescue.py --zip <antiSMASH.zip> --label <strain> --core <contig>.regionNNN \
         --reference <MIBiG.gbk> [--reference-name "AT2433-A1"] --out <dir> [--hits hits.tsv] [--threads 4]
--hits: precomputed DIAMOND/BLAST tabular (qseqid = reference gene id g001..., sseqid = genome protein id from
gap_rescue_proteins.faa, pident, qcovhsp, bitscore), for runs without DIAMOND.
"""
from __future__ import annotations

import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import io
import json
import re
import statistics
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

try:
    from mamey import parsers
    from mamey.csv_safety import SafeWriter
    from mamey.path_safety import assert_output_outside_bundle
except ImportError:  # bare-script run: bundle root is one level up
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from mamey import parsers
    from mamey.csv_safety import SafeWriter
    from mamey.path_safety import assert_output_outside_bundle

MIN_ID, MIN_COV, CLEAR_ID, CLEAR_RATIO = 30.0, 50.0, 35.0, 1.2
PARTNER_MIN, CONCENTRATION, SHORT_CONTIG = 2, 0.6, 30000
BIOSYNTHETIC_KINDS = {"biosynthetic", "biosynthetic-additional"}
COLS = ["#2f6db3", "#e07b28", "#3a9e5a"]
TABLE_COLS = ["reference_gene", "name", "reference_product", "reference_len_aa", "reference_gene_kind", "modular_pks", "status",
              "best_identity_pct", "best_coverage_pct", "reciprocal_best", "best_protein", "best_locus", "best_len_aa",
              "best_contig",
              "best_region_identity", "rivals", "bitscore_ratio_to_second"]
PARTNER_COLS = ["partner_contig", "partner_identity", "contig_length", "clear_finds", "biosynthetic_clear_finds",
                "genes", "concentrated", "split_plausible"]


def _say(*lines: str) -> None:
    emit(*lines, sep="\n")


def _seqio():
    return parsers._require_seqio()


def load_reference(gbk: Path) -> tuple[list[dict], str]:
    rec = next(_seqio().parse(str(gbk), "genbank"))
    cds = sorted([c for c in rec.features if c.type == "CDS" and "translation" in c.qualifiers],
                 key=lambda c: int(c.location.start))
    ks = [int(f.location.start) for f in rec.features if f.type == "aSDomain" and f.qualifiers.get("aSDomain") == ["PKS_KS"]]
    genes = []
    for i, c in enumerate(cds, 1):
        q = c.qualifiers
        n_ks = sum(1 for k in ks if int(c.location.start) <= k < int(c.location.end))
        genes.append({"id": f"g{i:03d}", "i": i, "start": int(c.location.start), "end": int(c.location.end), "ks": n_ks,
                      "strand": c.location.strand or 1,
                      "name": (q.get("gene") or q.get("locus_tag") or q.get("protein_id") or [f"g{i}"])[0],
                      "product": q.get("product", [""])[0], "kind": q.get("gene_kind", ["other"])[0],
                      "aa": q["translation"][0]})
    return genes, rec.description


def load_genome(zip_path: Path, label: str) -> tuple[dict, list]:
    """Every CDS of the whole-genome GenBank in the ZIP, and the antiSMASH regions with their full identities."""
    names = [n for n in zipfile.ZipFile(zip_path).namelist()
             if n.endswith(".gbk") and ".region" not in n and "__MACOSX" not in n and not Path(n).name.startswith("._")]
    if not names:
        raise SystemExit("no whole-genome GenBank file in the ZIP")
    # the engine parser is the bound source for contig names and aliases; the whole-genome GenBank can carry a
    # mangled record name (a SPAdes coverage suffix with a digit dropped), so regions are matched on
    # region number and coordinates, not on the name
    parsed = [(int(re.sub(r"\D", "", b.antismash_region or "0") or 0), int(b.start or 0), int(b.end or 0), b)
              for b in parsers.parse_bgcs_from_zip(zip_path, json_mode="off")]
    prots, regions = {}, []
    text = zipfile.ZipFile(zip_path).read(names[0]).decode(errors="replace")
    for rec in _seqio().parse(io.StringIO(text), "genbank"):
        dm = re.search(r"(\S+?),? whole genome", rec.description or "")
        node = dm.group(1) if dm and dm.group(1) not in rec.id and rec.id not in dm.group(1) else ""
        shown = f"{node} = {rec.id}" if node else rec.id
        for f in rec.features:
            if f.type == "region":
                n = int(f.qualifiers.get("region_number", ["0"])[0])
                s0, e0 = int(f.location.start), int(f.location.end)
                hits = [b for k, s, e, b in parsed if k == n and abs(s - s0) <= 1 and abs(e - e0) <= 1
                        and (b.contig[:12] == rec.id[:12])]
                b = hits[0] if len(hits) == 1 else None
                node = f"{shown.split(' = ')[0]} = " if " = " in shown else ""
                name = f"{node}{b.contig}" if b else shown
                regions.append({"contig": rec.id, "start": s0, "end": e0, "n": n,
                                "edge": f.qualifiers.get("contig_edge", [""])[0],
                                "identity": f"{label} / {name} / region{n:03d} / {b.bgc_id if b else 'IDENTITY_HOLD'}"})
            elif f.type == "CDS" and "translation" in f.qualifiers:
                pid = f"q{len(prots) + 1:06d}"
                prots[pid] = {"contig": rec.id, "shown": f"{label} / {shown}", "start": int(f.location.start),
                              "end": int(f.location.end), "strand": f.location.strand or 1,
                              "tag": f.qualifiers.get("locus_tag", [pid])[0], "aa": f.qualifiers["translation"][0],
                              "contig_len": len(rec.seq)}
    return prots, regions


def region_of(p: dict, regions: list) -> dict | None:
    return next((r for r in regions if r["contig"] == p["contig"] and r["start"] < p["end"] and r["end"] > p["start"]),
                None)


def run_diamond(ref: list, prots: dict, threads: int) -> list[dict]:
    from mamey import diamond_align
    with tempfile.TemporaryDirectory() as td:
        qf, rf = Path(td, "ref.faa"), Path(td, "genome.faa")
        qf.write_text("".join(f">{g['id']}\n{g['aa']}\n" for g in ref))
        rf.write_text("".join(f">{k}\n{v['aa']}\n" for k, v in prots.items()))
        res = diamond_align.align_fasta(str(qf), str(rf), threads=threads)
    if not res.get("ok"):
        raise RuntimeError(f"DIAMOND unavailable: {res.get('reason')}; pass --hits with a precomputed table")
    return res["hits"]


def read_hits(path: Path) -> list[dict]:
    out = []
    for line in open(path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 5:
            out.append({"qseqid": p[0], "sseqid": p[1], "pident": float(p[2]), "qcovhsp": float(p[3]),
                        "bitscore": float(p[4])})
    return out


def search(ref, prots, regions, hits, core):
    """-> rows (one per reference gene) and partner rows."""
    by_q = {}
    for h in hits:
        if float(h["pident"]) >= MIN_ID and float(h["qcovhsp"]) >= MIN_COV and h["sseqid"] in prots:
            by_q.setdefault(h["qseqid"], []).append(h)
    for q, values in by_q.items():
        unique = {}
        for h in sorted(values, key=lambda h: (-float(h["bitscore"]), -float(h["pident"]),
                                              -float(h["qcovhsp"]), h["sseqid"])):
            unique.setdefault(h["sseqid"], h)
        by_q[q] = list(unique.values())
    in_core = lambda p: p["contig"] == core["contig"] and p["start"] < core["end"] and p["end"] > core["start"]
    rows = []
    for g in ref:
        hs = by_q.get(g["id"], [])
        row = {"reference_gene": g["i"], "name": g["name"], "reference_product": g["product"],
               "reference_len_aa": len(g["aa"]), "reference_gene_kind": g["kind"], "modular_pks": g["ks"] > 0,
               "status": "MISSING_NOT_FOUND"}
        inside = [h for h in hs if in_core(prots[h["sseqid"]])]
        outside = [h for h in hs if not in_core(prots[h["sseqid"]])]
        best = None
        if inside:
            best, row["status"] = inside[0], "PRESENT_IN_CORE"
        elif outside:
            best = outside[0]
            second = outside[1] if len(outside) > 1 else None
            clear = float(best["pident"]) >= CLEAR_ID and (second is None or
                                                          float(best["bitscore"]) >= CLEAR_RATIO * float(second["bitscore"]))
            row["status"] = "MISSING_FOUND_CLEAR" if clear else "MISSING_FOUND_AMBIGUOUS"
            row["rivals"] = len(outside) - 1
            row["bitscore_ratio_to_second"] = round(float(best["bitscore"]) / float(second["bitscore"]), 2) if second else ""
        if best:
            p = prots[best["sseqid"]]
            reg = region_of(p, regions)
            row.update(best_identity_pct=round(float(best["pident"]), 1), best_coverage_pct=round(float(best["qcovhsp"])),
                       best_protein=best["sseqid"], best_locus=p["tag"], best_len_aa=len(p["aa"]), best_contig=p["contig"],
                       best_region_identity=reg["identity"] if reg else f"{p['shown']} (no antiSMASH region)")
        rows.append(row)
    # modular PKS genes are left out: their best whole-gene match follows module paralogy (use KS placement instead)
    # reciprocal best: of the reference genes whose best match is one genome protein, only the highest-identity one is
    # that protein's own match. The others are cross-hits (typically paralogous PKS modules) and get no ribbon.
    top_for = {}
    for r in rows:
        if r.get("best_protein"):
            b = top_for.get(r["best_protein"])
            if b is None or r["best_identity_pct"] > b["best_identity_pct"]:
                top_for[r["best_protein"]] = r
    for r in rows:
        if r.get("best_protein"):
            r["reciprocal_best"] = top_for[r["best_protein"]] is r
    clear = [r for r in rows if r["status"] == "MISSING_FOUND_CLEAR" and r["best_contig"] != core["contig"]
             and not r["modular_pks"] and r.get("reciprocal_best")]
    total_clear = sum(1 for r in rows if r["status"] == "MISSING_FOUND_CLEAR"
                      and not r["modular_pks"] and r.get("reciprocal_best"))
    by_c = Counter(r["best_contig"] for r in clear)
    top = [c for c, _ in by_c.most_common(2)]
    concentrated = total_clear and sum(by_c[c] for c in top) / total_clear >= CONCENTRATION
    core_edge = core["edge"] in ("True", "true", "Edge")
    partners = []
    for c, n in by_c.most_common():
        if n < PARTNER_MIN:
            continue
        genes = [r for r in clear if r["best_contig"] == c]
        p0 = prots[genes[0]["best_protein"]]
        regs = [region_of(prots[r["best_protein"]], regions) for r in genes]
        partners.append({"partner_contig": c, "partner_identity": genes[0]["best_region_identity"],
                         "contig_length": p0["contig_len"], "clear_finds": n,
                         "biosynthetic_clear_finds": sum(1 for r in genes if r["reference_gene_kind"] in BIOSYNTHETIC_KINDS),
                         "genes": "; ".join(f"{r['reference_gene']} {r['name']} ({r['best_identity_pct']}%)" for r in genes),
                         "concentrated": bool(concentrated and c in top),
                         "split_plausible": bool(core_edge or p0["contig_len"] < SHORT_CONTIG
                                                 or any(r and r["edge"] in ("True", "true") for r in regs))})
    return rows, partners


def _arrow(ax, s, e, strand, y, fc, h=0.36):
    from matplotlib.patches import FancyArrow
    L = e - s
    head = min(L * 0.35, 900)
    fwd = strand >= 0
    ax.add_patch(FancyArrow(s if fwd else e, y, (L - head) * (1 if fwd else -1), 0, width=h, head_width=h * 1.5,
                            head_length=head, length_includes_head=False, fc=fc, ec="#333", lw=0.5))


def draw(ref, rows, partners, prots, regions, core, label, ref_name, ref_acc, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Polygon
    r0 = min(g["start"] for g in ref)
    rpos = [(g["start"] - r0, g["end"] - r0, g["strand"]) for g in ref]
    rspan = max(e for _, e, _ in rpos)
    contigs = [core["contig"]] + [p["partner_contig"] for p in partners[:2]]
    matches = {c: [] for c in contigs}
    for i, r in enumerate(rows):
        if (r["status"] in ("PRESENT_IN_CORE", "MISSING_FOUND_CLEAR") and r.get("best_contig") in matches
                and r.get("reciprocal_best")):
            matches[r["best_contig"]].append((i, prots[r["best_protein"]], float(r["best_identity_pct"])))
    contigs = [c for c in contigs if matches[c]]
    span_of = {c: (min(rpos[i][0] for i, _, _ in m), max(rpos[i][1] for i, _, _ in m)) for c, m in matches.items() if m}
    sides, row = {"above": [], "below": []}, {}
    for c in contigs:
        lo, hi = span_of[c]
        cost = {s: sum(max(0, min(hi, span_of[o][1]) - max(lo, span_of[o][0])) for o in sides[s]) for s in sides}
        side = min(sides, key=lambda s: (cost[s], len(sides[s])))
        sides[side].append(c)
        row[c] = len(sides[side]) * (1 if side == "above" else -1)
    H = 4.0 + 1.25 * len(contigs) + 0.155 * len(rows)
    fig = plt.figure(figsize=(14, H))
    ax = fig.add_axes([0.05, 1 - (1.0 + 1.25 * len(contigs) + 0.6) / H, 0.9, (1.25 * len(contigs) + 0.9) / H])
    yref = 1.25 * len(sides["below"]) + 0.2
    ax.set_ylim(-0.9, yref + 1.25 * len(sides["above"]) + 0.7)
    ax.axis("off")
    for i, (s, e, st) in enumerate(rpos):
        _arrow(ax, s, e, st, yref, "#d9d9d9")
        ax.text((s + e) / 2, yref, str(i + 1), ha="center", va="center", fontsize=6.3)
    labels = [(yref, f"{ref_acc}\n(reference)", "k")]
    legend = [Patch(fc="#d9d9d9", ec="#333", label=f"{ref_acc}: {ref_name[:70]}")]
    xmin, xmax = 0, rspan
    for k, c in enumerate(contigs):
        y = yref + 1.25 * row[c]
        ms = matches[c]
        L = ms[0][1]["contig_len"]
        pm = [(p["start"] + p["end"]) / 2 for _, p, _ in ms]
        rm = [(rpos[i][0] + rpos[i][1]) / 2 for i, _, _ in ms]
        corr = statistics.correlation(pm, rm) if len(ms) >= 2 and len(set(pm)) > 1 and len(set(rm)) > 1 else 1
        flip = corr < 0
        tx = (lambda x: -x) if flip else (lambda x: x)
        shift = statistics.median(r - tx(p) for r, p in zip(rm, pm))
        X = lambda x: tx(x) + shift
        lo = max(0, min(p["start"] for _, p, _ in ms) - 3000)
        hi = min(L, max(p["end"] for _, p, _ in ms) + 3000)
        ax.plot(sorted([X(lo), X(hi)]), [y, y], color="#555", lw=1, zorder=0)
        for end in (0, L):
            if lo <= end <= hi:
                ax.plot([X(end), X(end)], [y - 0.32, y + 0.32], color="k", lw=3)
        matched = {id(p) for _, p, _ in ms}
        for p in prots.values():
            if p["contig"] == c and p["end"] > lo and p["start"] < hi:
                s, e = sorted((X(p["start"]), X(p["end"])))
                _arrow(ax, s, e, -p["strand"] if flip else p["strand"], y, COLS[k] if id(p) in matched else "#ffffff", h=0.3)
        nums = {}
        for i, p, _ in ms:
            nums.setdefault(id(p), (p, []))[1].append(i + 1)
        for p, idx in nums.values():
            s, e = sorted((X(p["start"]), X(p["end"])))
            ax.text((s + e) / 2, y, ",".join(map(str, idx)), ha="center", va="center", fontsize=6.3, color="white",
                    fontweight="bold")
            if any(ref[i - 1]["ks"] for i in idx):
                ax.add_patch(plt.Rectangle((s, y - 0.15), e - s, 0.3, fill=False, hatch="////", ec="white", lw=0))
        for i, p, pid in ms:
            s, e = sorted((X(p["start"]), X(p["end"])))
            ry, cy = (yref + 0.28, y - 0.22) if y > yref else (yref - 0.28, y + 0.22)
            alpha = (0.18 + 0.6 * max(0, min(1, (pid - 30) / 70))) * 0.7
            ax.add_patch(Polygon([(rpos[i][0], ry), (rpos[i][1], ry), (e, cy), (s, cy)], closed=True, fc=COLS[k],
                                 ec="none", alpha=alpha, zorder=-1))
        xmin, xmax = min(xmin, X(lo), X(hi)), max(xmax, X(lo), X(hi))
        reg = region_of(ms[0][1], regions) if k == 0 else next((region_of(p, regions) for _, p, _ in ms
                                                                if region_of(p, regions)), None)
        name = reg["identity"] if reg else f"{ms[0][1]['shown']} (no antiSMASH region)"
        role = "core" if k == 0 else f"partner {k}"
        labels.append((y, role, COLS[k]))
        legend.append(Patch(fc=COLS[k], ec="#333", label=f"{role}: {name}; contig {L / 1000:.1f} kb; {len(ms)} reference "
                                                         f"genes" + ("; drawn reversed" if flip else "")))
    ax.set_xlim(xmin - 0.13 * (xmax - xmin), xmax + 0.02 * (xmax - xmin))
    for y, lab, col in labels:
        ax.text(xmin - 0.035 * (xmax - xmin), y, lab, ha="right", va="center", fontsize=8, color=col, fontweight="bold")
    ax.plot([xmin, xmin + 5000], [-0.75, -0.75], color="k", lw=1)
    ax.text(xmin + 2500, -0.82, "5 kb", ha="center", va="top", fontsize=7)
    legend += [Patch(fc="#ffffff", ec="#333", label="gene on the contig with no match to this reference"),
               Patch(fc="k", ec="k", label="heavy bar: contig end (assembly break)"),
               Patch(fc="#999", ec="none", alpha=0.5, label="ribbon: best match, darker = higher identity (30-100%); "
                                                            "numbers = reference gene"),
               Patch(fc="#ffffff", ec="#ffffff", label="ribbons join reciprocal best matches only; a reference gene whose best "
                                                         "match is taken by a closer reference gene is a cross-hit (table)"),
               Patch(fc="#888", ec="#333", hatch="////", label="modular PKS gene: best match follows module paralogy; "
                                                              "order these with KS placement (tools/ks_module_placement.py)")]
    fig.legend(handles=legend, loc="upper left", bbox_to_anchor=(0.05, 1 - (1.0 + 1.25 * len(contigs) + 0.7) / H),
               fontsize=7.5, frameon=False)
    fig.suptitle(f"{label}: pieces matching {ref_acc} ({ref_name[:50]}) on {len(contigs)} contigs",
                 x=0.05, ha="left", fontsize=10)
    tab = fig.add_axes([0.05, 0.01, 0.9, (0.155 * len(rows) + 0.3) / H])
    tab.axis("off")
    who = {c: ("core" if k == 0 else f"partner {k}") for k, c in enumerate(contigs)}
    lines = ["#   ref gene      reference product                     ref aa  kind                     match      "
             "AS locus       AS aa   % id  % cov  contig"]
    st_name = {"PRESENT_IN_CORE": "in core", "MISSING_FOUND_CLEAR": "clear", "MISSING_FOUND_AMBIGUOUS": "ambiguous",
               "MISSING_NOT_FOUND": "none"}
    for r in rows:
        st = st_name[r["status"]]
        lines.append(f"{r['reference_gene']:<3} {r['name'][:13]:<13} {r['reference_product'][:37]:<37} "
                     f"{r['reference_len_aa']:>6}  {r['reference_gene_kind'][:23]:<24} {st:<10} "
                     f"{str(r.get('best_locus', ''))[:14]:<14} {str(r.get('best_len_aa', '')):>5}  "
                     f"{str(r.get('best_identity_pct', '')):>4}  {str(r.get('best_coverage_pct', '')):>5}  "
                     f"{who.get(r.get('best_contig', ''), str(r.get('best_contig', ''))[:40]) if st != 'none' else ''}"
                     f"{'  (cross-hit; no ribbon)' if r.get('best_protein') and not r.get('reciprocal_best') else ''}")
    tab.text(0, 1, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=6.6)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--zip", required=True, type=Path)
    ap.add_argument("--label", required=True)
    ap.add_argument("--core", required=True, help="core region as <contig>.regionNNN")
    ap.add_argument("--reference", required=True, type=Path, help="reference cluster GenBank file (MIBiG)")
    ap.add_argument("--reference-name", default="")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--hits", type=Path)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--no-figure", action="store_true")
    a = ap.parse_args(argv)
    assert_output_outside_bundle(a.out, __file__)
    ref, desc = load_reference(a.reference)
    prots, regions = load_genome(a.zip, a.label)
    m = re.match(r"(.+)\.region(\d+)$", a.core)
    if not m:
        raise SystemExit("--core must look like <contig>.regionNNN")
    matches = [r for r in regions if r["n"] == int(m.group(2)) and
               (r["contig"] == m.group(1) or
                (len(r["identity"].split(" / ")) == 4 and
                 m.group(1) in r["identity"].split(" / ")[1].split(" = ")))]
    if len(matches) != 1:
        raise SystemExit(f"core region {a.core} not found or ambiguous; use an exact bound contig or node alias")
    core = matches[0]
    parts = core["identity"].split(" / ")
    if len(parts) != 4 or any(not x.strip() or x in {"None", "?", "IDENTITY_HOLD"} for x in parts):
        raise SystemExit(f"core region {a.core} has an unresolved identity")
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "gap_rescue_proteins.faa").write_text("".join(f">{k}\n{v['aa']}\n" for k, v in prots.items()))
    hits = read_hits(a.hits) if a.hits else run_diamond(ref, prots, a.threads)
    rows, partners = search(ref, prots, regions, hits, core)
    with open(a.out / "gap_rescue.tsv", "w", newline="") as fh:
        w = SafeWriter(fh, delimiter="\t")
        w.writerow(TABLE_COLS)
        for r in rows:
            w.writerow([r.get(c, "") for c in TABLE_COLS])
    with open(a.out / "gap_rescue_partners.tsv", "w", newline="") as fh:
        w = SafeWriter(fh, delimiter="\t")
        w.writerow(PARTNER_COLS)
        for p in partners:
            w.writerow([p[c] for c in PARTNER_COLS])
    st = Counter(r["status"] for r in rows)
    name = a.reference_name or desc
    receipt = {"tool": "gap_directed_rescue", "label": a.label, "core": core["identity"], "reference": a.reference.name,
               "reference_name": name, "reference_genes": len(rows), **{k.lower(): st[k] for k in
               ("PRESENT_IN_CORE", "MISSING_FOUND_CLEAR", "MISSING_FOUND_AMBIGUOUS", "MISSING_NOT_FOUND")},
               "partners": partners, "homology": "precomputed hits" if a.hits else "DIAMOND",
               "non_claims": ["homology is similarity, not product identity",
                              "a partner contig is a candidate missing piece; no contigs are joined",
                              "a fragmented assembly is never joined with full confidence"]}
    (a.out / "gap_rescue_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if not a.no_figure:
        draw(ref, rows, partners, prots, regions, core, a.label, name, a.reference.stem, a.out / "gap_rescue.png")
    _say(f"[gap_directed_rescue] {core['identity']} vs {a.reference.stem}: {st['PRESENT_IN_CORE']} of {len(rows)} "
         f"reference genes in the core; {st['MISSING_FOUND_CLEAR']} missing and found clearly elsewhere; partners: "
         + ("; ".join(f"{p['partner_identity']} ({p['clear_finds']})" for p in partners) or "none") + f" -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

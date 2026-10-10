#!/usr/bin/env python3
"""gene_synteny_map.py — one genome against one reference cluster, gene by gene, with the ordered blocks.

Reader-side and NON-SCORING. For each gene of a reference cluster (a MIBiG GenBank file) it asks: does the genome carry a
candidate match, at what identity and coverage, on which contig, and do neighbouring reference genes find neighbouring
matches on one contig, in the reference's order? It writes a figure (reference drawn to scale, a heat row of best
identity, a contig row, and the full table beneath), a TSV and a JSON receipt.

Modular PKS genes are handled apart. Their modules resemble one another, so the "best whole-gene match" of a giant PKS
gene often goes to whichever contig carries the most modules, not to the contig that holds that gene's modules. With a
placement table from `tools/ks_module_placement.py place`, a PKS gene is assigned the contigs whose KS placed on its
modules. Without one, its best match is shown hatched and labelled "paralogous modules; see KS placement".

Homology comes from DIAMOND (`mamey.diamond_align`, optional) or from a precomputed DIAMOND/BLAST tabular file with the
columns qseqid sseqid pident length qlen slen qcovhsp scovhsp evalue bitscore qstart qend sstart send (--hits).

Claim-safety: identity is similarity, not product identity; placement under the reference orders no contigs and joins
nothing; a similar cluster is a class-level candidate.

CLI:
  python tools/gene_synteny_map.py --zip <antiSMASH.zip> --label <strain> --reference <MIBiG.gbk> \
         --reference-name "nystatin A1" --out <dir> [--placement placement.tsv] [--hits hits.tsv] [--threads 4]
"""
from __future__ import annotations

import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
import io
import json
import re
import sys
import tempfile
import zipfile
from collections import defaultdict
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

MIN_ID = 40.0          # a candidate match
STRONG_ID = 60.0       # pieces counted in the coverage fill
HIT_COLS = ["qseqid", "sseqid", "pident", "length", "qlen", "slen", "qcovhsp", "scovhsp", "evalue", "bitscore",
            "qstart", "qend", "sstart", "send"]
TABLE_COLS = ["reference_gene", "name", "reference_annotation", "reference_len_aa", "modular_pks", "assigned_by",
              "best_identity_pct", "best_coverage_of_gene_pct", "coverage_by_matches_ge60pct", "contig_tag",
              "region_identity", "best_locus", "synteny_block"]


def _seqio():
    return parsers._require_seqio()


def _say(*lines: str) -> None:
    emit(*lines, sep="\n")


def load_reference(gbk: Path) -> list[dict]:
    """Reference genes in record order, with role text and the KS module numbers each gene holds."""
    rec = next(_seqio().parse(str(gbk), "genbank"))
    cds = sorted([c for c in rec.features if c.type == "CDS" and "translation" in c.qualifiers],
                 key=lambda c: int(c.location.start))
    ks = sorted([f for f in rec.features if f.type == "aSDomain" and f.qualifiers.get("aSDomain") == ["PKS_KS"]],
                key=lambda f: int(f.location.start))
    genes = []
    for i, c in enumerate(cds, 1):
        q = c.qualifiers
        s, e = int(c.location.start), int(c.location.end)
        modules = [k for k, f in enumerate(ks, 1) if s <= int(f.location.start) < e]
        genes.append({"i": i, "id": f"g{i:03d}", "s": s / 1000, "e": e / 1000,
                      "strand": "+" if c.location.strand == 1 else "-", "len": len(q["translation"][0]),
                      "name": q.get("gene", [""])[0] or q.get("product", [""])[0] or f"g{i}",
                      "desc": (q.get("note", [""])[0] or q.get("function", [""])[0] or q.get("product", [""])[0])[:58],
                      "role_text": " ".join(q.get(k, [""])[0] for k in ("note", "function", "gene_functions",
                                                                         "sec_met_domain", "product")),
                      "modules": modules, "translation": q["translation"][0]})
    return genes, len(rec.seq) / 1000


def load_genome(zip_path: Path, label: str) -> tuple[dict, dict]:
    """Every protein of every antiSMASH region: {pid: info}; and {locus_tag: pid}. Identities come from the engine
    parser (contig, region, alias), with the submitter's node name from the DEFINITION line when it differs."""
    bgcs = {Path(b.source_gbk).name: b for b in parsers.parse_bgcs_from_zip(zip_path, json_mode="off")}
    SeqIO = _seqio()
    prots, by_tag = {}, {}
    with zipfile.ZipFile(zip_path) as z:
        for n in sorted(z.namelist()):
            m = re.match(r"(?:.*/)?([^/]+)\.(region\d+)\.gbk$", n)
            if not m or "__MACOSX" in n or Path(n).name.startswith("._"):
                continue
            recs = list(SeqIO.parse(io.StringIO(z.read(n).decode(errors="replace")), "genbank"))
            if not recs:
                continue
            r, b = recs[0], bgcs.get(Path(n).name)
            contig = b.contig if b else parsers._record_contig_id(r)
            dm = re.search(r"(\S+?),? whole genome", r.description or "")
            node = dm.group(1) if dm and dm.group(1) not in contig and contig not in dm.group(1) else ""
            ident = f"{label} / {node + ' = ' if node else ''}{contig} / {m.group(2)} / {b.bgc_id if b else '?'}"
            cds = sorted([c for c in r.features if c.type == "CDS" and "translation" in c.qualifiers],
                         key=lambda c: int(c.location.start))
            for k, c in enumerate(cds):
                pid = f"p{len(prots) + 1:05d}"
                tag = c.qualifiers.get("locus_tag", [""])[0]
                prots[pid] = {"region": ident, "order": k, "locus": tag,
                              "product": c.qualifiers.get("product", [""])[0], "translation": c.qualifiers["translation"][0]}
                if tag:
                    by_tag[tag] = pid
    return prots, by_tag


def read_hits(path: Path) -> list[dict]:
    rows = []
    for line in open(path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= len(HIT_COLS):
            rows.append(dict(zip(HIT_COLS, p)))
    return rows


def run_diamond(genes, prots, threads: int) -> list[dict]:
    from mamey import diamond_align
    with tempfile.TemporaryDirectory() as td:
        qf, rf = Path(td, "q.faa"), Path(td, "r.faa")
        qf.write_text("".join(f">{k}\n{v['translation']}\n" for k, v in prots.items()))
        rf.write_text("".join(f">{g['id']}\n{g['translation']}\n" for g in genes))
        res = diamond_align.align_fasta(str(qf), str(rf), threads=threads)
    if not res.get("ok"):
        raise RuntimeError(f"DIAMOND unavailable: {res.get('reason')}; pass --hits with a precomputed table")
    return [{**h, "slen": "", "qlen": ""} for h in res["hits"]]


def read_placement(path: Path, by_tag: dict, prots: dict, reference: str | None = None) -> dict[int, set]:
    """{module number: set of region identities} for PLACED_ON_REFERENCE_MODULE rows (tools/ks_module_placement.py).
    Query tips are `<strain>__<node>__<region>__<locus_tag>__<domain_id>`; the locus tag names the region."""
    out = defaultdict(set)
    for r in csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"):
        if r.get("verdict") != "PLACED_ON_REFERENCE_MODULE" or not r.get("module"):
            continue
        if reference is not None and r.get("reference") != reference:
            continue
        parts = r["query"].split("__")
        pid = by_tag.get(parts[3]) if len(parts) >= 5 else None
        if pid:
            out[int(r["module"])].add(prots[pid]["region"])
    return out


def assign(genes, prots, hits, placement):
    by_ref = defaultdict(list)
    for h in hits:
        if float(h["pident"]) >= MIN_ID and h["sseqid"] in {g["id"] for g in genes}:
            by_ref[h["sseqid"]].append(h)
    rows = []
    for g in genes:
        hs = sorted(by_ref.get(g["id"], []), key=lambda h: -float(h["bitscore"]))
        modular = len(g["modules"]) >= 1 and bool(re.search(r"polyketide synthase|pks|mod_ks", g["role_text"], re.I))
        placed_regions = set().union(*(placement.get(k, set()) for k in g["modules"])) if placement else set()
        row = {**g, "modular": modular, "best": None, "assigned_by": "", "regions": []}
        if modular and placed_regions:
            cand = [h for h in hs if prots[h["qseqid"]]["region"] in placed_regions]
            row["assigned_by"] = "KS placement"
            row["regions"] = sorted(placed_regions)
            hs_use = cand
        elif hs:
            row["assigned_by"] = "best match; paralogous modules, see KS placement" if modular else "best whole-gene match"
            hs_use = hs
        else:
            hs_use = []
        if hs_use:
            b = hs_use[0]
            strong = [h for h in hs_use if float(h["pident"]) >= STRONG_ID]
            iv = sorted((int(h["sstart"]), int(h["send"])) for h in strong)
            covered, cur = 0, None
            for a, e in iv:
                if cur and a <= cur[1] + 1:
                    cur = (cur[0], max(cur[1], e))
                else:
                    if cur:
                        covered += cur[1] - cur[0] + 1
                    cur = (a, e)
            covered += cur[1] - cur[0] + 1 if cur else 0
            row.update(best=b, identity=float(b["pident"]), best_cov=100 * (int(b["send"]) - int(b["sstart"]) + 1) / g["len"],
                       total_cov=min(100.0, 100 * covered / g["len"]), region=prots[b["qseqid"]]["region"],
                       order=prots[b["qseqid"]]["order"], locus=prots[b["qseqid"]]["locus"])
            if not row["regions"]:
                row["regions"] = [row["region"]]
        rows.append(row)
    # ordered blocks: consecutive reference genes whose best matches lie on one region, <= 1 gene apart, one direction
    blocks, cur = [], []
    for r in rows:
        ok = r["best"] is not None and not (r["modular"] and r["assigned_by"].startswith("best match; paralogous"))
        if ok and cur and r["region"] == cur[-1]["region"] and 1 <= abs(r["order"] - cur[-1]["order"]) <= 2 and \
                (len(cur) < 2 or (r["order"] - cur[-1]["order"]) * (cur[-1]["order"] - cur[-2]["order"]) > 0):
            cur.append(r)
        else:
            if len(cur) >= 2:
                blocks.append(cur)
            cur = [r] if ok else []
    if len(cur) >= 2:
        blocks.append(cur)
    return rows, blocks


def role_color(t: str) -> str:
    t = t.lower()
    if any(k in t for k in ("polyketide synthase", "mod_ks", "t1pks", "pks_ks", "pks_at")):
        return "#08519c"
    if any(k in t for k in ("regulat", "sensor", "response")):
        return "#969696"
    if any(k in t for k in ("transport", "membrane", "abc")):
        return "#74c476"
    return "#e6550d"


def draw(rows, blocks, L, label, ref_name, ref_acc, out_png, tag):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors as mcolors
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import Polygon
    from mamey.kcb_locusmap import _arrow_polygon, _identity_color
    from mamey.render_safe import safe_savefig_dpi
    cmap = mcolors.LinearSegmentedColormap.from_list("idgreen", [_identity_color(40), _identity_color(100)])
    norm = mcolors.Normalize(vmin=40, vmax=100)
    n = len(rows)
    key = [f"[{k}] {reg}" for reg, k in sorted(tag.items(), key=lambda kv: kv[1])]
    key_h = 0.22 * ((len(key) + 1) // 2) + 0.3
    fig = plt.figure(figsize=(18, 4.8 + 0.24 * n + key_h))
    gs = GridSpec(3, 2, height_ratios=[4.4, 0.24 * n + 0.6, key_h], width_ratios=[60, 1], hspace=0.12, wspace=0.01)
    ax, cax, tax = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
    kax = fig.add_subplot(gs[2, :])
    kax.axis("off")
    kax.text(0.0, 1.0, f"{label} contigs:", fontsize=7.2, fontweight="bold", va="top", transform=kax.transAxes)
    half = (len(key) + 1) // 2
    for col, chunk in enumerate((key[:half], key[half:])):
        kax.text(0.08 + 0.46 * col, 1.0, "\n".join(chunk), fontsize=7, va="top", transform=kax.transAxes,
                 linespacing=1.5)
    Y, RY, CY = 0.0, -1.2, -2.1
    for g in rows:
        ax.add_patch(Polygon(_arrow_polygon(g["s"], g["e"], Y, 0.5, g["strand"], tip_frac=0.25), closed=True,
                             fc=role_color(g["role_text"]), ec="black", lw=0.4))
    taken = []
    for g in rows:
        x, w_ = (g["s"] + g["e"]) / 2, len(g["name"]) * L / 220 + 1.2
        for tier in range(6):
            if all(not (t[2] == tier and x - w_ / 2 < t[1] and t[0] < x + w_ / 2) for t in taken):
                taken.append((x - w_ / 2, x + w_ / 2, tier))
                ax.text(x, Y + 0.45 + tier * 0.33, g["name"], ha="center", va="bottom", fontsize=7, style="italic")
                ax.plot([x, x], [Y + 0.26, Y + 0.43 + tier * 0.33], color="#bbbbbb", lw=0.4)
                break
    for r in rows:
        ax.add_patch(plt.Rectangle((r["s"], RY - 0.3), r["e"] - r["s"], 0.6, fc="#f4f4f4", ec="#bbbbbb", lw=0.4))
        if r["best"] is not None:
            hatch = "////" if r["assigned_by"].startswith("best match; paralogous") else None
            ax.add_patch(plt.Rectangle((r["s"], RY - 0.3), (r["e"] - r["s"]) * r["total_cov"] / 100, 0.6,
                                       fc=cmap(norm(r["identity"])), ec="#555555" if hatch else "none", lw=0.3,
                                       hatch=hatch))
    # contig row: consecutive genes on one region share a bar; a PKS gene placed on several regions gets one tag each
    runs, cur = [], []
    for r in rows:
        key = tuple(r["regions"]) if r["best"] is not None else None
        if key and cur and key == tuple(cur[-1]["regions"]):
            cur.append(r)
        else:
            if cur:
                runs.append(cur)
            cur = [r] if key else []
    if cur:
        runs.append(cur)
    k_narrow = 0
    for run in runs:
        x0, x1 = run[0]["s"], run[-1]["e"]
        unsure = run[0]["assigned_by"].startswith("best match; paralogous")
        ax.add_patch(plt.Rectangle((x0 + 0.05, CY - 0.22), x1 - x0 - 0.1, 0.44, fc="#f4f4f4" if unsure else "#dbe4f0",
                                   ec="#08306b", lw=0.6, ls="--" if unsure else "-"))
        text = " ".join(f"[{tag[reg]}]" for reg in run[0]["regions"]) + ("?" if unsure else "")
        if x1 - x0 >= L / 40 * max(1, len(run[0]["regions"])):
            ax.text((x0 + x1) / 2, CY, text, ha="center", va="center", fontsize=7.5, fontweight="bold", color="#08306b")
        else:
            yl = CY - 0.4 - 0.3 * (k_narrow % 2); k_narrow += 1
            ax.plot([(x0 + x1) / 2] * 2, [CY - 0.22, yl + 0.05], color="#08306b", lw=0.5)
            ax.text((x0 + x1) / 2, yl, text, ha="center", va="top", fontsize=6.5, fontweight="bold", color="#08306b")
    for bl in blocks:
        x0, x1 = bl[0]["s"], bl[-1]["e"]
        yb = RY + 0.45
        ax.plot([x0, x0, x1, x1], [yb - 0.08, yb, yb, yb - 0.08], color="#08306b", lw=1.4)
        ax.text(min(max((x0 + x1) / 2, 8), L - 8), yb + 0.05, f"{len(bl)} genes in order, one contig", ha="center",
                va="bottom", fontsize=6.8, color="#08306b", fontweight="bold")
    ax.text(-1, Y, f"{ref_name}\n({ref_acc})", ha="right", va="center", fontsize=8, fontweight="bold")
    ax.text(-1, RY, f"best {label} match", ha="right", va="center", fontsize=8, fontweight="bold")
    ax.text(-1, CY, f"{label} contig", ha="right", va="center", fontsize=8, fontweight="bold")
    ax.set_xlim(-14, L + 2)
    ax.set_ylim(CY - 1.1, Y + 2.6)
    ax.set_yticks([])
    for sp in ("left", "right", "top"):
        ax.spines[sp].set_visible(False)
    ax.set_xlabel(f"kb along the {ref_name} record", fontsize=8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, label=l_) for l_, c in
               [("modular PKS", "#08519c"), ("tailoring / precursor / release", "#e6550d"), ("transport", "#74c476"),
                ("regulation", "#969696"), ("no match ≥ 40%", "#f4f4f4")]]
    handles.append(plt.Rectangle((0, 0), 1, 1, fc="white", ec="#555555", hatch="////",
                                 label="PKS best match without KS placement"))
    ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 1.02), ncol=6, fontsize=7, frameon=False)
    cb = fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
    cb.set_label(f"best {label} identity (%)", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    hit = [r for r in rows if r["best"] is not None]
    ax.set_title(f"{ref_name} ({ref_acc}), gene by gene against {label}: {len(hit)} of {n} genes have a match (≥ 40% "
                 f"identity), {sum(1 for r in hit if r['identity'] >= 70)} at ≥ 70%; "
                 f"{sum(len(b) for b in blocks)} genes fall in {len(blocks)} block(s) kept in reference order on one "
                 f"contig.\nHeat row: colour = best identity; filled width = share of the gene covered by matches at ≥ 60%. "
                 f"Contig row: [n] = the {label} contig(s) assigned (table below); modular PKS genes are assigned by KS "
                 f"placement when available.", fontsize=8.6, loc="left")
    tax.axis("off")
    cells = []
    for r in rows:
        if r["best"] is None:
            cells.append([r["name"], r["desc"], "–", "–", "–", "no match at ≥ 40% identity", r["assigned_by"] or "", ""])
        else:
            cells.append([r["name"], r["desc"], f"{r['identity']:.0f}", f"{r['best_cov']:.0f}",
                          " ".join(f"[{tag[x]}]" for x in r["regions"]),
                          r["regions"][0] if len(r["regions"]) == 1 else
                          f"{len(r['regions'])} contigs: " + ", ".join(f"[{tag[x]}]" for x in r["regions"]) +
                          " (full names in the key below)",
                          r["assigned_by"], str(r.get("block", ""))])
    tb = tax.table(cellText=cells, colLabels=["gene", "reference annotation", "identity %", "coverage %", "contig",
                                              f"{label} region (strain / contig / region / alias)", "assigned by",
                                              "block"],
                   colWidths=[0.05, 0.21, 0.05, 0.06, 0.05, 0.33, 0.21, 0.04], loc="upper center", cellLoc="left")
    tb.auto_set_font_size(False)
    tb.set_fontsize(6.6)
    tb.scale(1, 1.05)
    for (ri, _), c in tb.get_celld().items():
        c.set_linewidth(0.3)
        if ri == 0:
            c.set_text_props(fontweight="bold")
    fig.savefig(out_png, dpi=safe_savefig_dpi(fig, 220), bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="One genome against one reference cluster, gene by gene.")
    ap.add_argument("--zip", required=True, type=Path, help="the genome's antiSMASH result ZIP")
    ap.add_argument("--label", required=True, help="strain label used in region identities")
    ap.add_argument("--reference", required=True, type=Path, help="reference cluster GenBank file (MIBiG)")
    ap.add_argument("--reference-name", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--placement", type=Path, help="placement.tsv from tools/ks_module_placement.py place")
    ap.add_argument("--hits", type=Path, help="precomputed tabular hits (columns in the module docstring)")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    assert_output_outside_bundle(a.out, __file__)
    genes, L = load_reference(a.reference)
    prots, by_tag = load_genome(a.zip, a.label)
    hits = read_hits(a.hits) if a.hits else run_diamond(genes, prots, a.threads)
    placement = read_placement(a.placement, by_tag, prots, reference=a.reference.name.split(".")[0]) if a.placement else {}
    rows, blocks = assign(genes, prots, hits, placement)
    for k, bl in enumerate(blocks, 1):
        for r in bl:
            r["block"] = k
    regions = []
    for r in rows:
        for reg in r["regions"]:
            if reg not in regions:
                regions.append(reg)
    tag = {reg: k for k, reg in enumerate(regions, 1)}
    a.out.mkdir(parents=True, exist_ok=True)
    acc = a.reference.name.split(".")[0]
    with open(a.out / "gene_synteny.tsv", "w", newline="", encoding="utf-8") as fh:
        w = SafeWriter(fh, delimiter="\t")
        w.writerow(TABLE_COLS)
        for r in rows:
            w.writerow([r["i"], r["name"], r["desc"], r["len"], r["modular"], r["assigned_by"],
                        f"{r['identity']:.1f}" if r["best"] else "", f"{r['best_cov']:.0f}" if r["best"] else "",
                        f"{r['total_cov']:.0f}" if r["best"] else "", " ".join(f"[{tag[x]}]" for x in r["regions"]),
                        "; ".join(r["regions"]), r.get("locus", ""), r.get("block", "")])
    draw(rows, blocks, L, a.label, a.reference_name, acc, a.out / "gene_synteny.png", tag)
    hit = [r for r in rows if r["best"] is not None]
    receipt = {"schema": "sapote-gene-synteny-map-v1", "genome": a.label, "reference": acc,
               "reference_genes": len(rows), "genes_matched": len(hit),
               "genes_ge70pct": sum(1 for r in hit if r["identity"] >= 70),
               "blocks": [[r["name"] for r in bl] for bl in blocks],
               "pks_genes_by_placement": sum(1 for r in rows if r["assigned_by"] == "KS placement"),
               "non_claims": ["Identity is similarity, not product identity.",
                              "Placement under the reference orders no contigs and joins nothing.",
                              "A similar cluster is a class-level candidate; no production or activity claim."]}
    (a.out / "gene_synteny_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    _say(f"[gene_synteny_map] {a.label} vs {acc}: {len(hit)}/{len(rows)} genes matched, "
         f"{receipt['genes_ge70pct']} at >= 70%, {len(blocks)} block(s) -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

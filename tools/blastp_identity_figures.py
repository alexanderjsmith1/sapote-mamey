#!/usr/bin/env python3
"""BLASTp identity of BGC genes, per genome and per BGC class: the bee paper's two figures, drawn from any genome set.

The two figures of the bee and wasp paper (Fig. 5 / S17 by genome, S18 by class), which until now lived only as paper scripts
(September 29 Claude Bee Paper/_tools/plot_global_blastp_identity.py v6 and plot_blastp_identity_by_class.py v3) with
hard-coded genome lists, snapshot paths and rank-1 hits. Same layouts; the inputs are now arguments.

  by-genome  A: per genome, one value per BGC gene (box + points), genomes grouped by genus, optional blocks (for example
             isolates, then comparators). B: per genome, share of genes in four identity bands; label = genes with a hit /
             all genes in the genome's antiSMASH regions.
  by-class   one panel per class (PKS, NRPS, RiPP, terpene, other): core biosynthetic genes, classed by their own antiSMASH
             rule hit, not by the region's label; a gene with rule hits in two classes is drawn in both.

Per gene the value is the identity of its top hit (--measure top1) or the mean identity of its top 10 hits (--measure top10,
the novelty measure the owner ruled on 12 Oct 2026). --db best takes the higher of nr and ClusteredNR per gene (as the bee
figures did); --db nr or --db clustered keeps one database. Per gene and database one search is used: the result file with
the most hits. The store keeps only rank 1 for some older result files, so ranks 1-10 are read from the result CSV on disk
when the store holds fewer (--root resolves the store's relative source paths). --extra-csv adds result CSVs not yet ingested
(ClusteredNR top-10 tables), read only. The store is opened read-only; give it a snapshot, never the live store.

Inputs
  --genomes  TSV with columns strain, genus, block, gene_context (path to <strain>_gene_context.jsonl; relative to --root).
             Rows keep their block order; within a block, Streptomyces first, then genus, then descending true median.
             Genomes without bound values retain denominator rows and empty plot positions; median is unavailable.
             Optional column proteins: the genome's protein FASTA (default: <strain>_proteins.faa beside gene_context).
  --palette-set  a per-paper colour set from mamey/data/genus_palette.json (moss, attine); default colours otherwise.
  --binding  sequence (default): use a protein hash when available, with a tag-and-length fallback; locus tags are numbered per
             antiSMASH run (12 Oct 2026: 9,709 of 29,274 name rows carried another run's protein). With --query-index
             (tools/blastp_query_index.py), a result binds to every gene with the same protein_sha256; without a sha it
             binds to its own tag only when the query length agrees within 1 aa; otherwise it is left out and counted in
             RUN_INFO.json. locus_tag: the earlier join on the tag alone.
Outputs (in --out, which must not hold earlier outputs): BLASTP_IDENTITY_BY_GENOME.png/.pdf + _numbers.tsv,
BLASTP_IDENTITY_BY_CLASS.png/.pdf + _numbers.tsv, GENE_VALUES.tsv (one row per gene and database), RUN_INFO.json.
The by-class figure fits --print-width, its genus key included; --split-classes N writes it as pages of N class panels
(BLASTP_IDENTITY_BY_CLASS_p1.png/.pdf, _p2, ...) with the same tables.
Extra CSVs are read with the runner's _result_generation.json beside them: a packet whose receipt says complete is false is
refused (its CSV still grows) unless --allow-incomplete-packets; a CSV with no completeness record warns. RUN_INFO.json
lists each extra CSV's packet state under extra_csv_packets.
Similarity to a public protein is not identity or function.

Usage: python3 tools/blastp_identity_figures.py --genomes genomes.tsv --store snapshot.sqlite --root <workspace> --out <folder>
       [--measure top10|top1] [--db best|nr|clustered] [--extra-csv <glob> ...] [--figure both|by-genome|by-class]
       [--palette-set moss|attine] [--print-width 6.5] [--split-classes N]
"""
from __future__ import annotations

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

import argparse
import csv
import glob
import hashlib
import json
import re
import textwrap
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.blastp_ingest import open_blastp_hits_store  # noqa: E402
from mamey.figure_stamp import savefig_metadata  # noqa: E402
from mamey.extra_csv_manifest import csv_inputs, write_csv_manifest  # noqa: E402
from mamey.protein_binding import bind_one, genome_index, proteins_from_faa, tag_of  # noqa: E402

TOOL = "blastp_identity_figures"
PALETTE = Path(__file__).resolve().parents[1] / "mamey" / "data" / "genus_palette.json"


def genus_colours(palette_set: str | None = None) -> dict:
    """The bundle genus palette: 'default', with the named per-paper set on top; unknown genera get the fallback."""
    d = json.loads(PALETTE.read_text())
    if palette_set and palette_set not in d["sets"]:
        raise SystemExit(f"--palette-set {palette_set!r} not in {PALETTE.name}: {sorted(d['sets'])}")
    out = defaultdict(lambda: d["fallback"], d["default"])
    out.update(d["sets"].get(palette_set or "", {}))
    return out


# by-genome gene points: one per gene, under the box. Darker than the first draft (0.5 pt^2 at alpha 0.25), which read as
# a pale haze at print size; the box and whiskers stay on top.
GENE_POINT_SIZE = 1.5
GENE_POINT_ALPHA = 0.6


def stable_jitter(parts, width):
    """A repeatable display offset for the same ordered input, independent of hash seed.

    JSON preserves tuple boundaries and Unicode labels. The 100-position grid and
    widths match the previous display; identities and summary statistics are unchanged.
    """
    key = json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % 100
    return (bucket / 100 - 0.5) * width


def median(v):
    """The median: the middle value, or the mean of the two middle values for an even count.

    The bee paper's v6 script took the upper middle value (sorted(v)[len(v) // 2]), which overstates the median of an even
    count. Figures and tables use the true median."""
    return statistics.median(v)

CHANNELS = {"nr": ("ncbi_nr",), "clustered": ("ncbi_clustered_nr",), "best": ("ncbi_nr", "ncbi_clustered_nr")}
DB_WORDS = {"nr": "nr", "clustered": "ClusteredNR", "best": "nr or ClusteredNR"}
BANDS = [(0, 50, "<50%", "#08306B"), (50, 70, "50–70%", "#4292C6"), (70, 90, "70–90%", "#C6DBEF"), (90, 101, "≥90%", "#F0F0F0")]
# BGC class rule (plot_blastp_identity_by_class.py v3)
PKS = {"T1PKS", "T2PKS", "T3PKS", "transAT-PKS", "transAT-PKS-like", "PKS-like", "hglE-KS", "HR-T2PKS", "enediyne", "arylpolyene"}
NRPS = {"NRPS", "NRPS-like", "NRP-metallophore", "thioamide-NRP", "isocyanide-nrp"}
TERP = {"terpene", "terpene-precursor"}
RIPP_WORDS = ("lanthipeptide", "lassopeptide", "thiopeptide", "linaridin", "RiPP", "RRE-containing", "LAP", "sactipeptide",
              "ranthipeptide", "redox-cofactor", "proteusin", "azole", "lanthidin", "triceptide", "atropopeptide", "crocagin",
              "epipeptide", "cyclic-lactone", "methanobactin", "spliceotide", "guanidinotide", "darobactin", "bottromycin",
              "glycocin", "microviridin", "cyanobactin", "head_to_tail", "lipolanthine", "strepbact")
CLASSES = ["PKS", "NRPS", "RiPP", "Terpene", "Other"]
RULE = re.compile(r"biosynthetic \(rule-based-clusters\) ([A-Za-z0-9_\-]+):")


def gene_classes(fn: str) -> set[str]:
    out = set()
    for c in RULE.findall(fn or ""):
        if c in PKS:
            out.add("PKS")
        elif c in NRPS:
            out.add("NRPS")
        elif c in TERP:
            out.add("Terpene")
        elif any(w.lower() in c.lower() for w in RIPP_WORDS):
            out.add("RiPP")
        else:
            out.add("Other")
    return out


def read_genomes(path: Path, root: Path) -> list[dict]:
    rows = list(csv.DictReader(open(path, newline=""), delimiter="\t"))
    need = {"strain", "genus", "block", "gene_context"}
    if not rows or not need <= set(rows[0]):
        raise SystemExit(f"--genomes needs columns {sorted(need)}")
    for r in rows:
        p = Path(r["gene_context"])
        r["gene_context"] = p if p.is_absolute() else root / p
        if not r["gene_context"].is_file():
            raise SystemExit(f"gene_context missing for {r['strain']}: {r['gene_context']}")
        f = Path(r.get("proteins") or str(r["gene_context"]).replace("_gene_context.jsonl", "_proteins.faa"))
        f = f if f.is_absolute() else root / f
        r["proteins"] = f if f.is_file() else None
    return rows


def read_genes(genomes: list[dict]) -> tuple[dict, dict, dict]:
    """-> region genes {strain: set(locus tags)}, core genes {(strain, tag): set(classes)},
    genome index {strain: ({protein sha: [tags]}, {tag: aa length})} for binding results by protein"""
    region, core, index = {}, {}, {}
    for g in genomes:
        s = g["strain"]
        region[s], length = set(), {}
        for line in open(g["gene_context"]):
            for c in json.loads(line).get("cds", []):
                region[s].add(c["locus_tag"])
                if c.get("aa_length") not in (None, ""):
                    length[c["locus_tag"]] = int(c["aa_length"])
                if c.get("gene_kind") == "biosynthetic":
                    core[(s, c["locus_tag"])] = gene_classes(c.get("gene_functions")) or {"Other"}
        by_sha = {}
        if g.get("proteins"):
            by_sha, from_faa = genome_index(proteins_from_faa(g["proteins"]))
            length = {**length, **from_faa}
        index[s] = (by_sha, length)
    return region, core, index


def _csv_ranks(path: Path, src: str = "", query_lengths=None) -> dict:
    out = defaultdict(dict)
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            try:
                rk, pid = int(r["hit_rank"]), float(r["pct_identity"])
            except (KeyError, TypeError, ValueError):
                continue
            if 1 <= rk <= 10:
                key = (r.get("strain", "").strip(), r.get("gene", "").strip().split("|")[-1])
                out[key].setdefault(rk, pid)
                if query_lengths is not None and src and r.get("aa_length"):
                    query_lengths.setdefault((*key, src), r["aa_length"])
    return out


def read_query_index(path) -> dict:
    """(strain, gene, source file) -> (protein_sha256, query length) from tools/blastp_query_index.py output."""
    if not path:
        return {}
    return {(r["strain"], r["gene"], r["source_file"]): (r["protein_sha256"], r["query_aa_length"])
            for r in csv.DictReader(open(path, newline="", encoding="utf-8"), delimiter="\t")}


def packet_state(path: Path) -> dict:
    """Completeness of the result packet that holds one extra CSV, from the RID runner's _result_generation.json beside it.

    A packet's CSV grows as each query batch for it returns, so a CSV bound by hash before the last batch is a partial packet.
    state: complete, incomplete (the receipt says complete is false), no_generation_file (older runs), or
    no_completeness_record (a receipt that predates the completeness fields, or one that cannot be read)."""
    gen = path.parent / "_result_generation.json"
    if not gen.is_file():
        return {"state": "no_generation_file", "genes_missing": [], "generation": ""}
    try:
        rec = json.loads(gen.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rec = None
    if not isinstance(rec, dict) or not isinstance(rec.get("complete"), bool):
        return {"state": "no_completeness_record", "genes_missing": [], "generation": ""}
    done, expected = set(rec.get("genes_done") or []), list(rec.get("genes_expected") or [])
    return {"state": "complete" if rec["complete"] else "incomplete",
            "genes_missing": [g for g in expected if g not in done], "generation": str(rec.get("generation", ""))}


def bind_values(by: dict, index: dict, qindex: dict, filled=frozenset(), query_lengths=None) -> tuple[dict, dict, set]:
    """Re-key {(strain, gene, channel): {source: ranks}} onto the genome's genes by protein.
    -> (bound, counts per strain, the bound keys' (key, source) pairs whose ranks came from disk)."""
    out = defaultdict(dict)
    counts = defaultdict(lambda: defaultdict(int))
    new_filled = set()
    for (s, g, ch), srcs in by.items():
        by_sha, length = index.get(s, ({}, {}))
        for src, ranks in srcs.items():
            sha, qlen = qindex.get((s, g, src), ("", ""))
            tags, how = bind_one(tag_of(g), sha, qlen or (query_lengths or {}).get((s, g, src)), by_sha, length)
            counts[s][how] += 1
            for t in tags:
                if len(ranks) > len(out[(s, t, ch)].get(src, {})):
                    out[(s, t, ch)][src] = ranks
                    if ((s, g, ch), src) in filled:
                        new_filled.add(((s, t, ch), src))
    return out, {s: dict(c) for s, c in counts.items()}, new_filled


def gene_values(store: Path, root: Path, region: dict, extra_csvs=(), channels=("ncbi_nr", "ncbi_clustered_nr"),
                index=None, qindex=None, binding_counts=None) -> dict:
    """(strain, gene, channel) -> (top-1 identity, mean of top 10, hits used, source file, ranks from disk) for region genes.
    index (from read_genes): bind each result to genes by protein (see --binding); None keeps the locus-tag join.
    binding_counts, a dict, receives per strain how the results bound."""
    query_lengths = {}  # This invocation only: never reuse lengths from a different snapshot.
    want = list(region)
    con = open_blastp_hits_store(store, writable=False)
    q = ("select strain, gene, channel, source_file, hit_rank, pct_identity, aa_length from hits where channel in (%s) "
         "and coalesce(provenance_suspect,0)=0 and pct_identity is not null and hit_rank between 1 and 10 and strain in (%s)"
         % (",".join("?" * len(channels)), ",".join("?" * len(want))))
    by = defaultdict(lambda: defaultdict(dict))
    for s, g, ch, src, rk, pid, alen in con.execute(q, (*channels, *want)):
        by[(s, g.split("|")[-1], ch)][src].setdefault(int(rk), float(pid))
        if alen not in (None, ""):
            query_lengths.setdefault((s, g.split("|")[-1], src), alen)
    con.close()
    if "ncbi_clustered_nr" in channels:
        for src in extra_csvs:
            for (s, g), ranks in _csv_ranks(root / src, str(src), query_lengths).items():
                if s in region:
                    by[(s, g, "ncbi_clustered_nr")][str(src)].update(ranks)
    disk, filled = {}, set()
    for key, srcs in by.items():
        for src in list(srcs):
            if src not in disk:
                p = root / src
                disk[src] = _csv_ranks(p, src, query_lengths) if p.is_file() and p.suffix == ".csv" else None
            d = disk[src]
            if d and len(d.get(key[:2], {})) > len(srcs[src]):
                srcs[src] = d[key[:2]]
                filled.add((key, src))
    if index is not None:
        by, counts, filled = bind_values(by, index, qindex or {}, filled, query_lengths)
        if binding_counts is not None:
            binding_counts.update(counts)
    out = {}
    for key, srcs in by.items():
        if key[1] not in region.get(key[0], ()):
            continue
        src = max(srcs, key=lambda k: len(srcs[k]))
        ranks = srcs[src]
        if 1 not in ranks:
            continue
        v = [ranks[r] for r in sorted(ranks)]
        out[key] = (ranks[1], statistics.mean(v), len(v), src, (key, src) in filled)
    return out


def per_gene(values: dict, measure: str) -> dict:
    """(strain, gene) -> the chosen measure, the higher across the databases present."""
    idx = 0 if measure == "top1" else 1
    best = {}
    for (s, g, ch), v in values.items():
        if v[idx] > best.get((s, g), -1):
            best[(s, g)] = v[idx]
    return best


def _order(genomes, per):
    blocks = []
    for g in genomes:
        if not blocks or blocks[-1][0] != g["block"]:
            blocks.append((g["block"], []))
        blocks[-1][1].append(g["strain"])
    genus = {g["strain"]: g["genus"] for g in genomes}
    out = []
    for name, ss in blocks:
        ss = sorted(ss,
                    key=lambda s: (genus[s] != "Streptomyces", genus[s], -median(per[s]) if per[s] else float("inf")))
        if ss:
            out.append((name, ss))
    return out


def _positions(groups):
    xs, order, x = [], [], 0
    for gi, (_, ss) in enumerate(groups):
        if gi:
            x += 1
        for s in ss:
            xs.append(x); order.append(s); x += 1
    return xs, order, x


def _legend_handles(plt, order, genus, colours):
    seen = []
    for s in order:
        if genus[s] not in seen:
            seen.append(genus[s])
    return [plt.Line2D([], [], marker="s", ls="", color=colours[g], label=g) for g in seen]


class BlockLabelDoesNotFit(ValueError):
    """An unbreakable title cannot fit its block at the required print size."""


def _block_labels(ax, groups, xs, x, y, va, bold=False):
    from matplotlib.font_manager import FontProperties
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    font = FontProperties(size=8)
    starts, offset = [], 0
    for name, strains in groups:
        starts.append(offset)
        offset += len(strains)
    texts = []
    for i, ((name, strains), start) in enumerate(zip(groups, starts)):
        left = -0.7 if i == 0 else xs[start] - 1
        right = x - 0.3 if i == len(groups) - 1 else xs[starts[i + 1]] - 1
        width = ax.transData.transform((right, 0))[0] - ax.transData.transform((left, 0))[0]
        available = width - 4 * fig.dpi / 72
        def measured(value):
            return renderer.get_text_width_height_descent(value, font, ismath=False)[0]
        lines, current = [], ""
        for word in name.split():
            if measured(word) > available:
                raise BlockLabelDoesNotFit(f"BLOCK_LABEL_DOES_NOT_FIT: {name!r}; word {word!r} exceeds block at 8 pt")
            trial = (current + " " + word).strip()
            if current and measured(trial) > available:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        text = ax.text((left + right) / 2, y, "\n".join(lines), transform=ax.get_xaxis_transform(),
                       ha="center", va=va, fontsize=8, color="#333", parse_math=False,
                       fontweight="bold" if bold else "normal")
        text.set_gid("block-title")
        text._block_bounds = (left, right)
        texts.append(text)
    return texts


def by_genome(genomes, region, best, colours, measure, db, out: Path, bar_counts: bool = False, block_labels: str = "above") -> list[str]:
    """Panel A: identity per genome. Panel B: share of genes per identity band. The genes-with-a-hit counts go to
    the numbers table and the caption; drawing them above panel B's bars is opt-in (bar_counts).
    block_labels: "above" (default) titles each block of genomes once, above panel A; "below" titles the blocks in bold
    under the genome names of both panels, with each key moved down below them."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    genus = {g["strain"]: g["genus"] for g in genomes}
    per = defaultdict(list)
    for (s, g), v in best.items():
        per[s].append(v)
    groups = _order(genomes, per)
    xs, order, x = _positions(groups)
    width = min(7.0, max(3.6, 0.36 * (x + 1) + 1.4))
    # the genus key sits under panel A (its colours mark panel A's points and the strain names), so the canvas is
    # taller than the 6.6 in of the earlier layout by the room that key needs
    fig, (a, b) = plt.subplots(2, 1, figsize=(width, 7.2), gridspec_kw={"height_ratios": [1.35, 1], "hspace": 0.62})
    for i, s in zip(xs, order):
        v = per[s]; col = colours[genus[s]]
        a.boxplot(v, positions=[i], widths=0.6, showfliers=False, medianprops=dict(color="black", lw=0.9), boxprops=dict(color=col, lw=0.8),
                  whiskerprops=dict(color=col, lw=0.8), capprops=dict(color=col, lw=0.8))
        a.scatter([i + stable_jitter((s, j), 0.5) for j in range(len(v))], v, s=GENE_POINT_SIZE, alpha=GENE_POINT_ALPHA, color=col, zorder=1,
                  linewidths=0)
        lo = 0
        for lo_, hi_, lab, cc in BANDS:
            f = sum(lo_ <= y < hi_ for y in v) / len(v) if v else 0
            b.bar(i, f, bottom=lo, width=0.8, color=cc, edgecolor="#555", linewidth=0.25, label=lab if i == xs[0] else None); lo += f
        if bar_counts:
            b.text(i, 1.02, f"{len(v)}/{len(region[s])}", ha="center", va="bottom", fontsize=8, color="#333", rotation=90)
    if len(groups) > 1:
        start = 0
        for gi, (name, ss) in enumerate(groups):
            pos = xs[start:start + len(ss)]; start += len(ss)
            if gi:
                for ax in (a, b):
                    ax.axvline(pos[0] - 1, color="#999", lw=0.6, ls=":")
    for ax in (a, b):
        ax.set_xticks(xs); ax.set_xticklabels(order, rotation=90, fontsize=8); ax.tick_params(axis="y", labelsize=8)
        ax.set_xlim(-0.7, x - 0.3)
        for t, s in zip(ax.get_xticklabels(), order):
            t.set_color(colours[genus[s]])
        ax.spines[["top", "right"]].set_visible(False)
    for y in (50, 70, 90):
        a.axhline(y, color="#bbb", lw=0.6, ls="--", zorder=0)
    what = "Mean identity of the top 10 hits\nin" if measure == "top10" else "Identity to the highest-similarity\nprotein in"
    a.set_ylabel(f"{what} {DB_WORDS[db]} (%)", fontsize=8)
    a.set_ylim(15, 101)
    for ax_, L_ in ((a, "A"), (b, "B")):
        ax_.text(-0.085 * 7.0 / width, 1.04, L_, transform=ax_.transAxes, fontsize=11, fontweight="bold", va="bottom", ha="left")
    b.set_ylabel("Share of genes", fontsize=8); b.set_ylim(0, 1.24 if bar_counts else 1.0)
    leg_b = b.legend(ncol=4 if width >= 4.5 else 2, fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.47),
                     title="Identity band", title_fontsize=8)
    b.add_artist(leg_b)
    below = {a: [], b: []}
    if len(groups) > 1 and block_labels == "below":
        for ax in (a, b):
            below[ax] = _block_labels(ax, groups, xs, x, -0.3, "top", bold=True)
    elif len(groups) > 1:
        labels = _block_labels(a, groups, xs, x, 1.03, "bottom")
        fig.canvas.draw()
        label_height = max(t.get_window_extent().height for t in labels) / fig.dpi
        fig.subplots_adjust(top=1 - (label_height + 0.22) / fig.get_figheight())
    # genus key directly under panel A's strain names (the owner, 19 Oct: "the legend for 4a is below the data of 4b and
    # hard to find"); the identity-band key directly under panel B's. Both are anchored to the measured bottom of the
    # strain names, and the gap between the panels and the bottom margin are widened until each key fits inside the
    # canvas without touching the panel below it.
    rend = fig.canvas.get_renderer()
    leg_a = a.legend(handles=_legend_handles(plt, order, genus, colours), ncol=4 if width >= 4.5 else 2, frameon=False,
                     loc="upper center", bbox_to_anchor=(0.5, -0.3), prop={"style": "italic", "size": 8}, markerscale=0.8)
    a.add_artist(leg_a)
    hspace, bottom = 0.62, 0.11

    def anchor(ax, leg):
        box = ax.get_window_extent(rend)
        tick_bottom = min(t.get_window_extent(rend).y0 for t in ax.get_xticklabels())
        if below[ax]:                              # bold block titles sit just under the genome names, the key under them
            for t in below[ax]:
                t.set_y((tick_bottom - box.y0 - 0.05 * fig.dpi) / box.height)
            fig.canvas.draw()
            tick_bottom = min(t.get_window_extent(rend).y0 for t in below[ax])
        leg.set_bbox_to_anchor((0.5, (tick_bottom - box.y0 - 0.06 * fig.dpi) / box.height), transform=ax.transAxes)

    for _ in range(40):
        a.get_gridspec().update(hspace=hspace)   # the gridspec's own hspace overrides subplots_adjust(hspace=...)
        fig.subplots_adjust(bottom=bottom)
        fig.canvas.draw()
        anchor(a, leg_a); anchor(b, leg_b)
        fig.canvas.draw()
        b_top = max([t.get_window_extent(rend).y1 for t in b.texts] + [b.get_window_extent(rend).y1])
        gap_ok = leg_a.get_window_extent(rend).y0 - b_top >= 0.12 * fig.dpi
        foot_ok = leg_b.get_window_extent(rend).y0 >= 0.04 * fig.dpi
        if gap_ok and foot_ok:
            break
        if not gap_ok:
            hspace += 0.06
        if not foot_ok:
            bottom += 0.015
    else:
        raise RuntimeError("by-genome: the genus and identity-band keys do not fit; widen the canvas")
    png = out / "BLASTP_IDENTITY_BY_GENOME.png"
    for p in (png, png.with_suffix(".pdf")):
        fig.savefig(p, dpi=600, bbox_inches="tight", bbox_extra_artists=[leg_a, leg_b, *a.texts, *b.texts], metadata=savefig_metadata(p, TOOL))
    plt.close(fig)
    allv = [y for s in order for y in per[s]]
    rows = ["block\tstrain\tgenus\tgenes_with_hit\tgenes_in_regions\tmedian\tshare_below_90\tshare_below_70\tshare_below_50"]
    for name, ss in groups:
        for s in ss:
            v = per[s]
            if not v:
                rows.append(f"{name}\t{s}\t{genus[s]}\t0\t{len(region[s])}\t\t\t\t")
                continue
            rows.append(f"{name}\t{s}\t{genus[s]}\t{len(v)}\t{len(region[s])}\t{median(v):.1f}\t"
                        f"{sum(y < 90 for y in v) / len(v):.3f}\t{sum(y < 70 for y in v) / len(v):.3f}\t{sum(y < 50 for y in v) / len(v):.3f}")
    head = [f"# genes with a value: {len(allv)} of {sum(len(region[s]) for s in order)} region genes in {len(order)} genomes; "
            f"median {median(allv):.1f}%" if allv else f"# genes with a value: 0 of {sum(len(region[s]) for s in order)} region genes in {len(order)} genomes; median unavailable"]
    (out / "BLASTP_IDENTITY_BY_GENOME_numbers.tsv").write_text("\n".join(head + rows) + "\n")
    return [str(png)]


def _fit_key(fig, place, preferred: int, print_width: float):
    """Draw the genus key with the most columns, up to `preferred`, at which the saved figure is no wider than
    `print_width`. `place(ncol)` draws the key and returns it. The width is measured from the rendered figure: the tight
    bounding box that savefig crops to, plus its padding on both sides. A key one entry per column too wide for the
    page printed the whole figure scaled down (Bee Fig. S18: 9 genera in one row, 12.8 in wide, 8 pt text at ~4 pt)."""
    import matplotlib
    pad = 2 * float(matplotlib.rcParams["savefig.pad_inches"])
    renderer = fig.canvas.get_renderer()
    ncol = max(1, preferred)
    while True:
        key = place(ncol)
        fig.canvas.draw()
        if ncol == 1 or fig.get_tightbbox(renderer).width + pad <= print_width + 1e-3:
            return key
        key.remove()
        ncol -= 1


def _class_page(png: Path, shown, panel_data, groups, xs, order, x, genus, colours, measure, db, print_width, grid):
    """Draw one page of class panels (`shown`, in order) and save it as `png` and its PDF."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    width = print_width   # the figure is saved with a tight crop, so it prints no wider than print_width
    ncols = 2 if grid == "auto" and len(shown) in (3, 4) else 1
    nrows = (len(shown) + ncols - 1) // ncols
    # In a two-column grid the strain names sit under the bottom panel of each column. When the panels do not fill the
    # grid (3 panels), one column's bottom panel is in the top row and its names need the wide 0.9 gap. When they fill
    # it (4 panels), every name is on the bottom row: the gap was empty space (Attine Fig. S11, 19 Oct), so it is
    # narrowed and the canvas made shorter by the same amount, keeping the figure inside the page.
    ragged = len(shown) % ncols != 0
    height = (8.4 if ragged else 7.4) if ncols == 2 else 3.0 * len(shown) + 1.2
    fig, matrix = plt.subplots(nrows, ncols, figsize=(width, height), sharex=True,
                               gridspec_kw={"hspace": (0.9 if ragged else 0.42) if ncols == 2 else 0.42}, squeeze=False)
    axes = list(matrix.flat)[:len(shown)]
    for unused in list(matrix.flat)[len(shown):]:
        unused.set_visible(False)
    bottom_axes = [axes[max(i for i in range(len(axes)) if i % ncols == col)] for col in range(ncols)]
    for k, ax in zip(shown, axes):
        vals, allv = panel_data[k]
        for i, s in zip(xs, order):
            v = vals[s]; col = colours[genus[s]]
            if v:
                if len(v) >= 5:
                    ax.boxplot(v, positions=[i], widths=0.6, showfliers=False, medianprops=dict(color="black"),
                               boxprops=dict(color=col), whiskerprops=dict(color=col), capprops=dict(color=col))
                ax.scatter([i + stable_jitter((s, k, j), 0.45) for j in range(len(v))], v, s=6, alpha=0.55,
                           color=col, edgecolor="none", zorder=3)
            ax.text(i, 101.5, f"{len(v)}", ha="center", va="bottom", fontsize=8, color="#333")
        for y in (50, 70, 90):
            ax.axhline(y, color="#bbb", lw=0.6, ls="--", zorder=0)
        if len(groups) > 1:
            ax.axvline(xs[len(groups[0][1])] - 1, color="#999", lw=0.6, ls=":")
        med = f"median {median(allv):.1f}%" if allv else "median unavailable"
        panel_title = f"{k} core genes (n = {len(allv)} with a hit; {med})"
        if ncols == 2:
            panel_title = textwrap.fill(panel_title, width=max(24, int(width * 4.5)))
        ax.set_title(panel_title, fontsize=8 if ncols == 2 else 10, loc="left", pad=14)
        ax.set_ylim(15, 101)
        if axes.index(ax) % ncols == 0:
            ax.set_ylabel("Top-10 mean identity (%)" if measure == "top10" else "Identity (%)", fontsize=8.5)
        ax.spines[["top", "right"]].set_visible(False); ax.tick_params(axis="y", labelsize=8)
    for ax in bottom_axes:
        ax.set_xticks(xs); ax.set_xticklabels(order, rotation=90, fontsize=8)
        ax.tick_params(axis="x", labelbottom=True)
        ax.set_xlim(-0.7, x - 0.3)
        for t, strain in zip(ax.get_xticklabels(), order):
            t.set_color(colours[genus[strain]])
    handles = _legend_handles(plt, order, genus, colours)
    blocks = len(groups) > 1
    what = ("Mean identity of the top 10 BLASTp hits of each core biosynthetic gene in the NCBI " if measure == "top10"
            else "Identity of each core biosynthetic gene to its highest-similarity protein in the NCBI ")
    title = (f"{what}{DB_WORDS[db]} databases, by the gene's own antiSMASH rule class (numbers above: genes with a hit)")
    # Wrap to the canvas: about 0.6 em per character at 10 pt, starting 7% in from the left edge.
    lines = textwrap.wrap(title, width=max(40, int((0.91 * width * 72) / (0.6 * 10))))
    fig.subplots_adjust(top=1 - (0.6 + 0.18 * len(lines)) / fig.get_figheight())
    if ncols == 2:
        fig.subplots_adjust(left=0.12, right=0.98, bottom=0.20, wspace=0.35)
    fig.text(0.07, 1 - 0.12 / fig.get_figheight(), "\n".join(lines), fontsize=10, va="top")
    if blocks:
        for ax in bottom_axes:
            _block_labels(ax, groups, xs, x, -0.34, "top")
    # The genus key is drawn last, once the layout is final, with as many columns as the print width holds.
    if ncols == 2:
        # key hangs below the figure (upper center at y = 0), clear of the block titles under the bottom panels; the
        # tight bounding box at save time takes it in (Moss Fig. S4, 20 Oct: the lower-center key ran into a block title)
        def place(n):
            return fig.legend(handles=handles, ncol=n, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.01),
                              prop={"style": "italic", "size": 8})
        _fit_key(fig, place, min(len(handles), 3), print_width)
    else:
        def place(n):
            return axes[-1].legend(handles=handles, ncol=n, frameon=False, loc="upper center",
                                   bbox_to_anchor=(0.5, -0.42 if blocks else -0.3), prop={"style": "italic", "size": 8})
        _fit_key(fig, place, len(handles) if not blocks else min(len(handles), 3), print_width)
    for p in (png, png.with_suffix(".pdf")):
        fig.savefig(p, dpi=600, bbox_inches="tight", metadata=savefig_metadata(p, TOOL))
    plt.close(fig)
    return str(png)


def by_class(genomes, core, best, colours, measure, db, out: Path, omit=(), print_width: float = 7.2, grid: str = "auto",
             split_classes: int = 0) -> list[str]:
    """One panel per BGC class. Classes in `omit` are left off the figure; their rows stay in the numbers table.
    The canvas is fitted to `print_width` (inches; 7.2 = double column) so text drawn at 8 pt prints at 8 pt; the genus key
    takes as many columns as that width holds. split_classes N > 0 draws N class panels per page, one figure per page
    (BLASTP_IDENTITY_BY_CLASS_p1, _p2, ...), so a tall stack fits a page at true print size; the tables are unchanged."""
    genus = {g["strain"]: g["genus"] for g in genomes}
    per_all = defaultdict(list)
    for (s, g), v in best.items():
        per_all[s].append(v)
    groups = _order(genomes, per_all)
    xs, order, x = _positions(groups)
    vals = {c: defaultdict(list) for c in CLASSES}
    searched = {c: defaultdict(int) for c in CLASSES}
    for (s, g), ks in core.items():
        for k in ks:
            searched[k][s] += 1
            if (s, g) in best:
                vals[k][s].append(best[(s, g)])
    shown = [c for c in CLASSES if c not in set(omit)]
    rows = ["bgc_class\tstrain\tgenus\tcore_genes\tcore_genes_with_hit\tmedian\tshare_below_70"]
    # BLASTp to-do list: every core gene of a drawn genome with no bound value, by class (all classes, omitted ones too)
    todo = ["bgc_class\tstrain\tgenus\tlocus_tag\tclass_genes_with_hit\tbox_drawn"]
    for (s, g), ks in sorted(core.items()):
        if s in genus and (s, g) not in best:
            for k in sorted(ks):
                todo.append(f"{k}\t{s}\t{genus[s]}\t{g}\t{len(vals[k][s])}\t{'yes' if len(vals[k][s]) >= 5 else 'no'}")
    (out / "CORE_GENES_WITHOUT_HIT.tsv").write_text("\n".join(todo) + "\n")
    panel_data = {}
    for k in CLASSES:             # every class's numbers are written, drawn or omitted
        allv = []
        for s in order:
            v = vals[k][s]
            allv += v
            rows.append(f"{k}\t{s}\t{genus[s]}\t{searched[k][s]}\t{len(v)}\t{median(v):.1f}\t"
                        f"{sum(y < 70 for y in v) / len(v):.3f}" if v else f"{k}\t{s}\t{genus[s]}\t{searched[k][s]}\t0\t\t")
        panel_data[k] = (vals[k], allv)
    pages = [shown[i:i + split_classes] for i in range(0, len(shown), split_classes)] if split_classes > 0 else [shown]
    made = []
    for n, page in enumerate(pages, 1):
        stem = "BLASTP_IDENTITY_BY_CLASS" if len(pages) == 1 else f"BLASTP_IDENTITY_BY_CLASS_p{n}"
        made.append(_class_page(out / f"{stem}.png", page, panel_data, groups, xs, order, x, genus, colours, measure, db,
                                print_width, grid))
    (out / "BLASTP_IDENTITY_BY_CLASS_numbers.tsv").write_text("\n".join(rows) + "\n")
    return made


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--genomes", type=Path, required=True)
    ap.add_argument("--store", type=Path, required=True, help="a read-only snapshot of the BLASTp store")
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="folder the store's source paths and gene_context paths are relative to")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--measure", choices=("top10", "top1"), default="top10")
    ap.add_argument("--db", choices=tuple(CHANNELS), default="best")
    ap.add_argument("--extra-csv", action="append", default=[], help="glob of ClusteredNR top-10 result CSVs (relative to --root)")
    ap.add_argument("--palette-set", help="per-paper colour set in mamey/data/genus_palette.json (moss, attine)")
    ap.add_argument("--figure", choices=("both", "by-genome", "by-class"), default="both")
    ap.add_argument("--binding", choices=("sequence", "locus_tag"), default="sequence",
                    help="bind results to genes by protein (default) or by locus tag alone (the earlier join)")
    ap.add_argument("--query-index", type=Path, help="tools/blastp_query_index.py output: protein_sha256 per result")
    ap.add_argument("--grid", choices=("auto", "column"), default="auto", help="by-class: use two columns for three or four panels; column restores the vertical stack")
    ap.add_argument("--bar-counts", action="store_true", help="by-genome: print genes-with-a-hit / region genes above panel B's bars (off by default; the counts are in the numbers table)")
    ap.add_argument("--genus-colour", action="append", default=[], metavar="GENUS=#RRGGBB", help="repeatable; colour for one genus")
    ap.add_argument("--block-labels", choices=("above", "below"), default="above", help="by-genome: block titles once above panel A (default), or bold under the genome names of both panels")
    ap.add_argument("--print-width", type=float, default=7.2, help="by-class: printed width in inches (7.2 double column; larger for a landscape page); text stays 8 pt at that width")
    ap.add_argument("--split-classes", type=int, default=0, metavar="N", help="by-class: draw N class panels per page, one figure per page (_p1, _p2, ...), so a tall stack prints at true size; 0 (default) draws one figure")
    ap.add_argument("--omit-class", action="append", default=[], choices=CLASSES, help="by-class: leave a class off the figure (repeatable); its rows stay in the numbers table")
    ap.add_argument("--extra-csv-list", type=Path, help="checked path/sha256/bytes TSV; exclusive with --extra-csv")
    ap.add_argument("--allow-incomplete-packets", action="store_true",
                    help="draw from an extra CSV whose packet receipt says complete is false; warns and records it in RUN_INFO.json "
                         "(default: refuse, naming the packet and its missing genes)")
    a = ap.parse_args(argv)
    if a.figure in ("both", "by-class") and set(a.omit_class) == set(CLASSES):
        ap.error("--omit-class must leave at least one class visible")
    if a.split_classes < 0:
        ap.error("--split-classes must be 0 (one figure) or a positive number of panels per page")
    root = a.root.resolve()
    try:
        extra_records, input_list_sha = csv_inputs(root, a.extra_csv, a.extra_csv_list)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    packets = [{"path": r["path"], **packet_state(root / r["path"])} for r in extra_records]
    incomplete = [p for p in packets if p["state"] == "incomplete"]
    if incomplete:
        named = "; ".join(f"{Path(p['path']).parent.name} ({p['path']}): missing genes "
                          f"{', '.join(p['genes_missing']) or 'not listed (no expected genes recorded)'}" for p in incomplete)
        if not a.allow_incomplete_packets:
            ap.error(f"{len(incomplete)} extra CSV packet(s) are incomplete; their CSVs will still grow: {named}. "
                     "Wait for the runner to finish them, or pass --allow-incomplete-packets to draw anyway")
        sys.stderr.write(f"warning: drawing from {len(incomplete)} incomplete packet(s) (--allow-incomplete-packets): {named}\n")  # direct write keeps the strict-health print_calls ratchet flat
    unknown = [p["path"] for p in packets if p["state"] in ("no_generation_file", "no_completeness_record")]
    if unknown:
        sys.stderr.write(f"warning: {len(unknown)} extra CSV(s) have no packet completeness record; completeness unknown: "
                         f"{', '.join(unknown[:5])}{' ...' if len(unknown) > 5 else ''} (all listed in RUN_INFO.json extra_csv_packets)\n")
    a.out.mkdir(parents=True, exist_ok=True)
    clash = [p.name for p in a.out.glob("BLASTP_IDENTITY_BY_*")] + [p.name for p in a.out.glob("GENE_VALUES.tsv")]
    clash += [name for name in ("EXTRA_CSV_FILES.tsv", "RUN_INFO.json") if (a.out / name).exists()]
    if clash:
        raise SystemExit(f"{a.out} already holds {clash}; nothing overwritten")
    colours = genus_colours(a.palette_set)
    for spec in a.genus_colour:                    # one genus recoloured so a figure matches the rest of its paper
        g, _, hx = spec.partition("=")
        if not (hx.startswith("#") and len(hx) == 7):
            raise SystemExit(f"--genus-colour wants GENUS=#RRGGBB, got {spec!r}")
        colours[g.strip()] = hx
    genomes = read_genomes(a.genomes, root)
    region, core, index = read_genes(genomes)
    extra = [r["path"] for r in extra_records]
    binding = {}
    values = gene_values(a.store, root, region, extra, CHANNELS[a.db],
                         index if a.binding == "sequence" else None, read_query_index(a.query_index), binding)
    best = per_gene(values, a.measure)
    made = []
    if a.figure in ("both", "by-genome"):
        made += by_genome(genomes, region, best, colours, a.measure, a.db, a.out, bar_counts=a.bar_counts, block_labels=a.block_labels)
    if a.figure in ("both", "by-class"):
        made += by_class(genomes, core, best, colours, a.measure, a.db, a.out, omit=a.omit_class, print_width=a.print_width, grid=a.grid,
                         split_classes=a.split_classes)
    with open(a.out / "GENE_VALUES.tsv", "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["strain", "gene", "channel", "top1_identity", "top10_mean_identity", "hits_used", "ranks_from_disk", "source_file"])
        for (s, g, ch), v in sorted(values.items()):
            w.writerow([s, g, ch, f"{v[0]:.1f}", f"{v[1]:.2f}", v[2], "yes" if v[4] else "", v[3]])
    manifest_sha = write_csv_manifest(a.out / "EXTRA_CSV_FILES.tsv", extra_records)
    info = {"extra_csv_manifest_sha256": manifest_sha, "extra_csv_list_sha256": input_list_sha, "genomes": len(genomes), "measure": a.measure, "db": a.db, "palette_set": a.palette_set or "default", "store": str(a.store), "extra_csvs": len(extra),
            "genes_with_value": len(best), "bar_counts": a.bar_counts, "grid": a.grid, "omitted_classes": a.omit_class, "print_width_in": a.print_width, "split_classes": a.split_classes, "figures": made, "binding": a.binding,
            "query_index": str(a.query_index or ""), "genomes_without_proteins": sorted(g["strain"] for g in genomes if not g["proteins"]),
            "results_binding": binding,
            "median_method": "statistics.median", "point_placement": "sha256-json-index-v1",
            "genomes_without_values": sorted(g["strain"] for g in genomes if not any(s == g["strain"] for s, _ in best)),
            "results_unbound": sum(n for c in binding.values() for k, n in c.items() if k.startswith("unbound")),
            "allow_incomplete_packets": a.allow_incomplete_packets, "extra_csv_packets": packets}
    (a.out / "RUN_INFO.json").write_text(json.dumps(info, indent=1) + "\n")
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""GECCO cohort report: list and draw GECCO 0.11 cluster calls beside the antiSMASH regions of a set of genomes.

GECCO (Carroll et al.) calls gene clusters from protein-domain content. `mamey_run.py gecco-crosscheck` runs it on one
package; locus pages and strain slides show its per-gene probability. This tool reports the calls themselves, for many
genomes at once:

  gecco_calls.tsv          every GECCO call: contig, coordinates, GECCO type and type probabilities, maximum and mean
                           probability, genes, Pfam domains (accessions and names), and how it relates to the antiSMASH
                           regions (OVERLAPS_REGION, NO_REGION_OVERLAP), with the overlapping regions' identities
  regions_with_gecco.tsv   every antiSMASH region with its products, antiSMASH categories, edge flag and overlapping calls
  summary_by_genome.tsv    counts per genome
  calls_by_genome/         figure: GECCO calls per genome by GECCO type, calls inside antiSMASH regions solid and calls
                           outside any region light
  type_vs_category/        figure: GECCO type against the antiSMASH category of the overlapping region (isolates, and
                           references as a second panel when supplied)
  calls_vs_references/     figure (references supplied): each isolate's calls, and calls outside every region, against
                           the reference genomes of its genus; isolate_percentiles.tsv gives each isolate's mid-rank percentile
  receipt.json             input and output SHA-256, settings, the overlap and contig rules

Inputs
  --genomes TSV   columns strain, group, antismash_zip, gecco_clusters; optional genus and role (isolate, reference or
                  SID; default isolate). With references, each isolate is drawn against the references of its genus
                  (calls_vs_references/) and the type-against-category figure gets a references panel. antismash_zip is an antiSMASH result zip (its
                  <contig>.regionNNN.gbk files are read); gecco_clusters is GECCO's <name>.clusters.tsv for that genome.
  --aliases TSV   optional; columns strain, contig, region, bgc_alias (a Mamey package inventory or locus manifest).
                  With it, regions are named strain / contig / region / alias; without it the alias is reported as not
                  supplied, never invented.
  --pfam-names TSV (accession, name) or --pfam-hmm Pfam-A.hmm: names for the domain accessions GECCO lists.
  --group-order   comma-separated group order for the figure (default: order of first appearance).

Rules
  Overlap: a call and a region overlap when they share at least one base on the same contig (GECCO coordinates are
  1-based inclusive, antiSMASH region coordinates 0-based half-open).
  Contigs: GECCO rewrites the coverage part of SPAdes contig names. A GECCO sequence is joined to a region contig by exact
  name, else by a NODE_n_length_L alias only when that alias names exactly one region contig and one GECCO sequence
  (tools/gap_rescue_locus_map._gecco_contig_map). A call on a contig with no region is reported with GECCO's own name.
  A GECCO call is a second opinion on capacity. It does not prove a cluster, and a call outside every antiSMASH region
  is not evidence of a new pathway.

usage: gecco_cohort_report.py --genomes genomes.tsv --out NEW_DIR [--aliases aliases.tsv]
       [--pfam-names names.tsv | --pfam-hmm Pfam-A.hmm] [--group-order A,B,C]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401

from mamey.logging_setup import get_logger as _get_logger  # noqa: E402

_OUT = _get_logger(__name__)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

TOOL = "tools/gecco_cohort_report.py"
TYPES = ["Polyketide", "NRP", "RiPP", "Terpene", "Saccharide", "Alkaloid", "Mixed", "Unknown"]
PROB_COLS = ["alkaloid_probability", "nrp_probability", "polyketide_probability", "ripp_probability",
             "saccharide_probability", "terpene_probability"]
MIN_PT = 8


class ReportError(ValueError):
    pass


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_tsv(path, required):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    missing = [c for c in required if rows and c not in rows[0]] or ([] if rows else ["(no rows)"])
    if missing:
        raise ReportError(f"{path}: missing columns {missing}")
    return rows


def gecco_type(raw: str) -> str:
    """GECCO writes several types joined by ';' (e.g. NRP;Polyketide); those are drawn as Mixed and listed as written."""
    raw = (raw or "").strip() or "Unknown"
    return "Mixed" if ";" in raw else (raw if raw in TYPES else "Unknown")


def antismash_regions(zip_path):
    """Regions of one antiSMASH zip: contig (from the region file name), region, 0-based start, end, products,
    categories, contig edge."""
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            m = re.search(r"([^/]+)\.(region\d{3})\.gbk$", name)
            if not m or "__MACOSX" in name:
                continue
            text = zf.read(name).decode(errors="replace")
            a = re.search(r"Orig\. start\s*::\s*(\d+)", text)
            b = re.search(r"Orig\. end\s*::\s*(\d+)", text)
            if not (a and b):
                raise ReportError(f"{zip_path}:{name}: no original region coordinates")
            edge = re.search(r'/contig_edge="(\w+)"', text)
            out.append(dict(contig=m.group(1), region=m.group(2), start=int(a.group(1)), end=int(b.group(1)),
                            products=sorted(set(re.findall(r'/product="([^"]+)"', text))),
                            categories=sorted(set(re.findall(r'/category="([^"]+)"', text))),
                            contig_edge=bool(edge and edge.group(1) == "True")))
    if not out:
        raise ReportError(f"{zip_path}: no antiSMASH region files")
    keys = [(r["contig"], r["region"]) for r in out]
    if len(set(keys)) != len(keys):
        raise ReportError(f"{zip_path}: repeated region file")
    return out


def pfam_names(names_tsv=None, hmm=None):
    if names_tsv:
        return {r["accession"].split(".")[0]: r["name"] for r in read_tsv(names_tsv, ["accession", "name"])}
    if hmm:
        names, name = {}, None
        with open(hmm, errors="replace") as fh:
            for line in fh:
                if line.startswith("NAME "):
                    name = line.split(None, 1)[1].strip()
                elif line.startswith("ACC ") and name:
                    names[line.split(None, 1)[1].strip().split(".")[0]] = name
                    name = None
        return names
    return {}


def build(genomes, aliases=None, names=None, group_order=None):
    """Tables only (no drawing): calls, regions, per-genome summary."""
    from gap_rescue_locus_map import _gecco_contig_map
    names = names or {}
    alias = {(r["strain"], r["contig"], r["region"]): r["bgc_alias"] for r in (aliases or [])}
    seen = set()
    calls, regions, summary = [], [], []
    for g in genomes:
        strain, group = g["strain"], g["group"]
        role, genus = (g.get("role") or "isolate").strip(), (g.get("genus") or "").strip()
        if role not in ("isolate", "reference", "SID"):
            raise ReportError(f"{strain}: role must be isolate, reference or SID, not {role!r}")
        if strain in seen:
            raise ReportError(f"strain {strain} listed twice")
        seen.add(strain)
        regs = antismash_regions(g["antismash_zip"])
        for r in regs:
            a = alias.get((strain, r["contig"], r["region"]))
            r.update(strain=strain, group=group,
                     identity=f"{strain} / {r['contig']} / {r['region']} / {a}" if a else
                     f"{strain} / {r['contig']} / {r['region']} / alias not supplied", calls=[])
        with open(g["gecco_clusters"], newline="") as fh:
            cl = list(csv.DictReader(fh, delimiter="\t"))
        need = {"sequence_id", "cluster_id", "start", "end", "type", "max_p", "average_p", "proteins", "domains"}
        if cl and not need <= set(cl[0]):
            raise ReportError(f"{g['gecco_clusters']}: not a GECCO 0.11 clusters table")
        cmap = _gecco_contig_map({c["sequence_id"] for c in cl}, {r["contig"] for r in regs})
        by_contig = defaultdict(list)
        for r in regs:
            by_contig[r["contig"]].append(r)
        n_in = 0
        for c in cl:
            s0, e = int(c["start"]) - 1, int(c["end"])
            contig = cmap.get(c["sequence_id"])
            hit = [r for r in by_contig.get(contig, []) if s0 < r["end"] and e > r["start"]] if contig else []
            for r in hit:
                r["calls"].append(c["cluster_id"])
            n_in += bool(hit)
            doms = [d for d in (c.get("domains") or "").split(";") if d]
            dcount = Counter(doms)
            calls.append(dict(
                strain=strain, group=group, role=role, genus=genus, contig=contig or c["sequence_id"],
                contig_source="joined to antiSMASH contig" if contig else "as written by GECCO (no region on this contig)",
                cluster_id=c["cluster_id"], start_1based=c["start"], end_inclusive=c["end"],
                gecco_type=c["type"] or "Unknown", drawn_type=gecco_type(c["type"]),
                max_p=c["max_p"], average_p=c["average_p"], **{k: c.get(k, "") for k in PROB_COLS},
                n_genes=len([p for p in (c.get("proteins") or "").split(";") if p]),
                pfam_domains="; ".join(f"{d} ({names.get(d.split('.')[0], 'not in the supplied Pfam release')})" + (f" x{n}" if n > 1 else "")
                                       for d, n in sorted(dcount.items())),
                state="OVERLAPS_REGION" if hit else "NO_REGION_OVERLAP",
                overlapping_regions=" | ".join(r["identity"] for r in hit),
                overlapping_categories=";".join(sorted({x for r in hit for x in r["categories"]}))))
        regions.extend(regs)
        summary.append(dict(strain=strain, group=group, role=role, genus=genus, regions=len(regs), regions_with_gecco=sum(bool(r["calls"]) for r in regs),
                            gecco_calls=len(cl), calls_in_regions=n_in, calls_outside_regions=len(cl) - n_in,
                            types=";".join(f"{t}:{n}" for t, n in Counter(gecco_type(c["type"]) for c in cl).most_common())))
    iso_groups = {g["group"] for g in genomes if (g.get("role") or "isolate").strip() == "isolate"}
    order = list(group_order or dict.fromkeys(g["group"] for g in genomes if g["group"] in iso_groups))
    if set(order) != iso_groups:
        raise ReportError(f"--group-order {order} does not name every isolate group")
    return calls, regions, summary, order


def write_tsv(path, rows, fields):
    with open(path, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _palette():
    from mamey.figures_extra import _CLASS_PALETTE
    # first five house class colours, then two that stay distinct from them (Saccharide and Mixed must not both be purple)
    colours = dict(zip(["Polyketide", "NRP", "RiPP", "Terpene", "Saccharide"], _CLASS_PALETTE[:5]))
    colours.update(Alkaloid=_CLASS_PALETTE[8], Mixed=_CLASS_PALETTE[14], Unknown="#9a9a9a")
    return colours


def _save(fig, stem):
    from mamey.figure_stamp import savefig_metadata
    out = []
    for ext, kw in ((".pdf", {}), (".png", {"dpi": 600}), (".svg", {})):
        p = stem.with_suffix(ext)
        fig.savefig(p, bbox_inches="tight", metadata=savefig_metadata(p, TOOL), **kw)
        out.append(p)
    return out


def _band(png, caption):
    """House rule 2: <base>_plot_only.png beside <base>.png, and the caption baked under a crop line (<base>_with_caption)."""
    import shutil
    from caption_band import add_band
    shutil.copyfile(png, png.with_name(png.stem + "_plot_only.png"))
    made = add_band(png, caption)
    return [png.with_name(png.stem + "_plot_only.png"), Path(made)]


def fig_calls_by_genome(calls, summary, order, folder):
    calls = [c for c in calls if c["role"] == "isolate"]; summary = [s for s in summary if s["role"] == "isolate"]
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    plt.rcParams.update({"font.family": "Arial", "font.size": MIN_PT, "pdf.fonttype": 42, "svg.fonttype": "none"})
    colours = _palette()
    rows = [s for grp in order for s in summary if s["group"] == grp]
    count = defaultdict(Counter)
    for c in calls:
        count[c["strain"]][(c["drawn_type"], c["state"])] += 1
    # one header line per group, then its genomes, top to bottom
    lines = []
    for grp in order:
        lines.append(("group", grp))
        lines += [("genome", s) for s in rows if s["group"] == grp]
    h = 0.16 * len(lines) + 1.6
    fig, ax = plt.subplots(figsize=(6.5, h))
    ypos = list(range(len(lines)))[::-1]
    ticks, labels = [], []
    for yi, (kind, item) in zip(ypos, lines):
        if kind == "group":
            ax.text(-0.01, yi, item, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=MIN_PT,
                    fontweight="bold")
            continue
        ticks.append(yi); labels.append(item["strain"])
        left = 0
        for state, alpha, hatch in (("OVERLAPS_REGION", 1.0, None), ("NO_REGION_OVERLAP", 0.45, "////")):
            for t in TYPES:
                n = count[item["strain"]][(t, state)]
                if n:
                    ax.barh(yi, n, left=left, height=0.72, color=colours[t], alpha=alpha, hatch=hatch,
                            edgecolor="white" if hatch else colours[t], linewidth=0)
                    left += n
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, fontsize=MIN_PT)
    ax.set_xlabel("GECCO cluster calls")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(-0.6, len(lines) - 0.4)
    used = [t for t in TYPES if any(c["drawn_type"] == t for c in calls)]
    h1 = [Patch(facecolor=colours[t], label=t) for t in used]
    h2 = [Patch(facecolor="#666666", label="inside an antiSMASH region"),
          Patch(facecolor="#666666", alpha=0.45, hatch="////", edgecolor="white", label="outside every region")]
    ax_h = ax.get_position().height * h
    ax.legend(handles=h1 + h2, ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.45 / ax_h),
              fontsize=MIN_PT, title="GECCO type", title_fontsize=MIN_PT)
    folder.mkdir()
    files = _save(fig, folder / "gecco_calls_by_genome")
    plt.close(fig)
    data = [dict(strain=s["strain"], group=s["group"], drawn_type=t, state=st, calls=count[s["strain"]][(t, st)])
            for s in rows for t in TYPES for st in ("OVERLAPS_REGION", "NO_REGION_OVERLAP") if count[s["strain"]][(t, st)]]
    write_tsv(folder / "gecco_calls_by_genome_data.tsv", data, ["strain", "group", "drawn_type", "state", "calls"])
    n_in = sum(c["state"] == "OVERLAPS_REGION" for c in calls)
    tcount = Counter(c["drawn_type"] for c in calls)
    (folder / "gecco_calls_by_genome_CAPTION.md").write_text(
        "**GECCO cluster calls per genome, by GECCO type.** Each bar is one genome, grouped as listed; each segment counts "
        "GECCO calls of one type. Solid segments are calls that share at least one base with an antiSMASH region; light "
        f"segments are calls outside every antiSMASH region. {len(calls):,} calls in {len(rows)} genomes: {n_in:,} inside "
        f"antiSMASH regions and {len(calls) - n_in:,} outside. By type: "
        + ", ".join(f"{t} {tcount[t]:,}" for t in TYPES if tcount[t]) + ". Mixed means GECCO assigned more than one type "
        "(listed as written in gecco_calls.tsv). GECCO was run at its default probability threshold; calls and their "
        "domains are listed in gecco_calls.tsv. A GECCO call is a second opinion on biosynthetic capacity from protein "
        "domains; it does not prove a cluster, and a call outside every antiSMASH region is not evidence of a new pathway.\n")
    return files + _band(folder / "gecco_calls_by_genome.png", folder / "gecco_calls_by_genome_CAPTION.md")


def _midrank_percentile(value, refs):
    """Mid-rank percentile of value among refs (ties count half), as the chitin comparison reports it."""
    below = sum(1 for r in refs if r < value); same = sum(1 for r in refs if r == value)
    return 100.0 * (below + 0.5 * same) / len(refs)


def fig_calls_vs_references(summary, order, folder, min_refs=5, per_mb=False):
    """Each isolate's GECCO calls (a) and calls outside every antiSMASH region (b) against the reference genomes of its
    genus: a box (median, quartiles, whiskers at the 5th and 95th percentiles) with five or more references, the
    individual reference values below five, and the isolate as a diamond. SID genomes are not in the reference box.
    per_mb: divide both measures by the genome size (summary column genome_bp), so genomes of different size compare."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family": "Arial", "font.size": MIN_PT, "pdf.fonttype": 42, "svg.fonttype": "none",
                         "mathtext.fontset": "custom", "mathtext.it": "Arial:italic", "mathtext.rm": "Arial"})   # genus names in italics
    refs = defaultdict(list)
    for r in summary:
        if r["role"] == "reference" and r["genus"]:
            refs[r["genus"]].append(r)
    iso = [r for grp in order for r in summary if r["role"] == "isolate" and r["group"] == grp]
    lines = []
    for grp in order:
        rows = [r for r in iso if r["group"] == grp]
        if rows:
            lines.append(("group", grp)); lines += [("genome", r) for r in rows]
    h = 0.17 * len(lines) + 1.3
    fig, axes = plt.subplots(1, 2, figsize=(6.5, h), sharey=True)
    ypos = list(range(len(lines)))[::-1]
    pct = []
    measures = (((axes[0], "gecco_calls", "GECCO calls per Mb"), (axes[1], "calls_outside_regions", "GECCO calls outside every\nantiSMASH region, per Mb"))
                if per_mb else ((axes[0], "gecco_calls", "GECCO calls per genome"),
                                (axes[1], "calls_outside_regions", "GECCO calls outside every antiSMASH region")))
    value = (lambda r, k: float(r[k]) / (float(r["genome_bp"]) / 1e6)) if per_mb else (lambda r, k: int(r[k]))
    for ax, key, xlabel in measures:
        ticks, labels = [], []
        for yi, (kind, item) in zip(ypos, lines):
            if kind == "group":
                if ax is axes[0]:
                    ax.text(-0.02, yi, item, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=MIN_PT, fontweight="bold")
                continue
            ticks.append(yi); labels.append(f"{item['strain']} (" + (f"$\\it{{{item['genus']}}}$" if item["genus"] else "genus not given") + ")")
            vals = [value(r, key) for r in refs.get(item["genus"], []) if str(r[key]).strip() != ""]   # a blank cell: not counted for this measure only
            if len(vals) >= min_refs:
                q = np.percentile(vals, [5, 25, 50, 75, 95])
                ax.bxp([dict(whislo=q[0], q1=q[1], med=q[2], q3=q[3], whishi=q[4], fliers=[])], positions=[yi], orientation="horizontal",
                       widths=0.6, showfliers=False, patch_artist=True,
                       boxprops=dict(facecolor="#dddddd", edgecolor="#888888", linewidth=0.6),
                       medianprops=dict(color="#555555", linewidth=0.8), whiskerprops=dict(color="#888888", linewidth=0.6),
                       capprops=dict(color="#888888", linewidth=0.6))
            elif vals:
                ax.plot(vals, [yi] * len(vals), "|", color="#888888", markersize=6, markeredgewidth=0.8)
            v = value(item, key)
            ax.plot([v], [yi], "D", color="#b03a3a", markersize=4.5, zorder=3)
            pct.append(dict(strain=item["strain"], group=item["group"], genus=item["genus"], measure=key + ("_per_Mb" if per_mb else ""), isolate_value=f"{v:.3g}" if per_mb else v,
                            reference_genomes=len(vals),
                            reference_median=f"{np.median(vals):g}" if vals else "",
                            midrank_percentile=f"{_midrank_percentile(v, vals):.0f}" if len(vals) >= min_refs else
                            ("range only" if vals else "no references")))
        ax.set_yticks(ticks); ax.set_yticklabels(labels, fontsize=MIN_PT)
        ax.set_xlabel(xlabel); ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(-0.6, len(lines) - 0.4); ax.set_xlim(left=0)
    axes[0].set_title("a", loc="left", fontweight="bold", fontsize=MIN_PT + 1)
    axes[1].set_title("b", loc="left", fontweight="bold", fontsize=MIN_PT + 1)
    folder.mkdir()
    files = _save(fig, folder / "gecco_calls_vs_references")
    plt.close(fig)
    write_tsv(folder / "isolate_percentiles.tsv", pct, list(pct[0]))
    n_ref = {g: len(v) for g, v in refs.items()}
    (folder / "gecco_calls_vs_references_CAPTION.md").write_text(
        "**GECCO calls of each isolate against the reference genomes of its genus.** (**a**) GECCO cluster calls per "
        + ("Mb of genome; (**b**) calls outside every antiSMASH region, per Mb. " if per_mb else "genome; (**b**) calls outside every antiSMASH region. ") + "Each row is one isolate (red diamond), grouped as listed, with the "
        f"public reference genomes of its genus behind it: a box (median, quartiles, whiskers at the 5th and 95th percentiles) "
        f"where there are at least {min_refs} references, otherwise one tick per reference. Reference genomes per genus: "
        + "; ".join(f"*{g}* {n}" for g, n in sorted(n_ref.items())) + ". SID genomes are not in the reference boxes. "
        "Each isolate's mid-rank percentile is in isolate_percentiles.tsv. GECCO was run with the same settings on every "
        "genome; references held only as antiSMASH region files could not be run and are not counted. Assembly "
        "fragmentation raises call counts in draft genomes, so a high count is not by itself more biosynthetic capacity.\n")
    return files + _band(folder / "gecco_calls_vs_references.png", folder / "gecco_calls_vs_references_CAPTION.md")


def fig_type_vs_category(calls, folder):
    """GECCO type (columns) against the antiSMASH category of the overlapping region (rows). Isolates only: counts.
    With reference genomes supplied: two panels, isolates and public references, each as the percentage of its row."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "font.size": MIN_PT, "pdf.fonttype": 42, "svg.fonttype": "none"})
    sets = [("Isolates", [c for c in calls if c["role"] == "isolate" and c["state"] == "OVERLAPS_REGION"])]
    refs = [c for c in calls if c["role"] == "reference" and c["state"] == "OVERLAPS_REGION"]
    if refs:
        sets.append(("Reference genomes", refs))
    pct = len(sets) > 1
    allin = [c for _, cs in sets for c in cs]
    cats = sorted({x for c in allin for x in c["overlapping_categories"].split(";") if x}) or ["category not recorded"]
    types = [t for t in TYPES if any(c["drawn_type"] == t for c in allin)]
    mats = []
    for _, cs in sets:
        m = [[sum(1 for c in cs if c["drawn_type"] == t and cat in (c["overlapping_categories"] or "category not recorded").split(";"))
              for t in types] for cat in cats]
        mats.append(m)
    fig, axes = plt.subplots(1, len(sets), figsize=((0.6 * len(types) + 0.4) * len(sets) + 1.6, 0.32 * len(cats) + 1.4),
                             sharey=True, squeeze=False)
    rows_out = []
    for ax, (title, cs), m in zip(axes[0], sets, mats):
        show = [[(100.0 * v / sum(r)) if sum(r) else 0.0 for v in r] for r in m] if pct else m
        vmax = max(max(r) for r in show) or 1
        ax.imshow(show, cmap="Greys", vmin=0, vmax=vmax * 1.25, aspect="auto")
        for i, r in enumerate(show):
            for j, v in enumerate(r):
                if m[i][j]:
                    ax.text(j, i, f"{v:.0f}" if pct else f"{v}", ha="center", va="center", fontsize=MIN_PT,
                            color="white" if v > vmax * 0.6 else "black")
                rows_out.append(dict(set=title, antismash_category=cats[i], gecco_type=types[j], calls=m[i][j],
                                     row_percent=f"{100.0 * m[i][j] / sum(m[i]):.1f}" if sum(m[i]) else ""))
        ax.set_xticks(range(len(types))); ax.set_xticklabels(types, rotation=45, ha="right")
        ax.set_yticks(range(len(cats))); ax.set_yticklabels(cats)
        ax.set_xlabel("GECCO type")
        if len(sets) > 1:
            ax.set_title(f"{title} ({len(cs):,} calls)", fontsize=MIN_PT)
    axes[0][0].set_ylabel("antiSMASH category of the overlapping region")
    folder.mkdir()
    files = _save(fig, folder / "gecco_type_vs_antismash_category")
    plt.close(fig)
    write_tsv(folder / "gecco_type_vs_antismash_category_data.tsv", rows_out,
              ["set", "antismash_category", "gecco_type", "calls", "row_percent"])
    head = ("**GECCO type against the antiSMASH category of the overlapping region, in the isolates and in the public "
            "reference genomes of their genera.** Each cell is the percentage of a row's GECCO calls of one type (columns) "
            "that overlap an antiSMASH region of that category (rows); counts are in the data table. "
            f"Isolates: {len(sets[0][1]):,} calls; reference genomes: {len(refs):,} calls. ") if pct else (
            "**GECCO type against the antiSMASH category of the overlapping region.** Each cell counts GECCO calls of one type "
            f"(columns) that overlap at least one antiSMASH region of one category (rows), over the {len(sets[0][1]):,} calls "
            "that overlap a region. ")
    (folder / "gecco_type_vs_antismash_category_CAPTION.md").write_text(
        head + "A call overlapping regions of several categories, or a region with several categories (a hybrid), counts once "
        "in each, so rows can sum to more than the number of calls. Categories are antiSMASH's own protocluster category; "
        "GECCO types are as GECCO assigns them. Agreement between the two detectors is agreement of class prediction, not "
        "of product.\n")
    return files + _band(folder / "gecco_type_vs_antismash_category.png", folder / "gecco_type_vs_antismash_category_CAPTION.md")

def _main_summary(a, out):
    """--summary: draw the calls-against-references figure from a per-genome summary computed elsewhere."""
    need = ["strain", "group", "role", "genus", "gecco_calls", "calls_outside_regions"] + (["genome_bp"] if a.per_mb else [])
    try:
        summary = read_tsv(a.summary, need)
    except (ReportError, OSError) as e:
        _OUT.error(f"refused: {e}")
        return 2
    bad = [r["strain"] for r in summary if r["role"] not in ("isolate", "reference", "SID")]
    if bad:
        _OUT.error(f"refused: role must be isolate, reference or SID ({bad[:3]})")
        return 2
    if a.per_mb and any(not r["genome_bp"] or float(r["genome_bp"]) <= 0 for r in summary):
        _OUT.error("refused: --per-mb needs a positive genome_bp on every row")
        return 2
    iso_groups = list(dict.fromkeys(r["group"] for r in summary if r["role"] == "isolate"))
    order = a.group_order.split(",") if a.group_order else iso_groups
    if set(order) != set(iso_groups):
        _OUT.error(f"refused: --group-order {order} does not name every isolate group")
        return 2
    out.mkdir(parents=True)
    figures = fig_calls_vs_references(summary, order, out / "calls_vs_references", per_mb=a.per_mb)
    from _min_text_check import text_sizes
    for p in figures:
        if p.suffix == ".pdf":
            sizes = text_sizes(str(p))
            if not sizes or min(sizes)[0] < MIN_PT - 0.05:
                _OUT.error(f"refused: {p.name} has text below {MIN_PT} pt ({min(sizes) if sizes else None})")
                return 2
    receipt = dict(tool=TOOL, schema="sapote.gecco-cohort-report.v1", mode="summary", per_mb=a.per_mb,
                   inputs_sha256={a.summary: sha256(a.summary)}, group_order=order, genomes=len(summary),
                   overlap_rule="as computed by the summary's producer; must be: a call and a region overlap when they share at least one base on the same contig",
                   outputs_sha256={str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob("*")) if p.is_file()})
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    _OUT.info(f"wrote {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--genomes", help="genomes TSV (see Inputs); required unless --summary is given")
    ap.add_argument("--summary", help="a per-genome summary computed elsewhere (columns strain, group, role, genus, gecco_calls, calls_outside_regions; genome_bp for --per-mb), drawn as the calls-against-references figure only, for reference genomes whose antiSMASH zips are on another machine. The overlap rule must be the one stated in Rules.")
    ap.add_argument("--per-mb", action="store_true", help="calls-against-references figure per Mb of genome (needs genome_bp)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--aliases")
    ap.add_argument("--pfam-names")
    ap.add_argument("--pfam-hmm")
    ap.add_argument("--group-order")
    ap.add_argument("--no-figures", action="store_true", help="tables and receipt only")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        _OUT.error(f"refused: {out} exists; give a new output folder")
        return 2
    if bool(a.genomes) == bool(a.summary):
        _OUT.error("refused: give --genomes or --summary, not both and not neither")
        return 2
    if a.summary:
        return _main_summary(a, out)
    try:
        genomes = read_tsv(a.genomes, ["strain", "group", "antismash_zip", "gecco_clusters"])
        aliases = read_tsv(a.aliases, ["strain", "contig", "region", "bgc_alias"]) if a.aliases else None
        names = pfam_names(a.pfam_names, a.pfam_hmm)
        calls, regions, summary, order = build(genomes, aliases, names, a.group_order.split(",") if a.group_order else None)
    except (ReportError, OSError, zipfile.BadZipFile) as e:
        _OUT.error(f"refused: {e}")
        return 2
    out.mkdir(parents=True)
    write_tsv(out / "gecco_calls.tsv", calls, list(calls[0]) if calls else ["strain"])
    write_tsv(out / "regions_with_gecco.tsv",
              [dict(identity=r["identity"], group=r["group"], start_0based=r["start"], end_exclusive=r["end"],
                    products=";".join(r["products"]), categories=";".join(r["categories"]), contig_edge=r["contig_edge"],
                    gecco_calls=";".join(r["calls"])) for r in regions],
              ["identity", "group", "start_0based", "end_exclusive", "products", "categories", "contig_edge", "gecco_calls"])
    write_tsv(out / "summary_by_genome.tsv", summary, list(summary[0]))
    typed_out = [c for c in calls if c["role"] == "isolate" and c["state"] == "NO_REGION_OVERLAP" and c["drawn_type"] != "Unknown"]
    lines = ["# GECCO calls outside every antiSMASH region, with a GECCO type", "",
             f"{len(typed_out)} of {sum(c['state'] == 'NO_REGION_OVERLAP' and c['role'] == 'isolate' for c in calls)} isolate calls outside every antiSMASH region "
             "carry a GECCO type other than Unknown. Each is named strain / contig / interval (1-based, inclusive) / GECCO cluster; "
             "domains are GECCO's Pfam annotations, with counts. A call outside every region is a candidate to read gene by gene, "
             "not evidence of a new pathway.", "",
             "| Identity | Group | GECCO type | Max probability | Genes | Pfam domains |", "|---|---|---|---|---|---|"]
    for c in sorted(typed_out, key=lambda c: (order.index(c["group"]), c["strain"], -float(c["max_p"] or 0))):
        lines.append(f"| {c['strain']} / {c['contig']} / {c['start_1based']}–{c['end_inclusive']} / {c['cluster_id']} | {c['group']} | "
                     f"{c['gecco_type']} | {float(c['max_p']):.3f} | {c['n_genes']} | {c['pfam_domains'] or 'none listed'} |")
    (out / "gecco_calls_outside_regions_typed.md").write_text("\n".join(lines) + "\n")
    figures = []
    if not a.no_figures and calls:
        figures += fig_calls_by_genome(calls, summary, order, out / "calls_by_genome")
        figures += fig_type_vs_category(calls, out / "type_vs_category")
        if any(r["role"] == "reference" for r in summary):
            figures += fig_calls_vs_references(summary, order, out / "calls_vs_references")
        from _min_text_check import text_sizes
        from pypdf import PdfReader
        text_check = {}
        for p in figures:
            if p.suffix == ".pdf":
                sizes = text_sizes(str(p))
                smallest = min(sizes) if sizes else (None, "")
                width = round(float(PdfReader(str(p)).pages[0].mediabox.width) / 72, 2)
                text_check[p.name] = dict(smallest_pt=smallest[0], smallest_text=smallest[1], page_width_in=width)
                if not sizes or smallest[0] < MIN_PT - 0.05:
                    _OUT.error(f"refused: {p.name} has text below {MIN_PT} pt ({smallest})")
                    return 2
    inputs = {}
    for g in genomes:
        for k in ("antismash_zip", "gecco_clusters"):
            inputs[g[k]] = sha256(g[k])
    for p in (a.genomes, a.aliases, a.pfam_names):
        if p:
            inputs[p] = sha256(p)
    receipt = dict(tool=TOOL, schema="sapote.gecco-cohort-report.v1", inputs_sha256=inputs, pfam_hmm=a.pfam_hmm,
                   text_check=locals().get("text_check", {}), min_text_pt=MIN_PT,
                   group_order=order, genomes=len(genomes), calls=len(calls), regions=len(regions),
                   overlap_rule="a call and a region overlap when they share at least one base on the same contig",
                   contig_rule="exact name, else a unique NODE_n_length_L alias (tools/gap_rescue_locus_map._gecco_contig_map)",
                   outputs_sha256={str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob("*")) if p.is_file()},
                   claim_ceiling="GECCO is a second opinion on capacity; a call is not proof of a cluster.")
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1))
    _OUT.info(f"{len(genomes)} genomes, {len(regions)} regions, {len(calls)} GECCO calls "
          f"({sum(c['state'] == 'OVERLAPS_REGION' for c in calls)} inside regions) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

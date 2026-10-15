"""M5_452 P5: caption, METHODS and GENOMES_USED for a protein PCoA page, written by tools/protein_pcoa_render.py --page from the page's
own receipts and tables (never hand-typed), then checked: tools/caption_guard.py on the caption and METHODS, tools/figure_render_qc.py
--ocr require on the page folder. Any finding refuses the page (the renderer exits 2 and the files stay as an incomplete attempt).
Called by the renderer, not by hand."""
from __future__ import annotations


import csv
import json
import statistics
import subprocess
import sys
from pathlib import Path

LAYOUT_NAME = {"pcoa": "principal coordinates analysis", "trimap": "TriMap", "tsne": "t-SNE"}


def _italic_name(display: str) -> str:
    """'Streptomyces laurentii ATCC 31255 [AP017424]' -> '*Streptomyces laurentii* ATCC 31255 [AP017424]'."""
    w = display.split(" ")
    return f"*{w[0]} {w[1]}*" + (" " + " ".join(w[2:]) if len(w) > 2 else "") if len(w) >= 2 and w[0][:1].isupper() else display


def _read(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _cli(args: dict) -> list[str]:
    """The render command line from the receipt's args (lists repeat the option; switches print bare)."""
    out = []
    for k, v in args.items():
        if v in (None, False, [], "") or k == "out":
            continue
        opt = "--" + k.replace("_", "-")
        out += ([f"{opt} {x!r}" if " " in str(x) else f"{opt} {x}" for x in v] if isinstance(v, list)
                else [opt] if v is True else [f"{opt} {v!r}" if " " in str(v) else f"{opt} {v}"])
    return out


def caption_text(rec: dict, labels: list[dict], names: dict, note: str | None) -> str:
    lays = rec["page"]; who = rec["legend"]["iso_low"].split(",")[0]
    per = sorted(rec["cohort_genomes"].values()); G = len(per)
    n_q, n_lo, n_md = rec["n_cohort_points"], rec["n_low"], rec["n_mid"]; n_hi = n_q - n_lo - n_md
    parts = [f"**{rec['title']}.** "
             + " and ".join(f"{LAYOUT_NAME[l][0].upper() + LAYOUT_NAME[l][1:] if k == 0 else LAYOUT_NAME[l]} (**{'abcdefgh'[k]}**)"
                            for k, l in enumerate(lays))
             + f" of the same points: {n_q:,} {who}s from {G} genomes (one point per protein; "
             + (f"{per[0]}–{per[-1]} per genome, median {statistics.median(per):g}" if G > 1 else f"{per[0]} proteins")
             + f"), {rec['n_ref_centroids']:,} reference cluster centroids representing {rec['n_ref']:,} proteins from "
             + f"{rec['n_reference_genomes']:,} reference genomes, and {rec['n_mibig_centroids']:,} MIBiG cluster centroids representing "
             + f"{rec['n_mibig']:,} proteins from characterized clusters."]
    if rec.get("approx_id"):
        parts.append(f"Reference and MIBiG proteins were clustered at {rec['approx_id']}% identity before ordination; a centroid is "
                     "drawn with area proportional to the number of proteins it represents.")
    lo, md = rec["label_below"], rec["mid_below"]
    parts.append(f"{who[0].upper() + who[1:]}s are coloured by the identity of their best match to any reference or MIBiG protein: "
                 f"dark red, < {lo:.0f}% ({n_lo:,}); light orange, {lo:.0f}–{md:.0f}% ({n_md:,}); open, ≥ {md:.0f}% ({n_hi:,}); they are "
                 "drawn over the reference and MIBiG points, which can lie hidden beneath them.")
    if rec.get("distance"):
        parts.append(f"Distances: {rec['distance']}.")
    axes = []
    for k, l in enumerate(lays):
        t = "abcdefgh"[k]
        if l == "pcoa" and rec.get("pct_axes"):
            axes.append(f"**{t}**, share of variance explained (axis 1, {rec['pct_axes'][0]:.1f}%; axis 2, {rec['pct_axes'][1]:.1f}%)")
        elif l != "pcoa":
            em = rec.get("embedding") or {}
            axes.append(f"**{t}**, unitless embedding coordinates" + (f" ({LAYOUT_NAME[l]} {em['version']}, seed {em['seed']})"
                                                                         if em.get("version") and em.get("seed") is not None else ""))
    if axes:
        parts.append("Axes: " + "; ".join(axes) + ".")
    drawn = [r for r in labels if r["drawn"] == "yes"]
    numbered = any(v["numbered"] for v in rec["labels"].values())
    fit = "; ".join(f"{v['labelled']} of {v['outlier_groups']} in **{'abcdefgh'[k]}**" for k, v in enumerate(rec["labels"].values()))
    rule = ("outlier proteins, those farther from every reference and MIBiG point than 95% of reference and MIBiG points are from "
            "their nearest neighbour (outliers of one genome lying close together share one label)")
    if numbered:
        key = sorted({(int(r["genome_number"]), r["strain"]) for r in drawn})
        parts.append(f"Numbers mark {rule}; each number is one genome, the same in every panel. Outlier groups labelled: {fit}; the "
                     f"others had no free label position within {rec['leader_max_in']} in at print size and are listed in "
                     f"LABELS_{rec['set']}_{rec['panel']}_PAGE.tsv. Key: "
                     + "; ".join(f"{n}, {_italic_name(names.get(s, s))}" for n, s in key) + ".")
    elif drawn:
        key = sorted({(r["label_text"].split(" x")[0], r["strain"]) for r in drawn})
        parts.append(f"Labels mark {rule}. Outlier groups labelled: {fit}; the others had no free label position within "
                     f"{rec['leader_max_in']} in at print size and are listed in LABELS_{rec['set']}_{rec['panel']}_PAGE.tsv. Labels: "
                     + "; ".join(f"*{t}*, {_italic_name(names.get(s, s))}" for t, s in key) + ".")
    else:
        parts.append(f"No outlier protein is labelled ({fit} outlier groups).")
    if note:
        parts.append(note.strip())
    parts.append("Proximity in a panel reflects sequence identity of these proteins only and does not establish product identity or "
                 "biosynthetic activity.")
    return f"# {rec['prefix']}\n\n" + " ".join(parts) + "\n"


def write_page_docs(out: Path, rec: dict, render: dict, meta: list[dict], names: dict, note: str | None, date: str) -> dict:
    try:
        from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    except ImportError:
        import os as _cs_os, sys as _cs_sys
        _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
        from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
    labels = _read(out / f"LABELS_{rec['set']}_{rec['panel']}_PAGE.tsv")
    cap = out / f"{rec['prefix']}_CAPTION.md"; meth = out / f"METHODS_{rec['prefix']}.md"; gen = out / f"GENOMES_USED_{rec['set']}.tsv"
    cap.write_text(caption_text(rec, labels, names, note))
    cohort = rec["cohort_genomes"]; num = rec["genome_numbers"]
    refs: dict[str, list] = {}
    for r in meta:
        if r.get("strain") and r.get("source") not in ("isolate", "MIBiG") and r["strain"] not in cohort:
            refs.setdefault(r["strain"], [r.get("source", ""), 0])[1] += 1
    with open(gen, "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n"); w.writerow(["genome", "role", "genome_number", "display_name", "proteins_in_set"])
        for s in sorted(cohort, key=lambda s: num.get(s, 10 ** 9)):
            w.writerow([s, "cohort", num.get(s, ""), names.get(s, ""), cohort[s]])
        for s, (src, n) in sorted(refs.items()):
            w.writerow([s, f"reference ({src})", "", "", n])
    mt = json.loads((out / f"{rec['prefix']}_min_text_check.json").read_text())
    lines = [f"# METHODS: {rec['prefix']} (written {date} by tools/protein_pcoa_page_docs.py)", "",
             f"Figure: `{rec['prefix']}.pdf` (vector, source artwork; {rec['min_text']['print_width']} in wide), `.svg`, `.png` (preview "
             f"rendered from the checked PDF). Caption: `{cap.name}`. Genomes: `{gen.name}`. Labels: `LABELS_{rec['set']}_{rec['panel']}_PAGE.tsv`.",
             "", "## Points", f"- cohort proteins: {rec['n_cohort_points']:,} from {len(cohort)} genomes (cohort table panel `{rec['panel']}`)",
             f"- reference: {rec['n_ref_centroids']:,} cluster centroids representing {rec['n_ref']:,} proteins from {rec['n_reference_genomes']:,} genomes "
             "(distinct non-cohort, non-MIBiG strains in the kit metadata)",
             f"- MIBiG: {rec['n_mibig_centroids']:,} centroids representing {rec['n_mibig']:,} proteins",
             f"- identity tiers (best reference/MIBiG match): < {rec['label_below']:.0f}% {rec['n_low']:,}; {rec['label_below']:.0f}-{rec['mid_below']:.0f}% "
             f"{rec['n_mid']:,}; >= {rec['mid_below']:.0f}% {rec['n_cohort_points'] - rec['n_low'] - rec['n_mid']:,}",
             "", "## Labels", f"- rule: {rec['label_rule']}", f"- placement: {rec['placement']}"]
    for k, (lay, v) in enumerate(rec["labels"].items()):
        lines.append(f"- panel {'abcdefgh'[k]} ({lay}): {v['labelled']} of {v['outlier_groups']} outlier groups labelled ({v['outlier_points']} outlier "
                     f"points; threshold {v['threshold']:.5g}); longest leader {v['longest_leader_in']:.3f} in; numbered: {v['numbered']}")
    lines += ["", "## Gates", f"- 8 pt floor read back from the PDF: {mt['status']} ({mt['text_runs']} text runs, smallest {mt['smallest_pt']} pt)",
              f"- PDF read-back (overlapping text, leaders > {rec['leader_max_in']} in): final draws {json.dumps(rec['final_draws'])}",
              "- tools/caption_guard.py and tools/figure_render_qc.py --ocr require: see QC_SUMMARY.json in this folder",
              "", "## Command", "```", "tools/protein_pcoa_render.py " + " ".join(_cli(render["args"])), "```",
              "", "## Software", f"- {json.dumps(render.get('rendering_runtime', {}))}",
              "", "## Inputs and outputs (sha256)"]
    for b in render.get("inputs", []) + render.get("outputs", []):
        lines.append(f"- `{b.get('path')}` {b.get('sha256', b.get('state', ''))}")
    meth.write_text("\n".join(lines) + "\n")
    return dict(caption=cap, methods=meth, genomes=gen)


def check_page_docs(out: Path, root: Path, docs: dict) -> dict:
    """caption_guard on caption + METHODS, figure_render_qc --ocr require on the folder; returns the summary (also QC_SUMMARY.json)."""
    sys.path.insert(0, str(root)); sys.path.insert(0, str(root / "tools"))
    from caption_guard import scan_paths
    guard = scan_paths([str(docs["caption"]), str(docs["methods"])])
    qc_dir = out / "QC_RENDER"
    r = subprocess.run([sys.executable, str(root / "tools" / "figure_render_qc.py"), str(out), "--out", str(qc_dir), "--ocr", "require"],
                       capture_output=True, text=True)
    summary = dict(caption_guard={k: [list(x) for x in v] for k, v in guard.items()}, figure_render_qc_exit=r.returncode,
                   figure_render_qc=(r.stdout.strip().splitlines() or [""])[-1])
    (out / "QC_SUMMARY.json").write_text(json.dumps(summary, indent=1))
    return summary

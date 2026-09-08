#!/usr/bin/env python3
"""assembly_line_pdf.py — print-ready PDF of every assembly-line BGC in a strain, N per page.

The interactive reader (`assembly_line_widget.py`) is one BGC at a time in a browser. This is the
paper/print companion: one panel per BGC, 4 or 6 to a page, every BGC in the strain, as a real PDF.

SINGLE SOURCE OF TRUTH — this imports `build_payload()` and `CATS` from `assembly_line_widget.py`
rather than re-deriving anything. The PDF and the widget therefore read the same package tables,
apply the same domain->category mapping and the same colours, and cannot drift apart. If the widget
is wrong, this is wrong in the same way, which is the correct failure mode for a companion view.

CLAIM SAFETY (mandatory, printed on every page): domain identities are antiSMASH Pfam/HMM
hypotheses (nrps_pks_domains); they do not prove product identity, expression or activity. Module
counts on contig-edge / truncated regions are a LOWER BOUND. Gene bars are each normalised to their
own aa length, so bar lengths are NOT comparable between genes. Class-level capacity only; judgment
deferred.

Usage:
  assembly_line_pdf.py --strain AS-XXX --runs-root <dir> --out <dir> [--per-page 6]
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import importlib.util
import os

# --- reuse the widget's own payload + palette (no re-derivation) --------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "assembly_line_widget_src", os.path.join(_HERE, "assembly_line_widget.py"))
_alw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_alw)

build_payload = _alw.build_payload
find_pkg = _alw.find_pkg
CATS = _alw.CATS
CAT_COLOR = _alw.CAT_COLOR

CLAIM_SAFETY = (
    "CLAIM SAFETY — Domain identities are antiSMASH Pfam/HMM hypotheses (nrps_pks_domains); they do "
    "not prove product identity, expression or activity. Substrate 'consensus' values are "
    "capacity-level PREDICTIONS, not confirmed monomer identity or a structure claim. Module counts "
    "on contig-edge / truncated regions are a LOWER BOUND. Each gene bar is normalised to its own aa "
    "length — bar lengths are NOT comparable between genes. Judgment deferred — Mamey extracts, "
    "Sapote judges."
)

MAX_GENES_PER_PANEL = 6   # deeper stacks become unreadable at 4-6 panels per page


def _draw_bgc(ax, b) -> None:
    """One BGC panel: a title line, then one normalised bar per gene with its domains."""
    ax.set_xlim(0, 1)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#d8dce3")

    genes = b["genes"][:MAX_GENES_PER_PANEL]
    hidden = len(b["genes"]) - len(genes)

    # Title and subtitle are drawn as explicit stacked text in axes coords. `ax.set_title(pad=…)`
    # was tried first and collided with the subtitle in every panel (the title sits at a pt-based
    # offset, the subtitle at a fraction of axes height, so they overlap at these panel sizes).
    products = b["products"] or "(class n/a)"
    if len(products) > 52:                       # long multi-class labels ran into the flag at right
        products = products[:51] + "…"
    title = f"{b['bgc_id']} — {products}"
    sub = (f"{b['n_domains']} aSDomains · {b['n_modules']} module(s), {b['n_complete']} complete · "
           f"boundary: {b['boundary'] or '?'}")
    ax.text(0, 1.135, title, transform=ax.transAxes, fontsize=7.2, fontweight="bold",
            color="#1b2129", va="bottom")
    ax.text(0, 1.030, sub, transform=ax.transAxes, fontsize=5.6, color="#5a6672", va="bottom")
    if b["boundary"] and any(k in str(b["boundary"]).lower() for k in ("edge", "truncat", "full-contig")):
        ax.text(1, 1.030, "LOWER BOUND (contig-edge)", transform=ax.transAxes, fontsize=5.4,
                color="#b0761f", va="bottom", ha="right")

    n = max(len(genes), 1)
    ax.set_ylim(0, n)
    for gi, g in enumerate(genes):
        y = n - gi - 1                      # top-down, genomic order
        aa = max(int(g.get("aa") or 1), 1)
        # the gene's own track
        ax.add_patch(__import__("matplotlib").patches.Rectangle(
            (0, y + 0.30), 1, 0.34, facecolor="#eef1f5", edgecolor="#d8dce3", linewidth=0.4))
        for d in g.get("domains", []):
            x0 = max(0.0, min(1.0, float(d.get("ps") or 0) / aa))
            x1 = max(0.0, min(1.0, float(d.get("pe") or 0) / aa))
            if x1 <= x0:
                continue
            ax.add_patch(__import__("matplotlib").patches.Rectangle(
                (x0, y + 0.30), x1 - x0, 0.34,
                facecolor=CAT_COLOR.get(d.get("cat"), "#9aa0ad"), edgecolor="none"))
            if (x1 - x0) > 0.055:           # only label a box wide enough to hold text
                ax.text((x0 + x1) / 2, y + 0.47, str(d.get("code") or "")[:9],
                        ha="center", va="center", fontsize=4.4, color="white")
        label = f"{g.get('locus','?')}  ·  {aa} aa"
        kind = (g.get("kind") or "").strip()
        if kind:
            label += f"  ·  {kind}"          # NB: full value, never truncated (cf. the widget's cap)
        ax.text(0, y + 0.72, label, fontsize=5.0, color="#3a4450", va="bottom")

    if hidden > 0:
        ax.text(1, -0.06, f"+{hidden} more gene lane(s) — see the interactive reader",
                transform=ax.transAxes, fontsize=5.0, color="#5a6672", ha="right", va="top")


def build_pdf(strain: str, runs_root: str, outdir: str, per_page: int = 6) -> str | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Patch

    pkg = find_pkg(runs_root, strain)
    if not pkg:
        emit(f"  [SKIP] {strain}: no antismash_modules.csv found under {runs_root}")
        return None
    payload = build_payload(strain, pkg)
    bgcs = payload["bgcs"]
    if not bgcs:
        emit(f"  [SKIP] {strain}: no NRPS/PKS assembly-line domains present")
        return None

    rows, cols = (3, 2) if per_page == 6 else (2, 2)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{strain}_assembly_lines.pdf")
    pages = (len(bgcs) + per_page - 1) // per_page

    with PdfPages(out) as pdf:
        for p in range(pages):
            chunk = bgcs[p * per_page:(p + 1) * per_page]
            fig, axes = plt.subplots(rows, cols, figsize=(11.69, 8.27))  # A4 landscape
            axes = axes.ravel()
            for ax in axes[len(chunk):]:
                ax.axis("off")
            for ax, b in zip(axes, chunk):
                _draw_bgc(ax, b)

            fig.suptitle(
                f"{strain} — NRPS/PKS assembly lines · page {p+1} of {pages} "
                f"({len(bgcs)} BGC(s) with assembly-line domain content)",
                fontsize=10, fontweight="bold", x=0.02, ha="left", y=0.985)
            fig.legend(handles=[Patch(facecolor=col, label=lab) for _, lab, col in CATS],
                       loc="lower left", bbox_to_anchor=(0.02, 0.055), ncol=4,
                       fontsize=5.6, frameon=False)
            fig.text(0.02, 0.012, CLAIM_SAFETY, fontsize=4.9, color="#5a6672", wrap=True)
            fig.subplots_adjust(left=0.035, right=0.985, top=0.90, bottom=0.115,
                                hspace=0.85, wspace=0.10)
            pdf.savefig(fig)
            plt.close(fig)

    emit(f"  [OK]   {strain}: {len(bgcs)} BGC(s) over {pages} page(s) ({per_page}/page) -> {out}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strain", help="one strain id (e.g. AS-XXX)")
    ap.add_argument("--strains", nargs="+", help="several strain ids")
    ap.add_argument("--runs-root", required=True, help="directory of sealed per-strain packages")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--per-page", type=int, default=6, choices=(4, 6),
                    help="BGC panels per page (default 6)")
    a = ap.parse_args()
    strains = a.strains or ([a.strain] if a.strain else None)
    if not strains:
        ap.error("give --strain or --strains")
    n = 0
    for s in strains:
        if build_pdf(s, a.runs_root, a.out, a.per_page):
            n += 1
    emit(f"assembly-line-pdf: {n}/{len(strains)} strain PDF(s) -> {a.out}",
         "  Class-level CAPACITY only; domain calls are HMM hypotheses; judgment deferred.",
         sep="\n")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())

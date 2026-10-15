#!/usr/bin/env python3
"""Study workflow figure (figure type W01): a row of chevrons, one per stage, each with a photo and a short label.

This is the paper's study-design panel (collection, isolation, bioassay, genomes), not the software diagram drawn by
build_workflow_figure.py. Input is an explicit stage table:

  --stages TSV  stage, label, photo, frame, crop
      label  text under the photo; "|" breaks the line; words listed with --italic are set in italics
      photo  image path (relative to --root); blank draws a dashed "photo to come" placeholder
      frame  circle (square crop, round mask), card (whole image on a white rounded card) or locus (photo is an
             antiSMASH region .gbk, drawn as one gene-arrow ribbon on a card, genes coloured by role with the
             gene-cluster-family renderer's role table; no text)
      crop   for circle frames: "cx,cy,side" as fractions of the image (centre x, centre y, side of the shorter edge)

The page is exactly --print-width wide (default 7.2 in) and every label is at least 8 pt; a label wider than its
chevron is refused, never shrunk. Writes PNG (600 dpi) and PDF, both stamped, and RUN_INFO.json with the SHA-256 of
the stage table and of every photo. Refuses an output that exists and a photo that is missing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MIN_PT = 8.0
INK, SUB = "#17212E", "#54637A"
FILL = ["#E9EEF4", "#DDE6EF", "#D1DDEA", "#C5D4E5", "#B9CBE0", "#ADC2DB"]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def square_crop(path: Path, crop: str, size: int = 1200):
    import numpy as np
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB"); w, h = im.size
    fx, fy, fs = (float(v) for v in crop.split(",")) if crop.strip() else (0.5, 0.5, 1.0)
    if not (0 < fs <= 1 and 0 <= fx <= 1 and 0 <= fy <= 1):
        raise ValueError(f"{path.name}: crop must be three fractions cx,cy,side with 0 < side <= 1")
    s = int(min(w, h) * fs); x = min(max(int(fx * w - s / 2), 0), w - s); y = min(max(int(fy * h - s / 2), 0), h - s)
    return np.asarray(im.crop((x, y, x + s, y + s)).resize((size, size), Image.LANCZOS))


def core_span(gbk: Path, flipped: bool, length: int, pad: int = 2000):
    """Span of the region's antiSMASH protocluster cores (proto_core features) plus pad bp each side, in the
    orientation read_cluster used; None when the file has no proto_core feature."""
    import re as _re
    spans = []
    feat = None
    for line in Path(gbk).read_text(errors="replace").splitlines():
        m = _re.match(r"^     (\S+)\s+(complement\()?<?(\d+)\.\.>?(\d+)", line)
        if m:
            feat = m.group(1)
            if feat == "proto_core":
                spans.append((int(m.group(3)) - 1, int(m.group(4))))
        if line.startswith("ORIGIN"):
            break
    if not spans:
        return None
    lo, hi = max(0, min(a for a, _ in spans) - pad), min(length, max(b for _, b in spans) + pad)
    return (length - hi, length - lo) if flipped else (lo, hi)


def draw_locus(ax, gbk: Path, cx: float, cy: float, r: float) -> None:
    """One region as a gene-arrow ribbon on a white card: the protocluster core(s) plus 2 kb each side, arrows to scale
    in the coding direction, coloured by role (unknown function light grey), thin white separators, no text."""
    from matplotlib.patches import FancyArrow, FancyBboxPatch
    from tools.render_gcf_synteny_tree import read_cluster, ROLE_COLOURS, UNKNOWN
    cl = read_cluster(str(gbk))
    span = core_span(gbk, cl["flipped"], cl["length"])
    genes = [g for g in cl["genes"] if span is None or (g["end"] > span[0] and g["start"] < span[1])]
    if not genes:
        raise ValueError(f"{gbk.name}: no CDS features to draw")
    bw_, bh = 2 * r * 1.15, 2 * r
    ax.add_patch(FancyBboxPatch((cx - bw_ / 2 - 0.12, cy - bh / 2 - 0.12), bw_ + 0.24, bh + 0.24,
                                boxstyle="round,pad=0,rounding_size=0.35", fc="white", ec="#D5DCE5", lw=0.6, zorder=3))
    lo = min(g["start"] for g in genes); hi = max(g["end"] for g in genes)
    x0, width = cx - bw_ / 2 + 0.25, bw_ - 0.5
    sc = width / max(1, hi - lo)
    ax.plot([x0, x0 + width], [cy, cy], color="#9AA3AE", lw=0.8, zorder=4)
    h = 0.95
    for g in genes:
        a0, a1 = x0 + (g["start"] - lo) * sc, x0 + (g["end"] - lo) * sc
        w = a1 - a0; head = min(0.28, 0.45 * w)
        args = (a0, cy, w) if g["strand"] >= 0 else (a1, cy, -w)
        fc = "#D5DCE5" if g["role"] == UNKNOWN[0] else ROLE_COLOURS[g["role"]]
        ax.add_patch(FancyArrow(*args, 0, width=h, head_width=h * 1.35, head_length=head, length_includes_head=True,
                                fc=fc, ec="white", lw=0.5, zorder=5))
    return {"genes_drawn": len(genes), "span_bp": [int(lo), int(hi)], "core_cropped": span is not None}


def styled(text: str, italic: list[str]) -> str:
    for it in italic:
        text = text.replace(it, "$\\mathit{" + it.replace(" ", "\\ ") + "}$")
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stages", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="folder that photo paths are relative to")
    ap.add_argument("--out", type=Path, required=True, help="output stem, without suffix")
    ap.add_argument("--print-width", type=float, default=7.2)
    ap.add_argument("--italic", action="append", default=["in vitro", "in vivo"], help="phrase set in italics (repeatable)")
    ap.add_argument("--dpi", type=int, default=600)
    a = ap.parse_args(argv)
    try:
        return run(a)
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        ap.exit(2, f"study_workflow_figure: {exc}\n")


def run(a) -> int:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Circle, FancyBboxPatch
    from PIL import Image, ImageOps
    outs = [a.out.with_suffix(".png"), a.out.with_suffix(".pdf"), Path(str(a.out) + "_RUN_INFO.json")]
    if any(p.exists() for p in outs):
        raise FileExistsError(f"refusing to overwrite {a.out}.*")
    with a.stages.open(newline="", encoding="utf-8-sig") as fh:
        st = list(csv.DictReader(fh, delimiter="\t"))
    need = {"stage", "label", "photo", "frame", "crop"}
    if not st or not need <= set(st[0]):
        raise ValueError(f"{a.stages}: needs columns {sorted(need)}")
    photos = []
    for s in st:
        s = {k: (v or "").strip() for k, v in s.items()}
        if s["frame"] not in ("circle", "card", "locus", ""):
            raise ValueError(f"stage {s['stage']}: frame must be circle, card or locus")
        if s["photo"]:
            p = a.root / s["photo"]
            if not p.is_file():
                raise FileNotFoundError(f"stage {s['stage']}: photo not found: {p}")
            photos.append({"stage": s["stage"], "path": str(p), "sha256": sha(p)})
    plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "mathtext.fontset": "custom",
                         "mathtext.rm": "Arial:bold", "mathtext.it": "Arial:italic:bold", "mathtext.bf": "Arial:bold"})
    n = len(st); Wd, top, lo = 10.0, 9.2, 1.9
    FW = a.print_width
    FH = FW * (top + 0.4 - lo) / (Wd * n)
    fig = plt.figure(figsize=(FW, FH))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, Wd * n); ax.set_ylim(lo, top + 0.4); ax.axis("off")
    labels = []
    for i, s in enumerate(st):
        x0 = i * Wd; tip = 1.4; y0 = 2.1; ym = (y0 + top) / 2
        pts = [(x0, y0), (x0 + Wd - tip, y0), (x0 + Wd, ym), (x0 + Wd - tip, top), (x0, top)] + ([] if i == 0 else [(x0 + tip, ym)])
        ax.add_patch(Polygon(pts, closed=True, fc=FILL[i % len(FILL)], ec="white", lw=1.5))
        cx, cy, r = x0 + Wd / 2 - 0.2, 6.85, 1.85
        photo, frame = (s.get("photo") or "").strip(), (s.get("frame") or "circle").strip() or "circle"
        if photo and frame == "locus":
            draw_locus(ax, a.root / photo, cx, cy, r)
        elif photo and frame == "card":
            im0 = ImageOps.exif_transpose(Image.open(a.root / photo)).convert("RGB"); w, h = im0.size
            bw_, bh = 2 * r * 1.15, 2 * r; sc = min(bw_ / w, bh / h); iw, ih = w * sc, h * sc
            ax.add_patch(FancyBboxPatch((cx - bw_ / 2 - 0.12, cy - bh / 2 - 0.12), bw_ + 0.24, bh + 0.24,
                                        boxstyle="round,pad=0,rounding_size=0.35", fc="white", ec="#D5DCE5", lw=0.6, zorder=3))
            ax.imshow(np.asarray(im0), extent=(cx - iw / 2, cx + iw / 2, cy - ih / 2, cy + ih / 2), zorder=4)
        elif photo:
            im = ax.imshow(square_crop(a.root / photo, s.get("crop") or ""), extent=(cx - r, cx + r, cy - r, cy + r), zorder=3)
            im.set_clip_path(Circle((cx, cy), r, transform=ax.transData))
            ax.add_patch(Circle((cx, cy), r, fc="none", ec="white", lw=1.5, zorder=4))
        else:
            ax.add_patch(Circle((cx, cy), r, fc="#F4F6F9", ec="#AEB8C5", lw=0.8, ls=(0, (4, 3)), zorder=3))
            labels.append((i, ax.text(cx, cy, "photo\nto come", ha="center", va="center", fontsize=MIN_PT, color=SUB, zorder=4)))
        lines = s["label"].split("|")
        for k, t in enumerate(lines):
            labels.append((i, ax.text(cx, 3.95 - k * 0.95 + (len(lines) - 2) * 0.45, styled(t, a.italic), ha="center", va="center",
                                      fontsize=MIN_PT, fontweight="bold", color=INK)))
    ax.set_aspect("equal")
    fig.canvas.draw(); rend = fig.canvas.get_renderer()
    for i, t in labels:   # every label must sit inside its own chevron body
        bb = t.get_window_extent(rend).transformed(ax.transData.inverted())
        if bb.x0 < i * Wd + 0.6 or bb.x1 > (i + 1) * Wd - 1.0:
            plt.close(fig)
            raise ValueError(f"label '{t.get_text()}' is wider than its stage at {MIN_PT} pt and {FW} in; shorten or break it with |")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    from mamey.figure_stamp import stamp_file
    fig.savefig(outs[0], dpi=a.dpi, facecolor="white"); fig.savefig(outs[1], facecolor="white"); plt.close(fig)
    for p in outs[:2]:
        stamp_file(p, "study_workflow_figure")
    outs[2].write_text(json.dumps({"tool": "study_workflow_figure", "stages": n, "print_width_in": FW, "height_in": round(FH, 3),
                                   "min_text_pt": MIN_PT, "stage_table": {"path": str(a.stages), "sha256": sha(a.stages)},
                                   "photos": photos}, indent=1) + "\n")
    print(f"[study_workflow_figure] {n} stages -> {outs[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

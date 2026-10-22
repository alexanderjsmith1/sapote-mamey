#!/usr/bin/env python3
"""Stack gap-rescue locus maps drawn as figure panels into one multi-panel figure with one shared key.

Each map folder comes from `gap_directed_rescue.py --redraw ... --print-width double --panel --no-key`. It holds
`gap_rescue.png` (300 dpi, at most the print width) and `gap_rescue_key.json`, which lists the gene classes that
map fills. Each map is placed at its native size, with a bold panel letter at its top left. The shared key is printed
once, on the last page:
  - the identity colour bar, with the ramp and range read from tools/gap_rescue_locus_map.py;
  - the gene-class legend, the union of the classes the maps fill, in that module's CLASS_ORDER, plus "class unclear"
    when any map has one.

Pages: `--pages ab,cd` splits the panels over pages, in order; without it, all panels share one page. A page taller
than `--max-page-height` (default 10 in) is refused, never scaled. `--overview` also writes all panels on one tall
PNG for screen viewing. The overview is not a print page, so the height limit does not apply to it.

Refusals (GAP_RESCUE_PANEL_FIGURE): a map folder without gap_rescue.png or gap_rescue_key.json; a map wider than the
print width; a page taller than the limit; pages that do not use every panel exactly once; an output that exists.

Outputs: <out>.pdf (one page per page group), <out>_page_<letters>.png per page (or <out>.png for a single page), and
<out>_RUN_INFO.json with the SHA-256 of every map and key file, the key classes and the page heights.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DPI = 300           # gap_rescue_locus_map saves panels at 300 dpi
LETTER_PT = 10      # panel letters
KEY_PT = 8          # every key text
GAP_IN = 0.12       # vertical gap between panels
KEY_COLS = 4
LEGEND_TITLE = "Genes not in the reference, by protein-search name"
GECCO_KEY_H = 0.62  # extra key height for the GECCO probability bar, when any map draws a GECCO track
TOL_IN = 0.01


class PanelFigureError(ValueError):
    pass


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_maps(folders):
    """Each map folder's image and key, checked; returns [(folder, png, key dict)]."""
    out = []
    for f in map(Path, folders):
        png, key = f / "gap_rescue.png", f / "gap_rescue_key.json"
        if not png.is_file():
            raise PanelFigureError(f"GAP_RESCUE_PANEL_FIGURE: no gap_rescue.png in {f}")
        if not key.is_file():
            raise PanelFigureError(f"GAP_RESCUE_PANEL_FIGURE: no gap_rescue_key.json in {f}; redraw the map with "
                                   "gap_directed_rescue.py --redraw --panel --no-key")
        out.append((f, png, json.loads(key.read_text())))
    return out


def union_key(keys) -> tuple[list[str], bool]:
    """The shared key's classes: the union of the classes the maps fill, in the map module's order."""
    import gap_rescue_locus_map as glm
    seen = {c for k in keys for c in k.get("classes", [])}
    unknown = sorted(seen - set(glm.CLASS_ORDER))
    if unknown:
        raise PanelFigureError(f"GAP_RESCUE_PANEL_FIGURE: classes not in the map module's CLASS_ORDER: {unknown}")
    return [c for c in glm.CLASS_ORDER if c in seen], any(k.get("class_unclear") for k in keys)


def key_height(n_handles: int, cols: int = KEY_COLS) -> float:
    """Height of the shared key in inches: the colour bar and a legend of `cols` columns under its title."""
    rows = max(1, math.ceil(n_handles / cols))
    return 0.45 + 0.15 * rows


def split_pages(n: int, letters: str, pages: str | None):
    """Page groups as lists of panel indices; every panel used once, in order."""
    if not pages:
        return [list(range(n))]
    groups = [g.strip() for g in pages.split(",") if g.strip()]
    flat = "".join(groups)
    if flat != letters[:n]:
        raise PanelFigureError(f"GAP_RESCUE_PANEL_FIGURE: --pages {pages!r} must use the panels {letters[:n]!r} "
                               "once each, in order")
    out, i = [], 0
    for g in groups:
        out.append(list(range(i, i + len(g)))); i += len(g)
    return out


def draw_page(maps, idx, letters, width_in, with_key, classes, unclear, gecco=False, show_letters=True):
    """Draw one page. The gene-class legend starts 2.45 in from the left; at a 6.5 in page four columns of long
    labels ("biosynthetic core", "class unclear") run off the right edge, so fewer columns are tried until the
    legend ends inside the page. Text size never changes."""
    import matplotlib.pyplot as plt
    for cols in range(KEY_COLS, 0, -1):
        fig, H, fits = _draw_page(maps, idx, letters, width_in, with_key, classes, unclear, gecco, cols, show_letters)
        if fits or cols == 1:
            return fig, H
        plt.close(fig)


def _draw_page(maps, idx, letters, width_in, with_key, classes, unclear, gecco, cols, show_letters=True):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.patches import Patch
    from PIL import Image
    import gap_rescue_locus_map as glm

    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"]})
    imgs = [Image.open(maps[i][1]) for i in idx]
    hs = [im.height / DPI for im in imgs]
    handles = [Patch(fc=glm.CLASS_FILL[c], ec="#333333", lw=0.6, label=c) for c in classes]
    if unclear:
        handles.append(Patch(fc="white", ec="#333333", lw=0.6, ls="--", label="class unclear"))
    kh = key_height(len(handles), cols) + (GECCO_KEY_H if gecco else 0.0) if with_key else 0.0
    H = sum(hs) + GAP_IN * (len(imgs) - 1) + kh
    fig = plt.figure(figsize=(width_in, H), dpi=DPI)
    y = H
    for im, h, i in zip(imgs, hs, idx):
        w = im.width / DPI
        y -= h
        ax = fig.add_axes([0, y / H, w / width_in, h / H]); ax.imshow(im, interpolation="none"); ax.axis("off")
        if show_letters:
            fig.text(0.02 / width_in, (y + h - 0.05) / H, letters[i], fontsize=LETTER_PT, weight="bold", va="top")
        y -= GAP_IN
    if with_key:
        cax = fig.add_axes([0.35 / width_in, (kh - 0.22) / H, 1.8 / width_in, 0.12 / H])
        cb = fig.colorbar(ScalarMappable(norm=Normalize(*glm.IDENTITY_RANGE),
                                         cmap=LinearSegmentedColormap.from_list("id", list(glm.IDENTITY_RAMP))),
                          cax=cax, orientation="horizontal")
        cb.set_label("Protein identity (%)", fontsize=KEY_PT, labelpad=2); cb.ax.tick_params(labelsize=KEY_PT)
        if gecco:   # a second bar under the identity bar: GECCO per-gene probability, ramp read from the map module
            gax = fig.add_axes([0.35 / width_in, (kh - 0.22 - GECCO_KEY_H) / H, 1.8 / width_in, 0.12 / H])
            gb = fig.colorbar(ScalarMappable(norm=Normalize(*glm.GECCO_RANGE),
                                             cmap=LinearSegmentedColormap.from_list("gecco", list(glm.GECCO_RAMP))),
                              cax=gax, orientation="horizontal")
            gb.outline.set_linewidth(0.6)
            gb.set_label("GECCO per-gene probability", fontsize=KEY_PT, labelpad=2); gb.ax.tick_params(labelsize=KEY_PT)
        if handles:
            leg = fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(2.45 / width_in, 0.02 / H), ncol=cols,
                             fontsize=KEY_PT, frameon=False, title=LEGEND_TITLE, title_fontsize=KEY_PT,
                             alignment="left", handlelength=1.6, columnspacing=1.0)
            fig.canvas.draw()
            right_in = leg.get_window_extent().x1 / fig.dpi
            return fig, H, right_in <= width_in - 0.02
    return fig, H, True


def compose(folders, out: Path, letters="abcdefgh", pages=None, width_in=7.2, max_page_height=10.0,
            overview=False, show_letters=True) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from PIL import Image
    import gap_rescue_locus_map as glm

    maps = read_maps(folders)
    if not letters.isalpha() or len(set(letters)) != len(letters):
        # one letter per panel, e.g. "ab" or "AB"; "A,B" would print the comma as a panel letter
        raise PanelFigureError(f"GAP_RESCUE_PANEL_FIGURE: --letters {letters!r} must be letters only, each once "
                               "(e.g. ab or AB, not A,B)")
    if len(maps) > len(letters):
        raise PanelFigureError(f"GAP_RESCUE_PANEL_FIGURE: {len(maps)} maps but only {len(letters)} letters")
    for f, png, _ in maps:
        with Image.open(png) as im:
            w = im.width / DPI
        if w > width_in + TOL_IN:
            raise PanelFigureError(f"GAP_RESCUE_PANEL_FIGURE: {f.name} is {w:.2f} in wide, wider than the "
                                   f"{width_in} in print width; redraw it at the print width, never shrink")
    if not show_letters and len(maps) != 1:
        # a figure of several panels needs its letters; only a one-map figure may leave the letter off
        raise PanelFigureError("GAP_RESCUE_PANEL_FIGURE: --no-letter is for a single map; panels need letters")
    groups = split_pages(len(maps), letters, pages)
    classes, unclear = union_key([k for *_, k in maps])
    gecco = any(k.get("gecco") for *_, k in maps)
    out = Path(out)
    pdf_path = out.with_suffix(".pdf")
    page_pngs = ([out.with_name(out.name + ".png")] if len(groups) == 1 else
                 [out.with_name(f"{out.name}_page_{''.join(letters[i] for i in g)}.png") for g in groups])
    over_png = out.with_name(out.name + "_overview.png") if overview and len(groups) > 1 else None
    info_path = out.with_name(out.name + "_RUN_INFO.json")
    for p in [pdf_path, *page_pngs, info_path] + ([over_png] if over_png else []):
        if p.exists():
            raise PanelFigureError(f"GAP_RESCUE_PANEL_FIGURE: {p} exists; choose a new --out")
    figs = []
    for gi, g in enumerate(groups):
        fig, H = draw_page(maps, g, letters, width_in, gi == len(groups) - 1, classes, unclear, gecco, show_letters)
        if H > max_page_height + TOL_IN:
            plt.close(fig)
            for f, _ in figs:
                plt.close(f)
            raise PanelFigureError(f"GAP_RESCUE_PANEL_FIGURE: page {''.join(letters[i] for i in g)} is {H:.2f} in "
                                   f"tall, over the {max_page_height} in limit; split it with --pages, never scale")
        figs.append((fig, H))
    out.parent.mkdir(parents=True, exist_ok=True)
    over_h = None
    # The page is exactly the print width: pin the save box, so a global "savefig.bbox: tight" left by another
    # module in the same process (mamey/cohort_figures.py, tools/render_dapr_boards.py) cannot crop or pad it.
    with plt.rc_context({"savefig.bbox": "standard"}):
        with PdfPages(pdf_path, metadata=glm.savefig_metadata(pdf_path, "gap_rescue_panel_figure")) as pdf:
            for (fig, _), png in zip(figs, page_pngs):
                pdf.savefig(fig, facecolor="white")
                fig.savefig(png, dpi=DPI, facecolor="white",
                            metadata=glm.savefig_metadata(png, "gap_rescue_panel_figure"))
                plt.close(fig)
        if over_png:
            fig, over_h = draw_page(maps, list(range(len(maps))), letters, width_in, True, classes, unclear, gecco)
            fig.savefig(over_png, dpi=DPI, facecolor="white",
                        metadata=glm.savefig_metadata(over_png, "gap_rescue_panel_figure"))
            plt.close(fig)
    info = {"tool": "gap_rescue_panel_figure", "print_width_in": width_in, "max_page_height_in": max_page_height,
            "panels": [{"letter": letters[i], "folder": str(f), "map_sha256": _sha(png),
                        "key_sha256": _sha(f / "gap_rescue_key.json"), "classes": k.get("classes", []),
                        "class_unclear": bool(k.get("class_unclear"))} for i, (f, png, k) in enumerate(maps)],
            "key_classes": classes, "key_class_unclear": unclear, "gecco_key": gecco,
            "identity_ramp": list(glm.IDENTITY_RAMP), "identity_range": list(glm.IDENTITY_RANGE),
            "pages": [{"letters": "".join(letters[i] for i in g), "height_in": round(H, 3), "png": str(p)}
                      for g, (_, H), p in zip(groups, figs, page_pngs)],
            "pdf": str(pdf_path), "overview_png": str(over_png) if over_png else None,
            "overview_height_in": round(over_h, 3) if over_h else None}
    info_path.write_text(json.dumps(info, indent=1) + "\n")
    return info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--maps", nargs="+", required=True, help="map folders, in panel order (each from --panel --no-key)")
    ap.add_argument("--out", required=True, help="output path prefix (no extension)")
    ap.add_argument("--letters", default="abcdefgh", help="panel letters, in order, as one string such as ab or AB (default abcdefgh); "
                    "anything but letters is refused")
    ap.add_argument("--pages", default=None, help="page groups by letter, e.g. ab,cd (default: one page)")
    ap.add_argument("--print-width", type=float, default=7.2, help="page width in inches (default 7.2)")
    ap.add_argument("--max-page-height", type=float, default=10.0, help="refuse a page taller than this (default 10 in)")
    ap.add_argument("--overview", action="store_true", help="with --pages: also write every panel on one tall PNG "
                    "for screen viewing (not a print page)")
    ap.add_argument("--no-letter", action="store_true", help="a single map drawn as a figure of its own: no panel letter "
                    "(refused for more than one map)")
    a = ap.parse_args(argv)
    try:
        info = compose(a.maps, Path(a.out), a.letters, a.pages, a.print_width, a.max_page_height, a.overview,
                       show_letters=not a.no_letter)
    except PanelFigureError as e:
        raise SystemExit(str(e))
    print(f"[gap_rescue_panel_figure] {len(info['panels'])} panels on {len(info['pages'])} page(s); key classes: "
          f"{', '.join(info['key_classes']) or 'none'}{' + class unclear' if info['key_class_unclear'] else ''} -> {info['pdf']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""novel_and_active_figure.py — tile table of isolates that are novel by 16S and active in a bioassay.

One row per isolate. Left: a genus color bar, the strain and genus as deposited, 16S identity to the closest type strain,
the number of GenBank strains at or above the identity threshold, and dDDH to the closest type strain. Right: one tile
per assay target and material, holding the best inhibition (%) as a rounded integer. Tiles at or above --strong-pct are
dark, at or above --active-pct gray, below it white with a gray edge; n.t. (no reading) is light gray with "n.t.";
a blank cell stays blank. The four states are never merged. A sand tint marks the 16S cell when identity is below
--identity-threshold and the GenBank cell when the count is --rarity-max or fewer.

Input table (--table, TSV; lines starting with # are skipped), one row per isolate:

    strain                       isolate name as it should be printed
    genus_as_deposited (or genus) genus as deposited; drawn italic and colored from mamey/data/genus_palette.json
    id16s_pct                    16S identity (%) to the closest type strain; blank = no value (printed n.a.)
    genbank_strains_ge98_65      GenBank strains at or above the threshold; blank = not computed (printed n.a.)
    dddh_d4                      dDDH d4 (%) to the closest type strain; blank = no genome or no result (left blank)
    <target>|crude               best inhibition (%) of the crude extract; n.t. = not tested; blank = not applicable
    <target>|fraction            the same for the fraction

Optional columns novel_by_identity and novel_by_rarity (yes/no/n.a.) are checked against the values and refused when
they disagree. Other columns are ignored.

Material (house rule 4: name the material, never pool crude and fraction into one value):

    --material crude_extract     crude-extract tiles only; rows qualify on crude-extract activity only
    --material fraction          fraction tiles only; rows qualify on fraction activity only
    --material side_by_side      crude and fraction tiles in separate columns under each target (never one value);
                                 a row qualifies when either material reaches --active-pct. This is the layout of the
                                 thesis novel-and-active figures.

The material is named in the title and the file name. --rows qualifying (default) keeps rows that are novel (identity
below the threshold, or --rarity-max or fewer GenBank strains) and active in the drawn material(s); --rows all keeps
every row of the table.

Outputs go to a new --out directory: <name>_<material>.png (600 dpi default), .pdf and .svg, the plotted left columns
and tiles as TSV, _PRINT_SIZE.json, and receipt.json with input and output SHA-256, settings and the smallest text size
read back from the PDF. The tool refuses to finish when any text is under --min-text-pt (8), and refuses a rounded
label that would cross a tier boundary.

Exit codes: 0 drawn, 2 refused input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.logging_setup import get_logger as _get_logger  # noqa: E402

_OUT = _get_logger(__name__)
TOOL = "novel_and_active_figure"
ROOT = Path(__file__).resolve().parents[1]
EXIT_OK, EXIT_INPUT = 0, 2
DEFAULT_TARGETS = "MRSA,C. albicans,C. auris,E. coli,P. larvae"
MATERIAL_MODES = ("crude_extract", "fraction", "side_by_side")
MAT_KEYS = {"crude_extract": ("crude",), "fraction": ("fraction",), "side_by_side": ("crude", "fraction")}
FILE_TAG = {"crude_extract": "crude_extract", "fraction": "fraction", "side_by_side": "crude_extract_and_fraction"}
TITLES = {"crude_extract": "Crude extract", "fraction": "Fraction",
          "side_by_side": "Crude extract and fraction, in separate columns"}
SUB = {"crude": "crude", "fraction": "fract."}

# House ink (tools/sapote_pub_layout.R) and the tile palette of the thesis figures.
INK, SUBINK = "#17212E", "#54637A"
FILLS = {"strong": "#333333", "moderate": "#A6A6A6", "below": "#FFFFFF", "n.t.": "#EFEFEF", "blank": "#FFFFFF"}
TEXT = {"strong": "#FFFFFF", "moderate": "#111111", "below": "#555555", "n.t.": "#777777", "blank": "#FFFFFF"}
EDGE_GREY, SAND = "#B8B8B8", "#F1E4C3"

# Layout, inches (1 plot unit = 1 inch). Defaults are the thesis-figure settings: 6.5 in page, 0.15 in white edge.
PAGE_W, EDGE = 6.5, 0.15
LAB_W, NUMW, GAP, CELL, RH, TH = 1.34, 0.48, 0.10, 0.325, 0.27, 0.245
HEAD, LEG, TITLE_H = 0.52, 0.52, 0.26


class InputError(ValueError):
    """A refused input: missing column, bad number, disagreeing flag, tier-crossing label, bad option."""


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_table(path: Path) -> list[dict]:
    if not Path(path).is_file():
        raise InputError(f"{path}: not found")
    with Path(path).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader((ln for ln in fh if not ln.startswith("#")), delimiter="\t"))
    if not rows:
        raise InputError(f"{path}: no rows")
    return rows


def _num(v: str, what: str):
    v = (v or "").strip()
    if v == "":
        return None
    try:
        x = float(v)
    except ValueError:
        raise InputError(f"{what}: {v!r} is not a number") from None
    if not math.isfinite(x):
        raise InputError(f"{what}: {v!r} is not finite")
    return x


def tile_state(raw: str, active: float, strong: float, what: str) -> tuple[str, str]:
    """(state, label) for one assay cell. n.t. and blank stay distinct; numbers get a rounded integer label."""
    raw = (raw or "").strip()
    if raw == "n.t.":
        return "n.t.", "n.t."
    v = _num(raw, what)
    if v is None:
        return "blank", ""
    state = "strong" if v >= strong else "moderate" if v >= active else "below"
    lab = int(math.floor(v + 0.5))
    if (state == "below" and lab >= active) or (state == "moderate" and (lab >= strong or lab < active)) \
            or (state == "strong" and lab < strong):
        raise InputError(f"{what}: {raw} rounds to {lab}, which crosses a tier boundary; give one more decimal or "
                         f"move the threshold")
    return state, str(lab)


def _natural(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def prepare(rows, targets, mode, a) -> tuple[list[dict], list[dict]]:
    """Checked rows (with novelty and activity worked out) and the tile records, before any drawing."""
    gcol = "genus_as_deposited" if "genus_as_deposited" in rows[0] else "genus" if "genus" in rows[0] else None
    need = ["strain", "id16s_pct", "genbank_strains_ge98_65", "dddh_d4"]
    need += [f"{t}|{m}" for t in targets for m in MAT_KEYS[mode]]
    missing = [c for c in need if c not in rows[0]] + ([] if gcol else ["genus_as_deposited or genus"])
    if missing:
        raise InputError(f"--table: missing columns {missing}")
    seen, out = set(), []
    for i, r in enumerate(rows, 2):
        s = (r["strain"] or "").strip()
        if not s or s in seen:
            raise InputError(f"--table row {i}: empty or repeated strain {s!r}")
        seen.add(s)
        ident = _num(r["id16s_pct"], f"{s} id16s_pct")
        rar = _num(r["genbank_strains_ge98_65"], f"{s} genbank_strains_ge98_65")
        if rar is not None and (rar < 0 or rar != int(rar)):
            raise InputError(f"{s}: genbank_strains_ge98_65 {rar} is not a count")
        dd = _num(r["dddh_d4"], f"{s} dddh_d4")
        nov_id = ident is not None and ident < a.identity_threshold
        nov_ra = rar is not None and rar <= a.rarity_max
        for col, mine, known in (("novel_by_identity", nov_id, ident is not None),
                                 ("novel_by_rarity", nov_ra, rar is not None)):
            given = (r.get(col) or "").strip()
            if given:
                want = "yes" if mine else ("no" if known else "n.a.")
                if given != want:
                    raise InputError(f"{s}: {col} is {given!r} in the table but the values give {want!r}")
        best = []
        for t in targets:
            for m in MAT_KEYS[mode]:
                v = (r[f"{t}|{m}"] or "").strip()
                if v not in ("", "n.t."):
                    best.append(_num(v, f"{s} {t}|{m}"))
        out.append({"strain": s, "genus": (r[gcol] or "").strip(), "ident": ident, "rar": rar, "dd": dd,
                    "novel_by_identity": nov_id, "novel_by_rarity": nov_ra, "novel": nov_id or nov_ra,
                    "best": max(best) if best else None,
                    "active": bool(best) and max(best) >= a.active_pct, "raw": r})
    if a.rows == "qualifying":
        out = [x for x in out if x["novel"] and x["active"]]
    if not out:
        raise InputError("no rows to draw (no isolate is both novel and active in the drawn material)")
    if a.order == "genus":
        out.sort(key=lambda x: (x["genus"], _natural(x["strain"])))
    tiles = []
    for i, x in enumerate(out):
        for t in targets:
            for m in MAT_KEYS[mode]:
                raw = (x["raw"][f"{t}|{m}"] or "").strip()
                st, lab = tile_state(raw, a.active_pct, a.strong_pct, f"{x['strain']} {t}|{m}")
                tiles.append({"strain": x["strain"], "target": t, "material": "crude_extract" if m == "crude" else "fraction",
                              "raw": raw, "state": st, "label": lab, "_i": i, "_m": m})
    return out, tiles


def _palette(a) -> tuple[dict, str, Path]:
    path = ROOT / "mamey/data/genus_palette.json"
    pal = json.loads(path.read_text(encoding="utf-8"))
    colors = dict(pal["default"])
    if a.palette_set:
        if a.palette_set not in pal.get("sets", {}):
            raise InputError(f"--palette-set {a.palette_set!r} is not in {path.name} (have {sorted(pal.get('sets', {}))})")
        colors.update(pal["sets"][a.palette_set])
    for it in a.genus_color or []:
        g, _, c = it.partition("=")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", c.strip()):
            raise InputError(f"--genus-color {it!r} is not Genus=#RRGGBB")
        colors[g.strip()] = c.strip()
    return colors, pal["fallback"], path


def _mt(s: str) -> str:
    return re.sub(r"([$_^{}\\%#&])", r"\\\1", s)


def _italic(s: str) -> str:
    return "$\\it{" + _mt(s).replace(" ", "\\ ") + "}$"


def draw(rows, tiles, targets, mode, a, colors, fallback):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    plt.rcParams.update({"font.family": a.font, "pdf.fonttype": 42, "svg.fonttype": "none",
                         "mathtext.fontset": "custom", "mathtext.rm": a.font, "mathtext.it": f"{a.font}:italic",
                         "mathtext.bf": f"{a.font}:bold"})
    PT = a.text_pt
    mats = MAT_KEYS[mode]
    cell = CELL * 2 / len(mats)          # one material keeps the page width: each tile is twice as wide
    roman = {t.strip() for t in a.roman_targets.split(",") if t.strip()}
    n = len(rows)
    DW = PAGE_W - 2 * EDGE
    x_num = [LAB_W + NUMW * k for k in range(3)]
    x_path0 = LAB_W + 3 * NUMW + GAP

    def x_cell(p, m):
        return x_path0 + p * 2 * CELL + m * cell

    if x_cell(len(targets) - 1, len(mats) - 1) + cell > DW + 1e-6:
        raise InputError(f"{len(targets)} targets do not fit the {PAGE_W} in page")
    head = HEAD + TITLE_H
    DH = head + n * RH + LEG
    H = DH + 2 * EDGE
    ytop = DH - head

    def ycen(i):
        return ytop - (i + 0.5) * RH

    fig = plt.figure(figsize=(PAGE_W, H))
    ax = fig.add_axes([EDGE / PAGE_W, EDGE / H, DW / PAGE_W, DH / H])
    ax.set_xlim(0, DW)
    ax.set_ylim(0, DH)
    ax.axis("off")
    txt = dict(fontsize=PT, color=INK)
    title = a.title or TITLES[mode]
    ax.text(0, DH - 0.02, title, ha="left", va="top", fontsize=PT + 1, fontweight="bold", color=INK)
    for i, x in enumerate(rows):
        y = ycen(i)
        if x["novel_by_identity"]:
            ax.add_patch(Rectangle((x_num[0] + 0.02, y - TH / 2), NUMW - 0.04, TH, fc=SAND, ec="none"))
        if x["novel_by_rarity"]:
            ax.add_patch(Rectangle((x_num[1] + 0.02, y - TH / 2), NUMW - 0.04, TH, fc=SAND, ec="none"))
        ax.add_patch(Rectangle((0, y - TH / 2), 0.10, TH, fc=colors.get(x["genus"], fallback), ec="none"))
        ax.text(0.16, y, f"{_mt(x['strain'])} {_italic(x['genus'])}", ha="left", va="center", **txt)
        ax.text(x_num[0] + NUMW / 2, y, "n.a." if x["ident"] is None else x["raw"]["id16s_pct"].strip(),
                ha="center", va="center", **txt)
        ax.text(x_num[1] + NUMW / 2, y, "n.a." if x["rar"] is None else str(int(x["rar"])), ha="center", va="center", **txt)
        ax.text(x_num[2] + NUMW / 2, y, "" if x["dd"] is None else f"{x['dd']:.1f}", ha="center", va="center", **txt)
    for t in tiles:
        p, m = targets.index(t["target"]), mats.index(t["_m"])
        x0, y = x_cell(p, m), ycen(t["_i"])
        ax.add_patch(Rectangle((x0 + 0.01, y - TH / 2), cell - 0.02, TH, fc=FILLS[t["state"]],
                               ec=EDGE_GREY if t["state"] == "below" else "none", lw=0.7))
        if t["label"]:
            ax.text(x0 + cell / 2, y, t["label"], ha="center", va="center", fontsize=PT, color=TEXT[t["state"]])
    thr = f"{a.identity_threshold:g}"
    for k, lab in enumerate(["16S\nidentity\n(%)", f"GenBank\nstrains at\n≥{thr}%", "dDDH\n(%)"]):
        ax.text(x_num[k] + NUMW / 2, ytop + 0.03, lab, ha="center", va="bottom", linespacing=1.0, **txt)
    ty = ytop + (0.22 if len(mats) == 2 else 0.03)
    for p, t in enumerate(targets):
        cx = x_path0 + p * 2 * CELL + CELL
        ax.text(cx, ty, t if t in roman else _italic(t), ha="center", va="bottom", **txt)
        if len(mats) == 2:
            for m, mk in enumerate(mats):
                ax.text(x_cell(p, m) + cell / 2, ytop + 0.03, SUB[mk], ha="center", va="bottom", fontsize=PT, color=SUBINK)
            ax.plot([x_path0 + p * 2 * CELL + 0.01, x_path0 + p * 2 * CELL + 2 * CELL - 0.01], [ytop + 0.20] * 2,
                    color=EDGE_GREY, lw=0.85)
    sq, ly1, ly2 = 0.16, LEG - 0.17, 0.17

    def key(x, y, lab, fill, edge):
        ax.add_patch(Rectangle((x, y - sq / 2), sq, sq, fc=fill, ec=edge or "none", lw=0.7))
        ax.text(x + sq + 0.06, y, lab, ha="left", va="center", **txt)

    act, strong = f"{a.active_pct:g}", f"{a.strong_pct:g}"
    mid = f"{act}–{a.strong_pct - 1:g}" if float(a.strong_pct).is_integer() and float(a.active_pct).is_integer() \
        else f"{act} to below {strong}"
    ax.text(0, ly1, a.legend_title, ha="left", va="center", **txt)
    key(2.30, ly1, f"{strong} or more", FILLS["strong"], None)
    key(3.28, ly1, mid, FILLS["moderate"], None)
    key(3.98, ly1, f"below {act}", FILLS["below"], EDGE_GREY)
    key(4.88, ly1, "n.t. (not tested)", FILLS["n.t."], None)
    key(0, ly2, f"16S identity below {thr}%, or {a.rarity_max:g} or fewer GenBank strains at {thr}% or more", SAND, None)
    return fig, plt, H


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", required=True, type=Path, help="per-isolate TSV (columns above)")
    ap.add_argument("--material", required=True, choices=MATERIAL_MODES)
    ap.add_argument("--out", required=True, type=Path, help="new output directory")
    ap.add_argument("--name", default="NOVEL_AND_ACTIVE", help="file prefix; the material tag is appended")
    ap.add_argument("--targets", default=DEFAULT_TARGETS, help="comma-separated assay targets, in column order "
                    "(default %(default)s)")
    ap.add_argument("--roman-targets", default="MRSA", help="targets printed upright; the rest are italic")
    ap.add_argument("--rows", choices=("qualifying", "all"), default="qualifying")
    ap.add_argument("--order", choices=("genus", "input"), default="genus",
                    help="genus = by genus, then strain in natural order (default); input = table order")
    ap.add_argument("--identity-threshold", type=float, default=98.65)
    ap.add_argument("--rarity-max", type=float, default=2)
    ap.add_argument("--active-pct", type=float, default=50)
    ap.add_argument("--strong-pct", type=float, default=80)
    ap.add_argument("--palette-set", default="", help="genus_palette.json set laid over the default (moss, attine)")
    ap.add_argument("--genus-color", action="append", metavar="Genus=#RRGGBB", help="override one genus color")
    ap.add_argument("--title", default="", help="title text; must name the material (default from --material)")
    ap.add_argument("--legend-title", default="Inhibition (%), best reading:",
                    help="first legend line; name the reading time if the table holds one (e.g. 48 h)")
    ap.add_argument("--font", default="Arial")
    ap.add_argument("--text-pt", type=float, default=8.0)
    ap.add_argument("--min-text-pt", type=float, default=8.0)
    ap.add_argument("--dpi", type=int, default=600)
    a = ap.parse_args(argv)
    try:
        return run(a)
    except InputError as exc:
        _OUT.error("REFUSED: %s", exc)
        return EXIT_INPUT


def run(a) -> int:
    from mamey.figure_policy import assert_no_banned_figure_text, matplotlib_visible_text, preflight_chart_data
    from mamey.figure_stamp import savefig_metadata
    from tools._min_text_check import check as _mt_check
    if a.dpi < 300:
        raise InputError("--dpi must be 300 or more")
    if not a.active_pct < a.strong_pct:
        raise InputError("--active-pct must be below --strong-pct")
    if a.text_pt < a.min_text_pt:
        raise InputError(f"--text-pt {a.text_pt} is below --min-text-pt {a.min_text_pt}")
    if a.title and not re.search(r"crude|fraction", a.title, re.I):
        raise InputError("--title must name the material (crude extract, fraction or both)")
    if a.material == "side_by_side" and a.title and not (re.search(r"crude", a.title, re.I) and re.search(r"fraction", a.title, re.I)):
        raise InputError("--title for side_by_side must name both crude extract and fraction")
    targets = [t.strip() for t in a.targets.split(",") if t.strip()]
    if not targets or len(set(targets)) != len(targets):
        raise InputError("--targets is empty or repeats a target")
    rows, tiles = prepare(read_table(a.table), targets, a.material, a)
    measured = [{"pct": float(t["raw"])} for t in tiles if t["state"] in ("strong", "moderate", "below")]
    preflight = preflight_chart_data(measured, chart_kind="tile", numeric_fields=["pct"])
    colors, fallback, palette_path = _palette(a)
    if a.out.exists():
        raise InputError(f"--out {a.out} exists; give a new directory")
    fig, plt, H = draw(rows, tiles, targets, a.material, a, colors, fallback)
    stem = a.out / f"{a.name}_{FILE_TAG[a.material]}"
    assert_no_banned_figure_text(matplotlib_visible_text(fig), figure_id=stem.name)
    a.out.mkdir(parents=True)
    outs = []
    for ext in ("png", "pdf", "svg"):
        p = stem.with_suffix("." + ext)
        fig.savefig(p, dpi=a.dpi, facecolor="white", metadata=savefig_metadata(p, TOOL))
        outs.append(p)
    plt.close(fig)
    mt = _mt_check(str(stem.with_suffix(".pdf")), float(a.min_text_pt), PAGE_W)
    if mt["status"] != "PASS":
        raise InputError(f"MIN_TEXT_CHECK_FAILED: smallest text {mt['smallest_pt']} pt ({mt['smallest_text']!r}), "
                         f"page {mt['page_width_in']} in; floor {a.min_text_pt} pt at {PAGE_W} in")
    left = [{"strain": x["strain"], "genus": x["genus"],
             "id16s_pct": "n.a." if x["ident"] is None else x["raw"]["id16s_pct"].strip(),
             "genbank_strains": "n.a." if x["rar"] is None else str(int(x["rar"])),
             "dddh_d4": "" if x["dd"] is None else f"{x['dd']:.1f}",
             "novel_by_identity": "yes" if x["novel_by_identity"] else "no",
             "novel_by_rarity": "yes" if x["novel_by_rarity"] else "no",
             "best_pct_drawn_material": "" if x["best"] is None else f"{x['best']:.2f}"} for x in rows]
    for path, data in ((stem.with_name(stem.name + "_plot_data_left_columns.tsv"), left),
                       (stem.with_name(stem.name + "_plot_data_tiles.tsv"),
                        [{k: v for k, v in t.items() if not k.startswith("_")} for t in tiles])):
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = _SafeDictWriter(fh, fieldnames=list(data[0]), delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(data)
        outs.append(path)
    ps = stem.with_name(stem.name + "_PRINT_SIZE.json")
    ps.write_text(json.dumps({"material": a.material, "width_in": PAGE_W, "height_in": round(H, 3),
                              "minimum_text_pt": a.min_text_pt, "dpi": a.dpi, "rows": len(rows), "font": a.font}) + "\n",
                  encoding="utf-8")
    outs.append(ps)
    rec = {"tool": TOOL, "material": a.material, "rows_drawn": len(rows), "targets": targets,
           "settings": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items()},
           "rules": {"novel": f"16S identity < {a.identity_threshold} or GenBank strains >= threshold <= {a.rarity_max}",
                     "active": f"best inhibition >= {a.active_pct} in the drawn material(s)",
                     "pooling": "none: crude extract and fraction are separate tiles"
                                if a.material == "side_by_side" else f"{a.material} only"},
           "preflight": preflight, "min_text": mt,
           "inputs": {str(a.table): _sha(a.table), str(palette_path): _sha(palette_path)},
           "outputs": {p.name: _sha(p) for p in outs}}
    (a.out / "receipt.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    _OUT.info("%s: %d rows, %.1f x %.2f in, smallest text %s pt", stem.name, len(rows), PAGE_W, H, mt["smallest_pt"])
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

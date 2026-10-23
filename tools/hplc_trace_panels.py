#!/usr/bin/env python3
"""hplc_trace_panels.py — draw HPLC UV/DAD chromatograms from native detector arrays, without smoothing.

Two subcommands:

    panels   one panel per chosen run, two panels per row, lettered A, B, ..., one wavelength legend on top.
             A main-text figure: one representative run per strain, chosen in a REPRESENTATIVE.tsv.
    pages    per-strain supplement pages: every run listed for the strain, one run per row, four rows per page,
             ordered by acquisition time (runs with no recorded time last).

Trace data (both subcommands; folders are arguments, never built in):

    --run-meta-dir  <run_id>.json  run metadata: label, xmin, xmax, method, flow, injection, and series, a list of
                                   {"name": "<wavelength> nm", ...} in detector channel order.
    --native-dir    <run_id>.npz   the complete native detector arrays x0,y0, x1,y1, ... in that channel order;
                    <run_id>.json  the native proof: a list of {"name", "member", "native_points"}, one per channel,
                                   in the same order. Lengths are checked against native_points.

Run tables (TSV, one row per run):

    panels  --representative  strain, run_id, sample_label, acquired, material; optional genus, chosen_by.
    pages   --runs            strain, run_id, sample_label, acquired, material; optional pick_number, genus.

`acquired` is ISO time (2024-01-19T16:07:38) or blank ("acquisition date not recorded"). `sample_label` must equal the
run metadata label. `material` names what was injected: crude_extract, fraction, or not_recorded. One figure holds one
material: rows of different materials are refused, and the material is part of every output file name.

Display rule (both subcommands): a channel with up to --max-native-points points (default 6002) is drawn point for
point. A longer channel keeps the source minimum and maximum of each of --bins equal-index bins (default 3000), its
first and last point, and both sides of every finite/non-finite edge. Every source minimum and maximum is kept. There
is no smoothing, resampling or baseline correction.

Channel colours: --channel-colors 210=#087C87,254=#70419A,280=#C25B0A,330=#C7313B (the default). The order given is
the legend order and the drawing order (first drawn underneath). A channel in the data with no colour is refused.

Outputs go to a new --out directory: PNG (600 dpi default), PDF and SVG per figure, a runs TSV, a caption draft
(_CAPTION.md, facts only), and receipt.json with input and output SHA-256 and the smallest text size read back from
each PDF. The tool refuses to finish when any text is under --min-text-pt (8).

Exit codes: 0 drawn, 2 refused input.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
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
TOOL = "hplc_trace_panels"
EXIT_OK, EXIT_INPUT = 0, 2
MATERIALS = ("crude_extract", "fraction", "not_recorded")
MATERIAL_WORDS = {"crude_extract": "crude extract", "fraction": "fraction", "not_recorded": "material not recorded"}
DEFAULT_COLORS = "210=#087C87,254=#70419A,280=#C25B0A,330=#C7313B"
REP_COLUMNS = ("strain", "run_id", "sample_label", "acquired", "material")

# Layout in inches. The defaults are the settings of the thesis-chapter figures (7.0 in print width).
PANELS = dict(width=7.0, cols=2, row=2.05, title=0.42, axes=1.25, top=0.36, bottom=0.06, left=0.62, gap=0.55,
              right=0.10, lw=0.5)
PAGES = dict(width=7.0, per_page=4, row=2.19, top=0.42, bottom=0.08, left=0.78, right=0.12, title=0.24, axes=1.48,
             lw=0.55)


class InputError(ValueError):
    """A refused input: missing file or column, label mismatch, mixed material, unknown channel."""


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_tsv(path: Path, required) -> list[dict]:
    if not Path(path).is_file():
        raise InputError(f"{path}: not found")
    with Path(path).open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader((ln for ln in fh if not ln.startswith("#")), delimiter="\t")]
    if not rows:
        raise InputError(f"{path}: no rows")
    missing = [c for c in required if c not in rows[0]]
    if missing:
        raise InputError(f"{path}: missing columns {missing}")
    for i, r in enumerate(rows, 2):
        for c in ("strain", "run_id", "sample_label", "material"):
            if not (r.get(c) or "").strip():
                raise InputError(f"{path} row {i}: empty {c}")
        if r["material"] not in MATERIALS:
            raise InputError(f"{path} row {i}: material {r['material']!r} is not one of {', '.join(MATERIALS)}")
        acq = (r.get("acquired") or "").strip()
        if acq:
            try:
                datetime.datetime.fromisoformat(acq)
            except ValueError:
                raise InputError(f"{path} row {i}: acquired {acq!r} is not an ISO time") from None
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", r["run_id"]):
            raise InputError(f"{path} row {i}: run_id {r['run_id']!r} may hold only letters, digits, _ . -")
    return rows


def parse_colors(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in [p.strip() for p in text.split(",") if p.strip()]:
        if "=" not in part:
            raise InputError(f"--channel-colors item {part!r} is not WAVELENGTH=#RRGGBB")
        k, v = (s.strip() for s in part.split("=", 1))
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
            raise InputError(f"--channel-colors {k}: {v!r} is not #RRGGBB")
        if k in out:
            raise InputError(f"--channel-colors names {k} twice")
        out[k] = v
    if not out:
        raise InputError("--channel-colors is empty")
    return out


def display(x, y, max_points: int = 6002, bins: int = 3000):
    """The native display rule: every point up to max_points; above it, each bin's source min and max, the first and
    last point and both sides of every finite/non-finite edge. Returns index-sorted copies; nothing is smoothed."""
    import numpy as np
    n = len(x)
    if n <= max_points:
        return x, y
    chosen = {0, n - 1}
    edges = np.linspace(0, n, bins + 1, dtype=int)
    for a, b in zip(edges[:-1], edges[1:]):
        v = y[a:b]
        if np.isfinite(v).any():
            chosen.update([a + int(np.nanargmin(v)), a + int(np.nanargmax(v))])
    good = np.isfinite(y)
    tr = np.flatnonzero(good[1:] != good[:-1])
    chosen.update(tr.tolist())
    chosen.update((tr + 1).tolist())
    ids = np.array(sorted(chosen))
    if good.any() and not (np.nanmin(y[ids]) == np.nanmin(y) and np.nanmax(y[ids]) == np.nanmax(y)):
        raise AssertionError("display rule lost a source extreme")  # cannot happen: each bin keeps its own extremes
    return x[ids], y[ids]


def load_run(run_id: str, meta_dir: Path, native_dir: Path) -> tuple[dict, list, list, list[Path]]:
    """Return (metadata, native proof, [(channel, x, y)], input files) for one run, checking lengths and order."""
    import numpy as np
    mp, pp, zp = meta_dir / f"{run_id}.json", native_dir / f"{run_id}.json", native_dir / f"{run_id}.npz"
    for p in (mp, pp, zp):
        if not p.is_file():
            raise InputError(f"{run_id}: missing {p}")
    meta = json.loads(mp.read_text(encoding="utf-8"))
    proof = json.loads(pp.read_text(encoding="utf-8"))
    for k in ("label", "xmin", "xmax", "series"):
        if k not in meta:
            raise InputError(f"{run_id}: run metadata has no {k!r}")
    names = [s["name"] for s in meta["series"]]
    if [p.get("name") for p in proof] != names:
        raise InputError(f"{run_id}: native proof channels {[p.get('name') for p in proof]} != metadata {names}")
    chans = []
    with np.load(zp) as z:
        for i, name in enumerate(names):
            if f"x{i}" not in z or f"y{i}" not in z:
                raise InputError(f"{run_id}: native arrays lack x{i}/y{i}")
            x = np.asarray(z[f"x{i}"], float)
            y = np.asarray(z[f"y{i}"], float)
            if len(x) != len(y) or len(x) != int(proof[i]["native_points"]):
                raise InputError(f"{run_id} channel {name}: {len(x)} points, proof says {proof[i]['native_points']}")
            chans.append((str(name).split()[0], x, y))
    return meta, proof, chans, [mp, pp, zp]


def title_of(row: dict) -> str:
    acq = (row.get("acquired") or "").strip()
    when = acq.replace("T", " ") if acq else "acquisition date not recorded"
    return f"{row['sample_label']}  |  {when}"


def _mathtext_escape(s: str) -> str:
    return re.sub(r"([$_^{}\\%#&])", r"\\\1", s)


def _setup_matplotlib(font: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": font, "font.size": 8, "axes.labelsize": 9, "xtick.labelsize": 8,
                         "ytick.labelsize": 8, "legend.fontsize": 9, "pdf.fonttype": 42, "svg.fonttype": "none",
                         "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
                         "mathtext.fontset": "custom", "mathtext.rm": font, "mathtext.it": f"{font}:italic",
                         "mathtext.bf": f"{font}:bold"})
    return plt


def _check_channels(chans, colors, run_id):
    unknown = sorted({c for c, _, _ in chans} - set(colors))
    if unknown:
        raise InputError(f"{run_id}: channel(s) {unknown} have no colour in --channel-colors")


def _draw_channels(ax, chans, colors, lw, max_points, bins, run_id):
    _check_channels(chans, colors, run_id)
    for w in colors:  # legend order is drawing order: the first channel sits underneath
        for name, x, y in chans:
            if name == w:
                dx, dy = display(x, y, max_points, bins)
                ax.plot(dx, dy, color=colors[w], lw=lw, solid_joinstyle="round")


def _style_axes(ax, meta, ylabelpad=2):
    ax.set_xlim(meta["xmin"], meta["xmax"])
    ax.set_xlabel("Time (min)", labelpad=2)
    ax.set_ylabel("Absorbance (mAU)", labelpad=ylabelpad)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=2.5, pad=2)


def _legend(fig, colors, h, x_center=0.5, drop_in=0.02):
    from matplotlib.lines import Line2D
    present = list(colors)
    handles = [Line2D([], [], color=colors[w], lw=1.2, label=f"{w} nm") for w in present]
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), frameon=False,
               bbox_to_anchor=(x_center, 1 - drop_in / h), handlelength=2.2, columnspacing=2.0)


def _one_material(rows: list[dict], where: str) -> str:
    mats = sorted({r["material"] for r in rows})
    if len(mats) != 1:
        raise InputError(f"{where}: one figure holds one material; found {', '.join(mats)}. Draw each material separately.")
    return mats[0]


def _save(fig, stem: Path, dpi: int, min_pt: float, width_in: float, policy_text) -> dict:
    from mamey.figure_policy import assert_no_banned_figure_text
    from mamey.figure_stamp import savefig_metadata
    from tools._min_text_check import check as _mt_check
    assert_no_banned_figure_text(policy_text(fig), figure_id=stem.name)
    out = {}
    for ext in ("png", "pdf", "svg"):
        p = stem.with_suffix("." + ext)
        fig.savefig(p, dpi=dpi, facecolor="white", metadata=savefig_metadata(p, TOOL))
        out[ext] = p
    mt = _mt_check(str(out["pdf"]), float(min_pt), float(width_in))
    if mt["status"] != "PASS":
        raise InputError(f"MIN_TEXT_CHECK_FAILED {stem.name}: smallest text {mt['smallest_pt']} pt "
                         f"({mt['smallest_text']!r}), page {mt['page_width_in']} in; floor {min_pt} pt at {width_in} in")
    return {"files": out, "min_text": mt}


def _write_tsv(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _receipt(out: Path, args, inputs: list[Path], outputs: list[Path], extra: dict):
    rec = {"tool": TOOL, "subcommand": args.cmd, "settings": {k: (str(v) if isinstance(v, Path) else v)
                                                              for k, v in vars(args).items() if k != "func"},
           "display_rule": {"max_native_points": args.max_native_points, "bins": args.bins, "smoothing": "none"},
           "inputs": {str(p): _sha(p) for p in sorted(set(inputs), key=str)},
           "outputs": {p.name: _sha(p) for p in outputs}, **extra}
    (out / "receipt.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")


def _preflight(rows: list[dict]):
    from mamey.figure_policy import preflight_chart_data
    return preflight_chart_data(rows, chart_kind="line", numeric_fields=["native_points", "run_minutes"])


def _parse_genus(items) -> dict[str, str]:
    out = {}
    for it in items or []:
        if "=" not in it:
            raise InputError(f"--genus {it!r} is not STRAIN=Genus")
        s, g = (x.strip() for x in it.split("=", 1))
        out[s] = g
    return out


def _new_out(out: Path):
    if out.exists():
        raise InputError(f"--out {out} exists; give a new directory")


# ---------------------------------------------------------------------------------------------------------- panels

def cmd_panels(a) -> int:
    from mamey.figure_policy import matplotlib_visible_text
    colors = parse_colors(a.channel_colors)
    rows = _read_tsv(a.representative, REP_COLUMNS)
    by_strain: dict[str, list[dict]] = {}
    for r in rows:
        by_strain.setdefault(r["strain"], []).append(r)
    strains = [s.strip() for s in a.strains.split(",") if s.strip()] if a.strains else list(by_strain)
    if len(set(strains)) != len(strains):
        raise InputError("--strains names a strain twice")
    chosen = []
    for s in strains:
        if s not in by_strain:
            raise InputError(f"--strains {s}: not in {a.representative}")
        chosen.extend(by_strain[s])  # every chosen run of the strain, in file order: one panel per run
    material = _one_material(chosen, str(a.representative))
    genus = _parse_genus(a.genus)
    for r in chosen:
        g = genus.get(r["strain"]) or (r.get("genus") or "").strip()
        if not g:
            raise InputError(f"{r['strain']}: no genus (add a genus column or --genus {r['strain']}=Genus)")
        r["_genus"] = g
    loaded = [(r, *load_run(r["run_id"], a.run_meta_dir, a.native_dir)) for r in chosen]
    pre = []
    for r, meta, proof, chans, _ in loaded:
        if meta["label"] != r["sample_label"]:
            raise InputError(f"{r['run_id']}: sample_label {r['sample_label']!r} != run label {meta['label']!r}")
        _check_channels(chans, colors, r["run_id"])
        pre.append({"native_points": min(int(p["native_points"]) for p in proof),
                    "run_minutes": float(meta["xmax"]) - float(meta["xmin"])})
    preflight = _preflight(pre)
    _new_out(a.out)
    plt = _setup_matplotlib(a.font)
    L = dict(PANELS, width=a.width)
    n, cols = len(loaded), L["cols"]
    nrows = (n + cols - 1) // cols
    W = L["width"]
    h = L["top"] + nrows * L["row"] + L["bottom"]
    pw = (W - cols * L["left"] - (cols - 1) * L["gap"] - L["right"]) / cols
    if pw <= 0.5:
        raise InputError(f"--width {W} in leaves no room for {cols} panels")
    fig = plt.figure(figsize=(W, h))
    run_rows, inputs = [], [a.representative]
    for i, (r, meta, proof, chans, files) in enumerate(loaded):
        inputs += files
        rr, c = divmod(i, cols)
        x0 = L["left"] + c * (pw + L["left"] + L["gap"])
        top = h - L["top"] - rr * L["row"] - L["title"]
        ax = fig.add_axes([x0 / W, (top - L["axes"]) / h, pw / W, L["axes"] / h])
        _draw_channels(ax, chans, colors, L["lw"], a.max_native_points, a.bins, r["run_id"])
        _style_axes(ax, meta)
        g = _mathtext_escape(r["_genus"]).replace(" ", r"\ ")
        ax.text(0, 1 + 0.17 / L["axes"], f"$\\it{{{g}}}$ sp. {_mathtext_escape(r['strain'])}", transform=ax.transAxes,
                ha="left", va="bottom", fontsize=9)
        ax.text(0, 1 + 0.03 / L["axes"], title_of(r), transform=ax.transAxes, ha="left", va="bottom", fontsize=8,
                color="#333333")
        letter = chr(ord("A") + i)
        fig.text((x0 - L["left"] + 0.02) / W, (top + L["title"] - 0.02) / h, letter, fontsize=11, fontweight="bold",
                 va="top")
        run_rows.append({"panel": letter, "strain": r["strain"], "genus": r["_genus"], "material": material,
                         "run_id": r["run_id"], "sample_label": r["sample_label"], "acquired": r.get("acquired", ""),
                         "method": meta.get("method", ""), "flow_ml_min": meta.get("flow", ""),
                         "injection_ul": meta.get("injection", ""), "channels": "; ".join(c for c, _, _ in chans),
                         "native_points": "; ".join(str(p["native_points"]) for p in proof),
                         "run_minutes": f"{float(meta['xmax']):.3f}",
                         "source_members": "; ".join(str(p.get("member", "")) for p in proof),
                         "native_npz_sha256": _sha(files[2]), "chosen_by": r.get("chosen_by", "")})
    _legend(fig, colors, h)
    a.out.mkdir(parents=True)
    stem = a.out / f"{a.name}_{material}_HPLC_UV_panels"
    saved = _save(fig, stem, a.dpi, a.min_text_pt, W, matplotlib_visible_text)
    plt.close(fig)
    runs_tsv = stem.with_name(stem.name + "_runs.tsv")
    _write_tsv(runs_tsv, run_rows)
    cap = stem.with_name(stem.name + "_CAPTION.md")
    cap.write_text(_caption_panels(run_rows, material, colors, a), encoding="utf-8")
    outs = [*saved["files"].values(), runs_tsv, cap]
    _receipt(a.out, a, inputs, outs, {"material": material, "panels": len(run_rows), "preflight": preflight,
                                      "print_size_in": [W, round(h, 3)], "min_text": [saved["min_text"]]})
    _OUT.info("%s: %d panels, %.1f x %.2f in, smallest text %s pt", stem.name, len(run_rows), W, h,
              saved["min_text"]["smallest_pt"])
    return EXIT_OK


def _caption_panels(rows, material, colors, a) -> str:
    parts = [f"({r['panel']}) *{r['genus']}* sp. {r['strain']}, {r['sample_label']}" for r in rows]
    waves = ", ".join(colors)
    return (f"**HPLC UV chromatograms, {MATERIAL_WORDS[material]}.** One run per panel: " + "; ".join(parts) + ". "
            f"UV absorbance at {waves} nm, plotted as recorded by the detector, without smoothing. Each panel title gives "
            f"the sample label and the acquisition date and time of the run.\n\n"
            f"Display rule: channels with up to {a.max_native_points} points are drawn point for point; longer channels "
            f"keep the source minimum and maximum of each of {a.bins} equal-index bins. Run identifiers, methods and "
            f"source hashes are in the runs table beside this figure.\n")


# ----------------------------------------------------------------------------------------------------------- pages

def _sort_key(r):
    acq = (r.get("acquired") or "").strip()
    pick = r.get("pick_number") or ""
    return (acq == "", acq, int(pick) if pick.strip().lstrip("-").isdigit() else 0)


def cmd_pages(a) -> int:
    from mamey.figure_policy import matplotlib_visible_text
    colors = parse_colors(a.channel_colors)
    rows = _read_tsv(a.runs, REP_COLUMNS)
    strains = [s.strip() for s in a.strains.split(",") if s.strip()] if a.strains else list(dict.fromkeys(r["strain"] for r in rows))
    plan = []
    for s in strains:
        keys = sorted([r for r in rows if r["strain"] == s], key=_sort_key)
        if not keys:
            raise InputError(f"--strains {s}: no runs in {a.runs}")
        material = _one_material(keys, f"{a.runs} strain {s}")
        loaded = [(r, *load_run(r["run_id"], a.run_meta_dir, a.native_dir)) for r in keys]
        for r, meta, _proof, chans, _files in loaded:
            if meta["label"] != r["sample_label"]:
                raise InputError(f"{r['run_id']}: sample_label {r['sample_label']!r} != run label {meta['label']!r}")
            _check_channels(chans, colors, r["run_id"])
        plan.append((s, material, loaded))
    pre = [{"native_points": min(int(p["native_points"]) for p in proof),
            "run_minutes": float(meta["xmax"]) - float(meta["xmin"])}
           for _, _, loaded in plan for _, meta, proof, _, _ in loaded]
    preflight = _preflight(pre)
    _new_out(a.out)
    plt = _setup_matplotlib(a.font)
    L = dict(PAGES, width=a.width, per_page=a.per_page)
    W = L["width"]
    a.out.mkdir(parents=True)
    inputs, outs, mts, sizes = [a.runs], [], [], []
    for strain, material, loaded in plan:
        sd = a.out / re.sub(r"[^A-Za-z0-9_.-]", "_", strain)
        sd.mkdir()
        run_rows = []
        npages = (len(loaded) + L["per_page"] - 1) // L["per_page"]
        for p0 in range(0, len(loaded), L["per_page"]):
            chunk = loaded[p0:p0 + L["per_page"]]
            letter = chr(ord("a") + p0 // L["per_page"])
            h = L["top"] + len(chunk) * L["row"] + L["bottom"]
            fig = plt.figure(figsize=(W, h))
            for i, (r, meta, proof, chans, files) in enumerate(chunk):
                inputs += files
                top = h - L["top"] - i * L["row"] - L["title"]
                ax = fig.add_axes([L["left"] / W, (top - L["axes"]) / h, (W - L["left"] - L["right"]) / W, L["axes"] / h])
                _draw_channels(ax, chans, colors, L["lw"], a.max_native_points, a.bins, r["run_id"])
                _style_axes(ax, meta, ylabelpad=3)
                ax.set_title(title_of(r), fontsize=9, loc="left", pad=4)
                run_rows.append({"strain": strain, "material": material, "page": letter,
                                 "pick_number": r.get("pick_number", ""), "run_id": r["run_id"],
                                 "sample_label": r["sample_label"], "acquired": r.get("acquired", ""),
                                 "method": meta.get("method", ""), "flow_ml_min": meta.get("flow", ""),
                                 "injection_ul": meta.get("injection", ""),
                                 "channels": "; ".join(c for c, _, _ in chans),
                                 "native_points": "; ".join(str(p["native_points"]) for p in proof),
                                 "run_minutes": f"{float(meta['xmax']):.3f}",
                                 "source_members": "; ".join(str(p.get("member", "")) for p in proof),
                                 "native_npz_sha256": _sha(files[2])})
            _legend(fig, colors, h, x_center=0.5 + (L["left"] - L["right"]) / W / 2, drop_in=0.04)
            suffix = f"_page_{letter}" if (npages > 1 or not a.single_page_without_letter) else ""
            stem = sd / f"{a.name.format(strain=strain)}_{material}_HPLC_UV_chromatograms{suffix}"
            saved = _save(fig, stem, a.dpi, a.min_text_pt, W, matplotlib_visible_text)
            plt.close(fig)
            outs += list(saved["files"].values())
            mts.append(saved["min_text"])
            sizes.append({"figure": stem.name, "runs": len(chunk), "print_size_in": [W, round(h, 3)]})
            _OUT.info("%s: %d runs, %.1f x %.2f in", stem.name, len(chunk), W, h)
        runs_tsv = sd / "runs.tsv"
        _write_tsv(runs_tsv, run_rows)
        outs.append(runs_tsv)
    _receipt(a.out, a, inputs, outs, {"strains": strains, "preflight": preflight, "pages": sizes, "min_text": mts})
    return EXIT_OK


# ------------------------------------------------------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--run-meta-dir", required=True, type=Path, help="folder of <run_id>.json run metadata")
        p.add_argument("--native-dir", required=True, type=Path,
                       help="folder of <run_id>.npz native arrays and <run_id>.json native proof")
        p.add_argument("--channel-colors", default=DEFAULT_COLORS,
                       help="WAVELENGTH=#RRGGBB list; order = legend and drawing order (default %(default)s)")
        p.add_argument("--out", required=True, type=Path, help="new output directory")
        p.add_argument("--strains", default="", help="comma-separated strains, in figure order (default: file order)")
        p.add_argument("--width", type=float, default=7.0, help="print width in inches (default 7.0)")
        p.add_argument("--dpi", type=int, default=600)
        p.add_argument("--font", default="Arial")
        p.add_argument("--min-text-pt", type=float, default=8.0)
        p.add_argument("--max-native-points", type=int, default=6002,
                       help="channels up to this many points are drawn point for point (default 6002)")
        p.add_argument("--bins", type=int, default=3000, help="equal-index bins for longer channels (default 3000)")

    p = sub.add_parser("panels", help="one panel per chosen run, two per row, one legend")
    common(p)
    p.add_argument("--representative", required=True, type=Path,
                   help="TSV: strain, run_id, sample_label, acquired, material; optional genus, chosen_by")
    p.add_argument("--genus", action="append", metavar="STRAIN=Genus",
                   help="genus for a strain's panel title, as deposited (overrides a genus column)")
    p.add_argument("--name", default="HPLC_representative", help="output file prefix (material is appended)")
    p.set_defaults(func=cmd_panels)

    p = sub.add_parser("pages", help="per-strain supplement pages, one run per row")
    common(p)
    p.add_argument("--runs", required=True, type=Path,
                   help="TSV: strain, run_id, sample_label, acquired, material; optional pick_number")
    p.add_argument("--per-page", type=int, default=4)
    p.add_argument("--name", default="{strain}", help="file prefix; {strain} is replaced (default %(default)s)")
    p.add_argument("--single-page-without-letter", action="store_true",
                   help="a strain with one page gets no _page_a suffix")
    p.set_defaults(func=cmd_pages)
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        if a.dpi < 300:
            raise InputError("--dpi must be 300 or more")
        if a.bins < 1 or a.max_native_points < 2 * a.bins:
            raise InputError("--max-native-points must be at least twice --bins")
        if getattr(a, "per_page", 1) < 1:
            raise InputError("--per-page must be 1 or more")
        return a.func(a)
    except InputError as exc:
        _OUT.error("REFUSED: %s", exc)
        return EXIT_INPUT


if __name__ == "__main__":
    raise SystemExit(main())

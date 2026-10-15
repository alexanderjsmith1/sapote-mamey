#!/usr/bin/env python3
"""Collection-site map (figure type C01): one mark per site, sized by its number of isolates, on a basemap read from
shapefiles (no built-in world data).

Inputs, all explicit:
  --isolates TSV  isolate, site, group, genus      one row per isolate; genus blank = no 16S genus on record
  --sites    TSV  site, label, lat, lon            one row per site; label is printed beside its mark (\\n breaks a line)
  --basemap  SHP  (repeatable) polygon shapefiles drawn in order, e.g. countries then states/provinces
Layout: a dot marks each site on the map (size by isolates); a leader line runs to a pie in a side column (west or
east of the sites' median longitude, ordered north to south), with the site's label and isolate counts beside it.
Pie area is proportional to the site's isolates.
  --mark pie     slices by genus (16S rRNA)
  --mark circle  slices by group (isolation source) Text is held at 8 pt at the print width (default 7.2 in). Refuses: an isolate whose site
has no coordinates (named), a site outside the map extent, duplicate isolates or sites, and an output that exists.
Writes PNG (600 dpi), PDF, <out>_numbers.tsv (isolates per site and group, and per genus) and <out>_RUN_INFO.json.
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
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MIN_PT = 8.0
NO_GENUS = "No 16S genus on record"
GROUP_COLOURS = ["#2E5E8C", "#C0973F", "#7E5AA2", "#2E8B84", "#B5543C"]
INK, SUB, LAND, LAND_EDGE, WATER = "#17212E", "#54637A", "#E6E9EE", "#FFFFFF", "#FFFFFF"


def table(path: Path, need: list[str]) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        r = csv.DictReader(fh, delimiter="\t")
        miss = [c for c in need if c not in (r.fieldnames or [])]
        if miss:
            raise ValueError(f"{path}: missing columns {miss}")
        return [{k: (v or "").strip() for k, v in row.items()} for row in r]


def read_polygons(paths: list[Path], extent):
    import shapefile
    lo0, lo1, la0, la1 = extent
    out = []
    for p in paths:
        r = shapefile.Reader(str(p))
        for shp in r.iterShapes():
            if not shp.points:
                continue
            bx = shp.bbox
            if bx[2] < lo0 or bx[0] > lo1 or bx[3] < la0 or bx[1] > la1:
                continue
            parts = list(shp.parts) + [len(shp.points)]
            for a, b in zip(parts[:-1], parts[1:]):
                out.append((str(p), shp.points[a:b]))
    return out


def palette(palette_set):
    cfg = json.loads((ROOT / "mamey/data/genus_palette.json").read_text())
    col = dict(cfg["default"]); col.update(cfg["sets"].get(palette_set or "", {}))
    return col, cfg.get("fallback", "#8C8C8C")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--isolates", type=Path, required=True)
    ap.add_argument("--sites", type=Path, required=True)
    ap.add_argument("--basemap", type=Path, action="append", required=True, help="polygon shapefile (.shp), repeatable")
    ap.add_argument("--out", type=Path, required=True, help="output stem, without suffix")
    ap.add_argument("--mark", choices=["pie", "circle"], default="pie")
    ap.add_argument("--extent", help="lon_min,lon_max,lat_min,lat_max (default: the sites plus a margin)")
    ap.add_argument("--group-order", help="comma-separated group order for the circle colours and labels")
    ap.add_argument("--genus-order", help="comma-separated legend order; other genera follow")
    ap.add_argument("--pool-below", type=int, default=3, help="genera with fewer isolates than this are drawn as Other genera")
    ap.add_argument("--palette-set", choices=["moss", "attine"])
    ap.add_argument("--print-width", type=float, default=7.2, help="printed width in inches; all text 8 pt at this width")
    ap.add_argument("--max-radius-in", type=float, default=0.32, help="radius in inches of the largest site's mark")
    ap.add_argument("--frame", action="store_true", help="draw a thin line round the map extent, so land cut by the extent "
                    "ends at a map border rather than a bare edge")
    ap.add_argument("--legend-title", help="key title (default 'Genus (16S rRNA)' for pies, 'Isolation source' for circles)")
    ap.add_argument("--dpi", type=int, default=600)
    a = ap.parse_args(argv)
    try:
        return run(a)
    except (ValueError, FileExistsError) as exc:
        ap.exit(2, f"collection_map: {exc}\n")


def run(a) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Wedge, Circle, Patch, FancyBboxPatch
    outs = [a.out.with_suffix(".png"), a.out.with_suffix(".pdf"), Path(str(a.out) + "_numbers.tsv"), Path(str(a.out) + "_RUN_INFO.json")]
    if any(p.exists() for p in outs):
        raise FileExistsError(f"refusing to overwrite {a.out}.*")
    iso = table(a.isolates, ["isolate", "site", "group", "genus"])
    sites = table(a.sites, ["site", "label", "lat", "lon"])
    if len({r["isolate"] for r in iso}) != len(iso):
        raise ValueError("duplicate isolate rows")
    if len({r["site"] for r in sites}) != len(sites):
        raise ValueError("duplicate site rows")
    where = {s["site"]: s for s in sites}
    nowhere = sorted({r["site"] for r in iso if r["site"] not in where})
    if nowhere:
        raise ValueError(f"isolates at sites without coordinates: {nowhere}")
    for s in sites:
        s["lat"], s["lon"] = float(s["lat"]), float(s["lon"])
        s["label"] = s["label"].replace("\\n", "\n")      # a literal \n in the sites table breaks the label line
    used = [s for s in sites if any(r["site"] == s["site"] for r in iso)]
    if a.extent:
        lo0, lo1, la0, la1 = (float(x) for x in a.extent.split(","))
    else:
        lo0, lo1 = min(s["lon"] for s in used) - 4, max(s["lon"] for s in used) + 4
        la0, la1 = min(s["lat"] for s in used) - 2.5, max(s["lat"] for s in used) + 2.5
    out_of = [s["site"] for s in used if not (lo0 <= s["lon"] <= lo1 and la0 <= s["lat"] <= la1)]
    if out_of:
        raise ValueError(f"sites outside the map extent: {out_of}")
    # genus display: pool rare genera; blank = no 16S genus
    for r in iso:
        r["genus"] = r["genus"] or NO_GENUS
    gcount = Counter(r["genus"] for r in iso)
    for r in iso:
        if r["genus"] != NO_GENUS and gcount[r["genus"]] < a.pool_below:
            r["genus_shown"] = "Other genera"
        else:
            r["genus_shown"] = r["genus"]
    shown = Counter(r["genus_shown"] for r in iso)
    first = a.genus_order.split(",") if a.genus_order else []
    gorder = [g for g in first if g in shown] + sorted((g for g in shown if g not in first and g not in ("Other genera", NO_GENUS)), key=lambda g: -shown[g])
    gorder += [g for g in ("Other genera", NO_GENUS) if g in shown and g not in gorder]
    gcol, fallback = palette(a.palette_set)
    gcol = {g: ("#8C96A6" if g == "Other genera" else "#DDE2E8" if g == NO_GENUS else gcol.get(g, fallback)) for g in gorder}
    groups = list(dict.fromkeys((a.group_order.split(",") if a.group_order else []) + sorted({r["group"] for r in iso})))
    groups = [g for g in groups if any(r["group"] == g for r in iso)]
    grcol = {g: GROUP_COLOURS[i % len(GROUP_COLOURS)] for i, g in enumerate(groups)}
    by_site = defaultdict(list)
    for r in iso:
        by_site[r["site"]].append(r)
    # projection: equirectangular, x scaled by cos(mid latitude)
    k = math.cos(math.radians((la0 + la1) / 2))
    px = lambda lon: (lon - lo0) * k
    py = lambda lat: lat - la0
    map_w, map_h = (lo1 - lo0) * k, la1 - la0
    W = a.print_width
    # each site's text: label, isolates, and the split by group on its own line when the site has more than one group
    def site_text(s):
        rows = by_site[s]; n = len(rows); gc = Counter(r["group"] for r in rows)
        t = f"{where[s]['label']}\n{n} isolate{'s' if n != 1 else ''}"
        if len(gc) > 1:
            t += "\n" + ", ".join(f"{gc[g]} {g.lower()}" for g in groups if gc[g])
        return t
    texts = {s: site_text(s) for s in by_site}
    probe = plt.figure(figsize=(W, 2)); pr = probe.canvas.get_renderer()
    text_w = max(probe.text(0, 0, t, fontsize=MIN_PT, linespacing=1.15).get_window_extent(pr).width for t in texts.values()) / probe.dpi
    plt.close(probe)
    rmax_in = a.max_radius_in
    col_w = text_w + 2 * rmax_in + 0.22             # text, gap, pie, gap
    map_in = W - 2 * col_w
    if map_in < W * 0.3:
        raise ValueError(f"site labels need {col_w:.2f} in a side; the map would get {map_in:.2f} of {W} in")
    unit = map_in / map_w                          # inches per projected degree
    map_h_in = map_h * unit
    med = sorted(where[s]["lon"] for s in by_site)[len(by_site) // 2]
    cols = {"W": sorted([s for s in by_site if where[s]["lon"] < med], key=lambda s: -where[s]["lat"]),
            "E": sorted([s for s in by_site if where[s]["lon"] >= med], key=lambda s: -where[s]["lat"])}
    slot_in = max(2 * rmax_in + 0.12, 3 * MIN_PT * 1.25 / 72 + 0.12)
    body_in = max(map_h_in, slot_in * max(len(v) for v in cols.values()))
    leg_h = 0.3 + 0.2 * math.ceil(len(gorder if a.mark == "pie" else groups) / 3)
    H = body_in + leg_h + 0.06
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, leg_h / H, 1, body_in / H])
    off_y = (body_in - map_h_in) / 2 / unit          # map centred vertically in the body
    ax.set_xlim(-col_w / unit, map_w + col_w / unit); ax.set_ylim(-off_y, map_h + off_y); ax.set_aspect("equal"); ax.axis("off")
    clip = matplotlib.patches.Rectangle((0, 0), map_w, map_h, transform=ax.transData)
    for _, pts in read_polygons(a.basemap, (lo0, lo1, la0, la1)):
        poly = ax.add_patch(Polygon([(px(x), py(y)) for x, y in pts], closed=True, fc=LAND, ec=LAND_EDGE, lw=0.5, zorder=1))
        poly.set_clip_path(clip)                    # after add_patch, which would otherwise clip to the whole axes
    if a.frame:
        ax.add_patch(matplotlib.patches.Rectangle((0, 0), map_w, map_h, fill=False, ec="#6B7483", lw=0.5, zorder=2))   # the leader-line grey
    nmax = max(len(v) for v in by_site.values())
    rpie = {s: rmax_in / unit * math.sqrt(len(v) / nmax) for s, v in by_site.items()}
    dot = {s: (0.035 + 0.05 * math.sqrt(len(v) / nmax)) / unit for s, v in by_site.items()}

    def pie(x, y, r, rows):
        if a.mark == "pie":
            cnt = Counter(rr["genus_shown"] for rr in rows); order, colours = gorder, gcol
        else:
            cnt = Counter(rr["group"] for rr in rows); order, colours = groups, grcol
        start = 90.0
        for g in order:
            if cnt[g]:
                sweep = 360.0 * cnt[g] / len(rows)
                ax.add_patch(Wedge((x, y), r, start - sweep, start, fc=colours[g], ec="white", lw=0.4, zorder=5))
                start -= sweep
        ax.add_patch(Circle((x, y), r, fc="none", ec="#6B7483", lw=0.4, zorder=6))

    lo, hi = -off_y, map_h + off_y
    for side, ss in cols.items():
        if not ss:
            continue
        ys = [hi - (hi - lo) * (i + 0.5) / len(ss) for i in range(len(ss))]
        cx = -(0.08 + rmax_in) / unit if side == "W" else map_w + (0.08 + rmax_in) / unit
        for s, yb in zip(ss, ys):
            x, y = px(where[s]["lon"]), py(where[s]["lat"])
            ax.add_patch(Circle((x, y), dot[s], fc=INK, ec="white", lw=0.4, zorder=4))
            pie(cx, yb, rpie[s], by_site[s])
            dx, dy = cx - x, yb - y; d = math.hypot(dx, dy) or 1
            ax.plot([x + dx / d * dot[s], cx - dx / d * rpie[s]], [y + dy / d * dot[s], yb - dy / d * rpie[s]],
                    color="#6B7483", lw=0.5, zorder=3)
            tx = cx - (rmax_in + 0.08) / unit if side == "W" else cx + (rmax_in + 0.08) / unit
            ax.text(tx, yb, texts[s], ha="right" if side == "W" else "left", va="center", fontsize=MIN_PT, color=INK,
                    linespacing=1.15, zorder=6)
    if a.mark == "pie":
        handles = [Patch(fc=gcol[g], ec="#999" if g == NO_GENUS else gcol[g], label=g) for g in gorder]
        title = "Genus (16S rRNA)"
    else:
        handles = [Patch(fc=grcol[g], ec=grcol[g], label=g) for g in groups]
        title = "Isolation source"
    if a.legend_title:
        title = a.legend_title
    leg = fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=MIN_PT, title=title, title_fontsize=MIN_PT,
                     frameon=False, bbox_to_anchor=(0.5, 0.0), handlelength=1.2, columnspacing=1.4)
    for t in leg.get_texts():
        if t.get_text() not in ("Other genera", NO_GENUS) and a.mark == "pie":
            t.set_fontstyle("italic")
    fig.canvas.draw()
    sizes = [t.get_fontsize() for t in ax.texts] + [t.get_fontsize() for t in leg.get_texts()] + [leg.get_title().get_fontsize()]
    if min(sizes) < MIN_PT - 1e-9:
        raise ValueError("text below 8 pt")
    rend = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(rend) for t in ax.texts] + [leg.get_window_extent(rend)]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if boxes[i].overlaps(boxes[j]):
                raise ValueError(f"text boxes overlap: {ax.texts[i].get_text().splitlines()[0] if i < len(ax.texts) else 'legend'}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    from mamey.figure_stamp import stamp_file
    fig.savefig(outs[0], dpi=a.dpi, facecolor="white"); fig.savefig(outs[1], facecolor="white"); plt.close(fig)
    for p in outs[:2]:
        stamp_file(p, "collection_map")
    with outs[2].open("w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t"); w.writerow(["site", "label", "group_or_genus", "isolates"])
        for s, rows in sorted(by_site.items(), key=lambda kv: -len(kv[1])):
            w.writerow([s, where[s]["label"], "ALL", len(rows)])
            for g, c in Counter(r["group"] for r in rows).most_common():
                w.writerow([s, where[s]["label"], f"group:{g}", c])
            for g, c in Counter(r["genus_shown"] for r in rows).most_common():
                w.writerow([s, where[s]["label"], f"genus:{g}", c])
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    outs[3].write_text(json.dumps({"tool": "collection_map", "mark": a.mark, "print_width_in": W, "height_in": round(H, 3),
                                   "extent": [lo0, lo1, la0, la1], "isolates": len(iso), "sites": len(by_site), "legend_title": title, "frame": bool(a.frame),
                                   "inputs": [{"path": str(p), "sha256": sha(p)} for p in [a.isolates, a.sites, *a.basemap]]},
                                  indent=1) + "\n")
    print(f"[collection_map] {len(iso)} isolates at {len(by_site)} sites -> {outs[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

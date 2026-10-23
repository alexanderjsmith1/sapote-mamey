#!/usr/bin/env python3
"""Locus-map figure pages from a spec file: redraw each gap-rescue map from its saved run, then stack the maps into print pages.

One command for what thesis figure sets did with dated-folder wrappers. For each spec row it runs
`tools/gap_directed_rescue.py --redraw <run> --panel --no-key --trim-kb <kb> --scale-bar-up` with protein-search gene names,
MIBiG compound names, a GECCO track under the strain row (that genome's GECCO tables) and, when supplied, a GECCO track
under the reference row (GECCO run on the MIBiG GenBank file). It then calls `tools/gap_rescue_panel_figure.py` to stack the
maps, with one shared key and panel letters, onto pages no taller than the page limit (a group that comes out too tall falls
back to one map per page). Nothing is recomputed; every map is redrawn from its run's saved tables.

spec.tsv columns: letter, run, strain, zip; optional mibig_dir, gecco_genes, gecco_clusters.
  letter    panel letter, or "-" for a figure of one map with no letter
  run       a gap_directed_rescue run folder (with gap_rescue_receipt.json)
  zip       the antiSMASH zip the run read (the decontaminated assembly where one was used)
  Relative paths are read against --root.
--gecco-dir supplies <strain>.genes.tsv and <strain>.clusters.tsv for rows that name none; --mibig-gecco-dir is a folder
of GECCO runs on the MIBiG GenBank files (<BGC>/<BGC>.genes.tsv), for the reference-row track.
--width: page6.5 (6.5 in, the thesis text column), double (7.2 in) or landscape (9.0 in, the text width of a landscape page).
--map-height: canvas height of each map in inches (default 6.2); larger values stretch crowded maps vertically.

Writes <out>/panels/<map>/, <out>/logs/, the page files <out>/<prefix>[_page_N].{pdf,png} and <out>/<prefix>_PAGES.json.

usage: locus_figure_pages.py --spec spec.tsv --out DIR --prefix NAME --mibig-dir DIR [--root DIR] [--gene-names TSV]
       [--mibig-names JSON] [--gecco-dir DIR] [--mibig-gecco-dir DIR] [--width page6.5|double|landscape]
       [--map-height IN] [--trim-kb KB] [--page-limit IN] [--own-key]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # bundle root, for a bare-script run from tools/
from mamey.logging_setup import get_logger as _get_logger  # noqa: E402

_OUT = _get_logger(__name__)


TOOLS = Path(__file__).resolve().parent
WIDTHS = {"page6.5": (6.5, 9.4), "double": (7.2, 9.4), "landscape": (9.0, 6.5)}   # page width, largest page height
PNG_DPI = 300


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_spec(path, root):
    rows = list(csv.DictReader(open(path), delimiter="\t"))
    if not rows:
        raise ValueError(f"{path}: no rows")
    for need in ("letter", "run", "strain", "zip"):
        if need not in rows[0]:
            raise ValueError(f"{path}: missing column {need}")
    letters = [r["letter"] for r in rows]
    if "-" in letters and len(rows) > 1:
        raise ValueError("letter '-' (no panel letter) is for a figure of one map")
    if len(set(letters)) != len(letters):
        raise ValueError("panel letters must be unique")
    for r in rows:
        for k in ("run", "zip", "mibig_dir", "gecco_genes", "gecco_clusters"):
            if r.get(k):
                r[k] = str((Path(root) / r[k]).resolve()) if not Path(r[k]).is_absolute() else r[k]
        if not Path(r["run"], "gap_rescue_receipt.json").is_file():
            raise ValueError(f"{r['run']}: not a gap_directed_rescue run (no gap_rescue_receipt.json)")
        if not Path(r["zip"]).is_file():
            raise ValueError(f"{r['zip']}: zip not found")
    return rows


def page_groups(letters, heights_in, limit_in, key_in=0.9):
    """Greedy groups in order: maps stacked plus about key_in for the shared key and letters, at most limit_in."""
    groups, cur, tot = [], [], 0.0
    for letter, h in zip(letters, heights_in):
        if cur and tot + h + key_in > limit_in:
            groups.append(cur); cur, tot = [], 0.0
        cur.append(letter); tot += h
    groups.append(cur)
    return groups


def map_command(r, a, dst):
    gecco_genes = r.get("gecco_genes") or (str(Path(a.gecco_dir) / f"{r['strain']}.genes.tsv") if a.gecco_dir else "")
    gecco_clusters = r.get("gecco_clusters") or (str(Path(a.gecco_dir) / f"{r['strain']}.clusters.tsv") if a.gecco_dir else "")
    cmd = [sys.executable, str(TOOLS / "gap_directed_rescue.py"), "--zip", r["zip"], "--label", r["strain"],
           "--mibig-dir", r.get("mibig_dir") or a.mibig_dir, "--redraw", r["run"], "--out", str(dst),
           "--print-width", "page6.5" if a.width == "page6.5" else a.width, "--trim-kb", str(a.trim_kb),
           "--panel", "--scale-bar-up"] + ([] if a.own_key else ["--no-key"])
    if a.mibig_names:
        cmd += ["--mibig-names", a.mibig_names]
    if a.gene_names:
        cmd += ["--gene-names", a.gene_names]
    if gecco_genes and Path(gecco_genes).is_file():
        cmd += ["--gecco-genes", gecco_genes] + (["--gecco-clusters", gecco_clusters] if Path(gecco_clusters or "-").is_file() else [])
    if a.mibig_gecco_dir:
        cmd += ["--mibig-gecco-dir", a.mibig_gecco_dir]
    if a.map_height:
        cmd += ["--map-height", str(a.map_height)]
    return cmd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--mibig-dir", required=True, help="folder of MIBiG GenBank files the runs name")
    ap.add_argument("--root", default=".", help="relative spec paths are read against this folder (default: current)")
    ap.add_argument("--gene-names", help="protein-search gene names (tools/gap_directed_rescue.py --gene-names)")
    ap.add_argument("--mibig-names", help="MIBiG compound names JSON (tools/gap_directed_rescue.py --mibig-names)")
    ap.add_argument("--gecco-dir", help="folder with <strain>.genes.tsv and <strain>.clusters.tsv")
    ap.add_argument("--mibig-gecco-dir", help="folder of GECCO runs on the MIBiG GenBank files (<BGC>/<BGC>.genes.tsv)")
    ap.add_argument("--width", choices=sorted(WIDTHS), default="page6.5")
    ap.add_argument("--map-height", type=float, help="canvas height of each map in inches (default 6.2)")
    ap.add_argument("--trim-kb", type=float, default=2.0)
    ap.add_argument("--page-limit", type=float, default=9.0, help="stack maps on a page up to this height in inches")
    ap.add_argument("--own-key", action="store_true", help="one map keeping the renderer's own key; no page composition")
    a = ap.parse_args(argv)
    out = Path(a.out)
    try:
        rows = read_spec(a.spec, a.root)
    except ValueError as e:
        _OUT.error(f"refused: {e}")
        return 2
    if a.own_key and len(rows) != 1:
        _OUT.error("refused: --own-key draws one map; the spec has more")
        return 2
    (out / "panels").mkdir(parents=True, exist_ok=True); (out / "logs").mkdir(exist_ok=True)
    pw, max_h = WIDTHS[a.width]
    done, status = [], []
    for r in rows:
        name = Path(r["run"]).name if Path(r["run"]).name.startswith(r["strain"]) else f"{r['strain']}_{Path(r['run']).name}"
        dst = out / "panels" / name
        if dst.exists():
            _OUT.error(f"refused: {dst} exists; give a new --out")
            return 2
        cmd = map_command(r, a, dst)
        with open(out / "logs" / f"{name}.log", "w") as log:
            p = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        ok = p.returncode == 0 and (dst / "gap_rescue.png").is_file()
        status.append(dict(letter=r["letter"], map=name, exit=p.returncode, drawn=ok, command=cmd))
        if ok:
            from PIL import Image
            done.append((r["letter"], dst, Image.open(dst / "gap_rescue.png").size[1] / PNG_DPI))
    pages = dict(tool="tools/locus_figure_pages.py", spec=str(Path(a.spec).resolve()), spec_sha256=sha256(a.spec),
                 width=a.width, page_width_in=pw, map_height_in=a.map_height or 6.2, maps=status)
    if not done or len(done) != len(rows):
        (out / f"{a.prefix}_PAGES.json").write_text(json.dumps(pages, indent=1) + "\n")
        _OUT.error(f"refused: {len(rows) - len(done)} of {len(rows)} maps were not drawn; see {out}/logs")
        return 2
    if a.own_key:
        import shutil
        for ext in ("png", "pdf"):
            shutil.copyfile(done[0][1] / f"gap_rescue.{ext}", out / f"{a.prefix}.{ext}")
        pages["pages"] = [[done[0][0]]]
    else:
        no_letter = len(done) == 1 and done[0][0] == "-"
        letters = "a" if no_letter else "".join(l for l, _, _ in done)
        groups = page_groups(list(letters), [h for _, _, h in done], a.page_limit)
        base = [sys.executable, str(TOOLS / "gap_rescue_panel_figure.py"), "--maps", *[str(d) for _, d, _ in done],
                "--letters", letters, "--print-width", str(pw), "--max-page-height", str(max_h), "--out", str(out / a.prefix)]
        cmd = base + (["--no-letter"] if no_letter else []) + (["--pages", ",".join("".join(g) for g in groups), "--overview"]
                                                               if len(groups) > 1 else [])
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode and len(groups) > 1:   # a group came out too tall: one map per page
            groups = [[l] for l in letters]
            cmd = base + ["--pages", ",".join(letters), "--overview"]
            p = subprocess.run(cmd, capture_output=True, text=True)
        (out / "logs" / f"{a.prefix}_pages.log").write_text(p.stdout + p.stderr)
        if p.returncode:
            (out / f"{a.prefix}_PAGES.json").write_text(json.dumps(pages, indent=1) + "\n")
            _OUT.error(f"refused: page composition failed; see {out}/logs/{a.prefix}_pages.log")
            return 2
        pages.update(pages=groups, page_command=cmd)
    pages["outputs_sha256"] = {f.name: sha256(f) for f in sorted(out.iterdir()) if f.is_file() and f.suffix in (".png", ".pdf")}
    (out / f"{a.prefix}_PAGES.json").write_text(json.dumps(pages, indent=1) + "\n")
    _OUT.info(f"{len(done)} maps on {len(pages['pages'])} page(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

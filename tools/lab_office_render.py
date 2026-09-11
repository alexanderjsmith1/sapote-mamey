#!/usr/bin/env python3
"""lab_office_render.py — the Lab Office "make-report" entry point (batch figure rendering).

Discovers every saved Figure Studio `.json` under a folder and renders each to SVG + 300-DPI PNG using the
HEADLESS Figure Studio engine (no browser) + cairosvg. Writes an INDEX.md and a sha256 manifest so a report
folder is reproducible and its inputs are pinned (ties to input_manifest / workflow-hardening).

One command turns a folder of figure JSONs into a report-ready figure set — the streamlined Lab Office path that
works identically in Claude Code and Codex (both have node + cairosvg locally).

Usage:
  python Tools/lab_office_render.py --dir "<folder of .json>" [--out <render dir>] [--dpi 300] [--recursive]
Defaults: --out = <dir>/_rendered ; --dpi 300 ; non-recursive.
Requires: node (miniconda3/bin/node), cairosvg (Tools/bin/python3). Both already local.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, hashlib, json, os, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NODE = os.path.join(ROOT, "miniconda3", "bin", "node")
RENDERER = os.path.join(ROOT, "FIGURE_STUDIO", "figure_studio_render.mjs")


def is_figure_json(p):
    try:
        o = json.load(open(p))
        return isinstance(o, dict) and "template" in o and "data" in o
    except Exception:
        return False


def sha256(p, buf=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(buf), b""):
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--recursive", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(NODE):
        emit(f"ERROR: node not found at {NODE}", file=sys.stderr); return 1
    if not os.path.isfile(RENDERER):
        emit(f"ERROR: renderer not found at {RENDERER}", file=sys.stderr); return 1
    try:
        import cairosvg  # noqa: F401
    except Exception:
        # v9.7.409 (CLAUDE_409_optional_deps_guard): already fail-closed (returns 1, never a bare
        # traceback); message now names the exact install so the PNG pass can be enabled.
        emit("ERROR: cairosvg not importable -- PNG rendering skipped. "
             "Install it with:  pip install cairosvg  (or:  pip install '.[render]'), "
             "or run under an interpreter that has it (e.g. Tools/bin/python3).",
             file=sys.stderr)
        return 1
    import cairosvg

    pat = os.path.join(args.dir, "**", "*.json") if args.recursive else os.path.join(args.dir, "*.json")
    jsons = sorted(p for p in glob.glob(pat, recursive=args.recursive) if is_figure_json(p))
    if not jsons:
        emit(f"no Figure Studio JSON found under {args.dir}", file=sys.stderr); return 1

    out = args.out or os.path.join(args.dir, "_rendered")
    os.makedirs(out, exist_ok=True)
    rows, ok, fail = [], 0, 0
    for j in jsons:
        stem = os.path.splitext(os.path.basename(j))[0]
        svg = os.path.join(out, stem + ".svg")
        png = os.path.join(out, stem + f"_{args.dpi}dpi.png")
        try:
            subprocess.run([NODE, RENDERER, j, svg], check=True, capture_output=True, text=True)
            # scale: viewBox px treated at 96 dpi baseline
            import xml.etree.ElementTree as ET
            view_box = ET.parse(svg).getroot().get("viewBox")
            if view_box is None:
                raise ValueError(f"rendered SVG has no viewBox attribute: {svg}")
            vb = view_box.split()
            w = float(vb[2]); ow = int(round(w * args.dpi / 96.0))
            cairosvg.svg2png(url=svg, write_to=png, output_width=ow)
            tpl = json.load(open(j)).get("template", "?")
            rows.append((stem, tpl, os.path.relpath(svg, out), os.path.relpath(png, out), sha256(j)))
            ok += 1
        except subprocess.CalledProcessError as e:
            emit(f"FAIL {stem}: {e.stderr.strip().splitlines()[-1] if e.stderr else e}", file=sys.stderr)
            fail += 1
        except Exception as e:
            # v97396 fix: this used to be uncaught -- a single figure whose rendered SVG lacks a
            # viewBox (or any other per-figure processing error beyond a failed node subprocess)
            # crashed main() entirely, before any remaining figure in the batch was even
            # attempted, and before INDEX.md/the manifest were ever written. One bad figure must
            # report as one FAIL, not take down the whole report folder.
            emit(f"FAIL {stem}: {e}", file=sys.stderr)
            fail += 1

    idx = os.path.join(out, "INDEX.md")
    now = datetime.date.today().isoformat()
    with open(idx, "w") as fh:
        fh.write(f"# Lab Office — rendered figures\n\n**Date:** {now} · **source:** `{args.dir}` · "
                 f"**engine:** headless Figure Studio + cairosvg @ {args.dpi} DPI\n\n")
        fh.write(f"Rendered **{ok}** figure(s)" + (f", **{fail}** failed" if fail else "") + ".\n\n")
        fh.write("| figure | template | SVG | PNG | source sha256 |\n|---|---|---|---|---|\n")
        for stem, tpl, s, p, h in rows:
            fh.write(f"| {stem} | {tpl} | `{s}` | `{p}` | `{h[:12]}…` |\n")
        fh.write("\n_Claim-safety travels in each figure's footer (class-level hypotheses, judgment deferred). "
                 "Figures regenerate from the JSON — edit the JSON in Figure Studio, re-run this._\n")
    emit(f"[lab_office] rendered {ok}/{len(jsons)} -> {out}  (index: {idx})")
    return 0 if fail == 0 else 3


if __name__ == "__main__":
    sys.exit(main())

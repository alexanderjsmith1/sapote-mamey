#!/usr/bin/env python3
"""Export an editable, portable ggtree source package from one rendered tree folder."""
from __future__ import annotations

import argparse, hashlib, json, shlex, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

# .452: placement_display writes a root-as-built diagnostic beside the accepted figure when the root edge is long
# (#482). Its files are not figure sources: every lookup below skips them, and the README lists them as diagnostics.
DIAGNOSTIC = "_GATE_FAIL_diagnostic_"


def one(folder: Path, pattern: str, label: str) -> Path:
    matches = sorted(p for p in folder.glob(pattern) if DIAGNOSTIC not in p.name)
    if len(matches) != 1:
        raise SystemExit(f"{label}: expected exactly one {pattern!r} in {folder}; found {len(matches)}")
    return matches[0]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--caption", help="caption text file; defaults to the renderer methods sidecar")
    ap.add_argument("--supplement", action="append", default=[],
                    help="additional provenance/selection file to copy; may be repeated")
    a = ap.parse_args()
    src, out = Path(a.source_dir).resolve(), Path(a.out).resolve()
    if out.exists(): raise SystemExit(f"output exists: {out}")
    if not src.is_dir(): raise SystemExit(f"source directory missing: {src}")
    meta = src / "display_input.tsv"
    fasta = src / "display_input.fasta"
    figure_png = one(src, "*_rect02.png", "PNG figure")
    figure_pdf = one(src, "*_rect02.pdf", "PDF figure")
    figure_stem = figure_png.name.removesuffix("_rect02.png")
    if not figure_stem or figure_pdf.name != figure_stem + "_rect02.pdf":
        raise SystemExit("PNG/PDF figure stems do not match")
    # the accepted display tree is bound by its exact name, never by a glob that a diagnostic could also match
    tree = src / f"{figure_stem}_display.nwk"
    if not tree.is_file():
        raise SystemExit(f"display tree: expected {tree.name} in {src}")
    diagnostics = sorted(p.name for p in src.iterdir() if DIAGNOSTIC in p.name)
    default_caption = one(src, "*_rect02.methods.txt", "caption sidecar")
    caption = Path(a.caption).resolve() if a.caption else default_caption
    methods = src / "METHODS.md"
    receipt_matches = [p for p in sorted(src.glob("*_display_receipt.json"))
                       if p.name != "placement_display_receipt.json" and DIAGNOSTIC not in p.name]
    if len(receipt_matches) != 1:
        raise SystemExit(f"display receipt: expected one stem-specific receipt; found {len(receipt_matches)}")
    receipt = receipt_matches[0]
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    analysis_name = receipt_payload["inputs"]["analysis_tree"]["path"]
    display_tree_name = receipt_payload["outputs"]["tree"]["path"]
    display_meta_name = receipt_payload["outputs"]["metadata"]["path"]
    analysis_tree = (src / analysis_name).resolve()
    required = [analysis_tree,meta,fasta,caption,methods,receipt]
    missing = [str(p) for p in required if not p.is_file()]
    if missing: raise SystemExit("missing required source files: " + ", ".join(missing))
    out.mkdir(parents=True)
    copies = [
      (HERE/"placement_stamp.py","placement_stamp.py"),
      (HERE.parent/"mamey/figure_stamp.py","mamey/figure_stamp.py"),
      (tree,f"{figure_stem}_tree.nwk"), (analysis_tree,f"{figure_stem}_analysis_tree.nwk"),
      (meta,f"{figure_stem}_metadata.tsv"), (fasta,f"{figure_stem}_aligned_sequences.fasta"),
      (caption,f"{figure_stem}_caption.txt"), (methods,f"{figure_stem}_methods.md"),
      (receipt,f"{figure_stem}_display_receipt.json"),
      (figure_png,f"{figure_stem}_clean.png"), (figure_pdf,f"{figure_stem}_clean.pdf"),
      (HERE/"ggtree_rect_heatmap.R",f"{figure_stem}_render_figure.R"),
      # gate_stem_aware.py binds this canonical internal dependency by name.
      # The collaborator-facing editable entry point above remains figure-specific.
      (HERE/"ggtree_rect_heatmap.R","ggtree_rect_heatmap.R"),
      (HERE/"tree_sanity_check.py","tree_sanity_check.py"),
      (HERE/"tree_annotation_gate.py","tree_annotation_gate.py"),
      (HERE/"tree_annotation_geometry.R","tree_annotation_geometry.R"),
      (HERE/"_phylo_metadata.py","_phylo_metadata.py"),
      (HERE/"phylo_display_contract.py","phylo_display_contract.py"),
      (HERE/"phylo_display_palette.tsv","phylo_display_palette.tsv"),
      (HERE/"gate_stem_aware.py","gate_stem_aware.py"),
      (HERE/"collapse_near_identical.py","collapse_near_identical.py"),
      (HERE/"_console.py","_console.py"),
      (HERE/"refresh_figure_source_manifest.py","refresh_figure_source_manifest.py"),
      (HERE.parent/"mamey/__init__.py","mamey/__init__.py"),
      (HERE.parent/"mamey/csv_safety.py","mamey/csv_safety.py"),
    ]
    display_summary = src / "placement_display_receipt.json"
    if display_summary.is_file():
        copies.append((display_summary, f"{figure_stem}_placement_display_receipt.json"))
    # Keep the receipt-bound names too. The generic aliases are convenient for editing;
    # these exact names permit fail-closed replay of the renderer's display gate.
    for group in ("inputs", "outputs"):
        for record in receipt_payload[group].values():
            source = (src / record["path"]).resolve()
            if not source.is_file() or source.parent != src:
                raise SystemExit(f"receipt-bound source unavailable: {source}")
            copies.append((source, record["path"]))
    pages_path = src / f"{figure_stem}_rect02.pages.json"
    if pages_path.is_file():
        pages = json.loads(pages_path.read_text())
        copies.append((pages_path, pages_path.name))
        for page in pages['pages']:
            for kind in ('pdf','png'):
                filename = page[kind]
                source = (src/filename).resolve()
                if source.parent != src or Path(filename).name != filename or not source.is_file():
                    raise SystemExit('page artifact outside figure folder or missing')
                copies.append((source,filename))
    for source,name in copies:
        (out/name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source,out/name)
    supplement = out / "supplementary_ledgers"
    extra = []
    for pattern in ("*_ledger.tsv", "*_selection.tsv", "custom_*.tsv",
                    "*_pairings.tsv", "required_closest_type.tsv",
                    "reference_metadata.tsv", "host_metadata.tsv", "genus_roster.tsv",
                    "label_sanity.tsv", "resolution_gaps.tsv",
                    "PANEL_SOURCE_MANIFEST.json", "BUILD_RECEIPT.json"):
        extra.extend(src.glob(pattern))
    for value in a.supplement:
        source = Path(value).resolve()
        if not source.is_file():
            raise SystemExit(f"supplement file missing: {source}")
        extra.append(source)
    if extra:
        supplement.mkdir()
        for source in sorted(set(extra)):
            shutil.copy2(source, supplement/source.name)
    # The editable R renderer remains the canonical entry point. This small shell helper is
    # convenience only and uses relative paths, so the package can move between machines.
    receipt_sha = sha(receipt)
    helper_name = f"{figure_stem}_rerender_captioned.sh"
    # Every interpolated value is shell-quoted. figure_stem comes from a filename and
    # analysis_name/display_* come from the receipt JSON, so a quote or $() in any of them
    # would otherwise be executed when an operator runs this helper. shlex.quote keeps the
    # generated script a data carrier rather than a second place the tool can run code.
    q = shlex.quote
    summary = json.loads(display_summary.read_text()) if display_summary.is_file() else {}
    replay_env = dict(summary.get('render_environment', {}))
    # Freeze the actual title choice; ambient opt-in must not change an exported replay.
    pages = json.loads(pages_path.read_text()) if pages_path.is_file() else {}
    if type(pages.get('page_titles')) is bool:
        replay_env['GG_PAGE_TITLE'] = '1' if pages['page_titles'] else '0'
    else:  # Legacy receipts: only the literal opt-in enables a title.
        replay_env['GG_PAGE_TITLE'] = '1' if replay_env.get('GG_PAGE_TITLE') == '1' else '0'
    allowed = {'GG_STRIPS','GG_ITALIC','GG_STRIP1_TITLE','GG_STRIP2_TITLE','GG_STRIP_KIND','GG_BLANK_MISSING',
               'GG_FOCAL_FACE','GG_FOCAL_BAND','GG_FIT_LABELS','GG_FIG_WIDTH','GG_PRINT_WIDTH',
               'GG_SUPPORT_MIN','GG_PAGE_TITLE','GG_CAPTION_MD','GG_ACTIVITY_SPEC','GG_ACTIVITY_PALETTE','GG_ACTIVITY_STATES','SAPOTE_GEOGRAPHY_LEVEL',
               'GG_SUPPORT_MAX','GG_SCALE_OFFSET',  # m5_452 tree display options
               'GG_SUPPORT_POS','GG_SUPPORT_UNPLACED','GG_SCALE_PAGES'}  # their v2 settings (v9.7.455 lane)
    replay_exports = '\n'.join('export '+key+'='+q(str(value)) for key,value in sorted(replay_env.items()) if key in allowed)
    (out/helper_name).write_text(f"""#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$HERE"
export GG_METHODS="$(cat {q(figure_stem + '_caption.txt')})"
export GG_FIGID="-"
export GG_STRIPS="2"
export GG_ITALIC="1"
export GG_STRIP1_TITLE="Isolation source"
export GG_STRIP2_TITLE="Location"
{replay_exports}
export GG_GATE_TREE={q(analysis_name)}
export GG_DISPLAY_RECEIPT={q(figure_stem + '_display_receipt.json')}
export GG_DISPLAY_RECEIPT_SHA256={q(receipt_sha)}
Rscript {q(figure_stem + '_render_figure.R')} {q(display_tree_name)} {q(display_meta_name)} {q(figure_stem + '_captioned')}
python3 refresh_figure_source_manifest.py
""",encoding="utf-8")
    (out/helper_name).chmod(0o755)
    (out/"README.md").write_text(f"""# Editable ggtree figure source package: {figure_stem}

This folder contains the exact displayed tree, its parent analysis tree, aligned FASTA, metadata, caption, complete methods, clean PNG/PDF, and the R/ggtree renderer used to draw the figure. Paths are relative to this folder.

Run `./{helper_name}` to make `{figure_stem}_captioned.png` and `{figure_stem}_captioned.pdf` with `{figure_stem}_caption.txt` in reserved white space below the tree. Edit `{figure_stem}_render_figure.R`, `{figure_stem}_metadata.tsv`, or the environment values in the helper to change typography, width, strips, colors, and caption layout. R packages required: ape, ggtree, ggplot2, aplot, treeio, and patchwork. Python 3 runs the included integrity gate and provenance stamper; print-width correction requires pypdf.

`{figure_stem}_clean.*` is the original clean render. `{figure_stem}_methods.md` and `{figure_stem}_caption.txt` travel with every copy. When available, `supplementary_ledgers/` retains reference-selection and grouping membership records. Editing the tree, FASTA, or scientific metadata creates a new analysis derivative and should receive a new receipt before publication.
"""
    + (("\n## Diagnostics (not figure sources)\n\nThe source folder also holds a root-as-built diagnostic render, which "
        "fails the strict tree gate by design and is kept only to show the tree before display rooting. It is not "
        "copied here:\n\n" + "".join(f"- `{n}`\n" for n in diagnostics)) if diagnostics else ""),
    encoding="utf-8")
    files = {str(p.relative_to(out)):{"sha256":sha(p),"bytes":p.stat().st_size}
             for p in sorted(out.rglob("*")) if p.is_file()}
    manifest={"schema":"sapote.tree-figure-source-package.v1","authority":"EDITABLE_RENDER_SOURCE_NOT_SCIENTIFIC_ACCEPTANCE","source_dir":str(src),"files":files}
    (out/"MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
    sys.stdout.write(str(out) + "\n")

if __name__ == "__main__": main()

#!/usr/bin/env python3
"""Check rendered figures before anyone uses them.

caption_guard.py checks caption files. The 2026-09-24 review found the offending text drawn inside
the images instead: footers, network keys ("query strain (AS)"), internal-notes bands, raw <i> tags,
literal "\\n", NA labels. This tool reads the text of each rendered figure and checks it.

Text sources, best first: the figure's own SVG (exact text), then macOS Vision OCR of the PNG
(compiled from figure_ocr.swift on first use, cached by sha256). A figure whose text could not be
read is reported as NOT CHECKED, never as clean.

Checks per figure (a PNG that is not a *_plot_only.png):
  text      claim-safety and governance wording (caption_guard.BLOCKED, same scoped "class-level"
            rule), raw HTML/markdown, literal \\n, NA/NaN/Inf, "page N of N", optional --extra-rules
  image     near-blank, dpi other than --dpi, transparent background, extreme aspect
  files     <stem>_plot_only.png, a PDF, a caption file; caption_guard on the caption file (a warning:
            the sidecar is not the page, but its caption gets pasted into manuscripts); raw HTML
  bioassay  (--bioassay) file name says crude, fraction or pooled; figure text says so too
  wording   "strains" is reported separately (house wording is "isolates"; not ruled for every figure)
Layout (overlaps, clipping, legend over data) is not judged. That still needs a person.

Usage:
  figure_render_qc.py <folder|png> [...] [--out DIR] [--ocr auto|off|require] [--bioassay]
                      [--extra-rules rules.tsv] [--dpi 300] [--warn-only]
  figure_render_qc.py --manifest MANIFEST.tsv [--out DIR] ...
  A manifest maps review copies to their source figures, whose folders hold the caption, PDF and
  _plot_only.png. Columns: png, source (paths absolute or relative to the manifest), optional note.
  The review-folder layout (section, review_file, figure_folder, source_png, note) is read too.
  A note containing "DO NOT USE" is reported as an error.
  rules.tsv columns: level (error|warn), name, regex. Example: error<TAB>Unassigned label<TAB>\\bUnassigned\\b
Writes RENDER_QC.md and RENDER_QC.tsv to --out (default: the first folder given).
Exit 0 = no errors · 2 = errors (do not use those figures) · 1 = usage problem.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from caption_guard import check_caption  # noqa: E402

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run from a foreign cwd
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

HERE = Path(__file__).resolve().parent
OCR_SRC = HERE / "figure_ocr.swift"
SKIP_DIRS = {"_replaced", "__MACOSX", "old", ".figure_qc_cache"}
LEVELS = ("error", "warn", "not_checked", "info", "wording")

TEXT_RULES = [
    ("error", "raw HTML tag", re.compile(r"</?(i|b|sup|sub|span|br|em|strong)\b[^>]*>", re.I)),
    ("error", "raw markdown", re.compile(r"\*\*[^*]+\*\*|(?<![\w*])\*[A-Z][a-z]+\*(?!\w)")),
    ("error", "literal \\n", re.compile(r"\\n")),
    ("error", "NA / NaN / Inf in text", re.compile(r"(?<![\w.-])(NA|NaN|Inf|-Inf)(?![\w.-])")),
    ("warn", "page N of N left in title", re.compile(r"\bpage \d+ of \d+\b", re.I)),
]
WORDING = re.compile(r"\bstrains\b", re.I)
MATERIAL = re.compile(r"crude|fraction|pooled", re.I)
CAPTION_TAG = re.compile(r"</?(?:b|i|span|br)\b[^>]*>")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_figures(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        cands = [p] if p.is_file() else sorted(p.rglob("*.png"))
        for f in cands:
            if f.suffix.lower() != ".png" or f.name.startswith("._") or f.stem.endswith("_plot_only"):
                continue
            if any(part in SKIP_DIRS or part.startswith("_withdrawn") for part in f.parts):
                continue
            out.append(f)
    return out


def read_manifest(path: Path) -> list[tuple[Path, Path, str]]:
    """Return (png, source_png, note) per row."""
    base = path.resolve().parent
    units = []
    for r in csv.DictReader(open(path), delimiter="\t"):
        if r.get("png"):
            png = base / r["png"]
            src = base / (r.get("source") or r["png"])
        elif r.get("review_file"):
            png = base / r.get("section", "") / r["review_file"]
            src = base.parent / r.get("figure_folder", "") / Path(r.get("source_png") or r["review_file"]).name
        else:
            raise SystemExit(f"{path}: needs columns png[,source] or section,review_file,figure_folder,source_png")
        units.append((png, src, r.get("note", "")))
    return units


def svg_text(svg: Path) -> list[str] | None:
    try:
        root = ET.parse(svg).getroot()
    except (ET.ParseError, OSError):
        return None
    lines = []
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] == "text":
            t = " ".join(s.strip() for s in el.itertext() if s.strip())
            if t:
                lines.append(t)
    return lines


class Ocr:
    """macOS Vision OCR, compiled once, results cached by image sha256."""

    def __init__(self, mode: str, cache_dir: Path):
        self.mode, self.bin, self.reason = mode, None, ""
        self.cache_file = cache_dir / "ocr.tsv"
        self.cache: dict[str, list[str]] = {}
        if mode == "off":
            self.reason = "OCR off"
            return
        if not shutil.which("swiftc") or not OCR_SRC.exists():
            self.reason = "OCR unavailable (needs macOS swiftc)"
            return
        cache_dir.mkdir(parents=True, exist_ok=True)
        binp = cache_dir / "figure_ocr"
        if not binp.exists() or binp.stat().st_mtime < OCR_SRC.stat().st_mtime:
            r = subprocess.run(["swiftc", "-O", str(OCR_SRC), "-o", str(binp)], capture_output=True, text=True)
            if r.returncode:
                self.reason = f"OCR build failed: {r.stderr.strip()[:120]}"
                return
        self.bin = binp
        if self.cache_file.exists():
            for line in self.cache_file.read_text(errors="ignore").splitlines():
                k, sep, t = line.partition("\t")
                if sep:
                    self.cache.setdefault(k, []).append(t)

    def read(self, pngs: dict[Path, str]) -> dict[Path, list[str] | None]:
        out: dict[Path, list[str] | None] = {}
        todo = [p for p, h in pngs.items() if h not in self.cache]
        # Small batches, cached as each finishes: an interrupted run resumes where it stopped.
        for i in range(0, len(todo) if self.bin else 0, 16):
            batch = todo[i:i + 16]
            res = subprocess.run([str(self.bin), *map(str, batch)], capture_output=True, text=True)
            by_path: dict[str, list[str]] = {}
            for line in res.stdout.splitlines():
                p, _, t = line.partition("\t")
                by_path.setdefault(p, []).append(t)
            with open(self.cache_file, "a") as fh:
                for p in batch:
                    lines = by_path.get(str(p), ["<<no text>>"])
                    self.cache[pngs[p]] = lines
                    for t in lines:
                        fh.write(f"{pngs[p]}\t{t.replace(chr(9), ' ')}\n")
            print(f"  OCR {min(i + 16, len(todo))}/{len(todo)}", file=sys.stderr)
        for p, h in pngs.items():
            lines = self.cache.get(h) if self.bin else None
            out[p] = None if lines is None or lines == ["<<unreadable>>"] else [t for t in lines if t != "<<no text>>"]
        return out


def caption_file(png: Path) -> Path | None:
    d, stem = png.parent, png.stem
    fig_id = "_".join(stem.split("_")[:2])
    cands = [d / f"{stem}_CAPTION.md", d / f"CAPTION_{stem}.md", d / f"CAPTION_{fig_id}.md",
             d / "CAPTION.md", d / "CAPTIONS.md", *sorted(d.glob(f"CAPTION_{fig_id}*.md"))]
    return next((c for c in cands if c.exists()), None)


def load_extra_rules(path: Path | None):
    if not path:
        return []
    rules = []
    for row in csv.reader(open(path), delimiter="\t"):
        if len(row) >= 3 and row[0] in ("error", "warn") and not row[0].startswith("#"):
            rules.append((row[0], row[1], re.compile(row[2])))
    return rules


def check_text(lines: list[str], rules) -> list[tuple[str, str]]:
    joined = "\n".join(lines)
    flags = []
    for level, name, rx in rules:
        hits = sorted({m.group(0) for m in rx.finditer(joined)})
        if hits:
            flags.append((level, f"{name}: {', '.join(hits[:4])}"))
    gov = check_caption(joined, raises=False)
    if gov:
        flags.append(("error", "claim-safety wording on the figure: " + ", ".join(p for p, _ in gov)))
    if WORDING.search(joined):
        flags.append(("wording", "says 'strains'"))
    return flags


def check_image(png: Path, want_dpi: int) -> list[tuple[str, str]]:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    flags = []
    with Image.open(png) as im:
        dpi = (im.info.get("dpi") or (0, 0))[0]
        w, h = im.size
        if dpi and abs(float(dpi) - want_dpi) > 5:
            flags.append(("warn", f"{float(dpi):.0f} dpi (expected {want_dpi})"))
        if im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 255:
            flags.append(("warn", "transparent background"))
        small = im.convert("L").resize((max(1, w // 8), max(1, h // 8)))
        hist = small.histogram()
        ink = sum(hist[:235]) / max(1, sum(hist))
        if ink < 0.01:
            flags.append(("error", f"near-blank image ({ink:.1%} ink)"))
        if h > 3 * w or w > 4 * h:
            flags.append(("info", f"extreme aspect {w}x{h}"))
    return flags


def check_files(png: Path) -> list[tuple[str, str]]:
    """Companion files are checked next to `png`, which is the SOURCE figure when a manifest is used."""
    flags, missing = [], []
    if not (png.parent / f"{png.stem}_plot_only.png").exists():
        missing.append("_plot_only.png")
    if not (png.with_suffix(".pdf")).exists():
        missing.append(".pdf")
    if missing:
        flags.append(("info", "missing next to figure: " + ", ".join(missing)))
    cap = caption_file(png)
    if cap is None:
        flags.append(("warn", "no caption file next to figure"))
        return flags
    text = cap.read_text(errors="replace")
    gov = check_caption(text, raises=False)
    if gov:
        # Not drawn on the figure (the text checks cover that), so a warning: Alex's 2026-09-24 rule keeps
        # claim guards in the work, not on the page. Strip it before the caption is pasted anywhere public.
        flags.append(("warn", f"claim-safety wording in {cap.name} (not on the figure; strip before a manuscript "
                              f"or talk): " + ", ".join(p for p, _ in gov)))
    tags = sorted(set(CAPTION_TAG.findall(text)))
    if tags:
        flags.append(("warn", f"raw HTML in {cap.name}: {', '.join(tags[:3])}"))
    return flags


def run(paths: list[Path], out: Path, ocr_mode: str = "auto", bioassay: bool = False,
        extra_rules: Path | None = None, want_dpi: int = 300,
        manifest: Path | None = None) -> list[tuple[Path, list[tuple[str, str]]]]:
    rules = TEXT_RULES + load_extra_rules(extra_rules)
    units = read_manifest(manifest) if manifest else [(f, f, "") for f in find_figures(paths)]
    figs = [u[0] for u in units]
    source = {u[0]: u[1] for u in units}
    notes = {u[0]: u[2] for u in units}
    ocr = Ocr(ocr_mode, out / ".figure_qc_cache")
    texts: dict[Path, list[str] | None] = {}
    need_ocr = {}
    for f in figs:
        svg = next((c for c in (source[f].with_suffix(".svg"), f.with_suffix(".svg")) if c.exists()), None)
        texts[f] = svg_text(svg) if svg else None
        if texts[f] is None:
            need_ocr[f] = sha256(f)
    texts.update({p: t for p, t in ocr.read(need_ocr).items() if t is not None})

    results = []
    for f in figs:
        flags = []
        if "DO NOT USE" in notes[f]:
            flags.append(("error", "defect logged: " + notes[f].split("DO NOT USE", 1)[1].strip(" :.")[:160]))
        lines = texts.get(f)
        if lines is None:
            flags.append(("not_checked", f"figure text not checked: no SVG next to it, {ocr.reason or 'OCR returned nothing'}"))
        else:
            flags += check_text(lines, rules)
        flags += check_image(f, want_dpi)
        flags += check_files(source[f])
        if bioassay:
            if not MATERIAL.search(f.name):
                flags.append(("error", "bioassay file name does not say crude, fraction or pooled"))
            if lines is not None and not MATERIAL.search("\n".join(lines)):
                flags.append(("warn", "bioassay figure text does not say crude, fraction or pooled"))
        results.append((f, flags))
    return results


def write_reports(results, out: Path, roots: list[Path]) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    order = {k: i for i, k in enumerate(LEVELS)}

    def rel(p: Path) -> str:
        for r in roots:
            base = r if r.is_dir() else r.parent
            if p.is_relative_to(base):
                return str(p.relative_to(base))
        return str(p)

    with open(out / "RENDER_QC.tsv", "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["figure", "level", "flag"])
        for f, fl in results:
            for lv, msg in sorted(fl, key=lambda x: order[x[0]]):
                w.writerow([rel(f), lv, msg])
    cnt = {k: sum(1 for _, fl in results for lv, _ in fl if lv == k) for k in LEVELS}
    md = ["# Figure render QC", "",
          f"{len(results)} figures. Errors {cnt['error']}, warnings {cnt['warn']}, text not checked {cnt['not_checked']}, "
          f"notes {cnt['info']}.",
          "Layout (overlaps, clipping, legends over data) is not judged here. A person still looks at every figure.", ""]
    for lv, title in [("error", "Errors: do not use until fixed"), ("warn", "Warnings"),
                      ("not_checked", "Text not checked"), ("info", "Notes")]:
        items = [f"- `{rel(f)}`: {m}" for f, fl in results for l, m in fl if l == lv]
        md += [f"## {title}", ""] + (items or ["None."]) + [""]
    wn = [rel(f) for f, fl in results if any(l == "wording" for l, _ in fl)]
    md += ["## Wording", "", f"{len(wn)} figures print \"strains\". House wording is \"isolates\"; "
           "whether it applies to every figure is Alex's call.", ""]
    (out / "RENDER_QC.md").write_text("\n".join(md))
    return cnt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--manifest", type=Path, help="TSV mapping review copies to source figures")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--ocr", choices=("auto", "off", "require"), default="auto")
    ap.add_argument("--bioassay", action="store_true", help="apply the crude/fraction/pooled labelling rule")
    ap.add_argument("--extra-rules", type=Path)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--warn-only", action="store_true")
    a = ap.parse_args(argv)
    if not a.paths and not a.manifest:
        ap.error("give figure folders/files or --manifest")
    missing = [p for p in [*a.paths, *([a.manifest] if a.manifest else [])] if not p.exists()]
    if missing:
        print(f"not found: {', '.join(map(str, missing))}", file=sys.stderr)
        return 1
    out = a.out or (a.manifest.parent if a.manifest else next((p for p in a.paths if p.is_dir()), a.paths[0].parent))
    results = run(a.paths, out, a.ocr, a.bioassay, a.extra_rules, a.dpi, a.manifest)
    if not results:
        print("no figures found (PNG files that are not *_plot_only.png)", file=sys.stderr)
        return 1
    cnt = write_reports(results, out, a.paths or [a.manifest.parent])
    print(f"checked {len(results)}; errors {cnt['error']}, warnings {cnt['warn']}, "
          f"text not checked {cnt['not_checked']}, notes {cnt['info']} -> {out / 'RENDER_QC.md'}")
    if a.ocr == "require" and cnt["not_checked"]:
        return 2
    return 2 if cnt["error"] and not a.warn_only else 0


if __name__ == "__main__":
    sys.exit(main())

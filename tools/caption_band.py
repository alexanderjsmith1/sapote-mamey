#!/usr/bin/env python3
"""caption_band.py — add a croppable caption band to a figure image, and keep the caption beside it.

House convention for publication figures (adopted 2026-09-22, used across the 2026-09-24 figure
sets). Each figure ships as a folder with:

  <name>_with_caption.png / .pdf   the plot with a white band baked into the bottom, under a
                                   hairline crop line marked "crop here for the manuscript figure"
  <name>_CAPTION.md                the same caption and methods, verbatim, as a sidecar

The methods travel with the image, so a figure on disk is never separated from how it was made.
For a manuscript, crop at the line and paste the caption normally.

The band is part of the image, so it is held to the same wording rule as the plot:
`mamey.figure_policy.FIGURE_BANNED_TEXT`. Wording that fails it is refused, not silently
dropped. Every line of the caption .md is printed, so the whole caption is checked.

Usage:
    python3 tools/caption_band.py <plot.png> <caption.md> [--outdir DIR]

Works on any PNG, matplotlib or R. Bold Arial where installed, DejaVu Sans Bold otherwise.
Needs Pillow (the `documents` extra); without it the tool prints why and exits 2.
"""
from __future__ import annotations

import argparse
import os as _os
import re
import shutil
import sys as _sys
import textwrap
from pathlib import Path

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from _console import emit  # noqa: E402
from mamey.figure_policy import figure_text_violations  # noqa: E402

INK = (23, 33, 46)
SUB = (84, 99, 122)
HAIR = (200, 208, 216)
PAPER = (255, 255, 255)
CROP_HINT = "↑ crop here for the manuscript figure"


class CaptionBandRefusal(ValueError):
    code = "CAPTION_BAND_REFUSED"


def _pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    return Image, ImageDraw, ImageFont


def load_font(image_font, size: int, bold: bool = True):
    candidates = (["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf"]
                  if bold else
                  ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"])
    # matplotlib is optional here: it only supplies a DejaVu fallback font. Without it the Arial
    # candidates above still apply, and Pillow's built-in font is the last resort below.
    try:
        import matplotlib
    except ImportError:
        matplotlib = None
    if matplotlib is not None:
        mpl = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
        candidates.append(str(mpl / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")))
    for path in candidates:
        if Path(path).exists():
            try:
                return image_font.truetype(path, size)
            except OSError:
                continue
    return image_font.load_default()


def flatten_md(md: str) -> list[str]:
    """Markdown to plain band lines: keeps the words, drops headings marks, bold, code and links."""
    out: list[str] = []
    for line in md.splitlines():
        s = line.strip()
        if not s:
            if out and out[-1] != "":
                out.append("")
            continue
        if s.startswith("#"):
            s = s.lstrip("#").strip()
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"`(.+?)`", r"\1", s)
        s = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", s)
        if s[:1] in "-*":
            s = s[1:].strip()
        out.append(s)
    return [s for s in out if s] or ["(caption)"]


def band_lines(caption_md: str) -> list[str]:
    """The exact lines that will be drawn, refused if any carries banned wording."""
    lines = flatten_md(caption_md)
    found = figure_text_violations(lines)
    if found:
        raise CaptionBandRefusal(
            f"CAPTION_BAND_REFUSED: {sorted(set(f.lower() for f in found))} would be printed on the "
            "figure. Every line of the caption .md is printed on the band, so keep that wording in "
            "the figure's receipt or a separate notes file, not the caption.")
    return lines


def add_band(plot_png, caption_md, outdir=None) -> Path:
    pil = _pillow()
    if pil is None:
        raise SystemExit("caption_band: Pillow is not installed (pip install '.[documents]'); "
                         "no figure was written")
    image_mod, draw_mod, font_mod = pil
    plot_png, caption_md = Path(plot_png), Path(caption_md)
    outdir = Path(outdir) if outdir else plot_png.parent
    outdir.mkdir(parents=True, exist_ok=True)

    md_text = caption_md.read_text(encoding="utf-8")
    lines_src = band_lines(md_text)

    img = image_mod.open(plot_png).convert("RGB")
    width, height = img.size
    fs = max(18, round(width * 0.0150))
    fs_head = max(20, round(width * 0.0170))
    line_h = round(fs * 1.42)
    margin = round(width * 0.035)
    body_font = load_font(font_mod, fs)
    head_font = load_font(font_mod, fs_head)
    small_font = load_font(font_mod, max(12, round(width * 0.010)))

    measure = draw_mod.Draw(img)

    def wrap(text, font):
        avg = measure.textlength("abcdefghijklmnopqrstuvwxyz ", font=font) / 27
        return textwrap.wrap(text, max(20, int((width - 2 * margin) / avg))) or [""]

    wrapped = [(w, head_font if i == 0 else body_font)
               for i, s in enumerate(lines_src) for w in wrap(s, head_font if i == 0 else body_font)]
    top_pad, gap_head, bot_pad = round(line_h * 1.05), round(line_h * 0.35), round(line_h * 1.0)
    band_h = top_pad + gap_head + line_h * len(wrapped) + bot_pad

    canvas = image_mod.new("RGB", (width, height + band_h), PAPER)
    canvas.paste(img, (0, 0))
    draw = draw_mod.Draw(canvas)
    draw.line([(margin, height), (width - margin, height)], fill=HAIR, width=max(2, round(width * 0.0012)))
    draw.text((width - margin, height + round(top_pad * 0.25)), CROP_HINT, font=small_font, fill=HAIR, anchor="ra")
    y = height + top_pad
    for i, (text, font) in enumerate(wrapped):
        draw.text((margin, y), text, font=font, fill=INK if i == 0 else SUB)
        y += line_h + (gap_head if i == 0 else 0)

    stem = plot_png.stem.replace("_plot_only", "")
    out_png = outdir / f"{stem}_with_caption.png"
    canvas.save(out_png, dpi=(300, 300))
    canvas.save(outdir / f"{stem}_with_caption.pdf", "PDF", resolution=300)
    sidecar = outdir / f"{stem}_CAPTION.md"
    if caption_md.resolve() != sidecar.resolve():
        shutil.copyfile(caption_md, sidecar)
    emit(f"wrote {out_png.name} (+.pdf) and {sidecar.name}  [band {band_h}px on {width}x{height}]")
    return out_png


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plot")
    ap.add_argument("caption")
    ap.add_argument("--outdir", default=None)
    a = ap.parse_args(argv)
    try:
        add_band(a.plot, a.caption, a.outdir)
    except CaptionBandRefusal as exc:
        emit(str(exc), file=_sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

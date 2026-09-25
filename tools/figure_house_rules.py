#!/usr/bin/env python3
"""House rules for publication figures: one place for the rules, and a checker that applies them.

The owner ruled these conventions while building the bee/wasp figure set (2026-09-22 to 09-24).
Until now they lived in chat notes and in one figure studio's scripts, so each new figure had to
rediscover them. This module holds them as data and checks a figure folder against them.

What it owns:
  * PATHOGEN_ORDER - fungi first, Gram-negatives together, MRSA last. order_pathogens() applies it,
    with an optional Enterobacter-omitted variant (Enterobacter is killed too easily and inflates
    apparent activity).
  * HOST_GROUPS - the four host-group labels for host-split figures, with display order and colours.
    This is a vocabulary, not a mapper: labels come from the deposited host string upstream and are
    never inferred here.
  * MATERIALS - every bioassay figure says whether it shows crude extracts, fractions, or both pooled.
  * The figure-folder layout: a caption sidecar travels with the image, plus a caption-free
    `<name>_plot_only.png` for slides.

What it does not own: which words may appear on a figure. That policy lives in caption_guard.py and
is applied here unchanged, to three surfaces - the caption sidecar, the text inside an SVG, and the
strings that renderer code draws onto a figure (scan-source).

Usage:
    python tools/figure_house_rules.py check <figure_dir>... [--bioassay] [--json]
    python tools/figure_house_rules.py scan-source <bundle_root> [--json]
    python tools/figure_house_rules.py pathogen-order [--drop-enterobacter] [--vertical]

`check` exits 1 when any ERROR is found and 0 otherwise. WARN findings (a missing plot-only image)
never fail the run, because most figures made before the 2026-09-24 ruling do not have one.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from caption_guard import check_caption  # noqa: E402  single source of truth for figure wording

PATHOGEN_ORDER: tuple[str, ...] = (
    "Candida albicans", "Candida auris",
    "E. coli", "Acinetobacter", "Enterobacter", "Klebsiella oxytoca", "Pseudomonas aeruginosa",
    "MRSA",
)
ENTEROBACTER = "Enterobacter"

# Display order and colours as used in the approved host-split figures (2026-09-23).
HOST_GROUPS: tuple[str, ...] = ("Bumblebees", "Honeybees", "Other bees", "Wasps")
HOST_GROUP_COLOURS: dict[str, str] = {
    "Bumblebees": "#2F5DA8", "Honeybees": "#C0973F", "Other bees": "#7E5AA2", "Wasps": "#2E8B84",
}
HOST_GROUP_AXIS_LABEL = "host group (as deposited)"

MATERIALS: dict[str, str] = {
    "crude": "crude extracts", "fraction": "fractions", "pooled": "crude extracts and fractions pooled",
}
_MATERIAL_TOKEN = re.compile(r"crude|fraction|pooled", re.I)

CAPTION_NAMES = ("CAPTION.md",)          # plus any `<name>_CAPTION.md`
PLOT_ONLY_SUFFIX = "_plot_only.png"

# Calls that put text onto a matplotlib figure. Strings passed to them are what a reader sees.
DRAWING_CALLS = frozenset({
    "text", "figtext", "suptitle", "set_title", "title", "annotate", "set_xlabel", "set_ylabel",
    "xlabel", "ylabel", "legend", "set_label", "table",
})
_R_DRAWING_LINE = re.compile(r"caption|ggtitle|labs\(|subtitle|annotate|mtext|title\s*=")
_SVG_TEXT = re.compile(r"<text\b[^>]*>(.*?)</text>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def order_pathogens(names, *, drop_enterobacter: bool = False, vertical: bool = False) -> list[str]:
    """Known pathogens in house order, then any unknown names sorted. `vertical` reverses the list so
    a plotting library that draws the first level at the bottom puts Candida at the top."""
    present = list(dict.fromkeys(str(n) for n in names))
    if drop_enterobacter:
        present = [n for n in present if n != ENTEROBACTER]
    known = [p for p in PATHOGEN_ORDER if p in present]
    unknown = sorted(n for n in present if n not in PATHOGEN_ORDER)
    out = known + unknown
    return out[::-1] if vertical else out


def unknown_host_groups(labels) -> list[str]:
    """Labels that are not one of the four ruled host groups (blank labels are ignored)."""
    return sorted({str(x) for x in labels if str(x).strip() and str(x) not in HOST_GROUPS})


def _finding(level: str, where: str, rule: str, detail: str) -> dict:
    return {"level": level, "where": where, "rule": rule, "detail": detail}


def _caption_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and (p.name in CAPTION_NAMES or p.name.endswith("_CAPTION.md")))


def check_folder(folder, *, bioassay: bool = False) -> list[dict]:
    """Check one figure folder. Returns findings; an empty list means the folder follows the rules."""
    folder = Path(folder)
    where = str(folder)
    if not folder.is_dir():
        return [_finding("ERROR", where, "FOLDER_MISSING", "not a directory, so it was not checked")]
    images = sorted(p for p in folder.iterdir()
                    if p.suffix.lower() in (".png", ".pdf", ".svg") and not p.name.startswith("."))
    if not images:
        return [_finding("ERROR", where, "NO_FIGURE", "no .png/.pdf/.svg in the folder")]
    out: list[dict] = []

    captions = _caption_files(folder)
    if not captions:
        out.append(_finding("ERROR", where, "CAPTION_MISSING",
                            "no CAPTION.md or <name>_CAPTION.md; the methods must travel with the figure"))
    for cap in captions:
        try:
            text = cap.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            out.append(_finding("ERROR", str(cap), "CAPTION_UNREADABLE", f"not checked: {exc}"))
            continue
        for phrase, why in check_caption(text, raises=False):
            out.append(_finding("ERROR", str(cap), "FIGURE_WORDING", f"{phrase!r}: {why}"))

    for svg in (p for p in images if p.suffix.lower() == ".svg"):
        try:
            raw = svg.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            out.append(_finding("ERROR", str(svg), "SVG_UNREADABLE", f"not checked: {exc}"))
            continue
        drawn = " ".join(_TAG.sub(" ", t) for t in _SVG_TEXT.findall(raw))
        for phrase, why in check_caption(drawn, raises=False):
            out.append(_finding("ERROR", str(svg), "FIGURE_WORDING", f"{phrase!r} drawn on the figure: {why}"))

    if not any(p.name.endswith(PLOT_ONLY_SUFFIX) for p in images):
        out.append(_finding("WARN", where, "PLOT_ONLY_MISSING",
                            f"no *{PLOT_ONLY_SUFFIX} (caption-free copy for slides)"))

    if bioassay:
        unlabelled = [p.name for p in images if not _MATERIAL_TOKEN.search(p.stem)]
        if unlabelled and not _MATERIAL_TOKEN.search(folder.name):
            out.append(_finding("ERROR", where, "MATERIAL_UNLABELLED",
                                "bioassay figure name does not say crude, fraction or pooled: "
                                + ", ".join(unlabelled)))
    return out


def scan_source(root) -> list[dict]:
    """List strings that renderer code draws onto a figure and that the wording policy refuses.

    Only strings passed to a drawing call (matplotlib) or on an R title/caption/label line count.
    A docstring or comment is not drawn, so it is not reported.
    """
    root = Path(root)
    hits: list[dict] = []
    for sub in ("mamey", "tools"):
        base = root / sub
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            try:
                tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except (SyntaxError, ValueError, OSError) as exc:
                hits.append(_finding("ERROR", str(p.relative_to(root)), "SOURCE_UNREADABLE", str(exc)))
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
                if name not in DRAWING_CALLS:
                    continue
                strings = [s.value for s in ast.walk(node)
                           if isinstance(s, ast.Constant) and isinstance(s.value, str)]
                found = check_caption(" ".join(strings), raises=False)
                if found:
                    hits.append(_finding("ERROR", f"{p.relative_to(root)}:{node.lineno}", "DRAWN_WORDING",
                                         f"{name}(): " + "; ".join(repr(x[0]) for x in found)))
    for p in sorted(root.rglob("*.R")):
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            hits.append(_finding("ERROR", str(p.relative_to(root)), "SOURCE_UNREADABLE", str(exc)))
            continue
        for i, line in enumerate(lines, 1):
            if _R_DRAWING_LINE.search(line):
                found = check_caption(line, raises=False)
                if found:
                    hits.append(_finding("ERROR", f"{p.relative_to(root)}:{i}", "DRAWN_WORDING",
                                         "R: " + "; ".join(repr(x[0]) for x in found)))
    return hits


def _write(findings: list[dict], as_json: bool) -> None:
    if as_json:
        sys.stdout.write(json.dumps(findings, indent=2) + "\n")
        return
    for f in findings:
        sys.stdout.write(f"{f['level']:5} {f['rule']:20} {f['where']}  {f['detail']}\n")
    n_err = sum(f["level"] == "ERROR" for f in findings)
    n_warn = sum(f["level"] == "WARN" for f in findings)
    sys.stdout.write(f"figure house rules: {n_err} error(s), {n_warn} warning(s)\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Publication-figure house rules")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check one or more figure folders")
    c.add_argument("folders", nargs="+")
    c.add_argument("--bioassay", action="store_true", help="also require crude/fraction/pooled in the name")
    c.add_argument("--json", action="store_true")
    s = sub.add_parser("scan-source", help="list figure text drawn by renderer code that the wording policy refuses")
    s.add_argument("root")
    s.add_argument("--json", action="store_true")
    o = sub.add_parser("pathogen-order", help="print the house pathogen order")
    o.add_argument("--drop-enterobacter", action="store_true")
    o.add_argument("--vertical", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "pathogen-order":
        sys.stdout.write("\n".join(order_pathogens(PATHOGEN_ORDER, drop_enterobacter=a.drop_enterobacter,
                                                   vertical=a.vertical)) + "\n")
        return 0
    if a.cmd == "scan-source":
        findings = scan_source(a.root)
        _write(findings, a.json)
        return 0          # an inventory for a ratchet, not a gate
    findings = [f for d in a.folders for f in check_folder(d, bioassay=a.bioassay)]
    _write(findings, a.json)
    return 1 if any(f["level"] == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""List every figure under a folder with the renderer stamp it carries.

Bundle renderers write their name into each file they save:
  PNG  tEXt "Software"            e.g. "Sapote-Mamey governed figure theme"
  PDF  /Creator or /Producer      e.g. "Sapote-Mamey Figure Factory Next"
  SVG  a comment or <metadata>    containing "Sapote-Mamey"

Verdicts:
  PASS          the file carries a Sapote-Mamey stamp
  PASS_DERIVED  a caption-band copy (<stem>_with_caption.*) whose <stem>_plot_only.png passes
  PLAIN_MPL     stamped by plain matplotlib: either a bundle tool that does not stamp yet, or a substitute
  UNKNOWN       no stamp either way: an unstamped R device, a screenshot, or another tool

PLAIN_MPL and UNKNOWN are not proof of a substitution until every bundle renderer stamps its output.
tests/test_figure_provenance_stamp.py keeps the list of bundle renderers that do not stamp yet.

A stamp shows which code saved the file. It does not check the data, the design, or the science.
Look at every figure as well.

Usage: check_figure_provenance.py FOLDER [--tsv OUT.tsv] [--strict]
  --strict  exit 1 if any figure is PLAIN_MPL or UNKNOWN
"""
from __future__ import annotations
import argparse, re, struct, sys, zlib
from collections import Counter
from pathlib import Path

try:
    from _console import emit
    from mamey.csv_safety import SafeDictWriter  # formula-injection guard for paths in the table
except ImportError:  # bare-script run from a foreign cwd
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from _console import emit
    from mamey.csv_safety import SafeDictWriter

MARK = "Sapote-Mamey"
EXTS = {".png", ".pdf", ".svg"}

def png_text(path: Path) -> dict:
    out = {}
    with path.open("rb") as h:
        if h.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("not a PNG")
        while True:
            head = h.read(8)
            if len(head) < 8:
                break
            n, kind = struct.unpack(">I4s", head)
            if kind == b"IDAT" or kind == b"IEND":
                break  # text chunks that matter are written before the image data
            body = h.read(n); h.read(4)
            if kind == b"tEXt" and b"\0" in body:
                k, v = body.split(b"\0", 1)
                out[k.decode("latin-1")] = v.decode("latin-1")
            elif kind == b"iTXt" and b"\0" in body:
                k, rest = body.split(b"\0", 1)
                flag = rest[0]; rest = rest[2:]
                _, rest = rest.split(b"\0", 1); _, text = rest.split(b"\0", 1)
                out[k.decode("latin-1")] = (zlib.decompress(text) if flag else text).decode("utf-8", "replace")
    return out

def pdf_text(path: Path) -> dict:
    data = path.read_bytes()
    out = {}
    for key in ("Creator", "Producer"):
        m = re.findall(rb"/" + key.encode() + rb"\s*\((.*?)(?<!\\)\)", data, re.S)
        if m:  # the last Info entry is the newest (incremental updates append)
            out[key] = m[-1].decode("latin-1")
    return out

def svg_text(path: Path) -> dict:
    head = path.read_bytes()[:20000].decode("utf-8", "replace")
    out = {}
    m = re.search(r"Sapote-Mamey[^<>\n]*", head)
    if m:
        out["Stamp"] = m.group(0).strip(" -")
    if "Created with matplotlib" in head or "matplotlib.org" in head:
        out["Generator"] = "matplotlib"
    return out

def stamp(path: Path) -> tuple[str, str]:
    """(verdict, evidence) from the file alone."""
    try:
        meta = {".png": png_text, ".pdf": pdf_text, ".svg": svg_text}[path.suffix.lower()](path)
    except Exception as exc:  # unreadable files are reported, not skipped
        return "UNKNOWN", f"unreadable: {exc}"
    text = "; ".join(f"{k}={v}" for k, v in meta.items())
    if any(MARK in v for v in meta.values()):
        return "PASS", text
    if any("matplotlib" in v.lower() for v in meta.values()):
        return "PLAIN_MPL", text
    return "UNKNOWN", text or "no stamp"

def check(folder: Path) -> list[dict]:
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTS)
    rows = {p: stamp(p) for p in files}
    out = []
    for p, (verdict, ev) in rows.items():
        if verdict == "UNKNOWN" and "_with_caption" in p.stem:
            # caption_band.py copies a plot_only PNG; its verdict follows the plot it was made from
            src = p.with_name(p.stem.replace("_with_caption", "_plot_only") + ".png")
            if src in rows and rows[src][0] == "PASS":
                verdict, ev = "PASS_DERIVED", f"from {src.name}: {rows[src][1]}"
        out.append(dict(verdict=verdict, path=str(p.relative_to(folder)), evidence=ev))
    return out

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--tsv", type=Path)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    if not a.folder.is_dir():
        ap.error(f"not a folder: {a.folder}")
    rows = check(a.folder)
    if a.tsv:
        with a.tsv.open("w", newline="") as h:
            w = SafeDictWriter(h, fieldnames=["verdict", "path", "evidence"], delimiter="\t")
            w.writeheader(); w.writerows(rows)
    n = Counter(r["verdict"] for r in rows)
    lines = [] if a.tsv else [f'{r["verdict"]:<13}{r["path"]}\t{r["evidence"]}' for r in rows]
    lines.append(f"{len(rows)} figures: " + ", ".join(f"{k} {n[k]}" for k in ("PASS", "PASS_DERIVED", "PLAIN_MPL", "UNKNOWN")))
    emit("\n".join(lines))
    return 1 if a.strict and (n["PLAIN_MPL"] or n["UNKNOWN"]) else 0

if __name__ == "__main__":
    sys.exit(main())

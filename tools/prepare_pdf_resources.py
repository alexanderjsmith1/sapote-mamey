#!/usr/bin/env python3
"""Resolve local Markdown image resources for a portable LaTeX fallback.

SVGs are converted only with an available local vector converter; unavailable
or malformed resources refuse the render. No network fetch or missing-image drop.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys

def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    text = source.read_text(encoding="utf-8")
    def image(match):
        raw = match.group(2).strip()
        name = raw[1:raw.index("> ")] if raw.startswith("<") and "> " in raw else raw.strip("<>")
        # Explicit angle targets support spaces. A quoted optional title is separate.
        if raw.startswith("<"):
            name = raw[1:raw.index(">")]
        else:
            name = raw.split(' "', 1)[0]
        if "://" in name:
            raise ValueError("PDF_REMOTE_RESOURCE_REFUSED")
        path = (source.parent / name).resolve()
        if not path.is_file():
            raise ValueError(f"PDF_IMAGE_UNAVAILABLE: {path}")
        if path.suffix.lower() == ".svg":
            import hashlib
            converted = destination.parent / (hashlib.sha256(str(path).encode()).hexdigest() + ".pdf")
            try:
                import cairosvg
                cairosvg.svg2pdf(url=str(path), write_to=str(converted))
            except Exception as exc:
                if shutil.which("rsvg-convert"):
                    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(converted), str(path)], check=True)
                elif shutil.which("inkscape"):
                    subprocess.run(["inkscape", str(path), "--export-type=pdf", f"--export-filename={converted}"], check=True)
                else:
                    raise ValueError("PDF_SVG_CONVERTER_UNAVAILABLE: install cairosvg, rsvg-convert or inkscape") from exc
            path = converted
        return f"![{match.group(1)}](<{path}>)"
    destination.write_text(re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", image, text), encoding="utf-8")

if __name__ == "__main__":
    prepare(sys.argv[1], sys.argv[2])

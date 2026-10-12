"""Write the Sapote-Mamey renderer stamp into saved figures.

Every bundle renderer should leave its name in the files it saves, so tools/check_figure_provenance.py can tell
bundle output from a figure made some other way. Two ways to do it:

  fig.savefig(path, metadata=savefig_metadata(path, "gap_rescue_locus_map"))   # matplotlib, at save time
  stamp_file(path, "caption_band")                                             # any PNG/PDF/SVG, after saving

The stamp names the code that saved the file. It says nothing about the data, the design, or the science.
"""
from __future__ import annotations
import re, struct, zlib
from pathlib import Path

PREFIX = "Sapote-Mamey"

def stamp_text(tool: str) -> str:
    return f"{PREFIX} {tool}"

def savefig_metadata(path, tool: str) -> dict:
    """metadata= for matplotlib savefig, by file type. Dates are left out so output stays reproducible."""
    ext = Path(path).suffix.lower()
    if ext == ".png":
        return {"Software": stamp_text(tool)}
    if ext == ".pdf":
        return {"Creator": stamp_text(tool), "CreationDate": None}
    if ext == ".svg":
        return {"Creator": stamp_text(tool), "Date": None}
    return {}

def _png_chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

def stamp_png(path, tool: str) -> None:
    p = Path(path); data = p.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {p}")
    out, i, done = [data[:8]], 8, False
    while i < len(data):
        n = struct.unpack(">I", data[i:i + 4])[0]; kind = data[i + 4:i + 8]; chunk = data[i:i + 12 + n]
        if kind == b"tEXt" and data[i + 8:i + 8 + n].split(b"\0", 1)[0] == b"Software":
            i += 12 + n; continue  # replace any earlier Software entry
        if kind == b"IDAT" and not done:
            out.append(_png_chunk(b"tEXt", b"Software\0" + stamp_text(tool).encode("latin-1"))); done = True
        out.append(chunk); i += 12 + n
    p.write_bytes(b"".join(out))

def stamp_svg(path, tool: str) -> None:
    p = Path(path); s = p.read_text(encoding="utf-8")
    m = re.search(r"<svg\b[^>]*>", s)
    if not m:
        raise ValueError(f"not an SVG: {p}")
    if f"<!-- {PREFIX}" not in s:
        s = s[:m.end()] + f"\n<!-- {stamp_text(tool)} -->" + s[m.end():]
        p.write_text(s, encoding="utf-8")

def stamp_pdf(path, tool: str) -> None:
    """Append an incremental-update Info dictionary; the original bytes are kept, readers take the newest Info."""
    p = Path(path); data = p.read_bytes()
    starts = re.findall(rb"startxref\s+(\d+)", data)
    root = re.findall(rb"/Root\s+(\d+\s+\d+\s+R)", data)
    sizes = re.findall(rb"/Size\s+(\d+)", data)
    if not (starts and root and sizes):
        raise ValueError(f"cannot stamp this PDF (no classic trailer): {p}")
    obj = int(sizes[-1]); off = len(data) + (0 if data.endswith(b"\n") else 1)
    body = (b"" if data.endswith(b"\n") else b"\n")
    info = f"{obj} 0 obj\n<< /Creator ({stamp_text(tool)}) >>\nendobj\n".encode("latin-1")
    xref = len(data) + len(body) + len(info)
    body += info + f"xref\n{obj} 1\n{off:010d} 00000 n \n".encode()
    body += (b"trailer\n<< /Size " + str(obj + 1).encode() + b" /Root " + root[-1] + b" /Info " + f"{obj} 0 R".encode()
             + b" /Prev " + starts[-1] + b" >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n")
    p.write_bytes(data + body)

def stamp_file(path, tool: str) -> None:
    {".png": stamp_png, ".svg": stamp_svg, ".pdf": stamp_pdf}[Path(path).suffix.lower()](path, tool)

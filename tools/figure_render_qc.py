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
import json
import io
import stat
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
            if f.stem.endswith("_with_caption") and p.is_dir() and (f.parent / f"{_base_stem(f)}.png").exists():
                continue   # the captioned copy of a figure already checked as <base>.png
            out.append(f)
    return out


def read_manifest(path: Path) -> list[tuple[Path, Path, str, str]]:
    """Return (review PNG, source PNG, note, optional expected SHA-256) per row."""
    base = path.resolve().parent
    units = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for r in csv.DictReader(handle, delimiter="\t"):
            if r.get("png"):
                png = base / r["png"]
                src = base / (r.get("source") or r["png"])
            elif r.get("review_file"):
                png = base / r.get("section", "") / r["review_file"]
                src = base.parent / r.get("figure_folder", "") / Path(r.get("source_png") or r["review_file"]).name
            else:
                raise SystemExit(f"{path}: needs columns png[,source] or section,review_file,figure_folder,source_png")
            units.append((png, src, r.get("note", ""), (r.get("sha256") or "").lower()))
    return units


def svg_text(svg: Path, raw_bytes: bytes | None = None) -> list[str] | None:
    try:
        root = ET.parse(io.BytesIO(raw_bytes) if raw_bytes is not None else svg).getroot()
    except (ET.ParseError, OSError):
        return None
    lines: list[str] = []
    undrawn = {"defs", "metadata", "title", "desc", "style", "script"}

    def hidden(el: ET.Element) -> bool:
        name = el.tag.rsplit("}", 1)[-1]
        style = re.sub(r"\s+", "", el.get("style", "").lower())
        return (name in undrawn or el.get("display", "").lower() == "none"
                or el.get("visibility", "").lower() == "hidden"
                or "display:none" in style or "visibility:hidden" in style)

    def visible_text(el: ET.Element) -> list[str]:
        chunks = [el.text or ""]
        for child in el:
            if not hidden(child):
                chunks.extend(visible_text(child))
            chunks.append(child.tail or "")
        return chunks

    def visit(el: ET.Element) -> None:
        if hidden(el):
            return
        if el.tag.rsplit("}", 1)[-1] == "text":
            value = " ".join(s.strip() for s in visible_text(el) if s.strip())
            if value:
                lines.append(value)
            return
        for child in el:
            visit(child)

    visit(root)
    # An SVG containing only definitions or metadata does not verify its PNG's text.
    return lines or None


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

    def read(self, pngs: dict[Path, str], admitted_bytes: dict[Path, bytes] | None = None) -> dict[Path, list[str] | None]:
        out: dict[Path, list[str] | None] = {}
        todo = [p for p, h in pngs.items() if h not in self.cache]
        # Small batches, cached as each finishes: an interrupted run resumes where it stopped.
        for i in range(0, len(todo) if self.bin else 0, 16):
            batch = todo[i:i + 16]
            execution_paths = {}
            for path in batch:
                if admitted_bytes and path in admitted_bytes:
                    raw = admitted_bytes[path]
                    if hashlib.sha256(raw).hexdigest() != pngs[path]:
                        raise RenderPacketAdmissionRefusal("OCR snapshot differs from admitted image")
                    directory = self.cache_file.parent / "admitted_pngs"
                    if directory.is_symlink():
                        raise RenderPacketAdmissionRefusal("OCR snapshot folder must not be a symlink")
                    directory.mkdir(parents=True, exist_ok=True)
                    snapshot = directory / (pngs[path] + ".png")
                    expected = {"bytes": len(raw), "sha256": pngs[path]}
                    try:
                        try:
                            with snapshot.open("xb") as handle:
                                handle.write(raw)
                        except FileExistsError:
                            # Reuse is admitted only after a regular no-follow read,
                            # matching binding and equality with the consumed buffer.
                            reused = _packet_read(directory, Path(snapshot.name), expected)
                            if reused != raw:
                                raise ValueError("existing OCR snapshot differs from admitted bytes")
                        else:
                            _packet_read(directory, Path(snapshot.name), expected, keep=False)
                    except (OSError, ValueError) as exc:
                        raise RenderPacketAdmissionRefusal(f"OCR snapshot refused: {exc}") from exc
                    execution_paths[path] = snapshot
                else:
                    execution_paths[path] = path
            res = subprocess.run([str(self.bin), *[str(execution_paths[p]) for p in batch]], capture_output=True, text=True)
            for path, execution_path in execution_paths.items():
                if execution_path != path:
                    try:
                        _packet_read(execution_path.parent, Path(execution_path.name),
                                     {"bytes": len(admitted_bytes[path]), "sha256": pngs[path]}, keep=False)
                    except (OSError, ValueError) as exc:
                        raise RenderPacketAdmissionRefusal(f"OCR snapshot changed during OCR: {exc}") from exc
            by_path: dict[str, list[str]] = {}
            for line in res.stdout.splitlines():
                p, _, t = line.partition("\t")
                by_path.setdefault(p, []).append(t)
            with open(self.cache_file, "a") as fh:
                for p in batch:
                    # An empty OCR response or a failed subprocess cannot certify text absence.
                    lines = by_path.get(str(execution_paths[p]), [])
                    if res.returncode or not lines:
                        lines = ["<<unreadable>>"]
                    self.cache[pngs[p]] = lines
                    for t in lines:
                        fh.write(f"{pngs[p]}\t{t.replace(chr(9), ' ')}\n")
            print(f"  OCR {min(i + 16, len(todo))}/{len(todo)}", file=sys.stderr)
        for p, h in pngs.items():
            lines = self.cache.get(h) if self.bin else None
            recognized = [t for t in (lines or []) if t.strip() and t not in ("<<no text>>", "<<unreadable>>")]
            out[p] = recognized if recognized and "<<unreadable>>" not in (lines or []) else None
        return out


def _base_stem(png: Path) -> str:
    """tools/caption_band.py writes <base>_with_caption.png beside <base>_plot_only.png and <base>_CAPTION.md."""
    return png.stem[: -len("_with_caption")] if png.stem.endswith("_with_caption") else png.stem


def caption_file(png: Path) -> Path | None:
    d, stem = png.parent, _base_stem(png)
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


def check_image(png: Path, want_dpi: int, print_width_in: float | None = None, raw_bytes: bytes | None = None) -> list[tuple[str, str]]:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    flags = []
    with Image.open(io.BytesIO(raw_bytes) if raw_bytes is not None else png) as im:
        dpi = (im.info.get("dpi") or (0, 0))[0]
        w, h = im.size
        # Metadata DPI is a print hint, never proof of native resolution.
        if dpi and float(dpi) + 5 < want_dpi:
            flags.append(("warn", f"metadata DPI {float(dpi):.0f} below minimum {want_dpi}; not a native-pixel measurement"))
        metadata = f"{float(dpi):.2f}" if dpi else "NOT_RECORDED"
        if print_width_in is None:
            flags.append(("info", f"raster {w}x{h}px; metadata DPI {metadata}; effective DPI NOT_CHECKED (no declared print width)"))
        else:
            effective = w / print_width_in
            level = "error" if w + 1 < want_dpi * print_width_in else "info"
            flags.append((level, f"raster {w}x{h}px at declared width {print_width_in:g}in: effective DPI {effective:.2f}; "
                                 f"minimum {want_dpi}; metadata DPI {metadata}; native render provenance not verified by QC"))
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


class RenderPacketWriteConflict(ValueError):
    """QA report destinations must be fresh, independent of receipt validity."""


class RenderPacketAdmissionRefusal(ValueError):
    """A refused completed packet is never sent to content QA or report writing."""


def admit_qa_destination(out: Path) -> None:
    """Protect existing reports even when a receipt is absent, malformed or untrusted."""
    for name in ("RENDER_QC.md", "RENDER_QC.tsv"):
        report = out / name
        if report.exists() or report.is_symlink():
            raise RenderPacketWriteConflict(f"QA report already exists: {report}; choose a fresh --out folder")


def packet_reader_requirements() -> list[str]:
    """Feature admission, not an operating-system name or an unsafe flag fallback."""
    missing = [name for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
               if type(getattr(_os, name, None)) is not int or not getattr(_os, name, 0)]
    supported = getattr(_os, "supports_dir_fd", None)
    if not isinstance(supported, (set, frozenset)) or _os.open not in supported:
        missing.append("os.open dir_fd")
    return missing


def _packet_read(root: Path, relative: Path, expected: dict | None = None,
                 *, keep: bool = True, max_bytes: int | None = None) -> bytes | None:
    """Read through directory handles without following packet-member symlinks.

    Hash the same buffers returned to content QA. Stat/read/stat alone is not a
    binding: the consumed buffer must match the admitted size and SHA-256.
    """
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError("invalid local packet locator")
    missing = packet_reader_requirements()
    if missing:
        raise ValueError("completed-packet reader unavailable; required capabilities: " + ", ".join(missing))
    descriptors = []
    try:
        directory = _os.open(root, _os.O_RDONLY | _os.O_DIRECTORY | _os.O_NOFOLLOW)
        descriptors.append(directory)
        for part in relative.parts[:-1]:
            directory = _os.open(part, _os.O_RDONLY | _os.O_DIRECTORY | _os.O_NOFOLLOW, dir_fd=directory)
            descriptors.append(directory)
        fd = _os.open(relative.name, _os.O_RDONLY | _os.O_NOFOLLOW | _os.O_NONBLOCK, dir_fd=directory)
        descriptors.append(fd)
        info = _os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("packet member is not a regular file")
        if max_bytes is not None and info.st_size > max_bytes:
            raise ValueError("receipt exceeds bounded manifest size")
        digest = hashlib.sha256(); chunks = []; length = 0
        while chunk := _os.read(fd, 1024 * 1024):
            length += len(chunk)
            if max_bytes is not None and length > max_bytes:
                raise ValueError("receipt exceeds bounded manifest size")
            digest.update(chunk)
            if keep:
                chunks.append(chunk)
        if expected is not None and (length != expected["bytes"] or digest.hexdigest() != expected["sha256"]):
            raise ValueError(f"completed output changed or missing: {relative.as_posix()}")
        return b"".join(chunks) if keep else None
    except (NotImplementedError, TypeError) as exc:
        raise ValueError(f"completed-packet descriptor traversal unavailable: {exc}") from exc
    finally:
        for fd in reversed(descriptors):
            _os.close(fd)


class PacketAdmission:
    """One admitted generation; content uses captured bytes and later drift refuses."""
    def __init__(self, root, files, receipt_bytes, png, caption, svg):
        self.root, self.files = root, files
        self.receipt_binding = {"bytes": len(receipt_bytes), "sha256": hashlib.sha256(receipt_bytes).hexdigest()}
        self.png, self.caption, self.svg = png, caption, svg
        self.buffers = {}
        for path in (png, caption, svg):
            if path is not None:
                relative = path.relative_to(root)
                self.buffers[path] = _packet_read(root, relative, files[relative.as_posix()][1])

    def recheck(self):
        try:
            _packet_read(self.root, Path("render_receipt.json"), self.receipt_binding, keep=False, max_bytes=4*1024*1024)
            if caption_file(self.png) != self.caption:
                raise ValueError("consumed caption selection changed after admission")
            current_svg = self.png.with_suffix(".svg")
            if (current_svg.exists() or current_svg.is_symlink()) != (self.svg is not None):
                raise ValueError("consumed SVG selection changed after admission")
            for name, (_, record) in self.files.items():
                _packet_read(self.root, Path(name), record, keep=False)
        except (OSError, ValueError) as exc:
            raise RenderPacketAdmissionRefusal(f"completed packet changed after admission: {exc}") from exc


class QaResults(list):
    def __init__(self, values, packets, reviews):
        super().__init__(values)
        self.packets, self.reviews = packets, reviews

    def recheck(self):
        for packet in self.packets:
            packet.recheck()
        for path, record in self.reviews.items():
            try:
                _packet_read(path.parent.resolve(), Path(path.name), record, keep=False)
            except (OSError, ValueError) as exc:
                raise RenderPacketAdmissionRefusal(f"review image changed after admission: {exc}") from exc


def completed_packet_flags(png: Path, expected_receipt_sha256: str | None = None,
                           qa_out: Path | None = None,
                           *, admission: dict | None = None) -> list[tuple[str, str]]:
    """Revalidate current bytes inside the selected artifact root, including transfers.

    An unpinned receipt checks staleness against its own manifest, not authenticity.
    Original paths are parsed lexically and never opened after a transfer.
    """
    root = png.parent.resolve()
    receipt = root / "render_receipt.json"
    if receipt.is_symlink():
        return [("error", "completed packet receipt must not be a symlink")]
    if not receipt.exists():
        return [("error", "expected completed packet receipt is missing")] if expected_receipt_sha256 else []
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    try:
        if receipt.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("receipt exceeds bounded manifest size")
        raw = _packet_read(root, Path("render_receipt.json"), max_bytes=4*1024*1024)
        receipt_hash = hashlib.sha256(raw).hexdigest()
        if expected_receipt_sha256 and receipt_hash != expected_receipt_sha256:
            raise ValueError("receipt SHA-256 differs from the admitted transfer binding")
        payload = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
        if not isinstance(payload, dict) or payload.get("completion_state") != "COMPLETE":
            raise ValueError("receipt does not establish a completed packet")
        origin = payload.get("artifact_root") or payload.get("args", {}).get("out")
        if not isinstance(origin, str) or not Path(origin).is_absolute() or ".." in Path(origin).parts:
            raise ValueError("absolute original artifact root is not recorded")
        original = Path(origin)
        records = payload.get("outputs")
        if not isinstance(records, list) or not records:
            raise ValueError("completed output roster is missing")
        files = {}
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                raise ValueError("invalid output binding")
            historical = Path(record["path"])
            if not historical.is_absolute():
                raise ValueError("historical output path is not absolute")
            try:
                relative = historical.relative_to(original)
            except ValueError:
                raise ValueError("output binding is outside the original artifact root") from None
            if not relative.parts or ".." in relative.parts or relative.as_posix() == "render_receipt.json":
                raise ValueError("invalid or self-referential output locator")
            declared = record.get("relative_path")
            if declared is not None and declared != relative.as_posix():
                raise ValueError("relative and historical output locators disagree")
            if relative.as_posix() in files:
                raise ValueError("duplicate output locator")
            if not isinstance(record.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
                raise ValueError("output SHA-256 is missing or invalid")
            if type(record.get("bytes")) is not int or record["bytes"] < 0:
                raise ValueError("output byte length is missing or invalid")
            current = root / relative
            if any(part.is_symlink() for part in [current, *list(current.parents)[:len(relative.parts)-1]]):
                raise ValueError("completed output traverses a symlink")
            files[relative.as_posix()] = (current, record)
        required = {png.name}
        cap = caption_file(root/png.name)
        if cap is not None:
            required.add(cap.name)
        svg = (root/png.name).with_suffix(".svg") if (root/png.name).with_suffix(".svg").exists() else None
        if svg is not None:
            required.add(svg.name)
        if not required <= files.keys():
            raise ValueError("selected image, SVG or caption is outside the completed roster")
        if qa_out is not None:
            destination = qa_out.resolve()
            if any(current.is_relative_to(destination) for current, _ in files.values()):
                raise RenderPacketWriteConflict("QA destination overlaps completed packet outputs; choose a fresh --out folder")
        for current, record in files.values():
            _packet_read(root, current.relative_to(root), record, keep=False)
        if admission is not None:
            admission["packet"] = PacketAdmission(root, files, raw, root/png.name, cap, svg)
    except RenderPacketWriteConflict:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
        return [("error", f"completed packet freshness refused: {exc}")]
    return [("info", f"completed packet: {len(files)} admitted output bindings verified at admission; content QA uses byte-bound readers; receipt SHA-256 {receipt_hash}; "
                      f"{'externally pinned' if expected_receipt_sha256 else 'self-manifest freshness only'}")]


def check_files(png: Path, packet: PacketAdmission | None = None) -> list[tuple[str, str]]:
    """Companion files are checked next to `png`, which is the SOURCE figure when a manifest is used."""
    flags, missing = [], []
    present = (lambda path: path.name in packet.files) if packet is not None else (lambda path: path.exists())
    if not present(png.parent / f"{_base_stem(png)}_plot_only.png"):
        missing.append("_plot_only.png")
    if not present(png.with_suffix(".pdf")):
        missing.append(".pdf")
    if missing:
        flags.append(("info", "missing next to figure: " + ", ".join(missing)))
    cap = packet.caption if packet is not None else caption_file(png)
    if cap is None:
        flags.append(("warn", "no caption file next to figure"))
        return flags
    try:
        text = packet.buffers[cap].decode("utf-8") if packet is not None else cap.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        flags.append(("error", f"caption unreadable: {cap.name} ({type(exc).__name__})"))
        return flags
    gov = check_caption(text, raises=False)
    if gov:
        # Not drawn on the figure (the text checks cover that), so a warning: The owner's 2026-09-24 rule keeps
        # claim guards in the work, not on the page. Strip it before the caption is pasted anywhere public.
        flags.append(("warn", f"claim-safety wording in {cap.name} (not on the figure; strip before a manuscript "
                              f"or talk): " + ", ".join(p for p, _ in gov)))
    tags = sorted(set(CAPTION_TAG.findall(text)))
    if tags:
        flags.append(("warn", f"raw HTML in {cap.name}: {', '.join(tags[:3])}"))
    return flags


def run(paths: list[Path], out: Path, ocr_mode: str = "auto", bioassay: bool = False,
        extra_rules: Path | None = None, want_dpi: int = 300,
        manifest: Path | None = None, print_width_in: float | None = None,
        expected_render_receipt_sha256: str | None = None) -> list[tuple[Path, list[tuple[str, str]]]]:
    admit_qa_destination(out)
    rules = TEXT_RULES + load_extra_rules(extra_rules)
    units = read_manifest(manifest) if manifest else [(f, f, "", "") for f in find_figures(paths)]
    admissions = {i: {} for i in range(len(units))}
    packet_flags = {i: completed_packet_flags(source, expected_render_receipt_sha256, out, admission=admissions[i])
                    for i, (_, source, _, _) in enumerate(units)}
    packets = {i: state["packet"] for i, state in admissions.items() if "packet" in state}
    refused = [(str(units[i][1]), msg) for i, flags in packet_flags.items()
               for level, msg in flags if level == "error"]
    if refused:
        raise RenderPacketAdmissionRefusal("completed packet admission refused: " +
                                           "; ".join(f"{path}: {msg}" for path, msg in refused))
    # A review PNG can occur in several manifest rows with different source,
    # hash or defect obligations. Keep row state separate; only OCR of the
    # identical review image is shared by path.
    ocr = Ocr(ocr_mode, out / ".figure_qc_cache")
    texts: dict[int, list[str] | None] = {}
    need_ocr = {}
    bound_ocr_bytes = {}
    review_buffers = {}
    review_bindings = {}
    identity_flags: dict[int, list[tuple[str, str]]] = {}
    for index, (f, source, note, expected) in enumerate(units):
        flags: list[tuple[str, str]] = list(packet_flags[index])
        packet = packets.get(index)
        if packet is not None:
            if f.absolute() == source.absolute():
                review_buffers[index] = packet.buffers[packet.png]
            else:
                try:
                    review_buffers[index] = _packet_read(f.parent.resolve(), Path(f.name))
                except (OSError, ValueError) as exc:
                    raise RenderPacketAdmissionRefusal(f"review image admission refused: {exc}") from exc
            review_hash = hashlib.sha256(review_buffers[index]).hexdigest()
            review_bindings[f] = {"bytes": len(review_buffers[index]), "sha256": review_hash}
        else:
            review_hash = sha256(f) if f.is_file() else None
        if manifest:
            if review_hash is None:
                flags.append(("error", "review PNG missing"))
            if not source.is_file():
                flags.append(("error", "source PNG missing"))
            elif review_hash is not None and (hashlib.sha256(packet.buffers[packet.png]).hexdigest() if packet is not None else sha256(source)) != review_hash:
                flags.append(("error", "review/source PNG mismatch"))
            if expected and review_hash != expected:
                flags.append(("error", "manifest SHA-256 mismatch"))
        identity_flags[index] = flags
        svg = None if any(lv == "error" for lv, _ in flags) else (packet.svg if packet is not None else next(
            (c for c in (source.with_suffix(".svg"), f.with_suffix(".svg")) if c.exists()), None))
        texts[index] = (svg_text(svg, packet.buffers[svg]) if packet is not None else svg_text(svg)) if svg else None
        if texts[index] is None and review_hash is not None and not any(lv == "error" for lv, _ in packet_flags[index]):
            need_ocr[f] = review_hash
            if packet is not None:
                bound_ocr_bytes[f] = review_buffers[index]
    ocr_texts = ocr.read(need_ocr, admitted_bytes=bound_ocr_bytes) if bound_ocr_bytes else ocr.read(need_ocr)

    results = []
    for index, (f, source, note, expected) in enumerate(units):
        flags = list(identity_flags[index])
        if any(lv == "error" for lv, _ in packet_flags[index]):
            flags.append(("not_checked", "figure content not checked after completed packet freshness refusal"))
            results.append((f, flags))
            continue
        if "DO NOT USE" in note:
            flags.append(("error", "defect logged: " + note.split("DO NOT USE", 1)[1].strip(" :.")[:160]))
        lines = texts[index] if texts[index] is not None else ocr_texts.get(f)
        if lines is None:
            flags.append(("not_checked", f"figure text not checked: no SVG next to it, {ocr.reason or 'OCR returned nothing'}"))
        else:
            flags += check_text(lines, rules)
        packet = packets.get(index)
        if packet is not None:
            flags += check_image(f, want_dpi, print_width_in, review_buffers[index])
        elif f.is_file():
            flags += check_image(f, want_dpi, print_width_in)
        flags += check_files(source, packet) if packet is not None else check_files(source)
        if bioassay:
            if not MATERIAL.search(f.name):
                flags.append(("error", "bioassay file name does not say crude, fraction or pooled"))
            if lines is not None and not MATERIAL.search("\n".join(lines)):
                flags.append(("warn", "bioassay figure text does not say crude, fraction or pooled"))
        results.append((f, flags))
    result = QaResults(results, list(packets.values()), review_bindings)
    result.recheck()
    return result


def write_reports(results, out: Path, roots: list[Path]) -> dict[str, int]:
    admit_qa_destination(out)
    if isinstance(results, QaResults):
        results.recheck()
    out.mkdir(parents=True, exist_ok=True)
    order = {k: i for i, k in enumerate(LEVELS)}

    def rel(p: Path) -> str:
        for r in roots:
            base = r if r.is_dir() else r.parent
            if p.is_relative_to(base):
                return str(p.relative_to(base))
        return str(p)

    # Reserve both destinations exclusively before writing either report. A race
    # can leave a new empty file, retained for inspection; it cannot truncate an old one.
    from contextlib import ExitStack
    reservations = ExitStack()
    try:
        fh = reservations.enter_context(open(out / "RENDER_QC.tsv", "x", newline=""))
        markdown = reservations.enter_context(open(out / "RENDER_QC.md", "x"))
    except FileExistsError as exc:
        reservations.close()
        raise RenderPacketWriteConflict("QA report appeared during admission; choose a fresh --out folder") from exc
    with reservations:
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
               "whether it applies to every figure is the owner's call.", ""]
        markdown.write("\n".join(md))
    return cnt


def cli_failure(message: str, exit_code: int) -> int:
    """One stderr outcome path for missing input, empty selection or admission refusal."""
    print(message, file=sys.stderr)
    return exit_code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--manifest", type=Path, help="TSV mapping review copies to source figures")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--ocr", choices=("auto", "off", "require"), default="auto")
    ap.add_argument("--bioassay", action="store_true", help="apply the crude/fraction/pooled labelling rule")
    ap.add_argument("--extra-rules", type=Path)
    ap.add_argument("--dpi", type=int, default=300, help="minimum raster DPI, not an exact target")
    ap.add_argument("--print-width-in", type=float, help="declared embedded width for every selected PNG; checks pixels/width independently of metadata")
    ap.add_argument("--render-receipt-sha256", help="admitted SHA-256 for one completed packet, including a transferred folder")
    ap.add_argument("--warn-only", action="store_true")
    a = ap.parse_args(argv)
    if a.dpi <= 0:
        ap.error("--dpi must be positive")
    if a.print_width_in is not None and (not __import__("math").isfinite(a.print_width_in) or a.print_width_in <= 0):
        ap.error("--print-width-in must be finite and positive")
    if a.render_receipt_sha256 and not re.fullmatch(r"[0-9a-f]{64}", a.render_receipt_sha256):
        ap.error("--render-receipt-sha256 must be a lowercase SHA-256")
    if not a.paths and not a.manifest:
        ap.error("give figure folders/files or --manifest")
    missing = [p for p in [*a.paths, *([a.manifest] if a.manifest else [])] if not p.exists()]
    if missing:
        return cli_failure(f"not found: {', '.join(map(str, missing))}", 1)
    out = a.out or (a.manifest.parent if a.manifest else next((p for p in a.paths if p.is_dir()), a.paths[0].parent))
    try:
        results = run(a.paths, out, a.ocr, a.bioassay, a.extra_rules, a.dpi, a.manifest, a.print_width_in, a.render_receipt_sha256)
        if not results:
            return cli_failure("no figures found (PNG files that are not *_plot_only.png)", 1)
        cnt = write_reports(results, out, a.paths or [a.manifest.parent])
    except (RenderPacketWriteConflict, RenderPacketAdmissionRefusal) as exc:
        return cli_failure(str(exc), 2)
    print(f"checked {len(results)}; errors {cnt['error']}, warnings {cnt['warn']}, "
          f"text not checked {cnt['not_checked']}, notes {cnt['info']} -> {out / 'RENDER_QC.md'}")
    if a.ocr == "require" and cnt["not_checked"]:
        return 2
    return 2 if cnt["error"] and not a.warn_only else 0


if __name__ == "__main__":
    sys.exit(main())

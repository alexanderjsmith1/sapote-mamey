"""Canonical paired figure writer and receipt inventory.

This post-seal utility writes governed PNG/SVG pairs and appends one portable,
hash-bound receipt row per render.  It does not select, interpret, publish, or
scientifically validate figures.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .figure_theme import CLAIM_SAFETY, add_claim_safety_footer, save_figure_pair


RECEIPT_SCHEMA = "sapote_mamey.figure_save_receipt.v1"
RECEIPT_NAME = "figure_receipts.jsonl"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class FigureSaveRefusal(RuntimeError):
    """Typed refusal when a paired figure cannot be written safely."""

    code = "FIGURE_SAVE_REFUSED"


@dataclass(frozen=True)
class NativeSvgFigure:
    """A deterministic SVG producer adapted to the canonical save contract."""

    svg: str


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _locator(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _append_receipt(root: Path, receipt: Mapping[str, object]) -> Path:
    target = root / RECEIPT_NAME
    if target.is_symlink():
        raise FigureSaveRefusal("FIGURE_SAVE_REFUSED: receipt path is a symlink")
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(receipt), sort_keys=True, separators=(",", ":")) + "\n")
    return target


def save_figure(
    fig: Any,
    *,
    figure_id: str,
    out_stem: str | Path,
    renderer: str,
    package_dir: str | Path,
    provenance: str,
    binding_state: str = "BOUND",
) -> dict[str, object]:
    """Write a PNG/SVG pair, add claim safety, and append a bound receipt row.

    Matplotlib figures use :func:`add_claim_safety_footer`. Native SVG producers
    use ``NativeSvgFigure`` and must already carry the same visible claim-safety
    text; CairoSVG creates the raster sibling from those exact SVG bytes.
    """
    root = Path(package_dir)
    stem = Path(out_stem)
    if not figure_id.strip() or not renderer.strip() or not provenance.strip():
        raise FigureSaveRefusal("FIGURE_SAVE_REFUSED: figure_id, renderer, and provenance are required")
    if not _inside(stem, root):
        raise FigureSaveRefusal("FIGURE_SAVE_REFUSED: out_stem must be contained by package_dir")
    root.mkdir(parents=True, exist_ok=True)
    stem.parent.mkdir(parents=True, exist_ok=True)

    png = stem.with_suffix(".png")
    svg = stem.with_suffix(".svg")
    if png.is_symlink() or svg.is_symlink():
        raise FigureSaveRefusal("FIGURE_SAVE_REFUSED: output path is a symlink")
    if isinstance(fig, NativeSvgFigure):
        if CLAIM_SAFETY not in fig.svg:
            raise FigureSaveRefusal("FIGURE_SAVE_REFUSED: native SVG lacks the claim-safety footer")
        svg_bytes = fig.svg.encode("utf-8")
        try:
            import cairosvg
        except (ImportError, OSError) as exc:
            raise FigureSaveRefusal(
                "FIGURE_RENDER_DEPENDENCY_MISSING: cairosvg is required for a PNG/SVG pair"
            ) from exc
        try:
            png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=2160)
        except (OSError, ValueError, RuntimeError) as exc:
            raise FigureSaveRefusal(
                f"FIGURE_RENDER_FAILED: cairosvg could not rasterize the SVG ({type(exc).__name__})"
            ) from exc
        if not isinstance(png_bytes, bytes) or not png_bytes.startswith(PNG_SIGNATURE):
            raise FigureSaveRefusal("FIGURE_RENDER_INVALID: SVG rasterizer did not return a PNG")
        svg.write_bytes(svg_bytes)
        png.write_bytes(png_bytes)
        authority = "Candidate Only"
    else:
        add_claim_safety_footer(
            fig, provenance=provenance, authority="Candidate Only — judgment deferred"
        )
        png, svg = save_figure_pair(fig, stem, profile="manuscript")
        authority = "Candidate Only — judgment deferred"

    outputs = {
        kind: {"logical_locator": _locator(path, root), "sha256": _sha(path), "bytes": path.stat().st_size}
        for kind, path in (("png", png), ("svg", svg))
    }
    receipt: dict[str, object] = {
        "schema_version": RECEIPT_SCHEMA,
        "status": "CANDIDATE_RENDERED",
        "figure_id": figure_id,
        "renderer": renderer,
        "provenance": provenance,
        "authority": authority,
        "claim_safety": CLAIM_SAFETY,
        "binding_state": binding_state,
        "outputs": outputs,
    }
    receipt_path = _append_receipt(root, receipt)
    return {**receipt, "receipt_locator": _locator(receipt_path, root)}


def audit_figure_outputs(package_dir: str | Path) -> dict[str, object]:
    """Inventory PNGs without mutating or regenerating legacy artwork."""
    root = Path(package_dir)
    receipt_path = root / RECEIPT_NAME
    receipt_rows: list[dict[str, object]] = []
    if receipt_path.is_file():
        for line_no, raw in enumerate(receipt_path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise FigureSaveRefusal(f"FIGURE_RECEIPT_INVALID: line {line_no}") from exc
            if not isinstance(row, dict):
                raise FigureSaveRefusal(f"FIGURE_RECEIPT_INVALID: line {line_no} is not an object")
            receipt_rows.append(row)

    bound_pngs: set[str] = set()
    for row in receipt_rows:
        outputs = row.get("outputs")
        if not isinstance(outputs, dict):
            continue
        records = {kind: outputs.get(kind) for kind in ("png", "svg")}
        if not all(isinstance(record, dict) for record in records.values()):
            continue
        valid = True
        resolved: dict[str, Path] = {}
        for kind, record in records.items():
            locator = record.get("logical_locator")
            pure = PurePosixPath(locator) if isinstance(locator, str) else None
            if pure is None or pure.is_absolute() or ".." in pure.parts:
                valid = False
                break
            path = root / pure
            if not _inside(path, root) or path.is_symlink() or not path.is_file():
                valid = False
                break
            if record.get("sha256") != _sha(path) or record.get("bytes") != path.stat().st_size:
                valid = False
                break
            resolved[kind] = path
        if valid and resolved["png"].with_suffix(".svg") == resolved["svg"]:
            bound_pngs.add(resolved["png"].relative_to(root).as_posix())
    figures = []
    for png in sorted(root.rglob("*.png")):
        locator = png.relative_to(root).as_posix()
        sibling = png.with_suffix(".svg")
        verified = sibling.is_file() and locator in bound_pngs
        figures.append({
            "png": locator,
            "svg": sibling.relative_to(root).as_posix() if sibling.is_file() else None,
            "state": "RECEIPT_BOUND_PAIR" if verified else "LEGACY_UNVERIFIED",
        })
    return {
        "schema_version": "sapote_mamey.figure_output_audit.v1",
        "status": "PASS" if all(row["state"] == "RECEIPT_BOUND_PAIR" for row in figures) else "PASS_WITH_LEGACY",
        "figures": figures,
    }

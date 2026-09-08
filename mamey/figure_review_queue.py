"""Build a portable, paginated owner-review surface for rendered figures.

This module does not render figures or decide whether they are scientifically
acceptable.  It validates an existing Figure Factory manifest, retains owner
decisions, and writes lightweight review pages that link to (rather than copy)
the source images, plotted data, and traveling caption/method files.
"""

from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import ctypes
import errno
import hashlib
import html
import json
import os
import platform
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "sapote.figure_review_queue/1"
ALLOWED_DECISIONS = ("UNREVIEWED", "KEEP", "REDESIGN", "DROP", "PARK")
QUEUE_FIELDS = (
    "figure_id",
    "title",
    "decision",
    "decision_note",
    "image",
    "caption_methods",
    "data",
    "image_sha256",
    "caption_sha256",
    "data_sha256",
)


class FigureReviewQueueError(ValueError):
    """Typed refusal raised before any review output is committed."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _locator(value: Any, *, field: str) -> PurePosixPath:
    text = str(value or "").strip()
    locator = PurePosixPath(text)
    if (
        not text
        or text.startswith(("/", "~"))
        or "\\" in text
        or locator.is_absolute()
        or any(part in ("", ".", "..") for part in locator.parts)
    ):
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_LOCATOR_INVALID",
            f"{field} must be a nonempty portable relative locator",
        )
    return locator


def _resolve_member(root: Path, value: Any, *, field: str) -> tuple[str, Path]:
    locator = _locator(value, field=field)
    resolved = (root / Path(*locator.parts)).resolve()
    if not _inside(resolved, root) or not resolved.is_file():
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_MEMBER_UNAVAILABLE",
            f"{field} does not resolve to a regular file inside the figure root",
        )
    return locator.as_posix(), resolved


def _verify_hash(path: Path, expected: Any, *, field: str) -> str:
    observed = _sha256(path)
    text = str(expected or "").strip().lower()
    if not text:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_HASH_REQUIRED", f"{field} requires an expected SHA-256 digest"
        )
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_HASH_INVALID", f"{field} is not a SHA-256 digest"
        )
    if text != observed:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_HASH_MISMATCH", f"{field} does not match its source file"
        )
    return observed


def _load_decisions(path: Path | None) -> dict[str, tuple[str, str]]:
    if path is None:
        return {}
    if not path.is_file():
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_DECISIONS_UNAVAILABLE", "decision register is unavailable"
        )
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not {"figure_id", "decision", "decision_note"}.issubset(
            reader.fieldnames
        ):
            raise FigureReviewQueueError(
                "FIGURE_REVIEW_DECISIONS_SCHEMA",
                "decision register requires figure_id, decision, and decision_note",
            )
        decisions: dict[str, tuple[str, str]] = {}
        for row in reader:
            figure_id = str(row.get("figure_id") or "").strip()
            if not figure_id:
                continue
            if figure_id in decisions:
                raise FigureReviewQueueError(
                    "FIGURE_REVIEW_DECISION_DUPLICATE", f"duplicate decision for {figure_id}"
                )
            decision = str(row.get("decision") or "UNREVIEWED").strip().upper()
            if decision not in ALLOWED_DECISIONS:
                raise FigureReviewQueueError(
                    "FIGURE_REVIEW_DECISION_INVALID", f"unsupported decision for {figure_id}"
                )
            decisions[figure_id] = (decision, str(row.get("decision_note") or "").strip())
    return decisions


def _manifest_rows(
    manifest_path: Path, figure_root: Path, decisions_path: Path | None
) -> tuple[list[dict[str, str]], str]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_MANIFEST_INVALID", "figure manifest is unreadable or invalid JSON"
        ) from exc
    figures = payload.get("figures") if isinstance(payload, dict) else None
    if not isinstance(figures, list) or not figures:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_MANIFEST_SCHEMA", "manifest must contain a nonempty figures list"
        )
    decisions = _load_decisions(decisions_path)
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in figures:
        if not isinstance(raw, dict):
            raise FigureReviewQueueError(
                "FIGURE_REVIEW_MANIFEST_SCHEMA", "every figure entry must be an object"
            )
        figure_id = str(raw.get("figure_set_id") or raw.get("figure_id") or "").strip()
        title = str(raw.get("title") or "").strip()
        if not figure_id or not title or figure_id in seen:
            raise FigureReviewQueueError(
                "FIGURE_REVIEW_IDENTITY_INVALID", "figure IDs and titles must be nonempty and unique"
            )
        seen.add(figure_id)
        image_value = raw.get("svg") or raw.get("png") or raw.get("image")
        image, image_path = _resolve_member(figure_root, image_value, field="image")
        if image_path.suffix.lower() not in {".svg", ".png", ".jpg", ".jpeg"}:
            raise FigureReviewQueueError(
                "FIGURE_REVIEW_IMAGE_TYPE", f"unsupported image type for {figure_id}"
            )
        caption, caption_path = _resolve_member(
            figure_root, raw.get("caption_methods"), field="caption_methods"
        )
        caption_text = caption_path.read_text(encoding="utf-8").strip()
        if not caption_text:
            raise FigureReviewQueueError(
                "FIGURE_REVIEW_CAPTION_EMPTY", f"caption/method file is empty for {figure_id}"
            )
        data_value = raw.get("data_csv") or raw.get("data")
        data = ""
        data_path: Path | None = None
        if data_value:
            data, data_path = _resolve_member(figure_root, data_value, field="data")
        decision, note = decisions.get(figure_id, ("UNREVIEWED", ""))
        rows.append(
            {
                "figure_id": figure_id,
                "title": title,
                "decision": decision,
                "decision_note": note,
                "image": image,
                "caption_methods": caption,
                "data": data,
                "image_sha256": _verify_hash(
                    image_path,
                    raw.get("svg_sha256") or raw.get("png_sha256") or raw.get("image_sha256"),
                    field="image_sha256",
                ),
                "caption_sha256": _verify_hash(
                    caption_path, raw.get("text_sha256") or raw.get("caption_sha256"),
                    field="caption_sha256",
                ),
                "data_sha256": (
                    _verify_hash(data_path, raw.get("data_sha256"), field="data_sha256")
                    if data_path is not None
                    else ""
                ),
                "caption_text": caption_text,
            }
        )
    unknown = sorted(set(decisions) - seen)
    if unknown:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_DECISION_ORPHAN",
            "decision register contains unknown figure IDs: " + ", ".join(unknown),
        )
    return rows, _sha256(manifest_path)


def _relative_from_output(outdir: Path, member: Path) -> str:
    return Path(os.path.relpath(member, outdir)).as_posix()


def _write_tsv(path: Path, rows: Iterable[Mapping[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=QUEUE_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in QUEUE_FIELDS})


def _publish_stage_noreplace(stage: Path, destination: Path) -> None:
    """Atomically publish one staged directory without replacing a competitor.

    A pre-publication existence check cannot close the race: POSIX ``rename`` may
    replace an empty directory created after that check.  Use the platform's
    atomic no-replace primitive, and fail closed when no such primitive is
    available.  The stage is created beside the destination, so descriptor-
    relative publication also avoids re-resolving a path hierarchy at commit.
    """

    if stage.parent != destination.parent:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_OUTPUT_COMMIT_UNAVAILABLE",
            "staged and final review directories must share one parent",
        )

    system = platform.system()
    if system == "Windows":
        try:
            os.rename(stage, destination)  # Windows refuses an existing destination.
        except FileExistsError as exc:
            raise FigureReviewQueueError(
                "FIGURE_REVIEW_OUTPUT_EXISTS",
                "refusing to replace an existing review directory",
            ) from exc
        except OSError as exc:
            raise FigureReviewQueueError(
                "FIGURE_REVIEW_OUTPUT_COMMIT_UNAVAILABLE",
                "atomic no-replace review-directory publication failed",
            ) from exc
        return

    if system not in {"Darwin", "Linux"}:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_OUTPUT_COMMIT_UNAVAILABLE",
            "atomic no-replace review-directory publication is unavailable",
        )

    try:
        libc = ctypes.CDLL(None, use_errno=True)
        function_name = "renameatx_np" if system == "Darwin" else "renameat2"
        rename_noreplace = getattr(libc, function_name)
        rename_noreplace.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        rename_noreplace.restype = ctypes.c_int
        parent_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        parent_fd = os.open(stage.parent, parent_flags)
    except (AttributeError, OSError) as exc:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_OUTPUT_COMMIT_UNAVAILABLE",
            "atomic no-replace review-directory publication is unavailable",
        ) from exc

    flag = 0x00000004 if system == "Darwin" else 0x00000001
    try:
        ctypes.set_errno(0)
        result = rename_noreplace(
            parent_fd,
            os.fsencode(stage.name),
            parent_fd,
            os.fsencode(destination.name),
            flag,
        )
        error_number = ctypes.get_errno() if result != 0 else 0
    finally:
        os.close(parent_fd)

    if result == 0:
        return
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_OUTPUT_EXISTS",
            "refusing to replace an existing review directory",
        )
    raise FigureReviewQueueError(
        "FIGURE_REVIEW_OUTPUT_COMMIT_UNAVAILABLE",
        "atomic no-replace review-directory publication failed",
    )


def _page_html(
    rows: Sequence[Mapping[str, str]], *, final_outdir: Path, figure_root: Path, page_number: int
) -> str:
    cards = []
    for row in rows:
        image = _relative_from_output(final_outdir / "pages", figure_root / row["image"])
        caption = _relative_from_output(final_outdir / "pages", figure_root / row["caption_methods"])
        data = (
            _relative_from_output(final_outdir / "pages", figure_root / row["data"])
            if row["data"]
            else ""
        )
        links = [f'<a href="{html.escape(caption)}">caption and methods</a>']
        if data:
            links.append(f'<a href="{html.escape(data)}">plotted data</a>')
        cards.append(
            '<article>'
            f'<h2>{html.escape(row["figure_id"])} — {html.escape(row["title"])}</h2>'
            f'<p class="decision"><strong>Decision:</strong> {html.escape(row["decision"])}'
            f' · {html.escape(row["decision_note"] or "No owner note recorded.")}</p>'
            f'<img src="{html.escape(image)}" alt="{html.escape(row["title"])}">'
            f'<p>{" · ".join(links)}</p>'
            f'<details open><summary>Traveling caption and methods</summary><pre>{html.escape(row["caption_text"])}</pre></details>'
            '</article>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Figure review page {page_number:03d}</title>'
        '<style>body{font:15px/1.5 system-ui;margin:0;background:#f3f5f7;color:#14283b}'
        'header,main{max-width:1450px;margin:auto;padding:20px}article{background:#fff;border:1px solid #ccd5dd;'
        'border-radius:8px;padding:16px;margin:0 0 22px}img{display:block;max-width:100%;height:auto;margin:12px auto}'
        '.decision{background:#f7f0dd;border-left:4px solid #b57b00;padding:8px 10px}'
        'pre{white-space:pre-wrap;font:14px/1.5 system-ui}a{color:#126b72}</style></head><body>'
        f'<header><h1>Figure review page {page_number:03d}</h1><p>Record KEEP, REDESIGN, DROP, or PARK in '
        'FIGURE_REVIEW_QUEUE.tsv. The review surface links to source artifacts and does not duplicate images.</p></header>'
        f'<main>{"".join(cards)}</main></body></html>\n'
    )


def build_review_queue(
    manifest: str | Path,
    figure_root: str | Path,
    outdir: str | Path,
    *,
    decisions: str | Path | None = None,
    page_size: int = 25,
) -> dict[str, Any]:
    """Validate a figure set and atomically write a paginated review queue."""

    root = Path(figure_root).resolve()
    manifest_path = Path(manifest).resolve()
    destination = Path(outdir).resolve()
    decisions_path = Path(decisions).resolve() if decisions is not None else None
    if not root.is_dir() or not _inside(manifest_path, root) or not manifest_path.is_file():
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_ROOT_INVALID", "manifest must be a file inside the figure root"
        )
    if decisions_path is not None and (
        not _inside(decisions_path, root) or not decisions_path.is_file()
    ):
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_DECISIONS_OUTSIDE_ROOT",
            "decision register must be a file inside the figure root",
        )
    if not _inside(destination, root) or destination == root:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_OUTPUT_OUTSIDE_ROOT", "output directory must be a new descendant of figure root"
        )
    if destination.exists():
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_OUTPUT_EXISTS", "refusing to replace an existing review directory"
        )
    if not destination.parent.is_dir():
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_OUTPUT_PARENT_UNAVAILABLE",
            "output directory parent must already exist inside the figure root",
        )
    if not isinstance(page_size, int) or page_size < 1 or page_size > 100:
        raise FigureReviewQueueError(
            "FIGURE_REVIEW_PAGE_SIZE", "page size must be an integer from 1 through 100"
        )
    rows, manifest_sha = _manifest_rows(manifest_path, root, decisions_path)

    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=destination.parent))
    try:
        pages = stage / "pages"
        pages.mkdir()
        _write_tsv(stage / "FIGURE_REVIEW_QUEUE.tsv", rows)
        page_files: list[str] = []
        for offset in range(0, len(rows), page_size):
            page_number = offset // page_size + 1
            filename = f"PAGE_{page_number:03d}.html"
            (pages / filename).write_text(
                _page_html(
                    rows[offset : offset + page_size],
                    final_outdir=destination,
                    figure_root=root,
                    page_number=page_number,
                ),
                encoding="utf-8",
            )
            page_files.append(f"pages/{filename}")
        overview_links = "".join(
            f'<li><a href="{html.escape(name)}">Review page {index:03d}</a></li>'
            for index, name in enumerate(page_files, 1)
        )
        (stage / "OPEN_FIGURE_REVIEW.html").write_text(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Figure review queue</title></head><body><h1>Figure review queue</h1>'
            f'<p>{len(rows)} figures; {len(page_files)} review pages; images are linked, not copied.</p>'
            f'<ol>{overview_links}</ol></body></html>\n',
            encoding="utf-8",
        )
        markdown = [
            "# Figure review queue",
            "",
            f"- Figures: {len(rows)}",
            f"- Review pages: {len(page_files)}",
            "- Images are linked from the source figure root and are not duplicated.",
            "- Record decisions in `FIGURE_REVIEW_QUEUE.tsv`.",
            "",
        ]
        for index, name in enumerate(page_files, 1):
            markdown.append(f"{index}. [Review page {index:03d}]({name})")
        (stage / "FIGURE_REVIEW_INDEX.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
        counts = {decision: 0 for decision in ALLOWED_DECISIONS}
        for row in rows:
            counts[row["decision"]] += 1
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "manifest_locator": manifest_path.relative_to(root).as_posix(),
            "manifest_sha256": manifest_sha,
            "decision_source": (
                {
                    "locator": decisions_path.relative_to(root).as_posix(),
                    "sha256": _sha256(decisions_path),
                }
                if decisions_path is not None
                else {"state": "NOT_SUPPLIED"}
            ),
            "figure_count": len(rows),
            "page_count": len(page_files),
            "page_size": page_size,
            "decision_counts": counts,
            "images_copied": 0,
            "outputs": [
                "OPEN_FIGURE_REVIEW.html",
                "FIGURE_REVIEW_INDEX.md",
                "FIGURE_REVIEW_QUEUE.tsv",
                *page_files,
            ],
        }
        (stage / "FIGURE_REVIEW_RECEIPT.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        _publish_stage_noreplace(stage, destination)
        return receipt
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise

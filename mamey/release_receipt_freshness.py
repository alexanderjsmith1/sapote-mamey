"""Detect a validation receipt that is older than the code it claims to validate.

The v9.7.416 unsealed candidate shipped ``validation/source_full_attempt02.log`` recording
``7 failed, 8951 passed`` — but the log was written at 17:18:58 and the archive's newest
source entry at 17:24:04.  The log described a tree roughly five minutes older than the one
packaged, and none of its seven failures reproduced against the shipped code.

That is the worst shape a receipt can take.  A red receipt that is merely stale looks
exactly like a red receipt that is true, so the archive cannot be sealed and cannot be
cleared without re-running the whole suite.  The cost is a full suite run (19m12s by that
candidate's own log) to learn nothing new.

The check is one comparison: no receipt may predate the newest artifact it covers.  This
module answers it for a directory pair or for a candidate archive, without unpacking.

Reports only; it raises for unusable input, never for a stale receipt.  The decision to
refuse a build belongs to the packager.  No biological claim; judgment deferred.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

__all__ = ["CURRENT", "STALE", "NO_RECEIPTS", "audit_tree", "audit_archive"]

CURRENT = "CURRENT"
STALE = "STALE"
NO_RECEIPTS = "NO_RECEIPTS"

#: Path segments whose files are receipts rather than shipped source.
RECEIPT_MARKERS = ("validation/", "receipts/")
#: Receipt suffixes worth checking; a receipt is evidence, so it is text.
RECEIPT_SUFFIXES = (".log", ".json", ".xml", ".txt")


def _is_receipt(name: str) -> bool:
    norm = name.replace("\\", "/")
    return (any(m in norm for m in RECEIPT_MARKERS)
            and norm.endswith(RECEIPT_SUFFIXES))


def _verdict(receipts: list[tuple[str, object]], newest_source: tuple[str, object] | None) -> dict:
    if not receipts:
        return {"state": NO_RECEIPTS, "stale": [], "newest_source": None, "receipts": []}
    if newest_source is None:
        return {"state": NO_RECEIPTS, "stale": [], "newest_source": None,
                "receipts": [n for n, _ in receipts]}
    src_name, src_when = newest_source
    stale = [{"receipt": n, "receipt_time": str(w), "newest_source": src_name,
              "newest_source_time": str(src_when)}
             for n, w in receipts if w < src_when]
    return {
        "state": STALE if stale else CURRENT,
        "stale": stale,
        "newest_source": {"path": src_name, "time": str(src_when)},
        "receipts": [n for n, _ in receipts],
    }


def audit_tree(root: Path | str) -> dict:
    """Audit an extracted tree, comparing receipt mtimes to the newest source mtime."""
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")
    receipts: list[tuple[str, object]] = []
    newest: tuple[str, object] | None = None
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        when = p.stat().st_mtime
        if _is_receipt(rel):
            receipts.append((rel, when))
        elif newest is None or when > newest[1]:
            newest = (rel, when)
    return _verdict(receipts, newest)


def audit_archive(path: Path | str) -> dict:
    """Audit a candidate archive in place, using zip entry timestamps.

    Zip entries carry a local timestamp with two-second granularity, which is far finer
    than the gap this is meant to catch.
    """
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        receipts: list[tuple[str, object]] = []
        newest: tuple[str, object] | None = None
        for info in zf.infolist():
            if info.is_dir():
                continue
            when = info.date_time
            if _is_receipt(info.filename):
                receipts.append((info.filename, when))
            elif newest is None or when > newest[1]:
                newest = (info.filename, when)
    return _verdict(receipts, newest)

"""Canonicalize XLSX container metadata after an atomic openpyxl save.

Spreadsheet cell content and workbook structure remain unchanged. The helper
removes wall-clock variation from OOXML core properties and ZIP member headers
so equal workbooks serialize to equal bytes on the same engine/runtime.
"""
from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path


FIXED_ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)
FIXED_W3CDTF = "1980-01-01T00:00:00Z"
_CORE_TIME = re.compile(
    rb"(<dcterms:(?:created|modified)\b[^>]*>).*?(</dcterms:(?:created|modified)>)"
)


def _canonical_member(name: str, data: bytes) -> bytes:
    if name == "docProps/core.xml":
        return _CORE_TIME.sub(lambda match: match.group(1) + FIXED_W3CDTF.encode() + match.group(2), data)
    return data


def canonicalize_xlsx(path: str | Path) -> Path:
    """Rewrite one XLSX with stable core times, member order, and ZIP metadata."""
    target = Path(path)
    if target.is_symlink():
        raise ValueError(f"refusing symlink workbook destination: {target}")
    if not target.is_file():
        raise ValueError(f"workbook destination must be an existing regular file: {target}")
    prior_mode = target.stat().st_mode & 0o7777
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.canonical.", suffix=".tmp", dir=target.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(target, "r") as source:
            members = [(info.filename, _canonical_member(info.filename, source.read(info.filename)), info.compress_type)
                       for info in source.infolist()]
        with zipfile.ZipFile(temporary, "w") as output:
            for name, data, compress_type in sorted(members):
                info = zipfile.ZipInfo(name, FIXED_ZIP_DATETIME)
                info.compress_type = compress_type
                info.create_system = 0
                info.external_attr = 0o600 << 16
                output.writestr(info, data)
        os.chmod(temporary, prior_mode)
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return target


# v9.7.409 (BC hostile audit H8): openpyxl stores any string that starts with "=" as a FORMULA
# (data_type "f"). antiSMASH annotation text is attacker-controlled input — a GBK `/product="=HYPERLINK(...)"`
# reached 21 live-formula cells across the package workbook and the master workbook, executable on
# open in Excel. Every workbook goes through this seam before it is saved; nothing about the cell's
# TEXT changes, only its type, so downstream readers see the same string.
_FORMULA_LEADERS = ("=", "+", "-", "@", "\t", "\r")


def neutralise_formula_strings(wb) -> int:
    """Force every string cell that Excel would treat as a formula to plain text. Returns the count."""
    n = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, str) and cell.data_type == "f":
                    # openpyxl types only "="-leading strings as formulas; "+ - @"-leading strings are
                    # already stored as text (t="s") in XLSX and are inert there. CSV consumers are a
                    # separate surface and are documented as machine-readable, not Excel-safe.
                    cell.data_type = "s"
                    n += 1
    return n


def save_workbook_safely(wb, path) -> int:
    """`wb.save(path)` with formula-string neutralisation first. The one save seam for all writers."""
    n = neutralise_formula_strings(wb)
    wb.save(path)
    return n


def atomic_save_workbook_safely(wb, path: str | Path, *, canonicalize: bool = False) -> int:
    """Publish a complete workbook through a unique sibling stage and ``os.replace``.

    This is the workbook analogue of the package atomic writers.  It prevents
    fixed-stage collisions and removes the private stage on any pre-publication
    failure; it does not serialize concurrent read-modify-write transactions.
    """
    target = Path(path)
    if target.is_symlink():
        raise ValueError(f"refusing symlink workbook destination: {target}")
    if target.exists() and not target.is_file():
        raise ValueError(f"workbook destination must be a regular file: {target}")
    prior_mode = target.stat().st_mode & 0o7777 if target.exists() else None
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        n = save_workbook_safely(wb, temporary)
        if canonicalize:
            canonicalize_xlsx(temporary)
        if prior_mode is not None:
            os.chmod(temporary, prior_mode)
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return n

import os as _os


# --------------------------------------------------------------------------- inflation guard
# v9.7.410 hostile audit (H40). Lives here rather than in a new module because this file is
# the workbook I/O seam (the accretion gate needs a CHANGELOG justification for any new
# mamey/ module, and that is a cut-time step).
#
# v9.7.410 hostile audit: `openpyxl.load_workbook` materialises the whole sheet XML and the shared-
# strings table in RAM. A 113 KB .xlsx built from one 60 KB string repeated 1,000 times cost 51 MB
# of RSS on load (450x); a crafted 10 MB file is a multi-gigabyte load. The master workbook and
# cohort workbooks are operator-supplied paths, so the readers that take them preflight the
# archive's *declared* uncompressed size (the same idea as the GBK zip guard in mamey/parsers.py)
# and refuse with a typed error instead of thrashing. The cap is generous for real workbooks
# (the largest shipped master is a few MB inflated) and env-overridable.
import zipfile as _zipfile


DEFAULT_MAX_INFLATED_BYTES = 512 * 1024 * 1024  # 512 MiB of sheet/shared-string XML
_ENV = "MAMEY_XLSX_MAX_INFLATED_BYTES"


class WorkbookTooLargeError(ValueError):
    code = "XLSX_INFLATION_GUARD_REFUSED"


def max_inflated_bytes() -> int:
    try:
        return max(1, int(_os.environ.get(_ENV, str(DEFAULT_MAX_INFLATED_BYTES))))
    except ValueError:
        return DEFAULT_MAX_INFLATED_BYTES


def guard_workbook_size(path: str | Path) -> int:
    """Return the declared inflated size of the .xlsx at ``path``; raise WorkbookTooLargeError
    when it exceeds the cap. A non-zip / unreadable file is left for openpyxl to report."""
    cap = max_inflated_bytes()
    try:
        with _zipfile.ZipFile(path) as zf:
            total = sum(info.file_size for info in zf.infolist())
    except (OSError, _zipfile.BadZipFile):
        return 0
    if total > cap:
        raise WorkbookTooLargeError(
            f"{WorkbookTooLargeError.code}: {Path(path).name} declares {total:,} bytes of inflated "
            f"content, over the {cap:,}-byte cap ({_ENV}); refusing to load it into memory")
    return total

"""v9.7.395: preflight_zip_hygiene's coarse large-file allow must bind to the
BASENAME, not the full path.

Regression cover for the .394 hole: `LARGE_FILE_ALLOW` was applied as `any(tok in name)` over the
FULL zip entry path. Any oversized entry whose path merely *contained* a token anywhere — a
directory segment named `figures.pdf_exports/`, a mid-name match like `report.pdf.zip`, or a
`registry_inventory_notes/` folder holding an arbitrary binary — was silently exempted from the
size gate with no ceiling and no reason, and the tool printed `OK: ... is clean`. That inverts the
gate's own contract ("no files > 5 MB unless explicitly allowlisted") and contradicts the code's
own comment ("checked by basename suffix/substring").

The fix (`_coarse_large_allow`) checks extension tokens as basename SUFFIXES and name tokens as
basename substrings. The negative cases matter more than the positive ones: a guard that cannot
fail is worthless.
"""
from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load():
    spec = importlib.util.spec_from_file_location(
        "preflight_zip_hygiene", TOOLS / "preflight_zip_hygiene.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _zip_with(tmp_path: Path, entries: dict) -> Path:
    zp = tmp_path / "t.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
        for arc, content in entries.items():
            z.writestr(arc, content)
    return zp


def _big(m):
    return b"x" * (m.LARGE_LIMIT + 1024 * 1024)  # 6 MB, over the 5 MB gate


def test_token_in_directory_segment_does_not_exempt(tmp_path):
    """A dot-token appearing only in a DIRECTORY name must not exempt the file inside it."""
    m = _load()
    zp = _zip_with(tmp_path, {"figures.pdf_exports/raw_dump.bin": _big(m)})
    large = m.scan(zp)["large"]
    assert len(large) == 1 and "raw_dump.bin" in large[0], large


def test_midname_token_does_not_exempt(tmp_path):
    """`report.pdf.zip` is a zip, not a pdf — a mid-basename token must not exempt it."""
    m = _load()
    zp = _zip_with(tmp_path, {"report.pdf.zip": _big(m)})
    large = m.scan(zp)["large"]
    assert len(large) == 1 and "report.pdf.zip" in large[0], large


def test_registry_inventory_directory_does_not_exempt_contents(tmp_path):
    """'registry_inventory' in a directory name must not exempt an arbitrary binary inside."""
    m = _load()
    zp = _zip_with(tmp_path, {"docs/registry_inventory_notes/raw_dump.bin": _big(m)})
    large = m.scan(zp)["large"]
    assert len(large) == 1 and "raw_dump.bin" in large[0], large


def test_genuine_matches_still_pass(tmp_path):
    """Back-compat: the legitimately-large families the tuple exists for still pass."""
    m = _load()
    zp = _zip_with(tmp_path, {
        "bundle_support/registry_inventory_v1.9.4.csv": _big(m),
        "Wheelhouse/some_pkg-1.0-py3-none-any.whl": _big(m),
        "runs/AS-1/AS-1_5_workbook.xlsx": _big(m),
        "docs/big_figure.pdf": _big(m),
    })
    assert m.scan(zp)["large"] == []


def test_unrelated_oversized_file_still_fails(tmp_path):
    """Control: the gate keeps its teeth on a plain oversized binary."""
    m = _load()
    zp = _zip_with(tmp_path, {"mamey/data/control_huge.bin": _big(m)})
    large = m.scan(zp)["large"]
    assert len(large) == 1 and "control_huge.bin" in large[0], large

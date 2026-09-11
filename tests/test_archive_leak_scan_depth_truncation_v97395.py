"""Regression: archive_leak_scan.py must not silently report a scan as clean when a nested
archive was skipped because it exceeded --max-depth.

Fails against the pristine .394 file: a real private-ID leak ("AS-705") buried inside a nested
zip beyond the depth cap produced ZERO findings of any kind -- not even a note -- so a genuine
leak this tool exists specifically to catch (per its own module docstring: closing coverage
holes other leak-audit tools miss) could pass as CLEAN.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import archive_leak_scan as als  # noqa: E402


def _make_zip(entries: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_depth_limit_truncation_is_visible_not_silent():
    inner_leak = _make_zip({"notes.txt": "AS-705 is a real strain identifier here."})
    outer = _make_zip({"nested.zip": inner_leak})

    findings = als._scan_zip_bytes(outer, "outer.zip", as_only=True, denylist=[],
                                    depth=0, max_depth=0)
    assert findings, (
        "a nested archive beyond --max-depth produced zero findings -- the truncation is "
        "completely silent, so a real leak inside it would report as a clean scan"
    )
    kinds = {f["kind"] for f in findings}
    assert "depth_limit_truncated" in kinds


def test_depth_limit_truncation_note_does_not_flip_exit_code_to_leak():
    # A truncation note must land in the "errs"/note bucket, never in the real-leak bucket --
    # it's a coverage gap, not a confirmed leak, and must not produce a false-positive LEAK exit.
    inner_leak = _make_zip({"notes.txt": "AS-705 is a real strain identifier here."})
    outer = _make_zip({"nested.zip": inner_leak})
    findings = als._scan_zip_bytes(outer, "outer.zip", as_only=True, denylist=[],
                                    depth=0, max_depth=0)
    real = [f for f in findings if f["kind"] in ("private_identifier", "held_phrase", "denylist_term")]
    assert not real, "a depth-limit truncation must not be misreported as a confirmed leak finding"


def test_sufficient_depth_still_finds_the_real_leak():
    inner_leak = _make_zip({"notes.txt": "AS-705 is a real strain identifier here."})
    outer = _make_zip({"nested.zip": inner_leak})
    findings = als._scan_zip_bytes(outer, "outer.zip", as_only=True, denylist=[],
                                    depth=0, max_depth=1)
    real = [f for f in findings if f["kind"] == "private_identifier"]
    assert real and real[0]["token"] == "AS-705"

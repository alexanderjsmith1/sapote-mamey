"""v9.7.401: tools/ + deliverable_tools/ Python must carry zero UNACCOUNTED cohort strain IDs.

Sibling of test_mamey_source_cohort_id_guard_v97401 for the tool layer, with the two legitimate
exception classes made explicit rather than silent:
  * DETECTOR files that must contain the patterns they hunt (same concept as
    public_release_audit._ALLOW);
  * the synthetic sentinel family ``AS-000_CONSDARK`` unioned into SSOT exclusion sets
    (a constructed token, not a strain; the SSOT regex clips the ``AS-000`` prefix).
Leak discipline: no real cohort identifiers in this file; sensitivity uses a runtime-built token.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from redact_public_tier import private_id_matches  # release-redaction SSOT

#: files that legitimately contain cohort-ID-shaped text: the redaction/disclosure machinery's own
#: docs and normalisation examples. Mirrors the public_release_audit._ALLOW concept for this layer.
DETECTOR_FILES = {"redact_public_tier.py", "strict_source_disclosure_audit.py",
                  "public_release_audit.py", "archive_leak_scan.py", "audit_public_cut.py"}


def _scan(root: Path) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for py in sorted(root.rglob("*.py")):
        if py.name in DETECTOR_FILES:
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            hits[str(py)] = ["<UNREADABLE>"]
            continue
        found = [t for t in sorted(set(private_id_matches(text, as_only=True)))
                 if f"{t}_CONSDARK" not in text]          # sentinel family, not a strain
        if found:
            hits[str(py.relative_to(root.parent))] = found
    return hits


def test_tool_layer_is_cohort_id_free():
    hits = {}
    for sub in ("tools", "deliverable_tools"):
        hits.update(_scan(ROOT / sub))
    assert not hits, "unaccounted cohort identifiers in tool-layer source: %r" % hits


def test_guard_detects_injected_token(tmp_path):
    d = tmp_path / "tools"; d.mkdir()
    token = "AS-" + str(8000 + 217)
    (d / "x.py").write_text(f'Y = "{token}"\n', encoding="utf-8")
    hits = _scan(d)
    assert hits and token in next(iter(hits.values()))


def test_sentinel_and_detector_exemptions(tmp_path):
    d = tmp_path / "tools"; d.mkdir()
    (d / "a.py").write_text('E = _excluded() | {"AS-000_CONSDARK"}\n', encoding="utf-8")
    (d / "redact_public_tier.py").write_text('DOC = "AS-" + "1234"\n', encoding="utf-8")
    assert _scan(d) == {}

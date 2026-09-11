"""v9.7.401: engine Python source must carry ZERO real cohort strain IDs (SSOT-checked).

`tools/public_release_audit.py` deliberately exempts executable Python from its content census
(documented: genericizing .py is a source-patch problem, not a release-time rewrite), and skips
`tests/` entirely. That leaves a latent boundary: a cohort `AS-####`/`AJS-*`/`PENDING-*` literal
hardcoded into `mamey/**/*.py` would pass EVERY release gate. Measured 0 occurrences at v9.7.397
and again when this guard landed — this test pins that at 0 forever, using the same redaction SSOT
(`redact_public_tier.private_id_matches`) as the release machinery, so the carve-outs
(enterocin AS-48 etc.) and detector stay single-sourced.

Leak discipline: this file contains no real cohort identifiers; the sensitivity self-test
constructs a synthetic token at runtime.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from redact_public_tier import private_id_matches  # the release-redaction SSOT


def _scan_tree(root: Path) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for py in sorted(root.rglob("*.py")):
        if "_vendor" in py.parts:      # vendored third-party code is not engine-authored surface
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            hits[str(py)] = ["<UNREADABLE — a guard cannot skip what it cannot read>"]
            continue
        found = sorted(set(private_id_matches(text, as_only=True)))
        if found:
            hits[str(py.relative_to(root.parent))] = found
    return hits


def test_engine_python_source_is_cohort_id_free():
    hits = _scan_tree(ROOT / "mamey")
    assert not hits, (
        "real cohort identifiers in engine Python source (invisible to public_release_audit's "
        "deliberate .py exemption — fix at source, never ship): %r" % hits
    )


def test_guard_detects_an_injected_token(tmp_path):
    """Sensitivity proof (fail-before equivalent): a runtime-constructed cohort-shaped token in a
    synthetic module MUST be caught — proves the SSOT wiring, not just a green run."""
    mod = tmp_path / "mamey" / "synthetic.py"
    mod.parent.mkdir(parents=True)
    token = "AS-" + str(9000 + 317)          # constructed, never a literal real ID
    mod.write_text(f'X = "{token}"\n', encoding="utf-8")
    hits = _scan_tree(tmp_path / "mamey")
    assert hits and token in next(iter(hits.values())), "guard failed to detect an injected token"


def test_public_carveouts_do_not_false_positive(tmp_path):
    """Enterocin AS-48 (KNOWN_PUBLIC_AS natural-product carve-out) must not trip the guard —
    single-sourcing through the SSOT is the point of this design."""
    mod = tmp_path / "mamey" / "synthetic.py"
    mod.parent.mkdir(parents=True)
    mod.write_text('DOC = "enterocin AS-48 reference"\n', encoding="utf-8")
    assert _scan_tree(tmp_path / "mamey") == {}

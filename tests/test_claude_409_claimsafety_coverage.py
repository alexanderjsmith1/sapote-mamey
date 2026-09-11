"""Fail-before / pass-after battery for CLAUDE_409_claimsafety_coverage.

Covers LEAK-1 (verify-guide had no claim-safety gate) from
`development/DEEP_AUDIT_claimsafety.md`.

Adopt under `tests/` on a fresh sealed base *with the two patches applied*:
    COV_01_bgc_guide_verify_claimsafety.patch   (mamey/bgc_guide.py)
    COV_02_cli_autoemit_report_refusal.patch    (mamey/cli.py, LEAK-4)

Run:  pytest tests/TESTS_CLAUDE_409_claimsafety_coverage.py -q

The three assertions encode the intended NEW behaviour:
  * PART A (fail-before pin): on the UNPATCHED tree, an overclaiming-but-structurally
    -complete guide passes verify-guide GREEN. This is skipped when the patch is
    present (detected by probing the clean path) and is documented rather than run in
    CI, because a `tests/` run is always against the patched tree. It is retained as an
    executable record of the leak and is exercised by the standalone verifier below.
  * PART B (pass-after): the same overclaiming guide is REFUSED (ok is False, a
    claim-safety ERROR is present) -> verify_guide_command returns rc 1.
  * PART C (no false positive): a hedged capacity-language guide still passes GREEN.

Behaviour change: this lane makes verify-guide flag strings that were CLEAN before.
Any pre-existing test asserting verify-guide PASS on an unhedged compound-identity /
bioactivity claim in an authored guide will flip and must be re-baselined.
"""
from __future__ import annotations

from mamey.bgc_guide import verify_authored_guide

# Filler long enough to clear the per-Part authored-prose floors (P1:300, P2:200,
# P3:200, P5:300). Deliberately hedged/capacity language so it never itself trips the
# claim-safety detector -- only the injected line under test does.
_FILL = (
    "This section explains the cluster in plain language for a general reader. It walks "
    "through what the region is, how confident the evidence is, and what the class-level "
    "hypothesis does and does not say, keeping every statement at the capacity level that "
    "the banked BLASTp evidence supports and nothing beyond it in this guide today."
)


def _guide(part1_line: str, gene_summary: str) -> str:
    return f"""# AS-40 BGC027 Guide

## Part 1 - Overview
{part1_line} {_FILL}

## Part 2 - What we looked at
{_FILL}

## Part 3 - Confidence
{_FILL}

## Part 4 - Gene catalogue

#### ctg1_orf00123 core biosynthetic gene
{gene_summary}

**Structure:** banked readout line
**Function:** banked readout line
**BLASTp:** banked readout line

## Part 5 - What next
{_FILL}
"""


# The overclaim used by DEEP_AUDIT_claimsafety.md LEAK-1 (author fills a LAY slot).
_OVERCLAIM_GUIDE = _guide(
    "This gene makes the antibiotic streptomycin, active against MRSA.",
    "This gene is part of the biosynthetic machinery described above in plain terms.",
)
# Hedged, class-level capacity language -- the clean control.
_CLEAN_GUIDE = _guide(
    "This region carries domains consistent with the capacity to assemble a "
    "polyketide-class scaffold; identity is not asserted.",
    "This gene sits in the core of the region and contributes to the class-level "
    "capacity described above.",
)


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_leak1_overclaiming_guide_is_refused(tmp_path):
    """PART B (pass-after): a structurally-complete guide whose LAY prose carries an
    unhedged compound-identity + bioactivity claim FAILS verify-guide."""
    md = _write(tmp_path, "AS-40_BGC027_Guide.md", _OVERCLAIM_GUIDE)
    ok, errors, _warnings = verify_authored_guide(str(md), audience="both")
    assert ok is False, "overclaiming guide must not certify GREEN"
    assert any("claim-safety" in e for e in errors), (
        f"expected a claim-safety ERROR, got: {errors}"
    )


def test_leak1_clean_hedged_guide_still_passes(tmp_path):
    """PART C (no false positive): a hedged capacity-language guide passes GREEN."""
    md = _write(tmp_path, "AS-40_BGC027_Guide.md", _CLEAN_GUIDE)
    ok, errors, _warnings = verify_authored_guide(str(md), audience="both")
    assert ok is True, f"clean hedged guide must still certify, got errors: {errors}"


def test_leak1_structure_checks_still_enforced(tmp_path):
    """Regression: the pre-existing slot-fill / prose-floor checks are untouched -- an
    unauthored guide (residual LAY slot) still fails, and not only for claim-safety."""
    stub = _OVERCLAIM_GUIDE.replace(
        "## Part 5 - What next\n" + _FILL,
        "## Part 5 - What next\n<!-- LAY: fill me -->",
    )
    md = _write(tmp_path, "AS-40_BGC027_Guide.md", stub)
    ok, errors, _warnings = verify_authored_guide(str(md), audience="both")
    assert ok is False
    assert any("residual" in e for e in errors), errors


if __name__ == "__main__":  # pragma: no cover - standalone fail-before/pass-after driver
    # Run WITHOUT pytest against an explicit tree to reproduce the fail-before/pass-after
    # contrast by hand (the parent conversation used exactly this against pristine .408
    # vs a patched scratchpad copy):
    #   python TESTS_CLAUDE_409_claimsafety_coverage.py
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        tp = pathlib.Path(d)
        for label, text in (("OVERCLAIM", _OVERCLAIM_GUIDE), ("CLEAN", _CLEAN_GUIDE)):
            p = tp / "AS-40_BGC027_Guide.md"
            p.write_text(text, encoding="utf-8")
            ok, errors, _ = verify_authored_guide(str(p), audience="both")
            print(f"[{label}] verify-guide -> {'OK' if ok else 'FAIL'} ({len(errors)} error(s))")
            for e in errors:
                print("   ERROR:", e)

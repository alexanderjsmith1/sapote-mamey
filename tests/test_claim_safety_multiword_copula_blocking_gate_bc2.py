"""BC2 (v9.7.395): lint_claim_safety() — the function wired into the BLOCKING seal gate
(mamey/seal_package.py::_gate_claim_safety) and judgment_store.py's write-time self-lint — must
flag a multi-word compound-identity overclaim after a copula the same way the report-only
lint_claim_safety_report() already does.

lint_claim_safety_report()'s _identity_hit() builds a probe from the captured single-word token
plus a short trailing window and tests substring membership against the compound-name set (Finding
2 / CS-01, v9.7.336), so a multi-word compound name like "phosphonoacetic acid" is caught even
though the identity-verb regex only captures the leading token "phosphonoacetic". lint_claim_
safety()'s _flag() never got that fix — it only tested `t in cnames` (bare single-word token) —
so a real multi-word compound-identity overclaim reached the blocking seal gate as zero findings
while the report-only path caught the same sentence. Reproduced live against the unpatched
tools/claim_safety_linter.py before this fix.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

from claim_safety_linter import lint_claim_safety, lint_claim_safety_report


def test_multiword_copula_overclaim_flagged_by_blocking_gate():
    text = "BGC001 is phosphonoacetic acid, based on strong KCB similarity."
    cnames = {"phosphonoacetic acid"}

    report_findings = lint_claim_safety_report(text, compound_names=cnames)
    assert any(r["violation_type"] == "identity_overclaim" for r in report_findings), (
        "sanity check: the report-only path is expected to already catch this"
    )

    blocking_findings = lint_claim_safety(text, compound_names=cnames)
    assert any(f.startswith("possible identity overclaim") for f in blocking_findings), (
        "the BLOCKING seal-gate function must catch the same multi-word compound-identity "
        f"overclaim as the report-only path; got: {blocking_findings}"
    )


def test_hallucinated_name_still_caught_regression_cs01():
    # CS-01 (v9.7.336) regression guard: a name NOT on the board must still be caught via the
    # shape heuristic for production verbs.
    text = "BGC001 synthesizes zorbamycin."
    findings = lint_claim_safety(text, compound_names={"realcompound"})
    assert any("zorbamycin" in f for f in findings)


def test_descriptive_copula_still_clean():
    # Regression guard: descriptive prose after a copula must remain clean.
    text = "This region is edge-truncated and short."
    findings = lint_claim_safety(text, compound_names={"realcompound"})
    assert findings == []

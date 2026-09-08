"""BC2-CSD-01 (v9.7.396): cross_strain_denominator_audit.py must not leave a badly-stale
cohort-size denominator completely invisible just because it falls outside the +/-12
detection window.

audit_denominators()'s +/-12 window around the registry length exists to avoid false-flagging a
genuinely smaller, unrelated per-category ratio as a stale cohort count — a reasonable
anti-false-positive design, left UNCHANGED by this fix (confirmed by the full existing
test_cross_strain_denominator_audit_v9_7_116.py suite still passing). But a denominator far from
the current registry length — e.g. a cross-strain sheet frozen at a much smaller cohort snapshot
from an earlier synthesis pass, exactly the "wrong number that looks computed" failure this
tool's own docstring says it exists to catch, just a bigger drift than its motivating 18-vs-24
incident — fell outside the window and was silently invisible: not in the allowed set, not in
[lo, hi], never mentioned anywhere in the tool's output.

This adds a new, separate, non-blocking `ambiguous_denominators()` function (main() prints its
output as a NOTE, not a failure) that surfaces exactly these previously-invisible tokens for
human review, without changing audit_denominators()'s return contract, blocking behavior, or exit
code in any way.

Reproduced live against the unpatched tools/cross_strain_denominator_audit.py before this fix.
"""
import os
import sys
import tempfile
import pathlib

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from cross_strain_denominator_audit import (  # noqa: E402
    audit_denominators,
    ambiguous_denominators,
    denominator_audit_result,
    main,
)


def _make_master(path, findings_rows, n_strains=44, n_bgc=100):
    wb = openpyxl.Workbook()
    reg = wb.active
    reg.title = "A2_Strain_Registry"
    reg.append(["strain", "taxonomy"])
    for i in range(n_strains):
        reg.append([f"AS-{900 + i}", "sp."])
    b1 = wb.create_sheet("B1_BGC_Master")
    b1.append(["bgc_uid"])
    for i in range(n_bgc):
        b1.append([f"AS-900:BGC{i}"])
    f = wb.create_sheet("Cross_Strain_Findings")
    f.append(["#", "finding", "value"])
    for r in findings_rows:
        f.append(r)
    wb.save(path)


def test_badly_stale_denominator_is_surfaced_not_silently_invisible():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "badly_stale.xlsx")
    # v9.7.405 reconciliation: BC-2's .401 fix widened the blocking window's LOWER bound to 2,
    # so a small stale denominator (5/10 in a 44-strain registry) is now a BLOCKING violation —
    # the fail-closed behaviour wins over CODEX_396 repair 13's assumption of lo=32. The
    # review-note path therefore exercises a denominator ABOVE the window (hi = n_reg + 12 = 56):
    # 5/70 is not a plausible stale cohort count, is not blocked, and must still be surfaced.
    _make_master(p, [[3, "ectoine", "5/70 strains"]], n_strains=44)

    # audit_denominators()'s own blocking contract is UNCHANGED: this case is still not a
    # confident violation (real ambiguity — could be an unrelated ratio).
    assert audit_denominators(p) == []

    notes = ambiguous_denominators(p)
    assert notes, "a denominator far outside the window must be surfaced as a review note"
    assert any("M=70" in n and "44" in n for n in notes)

    result = denominator_audit_result(p)
    assert result["status"] == "PASS_WITH_REVIEW_NOTES"
    assert result["blocking_violation_count"] == 0
    assert result["review_note_count"] == 1


def test_review_notes_do_not_emit_a_false_all_clear(capsys):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "review_notes.xlsx")
    _make_master(p, [[3, "ectoine", "5/70 strains"]], n_strains=44)   # above the window (see above)

    assert main([p]) == 0
    captured = capsys.readouterr()
    assert "PASS_WITH_REVIEW_NOTES" in captured.out
    assert "no blocking denominator violations" in captured.out
    assert "every cohort denominator matches" not in captured.out
    assert "review manually" in captured.err


def test_within_window_case_is_not_duplicated_into_ambiguous_notes():
    # Regression guard: a denominator audit_denominators() already catches (within the window)
    # must not ALSO appear in ambiguous_denominators() — the two functions must not overlap.
    d = tempfile.mkdtemp()
    p = os.path.join(d, "within_window.xlsx")
    _make_master(p, [[3, "universal", "38/38"]], n_strains=44)  # 38 is within [32, 56]
    violations = audit_denominators(p)
    assert violations and len(violations) == 1
    notes = ambiguous_denominators(p)
    assert notes == []


def test_clean_master_has_no_ambiguous_notes():
    # Regression guard: a genuinely clean master (matching denominators, one legitimate BGC-total
    # ratio) produces no ambiguous notes either.
    d = tempfile.mkdtemp()
    p = os.path.join(d, "clean.xlsx")
    _make_master(p, [[3, "universal", "44/44"], [7, "dark", "15/100 (15%)"]],
                 n_strains=44, n_bgc=100)
    assert audit_denominators(p) == []
    assert ambiguous_denominators(p) == []
    result = denominator_audit_result(p)
    assert result["status"] == "PASS"
    assert result["blocking_violation_count"] == 0
    assert result["review_note_count"] == 0

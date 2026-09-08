"""Bug #3: check_deliverable_suite gold Section-H must FAIL CLOSED.

Before the fix, the gold-only Section-H checks (`gold_completeness`, `Mode B cards written`)
only fired if their lines happened to exist (`if m and ...` / `if mb and ...`). A gold manifest
that omitted them passed with zero completeness evidence — a fail-OPEN gate.
"""
import importlib.util, pathlib

_root = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_deliverable_suite", _root / "tools" / "check_deliverable_suite.py")
cds = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(cds)


def _manifest(section_h="gold_completeness: COMPLETE\nMode B cards written: 12/12\n"):
    rows = "\n".join(f"| {i} | item{i} | COMPLETE | /path/art{i} |" for i in range(1, 14))
    return ("# M\n\n| # | Deliverable | Status | Artifact |\n|---|---|---|---|\n"
            + rows + "\n\n" + section_h)


def test_gold_missing_section_h_fails_closed():
    findings, _ = cds.check(_manifest(section_h="(no Section H lines)\n"), "gold")
    assert any("gold_completeness line MISSING" in f for f in findings)
    assert any("Mode B cards written" in f and "MISSING" in f for f in findings)


def test_gold_wellformed_passes():
    findings, stats = cds.check(_manifest(), "gold")
    assert findings == []
    assert stats["complete"] == 13


def test_gold_judgment_pending_fails():
    findings, _ = cds.check(
        _manifest("gold_completeness: JUDGMENT_PENDING\nMode B cards written: 12/12\n"), "gold")
    assert any("JUDGMENT_PENDING" in f for f in findings)


def test_gold_modeb_partial_fails():
    findings, _ = cds.check(
        _manifest("gold_completeness: COMPLETE\nMode B cards written: 8/12\n"), "gold")
    assert any("8/12" in f for f in findings)


def test_standard_mode_ignores_section_h():
    # standard mode has no Section-H requirement; a manifest without those lines is fine
    findings, _ = cds.check(_manifest(section_h="(none)\n"), "standard")
    assert findings == []

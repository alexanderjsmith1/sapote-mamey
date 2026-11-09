"""check_deliverable_suite rejects a repeated item row and any gold_completeness other than COMPLETE."""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("cds_464", ROOT / "tools" / "check_deliverable_suite.py")
cds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cds)

TAIL = ("\ngold_completeness: {gc}\nMode B cards written: 0/0\n"
        "Standing-constraint check: PASS\n")


def _manifest(extra_rows="", gc="COMPLETE"):
    rows = "\n".join(f"| {i} | item {i} | COMPLETE | a{i}.md |" for i in range(1, 14))
    return rows + "\n" + extra_rows + TAIL.format(gc=gc)


def test_duplicate_item_row_is_a_finding():
    text = _manifest("| 3 | item 3 | SKIPPED | deferred |\n")
    findings, _ = cds.check(text, "standard")
    assert any("item 3: listed 2 times" in f for f in findings)


def test_gold_unknown_completeness_is_a_finding():
    findings, _ = cds.check(_manifest(gc="UNKNOWN"), "gold")
    assert any("gold_completeness" in f and "UNKNOWN" in f for f in findings)


def test_clean_manifest_still_passes():
    assert cds.check(_manifest(), "gold")[0] == []

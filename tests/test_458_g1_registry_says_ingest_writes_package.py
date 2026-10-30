"""Registry item G1 must say what receipt ingestion does to the package.

`ingest-receipts` records Mode B cards through `judgment_store.record_mode_b`, which
writes `<package>/judgment/<strain>_<bgc>_mode_b.md` and the package's judgment
register. The G1 summary in `mamey/data/deliverables_registry.json` must say so,
and the generated menu must carry its reader summary with the same write locations.
"""
from pathlib import Path

from mamey import judgment_store
from mamey.deliverables_registry import load_registry

ROOT = Path(__file__).resolve().parents[1]


def _g1() -> dict:
    registry = load_registry()
    return next(item for item in registry["deliverables"] if item["label"] == "G1")


def test_ingest_writes_cards_and_register_inside_the_package(tmp_path):
    pkg = tmp_path / "AS-1" / "package"
    pkg.mkdir(parents=True)
    card = judgment_store._mode_b_path(pkg, "BGC0001")
    register = judgment_store._register_path(pkg)
    assert card.parent == pkg / "judgment"
    assert register.parent == pkg


def test_g1_summary_says_ingest_writes_judgment_cards_into_the_package():
    summary = _g1()["summary"]
    assert "without mutating" not in summary
    assert "`ingest-receipts` writes Mode B judgment cards into the package" in summary
    assert "`judgment/`" in summary
    assert "judgment register" in summary


def test_generated_menu_carries_the_g1_summary():
    menu = (ROOT / "docs" / "DELIVERABLE_MENU.md").read_text(encoding="utf-8")
    summary = _g1()["reader_summary"]
    assert summary in menu
    assert "`ingest-receipts` writes Mode B cards into `judgment/`" in summary
    assert "package's judgment register" in summary

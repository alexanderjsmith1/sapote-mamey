"""Keep internal Figure Factory repair packets out of the user documentation tree."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DOCS = ROOT / "docs" / "figure_factory"


def test_internal_figure_repair_packets_are_not_shipped_as_user_guides():
    assert not list(FIGURE_DOCS.glob("REPAIR_SPEC_*.md"))
    assert not (FIGURE_DOCS / "binding_status").exists()
    readme = (FIGURE_DOCS / "README.md").read_text(encoding="utf-8")
    assert "REPAIR_SPEC_" not in readme
    assert "binding_status" not in readme
    assert "development evidence stores" in readme

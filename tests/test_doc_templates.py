"""The shipped Mode-B doc templates exist and carry the claim-safety ceiling."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = [
    "templates/MODE_B_SUPPORT_CARD_TEMPLATE.md",
    "templates/DEEPER_DIVE_EXPLORATION_TEMPLATE.md",
    "templates/MODE_B_INTEGRATION_TEMPLATE.md",
]


def test_templates_ship():
    for rel in TEMPLATES:
        assert (ROOT / rel).is_file(), f"missing shipped template: {rel}"


def test_templates_are_claim_safe():
    for rel in TEMPLATES:
        text = (ROOT / rel).read_text(encoding="utf-8").lower()
        assert "claim" in text, f"{rel} lacks a claim ceiling"
        # a comparator/capacity framing, never a bare product/activity claim
        assert any(k in text for k in ("capacity", "hypothes", "not identified", "not a product",
                                       "claim ceiling", "not claims")), rel


def test_integration_template_has_reconciliation_section():
    text = (ROOT / "templates/MODE_B_INTEGRATION_TEMPLATE.md").read_text(encoding="utf-8")
    assert "Evidence-layer reconciliation" in text
    assert "Claim-safe thesis sentence" in text

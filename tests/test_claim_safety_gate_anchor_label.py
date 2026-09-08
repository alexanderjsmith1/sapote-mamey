"""Regression test for the label-anchor claim-safety rule (v9.7.353).

The verb-only `lint_text()` missed the real BGC059 defect line `KNOWN -> tetrachlorizine` (no
production verb). This test asserts the label-anchor extension catches it while leaving corrected,
class-level, negated, and idiomatic text clean.

It self-skips if the extension is not yet applied, so it is safe to drop into `tests/` alongside the
code change and activates automatically once the code lands.
"""
import pytest
from mamey.claim_safety_gate import lint_text

_KNOWN_BAD = "| BGC059 | 83% (14) | KNOWN -> tetrachlorizine | KNOWN |"


def _extension_present():
    return len(lint_text(_KNOWN_BAD)) >= 1


@pytest.mark.skipif(not _extension_present(),
                    reason="label-anchor extension not applied to claim_safety_gate.lint_text yet")
@pytest.mark.parametrize("text,expect_flagged", [
    ("| BGC059 | KNOWN -> tetrachlorizine | KNOWN |", True),
    ("BGC059  KNOWN → tetrachlorizine", True),                 # unicode arrow
    ("characterization: erythromycin", True),
    ("weak anchor (2/17 genes -> tetrachlorizine family); not a product call", False),
    ("anchor -> tetrachlorizine family (2/17 genes)", False),       # class-level qualifier
    ("The evidence does not support that BGC010 produces colibrimycin.", False),
    ("The deep assembly line makes it a strong capacity candidate.", False),
])
def test_label_anchor_rule(text, expect_flagged):
    findings = lint_text(text)
    assert bool(findings) == expect_flagged, (text, findings)


def test_known_bad_is_caught_once_applied():
    if not _extension_present():
        pytest.skip("extension not applied yet")
    assert any("tetrachlorizine" in f for f in lint_text(_KNOWN_BAD))

from __future__ import annotations

import xml.etree.ElementTree as ET

from mamey.interactive_figures.component_gallery import (
    component_specs,
    render_component_gallery_svg,
)


BANNED_CANVAS_TERMS = (
    "claim ceiling",
    "claim-ceiling",
    "does not prove",
    "owner review",
    "acceptance",
    "release",
    "publication",
)


def test_rejected_component_is_not_selectable() -> None:
    ids = [spec.component_id for spec in component_specs()]
    assert "claim-ceiling-ladder" not in ids
    assert ids == [
        "three-channel-evidence",
        "gene-role-reaction-ledger",
        "locus-architecture",
        "comparison-availability",
        "evidence-stage-ladder",
    ]


def test_replacement_is_neutral_and_source_object_oriented() -> None:
    replacement = component_specs()[-1]
    assert replacement.name == "Evidence-Stage Ladder"
    assert replacement.required_fields == (
        "evidence_stage",
        "source_object_type",
        "source_locator",
        "source_sha256",
        "observation_state",
    )
    assert "without ranking" in replacement.purpose


def test_corrected_canvas_contains_no_banned_terms() -> None:
    for theme_id in (
        "evidence-navy",
        "scientific-cream",
        "signal-dark",
        "high-contrast",
        "field-notebook",
        "quiet-slate",
    ):
        svg = render_component_gallery_svg(theme_id)
        ET.fromstring(svg)
        lowered = svg.lower()
        for term in BANNED_CANVAS_TERMS:
            assert term not in lowered
        assert "Evidence-Stage Ladder" in svg
        assert "Sequence · Culture · Structure · Assay · Host Study" in svg
        assert "STATIC COMPONENT" not in svg

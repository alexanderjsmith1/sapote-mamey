"""Synthetic Markdown only: YAML null metadata is missing, never the text "None"."""
import pytest

from mamey import sapote_markdown as sm

BASE = {
    "schema_version": sm.SCHEMA_VERSION,
    "document_type": "human_guide",
    "title": "A title",
    "audience": "New users",
    "authority": "User documentation; not a biological result",
    "render_profile": "human_guide",
    "claim_safety_footer": "Structure only; no biological claim.",
}


def _doc(**overrides):
    fields = dict(BASE, **overrides)
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    lines += ["---", "", "# Heading", "", "Body text.", ""]
    return "\n".join(lines)


def test_base_document_is_valid():
    assert sm.validate_model(sm.parse_text(_doc())).ok


@pytest.mark.parametrize("key", ["title", "audience", "authority", "claim_safety_footer"])
@pytest.mark.parametrize("null", ["null", "~", ""])
def test_null_required_field_is_reported_missing(key, null):
    with pytest.raises(sm.SapoteMarkdownError, match=f"META_{key.upper()}_REQUIRED") as caught:
        sm.parse_text(_doc(**{key: null}))
    assert "None" not in str(caught.value)


@pytest.mark.parametrize("value", ["true", "[a, b]", "{a: 1}", "2026-11-06"])
def test_non_text_field_is_refused(value):
    with pytest.raises(sm.SapoteMarkdownError, match="META_FIELD_TYPE_INVALID:authority"):
        sm.parse_text(_doc(authority=value))


def test_null_exact_locus_component_is_incomplete():
    text = _doc(document_type="mode_b_card", render_profile="mode_b_card").replace(
        "---\n\n#", "exact_locus:\n  strain: DEMO\n  node_or_contig: null\n  region: region001\n  bgc_alias: BGC001\n---\n\n#", 1)
    with pytest.raises(sm.SapoteMarkdownError, match="EXACT_LOCUS_INCOMPLETE") as caught:
        sm.parse_text(text)
    assert "DEMO / None /" not in str(caught.value)

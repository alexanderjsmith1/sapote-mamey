"""Regression guard for the complete exact-locus prompt authority chain."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTRACT = "strain / full node-or-contig / region / BGC alias"
GENERIC_COMPLETE_EXAMPLE = (
    "DEMO-STRAIN-01 / NODE_000001_length_50000_cov_30.0 / region001 / BGC001"
)
ACTIVE_SURFACES = (
    ROOT / "CHATGPT_START_HERE.md",
    ROOT / "CLAUDE_START_HERE.md",
    ROOT / "prompts" / "NODE_REGION_SELF_CHECK_PROMPT.md",
    ROOT / "prompts" / "CLAUDE_SYSTEM_PROMPT.md",
    ROOT / "prompts" / "SAPOTE_MAMEY_CO_EXECUTION_PROMPT.md",
    ROOT / "prompts" / "reuse" / "_SHARED_GUARD_BLOCK.md",
    ROOT / "prompts" / "reuse" / "SAPOTE_DELIVERABLES_REUSE_PROMPT.md",
)


def _text(path):
    return path.read_text(encoding="utf-8")


def _normalized(path):
    return " ".join(_text(path).split())


def test_every_active_surface_requires_all_four_components_in_order():
    missing = [str(path.relative_to(ROOT)) for path in ACTIVE_SURFACES
               if CONTRACT not in _normalized(path)]
    assert not missing, f"active exact-locus surfaces missing the complete contract: {missing}"


def test_canonical_guard_and_self_check_fail_closed_on_incomplete_identity():
    for path in (
        ROOT / "prompts" / "NODE_REGION_SELF_CHECK_PROMPT.md",
        ROOT / "prompts" / "reuse" / "_SHARED_GUARD_BLOCK.md",
    ):
        text = _normalized(path).lower()
        assert "identity hold" in text
        assert "guess" in text
        assert "fall back to the alias" in text


def test_start_files_do_not_present_node_region_validation_as_the_full_contract():
    for name in ("CHATGPT_START_HERE.md", "CLAUDE_START_HERE.md"):
        text = _normalized(ROOT / name)
        assert "narrower supplemental node/region check" in text
        assert "does not establish" in text
        assert "complete four-component identity" in text


def test_prompt_example_is_generic_portable_and_complete():
    text = _text(ROOT / "prompts" / "NODE_REGION_SELF_CHECK_PROMPT.md")
    assert GENERIC_COMPLETE_EXAMPLE in text
    assert "/Users/" not in text
    assert "Claude_Alex" not in text
    assert "Codex Alex" not in text


def test_delivery_recheck_repeats_the_complete_contract_and_hold_behavior():
    text = _text(ROOT / "prompts" / "NODE_REGION_SELF_CHECK_PROMPT.md")
    recheck = text.split("## RE-CHECK", 1)[1]
    assert CONTRACT in recheck
    assert "all four components came from one bound source record" in recheck
    assert "stop with an identity hold" in recheck
    assert "do not guess or fall back to the alias" in recheck


def test_superseded_short_form_is_not_normative_on_the_active_chain():
    forbidden = (
        "cite every bgc by node·region, never by bgc number",
        "every bgc reference carries `bgc_id (contig · regionxxx)`",
        "thereafter `bgc",
    )
    hits = []
    for path in ACTIVE_SURFACES:
        text = _normalized(path).lower()
        hits.extend(f"{path.relative_to(ROOT)}: {phrase}" for phrase in forbidden if phrase in text)
    assert not hits, "stale short-form exact-locus rules remain active: " + "; ".join(hits)

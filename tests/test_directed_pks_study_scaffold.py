"""Directed PKS Study scaffold tests.

The scaffold is intentionally public-tier safe: bundled example specs use AS-XXX,
not literal private strain identifiers. Private/merged runs can supply private
study specs outside public CODE/SID tiers.
"""
from pathlib import Path
import json

from mamey.directed_pks_study import (
    build_full20_skeleton,
    build_minimal_summary,
    forbidden_claim_hits,
    issue_dicts,
    load_rules,
    load_study_spec,
    private_identifier_hits,
    required_full20_sections,
    validate_full20_card_text,
    validate_study_spec,
    write_minimal_summary,
)


DATA = Path(__file__).resolve().parents[1] / "mamey" / "data" / "directed_pks_study"
SPEC_JSON = DATA / "example_ASXXX_directed_pks_study_spec.json"


def test_public_scaffold_data_has_no_literal_private_as705_identifier():
    hits = []
    for path in DATA.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if ("AS-" + "705") in text:
                hits.append(str(path.relative_to(DATA)))
    assert not hits, f"public directed PKS scaffold leaked private strain literal: {hits}"


def test_example_spec_loads_and_validates_public_safe():
    spec = load_study_spec(SPEC_JSON)
    issues = validate_study_spec(spec, public_tier=True)
    errors = [i for i in issues if i.severity == "ERROR"]
    assert errors == []
    assert spec["strain_id"] == "AS-XXX"
    assert private_identifier_hits(spec) == []


def test_literal_private_strain_id_is_rejected_in_public_spec():
    spec = load_study_spec(SPEC_JSON)
    spec["strain_id"] = "AS-" + "705"
    issues = validate_study_spec(spec, public_tier=True)
    codes = {i.code for i in issues}
    assert "PRIVATE_STRAIN_ID_IN_PUBLIC_SPEC" in codes


def test_excluded_bgc_requires_reason_and_preserves_background_logic():
    spec = load_study_spec(SPEC_JSON)
    assert "BGC011" in spec["focus"]["exclude_bgcs"]
    assert spec["focus"]["exclude_reason"]["BGC011"]
    spec["focus"]["exclude_reason"] = {}
    codes = {i.code for i in validate_study_spec(spec)}
    assert "EXCLUSION_WITHOUT_REASON" in codes


def test_functional_grouping_cannot_claim_physical_linkage_without_evidence():
    spec = load_study_spec(SPEC_JSON)
    spec["groups"]["SetA"]["interpretation_scope"] = "physical cluster; Set A is one BGC"
    issues = validate_study_spec(spec)
    codes = {i.code for i in issues}
    assert "UNSUPPORTED_PHYSICAL_LINKAGE_CLAIM" in codes
    assert "FORBIDDEN_CLAIM" in codes


def test_forbidden_product_identity_claims_are_caught():
    claimy = {"text": "This candidate makes desertomycin and uses product_identity_without_evidence."}
    assert forbidden_claim_hits(claimy)
    spec = load_study_spec(SPEC_JSON)
    spec["comparators"][0]["role"] = "AS-XXX makes desertomycin"
    codes = {i.code for i in validate_study_spec(spec)}
    assert "FORBIDDEN_CLAIM" in codes


def test_full20_sections_are_exactly_twenty_and_enforced():
    sections = required_full20_sections()
    assert len(sections) == 20
    skeleton = build_full20_skeleton()
    issues = validate_full20_card_text(skeleton)
    assert issue_dicts(issues) == []

    broken = skeleton.replace("Final Mode B judgement", "Final claim_scope statement")
    codes = {i.code for i in validate_full20_card_text(broken)}
    assert "MISSING_FULL20_SECTION" in codes
    assert "FORBIDDEN_TERM" in codes


def test_minimal_summary_emits_markdown_and_json(tmp_path):
    spec = load_study_spec(SPEC_JSON)
    md, payload = build_minimal_summary(spec)
    assert "functional_grouping" in md
    assert "comparator_context" in md
    assert payload["group_count"] == 2
    assert payload["excluded_bgcs"] == ["BGC011"]

    out = write_minimal_summary(spec, tmp_path)
    assert Path(out["markdown"]).exists()
    assert Path(out["json"]).exists()
    loaded = json.loads(Path(out["json"]).read_text())
    assert loaded["schema_version"] == "directed_pks_study_scaffold_v1"


def test_figure_gate_requires_nine_preflight_and_self_rating():
    spec = load_study_spec(SPEC_JSON)
    spec["figure_policy"]["quality_gate"] = 8
    codes = {i.code for i in validate_study_spec(spec)}
    assert "FIGURE_GATE_TOO_LOW" in codes

    spec = load_study_spec(SPEC_JSON)
    spec["figure_policy"]["require_self_rating"] = False
    codes = {i.code for i in validate_study_spec(spec)}
    assert "FIGURE_GATE_MISSING_REQUIREMENT" in codes

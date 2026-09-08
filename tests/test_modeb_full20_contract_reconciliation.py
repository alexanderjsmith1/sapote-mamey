from mamey.validators.modeb_full20 import (
    REQUIRED_MODEB_FULL20_SECTIONS,
    artifact_drift_issues,
    missing_modeb_sections,
    validate_full20,
    validate_modeb_card,
)

EXPECTED_CORRECTIVE_SECTIONS = [
    "Identity and node/region",
    "Why this BGC was selected",
    "Boundary and assembly status",
    "Gene-by-gene interpretation",
    "Core biosynthetic logic",
    "Tailoring and maturation logic",
    "Transport, resistance, and regulation",
    "Comparator/KCB interpretation",
    "Alternative hypotheses",
    "Fragmentation and co-capture risks",
    "Product-family interpretation",
    "Bee/microbe ecological interpretation",
    "Antibacterial/antifungal relevance",
    "What cannot be claimed",
    "Missing evidence",
    "BLASTP/HMMER next steps",
    "LC-MS / fermentation implications",
    "Figure/locus-map notes",
    "Final Mode B judgement",
    "Next actions",
]


def _full20_stub():
    return "\n".join(
        f"## §{i} — {section}\nEvidence unavailable: fixture. Required next step: fixture."
        for i, section in enumerate(REQUIRED_MODEB_FULL20_SECTIONS, start=1)
    )


def test_corrective_protocol_sections_are_the_only_current_contract():
    assert REQUIRED_MODEB_FULL20_SECTIONS == EXPECTED_CORRECTIVE_SECTIONS
    assert REQUIRED_MODEB_FULL20_SECTIONS[6] == "Transport, resistance, and regulation"
    assert REQUIRED_MODEB_FULL20_SECTIONS[15] == "BLASTP/HMMER next steps"


def test_full20_stub_passes_named_section_presence():
    assert validate_modeb_card(_full20_stub())
    result = validate_full20(_full20_stub())
    assert result.ok
    assert result.missing == []
    assert result.artifact_drift == []
    assert result.invented_or_obsolete_sections == []


def test_legacy_eight_section_card_fails_full20():
    legacy = "\n".join(f"## §{i} Legacy section\ntext" for i in range(1, 9))
    assert not validate_modeb_card(legacy)
    assert len(missing_modeb_sections(legacy)) >= 12


def test_old_full20_titles_fail_because_llm_cannot_make_up_sections():
    old_titles = [
        "Stable identity and node-first locator",
        "BGC class and antiSMASH call",
        "Assembly / boundary status",
        "Gene-by-gene architecture",
        "Core domain architecture",
        "Comparator / KCB / MIBiG evidence",
        "Manual BLASTP evidence, if present",
        "Functional grouping context",
        "Biosynthetic logic and predicted chemical space",
        "Antifungal relevance",
        "Bee-microbe ecological relevance",
        "Fragmentation risks and non-merge warnings",
        "Exclusion / background-control logic, if applicable",
        "Citation status ledger",
        "Wet-lab LC-HRMS/DAD expectations",
        "Genetic validation options",
        "Dereplication risks",
        "Figure-ready locus map notes",
        "Final interpretation_scope statement",
        "Next evidence needed",
    ]
    md = "\n".join(f"## §{i} — {section}\ntext" for i, section in enumerate(old_titles, start=1))
    result = validate_full20(md)
    assert not result.ok
    assert "§1 — Identity and node/region" in result.missing
    assert any("Manual BLASTP evidence" in s for s in result.invented_or_obsolete_sections)


def test_blastp_hmmer_belongs_at_section_16_not_section_7():
    md = _full20_stub().replace(
        "§7 — Transport, resistance, and regulation",
        "§7 — Manual BLASTP evidence, if present",
    )
    result = validate_full20(md)
    assert not result.ok
    assert "§7 — Transport, resistance, and regulation" in result.missing
    assert any("BLASTP" in issue for issue in result.artifact_drift)
    assert "§16 — BLASTP/HMMER next steps" not in result.missing


def test_integrated_table_only_fails_full20():
    table = """| Node | Class | CDS | BLASTP anchors |
|---|---|---:|---|
| NODE_12 | T1PKS/NRPS | 38 | comparator axis |
"""
    assert not validate_modeb_card(table)


def test_section_4_table_only_is_artifact_drift_even_with_all_headings():
    md = _full20_stub().replace(
        "Evidence unavailable: fixture. Required next step: fixture.",
        "Evidence unavailable: fixture. Required next step: fixture.",
        3,
    )
    md = md.replace(
        "## §4 — Gene-by-gene interpretation\nEvidence unavailable: fixture. Required next step: fixture.",
        "## §4 — Gene-by-gene interpretation\n| locus | protein_length_aa | role |\n|---|---:|---|\n| ctg1_1 | 1200 | core |\n| ctg1_2 | 240 | transporter |",
    )
    result = validate_full20(md)
    assert not result.ok
    assert any(issue.startswith("SECTION_4_TABLE_ONLY") for issue in result.artifact_drift)
    assert artifact_drift_issues(md)


def test_full_modeb_metadata_partial_sections_still_fails():
    md = """---
treatment_status: full Mode B
---
# BGC008
## §1 — Identity and node/region
text
## §2 — Why this BGC was selected
text
"""
    result = validate_full20(md)
    assert not result.ok
    assert len(result.missing) >= 18


def test_fragment_shell_with_all_sections_passes_even_when_evidence_unavailable():
    result = validate_full20(_full20_stub())
    assert result.ok

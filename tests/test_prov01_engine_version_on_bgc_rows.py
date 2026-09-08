"""PROV-01 (v9.7.336) — every B1_BGC_Master row carries the engine that produced it.

A2_Strain_Registry and A3_Run_Manifest already stamped a strain-level `workflow_version`, but
`B1_BGC_Master` — the sheet every cross-strain figure, cohort synthesis and lead comparison joins
on — had no engine field at all. A master accumulated one strain at a time across an engine bump
was therefore silently mixed, with nothing marking the boundary.

That is not hypothetical here. Engine 1.9.114 changed `parsers.extract_domain_features`
(`exclude_regions=True`, region-GBK de-duplication), which feeds `architecture_first`, so
`Arch_Capacity`, `Class_Conf` and `Lead_tier_auto` are **not comparable** across that boundary —
confirmed on AS-421, where BGC006 moved High -> Medium between 1.9.113 and 1.9.115.

The column is appended at the END of the schema so readers that index by header name are
unaffected.
"""

from mamey.master_workbook import CANONICAL_V1_HEADERS as SHEET_HEADERS


def test_b1_bgc_master_declares_engine_version():
    """The schema must carry the column at all."""
    assert "engine_version" in SHEET_HEADERS["B1_BGC_Master"], (
        "B1_BGC_Master is what cross-strain work joins on; without an engine stamp a mixed-engine "
        "master is silent"
    )


def test_engine_version_is_appended_last_so_named_readers_are_unaffected():
    """Additive at the tail — an existing reader indexing by name must not shift."""
    hdr = SHEET_HEADERS["B1_BGC_Master"]
    assert hdr[-1] == "engine_version", hdr[-5:]
    # the historically-last claim-safety triple must still be intact and in order
    assert hdr[-4:-1] == ["claim_confidence", "claim_ceiling", "safe_claim"], hdr[-6:]


def test_strain_level_provenance_still_present():
    """Control: PROV-01 adds to, and does not replace, the existing strain-level stamps."""
    assert "workflow_version" in SHEET_HEADERS["A2_Strain_Registry"]
    assert "version" in SHEET_HEADERS["A3_Run_Manifest"]

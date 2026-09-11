import json, tempfile, pathlib
from mamey import cli

def test_emit_bgc_bank_schema():
    manifest = {
        "strain_id": "SID-XXX", "taxonomy": "Streptomyces sp.",
        "assembly": {"contigs": 50, "n50": 120000, "genome_bp": 8_000_000, "gc_pct": 72.1, "largest_contig": 500000},
        "bgc_counts": {"raw": 2, "interior": 1, "edge": 1, "full_contig": 0, "corrected": 1.5},
        "bgcs": [
            {"bgc_id": "BGC001", "region_number": 1, "contig": "ctg1", "products": ["NRPS"],
             "edge_status": "Interior", "length_kb": 30.0, "cctt_triggers": "T43-HAL_halogenase", "release": "PUBLIC"},
            {"bgc_id": "BGC002", "region_number": 2, "contig": "ctg2", "products": ["T1PKS", "saccharide"],
             "edge_status": "Edge", "length_kb": 12.5, "cctt_triggers": "", "release": "PUBLIC"},
        ],
    }
    with tempfile.TemporaryDirectory() as d:
        pd = pathlib.Path(d)
        cli._emit_bgc_bank(pd, manifest)
        bank = json.loads((pd / "bgc_data.json").read_text())
        assert list(bank["strains"]) == ["SID-XXX"]
        assert len(bank["bgcs"]) == 2
        b0 = bank["bgcs"][0]
        assert b0["sid"] == "SID-XXX" and b0["bgc_id"] == "BGC001"
        assert b0["length_kb"] == 30.0 and b0["cctt_triggers"] == "T43-HAL_halogenase"
        assert b0["region"] == "region001" and b0["products"] == "NRPS"


def test_emit_bgc_bank_persists_membership_authority_for_other_cohort():
    # v9.7.402 (W402-35 round 3, requirement #6): the routing-vs-membership distinction must
    # survive into the persisted bank, not just the in-memory resolver result -- a reader of
    # bgc_data.json must not treat a persisted cohort="OTHER" row as confirmed scientific
    # cohort membership. Generic, non-project-specific strain_id: no real cohort resolves it.
    manifest = {
        "strain_id": "ZZZQ00000000", "taxonomy": "Streptomyces sp.",
        "assembly": {"contigs": 1, "n50": 1, "genome_bp": 1, "gc_pct": 50.0, "largest_contig": 1},
        "bgc_counts": {"raw": 0, "interior": 0, "edge": 0, "full_contig": 0, "corrected": 0},
        "bgcs": [],
    }
    with tempfile.TemporaryDirectory() as d:
        pd = pathlib.Path(d)
        cli._emit_bgc_bank(pd, manifest)
        bank = json.loads((pd / "bgc_data.json").read_text())
        strain = bank["strains"]["ZZZQ00000000"]
        assert strain["cohort"] == "OTHER"
        assert strain["membership_authority"] == "ROUTING_ONLY_NOT_SCIENTIFIC_COHORT_MEMBERSHIP"


def test_emit_bgc_bank_membership_authority_is_none_for_as_cohort():
    manifest = {
        "strain_id": "AS-1", "taxonomy": "Streptomyces sp.",
        "assembly": {"contigs": 1, "n50": 1, "genome_bp": 1, "gc_pct": 50.0, "largest_contig": 1},
        "bgc_counts": {"raw": 0, "interior": 0, "edge": 0, "full_contig": 0, "corrected": 0},
        "bgcs": [],
    }
    with tempfile.TemporaryDirectory() as d:
        pd = pathlib.Path(d)
        cli._emit_bgc_bank(pd, manifest)
        bank = json.loads((pd / "bgc_data.json").read_text())
        strain = bank["strains"]["AS-1"]
        assert strain["cohort"] == "AS"
        assert strain["membership_authority"] is None

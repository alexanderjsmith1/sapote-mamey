"""v9.7.87 Item A + P-11: per-BGC bldA tier is NOT_APPLICABLE on non-actinomycetes,
and kingdom-level labels (Fungi sp.) reach non_actinomycete."""
from __future__ import annotations
import pytest
from mamey.cohort_resolver import actino_status
from mamey.source_scans import scan_blda_tta


def test_kingdom_tokens_resolve_non_actino():
    # P-11: the bare-FASTA case — kingdom known, genus not
    for t in ("Fungi sp.", "fungi", "fungal", "Eukaryota", "eukaryote", "Archaea"):
        assert actino_status(t) == "non_actinomycete", t


def test_actinomycetes_unaffected():
    for t in ("Streptomyces", "Amycolatopsis", "Actinomadura rugatobispora", "Saccharopolyspora"):
        assert actino_status(t) == "actinomycete", t


class _BGC:
    def __init__(self, bid, start, end, contig="C1"):
        self.bgc_id, self.start, self.end, self.contig = bid, start, end, contig


def test_per_bgc_tier_not_applicable_on_non_actino():
    # Item A: scan_blda_tta gates per-BGC tiers when organism is non-actinomycete
    bgcs = [_BGC("BGC001", 0, 1000), _BGC("BGC002", 2000, 3000)]
    res = scan_blda_tta([], bgcs, organism="Fungi sp.")
    assert res["status"] == "NOT_APPLICABLE"
    for bid, d in res["per_bgc"].items():
        assert d["bldA_tier"] == "NOT_APPLICABLE", bid


def test_per_bgc_tier_fires_on_actino():
    # actino control: tiers still computed (no organism gate)
    bgcs = [_BGC("BGC001", 0, 1000)]
    res = scan_blda_tta([], bgcs, organism="Streptomyces coelicolor")
    assert res["status"] == "SOURCE_DERIVED"
    assert res["per_bgc"]["BGC001"]["bldA_tier"] in ("T1", "T2", "T3", "T4")

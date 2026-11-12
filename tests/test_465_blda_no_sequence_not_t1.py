"""A BGC with no readable CDS sequence must not be given bldA tier T1 ("no TTA codons").

Zero TTA counted from zero codons is not a measurement. gene_context already returns None for
this case; the per-BGC scan now says NOT_COMPUTED.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from mamey.models import CDSFeature
from mamey.source_scans import BLDA_TIER_NOT_COMPUTED, scan_blda_tta


class _BGC:
    def __init__(self, bid, start, end, contig="C1"):
        self.bgc_id, self.start, self.end, self.contig = bid, start, end, contig


def _cds(tag, start, end, seq):
    return CDSFeature("C1", start, end, 1, tag, "synthetic", nucleotide_seq=seq)


def _tier(cds, organism="Streptomyces sp."):
    return scan_blda_tta(cds, [_BGC("BGC001", 0, 1000)], organism=organism)["per_bgc"]["BGC001"]


def test_bgc_without_cds_is_not_computed():
    d = _tier([])
    assert d["bldA_tier"] == BLDA_TIER_NOT_COMPUTED == "NOT_COMPUTED"
    assert "No TTA codons detected" not in d["bldA_interpretation"]


def test_cds_without_sequence_are_not_computed():
    d = _tier([_cds("a", 10, 30, ""), _cds("b", 40, 90, "")])
    assert d["bldA_tier"] == "NOT_COMPUTED"
    assert (d["total_cds"], d["cds_without_sequence"], d["total_codons"]) == (2, 2, 0)


def test_partly_read_bgc_keeps_its_tier_and_names_the_unread_cds():
    d = _tier([_cds("a", 10, 30, "ATGGCCTAA"), _cds("b", 40, 90, "")])
    assert d["bldA_tier"] == "T1"
    assert d["cds_without_sequence"] == 1
    assert "1 of 2 BGC CDS" in d["bldA_interpretation"]


def test_read_sequences_still_tier_normally():
    assert _tier([_cds("a", 10, 30, "ATGGCCTAA")])["bldA_tier"] == "T1"
    assert _tier([_cds("a", 10, 30, "TTATTATTA")])["bldA_tier"] == "T3"


def test_non_actino_gate_is_unchanged():
    assert _tier([], organism="Fungi sp.")["bldA_tier"] == "NOT_APPLICABLE"


def _first_pass():
    tool = Path(__file__).resolve().parents[1] / "tools" / "build_first_pass_scans.py"
    spec = importlib.util.spec_from_file_location("bfps_465_blda", tool)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_first_pass_page_does_not_report_t1_when_no_scan_result():
    text = _first_pass()._blda({})
    assert "All BGCs at T1" not in text
    assert "No bldA/TTA result in this package" in text


def test_first_pass_page_lists_not_computed_bgcs():
    text = _first_pass()._blda({"blda_tta": {"per_bgc": {"BGC001": {"bldA_tier": "NOT_COMPUTED", "tta_codons": 0}}}})
    assert "All BGCs at T1" not in text
    assert "NOT_COMPUTED=1" in text

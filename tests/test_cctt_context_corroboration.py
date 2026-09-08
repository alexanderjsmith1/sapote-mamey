"""N-05/A-04: class-defining CCTT triggers must be corroborated by the BGC product class.

When a class-definitive trigger fires on an incompatible class (T43-PTM on a lasso, T43-TET on a saccharide,
T43-PHO on a T3PKS), it matched a single token with no corroborating context — a candidate false positive.
The firing is flagged (not deleted: evidence conservation) so a class-capacity claim is not built on it.
Promiscuous tailoring triggers (halogenase) and broad triggers (N-N bond) are never flagged.
"""
from dataclasses import dataclass, field
from mamey.source_scans import (cctt_trigger_corroborated, cctt_context_uncorroborated,
                                 CCTT_CLASS_COMPAT, CCTT_PROMISCUOUS)


@dataclass
class _B:
    bgc_id: str
    products: list = field(default_factory=list)


def test_corroborated_true_positives():
    assert cctt_trigger_corroborated("T43-PTM_hsaf_tetramate", ["PKS", "NRPS"])
    assert cctt_trigger_corroborated("T43-LAN_lanthipeptide", ["RiPP", "lanthipeptide-class-i"])
    assert cctt_trigger_corroborated("T43-BLA_betalactam", ["NRPS"])


def test_uncorroborated_false_positives():
    assert not cctt_trigger_corroborated("T43-PTM_hsaf_tetramate", ["RiPP", "lassopeptide"])  # lasso instance (the audit-flagged case)
    assert not cctt_trigger_corroborated("T43-TET_tetronate_spirotetronate", ["saccharide"])  # SID-XXX BGC043
    assert not cctt_trigger_corroborated("T43-PHO_phosphonate", ["PKS", "T3PKS"])             # SID-XXX BGC088
    assert not cctt_trigger_corroborated("T43-BLA_betalactam", ["terpene"])                   # A4 shape


def test_promiscuous_never_flagged():
    for t in CCTT_PROMISCUOUS:
        assert cctt_trigger_corroborated(t, ["terpene"])      # any class is fine for a tailoring/broad trigger


def test_ungated_trigger_passes():
    # a trigger with no compat entry is treated as corroborated (not gated)
    assert cctt_trigger_corroborated("T43-NOT-A-REAL-TRIGGER", ["terpene"])


def test_context_uncorroborated_listing():
    bgcs = [_B("BGC001", ["RiPP", "lassopeptide"]),   # PTM here is uncorroborated
            _B("BGC002", ["PKS", "NRPS"])]            # PTM here is fine
    per_bgc = {"BGC001": ["T43-PTM_hsaf_tetramate", "T43-LAN_lanthipeptide"],
               "BGC002": ["T43-PTM_hsaf_tetramate"]}
    flagged = cctt_context_uncorroborated(per_bgc, bgcs)
    pairs = {(e["bgc"], e["trigger"]) for e in flagged}
    assert ("BGC001", "T43-PTM_hsaf_tetramate") in pairs
    assert ("BGC001", "T43-LAN_lanthipeptide") not in pairs   # LAN is corroborated by RiPP
    assert ("BGC002", "T43-PTM_hsaf_tetramate") not in pairs   # PTM corroborated by PKS/NRPS

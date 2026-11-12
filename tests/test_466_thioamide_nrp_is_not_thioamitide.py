"""antiSMASH's thioamide-NRP product is nonribosomal; it must not be labelled or advised as the thioamitide RiPP class."""
from mamey.lead_pages import classify


def test_thioamide_nrp_is_its_own_class():
    assert classify("", "enteromycin", "thioamide-NRP") == "thioamide_NRP"


def test_thioamitide_ripp_keeps_its_class():
    assert classify("", "thioviridamide", "RiPP-like") == "thioamitide_thioamide"
    assert classify("T43-THA_thioamide", "", "RRE-containing;RiPP-like") == "thioamitide_thioamide"


def test_thioamide_nrp_with_thioamitide_evidence_stays_thioamitide():
    assert classify("", "thioamitide", "thioamide-NRP") == "thioamitide_thioamide"

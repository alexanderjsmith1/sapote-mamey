"""v9.7.196 Patch F — aSModule features are no longer dropped, and A-domain substrate consensus is
surfaced from the region GBK. (Substrate RESOLUTION is Patch G's job via JSON; F ensures the GBK-level
feature extraction is correct.)"""
import os
import pytest
from mamey.parsers import extract_domain_features

_ZIP = "/tmp/as421_region.zip"


@pytest.mark.skipif(not os.path.exists(_ZIP), reason="AS-421 region zip not present")
def test_asmodule_features_extracted():
    doms = extract_domain_features(_ZIP)
    asmod = [d for d in doms if d.feature_type == "aSModule"]
    assert asmod, "aSModule features dropped (wanted-set regression)"


@pytest.mark.skipif(not os.path.exists(_ZIP), reason="AS-421 region zip not present")
def test_substrate_consensus_field_populated():
    doms = extract_domain_features(_ZIP)
    subs = [d for d in doms if d.substrate_consensus]
    assert subs, "no substrate_consensus surfaced from /specificity"


# --- v9.7.197: F completion — aSModule_count reaches output (suffix-strip + coordinate keying) ---
def test_asmodule_count_nonzero_after_suffix_strip():
    """The region-GBK contig suffix (.NNNNNN) previously blocked keying → aSModule_count=0.
    After the suffix strip, modules key to a BGC on the bare contig + coordinate window."""
    import os
    if not os.path.exists("/tmp/as421_region.zip"):
        import pytest; pytest.skip("region zip fixture absent")
    from mamey.domain_level import modules_from_source_zip
    bgcs = [{"bgc_id": "BGC041", "contig": "NODE_6_length_340027_cov_84", "start": 0, "end": 50000}]
    out = modules_from_source_zip("/tmp/as421_region.zip", bgcs)
    assert len(out.get("BGC041", [])) > 0, "aSModule_count still 0 — suffix strip / keying regressed"

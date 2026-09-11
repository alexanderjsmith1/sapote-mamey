"""v9.7.134: bgc_decomp interpretation guard must not carry stale bundle versions."""
import re
from mamey import bgc_decomp


def test_bgc_decomp_interpretation_guard_is_version_neutral():
    guard = bgc_decomp._INTERP_GUARD
    assert "Gene-architecture two-model analysis." in guard
    assert not re.search(r"v\d+\.\d+\.\d+", guard), (
        "_INTERP_GUARD is emitted into two-model CSV rows; do not hard-code a bundle "
        "version there unless it is programmatically synced every release."
    )

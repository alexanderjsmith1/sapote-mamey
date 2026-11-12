"""The antifungal dossier calls a lead reference-dark only when KnownClusterBlast reported no hit."""
from mamey.af_dossier import _reference_dark


def test_named_anchor_is_not_dark():
    assert _reference_dark("BGC0000055 | erythromycin", {"BGC001": "UNKNOWN_KCB"}, "BGC001") == "no"


def test_reported_no_hit_is_dark():
    assert _reference_dark("", {"BGC001": "KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED"}, "BGC001") == "yes"


def test_missing_result_is_unknown():
    for states in ({"BGC001": "UNKNOWN_KCB"}, {"BGC001": "CLUSTERBLAST_FALLBACK_OBSERVED"}, {}, None):
        assert _reference_dark("", states, "BGC001") == "unknown", states

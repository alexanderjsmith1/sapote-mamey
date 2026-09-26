"""A mixed-profile acknowledgement cannot make missing provenance safe."""
import json

import pytest

from mamey.figure_policy import FigurePolicyError
from mamey.interactive_figures.figure_set_renderer import _load_with_benchmarks


def _payload(tmp_path, profiles, acknowledgement):
    records = {}
    for index, profile in enumerate(profiles, start=1):
        record = {"governance": "GOVERNED", "classes": {"NRPS": {"total": 3}}}
        if profile is not None:
            record["antismashProfile"] = profile
        records[f"AS-{index}"] = record
    path = tmp_path / "widget.json"
    path.write_text(json.dumps({
        "meta": {"antismashProfileMixAcknowledged": acknowledgement},
        "strains": records,
    }))
    return path


@pytest.mark.parametrize("profiles,ack", [
    (["loose", "unknown"], {"loose": 1, "unknown": 1}),
    (["loose", None], {"loose": 1, "unrecorded": 1}),
])
def test_acknowledgement_cannot_admit_missing_profile(tmp_path, profiles, ack):
    with pytest.raises(FigurePolicyError, match="FIGURE_ANTISMASH_PROFILE_MIXED"):
        _load_with_benchmarks(_payload(tmp_path, profiles, ack))


def test_acknowledgement_still_admits_known_mixed_profiles(tmp_path):
    _load_with_benchmarks(_payload(
        tmp_path, ["loose", "relaxed"], {"loose": 1, "relaxed": 1},
    ))

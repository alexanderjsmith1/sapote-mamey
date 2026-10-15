"""v9.7.452: the attine bioassay profile carries the same presentation keys as the moss profile (owner, 13 Oct: the
papers' bioassay figures match): dark axis titles, C. albicans and C. auris split in A01, one pooled Candida panel in A04."""
import json
from pathlib import Path

LAY = Path(__file__).resolve().parents[1] / "mamey" / "data" / "bioassay_layouts.json"


def test_attine_profile_matches_moss_presentation_keys():
    d = json.loads(LAY.read_text())
    att, moss = d["attine"], d["moss"]
    for k in ("split_candida", "axis_title_ink", "a04_pool_candida", "a04_candida_axis_label"):
        assert k in att, k
        assert att[k] == moss[k], k
    # point labels differ by the owner's ruling (13 Oct): attine labels every isolate off the origin, moss the strong ones
    assert att["a04_point_labels"] == "nonzero" and moss["a04_point_labels"] == "strong"
    # collection-specific keys stay the attine profile's own
    assert att["focal_group"] is None and att["a04_source_shape"] is False

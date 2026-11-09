"""TIGRFAM hits outside every region are not attributed to region 1; fallbacks are marked.

Before: a hit whose coordinate lay outside all recorded areas was keyed `<rec>_c1`, the same as a
hit with no readable location, and no field said the key was a fallback.
"""
from mamey.antismash_evidence import _tigrfam_from_rec


def _rec(location, areas=({"start": 0, "end": 1000},)):
    hit = {"identifier": "TIGR01454", "locus_tag": "g1"}
    if location is not None:
        hit["location"] = location
    rec = {"id": "NODE_9", "modules": {"antismash.detection.tigrfam": {"hits": [hit]}}}
    if areas is not None:
        rec["areas"] = list(areas)
    return rec


def _run(rec):
    out = {}
    _tigrfam_from_rec(rec, "x.json", out)
    return out


def test_hit_outside_all_areas_is_unassigned():
    out = _run(_rec("[5000:5600](+)"))
    assert set(out) == {"NODE_9_unassigned"}
    assert out["NODE_9_unassigned"][0]["region_assignment"] == "OUTSIDE_ALL_REGIONS"


def test_resolved_and_fallback_hits_are_labelled():
    assert _run(_rec("[100:400](+)"))["NODE_9_c1"][0]["region_assignment"] == "COORDINATE_RESOLVED"
    assert _run(_rec(None))["NODE_9_c1"][0]["region_assignment"] == "UNRESOLVED_FALLBACK_REGION1"
    assert _run(_rec("[100:400](+)", areas=None))["NODE_9_c1"][0]["region_assignment"] == "UNRESOLVED_FALLBACK_REGION1"

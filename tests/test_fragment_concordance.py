"""Fragment-concordance scorer — the consumer the reference panel feeds (v9.7.22-n).

The three adjudicated references are the fixtures: marker credit uses each reference's ADJUDICATED
expected_marker_set, so a PENDING scanned marker earns no credit (claim-safe).
"""
import importlib.util, json, pathlib
import pytest
ROOT = pathlib.Path(__file__).resolve().parent.parent
# reference_bgc_library.json is user-regenerated in the public release (not shipped, see
# FETCH_REFERENCE_DATA.md). Skip this curated-library test cleanly when it is absent.
_LIB_PATH = ROOT / "mamey" / "data" / "reference_bgc_library.json"
if not _LIB_PATH.exists():
    pytest.skip("reference_bgc_library.json absent (user-regenerated in public release)",
                allow_module_level=True)
_spec = importlib.util.spec_from_file_location("fcs", ROOT / "tools" / "fragment_concordance_scorer.py")
fcs = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(fcs)
_LIB = json.loads(_LIB_PATH.read_text(encoding="utf-8"))
_ITEMS = _LIB if isinstance(_LIB, list) else _LIB.get("entries", _LIB.get("references"))
def refsig(name): return fcs.ref_signature([e for e in _ITEMS if (e.get("compound") or e.get("name")) == name][0])
def panel(): return fcs.load_panel(ROOT / "mamey" / "data" / "reference_bgc_library.json")

# --- component units ---
def test_region_jaccard():
    assert abs(fcs._jaccard({"a", "b"}, {"b", "c"}) - 1/3) < 1e-9

def test_count_sim():
    assert fcs._count_sim(8, 8) == 1.0 and fcs._count_sim(0, 0) == 1.0
    assert fcs._count_sim(None, 3) == 0.5

def test_marker_concordance_partial():
    assert fcs._marker_concordance({"T43-ENE"}, {"T43-ENE", "T43-HAL"}) == 0.5

def test_marker_concordance_negative_reference():
    assert fcs._marker_concordance(set(), set()) == 1.0
    assert fcs._marker_concordance({"T43-HAL"}, set()) == 0.4

# --- the three adjudications as fixtures ---
def test_c1027_uses_widened_expected_marker_set():
    r = refsig("C-1027")
    assert r["markers"] == {"T43-ENE", "T43-HAL"} and r["marker_status"] == "RESOLVED"
    assert fcs._marker_concordance({"T43-ENE", "T43-HAL"}, r["markers"]) == 1.0
    assert fcs._marker_concordance({"T43-ENE"}, r["markers"]) == 0.5  # adjudication's effect

def test_pending_reference_gives_no_marker_credit():
    r = refsig("pekiskomycin")
    assert r["markers"] == set() and r["marker_status"] == "PENDING"
    assert fcs._marker_concordance({"T43-HAL"}, r["markers"]) == 0.4  # not credited (claim-safe)

def test_t43_negative_reference():
    r = refsig("piericidin")
    assert r["markers"] == set()
    assert fcs._marker_concordance(set(), r["markers"]) == 1.0

# --- end-to-end best_match over the real 73-ref panel ---
def test_best_match_piericidin_like_fragment():
    obs = fcs.obs_signature({"id": "X", "region": "PKS; T1PKS", "pks_ks": 8, "nrps_c": 0,
                             "nrps_a": 0, "markers": [], "size_kb": 49.4})
    res = fcs.best_match(obs, panel())
    assert res["best_compound"] == "piericidin" and res["tier"] == "STRONG"

def test_best_match_c1027_like_fragment_surfaces_c1027():
    obs = fcs.obs_signature({"id": "Y", "region": "NRPS; PKS; T1PKS; halogenated; other; saccharide",
                             "pks_ks": 1, "nrps_c": 1, "nrps_a": 3, "markers": ["T43-ENE", "T43-HAL"], "size_kb": 73.1})
    res = fcs.best_match(obs, panel())
    assert "C-1027" in res["top_matches"]

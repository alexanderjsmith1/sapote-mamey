"""reconstruction_verdict: overlap-fraction on shared reference-gene coverage gates acceptance."""
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location(
    "build_reconstruction", pathlib.Path(__file__).resolve().parent.parent / "tools" / "build_reconstruction.py")
br = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(br)

def _frag(subjects):
    return {"cb": {"R": {"hits": [{"subject": s, "query": "q", "pid": "80", "score": "100"} for s in subjects]}}}

def test_complementary_is_supported():
    v = br.reconstruction_verdict([_frag(["g1", "g2", "g3"]), _frag(["g4", "g5", "g6"])], "R")
    assert v["verdict"] == "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY" and v["overlap"] == 0

def test_high_overlap_not_supported():
    v = br.reconstruction_verdict([_frag(["g1", "g2", "g3", "g4"]), _frag(["g1", "g2", "g3", "g5"])], "R")
    assert v["verdict"] == "RECONSTRUCTION_NOT_SUPPORTED_HIGH_REFERENCE_OVERLAP"

def test_partial_overlap_is_weak():
    v = br.reconstruction_verdict([_frag(["g1", "g2", "g3", "g4", "g5"]), _frag(["g3", "g6", "g7", "g8", "g9"])], "R")
    assert v["verdict"] == "RECONSTRUCTION_WEAK_PARTIAL_OVERLAP"

def test_single_fragment_unevaluable():
    v = br.reconstruction_verdict([_frag(["g1", "g2"])], "R")
    assert v["verdict"] == "RECONSTRUCTION_UNEVALUABLE_SINGLE_OR_NO_COVERAGE"

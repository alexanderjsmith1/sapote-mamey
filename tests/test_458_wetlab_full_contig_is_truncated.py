"""The wet-lab matrix treats the engine's "Full-contig" edge status as truncated.

The tool tested for "Full-Contig"; the engine writes "Full-contig" (mamey/architecture_first.py).
Full-contig BGCs never got the -2 truncation term or the HIGH sequencing flag.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("build_wetlab_matrix_458", ROOT / "tools" / "build_wetlab_matrix.py")
wl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wl)

from mamey.architecture_first import BoundaryStatus  # noqa: E402


def _bgc(edge):
    return {"edge_status": edge, "architecture_confidence": "A", "kcb_cumulative": 500,
            "length_kb": 40, "products": ["NRPS"]}


def test_engine_spelling_is_what_the_tool_matches():
    assert BoundaryStatus.FULL_CONTIG.value == "Full-contig"


def test_full_contig_gets_the_truncation_term():
    _, terms, _ = wl.score_bgc(_bgc("Full-contig"), "T1")
    assert ("edge/FC truncation", -2, "edge_status") in terms


def test_full_contig_flags_sequencing_high():
    b = _bgc("Full-contig")
    base, _, _ = wl.score_bgc(b, "T1")
    assert wl.action_scores(b, base, "T1")[0] == "HIGH"   # (sequencing, activation, isolation, dereplication)


def test_interior_is_untouched():
    _, terms, _ = wl.score_bgc(_bgc("Interior"), "T1")
    assert not any(t[0] == "edge/FC truncation" for t in terms)

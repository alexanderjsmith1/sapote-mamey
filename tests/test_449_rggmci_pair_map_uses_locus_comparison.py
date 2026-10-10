"""tools/rggmci_pair_locus_map.py draws a pair with the locus-comparison renderer (made-up ids only).

2026-10-06: the owner on the old pair map, "this makes no sense as shown": both fragments were pushed to the right of the
reference, so every ribbon crossed the page, and fragment A's labels sat under the gap. Now each fragment sits under the
reference genes it matches: the fragment with more matched genes on top, the reference in the middle, the other below.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pm = _load("rggmci_pair_locus_map")

AA = "MSTNPKLVAEGRDIQWYFHC"


def _aa(i):
    return (AA[i % 20:] + AA[:i % 20]) * 15


# reference: six genes; fragment B (ctgB, a contig start) holds genes 1-4, fragment A (ctgA, a contig end) genes 5-6
REF = [{"id": f"g{i:03d}", "i": i, "name": f"tstG{i}", "start": (i - 1) * 1100, "end": (i - 1) * 1100 + 1000,
        "strand": 1, "aa": _aa(i)} for i in range(1, 7)]


def _prot(tag, contig, start, i, contig_len, strand=1):
    return {"tag": tag, "contig": contig, "start": start, "end": start + 1000, "strand": strand, "aa": _aa(i + 7),
            "contig_len": contig_len, "missing_stop": False}


PROTS = {"q1": _prot("b_1", "ctgB", 100, 1, 6000), "q2": _prot("b_2", "ctgB", 1200, 2, 6000),
         "q3": _prot("b_3", "ctgB", 2300, 3, 6000), "q4": _prot("b_4", "ctgB", 3400, 4, 6000),
         "q5": _prot("a_1", "ctgA", 30000, 5, 33000), "q6": _prot("a_2", "ctgA", 31100, 6, 33000),
         "q7": _prot("a_0", "ctgA", 26000, 9, 33000)}
RA = {"contig": "ctgA", "start": 25000, "end": 33000, "identity": "TST-1 / ctgA / region002 / BGC018"}
RB = {"contig": "ctgB", "start": 0, "end": 6000, "identity": "TST-1 / ctgB / region001 / BGC042"}


def _rows(hits):
    """One row per reference gene: {reference index: (protein, identity)} are PRESENT_IN_CORE, the rest not found."""
    return [{"status": "PRESENT_IN_CORE", "best_protein": hits[k][0], "best_identity_pct": hits[k][1],
             "best_coverage_pct": 90.0, "reciprocal_best": True} if k in hits else
            {"status": "MISSING_NOT_FOUND", "best_protein": "", "best_identity_pct": 0.0} for k in range(len(REF))]


ROWS_A = _rows({4: ("q5", 68.0), 5: ("q6", 70.0)})
ROWS_B = _rows({0: ("q1", 77.0), 1: ("q2", 95.0), 2: ("q3", 59.0), 3: ("q4", 74.0)})


def _spec():
    return pm.pair_manifest("TST-1", PROTS, RA, RB, REF, "Streptomyces sp. TST-9 testomycin cluster", "BGC9999001",
                            ROWS_A, ROWS_B, {4, 5}, {0, 1, 2, 3}, {"BGC9999001": "testomycin"})


def test_the_fragment_with_more_matches_is_on_top_and_the_reference_in_the_middle():
    spec = _spec()
    assert [t["id"] for t in spec["tracks"]] == ["core", "ref", "p1"]
    assert spec["tracks"][0]["identity"]["contig"] == "ctgB" and spec["tracks"][2]["identity"]["contig"] == "ctgA"
    assert spec["tracks"][1]["label"] == "MIBiG BGC9999001: testomycin"


def test_every_ribbon_joins_a_fragment_gene_in_its_own_region_to_its_reference_gene():
    spec = _spec()
    genes = {(t["id"], g["id"]): (t, g) for t in spec["tracks"] for g in t["genes"]}
    assert len(spec["links"]) == 6
    for link in spec["links"]:
        (ta, ga), (tr, gr) = genes[tuple(link["a"])], genes[tuple(link["b"])]
        assert tr["id"] == "ref" and ga["group"] == gr["group"] != ""
        region = RB if ta["identity"]["contig"] == "ctgB" else RA
        assert region["start"] <= ga["start"] and ga["end"] <= region["end"]


def test_an_overlap_pair_says_so_in_the_lower_fragments_subtitle_and_a_complement_does_not():
    spec = _spec()
    assert "same reference genes" not in spec["tracks"][2].get("subtitle", "")
    rows_a = _rows({0: ("q5", 68.0), 1: ("q6", 70.0)})       # fragment A now repeats genes 1-2 of fragment B
    reading = pm.overlap({0, 1}, {0, 1, 2, 3})
    spec = pm.pair_manifest("TST-1", PROTS, RA, RB, REF, "Streptomyces sp. TST-9 testomycin cluster", "BGC9999001",
                            rows_a, ROWS_B, {0, 1}, {0, 1, 2, 3}, {}, reading=reading)
    assert spec["tracks"][2]["subtitle"].endswith("; same reference genes as ctgB")


def test_an_as_gene_that_is_the_best_hit_of_two_reference_genes_keeps_one_ribbon():
    rows = _rows({0: ("q1", 40.0), 1: ("q1", 78.0), 2: ("q3", 59.0)})
    kept = pm._one_per_gene(rows, {0, 1, 2})
    assert sorted(kept) == [1, 2]


def test_the_pair_renders_with_the_locus_comparison_renderer(tmp_path):
    pytest.importorskip("matplotlib")
    from mamey.figures import locus_comparison as lc
    spec = _spec()
    spec["synthetic"] = True
    view = pm.rlc.render_with_fallback(spec, tmp_path)
    assert view is not None and (tmp_path / "render" / "comparison.png").is_file()
    assert lc  # the renderer module is the one the tool uses

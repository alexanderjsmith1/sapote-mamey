"""FA3 / ADD-03 — first-class Reference-Dark novelty prior (per-BGC, NON-RANKING).

Promotes the reference-dark determination (today re-derived ad hoc, with two conflated
definitions) to one authoritative, basis-tagged field computed once from the per-gene MIBiG
recognizability (`*_3_mibig_profile.csv`) + region-level KCB (`*_4_triage_board.csv`).

Contract asserted here: three-way classification with a denominator-bearing basis, and the
NON-RANKING guarantee (the module never imports/reads/writes AB/AF/novelty/lead_tier).

Standalone: python3 tests/test_reference_dark_prior.py
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey import reference_dark_prior as rdp


# ---- pure classifier -----------------------------------------------------------

def test_empty_no_kcb_is_reference_dark():
    cls, basis = rdp.classify_reference_dark(
        query_gene_count=23, recognizable_gene_count=0, recognizable_gene_fraction=0.0,
        dominant_mibig_accession="", dominant_convergence_tier="UNASSESSED",
        interpretation_class="NO_MIBIG_PROTEIN_HITS", kcb_top="")
    assert cls == rdp.REFERENCE_DARK
    assert "0/23 genes" in basis  # denominator carried


def test_empty_pergene_but_kcb_anchor_is_partial():
    # region-level KCB anchor with zero per-gene recognizability = the "unresolved" middle case
    cls, basis = rdp.classify_reference_dark(
        query_gene_count=15, recognizable_gene_count=0, recognizable_gene_fraction=0.0,
        dominant_mibig_accession="", dominant_convergence_tier="UNASSESSED",
        interpretation_class="NO_MIBIG_PROTEIN_HITS",
        kcb_top="BGC0000112.1 | neocarzinostatin | knownclusterblast #1")
    assert cls == rdp.PARTIALLY_CHARACTERIZED
    assert "kcb_region_anchor_only" in basis and "BGC0000112" in basis


def test_dense_anchor_is_well_characterized():
    cls, basis = rdp.classify_reference_dark(
        query_gene_count=7, recognizable_gene_count=5, recognizable_gene_fraction=0.7143,
        dominant_mibig_accession="BGC0001211", dominant_convergence_tier="H3_MULTI_GENE",
        interpretation_class="KNOWN_ANCHORED", kcb_top="BGC0001211.5 | albachelin | #1")
    assert cls == rdp.WELL_CHARACTERIZED
    assert "5/7 genes" in basis and "BGC0001211" in basis


def test_sparse_anchor_is_partial():
    cls, basis = rdp.classify_reference_dark(
        query_gene_count=88, recognizable_gene_count=30, recognizable_gene_fraction=0.3409,
        dominant_mibig_accession="BGC0000112", dominant_convergence_tier="H3_MULTI_GENE",
        interpretation_class="KNOWN_ANCHORED", kcb_top="")
    assert cls == rdp.PARTIALLY_CHARACTERIZED
    assert "sparse" in basis and "30/88 genes" in basis


def test_class_mismatch_never_well_even_if_dense():
    # a dense but class-mismatched anchor must NOT be called well-characterized
    cls, basis = rdp.classify_reference_dark(
        query_gene_count=10, recognizable_gene_count=8, recognizable_gene_fraction=0.8,
        dominant_mibig_accession="BGC0000999", dominant_convergence_tier="CAUTION_CLASS_MISMATCH",
        interpretation_class="KNOWN_ANCHORED", kcb_top="")
    assert cls == rdp.PARTIALLY_CHARACTERIZED
    assert "class_mismatch" in basis


def test_note_and_contract():
    dark, _ = rdp.classify_reference_dark(1, 0, 0.0, "", "", "NO_MIBIG_PROTEIN_HITS", "")
    well, _ = rdp.classify_reference_dark(4, 4, 1.0, "BGC0001211", "H2_STRONG_FAMILY", "KNOWN_ANCHORED", "")
    assert dark == rdp.REFERENCE_DARK and well == rdp.WELL_CHARACTERIZED
    assert "novelty PRIOR" in rdp._note_for(dark)
    assert "not proof" in rdp._note_for(well)


# ---- CSV round-trip on a tiny fixture ------------------------------------------

_PROFILE_HEADER = ("bgc_id,query_gene_count,recognizable_gene_count,recognizable_gene_fraction,"
                   "recognizable_min_pct_identity,median_pct_identity,distinct_mibig_refs,"
                   "interpretation_class,dominant_mibig_accession,dominant_mibig_compound,"
                   "dominant_distinct_query_genes,dominant_convergence_tier,report_only_contract")


def _write_fixture(tmp: Path):
    prof = tmp / "AS-TEST_3_mibig_profile.csv"
    prof.write_text("\n".join([
        _PROFILE_HEADER,
        "BGC001,7,5,0.7143,30,91,21,KNOWN_ANCHORED,BGC0001211,albachelin,4,H3_MULTI_GENE,REPORT_ONLY_NO_SCORING",
        "BGC002,88,30,0.3409,30,57,50,KNOWN_ANCHORED,BGC0000112,neocarzinostatin,10,H3_MULTI_GENE,REPORT_ONLY_NO_SCORING",
        "BGC003,23,0,0.0,,,0,NO_MIBIG_PROTEIN_HITS,,,0,UNASSESSED,REPORT_ONLY_NO_SCORING",
    ]) + "\n", encoding="utf-8")
    board = tmp / "AS-TEST_4_triage_board.csv"
    board.write_text("\n".join([
        "Rank,BGC_ID,KCB_top",
        "1,BGC001,BGC0001211.5 | albachelin | #1",
        "2,BGC002,",
        "3,BGC003,",  # BGC003 truly dark (no KCB anchor)
    ]) + "\n", encoding="utf-8")
    return prof, board


def test_compute_for_package_three_way_and_csv():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _write_fixture(tmp)
        rows, out = rdp.compute_for_package(tmp, write=True)
        by = {r["bgc_id"]: r for r in rows}
        assert by["BGC001"]["reference_dark_class"] == rdp.WELL_CHARACTERIZED
        assert by["BGC002"]["reference_dark_class"] == rdp.PARTIALLY_CHARACTERIZED
        assert by["BGC003"]["reference_dark_class"] == rdp.REFERENCE_DARK
        assert rdp.summarize(rows) == {rdp.REFERENCE_DARK: 1,
                                       rdp.PARTIALLY_CHARACTERIZED: 1,
                                       rdp.WELL_CHARACTERIZED: 1}
        # CSV was written with the documented header
        assert out.exists()
        first = out.read_text(encoding="utf-8").splitlines()[0]
        assert first.split(",") == rdp.CSV_HEADERS


def test_non_ranking_module_has_no_scoring_dependency():
    # the NON-RANKING guarantee: the module must not pull in the scorer or emit AB/AF/tier fields
    import inspect
    src = inspect.getsource(rdp)
    assert "import mamey.scoring" not in src and "from mamey.scoring" not in src
    for banned in ("lead_tier", "AB_auto", "AF_auto"):
        assert banned not in "".join(rdp.CSV_HEADERS)
    assert rdp.REPORT_ONLY_CONTRACT.startswith("NON_RANKING")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")

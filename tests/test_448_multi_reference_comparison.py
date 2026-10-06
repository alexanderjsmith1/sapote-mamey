"""Card 9: multi-reference comparison (one AS locus against its best MIBiG or reference-genome loci)."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytest.importorskip("matplotlib")


def _load():
    sys.path.insert(0, str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("mrc", ROOT / "tools" / "multi_reference_comparison.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hit(q, ref, i, pident, bits, cov=90):
    return {"qseqid": q, "sseqid": f"{ref}|{i}", "pident": str(pident), "qcovhsp": str(cov), "bitscore": str(bits)}


def test_pairs_are_one_to_one_by_bitscore():
    mrc = _load()
    hits = [_hit("q1", "BGC1", 0, 60, 300), _hit("q2", "BGC1", 0, 70, 200),  # q2 loses gene 0 to q1
            _hit("q2", "BGC1", 1, 55, 150), _hit("q3", "BGC1", 2, 50, 100)]
    (acc, pairs), = mrc.rank_references(hits, 4)
    assert acc == "BGC1"
    assert [(q, i) for q, i, *_ in pairs] == [("q1", 0), ("q2", 1), ("q3", 2)]


def test_ranked_by_genes_then_bitscore_and_thresholds_apply():
    mrc = _load()
    lo = mrc.rc.DISCOVERY_MIN_ID - 1
    hits = [_hit("q1", "A", 0, 60, 100), _hit("q2", "A", 1, 60, 100),                      # 2 genes, 200
            _hit("q1", "B", 0, 60, 900), _hit("q2", "B", 1, 60, 900),                      # 2 genes, 1800
            _hit("q1", "C", 0, 60, 50), _hit("q2", "C", 1, 60, 50), _hit("q3", "C", 2, 60, 50),  # 3 genes
            _hit("q1", "D", 0, 60, 999), _hit("q2", "D", 1, lo, 999),                       # one hit under the identity bar
            _hit("q1", "E", 0, 60, 999), _hit("q2", "E", 1, 60, 999, cov=10)]               # one hit under the coverage bar
    order = [a for a, _ in mrc.rank_references(hits, 4)]
    assert order == ["C", "B", "A"]  # D and E keep one gene each, below the two-gene minimum


def _m(n_refs, source="reference-genome antiSMASH regions"):
    return {"label": "AS-1", "bgc": "BGC001", "segments": [("NODE_1 · BGC001", [])], "source": source,
            "refs": [{"accession": f"R{k}", "also": []} for k in range(n_refs)], "scale_kb": 5}


def test_caption_reads_right_for_one_and_several_references():
    mrc = _load()
    one = mrc.caption(_m(1), [], [])
    assert "compared with its best-matching reference-genome antiSMASH region." in one
    assert "its 1 " not in one
    four = mrc.caption(_m(4, "MIBiG 4.0 clusters"), [], [])
    assert "compared with its 4 best-matching MIBiG 4.0 clusters." in four


def test_one_compound_under_its_full_name_its_bracketed_abbreviation_and_the_abbreviation_alone():
    mrc = _load()
    full = mrc.compound_keys("Ethylenediaminesuccinic acid hydroxyarginine")
    both = mrc.compound_keys("ethylenediaminesuccinic acid hydroxyarginine (EDHA)")
    abbr = mrc.compound_keys("EDHA")
    assert full & both and both & abbr        # build() chains them into one group
    assert not (mrc.compound_keys("lydicamycin") & both)
    assert mrc.compound_keys("Pekiskomycin ") == mrc.compound_keys("pekiskomycin")


def test_overlapping_texts_are_recorded_and_separate_ones_are_not():
    mrc = _load()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(4, 2))
    a = fig.text(.1, .5, "BGC0002568: a long heading", fontsize=11)
    b = fig.text(.15, .52, "6 of 10 locus genes", fontsize=9)      # on top of the first
    c = fig.text(.1, .1, "far away", fontsize=9)
    fig.canvas.draw()
    rnd = fig.canvas.get_renderer()
    hits = mrc.text_overlaps([a, b, c], rnd)
    assert hits == [["BGC0002568: a long heading", "6 of 10 locus genes"]]
    assert mrc.text_overlaps([a, b, c], rnd, skip=[b]) == []
    plt.close(fig)

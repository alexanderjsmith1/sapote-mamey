"""RG-GMCI read-depth fields and the optional DIAMOND residue-tiling layer (both report-only).

Synthetic ids only (TST-*). The DIAMOND round trip runs only when a `diamond` binary is available
($RGGMCI_DIAMOND or PATH); everything else is pure Python.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from mamey import parsers, rggmci
from mamey.rggmci import contig_depth, depth_fields
from mamey.residue_tiling import (_cds_proteins, add_residue_tiling, compare_sides, find_diamond, mibig_accession,
                                  place_side)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "rggmci_public_VWPH00000000.1_subset.zip"


def test_contig_depth_reads_spades_names_only():
    assert contig_depth("NODE_7_length_52011_cov_41.25") == 41.25
    assert contig_depth("NODE_7_length_52011_cov_41") == 41.0
    assert contig_depth("TST-1_contig_3") is None
    assert contig_depth("NODE_7_length_52011_cov_1.2.3") is None
    assert contig_depth("") is None


def test_depth_fields_flag_but_never_score():
    ok = depth_fields("NODE_1_length_9_cov_40.0", "NODE_2_length_9_cov_36.0")
    assert ok["depth_ratio"] == 0.9 and ok["depth_flag"] == "DEPTH_CONSISTENT"
    bad = depth_fields("NODE_1_length_9_cov_90.0", "NODE_2_length_9_cov_30.0")
    assert bad["depth_ratio"] == 0.333 and bad["depth_flag"] == "DEPTH_MISMATCH"
    none = depth_fields("TST-1_ctg1", "NODE_2_length_9_cov_30.0")
    assert none["depth_ratio"] == "" and none["depth_flag"] == "DEPTH_UNAVAILABLE" and none["depth_b"] == 30.0


def test_ranked_pairs_carry_depth_fields_and_no_residue_fields_by_default():
    bgcs = parsers.parse_bgcs_from_zip(str(FIXTURE), json_mode="off")
    res = rggmci.run_rggmci(str(FIXTURE), bgcs)
    assert res["ranked_pairs"]
    for p in res["ranked_pairs"]:
        assert {"depth_a", "depth_b", "depth_ratio", "depth_flag"} <= set(p)
        assert not any(k.startswith("residue") for k in p)
    assert "residue_tiling_status" not in res


def hsp(q, s, qs, qe, ss, se, bits, ident=60.0):
    return (q, s, ident, qs, qe, ss, se, bits)


def test_two_pieces_of_one_gene_are_complementary():
    # TST-A carries residues 1-1200 of the reference PKS, TST-B residues 1300-2600: one gene cut by a break
    a = place_side([hsp("TST-A|1", "BGC9999999|1", 1, 1200, 1, 1200, 1500)])
    b = place_side([hsp("TST-B|1", "BGC9999999|1", 1, 1300, 1300, 2600, 1600)])
    c = compare_sides(a, b)
    assert c["class"] == "COMPLEMENTARY" and c["residue_overlap"] == 0.0


def test_two_copies_of_one_machinery_overlap():
    a = place_side([hsp("TST-A|1", "BGC9999999|1", 1, 900, 100, 1000, 1200)])
    b = place_side([hsp("TST-B|1", "BGC9999999|1", 1, 900, 120, 1020, 1100)])
    assert compare_sides(a, b)["class"] == "OVERLAPPING"


def test_a_module_is_placed_once_not_against_every_similar_module():
    # one 450-aa module matches reference modules at 1-450 (best) and 2001-2450; only the best placement counts,
    # so the other side's true piece at 2001-2450 is not overlapped
    a = place_side([hsp("TST-A|1", "BGC9999999|1", 1, 450, 1, 450, 700),
                    hsp("TST-A|1", "BGC9999999|1", 1, 450, 2001, 2450, 500)])
    assert [(x[1], x[2]) for x in a] == [(1, 450)]
    b = place_side([hsp("TST-B|1", "BGC9999999|1", 1, 450, 2001, 2450, 800)])
    assert compare_sides(a, b)["class"] == "COMPLEMENTARY"


def test_small_matches_are_thin():
    a = place_side([hsp("TST-A|1", "BGC9999999|1", 1, 200, 1, 200, 300)])
    b = place_side([hsp("TST-B|1", "BGC9999999|1", 1, 200, 400, 600, 300)])
    assert compare_sides(a, b)["class"] == "THIN"


def test_mibig_accession_strips_version_and_index():
    assert mibig_accession("BGC0000996.5") == "BGC0000996"
    assert mibig_accession("BGC0000001|12") == "BGC0000001"
    assert mibig_accession("NZ_CP000001.1") == ""


GBK = """LOCUS       TST-1                   900 bp    DNA     linear   UNK
FEATURES             Location/Qualifiers
     region          1..900
                     /product="T1PKS"
     CDS             1..300
                     /locus_tag="TST_0001"
                     /translation="MSTNPKLLAA
                     GGWQ"
     CDS             complement(400..900)
                     /gene="tstB"
                     /translation="MKKLLV*"
ORIGIN
        1 atg
//
"""


def test_cds_proteins_joins_wrapped_translations():
    assert _cds_proteins(GBK) == [("TST_0001", "MSTNPKLLAAGGWQ"), ("tstB", "MKKLLV")]


def test_missing_diamond_leaves_pairs_untested(tmp_path, monkeypatch):
    monkeypatch.delenv("RGGMCI_DIAMOND", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    bgcs = parsers.parse_bgcs_from_zip(str(FIXTURE), json_mode="off")
    before = rggmci.run_rggmci(str(FIXTURE), bgcs)
    after = rggmci.run_rggmci(str(FIXTURE), bgcs, diamond_db=tmp_path / "none.dmnd", residue_scope="all")
    assert after["residue_tiling_status"]["state"] == "DIAMOND_NOT_FOUND"
    for x, y in zip(before["ranked_pairs"], after["ranked_pairs"]):
        assert y["residue_tiling"] == "NOT_TESTED"
        assert {k: v for k, v in y.items() if not k.startswith("residue")} == x


def test_bad_scope_is_refused():
    with pytest.raises(ValueError):
        add_residue_tiling({"ranked_pairs": []}, FIXTURE, [], {}, "x.dmnd", scope="everything")


@pytest.mark.skipif(not find_diamond(), reason="no diamond binary ($RGGMCI_DIAMOND or PATH)")
def test_diamond_round_trip_on_a_synthetic_split_gene(tmp_path):
    """A real DIAMOND run: a 1,000-aa synthetic reference, cut in two, is complementary; a duplicate overlaps."""
    import random
    from mamey.residue_tiling import _run_diamond
    rnd = random.Random(7)
    ref = "M" + "".join(rnd.choice("ACDEFGHIKLMNPQRSTVWY") for _ in range(999))
    faa = tmp_path / "ref.faa"
    faa.write_text(f">BGC9999999|1\n{ref}\n")
    subprocess.run([find_diamond(), "makedb", "--in", str(faa), "-d", str(tmp_path / "ref"), "--quiet"], check=True)
    q = tmp_path / "q.faa"
    q.write_text(f">TST-A|1\n{ref[:480]}\n>TST-B|1\n{ref[520:]}\n>TST-C|1\n{ref[:480]}\n")
    rows = _run_diamond(find_diamond(), str(tmp_path / "ref.dmnd"), q, tmp_path / "out.tsv", 1)
    side = lambda name: place_side([h for h in rows if h[0] == name])
    assert compare_sides(side("TST-A|1"), side("TST-B|1"))["class"] == "COMPLEMENTARY"
    assert compare_sides(side("TST-A|1"), side("TST-C|1"))["class"] == "OVERLAPPING"

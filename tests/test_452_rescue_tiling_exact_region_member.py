"""P300-065: diagnostic deep tiling binds each BGC to its exact clusterblast region member.

Two regions on one contig carry disjoint reference hits; the old prefix glob gave both regions the
first file's hits. Synthetic clusterblast text only.
"""
import json
import os

from mamey import diagnostic_rescue as DR
from mamey import package_addons as PA


def _cb_text(acc, subjects):
    rows = "\n".join(f"q{i}_1\t{s}\t60\t400\t90\t1e-50" for i, s in enumerate(subjects, 1))
    return ("ClusterBlast scores\n\n>>\n1. %s\nSource: synthetic reference\nType: other\n"
            "Cumulative BLAST score: 2000\n\nTable of Blast hits (query gene, subject gene, %%identity, "
            "blast score, %%coverage, e-value):\n%s\n" % (acc, rows))


def _write(d, name, acc, subjects):
    (d / name).write_text(_cb_text(acc, subjects), encoding="utf-8")


def _subjects(cb):
    return sorted(h["subject"] for ref in cb.values() for h in ref["hits"])


def test_two_regions_on_one_contig_get_their_own_hits(tmp_path):
    _write(tmp_path, "NODE_7_c1.txt", "REF_ONE", ["A_RS10", "A_RS20"])
    _write(tmp_path, "NODE_7_c2.txt", "REF_TWO", ["B_RS10", "B_RS20"])
    assert _subjects(DR._cb_for_node(str(tmp_path), "NODE_7", 1)) == ["A_RS10", "A_RS20"]
    assert _subjects(DR._cb_for_node(str(tmp_path), "NODE_7", 2)) == ["B_RS10", "B_RS20"]
    assert _subjects(DR._cb_for_node(str(tmp_path), "NODE_7", "2")) == ["B_RS10", "B_RS20"]


def test_zero_padded_region_member_matches(tmp_path):
    _write(tmp_path, "NODE_7_c003.txt", "REF_ONE", ["A_RS10"])
    assert _subjects(DR._cb_for_node(str(tmp_path), "NODE_7", 3)) == ["A_RS10"]


def test_missing_member_and_prefix_collision_are_held(tmp_path):
    _write(tmp_path, "NODE_7_c1.txt", "REF_ONE", ["A_RS10"])
    _write(tmp_path, "NODE_7_length_99_c2.txt", "REF_TWO", ["B_RS10"])
    assert DR._cb_for_node(str(tmp_path), "NODE_7", 2) == {}   # no exact NODE_7 region 2 member
    assert DR._cb_for_node(str(tmp_path), "NODE_7", "x") == {}


def test_legacy_contig_only_locator_is_held_when_ambiguous(tmp_path):
    _write(tmp_path, "NODE_7_c1.txt", "REF_ONE", ["A_RS10"])
    _write(tmp_path, "NODE_7_c2.txt", "REF_TWO", ["B_RS10"])
    assert DR._cb_for_node(str(tmp_path), "NODE_7") == {}


def test_legacy_contig_only_locator_with_one_member_unchanged(tmp_path):
    _write(tmp_path, "NODE_9_c4.txt", "REF_ONE", ["A_RS10"])
    assert _subjects(DR._cb_for_node(str(tmp_path), "NODE_9")) == ["A_RS10"]
    tiling = DR.make_tiling_fn(str(tmp_path), lambda bid: "NODE_9")
    assert tiling("BGC001", "BGC002")["verdict"] == "RECONSTRUCTION_NOT_SUPPORTED_HIGH_REFERENCE_OVERLAP"


def test_tiling_fn_accepts_exact_locator_tuple(tmp_path):
    _write(tmp_path, "NODE_7_c1.txt", "REF_ONE", ["A_RS10", "A_RS20"])
    _write(tmp_path, "NODE_7_c2.txt", "REF_TWO", ["B_RS10"])
    _write(tmp_path, "NODE_8_c1.txt", "REF_TWO", ["B_RS30"])
    loc = {"BGC001": ("NODE_7", 1), "BGC002": ("NODE_7", 2), "BGC003": ("NODE_8", 1)}
    tiling = DR.make_tiling_fn(str(tmp_path), loc.get)
    # BGC002 is region 2: it shares REF_TWO with BGC003, and nothing with region 1
    assert tiling("BGC002", "BGC003")["best_scaffold"] == "REF_TWO"
    assert tiling("BGC001", "BGC003")["verdict"] == "NO_SHARED_REFERENCE"


def test_emit_rescue_4b_uses_manifest_region_number(tmp_path):
    # Two arms sit on regions 1 and 2 of one contig, each pairing with the same core. Each region tiles
    # a different reference, so a contig-level first-file choice cannot give both pairs their own
    # scaffold, whatever order the files are listed in.
    pkg = tmp_path / "pkg"
    pkg.mkdir()

    def pair(arm):
        return {"pair": f"{arm}+BGC005", "bgc_a": arm, "bgc_b": "BGC005",
                "contig_a": "NODE_7", "contig_b": "NODE_8", "products_a": "halogenated",
                "products_b": "indole", "edge_a": "Edge", "edge_b": "Edge"}

    man = {"strain_id": "TEST-STRAIN",
           "bgcs": [{"bgc_id": "BGC001", "contig": "NODE_7", "region_number": 1},
                    {"bgc_id": "BGC002", "contig": "NODE_7", "region_number": 2},
                    {"bgc_id": "BGC005", "contig": "NODE_8", "region_number": 1}],
           "source_scans": {"cctt": {"per_bgc": {"BGC001": ["T43-HAL_halogenase"],
                                                 "BGC002": ["T43-HAL_halogenase"],
                                                 "BGC005": ["T43-IDC_indolocarbazole"]}}}}
    (pkg / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    (pkg / "TEST-STRAIN_4A_RGGMCI_full.json").write_text(
        json.dumps({"ranked_pairs": [pair("BGC001"), pair("BGC002")]}), encoding="utf-8")
    cb = tmp_path / "clusterblast"
    cb.mkdir()
    _write(cb, "NODE_7_c1.txt", "REF_ONE", ["A_RS10", "A_RS20"])
    _write(cb, "NODE_7_c2.txt", "REF_TWO", ["B_RS10", "B_RS20"])
    # the core's region hits both references (one ">>" block each)
    second_block = _cb_text("REF_TWO", ["B_RS30", "B_RS40", "B_RS50"]).split(">>", 1)[1]
    (cb / "NODE_8_c1.txt").write_text(_cb_text("REF_ONE", ["A_RS30", "A_RS40", "A_RS50"])
                                      + ">>" + second_block, encoding="utf-8")
    leads = {l["pair"]: l for l in PA.emit_rescue_4b(str(pkg), clusterblast_dir=str(cb))}
    assert leads["BGC001+BGC005"]["shared_scaffold"] == "REF_ONE"
    assert leads["BGC002+BGC005"]["shared_scaffold"] == "REF_TWO"
    assert leads["BGC001+BGC005"]["reference_genes_covered"] == 5
    assert os.path.exists(pkg / "TEST-STRAIN_4B_Diagnostic_Rescue_Tiling.csv")

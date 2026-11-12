"""Tests for tools/sequence_group_sharing_venn.py."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "sequence_group_sharing_venn.py"
spec = importlib.util.spec_from_file_location("sgsv", TOOL)
sgsv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sgsv)

MAP = {"Src1a": "Set A", "Src1b": "Set A", "Src1c": "Set A", "Src2a": "Set B", "Src2b": "Set B", "Src3a": "Set C"}
_MAPFILE = Path(__import__("tempfile").mkdtemp()) / "collection_map.tsv"
_MAPFILE.write_text("source_group\tcollection\n" + "".join(f"{k}\t{v}\n" for k, v in MAP.items()))
MAPARGS = ["--collection-map", str(_MAPFILE)]

COLS = ["genus", "threshold", "floor", "group_id", "isolate", "source_group", "no_eligible_comparison"]


def write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(COLS)
        w.writerows(rows)
    return path


def rows():
    g = ("Streptomyces", "99", "500")
    return [
        (*g, "G1", "A1", "Src1a", "False"), (*g, "G1", "A2", "Src2a", "False"),   # set A + set B
        (*g, "G2", "A3", "Src1b", "False"),                                                  # set A only
        (*g, "G3", "A4", "Src3a", "False"), (*g, "G3", "A5", "Src2b", "False"),
        (*g, "G3", "A6", "Src1c", "False"),                                              # all three
        (*g, "G4", "A7", "Src3a", "True"),                                             # excluded
    ]


def test_anchors_each_lie_in_their_region():
    assert sgsv.anchors_ok()


def test_regions_count_groups_and_whole_groups_of_isolates():
    res = sgsv.count_regions([dict(zip(COLS, r)) for r in rows()], MAP)
    assert res["regions"][(0, 1)] == {"groups": 1, "isolates": 2, "group_ids": ["G1"]}
    assert res["regions"][(0,)]["isolates"] == 1
    assert res["regions"][(0, 1, 2)]["isolates"] == 3
    assert res["regions"][(1, 2)]["groups"] == 0
    assert res["excluded"] == ["A7"]
    assert (res["groups"], res["isolates"]) == (3, 6)
    assert res["per_collection"] == {"Set A": 3, "Set B": 2, "Set C": 1}


def test_unmapped_source_and_duplicate_isolate_stop(tmp_path):
    bad = [dict(zip(COLS, r)) for r in rows()] + [dict(zip(COLS, ("Streptomyces", "99", "500", "G9", "A9", "SrcX", "False")))]
    with pytest.raises(SystemExit, match="no collection"):
        sgsv.count_regions(bad, MAP)
    dup = [dict(zip(COLS, r)) for r in rows()] + [dict(zip(COLS, ("Streptomyces", "99", "500", "G2", "A1", "Src1b", "False")))]
    with pytest.raises(SystemExit, match="more than once"):
        sgsv.count_regions(dup, MAP)


def test_no_comparable_isolates_is_not_drawn(tmp_path):
    m = write(tmp_path / "m.tsv", [("Streptomyces", "99", "500", "G1", "A1", "Src1b", "True")])
    with pytest.raises(SystemExit, match="not a biological zero"):
        sgsv.main(MAPARGS + ["--membership", str(m), "--genus", "Streptomyces", "--threshold", "99", "--floor", "500",
                   "--outdir", str(tmp_path / "o")])


def test_end_to_end_outputs_and_check_table(tmp_path):
    m = write(tmp_path / "m.tsv", rows())
    table = tmp_path / "t.tsv"
    table.write_text(FULL_TABLE)
    out = tmp_path / "o"
    assert sgsv.main(MAPARGS + ["--membership", str(m), "--genus", "Streptomyces", "--threshold", "99", "--floor", "500",
                      "--check-table", str(table), "--outdir", str(out)]) == 0
    stem = "Streptomyces_16S_sharing_99pct_complete_linkage_floor500"
    for suffix in (".png", ".svg", ".pdf", "_plot_only.png", "_CAPTION.md", "_plotted.tsv", "_receipt.json"):
        assert (out / f"{stem}{suffix}").exists(), suffix
    receipt = json.loads((out / f"{stem}_receipt.json").read_text())
    assert receipt["excluded_no_eligible_comparison"] == ["A7"]
    assert "no group of that kind among the isolates compared" in (out / f"{stem}_CAPTION.md").read_text()
    table.write_text(FULL_TABLE.replace("Set A\t1\t1\n", "Set A\t2\t1\n"))
    with pytest.raises(SystemExit, match="counts differ"):
        sgsv.main(MAPARGS + ["--membership", str(m), "--genus", "Streptomyces", "--threshold", "99", "--floor", "500",
                   "--check-table", str(table), "--outdir", str(tmp_path / "o2")])


FULL_TABLE = ("combination\tsequence_groups\tisolates_in_those_groups\n"
              "Set A\t1\t1\nSet B\t0\t0\nSet C\t0\t0\nSet A | Set B\t1\t2\n"
              "Set A | Set C\t0\t0\nSet B | Set C\t0\t0\nSet A | Set B | Set C\t1\t3\n")
ARGS = ["--genus", "Streptomyces", "--threshold", "99", "--floor", "500"]


@pytest.mark.parametrize("flag", ["true", "", "TRUE ", "yes"])
def test_invalid_no_comparison_flag_stops(flag):
    bad = [dict(zip(COLS, r)) for r in rows()]
    bad[0]["no_eligible_comparison"] = flag
    with pytest.raises(SystemExit, match="exactly True or False"):
        sgsv.count_regions(bad, MAP)


def test_blank_isolate_or_group_stops():
    bad = [dict(zip(COLS, r)) for r in rows()]
    bad[1]["group_id"] = " "
    with pytest.raises(SystemExit, match="blank isolate or group_id"):
        sgsv.count_regions(bad, MAP)


def test_check_table_must_cover_all_seven_regions_once(tmp_path):
    m = write(tmp_path / "m.tsv", rows())
    partial = tmp_path / "p.tsv"
    partial.write_text("combination\tsequence_groups\tisolates_in_those_groups\n")
    with pytest.raises(SystemExit, match="all seven regions"):
        sgsv.main(MAPARGS + ["--membership", str(m), *ARGS, "--check-table", str(partial), "--outdir", str(tmp_path / "o1")])
    dup = tmp_path / "d.tsv"
    dup.write_text(FULL_TABLE + "Set A\t1\t1\n")
    with pytest.raises(SystemExit, match="more than once"):
        sgsv.main(MAPARGS + ["--membership", str(m), *ARGS, "--check-table", str(dup), "--outdir", str(tmp_path / "o2")])
    full = tmp_path / "f.tsv"
    full.write_text(FULL_TABLE)
    assert sgsv.main(MAPARGS + ["--membership", str(m), *ARGS, "--check-table", str(full), "--outdir", str(tmp_path / "o3")]) == 0


def test_existing_outputs_are_not_overwritten(tmp_path):
    m = write(tmp_path / "m.tsv", rows())
    out = tmp_path / "o"
    assert sgsv.main(MAPARGS + ["--membership", str(m), *ARGS, "--outdir", str(out)]) == 0
    with pytest.raises(SystemExit, match="already exist"):
        sgsv.main(MAPARGS + ["--membership", str(m), *ARGS, "--outdir", str(out)])


def test_input_equal_to_an_output_is_refused_and_kept(tmp_path):
    out = tmp_path / "o"; out.mkdir()
    m = write(out / "Streptomyces_16S_sharing_99pct_complete_linkage_floor500_plotted.tsv", rows())
    before = m.read_bytes()
    with pytest.raises(SystemExit, match="also an input"):
        sgsv.main(MAPARGS + ["--membership", str(m), *ARGS, "--outdir", str(out)])
    assert m.read_bytes() == before


def test_collection_map_duplicates_and_blanks_stop_and_hash_is_recorded(tmp_path):
    dup = tmp_path / "dup.tsv"
    dup.write_text("source_group\tcollection\nSrc1b\tSet A\nSrc1b\tOther\n")
    with pytest.raises(SystemExit, match="more than once"):
        sgsv.load_map(dup)
    blank = tmp_path / "blank.tsv"
    blank.write_text("source_group\tcollection\nSrc1b\t\n")
    with pytest.raises(SystemExit, match="blank"):
        sgsv.load_map(blank)
    good = tmp_path / "map.tsv"
    good.write_text("source_group\tcollection\n" + "".join(f"{k}\t{v}\n" for k, v in MAP.items()))
    m = write(tmp_path / "m.tsv", rows())
    sgsv.main(MAPARGS + ["--membership", str(m), *ARGS, "--collection-map", str(good), "--outdir", str(tmp_path / "o")])
    rec = json.loads((tmp_path / "o" / "Streptomyces_16S_sharing_99pct_complete_linkage_floor500_receipt.json").read_text())
    assert rec["collection_map_sha256"] == sgsv.sha(good)


def test_decimal_thresholds_get_distinct_files(tmp_path):
    out = tmp_path / "o"
    for thr in ("99.9", "99.5"):
        rr = [(g, thr, f) + tuple(rest) for (g, _t, f, *rest) in rows()]
        m = write(tmp_path / f"m{thr}.tsv", rr)
        assert sgsv.main(MAPARGS + ["--membership", str(m), "--genus", "Streptomyces", "--threshold", thr, "--floor", "500", "--outdir", str(out)]) == 0
    names = sorted(p.name for p in out.iterdir())
    assert "Streptomyces_16S_sharing_99p9pct_complete_linkage_floor500.png" in names
    assert "Streptomyces_16S_sharing_99p5pct_complete_linkage_floor500.png" in names
    assert len([n for n in names if n.endswith("_receipt.json")]) == 2


def test_collection_map_is_required(tmp_path):
    m = write(tmp_path / "m.tsv", rows())
    with pytest.raises(SystemExit):
        sgsv.main(["--membership", str(m), *ARGS, "--outdir", str(tmp_path / "o")])


def test_reading_key_names_rule_and_italic_genus():
    key = sgsv.reading_key("Streptomyces", "99.5", "complete")
    assert key.startswith("How to read it\n")
    assert "$\\it{Streptomyces}$" in key and "at least 99.5% identical (complete linkage)" in key
    assert "Groups are not species." in key
    assert sgsv.italic("Genus sp") == "$\\it{Genus\\ sp}$"

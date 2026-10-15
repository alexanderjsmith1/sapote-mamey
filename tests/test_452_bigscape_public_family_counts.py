"""v9.7.452: tools/bigscape_public_family_counts.py counts BiG-SCAPE families per isolate (with a public genome,
MIBiG only, isolate only, parked) from a synthetic BiG-SCAPE 2 output folder. Synthetic IDs only (AS-971..976)."""
from pathlib import Path
import csv
import json
import subprocess
import sys

TOOL = Path(__file__).resolve().parents[1] / "tools/bigscape_public_family_counts.py"
CLUST_HDR = ["Record", "GBK", "Record_Type", "Record_Number", "CC", "Family"]
ANN_HDR = ["Record", "GBK", "Record_Type", "Record_Number", "Class", "Category", "Organism", "Taxonomy", "Description"]

# (family, GBK record, class)
MEMBERS = [
    ("FAM_1", "AS-971_NODE_1.region001", "NRPS"),          # with a public genome
    ("FAM_1", "Pubgenus_alpha_X1__CP1.1.region001", "NRPS"),
    ("FAM_2", "AS-971__NODE_2.region001", "T1PKS"),        # two-underscore staging name; MIBiG only
    ("FAM_2", "BGC0000001.1", "T1PKS"),
    ("FAM_3", "AS-972_NODE_3.region001", "RiPP"),          # isolate only, two isolates
    ("FAM_3", "AS-971_NODE_9.region001", "RiPP"),
    ("FAM_4", "AS-972_NODE_4.region001", "NRPS"),          # singleton
    ("FAM_5", "AS-972_NODE_5.region001", "terpene"),       # parked majority product
    ("FAM_5", "Pubgenus_alpha_X2__CP2.1.region001", "terpene"),
    ("FAM_5", "Pubgenus_alpha_X3__CP3.1.region001", "NRPS"),
    ("FAM_6", "AS-971_NODE_6.region001", "terpene"),       # 1:1 tie broken against the parked class
    ("FAM_6", "Pubgenus_alpha_X4__CP4.1.region001", "T1PKS"),
    ("FAM_7", "Pubgenus_alpha_X5__CP5.1.region001", "NRPS"),  # no isolate: not counted
]


def _tsv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def _bigscape(root, extra_c07=False):
    run = root / "output_files" / "2000-01-01_00-00-00_c0.7"
    _tsv(run / "mix" / "mix_clustering_c0.7.tsv", CLUST_HDR,
         [[f"{g}.gbk_region_1", g, "region", 1, 1, fam] for fam, g, _c in MEMBERS])
    _tsv(run / "record_annotations.tsv", ANN_HDR,
         [[f"{g}.gbk_region_1", g, "region", 1, c, c, "x", "x", "x"] for _f, g, c in MEMBERS])
    if extra_c07:
        (root / "output_files" / "2000-01-02_00-00-00_c0.7").mkdir()
    return root


def _isolates(path, strains=("AS-971", "AS-972")):
    _tsv(path, ["strain", "genus"], [[s, "Testgenus"] for s in strains])
    return path


def _run(tmp_path, *args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], cwd=tmp_path,
                          capture_output=True, text=True, timeout=60)


def _rows(p):
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_counts_per_isolate_and_totals(tmp_path):
    bs = _bigscape(tmp_path / "bs")
    out = tmp_path / "out"
    r = _run(tmp_path, "--run", f"Testgenus={bs}", "--isolates", _isolates(tmp_path / "iso.tsv"), "--out", out)
    assert r.returncode == 0, r.stderr
    iso = {x["strain"]: x for x in _rows(out / "PER_ISOLATE.tsv")}
    assert iso["AS-971"] == dict(strain="AS-971", genus="Testgenus", families="4", in_public="2", not_in_public="2",
                                 a_isolate_only="1", b_mibig_no_public="1", parked="0")
    assert iso["AS-972"] == dict(strain="AS-972", genus="Testgenus", families="2", in_public="0", not_in_public="2",
                                 a_isolate_only="2", b_mibig_no_public="0", parked="1")
    tot = json.loads((out / "TOTALS.json").read_text())
    assert (tot["a_isolate_only"], tot["b_mibig_no_public"], tot["c_with_public"], tot["parked_families"]) == (2, 1, 2, 1)
    fams = {x["family"]: x for x in _rows(out / "FAMILIES.tsv")}
    assert "FAM_7" not in fams                                   # no isolate member
    assert fams["FAM_5"]["group"] == "parked" and fams["FAM_5"]["majority_product"] == "terpene"
    assert fams["FAM_6"]["group"] == "c_with_public" and fams["FAM_6"]["majority_product"] == "T1PKS"
    assert fams["FAM_2"]["group"] == "b_mibig_no_public" and fams["FAM_2"]["mibig"] == "BGC0000001"
    assert fams["FAM_4"]["group"] == "a_isolate_only" and fams["FAM_4"]["n_isolate_regions"] == "1"


def test_drop_regex_removes_records(tmp_path):
    bs = _bigscape(tmp_path / "bs")
    out = tmp_path / "out"
    r = _run(tmp_path, "--run", f"Testgenus={bs}", "--isolates", _isolates(tmp_path / "iso.tsv"),
             "--drop-regex", r"^AS-972_+NODE_4\.", "--out", out)
    assert r.returncode == 0, r.stderr
    assert [x["record"] for x in _rows(out / "DROPPED.tsv")] == ["AS-972_NODE_4.region001"]
    assert {x["strain"]: x["a_isolate_only"] for x in _rows(out / "PER_ISOLATE.tsv")}["AS-972"] == "1"


def test_stop_on_two_cutoff_folders(tmp_path):
    bs = _bigscape(tmp_path / "bs", extra_c07=True)
    r = _run(tmp_path, "--run", f"Testgenus={bs}", "--isolates", _isolates(tmp_path / "iso.tsv"), "--out", tmp_path / "o")
    assert r.returncode != 0
    assert "expected exactly one *_c0.7" in r.stderr
    assert not (tmp_path / "o").exists()


def test_stop_when_listed_isolate_has_no_region(tmp_path):
    bs = _bigscape(tmp_path / "bs")
    r = _run(tmp_path, "--run", f"Testgenus={bs}", "--isolates",
             _isolates(tmp_path / "iso.tsv", ("AS-971", "AS-972", "AS-973")), "--out", tmp_path / "o")
    assert r.returncode != 0 and "AS-973" in r.stderr


def test_stop_when_out_exists(tmp_path):
    bs = _bigscape(tmp_path / "bs")
    (tmp_path / "o").mkdir()
    r = _run(tmp_path, "--run", f"Testgenus={bs}", "--isolates", _isolates(tmp_path / "iso.tsv"), "--out", tmp_path / "o")
    assert r.returncode != 0 and "exists" in r.stderr

"""v9.7.452: tools/bigscape_region_binding_check.py binds staged BiG-SCAPE region files to a Mamey package
inventory by name (one or two underscores) and by Orig. start/end. Synthetic IDs only (AS-974..976, AS-99, AS-998)."""
from pathlib import Path
import csv
import subprocess
import sys

TOOL = Path(__file__).resolve().parents[1] / "tools/bigscape_region_binding_check.py"
REGIONS = [("NODE_1_length_9000_cov_10.5.region001.gbk", 100, 2100), ("NODE_2_length_8000_cov_9.25.region002.gbk", 50, 950)]


def _inventory(d, strain, regions=REGIONS, name=None):
    d.mkdir(parents=True, exist_ok=True)
    with open(d / (name or f"{strain}_2_inventory.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Contig", "antiSMASH_Region", "Source_GBK", "Start", "End"])
        for i, (f, s, e) in enumerate(regions, 1):
            w.writerow([f"BGC{i:03d}", f.split(".region")[0], f"region{i:03d}", f, s, e])


def _stage(d, strain, sep="_", regions=REGIONS, shift=0):
    d.mkdir(parents=True, exist_ok=True)
    for f, s, e in regions:
        (d / f"{strain}{sep}{f}").write_text(
            f"LOCUS       x\nCOMMENT     Orig. start  :: {s + shift}\n            Orig. end    :: {e}\nFEATURES\n")


def _run(tmp_path, *args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args), "--out", tmp_path], cwd=tmp_path,
                          capture_output=True, text=True, timeout=60)


def _result(tmp_path):
    with open(tmp_path / "BINDING_CHECK.tsv", newline="") as fh:
        return {r["strain"]: r for r in csv.DictReader(fh, delimiter="\t")}


def test_match_one_and_two_underscores(tmp_path):
    _inventory(tmp_path / "inv", "AS-974"); _inventory(tmp_path / "inv", "AS-975")
    _stage(tmp_path / "gbk", "AS-974", "_"); _stage(tmp_path / "gbk", "AS-975", "__")
    r = _run(tmp_path, "--inventory-dir", tmp_path / "inv", "--gbk-dir", tmp_path / "gbk",
             "--strain", "AS-974", "--strain", "AS-975")
    assert r.returncode == 0, r.stderr
    res = _result(tmp_path)
    assert res["AS-974"]["result"] == res["AS-975"]["result"] == "MATCH"
    assert res["AS-975"]["staged_regions"] == "2"


def test_coordinate_mismatch(tmp_path):
    _inventory(tmp_path / "inv", "AS-974")
    _stage(tmp_path / "gbk", "AS-974", "__", shift=7)
    r = _run(tmp_path, "--inventory-dir", tmp_path / "inv", "--gbk-dir", tmp_path / "gbk", "--strain", "AS-974")
    assert r.returncode == 1
    row = _result(tmp_path)["AS-974"]
    assert row["result"] == "MISMATCH" and row["coordinate_mismatches"] == "2"


def test_missing_staged_file_is_mismatch(tmp_path):
    _inventory(tmp_path / "inv", "AS-974")
    _stage(tmp_path / "gbk", "AS-974", "_", regions=REGIONS[:1])
    r = _run(tmp_path, "--inventory-dir", tmp_path / "inv", "--gbk-dir", tmp_path / "gbk", "--strain", "AS-974")
    assert r.returncode == 1
    row = _result(tmp_path)["AS-974"]
    assert row["result"] == "MISMATCH" and row["only_in_inventory"] == "1" and row["only_staged"] == "0"


def test_other_strain_prefix_not_captured(tmp_path):
    # AS-99 must not pick up AS-998's files
    _inventory(tmp_path / "inv", "AS-998")
    _stage(tmp_path / "gbk", "AS-998", "_")
    _inventory(tmp_path / "inv2", "AS-99", regions=[])
    r = _run(tmp_path, "--inventory-dir", tmp_path / "inv2", "--gbk-dir", tmp_path / "gbk", "--strain", "AS-99")
    assert r.returncode == 0, r.stderr
    assert _result(tmp_path)["AS-99"]["staged_regions"] == "0"


def test_versioned_inventory_name_is_found(tmp_path):
    _inventory(tmp_path / "inv", "AS-976", name="AS-976_v30_2_inventory.csv")
    _stage(tmp_path / "gbk", "AS-976", "__")
    r = _run(tmp_path, "--inventory-dir", tmp_path / "inv", "--gbk-dir", tmp_path / "gbk", "--strain", "AS-976")
    assert r.returncode == 0, r.stderr
    assert _result(tmp_path)["AS-976"]["inventory"] == "AS-976_v30_2_inventory.csv"


def test_missing_inventory_is_typed_stop(tmp_path):
    (tmp_path / "inv").mkdir(); _stage(tmp_path / "gbk", "AS-974")
    r = _run(tmp_path, "--inventory-dir", tmp_path / "inv", "--gbk-dir", tmp_path / "gbk", "--strain", "AS-974")
    assert r.returncode == 2
    assert "BINDING_CHECK_STOP" in r.stderr and "Traceback" not in r.stderr


def test_missing_gbk_dir_is_typed_stop(tmp_path):
    _inventory(tmp_path / "inv", "AS-974")
    r = _run(tmp_path, "--inventory-dir", tmp_path / "inv", "--gbk-dir", tmp_path / "nope", "--strain", "AS-974")
    assert r.returncode == 2 and "BINDING_CHECK_STOP" in r.stderr

"""Generic count-table collision and decontamination-list controls."""
import csv
from pathlib import Path
import sys
import zipfile
import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import region_table_one_setting as rt

GBK = """LOCUS       NODE_1_length_100_cov_1   5000 bp    DNA
FEATURES             Location/Qualifiers
     region          1..5000
                     /product="NRPS"
ORIGIN
        1 atg
//
"""


def _zip(path, duplicate=False):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("QUERY.json", '{"records":[],"strictness":"loose"}')
        z.writestr("run_a/NODE_1_length_100_cov_1.region001.gbk", GBK)
        if duplicate:
            z.writestr("run_b/NODE_1_length_100_cov_1.region001.gbk", GBK)
    return path


def test_duplicate_region_filename_is_refused(tmp_path, capsys):
    z = _zip(tmp_path / "QUERY.zip", duplicate=True)
    out = tmp_path / "regions.tsv"
    rc = rt.main(["--zips", str(z), "--strictness", "loose", "--out", str(out),
                  "--no-exclusions"])
    assert rc == 2
    assert "duplicate region filename" in capsys.readouterr().err
    assert not out.exists()


def test_zero_drop_refused_unless_reviewed(tmp_path, capsys):
    z = _zip(tmp_path / "QUERY.zip")
    drop = tmp_path / "removed.tsv"
    drop.write_text("NODE_9_length_100_cov_1\n")
    out = tmp_path / "regions.tsv"
    args = ["--zips", str(z), "--strictness", "loose", "--out", str(out),
            "--no-exclusions", "--drop-contigs", f"QUERY={drop}"]
    assert rt.main(args) == 2
    assert "ZERO_DROP_REFUSED" in capsys.readouterr().err
    assert not out.exists()
    assert rt.main(args + ["--allow-zero-drop", "QUERY"]) == 0
    receipt = list(csv.DictReader((tmp_path / "regions_RECEIPT.tsv").open(), delimiter="\t"))
    assert receipt[0]["drop_list_matched"] == "0/1"
    assert receipt[0]["n_dropped"] == "0"


def test_header_is_not_a_contig_or_receipt_denominator(tmp_path):
    z = _zip(tmp_path / "QUERY.zip")
    drop = tmp_path / "removed.tsv"
    drop.write_text("contig\tremoved_reason\nNODE_1_length_100_cov_1\tcontaminant\n")
    out = tmp_path / "regions.tsv"
    assert rt.main(["--zips", str(z), "--strictness", "loose", "--out", str(out),
                    "--no-exclusions", "--drop-contigs", f"QUERY={drop}"]) == 0
    receipt = list(csv.DictReader((tmp_path / "regions_RECEIPT.tsv").open(), delimiter="\t"))
    assert receipt[0]["drop_list_matched"] == "1/1"
    assert receipt[0]["n_dropped"] == "1"


def test_empty_and_duplicate_drop_lists_refused(tmp_path):
    empty = tmp_path / "empty.tsv"
    empty.write_text("contig\tremoved_reason\n")
    valid = tmp_path / "valid.tsv"
    valid.write_text("NODE_1_length_100_cov_1\n")
    with pytest.raises(ValueError, match="no contig IDs"):
        rt.read_drop_lists([f"QUERY={empty}"])
    with pytest.raises(ValueError, match="duplicate --drop-contigs strain"):
        rt.read_drop_lists([f"QUERY={valid}", f"QUERY={valid}"])


def test_corrupt_zip_refused_without_table(tmp_path, capsys):
    bad = tmp_path / "QUERY.zip"
    bad.write_text("not a ZIP")
    out = tmp_path / "regions.tsv"
    assert rt.main(["--zips", str(bad), "--strictness", "loose", "--out", str(out),
                    "--no-exclusions"]) == 2
    assert "File is not a zip file" in capsys.readouterr().err
    assert not out.exists()

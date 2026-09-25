"""region_table_one_setting: a cross-genome region table never mixes antiSMASH strictness."""
from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import region_table_one_setting as rt  # noqa: E402

GBK = """LOCUS       {rec}   5000 bp    DNA     linear   UNK 01-JAN-1980
FEATURES             Location/Qualifiers
     region          1..5000
                     /contig_edge="{edge}"
                     /product="{prod}"
     CDS             1..300
ORIGIN
        1 atg
//
"""


def _zip(path: Path, strictness: str | None, regions: list[tuple[str, str, bool]]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        if strictness:
            zf.writestr(f"{path.stem}.json", '{"records": [], "strictness": "%s"}' % strictness)
        for i, (rec, prod, edge) in enumerate(regions, 1):
            zf.writestr(f"{rec}.region{i:03d}.gbk", GBK.format(rec=rec, prod=prod, edge=str(edge)))
        zf.writestr(f"__MACOSX/._{path.stem}.json", "junk")
    return path


def _rows(p: Path):
    return list(csv.DictReader(open(p), delimiter="\t"))


def test_one_setting_table_and_receipt(tmp_path):
    _zip(tmp_path / "AS-1.zip", "loose", [("NODE_1", "NRPS", False), ("NODE_2", "saccharide", True)])
    _zip(tmp_path / "AS-2.zip", "loose", [("NODE_1", "terpene", False)])
    out = tmp_path / "t.tsv"
    assert rt.main(["--zips", str(tmp_path), "--strictness", "loose", "--out", str(out), "--no-exclusions"]) == 0
    rows = _rows(out)
    assert [(r["strain"], r["products"], r["contig_edge"]) for r in rows] == [
        ("AS-1", "NRPS", "0"), ("AS-1", "saccharide", "1"), ("AS-2", "terpene", "0")]
    assert {r["strictness"] for r in rows} == {"loose"}
    rec = _rows(tmp_path / "t_RECEIPT.tsv")
    assert [r["n_regions"] for r in rec] == ["2", "1"] and all(len(r["sha256"]) == 64 for r in rec)


def test_mixed_strictness_is_refused(tmp_path, capsys):
    _zip(tmp_path / "AS-1.zip", "loose", [("NODE_1", "NRPS", False)])
    _zip(tmp_path / "AS-2.zip", "relaxed", [("NODE_1", "terpene", False)])
    out = tmp_path / "t.tsv"
    assert rt.main(["--zips", str(tmp_path), "--strictness", "loose", "--out", str(out), "--no-exclusions"]) == 2
    assert "AS-2: strictness relaxed" in capsys.readouterr().err
    assert not out.exists()


def test_unknown_strictness_is_refused(tmp_path):
    _zip(tmp_path / "AS-1.zip", None, [("NODE_1", "NRPS", False)])
    assert rt.main(["--zips", str(tmp_path), "--strictness", "loose", "--out", str(tmp_path / "t.tsv"),
                    "--no-exclusions"]) == 2


def test_different_zips_for_one_strain_are_refused_identical_copies_collapse(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    _zip(tmp_path / "a" / "AS-1.zip", "loose", [("NODE_1", "NRPS", False)])
    _zip(tmp_path / "b" / "AS-1.zip", "loose", [("NODE_1", "NRPS", False), ("NODE_9", "PKS", False)])
    assert rt.main(["--zips", str(tmp_path), "--strictness", "loose", "--out", str(tmp_path / "t.tsv"),
                    "--no-exclusions"]) == 2
    (tmp_path / "b" / "AS-1.zip").write_bytes((tmp_path / "a" / "AS-1.zip").read_bytes())
    assert rt.main(["--zips", str(tmp_path), "--strictness", "loose", "--out", str(tmp_path / "t.tsv"),
                    "--no-exclusions"]) == 0
    assert _rows(tmp_path / "t_RECEIPT.tsv")[0]["identical_copies"] == "2"


def test_drop_contigs_removes_regions_and_reports_matches(tmp_path):
    _zip(tmp_path / "AS-810.zip", "loose", [("NODE_1", "NRPS", False), ("NODE_7", "terpene", True)])
    drop = tmp_path / "removed.tsv"
    drop.write_text("NODE_7\tcontaminant\nNODE_99\tcontaminant\n")
    out = tmp_path / "t.tsv"
    assert rt.main(["--zips", str(tmp_path / "AS-810.zip"), "--strictness", "loose", "--out", str(out),
                    "--no-exclusions", "--drop-contigs", f"AS-810={drop}"]) == 0
    assert [r["record"] for r in _rows(out)] == ["NODE_1"]
    rec = _rows(tmp_path / "t_RECEIPT.tsv")[0]
    assert (rec["n_dropped"], rec["drop_list_matched"]) == ("1", "1/2")


def test_drop_list_for_a_missing_strain_is_refused(tmp_path):
    _zip(tmp_path / "AS-1.zip", "loose", [("NODE_1", "NRPS", False)])
    drop = tmp_path / "removed.tsv"
    drop.write_text("NODE_7\n")
    assert rt.main(["--zips", str(tmp_path / "AS-1.zip"), "--strictness", "loose", "--out", str(tmp_path / "t.tsv"),
                    "--no-exclusions", "--drop-contigs", f"AS-810={drop}"]) == 2


def test_hard_excluded_strain_is_dropped_and_recorded(tmp_path):
    _zip(tmp_path / "AS-1.zip", "loose", [("NODE_1", "NRPS", False)])
    _zip(tmp_path / "AS-260.zip", "loose", [("NODE_1", "PKS", False)])
    rows, receipt, problems = rt.build(rt.find_zips([tmp_path]), "loose", {}, {"AS-260"})
    assert problems == [] and {r["strain"] for r in rows} == {"AS-1"}
    assert [r["status"] for r in receipt] == ["kept", "hard-excluded"]

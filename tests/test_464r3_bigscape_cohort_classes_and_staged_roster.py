"""Round 3c: reviewed-subtype rows with missing cells are held; unresolved members are counted beside the
family class; bigscape_prep writes a source-to-member roster with hashes."""
import csv
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_bigscape_cohort_report_and_network_widget_v97435 import fixture, report  # noqa: E402

HEADER = "family_id\treviewed_subtype_code\tfull_name\tplain_language_meaning\tsource_basis\tclaim_ceiling\n"


def test_short_reviewed_subtype_row_is_held_not_read_as_none(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    reviewed = tmp_path / "reviewed.tsv"
    reviewed.write_text(HEADER + "12\tSUB1\tFixture subtype\n")          # three trailing cells missing
    with pytest.raises(ValueError, match="REVIEWED_SUBTYPE_GATE"):
        report.build(database, 7, .3, host, crosswalk, tmp_path / "cohort", True, reviewed)


@pytest.mark.parametrize("token", ["NA", "None", "-"])
def test_placeholder_reviewed_subtype_value_is_held(tmp_path, token):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    reviewed = tmp_path / "reviewed.tsv"
    reviewed.write_text(HEADER + f"12\tSUB1\tFixture\tMeaning\t{token}\tCeiling\n")
    with pytest.raises(ValueError, match="REVIEWED_SUBTYPE_GATE"):
        report.build(database, 7, .3, host, crosswalk, tmp_path / "cohort", True, reviewed)


def test_unresolved_members_are_counted_beside_the_family_class():
    rows = [{"bin_label": "", "category": "NRPS", "product": "NRPS"},
            {"bin_label": "", "category": "", "product": "unlabelled"}]
    assert report.classify_family(rows)[0] == "NRPS"
    assert report.member_class_codes(rows) == ["NRPS", "UNK"]


def test_summary_carries_unresolved_member_count(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    cohort = tmp_path / "cohort"
    report.build(database, 7, .3, host, crosswalk, cohort, True)
    summary = list(csv.DictReader((cohort / "BIGSCAPE_GCF_SUMMARY.tsv").open(), delimiter="\t"))[0]
    assert summary["n_unresolved_class_records"] == "0"


def _zip(path, member="NODE_1.region001.gbk", body=b"LOCUS test\n     CDS             1..30\n//\n"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"{path.stem}.json", json.dumps({"strictness": "loose"}))
        z.writestr(member, body)
    return path


def _prep(tmp_path, *inputs):
    official = tmp_path / "OFFICIAL_DATA"
    official.mkdir(exist_ok=True)
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": []}))
    out = tmp_path / "out"
    env = dict(os.environ, MAMEY_OFFICIAL_DATA=str(official), MAMEY_DATA_ROOT=str(tmp_path))
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "bigscape_prep.py"), "--inputs", *map(str, inputs),
                        "--out", str(out), "--strictness", "loose"], capture_output=True, text=True, env=env)
    rows = list(csv.DictReader((out / "STAGED_MEMBERS.tsv").open(), delimiter="\t"))
    return r, out, rows


def test_staged_member_roster_binds_source_and_member_bytes(tmp_path):
    src = _zip(tmp_path / "SYN-1.zip")
    r, out, rows = _prep(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert len(rows) == 1
    row = rows[0]
    staged = out / row["staged_file"]
    assert row["source_sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert row["member_sha256"] == hashlib.sha256(staged.read_bytes()).hexdigest()
    assert int(row["member_bytes"]) == staged.stat().st_size
    assert (row["record_id"], row["region"], row["member_path"]) == ("NODE_1", "region001", "NODE_1.region001.gbk")


def test_collision_keeps_first_and_records_no_row_for_the_rolled_back_input(tmp_path):
    first = _zip(tmp_path / "SYN-1.zip")
    (tmp_path / "copy").mkdir()
    second = _zip(tmp_path / "copy" / "SYN-1.zip", body=b"LOCUS other\n     CDS             1..60\n//\n")
    r, out, rows = _prep(tmp_path, first, second)
    assert r.returncode == 2
    assert "STAGING_COLLISION" in r.stderr or "ValueError" in r.stderr
    assert [row["source"] for row in rows] == [str(first)]
    assert (out / rows[0]["staged_file"]).read_bytes() == b"LOCUS test\n     CDS             1..30\n//\n"

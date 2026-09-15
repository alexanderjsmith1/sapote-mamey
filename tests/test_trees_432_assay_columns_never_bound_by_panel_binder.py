"""TREES_432: the panel binder fills Candida/MRSA on QUERY rows from the bioassay table.

Four assay states (+, -, n.t., blank). Blank stays blank; n.t. stays n.t.; a reference row is
never touched; a strain absent from the table is reported, not guessed; an unknown state fails.
"""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))

import bind_panel_metadata as bpm  # noqa: E402
from trees_432_panel_fixture import make_panel, rows  # noqa: E402

ASSAY = "strain\tanti_candida\tanti_mrsa\nAS-1\t+\t+\nAS-2\t-\t+\nAS-3\tn.t.\tn.t.\nAS-4\t\t\nAS-5\t+\t\n"


def _query(tip, ident, cand="", mrsa=""):
    return dict(tip=tip, identifier=ident, role="QUERY", Candida=cand, MRSA=mrsa, metadata_status="base")


def test_four_states_preserved_exactly(tmp_path):
    table = tmp_path / "bioassay_table.tsv"
    table.write_text(ASSAY)
    assay = bpm.load_assay_table(table)
    assert assay["AS-1"] == ("+", "+")
    assert assay["AS-2"] == ("-", "+")
    assert assay["AS-3"] == ("n.t.", "n.t.")
    assert assay["AS-4"] == ("", "")
    assert assay["AS-5"] == ("+", "")

    data = [_query("AS-1", "AS-1"), _query("AS-2_cleaned_min1kb", "AS-2"), _query("AS-3", "AS-3"),
            _query("AS-4", "AS-4"), _query("AS-5", "AS-5"),
            dict(tip="GCF_1", identifier="GCF_1", role="REFERENCE", Candida="", MRSA="", metadata_status="base")]
    report = bpm.bind_assay_cells(data, assay, "bioassay_table.tsv")
    got = {r["identifier"]: (r["Candida"], r["MRSA"]) for r in data}
    assert got["AS-1"] == ("+", "+")
    assert got["AS-2"] == ("-", "+")
    assert got["AS-3"] == ("n.t.", "n.t.")          # not tested is not a negative
    assert got["AS-4"] == ("", "")                  # blank stays blank, never n.t.
    assert got["AS-5"] == ("+", "")
    assert got["GCF_1"] == ("", "")
    assert all(r["metadata_status"] == "base+ASSAY_FROM:bioassay_table.tsv" for r in data if r["role"] == "QUERY")
    assert data[-1]["metadata_status"] == "base"    # reference row untouched
    assert set(report.values()) == {"BOUND"}


def test_strain_id_comes_from_tip_prefix_when_identifier_is_not_a_strain():
    assert bpm.strain_id_from_row({"tip": "AS-425_cleaned_min1kb", "identifier": ""}) == "AS-425"
    assert bpm.strain_id_from_row({"tip": "AS-696", "identifier": "AS-696"}) == "AS-696"


def test_missing_strain_is_reported_not_guessed(tmp_path):
    table = tmp_path / "t.tsv"
    table.write_text(ASSAY)
    data = [_query("AS-9", "AS-9", cand="", mrsa="")]
    report = bpm.bind_assay_cells(data, bpm.load_assay_table(table), "t.tsv")
    assert report == {"AS-9": "NO_ASSAY_ROW"}
    assert (data[0]["Candida"], data[0]["MRSA"]) == ("", "")
    assert data[0]["metadata_status"] == "base"


def test_unknown_state_is_refused_never_coerced(tmp_path):
    table = tmp_path / "t.tsv"
    table.write_text("strain\tanti_candida\tanti_mrsa\nAS-1\tpositive\t-\n")
    with pytest.raises(SystemExit, match="ASSAY_STATE_INVALID"):
        bpm.load_assay_table(table)


def test_bad_header_is_refused(tmp_path):
    table = tmp_path / "t.tsv"
    table.write_text("strain\tcandida\tmrsa\nAS-1\t+\t-\n")
    with pytest.raises(SystemExit, match="ASSAY_TABLE_HEADER"):
        bpm.load_assay_table(table)


def test_cli_binds_query_cells_from_assay_table(tmp_path):
    data = rows()
    data[0].update(tip="AS-7_cleaned", identifier="AS-7", Candida="", MRSA="")
    panel = make_panel(tmp_path, "GTR-09-GENUS", data=data)
    table = tmp_path / "bioassay_table_AS.tsv"
    table.write_text("strain\tanti_candida\tanti_mrsa\nAS-7\tn.t.\t+\n")
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "bind_panel_metadata.py"), "--panel-dir", str(panel),
                        "--out-dir", str(out), "--assay-table", str(table)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    text = (out / "figure_metadata.tsv").read_text().splitlines()
    header = text[0].split("\t")
    q = dict(zip(header, text[1].split("\t")))
    assert (q["Candida"], q["MRSA"]) == ("n.t.", "+")
    assert "ASSAY_FROM:bioassay_table_AS.tsv" in q["metadata_status"]
    for line in text[2:]:
        row = dict(zip(header, line.split("\t")))
        assert (row["Candida"], row["MRSA"]) == ("", "")

"""Inspector identity is complete, shared by JSON/table, and refused before output."""
import argparse
import csv
import json

import pytest
from mamey.package_inspector import list_bgcs_command, bgc_json_list_from_board
from mamey.exact_identity import ExactLocusIdentityError

STRAIN = "SYNTHETIC-001"
CONTIG = "NODE_1_length_1000_cov_1.5"


def _row():
    return dict(Strain=STRAIN, Contig=CONTIG, Node_ID="NODE_1_length_1000_cov_1",
                antiSMASH_Region="region001", BGC_ID="BGC001", AB_auto="10")


def _board(tmp_path, rows):
    path = tmp_path / f"{STRAIN}_4_triage_board.csv"
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _args(tmp_path, as_json):
    return argparse.Namespace(package_dir=str(tmp_path), json=as_json, axis="rank",
                              top_n=None, include_dropped=False)


def test_table_json_and_board_consumer_preserve_same_complete_identity(tmp_path, capsys):
    row = _row()
    other = dict(row, Contig="NODE_1_length_1000_cov_1.9", BGC_ID="BGC002")
    path = _board(tmp_path, [row, other])
    expected = [f"{STRAIN} / {r['Contig']} / region001 / {r['BGC_ID']}" for r in [row, other]]
    before = path.read_bytes()
    assert list_bgcs_command(_args(tmp_path, False)) == 0
    table = capsys.readouterr().out
    assert all(identity in table for identity in expected)
    assert list_bgcs_command(_args(tmp_path, True)) == 0
    records = json.loads(capsys.readouterr().out)
    assert [r['exact_locus'] for r in records] == expected
    assert records == bgc_json_list_from_board(path)
    assert records[0]['assembly_locator'] == f"{CONTIG} region001"
    assert records[0]['node_id'] == "NODE_1_length_1000_cov_1"
    assert path.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("Contig", ""), ("Contig", "NODE_1"), ("Node_ID", "NODE_9"),
    ("antiSMASH_Region", ""), ("antiSMASH_Region", "region1"),
    ("BGC_ID", ""), ("Strain", "SYNTHETIC-OTHER"),
    ("region", "region002"), ("Full_Node_ID", "CP123456.1"),
])
@pytest.mark.parametrize("as_json", [False, True])
def test_identity_hold_precedes_any_partial_output(tmp_path, capsys, field, value, as_json):
    good = _row()
    bad = dict(good, BGC_ID="BGC002", Standing_rule="excluded")
    bad[field] = value
    path = _board(tmp_path, [good, bad])
    args = _args(tmp_path, as_json)
    args.top_n = 1
    assert list_bgcs_command(args) == 1
    output = capsys.readouterr()
    assert not output.out and "IDENTITY_HOLD" in output.err
    with pytest.raises(ExactLocusIdentityError):
        bgc_json_list_from_board(path, top_n=1)


def test_duplicate_alias_and_multiple_boards_are_refused(tmp_path, capsys):
    path = _board(tmp_path, [_row(), _row()])
    assert list_bgcs_command(_args(tmp_path, True)) == 1
    assert not capsys.readouterr().out
    _board(tmp_path, [_row()])
    path.with_name("OTHER_4_triage_board.csv").write_bytes(path.read_bytes())
    assert list_bgcs_command(_args(tmp_path, False)) == 1
    assert not capsys.readouterr().out


def test_csv_shape_and_missing_identity_column_are_refused(tmp_path):
    path = _board(tmp_path, [_row()])
    path.write_text(path.read_text() + "extra,row\n")
    with pytest.raises(ExactLocusIdentityError): bgc_json_list_from_board(path)
    path.write_text("BGC_ID,Contig,Node_ID\n")
    with pytest.raises(ExactLocusIdentityError): bgc_json_list_from_board(path)

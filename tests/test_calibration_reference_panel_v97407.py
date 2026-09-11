import csv

from tools.calibration_run import reference_control_rows, write_reference_control_tsv


def test_reference_panel_accounts_for_all_75_controls_without_inference(tmp_path):
    rows = reference_control_rows()
    assert len(rows) == 75
    assert {row["overall_status"] for row in rows} == {"NOT_EXERCISABLE"}
    assert {row["miss_classification"] for row in rows} == {"FIXTURE_DEFECT_MISSING_RUNNABLE_BINDING"}
    output = write_reference_control_tsv(tmp_path / "panel.tsv")
    persisted = list(csv.DictReader(output.open(), delimiter="\t"))
    assert len(persisted) == 75
    assert all(row["mibig_accession"] for row in persisted)

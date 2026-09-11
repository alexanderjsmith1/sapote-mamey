from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "bioassay_plate_map.py"
PROFILE = "96_TO_384_QUADRANT_120_60_30_15"


def run(tmp_path, *args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args], cwd=tmp_path,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True,
        text=True, timeout=30,
    )


def read(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_emitted_profile_has_complete_96_to_384_geometry(tmp_path):
    output = tmp_path / "map.tsv"
    result = run(tmp_path, "emit", "--profile", PROFILE, "--out", str(output))
    assert result.returncode == 0, result.stderr
    rows = read(output)
    assert len(rows) == 384
    by_destination = {row["destination_well"]: row for row in rows}
    assert len(by_destination) == 384
    assert (by_destination["A1"]["source_well"], by_destination["A1"]["final_concentration_ug_ml"]) == ("A1", "120")
    assert (by_destination["A2"]["source_well"], by_destination["A2"]["final_concentration_ug_ml"]) == ("A1", "60")
    assert (by_destination["B1"]["source_well"], by_destination["B1"]["final_concentration_ug_ml"]) == ("A1", "30")
    assert (by_destination["P24"]["source_well"], by_destination["P24"]["final_concentration_ug_ml"]) == ("H12", "15")
    assert all(row["mapping_state"] == "MAPPED" for row in rows)


def test_annotation_preserves_unmapped_row_as_explicit_hold(tmp_path):
    source = tmp_path / "readings.csv"
    source.write_text("Well_384,OD\nA01,0.2\nZ9,0.3\n", encoding="utf-8")
    output = tmp_path / "annotated.tsv"
    result = run(tmp_path, "annotate", "--profile", PROFILE, "--input", str(source), "--out", str(output))
    assert result.returncode == 0, result.stderr
    assert "PASS_WITH_HOLDS" in result.stdout
    rows = read(output)
    assert rows[0]["mapping_state"] == "MAPPED"
    assert rows[0]["source_well"] == "A1"
    assert rows[0]["destination_well"] == "A1"
    assert rows[1]["mapping_state"] == "UNMAPPED"
    assert rows[1]["final_concentration_ug_ml"] == ""


def test_validate_round_trip_and_refuse_changed_concentration(tmp_path):
    output = tmp_path / "map.tsv"
    assert run(tmp_path, "emit", "--profile", PROFILE, "--out", str(output)).returncode == 0
    assert run(tmp_path, "validate", "--profile", PROFILE, "--input", str(output)).returncode == 0
    rows = read(output)
    rows[0]["final_concentration_ug_ml"] = "999"
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0], delimiter="\t")
        writer.writeheader(); writer.writerows(rows)
    result = run(tmp_path, "validate", "--profile", PROFILE, "--input", str(output))
    assert result.returncode == 2
    assert "PLATE_MAP_MISMATCH" in result.stderr
    assert "Traceback" not in result.stderr


def test_validate_refuses_incomplete_map(tmp_path):
    source = tmp_path / "partial.tsv"
    source.write_text(
        "mapping_profile\tsource_well\tdestination_well\tquadrant\tfinal_concentration_ug_ml\n"
        f"{PROFILE}\tA1\tA1\tTL\t120\n", encoding="utf-8",
    )
    result = run(tmp_path, "validate", "--profile", PROFILE, "--input", str(source))
    assert result.returncode == 2
    assert "PLATE_MAP_COVERAGE" in result.stderr

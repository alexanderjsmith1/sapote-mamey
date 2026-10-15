"""Card 018c0f08_452_bioassay_ingest_adapters.

The Figure Factory takes one canonical observation table, but nothing brought a project's admitted per-well tables
into it, and the paper activity renderers read a best-value table built outside the bundle. These tests hold the
adapter: profile-driven mapping (no study values in code), the factory's own validator accepts the output, unmapped
calibrations and material groups are held rather than guessed, corrections apply by key, and the best table takes the
higher platform reading with 384-well readings at one dose only. Synthetic tables only.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "bioassay_admitted_observations.py"
EXAMPLE = ROOT / "examples" / "bioassay_admitted_profile_example.json"
DOC = ROOT / "docs" / "BIOASSAY_FIGURE_FACTORY.md"


def _tool():
    spec = importlib.util.spec_from_file_location("bioassay_admitted_t452", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(path: Path, header, rows, delimiter=","):
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow(header)
        writer.writerows(rows)


H96 = ["event_id", "strain_id", "fraction_plate", "source_96_well", "pathogen", "material_group", "material_id",
       "value_uncapped", "dose_ug_ml", "timepoint", "calibration_status", "assay_header"]
H384 = ["strain_id", "assay_plate", "fraction_plate", "source_96_well", "target_384_well", "pathogen", "material_group",
        "material_id", "value_uncapped", "dose_ug_ml", "timepoint", "calibration_basis"]


@pytest.fixture
def world(tmp_path):
    _write(tmp_path / "t96.csv", H96, [
        ["P1|L1", "SYN-1", "1", "A2", "Target alpha", "CRUDE", "1:A2", "-6.5", "", "48h", "WORKBOOK", "alpha plate"],
        ["P1|L1", "SYN-1", "1", "A3", "Target alpha", "CRUDE", "1:A3", "40.0", "", "48h", "WORKBOOK", "alpha plate"],
        ["P1|M1", "SYN-2", "1", "B2", "Target species unnamed", "FRACTION", "1:B2", "85.0", "100", "48h", "WORKBOOK", "beta plate"],
        ["P1|M1", "SYN-2", "1", "B3", "Target alpha", "MYSTERY", "1:B3", "12.0", "", "48h", "WORKBOOK", "beta plate"],
    ])
    _write(tmp_path / "t384.csv", H384, [
        ["SYN-1", "7", "1", "A2", "A3", "Target alpha", "CRUDE", "1:A2", "55.0", "120", "48h", "SIGNED"],
        ["SYN-1", "7", "1", "A2", "A4", "Target alpha", "CRUDE", "1:A2", "99.0", "60", "48h", "SIGNED"],
        ["SYN-1", "7", "1", "A2", "B3", "Target alpha", "CRUDE", "1:A2", "-3.0", "30", "48h", "SIGNED"],
        ["SYN-3", "7", "1", "C2", "E3", "Target beta", "FRACTION", "1:C2", "70.0", "120", "48h", "EXPECTED_ONLY"],
    ])
    _write(tmp_path / "fix.tsv", ["platform", "fraction_plate", "source_96_well", "strain_id", "material_group"],
           [["96-well", "1", "A3", "SYN-1", "FRACTION"]], delimiter="\t")
    c96 = {"row_id": "event_id", "strain": "strain_id", "plate": "fraction_plate", "well": "source_96_well",
           "target": "pathogen", "material_group": "material_group", "material_id": "material_id",
           "value": "value_uncapped", "dose": "dose_ug_ml", "timepoint": "timepoint",
           "calibration": "calibration_status", "experiment": "assay_header"}
    c384 = {"strain": "strain_id", "plate": "assay_plate", "well": "target_384_well", "target": "pathogen",
            "material_group": "material_group", "material_id": "material_id", "value": "value_uncapped",
            "dose": "dose_ug_ml", "timepoint": "timepoint", "calibration": "calibration_basis"}
    profile = {
        "schema_version": "sapote.bioassay-admitted-profile.v1",
        "tables": [{"key": "t96", "platform": "96", "path": "t96.csv", "columns": c96},
                   {"key": "t384", "platform": "384", "path": "t384.csv", "columns": c384}],
        "corrections": {"path": "fix.tsv", "platform_column": "platform",
                        "platform_values": {"96": "96-well", "384": "384-well"},
                        "match_columns": ["fraction_plate", "source_96_well", "strain_id"],
                        "apply": {"material_group": "material_group"}},
        "material_types": {"CRUDE": "CRUDE_EXTRACT", "FRACTION": "FLASH_FRACTION"},
        "targets": {"Target species unnamed": "AMBIGUOUS", "Target alpha": "VERIFIED"},
        "dose_states": {"384": "VERIFIED", "96": "AS_RECORDED"},
        "replicate_type": "SINGLETON",
        "control_states": {"WORKBOOK": {"state": "VALID", "basis": "owner-computed"},
                           "SIGNED": {"state": "VALID", "basis": "signed anchors"},
                           "EXPECTED_ONLY": {"state": "EXPECTED_OD_NORMALIZATION_HOLD", "basis": "expected OD"}},
    }
    (tmp_path / "profile.json").write_text(json.dumps(profile))
    return tmp_path


def _obs(world):
    mod = _tool()
    out = world / "obs.tsv"
    assert mod.main(["observations", "--profile", str(world / "profile.json"), "--out", str(out)]) == 0
    return mod, out, {r["source_locator"].split("/")[0] + "|" + r["well"] + "|" + r["final_concentration_ug_ml"]: r
                      for r in csv.DictReader(open(out), delimiter="\t")}


def test_columns_match_the_factory_template_and_the_factory_admits_them(world):
    _, out, _ = _obs(world)
    template = (ROOT / "examples" / "bioassay_observations_template.tsv").read_text().splitlines()[0].split("\t")
    assert open(out).readline().rstrip("\n").split("\t") == template
    sys.path.insert(0, str(ROOT))
    from mamey.bioassay_figure_factory import _read, validate_rows
    rows = validate_rows(_read(out))
    assert len(rows) == 8


def test_values_are_copied_uncapped_and_doses_carry_their_states(world):
    _, _, rows = _obs(world)
    assert rows["t96|A2|"]["inhibition_pct"] == "-6.5"
    assert rows["t96|A2|"]["dose_state"] == "UNRECORDED" and rows["t96|A2|"]["final_concentration_ug_ml"] == ""
    assert rows["t96|B2|100"]["dose_state"] == "AS_RECORDED"
    assert rows["t384|A3|120"]["dose_state"] == "VERIFIED" and rows["t384|A3|120"]["timepoint_hours"] == "48"


def test_unmapped_material_and_unruled_calibration_are_held_not_guessed(world):
    _, out, rows = _obs(world)
    assert rows["t96|B3|"]["inclusion_state"] == "HOLD" and "MATERIAL_GROUP_UNMAPPED:MYSTERY" in rows["t96|B3|"]["exclusion_reason"]
    held = rows["t384|E3|120"]
    assert held["inclusion_state"] == "HOLD" and held["control_state"] == "EXPECTED_OD_NORMALIZATION_HOLD"
    receipt = json.loads(Path(str(out) + ".receipt.json").read_text())
    assert sum(c["rows"] for c in receipt["inclusion_counts"] if c["inclusion_state"] == "HOLD") == 2
    assert all(len(t["sha256"]) == 64 for t in receipt["tables"]) and receipt["corrections_applied"] == 1


def test_targets_keep_their_state_and_corrections_apply_by_key(world):
    _, _, rows = _obs(world)
    assert rows["t96|B2|100"]["target_state"] == "AMBIGUOUS" and rows["t96|B2|100"]["target_canonical"] == ""
    assert rows["t96|A2|"]["target_canonical"] == "Target alpha"
    assert rows["t96|A3|"]["material_type"] == "FLASH_FRACTION"     # reclassified by the corrections table
    assert rows["t96|A2|"]["material_type"] == "CRUDE_EXTRACT"


def test_best_table_takes_the_higher_platform_reading_at_one_384_dose(world):
    mod, out, _ = _obs(world)
    best = world / "best.tsv"
    assert mod.main(["best-table", "--observations", str(out), "--out", str(best)]) == 0
    rows = {(r["strain"], r["organism"], r["material"]): r for r in csv.DictReader(open(best), delimiter="\t")}
    crude = rows[("SYN-1", "Target alpha", "Crude extract")]
    assert crude["best_pct"] == "55.00"          # the 60 ug/mL 99.0 does not count; 120 only
    assert (crude["best_96"], crude["best_384_120"], crude["read_on"]) == ("0.00", "55.00", "both")  # -6.5 floored
    assert (crude["n_96"], crude["n_384_120"]) == ("1", "1")
    assert ("SYN-3", "Target beta", "Fraction") not in rows       # held rows are not summarized
    assert ("SYN-2", "Target alpha", "Material unresolved") not in rows
    assert rows[("SYN-2", "Target species unnamed", "Fraction")]["read_on"] == "96-well"


def test_no_floor_keeps_negative_readings(world):
    mod, out, _ = _obs(world)
    best = world / "best_nofloor.tsv"
    assert mod.main(["best-table", "--observations", str(out), "--out", str(best), "--no-floor", "--dose-384", "30"]) == 0
    rows = {(r["strain"], r["organism"], r["material"]): r for r in csv.DictReader(open(best), delimiter="\t")}
    assert rows[("SYN-1", "Target alpha", "Crude extract")]["best_384_30"] == "-3.00"


def test_refusals(world, tmp_path):
    mod = _tool()
    out = world / "obs.tsv"
    assert mod.main(["observations", "--profile", str(world / "profile.json"), "--out", str(out)]) == 0
    assert mod.main(["observations", "--profile", str(world / "profile.json"), "--out", str(out)]) == 2  # no overwrite
    bad = json.loads((world / "profile.json").read_text())
    bad["control_states"]["WORKBOOK"] = {"state": "VALID"}                                             # no basis
    (world / "bad.json").write_text(json.dumps(bad))
    assert mod.main(["observations", "--profile", str(world / "bad.json"), "--out", str(world / "o2.tsv")]) == 2
    dup = json.loads((world / "profile.json").read_text())
    dup["tables"][0]["columns"]["well"] = "fraction_plate"                                             # ids collide
    (world / "dup.json").write_text(json.dumps(dup))
    assert mod.main(["observations", "--profile", str(world / "dup.json"), "--out", str(world / "o3.tsv")]) == 2


def test_example_profile_loads_and_code_holds_no_study_values():
    mod = _tool()
    profile = json.loads(EXAMPLE.read_text())
    assert profile["schema_version"] == mod.PROFILE_SCHEMA
    src = TOOL.read_text()
    labels = list(profile["control_states"]) + list(profile["targets"]) + list(profile["material_types"])
    assert not [label for label in labels if f'"{label}"' in src]     # every mapping comes from the profile
    assert "/Users/" not in src and "/home/" not in src


def test_doc_explains_the_adapter_and_the_control_state_rule():
    text = DOC.read_text()
    assert "## Bring admitted per-well tables in" in text
    assert "bioassay_admitted_observations.py observations --profile" in text
    assert "bioassay_admitted_observations.py best-table" in text
    assert "UNRECORDED" in text and "held" in text

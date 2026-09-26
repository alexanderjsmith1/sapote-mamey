"""Owner rulings (for example "these fraction-series wells are fractions, not crude") are applied as data.

The failure this guards against: material corrections were applied downstream, in figure scripts, so
figures moved twice in one day and each rebuild had to re-apply the rulings by hand.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from mamey import bioassay_figure_factory as factory


def _row(**updates):
    row = dict.fromkeys(factory.FIELDS, "")
    row.update({
        "observation_id": "obs-1", "strain_id": "SYN-1", "experiment_id": "exp-1",
        "assay_plate_id": "plate-45", "plate_format": "96", "well": "A02",
        "material_id": "SYN-1", "material_type": "CRUDE_EXTRACT",
        "parent_material_id": "", "lineage_state": "UNRECORDED",
        "material_amount_mg": "", "dose_state": "UNRECORDED",
        "stock_concentration_mg_ml": "", "delivered_amount_ug": "", "final_concentration_ug_ml": "",
        "target_raw": "Candida albicans", "target_state": "VERIFIED",
        "target_canonical": "Candida albicans", "timepoint_hours": "48", "replicate_id": "rep-1",
        "replicate_type": "SINGLETON", "inhibition_pct": "91.0", "control_state": "VALID",
        "inclusion_state": "INCLUDE", "exclusion_reason": "", "source_locator": "plates/plate-45.csv",
    })
    row.update(updates)
    return row


def _ruling(**updates):
    ruling = {
        "ruling_id": "R1", "assay_plate_id": "plate-45", "well": "A02", "strain_id": "SYN-1",
        "field": "material_type", "from_value": "CRUDE_EXTRACT", "to_value": "FLASH_FRACTION",
        "basis": "workbook lists F1 (tubes 3-8)", "ruled_by": "owner",
    }
    ruling.update(updates)
    return ruling


def _write(path: Path, fields, rows, delimiter=","):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=delimiter)
        writer.writeheader(); writer.writerows(rows)


def _rulings_file(tmp_path, rulings):
    path = tmp_path / "rulings.tsv"
    _write(path, factory.RULING_FIELDS, rulings, delimiter="\t")
    return path


def test_ruling_changes_every_observation_of_the_ruled_well(tmp_path):
    rows = [_row(), _row(observation_id="obs-2", target_raw="MRSA", target_canonical="MRSA", inhibition_pct="40")]
    other = _row(observation_id="obs-3", well="A03")
    out, ledger = factory.apply_rulings(rows + [other], factory.read_rulings(_rulings_file(tmp_path, [_ruling()])))
    assert [row["material_type"] for row in out] == ["FLASH_FRACTION", "FLASH_FRACTION", "CRUDE_EXTRACT"]
    assert ledger[0]["observations_changed"] == 2
    assert rows[0]["material_type"] == "CRUDE_EXTRACT"          # input rows are not mutated
    summary = factory.summarize(factory.validate_rows(out))
    assert {row["material_type"] for row in summary} == {"FLASH_FRACTION", "CRUDE_EXTRACT"}


def test_ruling_that_matches_nothing_refuses(tmp_path):
    rulings = factory.read_rulings(_rulings_file(tmp_path, [_ruling(well="H12")]))
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_RULING_UNMATCHED_HOLD"):
        factory.apply_rulings([_row()], rulings)


def test_stale_ruling_refuses_instead_of_overwriting(tmp_path):
    rulings = factory.read_rulings(_rulings_file(tmp_path, [_ruling()]))
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_RULING_STALE_HOLD"):
        factory.apply_rulings([_row(material_type="HPLC_FRACTION")], rulings)


@pytest.mark.parametrize("rulings,code", [
    ([_ruling(), _ruling(ruling_id="R2", to_value="HPLC_FRACTION")], "BIOASSAY_RULING_CONFLICT_HOLD"),
    ([_ruling(), _ruling(well="A03")], "BIOASSAY_RULING_DUPLICATE_HOLD"),
    ([_ruling(to_value="FRACTION")], "BIOASSAY_RULING_VALUE_HOLD"),
    ([_ruling(to_value="CRUDE_EXTRACT")], "BIOASSAY_RULING_VALUE_HOLD"),
    ([_ruling(field="inhibition_pct", from_value="91.0", to_value="95")], "BIOASSAY_RULING_FIELD_HOLD"),
    ([_ruling(basis="")], "BIOASSAY_RULING_FIELD_HOLD"),
])
def test_malformed_rulings_refuse(tmp_path, rulings, code):
    with pytest.raises(factory.BioassayFigureHold, match=code):
        factory.read_rulings(_rulings_file(tmp_path, rulings))


def test_rulings_table_needs_its_exact_columns(tmp_path):
    path = tmp_path / "rulings.tsv"
    _write(path, ["ruling_id", "well"], [{"ruling_id": "R1", "well": "A02"}], delimiter="\t")
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_RULING_SCHEMA_HOLD"):
        factory.read_rulings(path)


def test_hold_ruling_keeps_the_row_with_its_reason(tmp_path):
    ruling = _ruling(field="inclusion_state", from_value="INCLUDE", to_value="HOLD",
                     basis="material unknown until the plate map is read")
    out, _ = factory.apply_rulings([_row(), _row(observation_id="obs-2", well="A03")],
                                   factory.read_rulings(_rulings_file(tmp_path, [ruling])))
    rows = factory.validate_rows(out)
    assert rows[0]["inclusion_state"] == "HOLD"
    assert rows[0]["exclusion_reason"] == "ruling R1: material unknown until the plate map is read"
    assert len(factory.summarize(rows)) == 1


def test_ruling_cannot_create_a_row_validation_would_refuse(tmp_path):
    rulings = factory.read_rulings(_rulings_file(tmp_path, [_ruling()]))
    out, _ = factory.apply_rulings([_row(lineage_state="VERIFIED")], rulings)
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_LINEAGE_HOLD"):
        factory.validate_rows(out)


def _config(tmp_path, rulings_sha=None):
    source = tmp_path / "observations.csv"
    _write(source, factory.FIELDS, [_row(), _row(observation_id="obs-2", well="A03")])
    config = {
        "schema_version": factory.SCHEMA, "figure_kind": factory.FIGURE_KIND,
        "external_data_root": str(tmp_path),
        "observations": {"logical_locator": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "output_dir": "out", "render_with_r": False,
    }
    if rulings_sha is not None:
        rules = _rulings_file(tmp_path, [_ruling()])
        config["rulings"] = {"logical_locator": rules.name,
                             "sha256": rulings_sha or hashlib.sha256(rules.read_bytes()).hexdigest()}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_build_applies_hash_bound_rulings_and_writes_a_ledger(tmp_path):
    receipt = factory.build(_config(tmp_path, rulings_sha=""))
    assert receipt["rulings"]["rulings_applied"] == 1
    ledger = (tmp_path / "out" / "bioassay_rulings_applied.tsv").read_text()
    assert "R1" in ledger and "FLASH_FRACTION" in ledger
    caption = json.loads((tmp_path / "out" / "bioassay_caption_methods.json").read_text())
    assert caption["rulings_applied"] == 1 and caption["observations_changed_by_rulings"] == 1
    clean = (tmp_path / "out" / "bioassay_observations_admitted.tsv").read_text()
    assert "FLASH_FRACTION" in clean
    assert any(entry["logical_locator"] == "bioassay_rulings_applied.tsv" for entry in receipt["outputs"])


def test_build_refuses_rulings_with_the_wrong_hash(tmp_path):
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_RULING_HASH_HOLD"):
        factory.build(_config(tmp_path, rulings_sha="0" * 64))
    assert not (tmp_path / "out").exists()


def test_build_without_rulings_is_unchanged(tmp_path):
    receipt = factory.build(_config(tmp_path))
    assert "rulings" not in receipt
    assert not (tmp_path / "out" / "bioassay_rulings_applied.tsv").exists()

"""Every source assay column must be accounted for at admission.

The failure this guards against (Gap A): twelve 48 h 96-well columns were admitted in the plate rebuild but were
missing from the table the figures used, with no reason recorded. Nothing noticed, because the factory only sees
the rows it is given.
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
        "assay_plate_id": "plate-22", "plate_format": "96", "well": "A02",
        "material_id": "SYN-1", "material_type": "CRUDE_EXTRACT",
        "parent_material_id": "", "lineage_state": "UNRECORDED",
        "material_amount_mg": "", "dose_state": "UNRECORDED",
        "stock_concentration_mg_ml": "", "delivered_amount_ug": "", "final_concentration_ug_ml": "",
        "target_raw": "Candida 96 well inhibition", "target_state": "AMBIGUOUS",
        "target_canonical": "", "timepoint_hours": "48", "replicate_id": "rep-1",
        "replicate_type": "SINGLETON", "inhibition_pct": "12.0", "control_state": "VALID",
        "inclusion_state": "INCLUDE", "exclusion_reason": "", "source_locator": "plates/plate-22.csv",
    })
    row.update(updates)
    return row


def _entry(**updates):
    entry = {"column_id": "FP22|P1", "assay_plate_id": "plate-22", "target_raw": "Candida 96 well inhibition",
             "timepoint_hours": "48", "disposition": "ADMIT", "reason": ""}
    entry.update(updates)
    return entry


def _write(path: Path, fields, rows, delimiter=","):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=delimiter)
        writer.writeheader(); writer.writerows(rows)


def _inventory(tmp_path, entries):
    path = tmp_path / "columns.tsv"
    _write(path, factory.INVENTORY_FIELDS, entries, delimiter="\t")
    return factory.read_column_inventory(path)


def test_every_admitted_column_present_gives_a_ledger(tmp_path):
    rows = factory.validate_rows([_row(), _row(observation_id="obs-2", well="A03")])
    excluded = _entry(column_id="FP22|Q1", target_raw="Candida 24 h", timepoint_hours="24", disposition="EXCLUDE",
                      reason="24 h reading; figures use 48 h")
    ledger = factory.reconcile_column_inventory(rows, _inventory(tmp_path, [_entry(), excluded]))
    assert [(e["column_id"], e["observations"]) for e in ledger] == [("FP22|P1", 2), ("FP22|Q1", 0)]


def test_admitted_column_with_no_observations_refuses(tmp_path):
    """The Gap A case: the inventory says ADMIT, the observations table has none of that column."""
    rows = factory.validate_rows([_row()])
    dropped = _entry(column_id="FP50|V1", assay_plate_id="plate-50", target_raw="Candida Jan 23")
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_INVENTORY_MISSING_HOLD: 1 .*FP50\\|V1"):
        factory.reconcile_column_inventory(rows, _inventory(tmp_path, [_entry(), dropped]))


def test_observed_column_missing_from_inventory_refuses(tmp_path):
    rows = factory.validate_rows([_row(), _row(observation_id="obs-2", target_raw="MRSA 48 hrs")])
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_INVENTORY_UNLISTED_HOLD"):
        factory.reconcile_column_inventory(rows, _inventory(tmp_path, [_entry()]))


def test_observations_from_an_excluded_column_refuse(tmp_path):
    rows = factory.validate_rows([_row()])
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_INVENTORY_CONTRADICTION_HOLD"):
        factory.reconcile_column_inventory(rows, _inventory(tmp_path, [_entry(disposition="EXCLUDE", reason="failed plate")]))


def test_held_rows_still_count_as_present(tmp_path):
    rows = factory.validate_rows([_row(inclusion_state="HOLD", exclusion_reason="material unknown")])
    ledger = factory.reconcile_column_inventory(rows, _inventory(tmp_path, [_entry()]))
    assert ledger[0]["observations"] == 1


@pytest.mark.parametrize("entries,code", [
    ([_entry(disposition="EXCLUDE")], "BIOASSAY_INVENTORY_REASON_HOLD"),
    ([_entry(disposition="HOLD")], "BIOASSAY_INVENTORY_REASON_HOLD"),
    ([_entry(disposition="DROP", reason="x")], "BIOASSAY_INVENTORY_FIELD_HOLD"),
    ([_entry(), _entry()], "BIOASSAY_INVENTORY_DUPLICATE_HOLD"),
    ([_entry(), _entry(column_id="FP22|P1-copy")], "BIOASSAY_INVENTORY_DUPLICATE_HOLD"),
    ([_entry(timepoint_hours="48h")], "BIOASSAY_INVENTORY_FIELD_HOLD"),
    ([], "BIOASSAY_INVENTORY_EMPTY_HOLD"),
])
def test_malformed_inventory_refuses(tmp_path, entries, code):
    with pytest.raises(factory.BioassayFigureHold, match=code):
        _inventory(tmp_path, entries)


def _config(tmp_path, entries, sha=None):
    source = tmp_path / "observations.csv"
    _write(source, factory.FIELDS, [_row(), _row(observation_id="obs-2", well="A03")])
    inv = tmp_path / "columns.tsv"
    _write(inv, factory.INVENTORY_FIELDS, entries, delimiter="\t")
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "schema_version": factory.SCHEMA, "figure_kind": factory.FIGURE_KIND,
        "external_data_root": str(tmp_path),
        "observations": {"logical_locator": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "column_inventory": {"logical_locator": inv.name, "sha256": sha or hashlib.sha256(inv.read_bytes()).hexdigest()},
        "output_dir": "out", "render_with_r": False,
    }), encoding="utf-8")
    return path


def test_build_writes_the_column_ledger_and_records_the_inventory(tmp_path):
    receipt = factory.build(_config(tmp_path, [_entry()]))
    assert receipt["column_inventory"]["columns"] == 1 and receipt["column_inventory"]["admitted"] == 1
    ledger = (tmp_path / "out" / "bioassay_column_ledger.tsv").read_text()
    assert "FP22|P1" in ledger


def test_build_refuses_a_dropped_column_and_writes_nothing(tmp_path):
    dropped = _entry(column_id="FP53|M1", assay_plate_id="plate-53", target_raw="Candida albicans 48 hrs")
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_INVENTORY_MISSING_HOLD"):
        factory.build(_config(tmp_path, [_entry(), dropped]))
    assert not (tmp_path / "out").exists()


def test_build_refuses_an_inventory_with_the_wrong_hash(tmp_path):
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_INVENTORY_HASH_HOLD"):
        factory.build(_config(tmp_path, [_entry()], sha="0" * 64))

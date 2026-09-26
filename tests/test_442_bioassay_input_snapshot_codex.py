"""Factory receipts must describe the bytes actually parsed."""
import csv
import hashlib
import json

from mamey import bioassay_figure_factory as factory


def _write(path, fields, rows, delimiter=","):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path, with_ruling):
    row = dict.fromkeys(factory.FIELDS, "")
    row.update(observation_id="obs-1", strain_id="SYN-1", experiment_id="exp-1",
               assay_plate_id="plate-1", plate_format="96", well="A01",
               material_id="SYN-1", material_type="CRUDE_EXTRACT",
               lineage_state="UNRECORDED", dose_state="UNRECORDED",
               target_raw="target", target_state="AS_RECORDED", timepoint_hours="48",
               replicate_id="rep-1", replicate_type="SINGLETON", inhibition_pct="50",
               control_state="VALID", inclusion_state="INCLUDE", source_locator="plate-1.csv")
    observation = tmp_path / "observations.csv"
    _write(observation, factory.FIELDS, [row])
    config = {"schema_version": factory.SCHEMA, "figure_kind": factory.FIGURE_KIND,
              "external_data_root": str(tmp_path), "output_dir": "out", "render_with_r": False,
              "observations": {"logical_locator": observation.name,
                               "sha256": hashlib.sha256(observation.read_bytes()).hexdigest()}}
    ruling = None
    if with_ruling:
        ruling = tmp_path / "rulings.tsv"
        _write(ruling, factory.RULING_FIELDS, [{
            "ruling_id": "R1", "assay_plate_id": "plate-1", "well": "A01", "strain_id": "SYN-1",
            "field": "material_type", "from_value": "CRUDE_EXTRACT", "to_value": "FLASH_FRACTION",
            "basis": "synthetic correction", "ruled_by": "owner"}], delimiter="\t")
        config["rulings"] = {"logical_locator": ruling.name,
                             "sha256": hashlib.sha256(ruling.read_bytes()).hexdigest()}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path, observation, ruling


def test_observation_parse_uses_verified_snapshot_even_if_source_changes(tmp_path, monkeypatch):
    config, source, _ = _fixture(tmp_path, False)
    original = factory._read
    def changed_before_parse(path, data=None):
        source.write_bytes(source.read_bytes().replace(b",50,", b",90,"))
        return original(path, data=data) if data is not None else original(path)
    monkeypatch.setattr(factory, "_read", changed_before_parse)
    receipt = factory.build(config)
    admitted = (tmp_path / "out" / "bioassay_observations_admitted.tsv").read_text()
    assert "\t50.0\t" in admitted
    assert "\t90.0\t" not in admitted
    assert receipt["input"]["sha256"] != hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt["input"]["bytes"] == len(source.read_bytes())


def test_ruling_parse_uses_verified_snapshot_even_if_source_changes(tmp_path, monkeypatch):
    config, _, source = _fixture(tmp_path, True)
    original = factory.read_rulings
    def changed_before_parse(path, data=None):
        source.write_bytes(source.read_bytes().replace(b"FLASH_FRACTION", b"HPLC_FRACTION"))
        return original(path, data=data) if data is not None else original(path)
    monkeypatch.setattr(factory, "read_rulings", changed_before_parse)
    receipt = factory.build(config)
    admitted = (tmp_path / "out" / "bioassay_observations_admitted.tsv").read_text()
    assert "FLASH_FRACTION" in admitted
    assert "HPLC_FRACTION" not in admitted
    assert receipt["rulings"]["sha256"] != hashlib.sha256(source.read_bytes()).hexdigest()

"""A plan's dataset byte count must describe the bytes that were hashed."""

import hashlib
import json

from mamey import bioassay_figure_factory as factory


def test_plan_input_byte_count_is_bound_to_verified_hash(tmp_path, monkeypatch):
    source = tmp_path / "raw.csv"
    original_bytes = b"raw\n1\n"
    source.write_bytes(original_bytes)
    config = tmp_path / "plan.json"
    config.write_text(json.dumps({
        "schema_version": factory.PLAN_SCHEMA, "figure_kind": factory.PLAN_KIND,
        "external_data_root": str(tmp_path), "output_dir": "out",
        "datasets": [{"dataset_id": "raw", "data_state": "RAW_OD",
                      "material_scope": "CRUDE_EXTRACT", "logical_locator": source.name,
                      "sha256": hashlib.sha256(original_bytes).hexdigest()}],
    }), encoding="utf-8")
    original_hash = factory.sha256_file

    def changed_after_hash(path):
        digest = original_hash(path)
        if path == source:
            source.write_bytes(original_bytes + b"2\n")
        return digest

    monkeypatch.setattr(factory, "sha256_file", changed_after_hash)
    factory.build_plan(config)
    plan = json.loads((tmp_path / "out" / "bioassay_project_plan.json").read_text())
    admitted = plan["datasets"][0]
    assert admitted["sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert admitted["bytes"] == len(original_bytes)

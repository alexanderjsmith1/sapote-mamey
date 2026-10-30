"""Reject unsafe filename components; no authored card, register or verdict is saved."""
import json
import sys
import types

import pytest

from mamey import judgment_store as store


@pytest.mark.parametrize("strain", ["../outside", "/tmp/outside", "nested/name", r"nested\name", "..", "C:relative"])
def test_manifest_strain_must_be_one_filename_component(tmp_path, strain):
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": strain}))
    with pytest.raises(ValueError, match="filename component"):
        store._register_path(tmp_path)


@pytest.mark.parametrize("identifier", ["/../../../outside", "../outside", r"..\outside", "nested/name"])
def test_card_identifier_must_be_one_filename_component(tmp_path, identifier):
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "engineering_fixture"}))
    with pytest.raises(ValueError, match="filename component"):
        store._mode_b_path(tmp_path, identifier)


def test_valid_components_remain_inside_package_without_creating_directories(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "engineering_fixture"}))
    paths = [store._register_path(tmp_path), store._mode_b_path(tmp_path, "software_record"),
             store._laypersons_path(tmp_path), store._fermentation_path(tmp_path)]
    assert all(path.resolve().is_relative_to(tmp_path) for path in paths)
    assert not (tmp_path / "judgment").exists()


def test_public_record_refuses_before_first_write(tmp_path, monkeypatch):
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "engineering_fixture"}))
    fake = types.ModuleType("mamey.mode_b_quality_gate")
    monkeypatch.setattr(fake, "evaluate_card", lambda *a, **k: types.SimpleNamespace(
        tier="FULL", priority="SOFTWARE", char_count=0, gene_mentions=0, section_count=0,
        message="mocked gate: filename admission only"), raising=False)
    monkeypatch.setitem(sys.modules, "mamey.mode_b_quality_gate", fake)
    calls = []
    def forbidden_writer(path, text):
        calls.append(path)
        raise AssertionError("unsafe identifier reached the writer")
    monkeypatch.setattr(store, "_atomic_write_text", forbidden_writer)
    with pytest.raises(ValueError, match="filename component"):
        store.record_mode_b(tmp_path, "/../../../outside", "software path fixture only")
    assert not calls

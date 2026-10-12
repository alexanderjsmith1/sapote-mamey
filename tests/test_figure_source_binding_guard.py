"""Saved Figure Factory sources remain bound at admission and final receipt."""
from __future__ import annotations

import hashlib
import importlib
import io
import json
import zipfile

import pytest

from mamey.figure_policy import FigurePolicyError
from mamey.interactive_figures import figure_atlas
from mamey.interactive_figures.figure_source_bundle import _member, verify_source_bundle


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_sources(tmp_path, status="PASS", names=("fixture.csv",)):
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps({"strains": {"TEST-STUDY": {"governance": "GOVERNED"}}}), encoding="utf-8")
    bundle = tmp_path / "sources"
    bundle.mkdir()
    outputs = []
    for name in names:
        path = bundle / name
        path.write_text("value\n1\n", encoding="utf-8")
        outputs.append({"path": name, "sha256": _sha(path), "rows": 1})
    receipt = {"status": status, "source": {"widget_sha256": _sha(widget)}, "outputs": outputs}
    receipt_path = bundle / "SOURCE_BUNDLE_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return widget, bundle, receipt_path, receipt


def _store(path, receipt):
    path.write_text(json.dumps(receipt), encoding="utf-8")


def test_unique_and_missing_zip_members_keep_their_contract():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("package/S_2_inventory.csv", "unique")
    with zipfile.ZipFile(stream) as archive:
        assert _member(archive, "_2_inventory.csv") == "package/S_2_inventory.csv"
        assert _member(archive, "_cds_table.csv") is None


@pytest.mark.parametrize("duplicate_name", [False, True])
def test_ambiguous_zip_member_is_refused(duplicate_name):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("a/S_2_inventory.csv", "first")
        if duplicate_name:
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr("a/S_2_inventory.csv", "second")
        else:
            archive.writestr("b/S_2_inventory.csv", "second")
    with zipfile.ZipFile(stream) as archive:
        with pytest.raises(ValueError, match="FIGURE_INPUT_SOURCE_MEMBER_AMBIGUOUS"):
            _member(archive, "_2_inventory.csv")


@pytest.mark.parametrize("status", ["PASS", "PASS_WITH_ISSUES"])
def test_saved_source_bindings_are_verified_without_rewriting(tmp_path, status):
    widget, bundle, receipt_path, receipt = _bound_sources(tmp_path, status)
    paths = [widget, *bundle.iterdir()]
    before = {p: p.read_bytes() for p in paths}
    binding = verify_source_bundle(widget, bundle, required_tables=("fixture.csv",))
    assert binding["receipt"] == receipt
    assert binding["receipt_sha256"] == _sha(receipt_path)
    verify_source_bundle(widget, bundle, expected_receipt_sha256=binding["receipt_sha256"])
    assert {p: p.read_bytes() for p in paths} == before


@pytest.mark.parametrize("fault,code", [
    ("failed", "SOURCE_BUNDLE_NOT_USABLE"),
    ("invalid_json", "SOURCE_RECEIPT_INVALID"),
    ("widget", "WIDGET_BINDING_MISMATCH"),
    ("table", "SOURCE_TABLE_BINDING_FAILED"),
    ("missing_table", "SOURCE_TABLE_BINDING_FAILED"),
    ("missing_outputs", "SOURCE_OUTPUT_BINDINGS_MISSING"),
    ("duplicate_record", "SOURCE_OUTPUT_BINDING_INVALID"),
    ("bad_hash", "SOURCE_TABLE_BINDING_FAILED"),
    ("parent_path", "SOURCE_OUTPUT_BINDING_INVALID"),
    ("absolute_path", "SOURCE_OUTPUT_BINDING_INVALID"),
])
def test_changed_or_unusable_saved_sources_refuse(tmp_path, fault, code):
    widget, bundle, receipt_path, receipt = _bound_sources(tmp_path)
    if fault == "failed":
        receipt["status"] = "FAIL"
    elif fault == "invalid_json":
        receipt_path.write_text("not JSON", encoding="utf-8")
    elif fault == "widget":
        widget.write_text("{}", encoding="utf-8")
    elif fault == "table":
        (bundle / "fixture.csv").write_text("value\n2\n", encoding="utf-8")
    elif fault == "missing_table":
        (bundle / "fixture.csv").unlink()
    elif fault == "missing_outputs":
        receipt.pop("outputs")
    elif fault == "duplicate_record":
        receipt["outputs"].append(dict(receipt["outputs"][0]))
    elif fault == "bad_hash":
        receipt["outputs"][0]["sha256"] = "bad"
    elif fault == "parent_path":
        receipt["outputs"][0]["path"] = "../fixture.csv"
    elif fault == "absolute_path":
        receipt["outputs"][0]["path"] = str((bundle / "fixture.csv").resolve())
    if fault != "invalid_json":
        _store(receipt_path, receipt)
    with pytest.raises(ValueError, match=code):
        verify_source_bundle(widget, bundle, required_tables=("fixture.csv",))


def test_used_table_must_be_declared_in_receipt(tmp_path):
    widget, bundle, _, _ = _bound_sources(tmp_path)
    (bundle / "undeclared.csv").write_text("value\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_TABLE_BINDING_FAILED: undeclared.csv"):
        verify_source_bundle(widget, bundle, required_tables=("undeclared.csv",))


def test_changed_receipt_cannot_be_used_as_the_original_snapshot(tmp_path):
    widget, bundle, receipt_path, receipt = _bound_sources(tmp_path)
    binding = verify_source_bundle(widget, bundle)
    receipt["status"] = "PASS_WITH_ISSUES"
    _store(receipt_path, receipt)
    with pytest.raises(ValueError, match="SOURCE_RECEIPT_CHANGED"):
        verify_source_bundle(widget, bundle, expected_receipt_sha256=binding["receipt_sha256"])


@pytest.mark.parametrize("tranche", [2, 3, 4, 5, 6])
@pytest.mark.parametrize("existing_output", [False, True])
def test_direct_tranche_refuses_failed_source_before_any_output(tmp_path, monkeypatch, tranche, existing_output):
    module = importlib.import_module(f"mamey.interactive_figures.figure_set_renderer_tranche{tranche}")
    widget, bundle, _, _ = _bound_sources(tmp_path, status="FAIL")
    monkeypatch.setattr(module, "_load", lambda _path, **kwargs: (widget, {}, [], []))
    def unexpected(*args, **kwargs):
        pytest.fail("chart construction must not run for rejected sources")
    monkeypatch.setattr(module, f"build_charts_{tranche}", unexpected)
    destination = tmp_path / "out"
    if existing_output:
        destination.mkdir()
        (destination / "sentinel").write_bytes(b"original")
    args = (widget, bundle, tmp_path / "leads.csv", destination) if tranche == 6 else (widget, bundle, destination)
    with pytest.raises(ValueError, match="SOURCE_BUNDLE_NOT_USABLE"):
        getattr(module, f"render_tranche_{tranche}")(*args)
    assert destination.exists() is existing_output
    if existing_output:
        assert {p.name: p.read_bytes() for p in destination.iterdir()} == {"sentinel": b"original"}


def test_tranche_source_drift_prevents_a_success_receipt_without_rendering(tmp_path, monkeypatch):
    module = importlib.import_module("mamey.interactive_figures.figure_set_renderer_tranche2")
    widget, bundle, _, _ = _bound_sources(tmp_path, names=module.SOURCE_TABLES_2)
    monkeypatch.setattr(module, "_load", lambda _path, **kwargs: (widget, {}, [], []))
    monkeypatch.setattr(module, "build_registry", lambda: [])
    monkeypatch.setattr(module, "_validate_outputs", lambda *args, **kwargs: [])
    def empty_charts_after_drift(*args, **kwargs):
        (bundle / "BGC_RECORDS.csv").write_text("value\nchanged\n", encoding="utf-8")
        return []
    monkeypatch.setattr(module, "build_charts_2", empty_charts_after_drift)
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="SOURCE_TABLE_BINDING_FAILED"):
        module.render_tranche_2(widget, bundle, destination)
    assert not (destination / "TRANCHE_2_QA_RECEIPT.json").exists()


def test_atlas_checks_source_hashes_before_any_tranche_or_output(tmp_path, monkeypatch):
    widget, bundle, _, _ = _bound_sources(tmp_path)
    (bundle / "fixture.csv").write_text("value\nchanged\n", encoding="utf-8")
    def unexpected(*args, **kwargs):
        pytest.fail("tranche must not run for changed saved sources")
    for name in ("render_tranche", "render_tranche_2", "render_tranche_3", "render_tranche_4", "render_tranche_5", "render_tranche_6"):
        monkeypatch.setattr(figure_atlas, name, unexpected)
    destination = tmp_path / "atlas"
    with pytest.raises(FigurePolicyError, match="FIGURE_ATLAS_SOURCE_BINDING_INVALID"):
        figure_atlas.render_implemented_atlas(widget, bundle, destination)
    assert not destination.exists()


def test_tranche6_rejects_source_before_reading_optional_ledger(tmp_path, monkeypatch):
    module = importlib.import_module("mamey.interactive_figures.figure_set_renderer_tranche6")
    widget, bundle, _, _ = _bound_sources(tmp_path, status="FAIL")
    monkeypatch.setattr(module, "_load", lambda _path, **kwargs: (widget, {}, [], []))
    def unexpected_ledger(*args, **kwargs):
        pytest.fail("lead ledger must not be read for rejected source bindings")
    monkeypatch.setattr(module, "_read_lead_ledger", unexpected_ledger)
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="FIGURE_INPUT_SOURCE_BUNDLE_NOT_USABLE"):
        module.render_tranche_6(widget, bundle, tmp_path / "missing_ledger.csv", destination)
    assert not destination.exists()


@pytest.mark.parametrize("tranche", [2, 3, 4, 5, 6])
def test_direct_tranche_keeps_source_receipt_binding_with_fake_charts(tmp_path, monkeypatch, tranche):
    # Chart builders and validation are deliberately fakes: this checks source
    # admission/final binding and receipt plumbing, not figure QA or rendering.
    module = importlib.import_module(f"mamey.interactive_figures.figure_set_renderer_tranche{tranche}")
    names = getattr(module, f"SOURCE_TABLES_{tranche}")
    widget, bundle, receipt_path, _ = _bound_sources(tmp_path, names=names)
    monkeypatch.setattr(module, "_load", lambda _path, **kwargs: (widget, {}, ["TEST-STUDY"], ["TEST-STUDY"]))
    monkeypatch.setattr(module, "build_registry", lambda: [])
    monkeypatch.setattr(module, f"build_charts_{tranche}", lambda *args, **kwargs: [])
    monkeypatch.setattr(module, "_validate_outputs", lambda *args, **kwargs: [])
    ledger = tmp_path / "leads.csv"
    ledger.write_text("strain\nTEST-STUDY\n", encoding="utf-8")
    destination = tmp_path / "out"
    args = (widget, bundle, ledger, destination) if tranche == 6 else (widget, bundle, destination)
    result = getattr(module, f"render_tranche_{tranche}")(*args)
    assert result["source"]["source_bundle_receipt_sha256"] == _sha(receipt_path)
    stored = json.loads((destination / f"TRANCHE_{tranche}_QA_RECEIPT.json").read_text())
    assert stored["source"] == result["source"]
    if tranche == 6:
        assert result["source"]["lead_ledger_sha256"] == _sha(ledger)
        assert result["lead_strains"] == ["TEST-STUDY"]


@pytest.mark.parametrize("fault,code", [
    ("missing_receipt", "FIGURE_INPUT_SOURCE_RECEIPT_MISSING"),
    ("failed", "FIGURE_INPUT_SOURCE_BUNDLE_NOT_USABLE"),
    ("widget", "FIGURE_INPUT_WIDGET_BINDING_MISMATCH"),
    ("missing_used_table", "FIGURE_INPUT_SOURCE_TABLE_BINDING_FAILED"),
    ("changed_used_table", "FIGURE_INPUT_SOURCE_TABLE_BINDING_FAILED"),
])
def test_owner_adapter_keeps_existing_source_refusal_codes(tmp_path, monkeypatch, fault, code):
    module = importlib.import_module("mamey.interactive_figures.owner_kept_inputs")
    widget, bundle, receipt_path, receipt = _bound_sources(tmp_path, names=module.REQUIRED_SOURCE_TABLES)
    monkeypatch.setattr(module, "_load_with_benchmarks", lambda *args, **kwargs: (widget, {}, [], [], [], []))
    if fault == "missing_receipt":
        receipt_path.unlink()
    elif fault == "failed":
        receipt["status"] = "FAIL"
        _store(receipt_path, receipt)
    elif fault == "widget":
        widget.write_text("{}", encoding="utf-8")
    elif fault == "missing_used_table":
        (bundle / module.REQUIRED_SOURCE_TABLES[0]).unlink()
    elif fault == "changed_used_table":
        (bundle / module.REQUIRED_SOURCE_TABLES[0]).write_text("value\nchanged\n", encoding="utf-8")
    destination = tmp_path / "adapted"
    with pytest.raises(ValueError, match=code):
        module.build_owner_kept_inputs(widget, bundle, destination)
    assert not destination.exists()

"""IO-only guards for parsed CSV snapshots, parent atlas receipt and lead-ledger bytes.

Tool/render work is faked; pure chart-construction parity checks use empty synthetic
CSV tables only. No test result is claimed until parent-owned serial execution.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest

from mamey.interactive_figures import figure_atlas, owner_kept_inputs
from mamey.interactive_figures.figure_source_bundle import read_verified_source_tables, verify_source_bundle


def _sha(path):
    with path.open("rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def _sources(tmp_path, names, *, rows=True):
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps({"strains": {"TEST-STUDY": {"governance": "GOVERNED"}}}), encoding="utf-8")
    bundle = tmp_path / "sources"
    bundle.mkdir()
    outputs = []
    for name in names:
        table = bundle / name
        table.write_text("strain,value\n" + ("TEST-STUDY,1\n" if rows else ""), encoding="utf-8")
        outputs.append({"path": name, "sha256": _sha(table)})
    receipt_path = bundle / "SOURCE_BUNDLE_RECEIPT.json"
    receipt_path.write_text(json.dumps({"status": "PASS", "source": {"widget_sha256": _sha(widget)}, "outputs": outputs}), encoding="utf-8")
    return widget, bundle, receipt_path


def _substitute_read(monkeypatch, target, replacement):
    original = Path.read_bytes
    def read_bytes(path):
        return replacement if path.resolve() == target.resolve() else original(path)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)


def _module(tranche):
    return importlib.import_module(f"mamey.interactive_figures.figure_set_renderer_tranche{tranche}")


def _call(module, tranche, widget, bundle, ledger, destination, **kwargs):
    args = (widget, bundle, ledger, destination) if tranche == 6 else (widget, bundle, destination)
    return getattr(module, f"render_tranche_{tranche}")(*args, **kwargs)


def _fake_work(monkeypatch, module, tranche, builder=None):
    monkeypatch.setattr(module, "build_registry", lambda: [])
    monkeypatch.setattr(module, "_validate_outputs", lambda *args, **kwargs: [])
    monkeypatch.setattr(module, f"build_charts_{tranche}", builder or (lambda *args, **kwargs: []))


def test_common_csv_reader_parses_exact_bytes_named_by_initial_receipt(tmp_path):
    widget, bundle, _ = _sources(tmp_path, ("fixture.csv",))
    binding = verify_source_bundle(widget, bundle, required_tables=("fixture.csv",))
    parsed = read_verified_source_tables(bundle, binding, tables=("fixture.csv",))
    assert parsed == {"fixture.csv": [{"strain": "TEST-STUDY", "value": "1"}]}


def test_changed_then_restored_csv_read_cannot_evade_consumed_hash(tmp_path, monkeypatch):
    widget, bundle, _ = _sources(tmp_path, ("fixture.csv",))
    binding = verify_source_bundle(widget, bundle, required_tables=("fixture.csv",))
    target = bundle / "fixture.csv"
    expected = _sha(target)
    _substitute_read(monkeypatch, target, b"strain,value\nOTHER-STUDY,99\n")
    assert _sha(target) == expected
    # The initial/final live file remains original, but the consumed bytes differ.
    verify_source_bundle(widget, bundle, expected_receipt_sha256=binding["receipt_sha256"])
    with pytest.raises(ValueError, match="FIGURE_INPUT_SOURCE_TABLE_CONSUMED_MISMATCH: fixture.csv"):
        read_verified_source_tables(bundle, binding, tables=("fixture.csv",))


@pytest.mark.parametrize("tranche", [2, 3, 4, 5, 6])
def test_direct_renderer_refuses_substituted_csv_before_output_or_builder(tmp_path, monkeypatch, tranche):
    module = _module(tranche)
    names = getattr(module, f"SOURCE_TABLES_{tranche}")
    widget, bundle, _ = _sources(tmp_path, names)
    _substitute_read(monkeypatch, bundle / names[0], b"strain,value\nOTHER-STUDY,99\n")
    monkeypatch.setattr(module, f"build_charts_{tranche}", lambda *args, **kwargs: pytest.fail("builder must not consume unbound CSV"))
    ledger = tmp_path / "leads.csv"
    ledger.write_text("strain\nTEST-STUDY\n", encoding="utf-8")
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="FIGURE_INPUT_SOURCE_TABLE_CONSUMED_MISMATCH"):
        _call(module, tranche, widget, bundle, ledger, destination)
    assert not destination.exists()


def test_owner_adapter_refuses_substituted_csv_before_staging(tmp_path, monkeypatch):
    names = owner_kept_inputs.REQUIRED_SOURCE_TABLES
    widget, bundle, _ = _sources(tmp_path, names)
    _substitute_read(monkeypatch, bundle / names[0], b"strain,value\nOTHER-STUDY,99\n")
    destination = tmp_path / "adapted"
    with pytest.raises(ValueError, match="FIGURE_INPUT_SOURCE_TABLE_CONSUMED_MISMATCH"):
        owner_kept_inputs.build_owner_kept_inputs(widget, bundle, destination)
    assert not destination.exists()
    assert not list(tmp_path.glob(".adapted.stage-*"))


@pytest.mark.parametrize("tranche", [2, 3, 4, 5, 6])
def test_renderers_supply_verified_parsed_tables_to_builder(tmp_path, monkeypatch, tranche):
    module = _module(tranche)
    names = getattr(module, f"SOURCE_TABLES_{tranche}")
    widget, bundle, receipt_path = _sources(tmp_path, names)
    seen = []
    def capture(*args, parsed_tables=None):
        seen.append(parsed_tables)
        assert set(parsed_tables) == set(names)
        assert all(rows == [{"strain": "TEST-STUDY", "value": "1"}] for rows in parsed_tables.values())
        return []
    _fake_work(monkeypatch, module, tranche, capture)
    ledger = tmp_path / "leads.csv"
    ledger.write_text("strain\nTEST-STUDY\n", encoding="utf-8")
    result = _call(module, tranche, widget, bundle, ledger, tmp_path / "out", expected_receipt_sha256=_sha(receipt_path))
    assert len(seen) == 1
    assert result["source"]["source_bundle_receipt_sha256"] == _sha(receipt_path)


@pytest.mark.parametrize("tranche", [2, 3, 4, 5])
def test_pure_chart_builders_keep_legacy_results_without_rereading_live_tables(tmp_path, monkeypatch, tranche):
    module = _module(tranche)
    names = getattr(module, f"SOURCE_TABLES_{tranche}")
    widget, bundle, _ = _sources(tmp_path, names, rows=False)
    binding = verify_source_bundle(widget, bundle, required_tables=names)
    parsed = read_verified_source_tables(bundle, binding, tables=names)
    payload = json.loads(widget.read_text())
    args = (payload, ["TEST-STUDY"], bundle) if tranche == 5 else (payload, ["TEST-STUDY"], ["TEST-STUDY"], bundle)
    builder = getattr(module, f"build_charts_{tranche}")
    legacy = builder(*args)
    # Subsequent path content cannot affect the already verified rows used below.
    for name in names:
        (bundle / name).write_text("unrelated\nchanged\n", encoding="utf-8")
    monkeypatch.setattr(module, "_read_csv" if tranche == 2 else "_read", lambda *args: pytest.fail("live CSV reread"))
    bound = builder(*args, parsed_tables=parsed)
    assert bound == legacy


def test_tranche6_forwards_same_parsed_mapping_to_its_child_builders(monkeypatch):
    module = _module(6)
    parsed = {"fixture.csv": []}
    seen = []
    def child(*args, parsed_tables=None):
        seen.append(parsed_tables)
        return []
    source = module.Chart("FIXTURE_SOURCE", "scatter", "Fixture", "Synthetic context",
                          [{"strain": "TEST-STUDY", "x_value": 1, "y_value": 2}], {"label": "strain"})
    monkeypatch.setattr(module, "build_charts", lambda *args: [source])
    for tranche in range(2, 6):
        monkeypatch.setattr(module, f"build_charts_{tranche}", child)
    monkeypatch.setattr(module, "SOURCE_TO_LEAD", (("fixture", "FIXTURE_SOURCE", "FIXTURE_LEAD"),))
    monkeypatch.setattr(module, "IMPLEMENTED_IDS_6", ("FIXTURE_LEAD",))
    charts = module.build_charts_6({"strains": {}}, ["TEST-STUDY"], ["TEST-STUDY"], Path("unused"),
                                   {"TEST-STUDY": ["STRAIN_LEVEL"]}, parsed_tables=parsed)
    assert [chart.figure_id for chart in charts] == ["FIXTURE_LEAD"]
    assert charts[0].rows == [{"strain": "TEST-STUDY", "x_value": 1, "y_value": 2,
                              "lead_context": "YES", "declared_lead_scope": "STRAIN_LEVEL"}]
    assert len(seen) == 4 and all(item is parsed for item in seen)


@pytest.mark.parametrize("tranche", [2, 3, 4, 5, 6])
def test_child_renderer_refuses_different_parent_receipt_before_widget_or_ledger(tmp_path, monkeypatch, tranche):
    module = _module(tranche)
    widget, bundle, _ = _sources(tmp_path, getattr(module, f"SOURCE_TABLES_{tranche}"))
    monkeypatch.setattr(module, "_load", lambda *args, **kwargs: pytest.fail("widget parse before parent receipt guard"))
    if tranche == 6:
        monkeypatch.setattr(module, "_read_lead_ledger", lambda *args, **kwargs: pytest.fail("ledger parse before parent receipt guard"))
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="FIGURE_INPUT_SOURCE_RECEIPT_CHANGED"):
        _call(module, tranche, widget, bundle, tmp_path / "missing.csv", destination, expected_receipt_sha256="0" * 64)
    assert not destination.exists()


def test_atlas_child_cannot_admit_changed_then_restored_receipt_and_widget(tmp_path, monkeypatch):
    widget, bundle, receipt_path = _sources(tmp_path, figure_atlas.SOURCE_TABLES_ATLAS)
    original_widget, original_receipt = widget.read_bytes(), receipt_path.read_bytes()
    def empty(*args, **kwargs):
        return {"status": "PASS", "implemented_count": 0, "implemented_ids": [], "figures": []}
    for name in ("render_tranche", "render_tranche_3", "render_tranche_4", "render_tranche_5"):
        monkeypatch.setattr(figure_atlas, name, empty)
    child = _module(2)
    _fake_work(monkeypatch, child, 2)
    def replace_restore(*args, **kwargs):
        widget.write_text(json.dumps({"strains": {"OTHER-STUDY": {"governance": "GOVERNED"}}}))
        changed = json.loads(original_receipt)
        changed["source"]["widget_sha256"] = _sha(widget)
        receipt_path.write_text(json.dumps(changed))
        try:
            return child.render_tranche_2(*args, **kwargs)
        finally:
            widget.write_bytes(original_widget)
            receipt_path.write_bytes(original_receipt)
    monkeypatch.setattr(figure_atlas, "render_tranche_2", replace_restore)
    destination = tmp_path / "atlas"
    with pytest.raises(ValueError, match="FIGURE_INPUT_SOURCE_RECEIPT_CHANGED"):
        figure_atlas.render_implemented_atlas(widget, bundle, destination)
    assert widget.read_bytes() == original_widget and receipt_path.read_bytes() == original_receipt
    assert not (destination / "CUMULATIVE_175_QA_RECEIPT.json").exists()
    assert not (destination / "tranche_2").exists()


def test_tranche6_binds_exact_consumed_ledger_even_when_live_hash_is_restored(tmp_path, monkeypatch):
    module = _module(6)
    widget, bundle, _ = _sources(tmp_path, module.SOURCE_TABLES_6)
    ledger = tmp_path / "leads.csv"
    ledger.write_text("strain\nTEST-STUDY\n", encoding="utf-8")
    expected = _sha(ledger)
    _substitute_read(monkeypatch, ledger, b"strain\nOTHER-STUDY\n")
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="FIGURE_INPUT_LEAD_LEDGER_CONSUMED_MISMATCH"):
        module.render_tranche_6(widget, bundle, ledger, destination, expected_lead_ledger_sha256=expected)
    assert _sha(ledger) == expected and not destination.exists()


def test_tranche6_final_ledger_drift_refuses_success_receipt(tmp_path, monkeypatch):
    module = _module(6)
    widget, bundle, _ = _sources(tmp_path, module.SOURCE_TABLES_6)
    ledger = tmp_path / "leads.csv"
    ledger.write_text("strain\nTEST-STUDY\n", encoding="utf-8")
    def drift(*args, **kwargs):
        ledger.write_text("strain\nOTHER-STUDY\n", encoding="utf-8")
        return []
    _fake_work(monkeypatch, module, 6, drift)
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="FIGURE_INPUT_LEAD_LEDGER_CHANGED"):
        module.render_tranche_6(widget, bundle, ledger, destination)
    assert not (destination / "TRANCHE_6_QA_RECEIPT.json").exists()
    assert not (destination / "FIGURE_MANIFEST.json").exists()


def test_atlas_passes_receipt_and_ledger_snapshot_to_children(tmp_path, monkeypatch):
    widget, bundle, receipt_path = _sources(tmp_path, figure_atlas.SOURCE_TABLES_ATLAS)
    ledger = tmp_path / "leads.csv"
    ledger.write_text("strain\nTEST-STUDY\n", encoding="utf-8")
    seen = {}
    def fake(name):
        def render(*args, **kwargs):
            seen[name] = kwargs
            return {"status": "PASS", "implemented_count": 0, "implemented_ids": [], "figures": []}
        return render
    for name in ("render_tranche", "render_tranche_2", "render_tranche_3", "render_tranche_4", "render_tranche_5", "render_tranche_6"):
        monkeypatch.setattr(figure_atlas, name, fake(name))
    result = figure_atlas.render_implemented_atlas(widget, bundle, tmp_path / "atlas", lead_ledger=ledger)
    assert seen["render_tranche"] == {"expected_widget_sha256": _sha(widget)}
    assert all(seen[f"render_tranche_{n}"] == {"expected_receipt_sha256": _sha(receipt_path)} for n in range(2, 6))
    assert seen["render_tranche_6"] == {"expected_receipt_sha256": _sha(receipt_path), "expected_lead_ledger_sha256": _sha(ledger)}
    assert result["lead_ledger_sha256"] == _sha(ledger)
    assert result["status"] == "FAIL"  # fake empty tranches fail real atlas reconciliation


def test_atlas_final_ledger_drift_refuses_top_receipt(tmp_path, monkeypatch):
    widget, bundle, _ = _sources(tmp_path, figure_atlas.SOURCE_TABLES_ATLAS)
    ledger = tmp_path / "leads.csv"
    ledger.write_text("strain\nTEST-STUDY\n", encoding="utf-8")
    def fake(*args, **kwargs):
        ledger.write_text("strain\nOTHER-STUDY\n", encoding="utf-8")
        return {"status": "PASS", "implemented_count": 0, "implemented_ids": [], "figures": []}
    for name in ("render_tranche", "render_tranche_2", "render_tranche_3", "render_tranche_4", "render_tranche_5", "render_tranche_6"):
        monkeypatch.setattr(figure_atlas, name, fake)
    destination = tmp_path / "atlas"
    with pytest.raises(ValueError, match="FIGURE_ATLAS_LEAD_LEDGER_CHANGED"):
        figure_atlas.render_implemented_atlas(widget, bundle, destination, lead_ledger=ledger)
    assert not (destination / "CUMULATIVE_200_QA_RECEIPT.json").exists()

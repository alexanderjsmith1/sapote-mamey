"""Portable snapshot/output guard cases; figure builders and tools are fakes.

These tests check admission and receipt plumbing only. They do not claim visual,
biological, publication, or release validation.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest

from mamey.interactive_figures import figure_atlas, figure_set_renderer as renderer
from mamey.interactive_figures import owner_kept_inputs


def _sha(path):
    with path.open("rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def _widget(tmp_path):
    path = tmp_path / "widget.json"
    path.write_text(json.dumps({"strains": {"TEST-STUDY": {"governance": "GOVERNED"}}}), encoding="utf-8")
    return path


def _sources(tmp_path, names):
    widget = _widget(tmp_path)
    bundle = tmp_path / "sources"
    bundle.mkdir()
    outputs = []
    for name in names:
        path = bundle / name
        path.write_text("strain,value\nTEST-STUDY,1\n", encoding="utf-8")
        outputs.append({"path": name, "sha256": _sha(path)})
    receipt_path = bundle / "SOURCE_BUNDLE_RECEIPT.json"
    receipt_path.write_text(json.dumps({
        "status": "PASS", "source": {"widget_sha256": _sha(widget)}, "outputs": outputs,
    }), encoding="utf-8")
    return widget, bundle, receipt_path


def _substitute_widget_read(monkeypatch, widget):
    # verify_source_bundle hashes via open(), while loaders consume read_bytes().
    # The disk path remains unchanged, exposing a hash-live-path/parse-other-bytes gap.
    original = Path.read_bytes
    altered = json.dumps({"strains": {"OTHER-STUDY": {"governance": "GOVERNED"}}}).encode("utf-8")
    def substituted(path):
        return altered if path.resolve() == widget.resolve() else original(path)
    monkeypatch.setattr(Path, "read_bytes", substituted)


def _module(tranche):
    return renderer if tranche == 1 else importlib.import_module(
        f"mamey.interactive_figures.figure_set_renderer_tranche{tranche}"
    )


def _call(module, tranche, widget, bundle, destination, ledger):
    if tranche == 1:
        return module.render_tranche(widget, destination)
    args = (widget, bundle, ledger, destination) if tranche == 6 else (widget, bundle, destination)
    return getattr(module, f"render_tranche_{tranche}")(*args)


def _fake_render_work(monkeypatch, module, tranche, build=None):
    monkeypatch.setattr(module, "build_registry", lambda: [])
    monkeypatch.setattr(module, "_validate_outputs", lambda *args, **kwargs: [])
    monkeypatch.setattr(module, "build_charts" if tranche == 1 else f"build_charts_{tranche}", build or (lambda *args, **kwargs: []))
    if tranche == 1:
        monkeypatch.setattr(module, "_native_svg_rasterization_capability", lambda: {"state": "FAKE_NOT_PROBED"})


@pytest.mark.parametrize("extended", [False, True])
def test_loaders_preserve_return_shape_and_matching_snapshot(tmp_path, extended):
    widget = _widget(tmp_path)
    loader = renderer._load_with_benchmarks if extended else renderer._load
    default = loader(widget)
    bound = loader(widget, expected_widget_sha256=_sha(widget))
    assert len(default) == (6 if extended else 4)
    assert bound == default
    assert bound[2:4] == (["TEST-STUDY"], ["TEST-STUDY"])


@pytest.mark.parametrize("extended", [False, True])
def test_loaders_check_exact_consumed_bytes_before_json_parse(tmp_path, monkeypatch, extended):
    widget = _widget(tmp_path)
    expected = _sha(widget)
    _substitute_widget_read(monkeypatch, widget)
    assert _sha(widget) == expected  # live path/hash itself remains unchanged
    loader = renderer._load_with_benchmarks if extended else renderer._load
    with pytest.raises(ValueError, match="FIGURE_INPUT_WIDGET_BINDING_MISMATCH"):
        loader(widget, expected_widget_sha256=expected)


def test_bound_loader_hash_guard_wins_over_invalid_json(tmp_path, monkeypatch):
    widget = _widget(tmp_path)
    expected = _sha(widget)
    original = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda p: b"not JSON" if p.resolve() == widget.resolve() else original(p))
    with pytest.raises(ValueError, match="FIGURE_INPUT_WIDGET_BINDING_MISMATCH"):
        renderer._load(widget, expected_widget_sha256=expected)


@pytest.mark.parametrize("tranche", [1, 2, 3, 4, 5, 6])
def test_direct_renderers_reject_different_consumed_widget_bytes_before_output(tmp_path, monkeypatch, tranche):
    module = _module(tranche)
    names = ("fixture.csv",) if tranche == 1 else getattr(module, f"SOURCE_TABLES_{tranche}")
    widget, bundle, _ = _sources(tmp_path, names)
    _substitute_widget_read(monkeypatch, widget)
    def unexpected(*args, **kwargs):
        pytest.fail("no chart/tool/ledger work for a rejected widget snapshot")
    monkeypatch.setattr(module, "build_charts" if tranche == 1 else f"build_charts_{tranche}", unexpected)
    if tranche == 1:
        monkeypatch.setattr(module, "_native_svg_rasterization_capability", unexpected)
    if tranche == 6:
        monkeypatch.setattr(module, "_read_lead_ledger", unexpected)
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="FIGURE_INPUT_WIDGET_BINDING_MISMATCH"):
        _call(module, tranche, widget, bundle, destination, tmp_path / "missing.csv")
    assert not destination.exists()


def test_owner_adapter_rejects_different_consumed_widget_before_stage(tmp_path, monkeypatch):
    widget, bundle, _ = _sources(tmp_path, owner_kept_inputs.REQUIRED_SOURCE_TABLES)
    _substitute_widget_read(monkeypatch, widget)
    def unexpected(*args, **kwargs):
        pytest.fail("no table/staging work for a rejected widget snapshot")
    monkeypatch.setattr(owner_kept_inputs, "_read_csv", unexpected)
    destination = tmp_path / "adapted"
    with pytest.raises(ValueError, match="FIGURE_INPUT_WIDGET_BINDING_MISMATCH"):
        owner_kept_inputs.build_owner_kept_inputs(widget, bundle, destination)
    assert not destination.exists()
    assert not list(tmp_path.glob(".adapted.stage-*"))


def test_atlas_rejects_different_consumed_widget_before_root_or_tranches(tmp_path, monkeypatch):
    widget, bundle, _ = _sources(tmp_path, figure_atlas.SOURCE_TABLES_ATLAS)
    _substitute_widget_read(monkeypatch, widget)
    monkeypatch.setattr(figure_atlas, "render_tranche", lambda *args, **kwargs: pytest.fail("tranche invoked"))
    destination = tmp_path / "atlas"
    with pytest.raises(ValueError, match="FIGURE_ATLAS_SOURCE_BINDING_INVALID.*FIGURE_INPUT_WIDGET_BINDING_MISMATCH"):
        figure_atlas.render_implemented_atlas(widget, bundle, destination)
    assert not destination.exists()


@pytest.mark.parametrize("tranche", [1, 2, 3, 4, 5, 6])
@pytest.mark.parametrize("prior_kind", ["pass", "empty", "file"])
def test_direct_renderers_preserve_any_prior_destination(tmp_path, monkeypatch, tranche, prior_kind):
    module = _module(tranche)
    names = ("fixture.csv",) if tranche == 1 else getattr(module, f"SOURCE_TABLES_{tranche}")
    widget, bundle, _ = _sources(tmp_path, names)
    def unexpected(*args, **kwargs):
        pytest.fail("chart/tool/ledger work must not run for a reused destination")
    monkeypatch.setattr(module, "build_charts" if tranche == 1 else f"build_charts_{tranche}", unexpected)
    if tranche == 1:
        monkeypatch.setattr(module, "_native_svg_rasterization_capability", unexpected)
    if tranche == 6:
        monkeypatch.setattr(module, "_read_lead_ledger", unexpected)
    destination = tmp_path / "out"
    if prior_kind == "file":
        destination.write_bytes(b"original file")
        before = destination.read_bytes()
    else:
        destination.mkdir()
        if prior_kind == "pass":
            (destination / f"TRANCHE_{tranche}_QA_RECEIPT.json").write_text('{"status":"PASS","old":true}')
            (destination / "sentinel").write_bytes(b"original output")
        before = {p.name: p.read_bytes() for p in destination.iterdir()}
    with pytest.raises(ValueError, match="FIGURE_OUTPUT_EXISTS"):
        _call(module, tranche, widget, bundle, destination, tmp_path / "missing.csv")
    after = destination.read_bytes() if prior_kind == "file" else {p.name: p.read_bytes() for p in destination.iterdir()}
    assert after == before


@pytest.mark.parametrize("prior_kind", ["pass", "empty", "file"])
def test_atlas_preserves_any_prior_destination(tmp_path, monkeypatch, prior_kind):
    widget, bundle, _ = _sources(tmp_path, figure_atlas.SOURCE_TABLES_ATLAS)
    destination = tmp_path / "atlas"
    if prior_kind == "file":
        destination.write_bytes(b"original file")
        before = destination.read_bytes()
    else:
        destination.mkdir()
        if prior_kind == "pass":
            (destination / "CUMULATIVE_175_QA_RECEIPT.json").write_text('{"status":"PASS","old":true}')
            (destination / "sentinel").write_bytes(b"original atlas")
        before = {p.name: p.read_bytes() for p in destination.iterdir()}
    monkeypatch.setattr(figure_atlas, "render_tranche", lambda *args, **kwargs: pytest.fail("tranche invoked"))
    with pytest.raises(ValueError, match="FIGURE_ATLAS_OUTPUT_EXISTS"):
        figure_atlas.render_implemented_atlas(widget, bundle, destination)
    after = destination.read_bytes() if prior_kind == "file" else {p.name: p.read_bytes() for p in destination.iterdir()}
    assert after == before


@pytest.mark.parametrize("tranche", [1, 2, 3, 4, 5, 6])
def test_direct_renderers_refuse_final_widget_drift_without_success_receipt(tmp_path, monkeypatch, tranche):
    module = _module(tranche)
    names = ("fixture.csv",) if tranche == 1 else getattr(module, f"SOURCE_TABLES_{tranche}")
    widget, bundle, _ = _sources(tmp_path, names)
    def drift_after_parse(*args, **kwargs):
        widget.write_text(json.dumps({"strains": {"CHANGED-STUDY": {"governance": "GOVERNED"}}}), encoding="utf-8")
        return []
    _fake_render_work(monkeypatch, module, tranche, drift_after_parse)
    ledger = tmp_path / "leads.csv"
    ledger.write_text("strain\nTEST-STUDY\n", encoding="utf-8")
    destination = tmp_path / "out"
    code = "FIGURE_INPUT_WIDGET_BINDING_CHANGED" if tranche == 1 else "FIGURE_INPUT_WIDGET_BINDING_MISMATCH"
    with pytest.raises(ValueError, match=code):
        _call(module, tranche, widget, bundle, destination, ledger)
    assert not (destination / f"TRANCHE_{tranche}_QA_RECEIPT.json").exists()
    assert not (destination / "FIGURE_MANIFEST.json").exists()


def test_tranche1_positive_fake_work_records_exact_snapshot(tmp_path, monkeypatch):
    widget = _widget(tmp_path)
    expected = _sha(widget)
    _fake_render_work(monkeypatch, renderer, 1)
    destination = tmp_path / "out"
    result = renderer.render_tranche(widget, destination, expected_widget_sha256=expected)
    assert result["source"]["sha256"] == expected
    assert result["native_svg_rasterization"]["state"] == "FAKE_NOT_PROBED"
    stored = json.loads((destination / "TRANCHE_1_QA_RECEIPT.json").read_text())
    assert stored["source"] == result["source"]


def test_tranche1_explicit_wrong_snapshot_refuses_before_probe(tmp_path, monkeypatch):
    widget = _widget(tmp_path)
    monkeypatch.setattr(renderer, "_native_svg_rasterization_capability", lambda: pytest.fail("native tool probe invoked"))
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="FIGURE_INPUT_WIDGET_BINDING_MISMATCH"):
        renderer.render_tranche(widget, destination, expected_widget_sha256="0" * 64)
    assert not destination.exists()


def test_caption_metadata_binds_hash_and_size_from_same_verified_bytes(tmp_path, monkeypatch):
    widget = _widget(tmp_path)
    expected = _sha(widget)
    payload = json.loads(widget.read_text())
    chart = renderer.Chart("TEST", "bar", "Fixture", "", [], {"category": "fixture", "value": "value"})
    metadata = renderer._caption_metadata(
        chart, {}, source=widget, payload=payload, all_ids=["TEST-STUDY"], governed=["TEST-STUDY"],
        benchmark_ids=[], selected_benchmarks=[], expected_widget_sha256=expected,
    )
    assert f"sha256={expected}; bytes={widget.stat().st_size}" in metadata["source_bindings"]
    _substitute_widget_read(monkeypatch, widget)
    with pytest.raises(ValueError, match="FIGURE_INPUT_WIDGET_BINDING_MISMATCH: caption"):
        renderer._caption_metadata(
            chart, {}, source=widget, payload=payload, all_ids=["TEST-STUDY"], governed=["TEST-STUDY"],
            benchmark_ids=[], selected_benchmarks=[], expected_widget_sha256=expected,
        )


def _fake_atlas_tranches(monkeypatch, calls, drift=None):
    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        if drift is not None:
            drift()
        # Deliberately no figure work; atlas render reconciliation stays FAIL.
        return {"status": "PASS", "implemented_count": 0, "implemented_ids": [], "figures": []}
    for name in ("render_tranche", "render_tranche_2", "render_tranche_3", "render_tranche_4", "render_tranche_5"):
        monkeypatch.setattr(figure_atlas, name, fake)


def test_atlas_passes_bound_snapshot_to_tranche1_and_records_final_binding(tmp_path, monkeypatch):
    widget, bundle, receipt_path = _sources(tmp_path, figure_atlas.SOURCE_TABLES_ATLAS)
    expected = _sha(widget)
    calls = []
    _fake_atlas_tranches(monkeypatch, calls)
    destination = tmp_path / "atlas"
    result = figure_atlas.render_implemented_atlas(widget, bundle, destination)
    assert calls[0][1] == {"expected_widget_sha256": expected}
    assert all(kwargs == {"expected_receipt_sha256": _sha(receipt_path)} for _, kwargs in calls[1:])
    assert result["widget_sha256"] == expected
    assert result["source_bundle_receipt_sha256"] == _sha(receipt_path)
    assert result["status"] == "FAIL"  # fake empty figures do not satisfy real atlas QA
    assert (destination / "CUMULATIVE_175_QA_RECEIPT.json").is_file()


def test_atlas_final_widget_drift_cannot_commit_success_receipt(tmp_path, monkeypatch):
    widget, bundle, _ = _sources(tmp_path, figure_atlas.SOURCE_TABLES_ATLAS)
    calls = []
    _fake_atlas_tranches(monkeypatch, calls, lambda: widget.write_text("{}", encoding="utf-8"))
    destination = tmp_path / "atlas"
    with pytest.raises(ValueError, match="FIGURE_ATLAS_SOURCE_BINDING_CHANGED"):
        figure_atlas.render_implemented_atlas(widget, bundle, destination)
    assert not (destination / "CUMULATIVE_175_QA_RECEIPT.json").exists()
    assert not (destination / "CUMULATIVE_175_FIGURE_MANIFEST.json").exists()

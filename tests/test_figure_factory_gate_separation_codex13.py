"""CODEX-13: Figure Factory render PASS must not imply scientific readiness."""

from __future__ import annotations

import json

import pytest

from mamey.figure_policy import FigurePolicyError
from mamey.interactive_figures import figure_atlas


@pytest.mark.parametrize("source_status", ["PASS", "PASS_WITH_ISSUES"])
def test_atlas_receipt_separates_independent_gates(tmp_path, monkeypatch, source_status):
    figure = {
        "figure_set_id": "FS001",
        "svg": "figures/FS001.svg",
        "data_csv": "data/FS001.csv",
        "caption_methods": "text/FS001.md",
        "svg_sha256": "a" * 64,
    }

    def fake_renderer(*args, **kwargs):
        out = args[-1]
        out.mkdir(parents=True, exist_ok=True)
        (out / "OPEN_FIGURE_SET_TRANCHE_1.html").write_text("ok", encoding="utf-8")
        (out / "FIGURE_MANIFEST.json").write_text("{}", encoding="utf-8")
        return {
            "status": "PASS", "implemented_count": 1,
            "implemented_ids": ["FS001"], "figures": [figure],
        }

    monkeypatch.setattr(figure_atlas, "render_tranche", fake_renderer)
    monkeypatch.setattr(figure_atlas, "render_tranche_2", fake_renderer)
    monkeypatch.setattr(figure_atlas, "render_tranche_3", fake_renderer)
    monkeypatch.setattr(figure_atlas, "render_tranche_4", fake_renderer)
    monkeypatch.setattr(figure_atlas, "render_tranche_5", fake_renderer)

    # The synthetic count/IDs deliberately fail atlas reconciliation; the gate
    # separation itself must still be present and publication must stay unset.
    source_bundle = tmp_path / "bundle"
    source_bundle.mkdir()
    (source_bundle / "SOURCE_BUNDLE_RECEIPT.json").write_text(
        json.dumps({"status": source_status}), encoding="utf-8"
    )
    receipt = figure_atlas.render_implemented_atlas(
        tmp_path / "widget.json", source_bundle, tmp_path / "atlas"
    )
    assert receipt["independent_gates"]["render_qa"] == receipt["status"]
    assert receipt["independent_gates"]["source_reconciliation"] == source_status
    assert receipt["independent_gates"]["publication_approval"] == "NOT_ASSESSED"
    assert receipt["independent_gates"]["biological_validation"] == "NOT_ASSESSED"
    stored = json.loads((tmp_path / "atlas" / "CUMULATIVE_175_QA_RECEIPT.json").read_text())
    assert stored["independent_gates"] == receipt["independent_gates"]


@pytest.mark.parametrize("existing_output", [False, True])
@pytest.mark.parametrize("source_status", ["FAIL", "UNKNOWN", "pass", ""])
def test_atlas_rejects_failed_source_reconciliation(
    tmp_path, monkeypatch, source_status, existing_output
):
    renderer_calls = []

    def fake_renderer(*args, **kwargs):
        renderer_calls.append((args, kwargs))
        raise AssertionError("renderer must not run for an inadmissible source receipt")

    for name in ("render_tranche", "render_tranche_2", "render_tranche_3", "render_tranche_4", "render_tranche_5"):
        monkeypatch.setattr(figure_atlas, name, fake_renderer)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "SOURCE_BUNDLE_RECEIPT.json").write_text(
        json.dumps({"status": source_status}), encoding="utf-8"
    )
    destination = tmp_path / "atlas"
    if existing_output:
        destination.mkdir()
        (destination / "sentinel.txt").write_bytes(b"existing output must survive")
    before = {p.name: p.read_bytes() for p in destination.iterdir()} if existing_output else {}
    with pytest.raises(FigurePolicyError, match="FIGURE_ATLAS_SOURCE_INADMISSIBLE") as error:
        figure_atlas.render_implemented_atlas(tmp_path / "widget.json", bundle, destination)
    assert error.value.code == "FIGURE_ATLAS_SOURCE_INADMISSIBLE"
    assert renderer_calls == []
    assert destination.exists() is existing_output
    if existing_output:
        assert {p.name: p.read_bytes() for p in destination.iterdir()} == before


@pytest.mark.parametrize("payload", [None, "not JSON", "{}", "[]", "null"])
def test_atlas_rejects_missing_or_unreadable_source_before_write(tmp_path, monkeypatch, payload):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    if payload is not None:
        (bundle / "SOURCE_BUNDLE_RECEIPT.json").write_text(payload, encoding="utf-8")
    def unexpected_renderer(*_args, **_kwargs):
        raise AssertionError("renderer called")

    monkeypatch.setattr(figure_atlas, "render_tranche", unexpected_renderer)
    destination = tmp_path / "atlas"
    with pytest.raises(FigurePolicyError, match="FIGURE_ATLAS_SOURCE_INADMISSIBLE"):
        figure_atlas.render_implemented_atlas(tmp_path / "widget.json", bundle, destination)
    assert not destination.exists()

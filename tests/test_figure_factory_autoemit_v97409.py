"""v9.7.409: the Figure Factory auto-emits as an expected post-seal deliverable.

Mirrors how ``build_cohort_figures`` is auto-invoked from the run/cohort flow. The
auto-emit call site is ``mamey.cli._auto_emit_figure_factory``. These tests exercise
the helper directly (the wiring into ``run_one_strain`` / ``run_batch`` is a plain
call to it): it must FIRE when a Figure Factory Next config sits in a sealed package
dir, and it must degrade to a TYPED SKIP (never a crash) when the config or its
declared inputs are absent or unusable.
"""
from __future__ import annotations

from pathlib import Path

from mamey.cli import _auto_emit_figure_factory

# Reuse the vetted figure-factory fixture (valid metrics + cohort manifest + config).
from tests.test_figure_factory_next import _fixture


def _plant_config(pkg: Path, cfg_path: Path) -> None:
    """Drop the fixture config into the package dir under the discovered name."""
    (pkg / "figure_factory_next_config.json").write_text(
        cfg_path.read_text(encoding="utf-8"), encoding="utf-8")


def test_autoemit_fires_on_sealed_package(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MAMEY_FIGURE_FACTORY_CONFIG", raising=False)
    cfg = _fixture(tmp_path, output_dir="ignored-by-autoemit")
    pkg = tmp_path / "package"
    pkg.mkdir()
    _plant_config(pkg, cfg)

    lines: list[str] = []
    receipt = _auto_emit_figure_factory(pkg, logger=lines.append, source_dir=pkg)

    # Figures landed in the conventional <package>/figure_factory subdir.
    out = pkg / "figure_factory"
    assert out.is_dir()
    for profile in ("single_column", "double_column"):
        assert (out / f"figure_factory_next_{profile}.svg").is_file()
        assert (out / f"figure_factory_next_{profile}.png").is_file()

    # Typed receipt with an image count (2 profiles x svg+png).
    assert receipt.get("figure_count", 0) >= 4
    assert receipt.get("status") == "PASS_PORTABLE_POLICY_RENDERER_CANDIDATE"

    # One-line cohort-figures-style announcement was emitted.
    assert any("[figure-factory]" in ln and "figures" in ln for ln in lines)


def test_autoemit_deterministic_on_reemit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MAMEY_FIGURE_FACTORY_CONFIG", raising=False)
    cfg = _fixture(tmp_path, output_dir="ignored")
    pkg = tmp_path / "package"
    pkg.mkdir()
    _plant_config(pkg, cfg)

    first = _auto_emit_figure_factory(pkg, source_dir=pkg)
    # Re-emit over an existing figure_factory dir must succeed (not FileExists-skip)
    # and reproduce byte-identical outputs.
    second = _auto_emit_figure_factory(pkg, source_dir=pkg)
    first_hashes = {o["logical_locator"]: o["sha256"] for o in first["outputs"]}
    second_hashes = {o["logical_locator"]: o["sha256"] for o in second["outputs"]}
    assert first_hashes == second_hashes


def test_autoemit_skips_cleanly_when_config_absent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MAMEY_FIGURE_FACTORY_CONFIG", raising=False)
    pkg = tmp_path / "package"
    pkg.mkdir()

    lines: list[str] = []
    res = _auto_emit_figure_factory(pkg, logger=lines.append, source_dir=pkg)

    assert res == {"status": "SKIPPED_NO_CONFIG", "figure_count": 0}
    assert not (pkg / "figure_factory").exists()
    # A no-op run is silent (feature simply not in use).
    assert lines == []


def test_autoemit_typed_skip_on_unusable_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MAMEY_FIGURE_FACTORY_CONFIG", raising=False)
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "figure_factory_next_config.json").write_text("{ not valid json",
                                                         encoding="utf-8")

    lines: list[str] = []
    res = _auto_emit_figure_factory(pkg, logger=lines.append, source_dir=pkg)

    # Typed skip, no crash, no figure dir left behind.
    assert res.get("figure_count", 0) == 0
    assert str(res.get("status", "")).startswith("SKIPPED_")
    assert not (pkg / "figure_factory").exists()
    # A found-but-unusable config is announced.
    assert any("[figure-factory] SKIPPED" in ln for ln in lines)

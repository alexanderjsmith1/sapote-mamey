"""CLAUDE_410 savefig_oom_sweep — every raster write clamps DPI under the Agg pixel ceiling.

`.409` ships `mamey/render_safe.py::safe_savefig_dpi`, which clamps a requested DPI so
`max(width_in, height_in) * dpi` stays under `max_figure_edge_px()` (matplotlib-Agg refuses above
65,536 px, and a near-ceiling raster allocates multiple GB). `.409` wired it into exactly ONE
module — `mamey/cohort_class_heatmap.py`. Every other figure writer still passed a hard-coded
publication DPI straight to `savefig`, so a wide cohort, a long contig, or a deep domain table
crashed the run with a bare matplotlib `ValueError` or OOM-killed the process.

This lane wires the shipped helper into the remaining 27 sites across 15 modules.

Effect at a site: the common case renders at a slightly lower DPI instead of dying. The extreme
case raises the coded `FigureCanvasTooLargeError` — still a stop, but a named, actionable one that
says "panel/split this figure" rather than an OOM kill. Per-figure SKIP handling (what
`cohort_class_heatmap` does with its `.SKIPPED.md`) is deliberately NOT in this lane: it is a
per-caller decision about what a missing figure means for that deliverable.
"""
from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# `.409` already guards this module correctly: both of its savefig calls take a DPI that
# safe_savefig_dpi has already clamped (`_pub_dpi`, and `screen_dpi` derived below it), with a
# FigureCanvasTooLargeError handler that writes a `.SKIPPED.md` rather than crashing the run.
#
# Allowlisted by FILE, deliberately not by line number: a co-applied lane that edits this module
# shifts those lines (CLAUDE_410_csv_writer_coverage moves them 208/221 -> 212/225), and a
# line-keyed skip set silently stops matching and reports a false offender.
ALREADY_GUARDED_FILES = {"mamey/cohort_class_heatmap.py"}

# tools/ is out of scope for this lane: those are standalone operator scripts, not the wired
# deliverable path, and several build their figure outside any mamey import context.
SWEPT_TREES = ("mamey", "deliverable_tools")


def _unguarded_dpi_sites() -> dict[str, list[int]]:
    """Every `X.savefig(..., dpi=EXPR)` whose EXPR is not routed through the clamp."""
    offenders: dict[str, list[int]] = {}
    for sub in SWEPT_TREES:
        for py in sorted((ROOT / sub).rglob("*.py")):
            rel = py.relative_to(ROOT).as_posix()
            src = py.read_text(encoding="utf-8", errors="replace")
            if ".savefig(" not in src or "dpi=" not in src:
                continue
            try:
                tree = ast.parse(src)
            except SyntaxError:  # pragma: no cover
                continue
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "savefig"):
                    continue
                for kw in node.keywords:
                    if kw.arg != "dpi":
                        continue
                    val = ast.get_source_segment(src, kw.value) or ""
                    if "safe_savefig_dpi" in val or "_safe_dpi" in val:
                        continue
                    if rel in ALREADY_GUARDED_FILES:
                        continue
                    offenders.setdefault(rel, []).append(kw.value.lineno)
    return offenders


def test_no_unguarded_savefig_dpi_remains() -> None:
    """Coverage lock. Fails on pristine .409 with 27 sites in 15 files."""
    offenders = _unguarded_dpi_sites()
    assert not offenders, f"unclamped savefig dpi: {offenders}"


def test_plt_savefig_sites_measure_the_current_figure() -> None:
    """`plt.savefig` writes whatever figure is current — measuring a stale local `fig` would clamp
    against the wrong canvas. Every swept `plt.savefig` must pass `plt.gcf()`."""
    bad: list[str] = []
    for sub in SWEPT_TREES:
        for py in sorted((ROOT / sub).rglob("*.py")):
            src = py.read_text(encoding="utf-8", errors="replace")
            if "plt.savefig(" not in src:
                continue
            try:
                tree = ast.parse(src)
            except SyntaxError:  # pragma: no cover
                continue
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "savefig"
                        and ast.get_source_segment(src, node.func.value) == "plt"):
                    continue
                for kw in node.keywords:
                    if kw.arg != "dpi":
                        continue
                    val = ast.get_source_segment(src, kw.value) or ""
                    if "_safe_dpi(" in val and "plt.gcf()" not in val:
                        bad.append(f"{py.relative_to(ROOT).as_posix()}:{kw.value.lineno} {val}")
    assert not bad, bad


def test_every_swept_module_binds_the_clamp_at_import_time() -> None:
    """An added call with a missing import is a NameError that only fires when a figure is written —
    i.e. deep in a long run. Import each swept module and check the name is bound."""
    swept = sorted(_modules_using_the_clamp())
    # 14 importable mamey modules. deliverable_tools/render_mlsa_tree.py is the 15th swept file but
    # is a __main__ script, not an importable package module, so it is checked by source above.
    assert len(swept) == 14, f"expected the full sweep, found {len(swept)}: {swept}"
    for dotted in swept:
        mod = importlib.import_module(dotted)
        assert hasattr(mod, "_safe_dpi"), f"{dotted} calls _safe_dpi but does not bind it"


def _modules_using_the_clamp() -> set[str]:
    found = set()
    for py in sorted((ROOT / "mamey").rglob("*.py")):
        if "_safe_dpi(" in py.read_text(encoding="utf-8", errors="replace"):
            rel = py.relative_to(ROOT).with_suffix("")
            found.add(".".join(rel.parts))
    return found


@pytest.mark.slow
def test_clamp_lowers_dpi_for_an_oversize_canvas(tmp_path: Path) -> None:
    """Behavioural proof, not just a source scan: a canvas that would exceed the ceiling at the
    requested DPI is written at a lower one, and the file is a real PNG."""
    matplotlib = importlib.import_module("matplotlib")
    matplotlib.use("Agg")
    plt = importlib.import_module("matplotlib.pyplot")

    from mamey.render_safe import max_figure_edge_px, safe_savefig_dpi

    # The ceiling is 30,000 px (MAMEY_MAX_FIGURE_EDGE_PX) and the floor 100 dpi, so a 150-inch
    # canvas fits at 200 dpi but not at the requested 300 (150 x 300 = 45,000 px).
    fig = plt.figure(figsize=(150, 4))
    try:
        requested = 300
        clamped = safe_savefig_dpi(fig, requested)
        assert clamped < requested
        assert 150 * clamped <= max_figure_edge_px()
        out = tmp_path / "wide.png"
        fig.savefig(out, dpi=clamped)
        assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    finally:
        plt.close(fig)


@pytest.mark.slow
def test_clamp_is_a_no_op_for_an_ordinary_canvas() -> None:
    """The clamp must not silently downgrade normal publication figures — otherwise this lane would
    quietly change the resolution of every figure Alex has already produced."""
    matplotlib = importlib.import_module("matplotlib")
    matplotlib.use("Agg")
    plt = importlib.import_module("matplotlib.pyplot")

    from mamey.render_safe import safe_savefig_dpi

    fig = plt.figure(figsize=(7.5, 5.0))
    try:
        for dpi in (120, 150, 160, 170, 180, 200, 220, 300):
            assert safe_savefig_dpi(fig, dpi) == dpi
    finally:
        plt.close(fig)


@pytest.mark.slow
def test_refusal_is_coded_when_even_the_floor_will_not_fit() -> None:
    """The extreme case is a named refusal that tells the operator what to do, not an OOM kill."""
    matplotlib = importlib.import_module("matplotlib")
    matplotlib.use("Agg")
    plt = importlib.import_module("matplotlib.pyplot")

    from mamey.render_safe import FigureCanvasTooLargeError, safe_savefig_dpi

    fig = plt.figure(figsize=(100000, 4))
    try:
        with pytest.raises(FigureCanvasTooLargeError) as exc:
            safe_savefig_dpi(fig, 300)
        assert FigureCanvasTooLargeError.code in str(exc.value)
    finally:
        plt.close(fig)

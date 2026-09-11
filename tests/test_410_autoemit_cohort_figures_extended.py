"""v9.7.410: the extended cross-strain figure suite auto-emits from a multi-strain run.

``mamey/cohort_figures_extended.py`` describes itself as the auto-emit companion to
``cohort_figures.generate``, but through v9.7.409 the only call site was the manual
``cohort-figures`` subcommand: the ``run_batch`` multi-strain block (``if len(results) > 1:``)
called ``build_cohort_figures`` and the gold F-series and never the extended suite. The
bridge is ``mamey.cli._auto_emit_cohort_figures_extended``. These tests exercise the helper
directly with two package fixtures shaped like a 2-strain batch result (the wiring into
``run_batch`` is a plain call to it, checked by AST below): it must FIRE on two strains with
inventories, degrade to a TYPED SKIP (never a crash) otherwise, and re-emit deterministically.

Fail-before on v9.7.409: the helper does not exist (ImportError) and ``run_batch`` does not
reference the extended suite.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from mamey import cli
from mamey.cli import _auto_emit_cohort_figures_extended

# Reuse the vetted extended-suite package fixture (inventory + gene-by-gene CSVs).
from tests.test_cohort_figures_extended_v9_7_279 import _mini_package

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow


def _two_strain_batch(root: Path) -> list[dict]:
    """Two sealed-shaped packages plus the ``run_batch`` result dicts that point at them."""
    results = []
    for sid in ("AS-001", "AS-002"):
        _mini_package(root, sid)
        results.append({"strain_id": sid, "status": "OK", "raw_bgcs": 2, "assembly_tier": "T1"})
    return results


def test_autoemit_fires_on_two_strain_batch(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    results = _two_strain_batch(root)

    lines: list[str] = []
    receipt = _auto_emit_cohort_figures_extended(results, root, logger=lines.append)

    out = root / "cohort_figures_extended"
    assert out.is_dir()
    assert receipt["status"] == "PASS"
    assert receipt["figure_count"] >= 8, receipt
    assert receipt["strains"] == ["AS-001", "AS-002"]
    assert (out / "fig9_domain_cooccur.png").is_file()
    assert any(ln.startswith("[cohort-figures-extended] ") and "figures ->" in ln for ln in lines)


def test_autoemit_typed_skip_when_fewer_than_two_inventories(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _mini_package(root, "AS-001")
    # Second strain ran but has no package inventory (e.g. failed/quarantined run).
    results = [{"strain_id": "AS-001"}, {"strain_id": "AS-999"}]

    lines: list[str] = []
    receipt = _auto_emit_cohort_figures_extended(results, root, logger=lines.append)

    assert receipt == {"status": "SKIPPED_INSUFFICIENT_INVENTORIES", "figure_count": 0}
    assert not (root / "cohort_figures_extended").exists()
    assert any("[cohort-figures-extended] SKIPPED" in ln for ln in lines)


def test_autoemit_never_raises_on_garbage_input(tmp_path: Path) -> None:
    receipt = _auto_emit_cohort_figures_extended([None, {}, {"strain_id": 7}], tmp_path / "nope",
                                                 logger=lambda *a, **k: None)
    assert receipt["figure_count"] == 0
    assert receipt["status"].startswith("SKIPPED_")


def test_autoemit_deterministic_on_reemit(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    results = _two_strain_batch(root)
    quiet = lambda *a, **k: None  # noqa: E731
    first = _auto_emit_cohort_figures_extended(results, root, logger=quiet)
    listing_1 = sorted(p.name for p in (root / "cohort_figures_extended").iterdir())
    second = _auto_emit_cohort_figures_extended(results, root, logger=quiet)
    listing_2 = sorted(p.name for p in (root / "cohort_figures_extended").iterdir())
    assert first["figure_count"] == second["figure_count"]
    assert listing_1 == listing_2


def test_run_batch_multistrain_block_calls_extended_bridge() -> None:
    """The bridge is wired inside ``if len(results) > 1:`` in ``run_batch`` — the same guard
    as ``build_cohort_figures`` — and nowhere in the single-strain path."""
    tree = ast.parse(inspect.getsource(cli.run_batch))
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        guarded = (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Call)
            and getattr(test.left.func, "id", None) == "len"
            and getattr(test.left.args[0], "id", None) == "results"
            and isinstance(test.ops[0], ast.Gt)
            and getattr(test.comparators[0], "value", None) == 1
        )
        if not guarded:
            continue
        names = {getattr(n.func, "id", None) or getattr(n.func, "attr", None)
                 for n in ast.walk(node) if isinstance(n, ast.Call)}
        if "_auto_emit_cohort_figures_extended" in names:
            assert "build_cohort_figures" in names, "should share the cohort-figures guard"
            hits.append(node)
    assert hits, "run_batch's multi-strain block must call _auto_emit_cohort_figures_extended"
    assert "_auto_emit_cohort_figures_extended" not in inspect.getsource(cli.run_one_strain)


def test_manual_subcommand_still_reaches_extended_suite() -> None:
    """Thin integration: the pre-existing manual path is untouched."""
    src = inspect.getsource(cli.cohort_figures_command)
    assert "generate_extended" in src

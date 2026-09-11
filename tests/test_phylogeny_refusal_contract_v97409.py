"""Phylogeny Figure Factory structural-refusal contract (CLAUDE_409, v9.7.409).

Two bugs in the phylogeny arm of the Figure Factory, both surfaced on first
real-data contact (FIGURE_FACTORY_REALRUN.md, RB68 / rifamycini cohort):

  Bug 1 - a *structural* refusal (e.g. an incomplete evidence receipt) is raised
          by ``phylogeny_figure_factory.tree()`` as a plain ``ValueError``. The CLI
          (``tools/figure_factory_next.py``) only catches ``PhylogenyFigureHold``,
          so the process died with a RAW traceback at **exit 1** instead of the
          clean ``figure_factory_next: REFUSED ...`` path at **exit 2** that the
          typed refusals already use.

  Bug 2 - ``build()`` called ``out.mkdir()`` *before* validating inputs and never
          cleaned up on refusal, leaving a stray empty ``output_dir`` that made a
          naive re-run hit ``FileExistsError``. The aggregate arm stages into a
          temp dir and ``shutil.rmtree``s on any exception; the phylogeny arm now
          mirrors that.

These tests pin BOTH halves of the fixed contract for the exact real-run trigger
(an incomplete ``tree_evidence`` receipt):

  * exit code 2 with a typed ``REFUSED`` message on stderr (not a traceback), and
  * no stray ``output_dir`` and no leftover staging dir after the refusal.

FAIL-BEFORE (why this is a regression guard): run against the pristine v9.7.408
bundle these assertions fail exactly as the bug describes - the CLI returns 1 with
a ``Traceback (most recent call last)`` on stderr, and the ``output_dir`` is left
behind on disk. They pass only once CLAUDE_409_figure_factory_refusal.patch is
applied. (The Python-level test additionally proves the promoted exception is the
typed ``PhylogenyFigureHold`` subtype, not a bare ``ValueError``.)

Run from the (patched) bundle root, e.g.:
    env/.venv312/bin/python -m pytest <this file> -q
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import mamey.phylogeny_figure_factory as pff

BUNDLE_ROOT = Path(pff.__file__).resolve().parents[1]
CLI = BUNDLE_ROOT / "tools" / "figure_factory_next.py"

SCHEMA = "sapote.phylogeny-figure-factory.v1"
EVIDENCE_WIDGET_KIND = "phylogeny_evidence_receipt_widget_v1"


def _refusing_config(tmp_path: Path) -> tuple[Path, Path]:
    """A well-formed config whose ``tree_evidence`` is an incomplete receipt.

    This is the real-run trigger: ``tree()`` refuses with
    "tree_evidence: complete evidence receipt required". Everything else (schema,
    external_data_root, output_dir parent) is valid, so the refusal happens *after*
    the arm has begun input validation - precisely where the stray dir used to
    appear.
    """
    ext = tmp_path / "ext"
    ext.mkdir()
    out = tmp_path / "phylogeny_run"  # must NOT exist yet
    config = {
        "schema_version": SCHEMA,
        "figure_kind": EVIDENCE_WIDGET_KIND,
        "external_data_root": str(ext),
        "output_dir": str(out),
        "figure_id": "FFPHYLO_REFUSE",
        "tree_evidence": {},  # incomplete receipt -> structural refusal
    }
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps(config), encoding="utf-8")
    return cfg, out


def _stray_staging_dirs(parent: Path) -> list[Path]:
    return [p for p in parent.iterdir() if p.name.startswith(".phylogeny_figure_factory.")]


def test_structural_refusal_exits_2_with_typed_refused_and_no_stray_dir(tmp_path):
    """CLI contract: exit 2, typed REFUSED on stderr, no traceback, no stray dir."""
    cfg, out = _refusing_config(tmp_path)
    run = subprocess.run(
        [sys.executable, str(CLI), "--config", str(cfg)],
        capture_output=True, text=True,
    )
    # Bug 1: clean typed refusal at exit 2, not a raw traceback at exit 1.
    assert run.returncode == 2, (run.returncode, run.stderr)
    assert "figure_factory_next: REFUSED" in run.stderr, run.stderr
    assert "PHYLO_STRUCTURAL_REFUSED" in run.stderr, run.stderr
    assert "complete evidence receipt required" in run.stderr, run.stderr
    assert "Traceback (most recent call last)" not in run.stderr, run.stderr
    # Bug 2: the refused run leaves no output_dir and no leftover staging dir.
    assert not out.exists(), "refused run left a stray output_dir behind"
    assert _stray_staging_dirs(tmp_path) == [], "refused run left a staging dir behind"


def test_build_promotes_structural_refusal_to_typed_hold_and_cleans_up(tmp_path):
    """Python-level: build() raises the typed PhylogenyFigureHold and leaves no dir."""
    cfg, out = _refusing_config(tmp_path)
    with pytest.raises(pff.PhylogenyFigureHold) as excinfo:
        pff.build(cfg)
    assert excinfo.value.code == "PHYLO_STRUCTURAL_REFUSED"
    assert "complete evidence receipt required" in excinfo.value.detail
    # PhylogenyFigureHold is a ValueError subclass; the point is the *typed* subtype.
    assert isinstance(excinfo.value, ValueError)
    assert not out.exists()
    assert _stray_staging_dirs(tmp_path) == []


def test_preexisting_output_dir_still_reports_file_exists(tmp_path):
    """Guard: the atomic-replace refactor keeps the pre-existing-output_dir contract.

    A pre-existing output_dir is a caller/collision error, not a structural refusal,
    so it must stay a FileExistsError (raised before any staging dir is created)."""
    cfg, out = _refusing_config(tmp_path)
    out.mkdir()  # collide
    with pytest.raises(FileExistsError):
        pff.build(cfg)
    assert _stray_staging_dirs(tmp_path) == []

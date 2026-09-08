"""PER_BGC_REPORT_CARD_SPEC §6.1 — mamey report-card L0-L1 renderer.
CLI-level + function-level (the Patch-B lesson: exercise the command path, not only the function)."""
import os
import pytest
from types import SimpleNamespace

from mamey.report_card import render_report_cards, report_card_command

_PKG = "/data/mamey-local/work/strain_intake/runs_v184/AS-421/package"
_HAVE = os.path.isdir(_PKG)


@pytest.mark.skipif(not _HAVE, reason="AS-421 package not present")
def test_render_report_cards_function():
    r = render_report_cards(_PKG)
    assert r["cards"] > 0
    md = r["markdown"]
    # claim discipline is in the wording
    assert "similarity, not identity" in md
    assert "Novelty" in md
    # never a 'produces' claim
    assert "produces " not in md


@pytest.mark.skipif(not _HAVE, reason="AS-421 package not present")
def test_report_card_command_cli_path(tmp_path):
    """Exercise report_card_command (the CLI entry), not just render_report_cards."""
    out = tmp_path / "cards.md"
    args = SimpleNamespace(package=_PKG, bgc=None, out=str(out))
    rc = report_card_command(args)
    assert rc == 0
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.skipif(not _HAVE, reason="AS-421 package not present")
def test_report_card_single_bgc(tmp_path):
    args = SimpleNamespace(package=_PKG, bgc="BGC041", out=str(tmp_path / "one.md"))
    assert report_card_command(args) == 0


# ── F09 (v9.7.353): engine label derives from manifest / live version, never a stale literal ──
import json as _json
from mamey import __version__ as _ENGINE_VERSION


def _min_pkg(tmp_path, manifest=None):
    """Hermetic minimal package (no external /data path): header-only triage board so the strain
    name resolves and render_report_cards() runs to produce its header line with the version."""
    pkg = tmp_path / "pkg"; pkg.mkdir()
    (pkg / "AS-TEST_4_triage_board.csv").write_text(
        "Rank,BGC_ID,Contig,antiSMASH_Region,Products\n", encoding="utf-8")
    if manifest is not None:
        (pkg / "manifest.json").write_text(_json.dumps(manifest), encoding="utf-8")
    return pkg


def test_report_card_version_from_manifest(tmp_path):
    """The engine label is read from manifest.json workflow_version. Under the F09 defect (no
    module-scope json import) _loadj raised NameError, the except swallowed it, and the label
    stayed the stale hard-coded 'v1.9.110' — this test would have caught that."""
    pkg = _min_pkg(tmp_path, manifest={"strain_id": "AS-TEST",
                                       "workflow_version": "Mamey v1.9.119"})
    md = render_report_cards(str(pkg))["markdown"]
    assert "Mamey v1.9.119" in md
    assert "1.9.110" not in md  # the stale hard-coded default must never appear


def test_report_card_version_falls_back_to_live_engine(tmp_path):
    """No manifest -> label derives from the LIVE engine __version__, not a frozen literal."""
    pkg = _min_pkg(tmp_path, manifest=None)
    md = render_report_cards(str(pkg))["markdown"]
    assert _ENGINE_VERSION in md
    assert "1.9.110" not in md

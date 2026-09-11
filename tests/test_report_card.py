"""PER_BGC_REPORT_CARD_SPEC §6.1 — mamey report-card L0-L1 renderer.
CLI-level + function-level (the Patch-B lesson: exercise the command path, not only the function)."""
import os
import builtins
import pytest
from types import SimpleNamespace

from mamey.report_card import build_card, render_report_cards, report_card_command

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


def test_report_card_marks_unreadable_manifest_version(tmp_path):
    pkg = _min_pkg(tmp_path, manifest=None)
    (pkg / "manifest.json").write_text("{broken", encoding="utf-8")
    md = render_report_cards(str(pkg))["markdown"]
    assert "manifest unreadable: JSONDecodeError" in md


@pytest.mark.parametrize("manifest", [None, [], "text"])
def test_report_card_marks_non_object_manifest_invalid(tmp_path, manifest):
    pkg = _min_pkg(tmp_path, manifest=manifest)
    if manifest is None:
        (pkg / "manifest.json").write_text("null", encoding="utf-8")
    md = render_report_cards(str(pkg))["markdown"]
    assert "manifest invalid: root must be an object" in md


@pytest.mark.parametrize("workflow_version", [7, [], {}])
def test_report_card_marks_invalid_workflow_version_type(tmp_path, workflow_version):
    pkg = _min_pkg(tmp_path, manifest={"workflow_version": workflow_version})
    md = render_report_cards(str(pkg))["markdown"]
    assert "manifest invalid: workflow_version must be a string" in md


def test_report_card_does_not_convert_malformed_scores_to_zero_badges():
    row = {
        "BGC_ID": "BGC001", "Contig": "NODE_1", "antiSMASH_Region": "region001",
        "Products": "NRPS", "KCB_top": "MIBiG | comparator", "KCB_score": "bad-score",
        "Novelty_auto": "bad-novelty", "AB_auto": "bad-ab", "AF_auto": "0",
    }
    card = build_card(row, None, [], "TEST-STRAIN", "Mamey test", 1)
    assert "KCB `comparator` (score unresolved)" in card
    assert "Novelty **UNRESOLVED" in card
    assert "Predicted activity **UNRESOLVED" in card
    assert "hold routing interpretation" in card


def test_report_card_preserves_measured_zero_scores():
    row = {
        "BGC_ID": "BGC001", "Contig": "NODE_1", "antiSMASH_Region": "region001",
        "Products": "NRPS", "KCB_top": "NONE", "KCB_score": "0",
        "Novelty_auto": "0", "AB_auto": "0", "AF_auto": "0",
    }
    card = build_card(row, None, [], "TEST-STRAIN", "Mamey test", 1)
    assert "KCB: none (KCB-dark)" in card
    assert "Predicted activity **low-confidence (AB 0/AF 0)" in card
    assert "UNRESOLVED" not in card


def test_report_card_surfaces_rescue_provider_import_failure(tmp_path, monkeypatch):
    pkg = _min_pkg(tmp_path, manifest={"workflow_version": "Mamey test"})
    real_import = builtins.__import__
    def fail_rescue_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 1 and "card_verdicts" in fromlist:
            raise ImportError("provider broken")
        return real_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", fail_rescue_import)
    md = render_report_cards(str(pkg))["markdown"]
    assert "RESCUE_PROVIDER_UNAVAILABLE: ImportError" in md
    assert "evidence is unresolved, not absent" in md


def test_report_card_missing_rescue_table_is_not_provider_failure(tmp_path):
    pkg = _min_pkg(tmp_path, manifest={"workflow_version": "Mamey test"})
    md = render_report_cards(str(pkg))["markdown"]
    assert "RESCUE_PROVIDER_UNAVAILABLE" not in md

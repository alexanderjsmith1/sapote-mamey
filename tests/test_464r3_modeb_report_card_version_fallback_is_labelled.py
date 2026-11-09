"""A report card that falls back to the running engine version says so.

With no manifest, or a manifest without workflow_version, the card printed a
bare `Mamey v<running engine>`, which reads as the engine that built the package.
"""
from mamey import __version__ as ENGINE
from mamey.report_card import render_report_cards
from tests.test_report_card import _min_pkg


def test_missing_manifest_names_running_engine(tmp_path):
    md = render_report_cards(str(_min_pkg(tmp_path, manifest=None)))["markdown"]
    assert f"Mamey v{ENGINE} (running engine; package manifest.json absent)" in md


def test_manifest_without_workflow_version_names_running_engine(tmp_path):
    md = render_report_cards(str(_min_pkg(tmp_path, manifest={"strain_id": "PUBLIC-1"})))["markdown"]
    assert f"Mamey v{ENGINE} (running engine; manifest has no workflow_version)" in md


def test_manifest_version_is_used_unchanged(tmp_path):
    md = render_report_cards(str(_min_pkg(tmp_path, manifest={"workflow_version": "Mamey v1.9.119"})))["markdown"]
    assert "Mamey v1.9.119" in md and "running engine" not in md

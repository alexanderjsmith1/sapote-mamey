"""Public-source inventory identity must survive the evidence-summary display."""
import csv
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("eb461id", Path(__file__).resolve().parents[1] / "tools/evidence_bundle.py")
eb = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(eb)


def test_public_inventory_identity_survives_markdown(tmp_path):
    pkg = tmp_path / "package"; pkg.mkdir()
    with (pkg / "Micromonospora_humida_JAFEUC01_2_inventory.csv").open("w", newline="") as h:
        w = csv.writer(h)
        w.writerow(["BGC_ID", "Contig", "Node_ID", "antiSMASH_Region", "Region", "Strain"])
        w.writerow(["BGC001", "JAFEUC010000001.1", "JAFEUC010000001.1", "region002", "2", "Micromonospora_humida_JAFEUC01"])
    bundle = eb.build_evidence_bundle(pkg)
    eb.write_evidence_bundle(bundle, tmp_path / "out")
    md = next((tmp_path / "out").glob("*.md")).read_text()
    assert "## Evidence Summary — Micromonospora_humida_JAFEUC01 / JAFEUC010000001.1 / region002 / BGC001" in md


def test_incomplete_identity_is_held_instead_of_alias_display(tmp_path):
    pkg = tmp_path / "package"; pkg.mkdir()
    (pkg / "PUBLIC_2_inventory.csv").write_text("bgc_id,contig\nBGC001,JAFEUC010000001.1\n")
    bundle = eb.build_evidence_bundle(pkg)
    eb.write_evidence_bundle(bundle, tmp_path / "out")
    md = next((tmp_path / "out").glob("*.md")).read_text()
    assert "IDENTITY_HOLD" in md
    assert "## Evidence Summary — BGC001" not in md


def test_filename_prefix_cannot_supply_missing_source_strain(tmp_path):
    pkg = tmp_path / "package"; pkg.mkdir()
    with (pkg / "Micromonospora_humida_JAFEUC01_2_inventory.csv").open("w", newline="") as h:
        w = csv.writer(h)
        w.writerow(["BGC_ID", "Contig", "Node_ID", "antiSMASH_Region", "Region"])
        w.writerow(["BGC001", "JAFEUC010000001.1", "JAFEUC010000001.1", "region002", "2"])
    bundle = eb.build_evidence_bundle(pkg)
    eb.write_evidence_bundle(bundle, tmp_path / "out")
    md = next((tmp_path / "out").glob("*.md")).read_text()
    assert "IDENTITY_HOLD" in md
    assert "Evidence Summary — Micromonospora_humida_JAFEUC01 /" not in md

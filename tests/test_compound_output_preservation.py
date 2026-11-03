"""Output-inode admission only; synthetic empty report rows and no structures."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mamey.compound_candidate", ROOT / "mamey/compound_family_report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
OUTPUTS = ["ANCHORED_BGC_COMPOUND_FAMILIES.tsv", "COMPOUND_FAMILY_ROLLUP.tsv", "ANCHOR_STRUCTURES.tsv", "EXCLUDED.txt"]


def setup(tmp_path, monkeypatch, sealed, excluded=False):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "SOFTWARE_FIXTURE"}))
    (pkg / "SOFTWARE_FIXTURE_4_triage_board.csv").write_text("BGC_ID,KCB_top,Products\n")
    source = pkg / "retained_unique_evidence.txt"
    source.write_bytes(b"unique source bytes must survive")
    if sealed:
        (pkg / "checksums_sha256.txt").write_text("software seal-marker fixture only")
    monkeypatch.setattr(report, "EXCLUDE_STRAINS", {"SOFTWARE_FIXTURE"} if excluded else set())
    monkeypatch.setattr(report, "load_rules", lambda: [])
    def forbidden(*args):
        pytest.fail("structure resolver must not run for empty synthetic rows")
    monkeypatch.setitem(sys.modules, "mamey.npatlas_structure", SimpleNamespace(resolve_name_to_structure=forbidden))
    root = tmp_path / "output"
    directory = root / "COMPOUND_FAMILIES"
    directory.mkdir(parents=True)
    return pkg, source, root, directory


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("sealed", [False, True])
@pytest.mark.parametrize("name", OUTPUTS)
def test_multilink_output_refuses_before_any_write(tmp_path, monkeypatch, sealed, name):
    pkg, source, root, directory = setup(tmp_path, monkeypatch, sealed, name == "EXCLUDED.txt")
    os.link(source, directory / name)
    before = snapshot(tmp_path)
    refused = False
    try:
        report.run(pkg, root, with_structures=name == "ANCHOR_STRUCTURES.tsv")
    except ValueError as error:
        refused = True
        assert "COMPOUND_OUTPUT_LINK_HOLD" in str(error)
    after = snapshot(tmp_path)
    assert refused and before == after, {"refused": refused, "changed_paths": [p for p in before if before.get(p) != after.get(p)], "new_paths": sorted(after.keys() - before.keys())}


@pytest.mark.parametrize("sealed", [False, True])
def test_symlink_output_refuses_and_preserves_inputs(tmp_path, monkeypatch, sealed):
    pkg, source, root, directory = setup(tmp_path, monkeypatch, sealed)
    (directory / OUTPUTS[0]).symlink_to(source)
    before = snapshot(tmp_path)
    refused = False
    try:
        report.run(pkg, root, with_structures=False)
    except ValueError:
        refused = True
    assert refused and snapshot(tmp_path) == before


@pytest.mark.parametrize("sealed", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_regular_output_keeps_inputs_and_overwrite_behavior(tmp_path, monkeypatch, sealed, existing):
    pkg, source, root, directory = setup(tmp_path, monkeypatch, sealed)
    before = snapshot(pkg)
    if existing:
        (directory / OUTPUTS[0]).write_text("old generated output")
    result = report.run(pkg, root, with_structures=False)
    assert result["status"] == "ok" and result["rows"] == 0
    assert snapshot(pkg) == before
    assert (directory / OUTPUTS[0]).read_text().startswith(report.CLAIM_HEADER)


@pytest.mark.parametrize("name", ["ANCHOR_STRUCTURES.tsv", "EXCLUDED.txt"])
def test_unused_linked_destination_does_not_block_selected_outputs(tmp_path, monkeypatch, name):
    pkg, source, root, directory = setup(tmp_path, monkeypatch, True)
    os.link(source, directory / name)
    source_before = source.read_bytes()
    assert report.run(pkg, root, with_structures=False)["status"] == "ok"
    assert source.read_bytes() == source_before
    assert (directory / name).read_bytes() == source_before

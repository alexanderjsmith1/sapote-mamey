import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


batch_context = load("deliverable_tools/batch_mibig_comparator_context.py", "batch_mibig_comparator_context_test")
widget = load("deliverable_tools/bigscape_network_widget.py", "bigscape_network_widget_batch_test")


def report_fixture():
    return (
        "<html><body><!-- MIBIG_IDENTITY_SUMMARY_START --><table>"
        "<tr><th>Rank</th><th>Complete identity</th><th>Comparator</th><th>Matched CDS</th></tr>"
        "<tr><td>1</td><td>DEMO-A / contig_alpha / region001 / BGC001</td>"
        "<td>BGC0000001 neutral fixture</td><td>2/4</td></tr></table>"
        "<!-- MIBIG_IDENTITY_SUMMARY_END --></body></html>"
    )


def mibig_fixture(tmp_path):
    root = tmp_path / "mibig"
    root.mkdir()
    (root / "BGC0000001.json").write_text(json.dumps({
        "accession": "BGC0000001", "biosynthesis": {"classes": [{"class": "NRPS"}]}
    }))
    return root


def test_batch_comparator_context_creates_additive_portable_report_copies(tmp_path):
    source_root = tmp_path / "authoritative"
    for strain in ("DEMO-A", "DEMO-B"):
        report_path = source_root / strain / "REPORT.html"
        report_path.parent.mkdir(parents=True)
        report_path.write_text(report_fixture())
    source_hashes = {path: widget.sha256(path) for path in source_root.rglob("REPORT.html")}
    output_root = tmp_path / "copies"
    receipt = batch_context.build(source_root, output_root, mibig_fixture(tmp_path), None)
    assert receipt["report_count"] == 2
    assert receipt["authoritative_inputs_mutated"] is False
    assert all(not Path(row["source_locator"]).is_absolute() for row in receipt["records"])
    assert all(not Path(row["output_locator"]).is_absolute() for row in receipt["records"])
    assert all(widget.sha256(path) == digest for path, digest in source_hashes.items())
    assert len(list(output_root.rglob("REPORT.html"))) == 2


def test_batch_comparator_context_refuses_output_inside_authoritative_tree(tmp_path):
    source_root = tmp_path / "authoritative"
    report_path = source_root / "DEMO-A" / "REPORT.html"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(report_fixture())
    with pytest.raises(ValueError, match="MIBIG_BATCH_GATE"):
        batch_context.build(source_root, source_root / "copies", mibig_fixture(tmp_path), None)

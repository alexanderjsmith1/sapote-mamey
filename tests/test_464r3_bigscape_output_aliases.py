"""Component-context extract and widget report/receipt outputs never replace inputs or existing files."""
import csv
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
IDENTITY = "SYNTH-01 / NODE_7_length_47000_cov_20.0 / region001 / BGC004"
OTHER = "SYNTH-02 / NODE_3_length_30000_cov_9.0 / region002 / BGC009"
ACCESSION = "BGC0002010"


def _load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _evidence(path):
    rows = []
    for identity in (IDENTITY, OTHER):
        for order in range(1, 6):
            rows.append({"complete_identity": identity, "gene_order": str(order),
                         "dominant_reference_gene_match": "YES" if order < 4 else "NO",
                         "dominant_mibig_accession": ACCESSION})
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_component_extract_cannot_replace_the_evidence_table(tmp_path):
    tool = _load("deliverable_tools/mibig_component_context.py", "_mcc_alias")
    source = tmp_path / "all.tsv"
    _evidence(source)
    before = source.read_bytes()
    with pytest.raises(ValueError):
        tool.build(source, IDENTITY, ACCESSION, source, tmp_path / "out.tsv", "all.tsv")
    assert source.read_bytes() == before
    assert not (tmp_path / "out.tsv").exists()


def test_component_refuses_existing_output_and_writes_nothing_on_no_match(tmp_path):
    tool = _load("deliverable_tools/mibig_component_context.py", "_mcc_fresh")
    source = tmp_path / "all.tsv"
    _evidence(source)
    out = tmp_path / "out.tsv"
    out.write_text("earlier result\n")
    with pytest.raises(ValueError):
        tool.build(source, IDENTITY, ACCESSION, tmp_path / "x.tsv", out, "x.tsv")
    assert out.read_text() == "earlier result\n"
    assert not (tmp_path / "x.tsv").exists()
    extract = tmp_path / "nomatch_extract.tsv"
    with pytest.raises(ValueError):
        tool.build(source, IDENTITY, "BGC0000001", extract, tmp_path / "o2.tsv", "nomatch_extract.tsv")
    assert not extract.exists()


def test_component_extract_hash_matches_written_file(tmp_path):
    tool = _load("deliverable_tools/mibig_component_context.py", "_mcc_hash")
    source = tmp_path / "all.tsv"
    _evidence(source)
    extract = tmp_path / "sources" / "one.tsv"
    row = tool.build(source, IDENTITY, ACCESSION, extract, tmp_path / "out.tsv", "sources/one.tsv")
    assert row["evidence_sha256"] == tool.sha256(extract)
    assert OTHER not in extract.read_text()


def _cohort(tmp_path):
    from test_bigscape_cohort_report_and_network_widget_v97435 import fixture, report
    database, host, crosswalk = fixture(tmp_path, complete=True)
    cohort = tmp_path / "cohort"
    report.build(database, 7, .3, host, crosswalk, cohort, True)
    return cohort


def _argv(cohort, tmp_path, report_html, report_out, receipt=None):
    argv = ["--membership", str(cohort / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv"),
            "--summary", str(cohort / "BIGSCAPE_GCF_SUMMARY.tsv"),
            "--pairwise", str(cohort / "BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv"),
            "--direct-edges", str(cohort / "BIGSCAPE_DIRECT_EDGES.tsv"),
            "--out", str(tmp_path / "widgets"), "--require-complete-alias",
            "--report-html", str(report_html), "--report-out", str(report_out),
            "--strain", "DEMO-A", "--family-id", "12"]
    if receipt:
        argv += ["--report-receipt-out", str(receipt)]
    return argv


SOURCE_HTML = "<html><body><main><h1>Fixture</h1><h2>Claim ceiling</h2></main></body></html>"


def test_widget_report_out_cannot_replace_source_report(tmp_path):
    widget = _load("deliverable_tools/bigscape_network_widget.py", "_bnw_alias")
    cohort = _cohort(tmp_path)
    source = tmp_path / "REPORT.html"
    source.write_text(SOURCE_HTML)
    with pytest.raises(SystemExit) as caught:
        widget.main(_argv(cohort, tmp_path, source, source))
    assert "REPORT_INTEGRATION_GATE" in str(caught.value)
    assert source.read_text() == SOURCE_HTML
    assert not (tmp_path / "widgets").exists()


def test_widget_refuses_existing_receipt_and_report_out(tmp_path):
    widget = _load("deliverable_tools/bigscape_network_widget.py", "_bnw_fresh")
    cohort = _cohort(tmp_path)
    source = tmp_path / "REPORT.html"
    source.write_text(SOURCE_HTML)
    receipt = tmp_path / "receipt.json"
    receipt.write_text("prior receipt\n")
    with pytest.raises(SystemExit):
        widget.main(_argv(cohort, tmp_path, source, tmp_path / "INTEGRATED.html", receipt))
    assert receipt.read_text() == "prior receipt\n"
    assert not (tmp_path / "INTEGRATED.html").exists()
    prior = tmp_path / "PRIOR.html"
    prior.write_text("prior integrated copy")
    with pytest.raises(SystemExit):
        widget.main(_argv(cohort, tmp_path, source, prior))
    assert prior.read_text() == "prior integrated copy"
    # a fresh pair works
    assert widget.main(_argv(cohort, tmp_path, source, tmp_path / "NEW.html", tmp_path / "new.json")) == 0
    assert (tmp_path / "NEW.html").exists() and (tmp_path / "new.json").exists()

import csv
import importlib.util
import json
import re
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = load("tools/bigscape_cohort_report.py", "bigscape_cohort_report")
widget = load("deliverable_tools/bigscape_network_widget.py", "bigscape_network_widget")
glossary_tool = load("tools/bigscape_class_glossary.py", "bigscape_class_glossary")


def write_tsv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fixture(tmp_path, complete=True):
    database = tmp_path / "cohort.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        "create table family(id integer,bin_label text,run_id integer,cutoff real);"
        "create table bgc_record_family(family_id integer,record_id integer);"
        "create table bgc_record(id integer,gbk_id integer,product text,category text,contig_edge integer);"
        "create table gbk(id integer,path text);"
        "create table edge_params(id integer,weights text,alignment_mode text,extend_strategy text);"
        "create table distance(record_a_id integer,record_b_id integer,distance real,jaccard real,"
        "adjacency real,dss real,edge_param_id integer);"
    )
    connection.execute("insert into edge_params values(1,'mix','GLOCAL','LEGACY')")
    connection.execute("insert into family values(12,'NRPS',7,.3)")
    for record_id, strain, node in [
        (1, "DEMO-A", "NODE_1_length_100_cov_2"),
        (2, "DEMO-B", "NODE_2_length_200_cov_3"),
    ]:
        connection.execute(
            "insert into gbk values(?,?)", (record_id, f"/input/{strain}_{node}.region001.gbk")
        )
        connection.execute(
            "insert into bgc_record values(?,?,'NRPS','NRPS',?)", (record_id, record_id, record_id - 1)
        )
        connection.execute("insert into bgc_record_family values(12,?)", (record_id,))
    connection.execute("insert into distance values(1,2,.24,.7,.6,.5,1)")
    connection.commit()
    connection.close()
    host = tmp_path / "host.tsv"
    write_tsv(host, [
        {"strain": "DEMO-A", "genus": "GenusA", "host_as_deposited": "Example host"},
        {"strain": "DEMO-B", "genus": "GenusB", "host_as_deposited": "Example environment"},
    ])
    crosswalk = tmp_path / "crosswalk.tsv"
    rows = [{"strain": "DEMO-A", "node_num": "1", "region": "001", "legacy_bgc": "BGC001"}]
    if complete:
        rows.append({"strain": "DEMO-B", "node_num": "2", "region": "001", "legacy_bgc": "BGC002"})
    write_tsv(crosswalk, rows)
    return database, host, crosswalk


def mibig_report_fixture():
    return (
        "<html><body><main>"
        "<!-- MIBIG_IDENTITY_SUMMARY_START -->"
        "<h2>MIBiG Comparator Identity Summary</h2>"
        "<table><tr><th>Rank</th><th>Complete identity</th><th>Comparator</th>"
        "<th>Matched CDS</th><th>Hit fraction</th><th>Mean identity</th>"
        "<th>Median identity</th><th>Range</th></tr>"
        "<tr><td>1</td><td>DEMO-A / NODE_1_length_100_cov_2 / region001 / BGC001</td>"
        "<td>BGC0000001 activity-sounding fixture name</td><td>2/4</td><td>50.0%</td>"
        "<td>60.0%</td><td>60.0%</td><td>55.0-65.0%</td></tr></table>"
        "<!-- MIBIG_IDENTITY_SUMMARY_END -->"
        "<h2>Claim ceiling</h2></main></body></html>"
    )


def mibig_json_fixture(tmp_path):
    root = tmp_path / "mibig"
    root.mkdir()
    (root / "BGC0000001.json").write_text(json.dumps({
        "accession": "BGC0000001",
        "biosynthesis": {"classes": [{"class": "NRPS", "subclass": "Unknown"}]},
    }))
    return root


def test_exact_alias_gate_direct_edges_and_boundary_state(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=False)
    out = tmp_path / "out"
    result = report.build(database, 7, .3, host, crosswalk, out, False)
    assert result["unresolved_alias_records"] == 1
    assert result["direct_edges"] == 1
    members = list(csv.DictReader((out / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv").open(), delimiter="\t"))
    assert {row["boundary_state"] for row in members} == {"CONTIG_EDGE", "INTERIOR"}
    assert all(not Path(row["source_path"]).is_absolute() for row in members)
    assert all("path" not in source and not Path(source["locator"]).is_absolute() for source in result["sources"])
    edges = list(csv.DictReader((out / "BIGSCAPE_DIRECT_EDGES.tsv").open(), delimiter="\t"))
    assert edges[0]["distance"] == "0.24"
    strict_out = tmp_path / "strict"
    with pytest.raises(ValueError, match="EXACT_ALIAS_GATE"):
        report.build(database, 7, .3, host, crosswalk, strict_out, True)
    assert not strict_out.exists()


def test_base_crosswalk_unresolved_sentinel_never_counts_as_complete(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    rows = list(csv.DictReader(crosswalk.open(), delimiter="\t"))
    rows[1]["legacy_bgc"] = "UNRESOLVED_BGC_ALIAS"
    write_tsv(crosswalk, rows)
    out = tmp_path / "out"
    receipt = report.build(database, 7, .3, host, crosswalk, out, False)
    assert receipt["unresolved_alias_records"] == 1
    held = next(row for row in csv.DictReader((out / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv").open(), delimiter="\t") if row["strain"] == "DEMO-B")
    assert held["identity_status"] == "MISSING_BGC_ALIAS_HOLD"
    strict_out = tmp_path / "strict"
    with pytest.raises(ValueError, match="EXACT_ALIAS_GATE"):
        report.build(database, 7, .3, host, crosswalk, strict_out, True)
    assert not strict_out.exists()


def test_exact_alias_overlay_precedes_base_crosswalk_and_is_hashed(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    overlay = tmp_path / "overlay.tsv"
    write_tsv(overlay, [{
        "strain": "DEMO-A",
        "full_node_or_contig": "NODE_1_length_100_cov_2",
        "region": "region001",
        "recovered_bgc_alias": "BGC901",
        "complete_identity": "DEMO-A / NODE_1_length_100_cov_2 / region001 / BGC901",
        "recovery_status": "RESOLVED_EXACT_CURRENT_PACKAGE",
    }])
    out = tmp_path / "out"
    receipt = report.build(database, 7, .3, host, crosswalk, out, True, alias_overlay=overlay)
    members = list(csv.DictReader((out / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv").open(), delimiter="\t"))
    first = next(row for row in members if row["strain"] == "DEMO-A")
    second = next(row for row in members if row["strain"] == "DEMO-B")
    assert first["bgc_alias"] == "BGC901"
    assert first["alias_source"] == "EXACT_ALIAS_OVERLAY"
    assert second["bgc_alias"] == "BGC002"
    assert second["alias_source"] == "BASE_CROSSWALK"
    overlay_source = next(item for item in receipt["sources"] if item["role"] == "exact_alias_overlay")
    assert overlay_source["sha256"] == report.sha256(overlay)
    assert receipt["alias_overlay_summary"] == {"rows": 1, "resolved": 1, "held": 0}


def test_held_alias_overlay_overrides_old_alias_and_never_guesses(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    overlay = tmp_path / "overlay.tsv"
    write_tsv(overlay, [{
        "strain": "DEMO-A",
        "full_node_or_contig": "NODE_1_length_100_cov_2",
        "region": "region001",
        "recovered_bgc_alias": "",
        "complete_identity": "",
        "recovery_status": "HELD_NO_EXACT_CURRENT_PACKAGE_ROW",
    }])
    out = tmp_path / "out"
    receipt = report.build(database, 7, .3, host, crosswalk, out, False, alias_overlay=overlay)
    members = list(csv.DictReader((out / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv").open(), delimiter="\t"))
    held = next(row for row in members if row["strain"] == "DEMO-A")
    assert held["bgc_alias"] == "UNRESOLVED_BGC_ALIAS"
    assert held["identity_status"] == "ALIAS_OVERLAY_HOLD"
    assert held["alias_source"] == "EXACT_ALIAS_OVERLAY_HOLD"
    assert held["alias_recovery_status"] == "HELD_NO_EXACT_CURRENT_PACKAGE_ROW"
    assert receipt["unresolved_alias_records"] == 1
    strict_out = tmp_path / "strict"
    with pytest.raises(ValueError, match="EXACT_ALIAS_GATE"):
        report.build(database, 7, .3, host, crosswalk, strict_out, True, alias_overlay=overlay)
    assert not strict_out.exists()


def test_label_modes_are_deterministic():
    assert widget.label_mode(3) == "SMALL_COMPACT_STRAIN_ALIAS"
    assert widget.label_mode(4) == "MEDIUM_COLLISION_MANAGED_STRAIN"
    assert widget.label_mode(8) == "MEDIUM_COLLISION_MANAGED_STRAIN"
    assert widget.label_mode(9) == "DENSE_FOCAL_LABEL_HOVER_CLICK"


def test_metadata_driven_strain_prefix_supports_hyphens_and_prefers_longest():
    assert report.parse_admitted_gbk_name(
        "/input/DEMO-A_scaffold-alpha.region007.gbk",
        {"DEMO", "DEMO-A"},
    ) == ("DEMO-A", "scaffold-alpha", "007")


def test_metadata_driven_strain_prefix_rejects_unmatched_and_ambiguous_names():
    with pytest.raises(ValueError, match="no admitted strain prefix"):
        report.parse_admitted_gbk_name(
            "/input/UNKNOWN_scaffold-alpha.region007.gbk",
            {"DEMO-A", "DEMO-B"},
        )
    with pytest.raises(ValueError, match="ambiguous admitted strain prefix"):
        report.parse_admitted_gbk_name(
            "/input/DEMO-A_scaffold-alpha.region007.gbk",
            {"DEMO-A", "demo-a"},
        )


def test_unmatched_database_record_is_excluded_and_counted_without_guessing(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    connection = sqlite3.connect(database)
    connection.execute(
        "insert into gbk values(3,'/reference/REFERENCE_scaffold-alpha.region007.gbk')"
    )
    connection.execute("insert into bgc_record values(3,3,'NRPS','NRPS',0)")
    connection.execute("insert into bgc_record_family values(12,3)")
    connection.commit()
    connection.close()
    out = tmp_path / "out"
    receipt = report.build(database, 7, .3, host, crosswalk, out, True)
    assert receipt["records"] == 2
    assert receipt["excluded_unadmitted_records"] == 1
    members = list(csv.DictReader((out / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv").open(), delimiter="\t"))
    assert {row["strain"] for row in members} == {"DEMO-A", "DEMO-B"}


def test_class_nicknames_cover_unknown_and_mixed_without_product_inference():
    code, nickname = report.classify_family([
        {"bin_label": "", "category": "", "product": ""},
    ])
    assert (code, nickname) == ("UNK", "Unresolved class")
    code, nickname = report.classify_family([
        {"bin_label": "NRPS", "category": "NRPS", "product": "NRPS"},
        {"bin_label": "terpene", "category": "terpene", "product": "terpene"},
    ])
    assert (code, nickname) == ("MIX", "Mixed broad classes")
    assert report.classify_family([
        {"bin_label": "NRPS", "category": "NRPS", "product": "NRP-metallophore.NRPS"},
    ])[0] == "NRPS"


def test_single_source_glossary_is_unique_complete_and_documented():
    payload = report.load_class_vocabulary()
    codes = [entry["code"] for entry in payload["entries"]]
    assert len(codes) == len(set(codes))
    assert {"PKS-NRPS", "MIX", "UNK"}.issubset(codes)
    for entry in payload["entries"]:
        assert all(entry[field] for field in (
            "code", "full_name", "plain_language_meaning", "source_basis", "claim_ceiling"
        ))
    generated = glossary_tool.render()
    shipped = (ROOT / "docs" / "BIGSCAPE_CLASS_GLOSSARY.md").read_text()
    assert generated == shipped
    assert "How to read a network" in shipped


def test_widget_and_report_integration_preserve_complete_identity(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    cohort = tmp_path / "cohort"
    report.build(database, 7, .3, host, crosswalk, cohort, True)
    widgets = tmp_path / "widgets"
    result = widget.build(
        cohort / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv",
        cohort / "BIGSCAPE_GCF_SUMMARY.tsv",
        cohort / "BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv",
        widgets,
        cohort / "BIGSCAPE_DIRECT_EDGES.tsv",
        "DEMO-A",
        True,
    )
    assert result["families"] == 1
    assert result["direct_edges"] == 1
    summary = list(csv.DictReader((cohort / "BIGSCAPE_GCF_SUMMARY.tsv").open(), delimiter="\t"))[0]
    assert summary["class_code"] == "NRPS"
    assert summary["class_nickname"] == "Nonribosomal peptide synthetase"
    assert summary["reviewed_subtype_code"] == ""
    source = tmp_path / "REPORT.html"
    source.write_text("<html><body><main><h1>Fixture</h1><h2>Claim ceiling</h2></main></body></html>")
    integrated = tmp_path / "REPORT_INTEGRATED.html"
    receipt = widget.integrate_report_html(
        source,
        integrated,
        cohort / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv",
        cohort / "BIGSCAPE_GCF_SUMMARY.tsv",
        cohort / "BIGSCAPE_DIRECT_EDGES.tsv",
        "DEMO-A",
        ["12"],
    )
    text = integrated.read_text()
    assert receipt["status"] == "PASS"
    assert "DEMO-A / NODE_1_length_100_cov_2 / region001 / BGC001" in text
    assert "DEMO-B / NODE_2_length_200_cov_3 / region001 / BGC002" in text
    assert "Direct BiG-SCAPE edge distance" in text
    assert "cutoff 0.3" in text
    assert "GCF 12 · NRPS" in text
    assert "NRPS means Nonribosomal peptide synthetase" in text
    assert "Open the full BiG-SCAPE class glossary" in text
    shown_codes = re.findall(r"GCF \d+ · ([A-Za-z0-9-]+)", text)
    vocabulary_codes = [entry["code"] for entry in widget.load_class_vocabulary()["entries"]]
    assert shown_codes and all(vocabulary_codes.count(code) == 1 for code in shown_codes)
    assert "GenusA" in text and "Example host" in text
    assert "CONTIG_EDGE" in text and "INTERIOR" in text
    assert widget.CLAIM_CEILING in text


def test_report_integration_refuses_unresolved_selected_family_without_output(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=False)
    cohort = tmp_path / "cohort"
    report.build(database, 7, .3, host, crosswalk, cohort, False)
    source = tmp_path / "REPORT.html"
    source.write_text("<html><body><h2>Claim ceiling</h2></body></html>")
    output = tmp_path / "SHOULD_NOT_EXIST.html"
    with pytest.raises(ValueError, match="EXACT_ALIAS_GATE"):
        widget.integrate_report_html(
            source,
            output,
            cohort / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv",
            cohort / "BIGSCAPE_GCF_SUMMARY.tsv",
            cohort / "BIGSCAPE_DIRECT_EDGES.tsv",
            "DEMO-A",
            ["12"],
        )
    assert not output.exists()


def test_widget_refuses_complete_status_when_display_identity_disagrees(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    cohort = tmp_path / "cohort"
    report.build(database, 7, .3, host, crosswalk, cohort, True)
    membership = cohort / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv"
    rows = list(csv.DictReader(membership.open(), delimiter="\t"))
    rows[0]["locus_display_with_hold"] = "DEMO-A / WRONG_NODE / region001 / BGC001"
    write_tsv(membership, rows)
    with pytest.raises(ValueError, match="EXACT_ALIAS_GATE"):
        widget.build(
            membership, cohort / "BIGSCAPE_GCF_SUMMARY.tsv",
            cohort / "BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv", tmp_path / "widgets",
            cohort / "BIGSCAPE_DIRECT_EDGES.tsv", "DEMO-A", True,
        )


def test_reviewed_subtype_requires_and_displays_its_own_glossary(tmp_path):
    database, host, crosswalk = fixture(tmp_path, complete=True)
    reviewed = tmp_path / "reviewed.tsv"
    write_tsv(reviewed, [{
        "family_id": "12",
        "reviewed_subtype_code": "SUB1",
        "full_name": "Reviewed fixture subtype",
        "plain_language_meaning": "A separately reviewed fixture interpretation.",
        "source_basis": "Generic fixture review record.",
        "claim_ceiling": "Fixture subtype only; no product claim.",
    }])
    cohort = tmp_path / "cohort"
    report.build(database, 7, .3, host, crosswalk, cohort, True, reviewed)
    source = tmp_path / "REPORT.html"
    source.write_text("<html><body><h2>Claim ceiling</h2></body></html>")
    output = tmp_path / "REPORT_INTEGRATED.html"
    widget.integrate_report_html(
        source, output,
        cohort / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv",
        cohort / "BIGSCAPE_GCF_SUMMARY.tsv",
        cohort / "BIGSCAPE_DIRECT_EDGES.tsv",
        "DEMO-A", ["12"],
    )
    text = output.read_text()
    assert "GCF 12 · NRPS · SUB1" in text
    assert "Reviewed subtype SUB1 means Reviewed fixture subtype" in text
    assert "Fixture subtype only; no product claim." in text


def test_mibig_comparator_context_uses_bound_class_and_never_infers_activity(tmp_path):
    mibig = mibig_json_fixture(tmp_path)
    enhanced, receipt = widget.enhance_mibig_summary(mibig_report_fixture(), mibig)
    assert "MIBiG biosynthetic class" in enhanced
    assert "<td>NRPS</td>" in enhanced
    assert f"<td>{widget.NOT_VERIFIED}</td>" not in enhanced
    assert ">Comparator context unresolved</span>" in enhanced
    assert 'data-evidence-status="NOT_VERIFIED_CURRENT_EVIDENCE"' in enhanced
    assert widget.COMPARATOR_CAUTION in enhanced
    assert "activity-sounding fixture name" in enhanced
    assert receipt["rows"] == 1
    assert receipt["class_bound_rows"] == 1
    assert receipt["verified_context_rows"] == 0
    assert receipt["comparator_context_unresolved_rows"] == 1
    assert receipt["class_sources"][0]["sha256"] == widget.sha256(mibig / "BGC0000001.json")


def test_mibig_verified_curated_context_displays_primary_source_links(tmp_path):
    mibig = mibig_json_fixture(tmp_path)
    curated = tmp_path / "curated.tsv"
    evidence = tmp_path / "fixture.xml"
    evidence.write_text("bound primary article")
    write_tsv(curated, [{
        "mibig_accession": "BGC0000001",
        "mibig_biosynthetic_class": "NRPS",
        "activity_category": "antibacterial activity reported for comparator",
        "activity_verification_status": widget.VERIFIED_EVIDENCE,
        "mechanism_or_target": "fixture target reported for comparator",
        "mechanism_verification_status": widget.VERIFIED_EVIDENCE,
        "evidence_status": "ACTIVITY_AND_MECHANISM_VERIFIED_PRIMARY_LITERATURE",
        "pmid": "12345678",
        "pmcid": "",
        "doi": "10.0000/fixture",
        "primary_literature_title": "Fixture primary article",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
        "citation_identifiers": "PMID:12345678",
        "citation_links": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
        "evidence_locator": "Fixture abstract: direct activity and target statement.",
        "hold_reason": "",
        "provenance_source": "fixture.xml",
        "provenance_sha256": widget.sha256(evidence),
        "curator": "fixture-curator",
        "reviewed_at": "2026-09-19",
    }])
    enhanced, receipt = widget.enhance_mibig_summary(mibig_report_fixture(), mibig, curated)
    assert "antibacterial activity reported for comparator" in enhanced
    assert "fixture target reported for comparator" in enhanced
    assert "ACTIVITY_AND_MECHANISM_VERIFIED_PRIMARY_LITERATURE" in enhanced
    assert '<a href="https://pubmed.ncbi.nlm.nih.gov/12345678/"' in enhanced
    assert ">PMID:12345678</a>" in enhanced
    assert receipt["verified_context_rows"] == 1
    assert receipt["curated_context_source"]["sha256"] == widget.sha256(curated)


@pytest.mark.parametrize("broken", [
    {"provenance_sha256": "not-a-sha"},
    {"citation_links": "javascript:alert(1)"},
    {"evidence_status": "UNVERIFIED"},
    {"provenance_source": "missing.xml"},
])
def test_mibig_curated_context_fails_closed_on_unverified_or_invalid_provenance(tmp_path, broken):
    mibig = mibig_json_fixture(tmp_path)
    evidence = tmp_path / "fixture.xml"
    evidence.write_text("bound primary article")
    row = {
        "mibig_accession": "BGC0000001",
        "mibig_biosynthetic_class": "NRPS",
        "activity_category": "fixture activity",
        "activity_verification_status": widget.VERIFIED_EVIDENCE,
        "mechanism_or_target": "fixture target",
        "mechanism_verification_status": widget.VERIFIED_EVIDENCE,
        "evidence_status": "ACTIVITY_AND_MECHANISM_VERIFIED_PRIMARY_LITERATURE",
        "pmid": "12345678",
        "pmcid": "",
        "doi": "10.0000/fixture",
        "primary_literature_title": "Fixture primary article",
        "source_url": "https://doi.org/10.0000/fixture",
        "citation_identifiers": "DOI:10.0000/fixture",
        "citation_links": "https://doi.org/10.0000/fixture",
        "evidence_locator": "Fixture abstract.",
        "hold_reason": "",
        "provenance_source": "fixture.xml",
        "provenance_sha256": widget.sha256(evidence),
        "curator": "fixture-curator",
        "reviewed_at": "2026-09-19",
    }
    row.update(broken)
    curated = tmp_path / "curated.tsv"
    write_tsv(curated, [row])
    with pytest.raises(ValueError, match="MIBIG_CONTEXT_GATE"):
        widget.enhance_mibig_summary(mibig_report_fixture(), mibig, curated)


def test_mibig_field_level_status_preserves_activity_and_mechanism_hold(tmp_path):
    mibig = mibig_json_fixture(tmp_path)
    curated = tmp_path / "curated.tsv"
    evidence = tmp_path / "fixture.xml"
    evidence.write_text("bound primary article")
    write_tsv(curated, [{
        "mibig_accession": "BGC0000001",
        "mibig_biosynthetic_class": "NRPS",
        "activity_category": "antibacterial activity reported for comparator",
        "activity_verification_status": widget.VERIFIED_EVIDENCE,
        "mechanism_or_target": widget.NOT_VERIFIED,
        "mechanism_verification_status": widget.UNVERIFIED_EVIDENCE,
        "evidence_status": "ACTIVITY_VERIFIED_MECHANISM_NOT_VERIFIED",
        "pmid": "12345678",
        "pmcid": "",
        "doi": "10.0000/fixture",
        "primary_literature_title": "Fixture primary article",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
        "citation_identifiers": "PMID:12345678",
        "citation_links": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
        "evidence_locator": "Fixture abstract: activity only.",
        "hold_reason": "No molecular target stated.",
        "provenance_source": "fixture.xml",
        "provenance_sha256": widget.sha256(evidence),
        "curator": "fixture-curator",
        "reviewed_at": "2026-09-19",
    }])
    enhanced, receipt = widget.enhance_mibig_summary(mibig_report_fixture(), mibig, curated)
    assert "ACTIVITY_VERIFIED_MECHANISM_NOT_VERIFIED" in enhanced
    assert ">—</span>" in enhanced
    assert ">Activity verified; mechanism unresolved</span>" in enhanced
    assert receipt["activity_verified_context_rows"] == 1
    assert receipt["mechanism_verified_context_rows"] == 0


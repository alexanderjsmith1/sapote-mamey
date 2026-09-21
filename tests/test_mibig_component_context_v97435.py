from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IDENTITY = "SYNTH-01 / NODE_7_length_47000_cov_20.0 / region001 / BGC004"
ACCESSION = "BGC0002010"


def _load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_tsv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fixture_rows():
    matched = set(range(1, 27)) - {4, 14}
    matched.add(32)
    rows = []
    for order in range(1, 48):
        gene_functions = ""
        if order == 42:
            gene_functions = "biosynthetic (rule-based-clusters) T2PKS: t2ks; KS (Score: 50)"
        elif order == 43:
            gene_functions = "biosynthetic (rule-based-clusters) T2PKS: t2clf; CLF 8|9"
        elif order == 44:
            gene_functions = "biosynthetic-additional (t2pks) ACP (Score: 45)"
        rows.append({
            "complete_identity": IDENTITY,
            "gene_order": str(order),
            "dominant_reference_gene_match": "YES" if order in matched else "NO",
            "dominant_mibig_accession": ACCESSION,
            "primary_functional_role": "core" if order in {42, 43, 44} else "other",
            "functional_logic_tags": "assembly_line_pks" if order in {42, 43, 44} else "",
            "product_annotation": "",
            "sec_met_domains": "",
            "gene_functions": gene_functions,
        })
    return rows


def test_generic_25_in_47_fixture_retains_whole_fraction_and_adds_component(tmp_path):
    tool = _load("deliverable_tools/mibig_component_context.py", "mibig_component_context_test")
    source = tmp_path / "all.tsv"
    extract = tmp_path / "sources" / "exact.tsv"
    out = tmp_path / "component.tsv"
    _write_tsv(source, _fixture_rows())
    row = tool.build(source, IDENTITY, ACCESSION, extract, out, "sources/exact.tsv")
    assert (row["whole_region_matched_cds"], row["whole_region_total_cds"]) == ("25", "47")
    assert (row["coherent_block_matched_cds"], row["local_component_denominator"]) == ("24", "26")
    assert row["gene_order_status"] == "COHERENT_24_OF_26_BLOCK_PLUS_1_OUTLIER"
    assert row["core_completeness_status"] == "MINIMAL_T2PKS_CORE_3_OF_3_PRESENT_OUTSIDE_SELECTED_COMPARATOR_BLOCK"
    assert row["segmentation_hold"] == "OVERMERGED_REGION_COMPONENT_BOUNDARIES_REQUIRE_REVIEW"
    assert row["component_interpretation"] == "COMPONENT_SUPPORTED_PATHWAY_FAMILY_CONTEXT_ONLY"


def test_widget_displays_component_without_replacing_whole_region_metric(tmp_path):
    component_tool = _load("deliverable_tools/mibig_component_context.py", "mibig_component_context_display")
    widget = _load("deliverable_tools/bigscape_network_widget.py", "bigscape_network_widget_component")
    source = tmp_path / "all.tsv"
    extract = tmp_path / "sources" / "exact.tsv"
    context = tmp_path / "component.tsv"
    _write_tsv(source, _fixture_rows())
    component_tool.build(source, IDENTITY, ACCESSION, extract, context, "sources/exact.tsv")
    mibig = tmp_path / "mibig"
    mibig.mkdir()
    (mibig / f"{ACCESSION}.json").write_text(json.dumps({
        "accession": ACCESSION, "biosynthesis": {"classes": [{"class": "PKS"}]}
    }), encoding="utf-8")
    html = (
        "<html><body><!-- MIBIG_IDENTITY_SUMMARY_START --><table>"
        "<tr><th>Rank</th><th>Complete identity</th><th>Comparator</th><th>Matched CDS</th></tr>"
        f"<tr><td>1</td><td>{IDENTITY}</td><td>{ACCESSION}</td><td>25 / 47</td></tr>"
        "</table><!-- MIBIG_IDENTITY_SUMMARY_END --></body></html>"
    )
    rendered, receipt = widget.enhance_mibig_summary(html, mibig, component_context_path=context)
    assert "24/26 matched in genes 1–26 (92.3%); 25/47 retained for the whole region" in rendered
    assert ">25 / 47<" in rendered
    assert "Merged flanks depress the whole-region fraction" in rendered
    assert receipt["component_bound_rows"] == 1


def test_component_context_refuses_missing_bound_evidence(tmp_path):
    tool = _load("deliverable_tools/mibig_component_context.py", "mibig_component_context_missing")
    widget = _load("deliverable_tools/bigscape_network_widget.py", "bigscape_network_widget_missing")
    source = tmp_path / "all.tsv"
    extract = tmp_path / "sources" / "exact.tsv"
    context = tmp_path / "component.tsv"
    _write_tsv(source, _fixture_rows())
    tool.build(source, IDENTITY, ACCESSION, extract, context, "sources/exact.tsv")
    extract.unlink()
    try:
        widget._component_context(context)
    except ValueError as error:
        assert "missing or hash-mismatched evidence file" in str(error)
    else:
        raise AssertionError("missing evidence was accepted")

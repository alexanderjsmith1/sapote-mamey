"""Tests for lightweight SVG locus map renderer — v9.7.145."""
import xml.etree.ElementTree as ET
from pathlib import Path
from mamey.figures.locus_map import render_locus_map_svg, _parse_gbk_cds

# Minimal GBK fixture with two CDS (antiSMASH region format)
MINIMAL_GBK = """\
LOCUS       NODE_32_test           800 bp    DNA     linear
FEATURES             Location/Qualifiers
     CDS             complement(100..500)
                     /locus_tag="ctg32_1"
                     /gene_kind="biosynthetic-additional"
                     /aSDomain="p450"
     CDS             complement(550..790)
                     /locus_tag="ctg32_2"
                     /gene_kind="biosynthetic"
//
"""


def test_render_returns_valid_xml():
    svg = render_locus_map_svg(gbk_text=MINIMAL_GBK, title="Test BGC")
    root = ET.fromstring(svg)
    # Tag may be namespace-qualified: "{http://www.w3.org/2000/svg}svg" or bare "svg"
    assert root.tag == "svg" or root.tag.endswith("}svg")


def test_render_contains_expected_gene_count():
    svg = render_locus_map_svg(gbk_text=MINIMAL_GBK)
    # Should have 2 polygon elements (gene arrows) 
    root = ET.fromstring(svg)
    polygons = root.findall(".//{http://www.w3.org/2000/svg}polygon") or root.findall(".//polygon")
    # SVG namespace may not be present; count polygon tags by text search
    assert svg.count("<polygon") == 2


def test_render_contains_scale_bar():
    svg = render_locus_map_svg(gbk_text=MINIMAL_GBK)
    assert "5 kb" in svg


def test_render_truncation_markers():
    svg = render_locus_map_svg(gbk_text=MINIMAL_GBK, truncated="both")
    assert "truncated" in svg
    assert "polyline" in svg


def test_render_no_truncation():
    svg = render_locus_map_svg(gbk_text=MINIMAL_GBK, truncated="none")
    assert "truncated" not in svg


def test_parse_gbk_cds_extracts_genes():
    genes = _parse_gbk_cds(MINIMAL_GBK)
    assert len(genes) == 2
    assert genes[0].locus == "ctg32_1"
    assert genes[0].strand == "-"
    assert genes[0].p450 is True
    assert genes[1].locus == "ctg32_2"


def test_write_to_file(tmp_path):
    svg = render_locus_map_svg(gbk_text=MINIMAL_GBK, title="Test")
    out = tmp_path / "test_locus_map.svg"
    out.write_text(svg)
    assert out.exists()
    assert out.stat().st_size > 100

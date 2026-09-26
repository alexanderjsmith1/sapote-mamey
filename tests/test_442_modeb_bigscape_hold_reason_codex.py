"""Mode B identity holds must distinguish region and contig mismatch reasons."""

from mamey.modeb_template_emitter import _body_40_bigscape


CONTIG = "NODE_7_length_3666_cov_7.5"


def _render(tmp_path, filename):
    (tmp_path / filename).write_text("")
    facts = {"_sources": {"bigscape_regions_dir": str(tmp_path)},
             "strain_id": "SID999", "contig": CONTIG, "region": "region002",
             "bgc_id": "BGC001"}
    return _body_40_bigscape(facts)


def test_same_full_contig_other_region_is_not_other_assembly(tmp_path):
    section = _render(tmp_path, f"SID999_{CONTIG}.region003.gbk")
    assert "IDENTITY HOLD" in section
    assert "different region" in section
    assert "different assembly" not in section


def test_node_text_inside_other_contig_does_not_claim_same_node(tmp_path):
    section = _render(tmp_path, f"SID999_X{CONTIG}.region002.gbk")
    assert "IDENTITY HOLD" in section
    assert "same node number" not in section
    assert "different assembly" not in section

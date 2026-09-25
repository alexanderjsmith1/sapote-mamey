from pathlib import Path

from mamey.modeb_template_emitter import _body_40_bigscape


def _facts(root: Path, strain: str = "QUERY") -> dict:
    return {
        "_sources": {"bigscape_regions_dir": str(root)},
        "strain_id": strain,
        "contig": "NODE_1_length_100_cov_1",
        "region": "region001",
        "bgc_id": "BGC001",
    }


def test_same_contig_and_region_from_other_strain_is_hold(tmp_path):
    (tmp_path / "REF_NODE_1_length_100_cov_1.region001.gbk").write_text("")
    section = _body_40_bigscape(_facts(tmp_path))
    assert "IDENTITY HOLD" in section
    assert "do not join across strains" in section
    assert "Region GBK bound" not in section


def test_exact_four_field_region_is_bound(tmp_path):
    (tmp_path / "REF_NODE_1_length_100_cov_1.region001.gbk").write_text("")
    (tmp_path / "QUERY_NODE_1_length_100_cov_1.region001.gbk").write_text("")
    section = _body_40_bigscape(_facts(tmp_path))
    assert "Region GBK bound on the exact full contig and region for the same strain" in section
    assert "QUERY_NODE_1_length_100_cov_1.region001.gbk" in section
    assert "REF_NODE_1_length_100_cov_1.region001.gbk" not in section


def test_unknown_strain_is_hold(tmp_path):
    (tmp_path / "QUERY_NODE_1_length_100_cov_1.region001.gbk").write_text("")
    section = _body_40_bigscape(_facts(tmp_path, "?"))
    assert "IDENTITY HOLD" in section
    assert "Region GBK bound" not in section

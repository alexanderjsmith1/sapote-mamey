"""§40 IDENTITY HOLD must give the true reason a region GBK is not bound.

Two real staging shapes put the exact full contig and region in a file the strict strain binding
refuses: a bare `<contig>.<region>.gbk` with no strain prefix, and a prefix that
`bigscape_namespace.strain_from_gbk_name` resolves to the `?` staging-defect sentinel
(`<strain> (1)_…`). Refusing to bind is correct. Calling either one a "different assembly" or
"another strain" is not: both files carry the same assembly's contig name. Strain tokens are
runtime-built so the file carries no cohort identifier.
"""
from pathlib import Path

from mamey.modeb_template_emitter import _body_40_bigscape

T = "AS-" + str(900 + 9)
CONTIG = "NODE_7_length_3666_cov_7.5"


def _facts(root: Path) -> dict:
    return {"_sources": {"bigscape_regions_dir": str(root)}, "strain_id": T,
            "contig": CONTIG, "region": "region002", "bgc_id": "BGC001"}


def test_bare_contig_name_is_held_as_unattributed_not_as_a_different_assembly(tmp_path):
    (tmp_path / f"{CONTIG}.region002.gbk").write_text("")
    section = _body_40_bigscape(_facts(tmp_path))
    assert "IDENTITY HOLD" in section and "Region GBK bound" not in section
    assert "no strain prefix" in section
    assert "different assembly" not in section


def test_unparseable_prefix_is_held_as_a_staging_defect_not_as_another_strain(tmp_path):
    (tmp_path / f"{T} (1)_{CONTIG}.region002.gbk").write_text("")
    section = _body_40_bigscape(_facts(tmp_path))
    assert "IDENTITY HOLD" in section and "Region GBK bound" not in section
    assert "staging defect" in section
    assert "another strain" not in section and "across strains" not in section


def test_different_full_contig_with_same_node_is_still_a_different_assembly(tmp_path):
    (tmp_path / f"{T}_NODE_7_length_1234_cov_9.9.region002.gbk").write_text("")
    section = _body_40_bigscape(_facts(tmp_path))
    assert "different assembly" in section


def test_contig_suffix_collision_is_not_treated_as_the_same_contig(tmp_path):
    # `XNODE_7_…` ends with the contig text but is a different contig name.
    (tmp_path / f"{T}_X{CONTIG}.region002.gbk").write_text("")
    section = _body_40_bigscape(_facts(tmp_path))
    assert "no strain prefix" not in section and "staging defect" not in section

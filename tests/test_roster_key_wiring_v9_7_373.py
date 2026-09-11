"""Locks in the v9.7.373 roster-key wiring (B2).

`mamey.authored_verify._bgc_context_from_package` now binds the authoritative
per-BGC locus-tag roster into ctx["known_locus_tags"], read by the .372 matrix
gate `_section4_complete_blastp_matrix_findings`. Before this fix no production
caller set that key, so finished cards verified with --package/--bgc always hit
BLASTP_MATRIX_ROSTER_UNBOUND. These tests prove the key is set, is filtered
per-BGC (not the strain-wide universe), and is absent when a bgc has no members.
"""

from mamey.authored_verify import _bgc_context_from_package

_HEADER = "bgc_id,rank,locus_tag,contig,bgc_start,bgc_end,cds_start,cds_end"
_ROWS = [
    "BGC001,1,ctg1_10,ctg1,1000,9000,1000,1500",
    "BGC001,2,ctg1_11,ctg1,1000,9000,2000,2500",
    "BGC001,3,ctg1_12,ctg1,1000,9000,3000,3500",
    "BGC002,1,ctg2_5,ctg2,100,4000,100,600",
    "BGC002,2,ctg2_6,ctg2,100,4000,700,1200",
]


def _make_pkg(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    csv_path = pkg / "AS-TEST_gene_by_gene_all_bgcs.csv"
    csv_path.write_text("\n".join([_HEADER, *_ROWS]) + "\n", encoding="utf-8")
    return pkg


def test_known_locus_tags_bound_per_bgc_for_bgc001(tmp_path):
    pkg = _make_pkg(tmp_path)
    ctx = _bgc_context_from_package(str(pkg), "BGC001")
    assert ctx is not None
    # sorted, per-BGC roster; no BGC002 loci leak in
    assert ctx["known_locus_tags"] == ["ctg1_10", "ctg1_11", "ctg1_12"]
    # the full locus->home map is built and the per-BGC filter is real
    assert ctx.get("locus_home", {}).get("ctg2_5") == "BGC002"


def test_known_locus_tags_bound_per_bgc_for_bgc002(tmp_path):
    pkg = _make_pkg(tmp_path)
    ctx = _bgc_context_from_package(str(pkg), "BGC002")
    assert ctx is not None
    assert ctx["known_locus_tags"] == ["ctg2_5", "ctg2_6"]


def test_absent_bgc_yields_no_roster_key(tmp_path):
    pkg = _make_pkg(tmp_path)
    ctx = _bgc_context_from_package(str(pkg), "BGC999")
    assert ctx is not None
    # the code only sets the key `if _roster:`; an unknown bgc has no members
    assert not ctx.get("known_locus_tags")
    # but the home map is still built (proves we reached the roster branch)
    assert ctx.get("locus_home", {}).get("ctg1_10") == "BGC001"

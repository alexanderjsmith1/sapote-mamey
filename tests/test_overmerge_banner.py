"""HIGH — emit-modeb-template must surface Patch G's over-merge signal so an authoring chat doesn't
write a single-product card for a region antiSMASH resolved as >=2 protoclusters. Same failure class
as the Patch A blank-grid bug (author over a skeleton that doesn't warn you)."""
import tempfile
from pathlib import Path

from mamey.modeb_template_emitter import _over_merge_facts, _over_merge_banner


def _pkg_with_csv(rows: str) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "predicted_polymers.csv").write_text(
        "record_id,region_number,predicted_polymer,n_protoclusters,candidate_kind,over_merge_flag\n" + rows)
    return d


def test_banner_fires_on_over_merged_region():
    """v9.7.240 (P1): `facts` must now carry the BGC's own `region`.

    This test previously passed `facts` with no region key at all, and asserted the
    banner fired -- which is exactly the contig-only match the P1 patch removes. It
    could not have caught the inheritance bug (see the next test): with only a contig
    to match on, a hit on ANY region of that contig satisfied it. Updated to supply the
    region, which is what the emitter really has (facts["region"] comes from the triage
    board's antiSMASH_Region column).
    """
    d = _pkg_with_csv("NODE_6_length_340027_cov_84.228413,2,(Ser-Leu),3,chemical_hybrid|neighbouring,YES (>=2 BGCs)\n")
    facts = {"node": "NODE_6_length_340027_cov_84", "contig": "NODE_6_length_340027_cov_84",
             "region": "region002"}
    fx = _over_merge_facts(d, facts)
    assert fx.get("over_merge") is True
    assert fx["n_protoclusters"] == "3"
    banner = _over_merge_banner(fx)
    assert "OVER-MERGED REGION" in banner and "3 protoclusters" in banner


def test_banner_is_not_inherited_by_a_sibling_region_on_the_same_contig():
    """The P1 regression, in the file that should have caught it.

    NODE_2 region001 is over-merged (2 protoclusters); NODE_2 region003 is a single
    lanthipeptide protocluster. Pre-patch, region003 inherited region001's banner.
    On the real AS-421 package this stamped a false banner on 7 of 13 templates.
    """
    d = _pkg_with_csv(
        "NODE_2_length_553361_cov_80.858698,1,(Leu),2,neighbouring|single,YES (>=2 BGCs)\n"
        "NODE_2_length_553361_cov_80.858698,2,(Thr-Leu),1,single,no\n")
    base = {"node": "NODE_2_length_553361_cov_80", "contig": "NODE_2_length_553361_cov_80"}

    assert _over_merge_facts(d, {**base, "region": "region001"}).get("over_merge") is True
    assert _over_merge_facts(d, {**base, "region": "region002"}) == {}
    # region003 has no row in predicted_polymers.csv at all (lanthipeptide, no polymer
    # prediction). Honest-blank, not inherited.
    assert _over_merge_facts(d, {**base, "region": "region003"}) == {}


def test_manifest_protocluster_count_is_the_fallback_for_unrowed_regions():
    """predicted_polymers.csv covers only NRPS/PKS-bearing regions, so a
    lanthipeptide+terpene merge has no row. manifest protocluster_count (P2) covers it."""
    d = _pkg_with_csv("")
    base = {"node": "NODE_9_length_297282_cov_79", "contig": "NODE_9_length_297282_cov_79",
            "region": "region001"}
    assert _over_merge_facts(d, {**base, "manifest_protocluster_count": 3}) == {
        "over_merge": True, "n_protoclusters": 3, "candidate_kind": "?"}
    assert _over_merge_facts(d, {**base, "manifest_protocluster_count": 1}) == {}


def test_no_false_positive_on_single_protocluster():
    d = _pkg_with_csv("NODE_9_length_100_cov_5.111,1,(Ala),1,single,no\n")
    facts = {"node": "NODE_9_length_100_cov_5", "contig": "NODE_9_length_100_cov_5"}
    assert _over_merge_facts(d, facts) == {}
    assert _over_merge_banner({}) == ""


def test_honest_blank_when_csv_absent():
    d = Path(tempfile.mkdtemp())  # no predicted_polymers.csv
    assert _over_merge_facts(d, {"node": "NODE_1", "contig": "NODE_1"}) == {}

"""v9.7.42 — co-cluster product-gate exemption (from the v9.7.41 lateral review).

A genuine cross-contig split is complementary by construction (core + tailoring carry different labels),
so the v9.7.41 product gate demotes it as `incompatible_product_classes`. The carve-out restores such a
pair ONLY when corroborated by >=2 OVERLAPPING/ADJACENT MIBiG cluster references, and ONLY on the
`incompatible_product_classes` reason — never on convergence-on-exclusion (`no_specific_product_class`,
the saccharide/NAPAA case) or distinct RiPP subclasses.

Real-strain proof (not automated here — needs the PRIVATE strain zips):
  indolocarbazole pair (indole core + halogenated/saccharide arm; two MIBiG refs gap=1 and gap=3,
    mibig_gg=2) -> HIGH via OK_cocluster_exempt_complementary_shared_mibig.
  NAPAA convergence pair (mibig_gg=3 but reason=no_specific) -> stays MODERATE.
"""
import mamey.rggmci as rg


def test_exempt_fires_on_incompatible_with_two_mibig():
    assert rg._cocluster_exempt("DEMOTED_HIGH_TO_MODERATE_incompatible_product_classes", 2) is True


def test_exempt_needs_two_mibig_not_one():
    # the review's point: a single shared MIBiG cluster must not exempt.
    assert rg._cocluster_exempt("DEMOTED_HIGH_TO_MODERATE_incompatible_product_classes", 1) is False


def test_exempt_never_fires_on_no_specific_even_with_many_mibig():
    # the NAPAA negative: 3 ADJACENT MIBiG refs, but convergence-on-exclusion stays demoted.
    assert rg._cocluster_exempt("DEMOTED_HIGH_TO_MODERATE_no_specific_product_class_after_exclusions", 3) is False


def test_exempt_never_fires_on_distinct_ripp():
    assert rg._cocluster_exempt("DEMOTED_HIGH_TO_MODERATE_distinct_ripp_subclasses", 2) is False


def test_ranked_output_carries_mibig_good_geometry_field():
    # the field must exist for transparency + the post-fix recalibration.
    import inspect
    src = inspect.getsource(rg.compute_rggmci)
    assert '"mibig_good_geometry_references": acc["mibig_good_geometry_references"]' in src

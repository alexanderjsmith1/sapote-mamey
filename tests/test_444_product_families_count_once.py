"""A region's product types and antiSMASH's category for them are one class, not two.

antiSMASH writes a product type (/product, e.g. "T1PKS") and its category (/category, e.g. "PKS") on each
protocluster. BGC products hold the types only; rules about a family read the category table in
mamey/class_architecture.py. These tests pin three things:
  - rules that ask about a family (RiPP, PKS, terpene, and CCTT trigger corroboration) give the same answer with
    or without the category words;
  - the multi-class guard counts families, so an ordinary two-family hybrid is not called multi-class;
  - the guards that read a region's own types (weak-only standing rules, housekeeping inventory) apply to the
    types, which the category words used to block; keyword credit comes from the types alone.
"""
import glob
import os
import re
import zipfile

import pytest

from mamey import class_architecture as A
from mamey import parsers
from mamey import scoring as S
from mamey.models import BGCRecord

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
HUMIDA = os.path.join(FIXTURES, "micromonospora_humida_JAFEUC01.zip")


def cap(products, ks=0, c=0, a=0, tail=()):
    return A.classify_architecture("BGC001", products, ks, c, a, list(tail)).capacity


@pytest.mark.parametrize("types,with_category,ks,c,a,tail,expect", [
    (["lanthipeptide-class-i"], ["lanthipeptide-class-i", "RiPP"], 0, 0, 0, [], "RiPP"),
    (["RiPP-like"], ["RiPP-like", "RiPP"], 0, 0, 0, [], "RiPP"),
    (["thioamitides"], ["thioamitides", "RiPP"], 0, 0, 0, [], "RiPP"),
    (["T3PKS"], ["T3PKS", "PKS"], 0, 0, 0, ["prenyltransferase"], "meroterpenoid"),
    (["T1PKS", "NRPS"], ["T1PKS", "PKS", "NRPS"], 2, 2, 2, [], "PKS-NRPS hybrid"),
    (["arylpolyene", "T2PKS"], ["arylpolyene", "T2PKS", "PKS"], 0, 0, 0, [], "aromatic type II PKS"),
    (["terpene-precursor"], ["terpene-precursor", "terpene"], 0, 0, 0, [], "terpene"),
    (["CDPS"], ["CDPS", "NRPS"], 0, 0, 0, [], "diketopiperazine"),
    (["NRP-metallophore"], ["NRP-metallophore", "NRPS"], 0, 2, 3, [], "siderophore"),
])
def test_family_rules_answer_the_same_with_or_without_category_words(types, with_category, ks, c, a, tail, expect):
    assert expect in cap(types, ks, c, a, tail)
    assert cap(types, ks, c, a, tail) == cap(with_category, ks, c, a, tail)


@pytest.mark.parametrize("products,multi", [
    (["T1PKS", "NRPS"], False),                         # PKS + NRPS: two families
    (["T1PKS", "PKS", "NRPS"], False),                  # the category word adds no class
    (["NRPS", "T1PKS", "lanthipeptide-class-i"], True),  # NRPS + PKS + RiPP
    (["betalactone", "NRPS", "T1PKS"], True),           # a listed class from antiSMASH's catch-all "other"
    (["halogenated", "NRPS", "T1PKS"], False),          # an unlisted "other" label is not a class
    (["terpene-precursor", "NRPS", "T1PKS"], False),    # a noise label never counts
])
def test_multiclass_guard_counts_families(products, multi):
    assert ("complex multi-class" in cap(products, 2, 2, 2)) is multi


def _fixture_protocluster_pairs():
    pairs = set()
    for z in sorted(glob.glob(os.path.join(FIXTURES, "*.zip"))):
        try:
            zf = zipfile.ZipFile(z)
        except zipfile.BadZipFile:
            continue
        for name in zf.namelist():
            if not name.endswith(".gbk"):
                continue
            product = category = None
            in_protocluster = False
            for line in zf.read(name).decode("utf-8", "replace").splitlines():
                if line.startswith("ORIGIN"):
                    break
                m = re.match(r"^ {5}(\S+)\s+\S", line)
                if m:
                    if in_protocluster and product and category:
                        pairs.add((product, category))
                    in_protocluster, product, category = m.group(1) == "protocluster", None, None
                    continue
                q = re.match(r'^ {21}/(product|category)="([^"]*)"', line)
                if q and in_protocluster:
                    if q.group(1) == "product":
                        product = q.group(2)
                    else:
                        category = q.group(2)
            if in_protocluster and product and category:
                pairs.add((product, category))
    return pairs


def test_family_table_matches_antismash_on_every_bundled_fixture():
    pairs = _fixture_protocluster_pairs()
    assert pairs, "no protocluster product/category pairs in tests/fixtures; this test would compare nothing"
    wrong = sorted((p, c, A.product_family(p)) for p, c in pairs if A.product_family(p) != c.lower())
    assert not wrong, wrong


def test_unknown_types_are_placed_by_name():
    assert A.product_family("archaeal-RiPP-like") == "ripp"
    assert A.product_family("PpyS-KS") == "pks"
    assert A.product_family("a-new-label") == "other"


def test_region_products_hold_types_not_categories():
    if not os.path.exists(HUMIDA):
        pytest.skip("micromonospora_humida_JAFEUC01.zip fixture not available")
    bgcs = parsers.parse_bgcs_from_zip(HUMIDA)
    assert [b.products for b in bgcs] == [["T2PKS", "arylpolyene", "fatty_acid"], ["NRPS", "T1PKS", "hglE-KS"]]


def _bgc(products):
    return BGCRecord("BGC001", "ctg1", 1, 1, 1000, 50000, products=products)


def test_weak_only_region_meets_its_standing_rule():
    # NRPS-like + saccharide is weak-only; the leaked category word "nrps" used to make it look committed.
    assert "saccharide" in S.standing_rule_for("nrps-like saccharide", "nrps-like saccharide")
    assert S.standing_rule_for("t1pks saccharide", "t1pks saccharide") == ""   # a committed class still protects


def test_housekeeping_inventory_reads_the_type():
    assert S.is_housekeeping_only(_bgc(["NAPAA"]))
    assert not S.is_housekeeping_only(_bgc(["NAPAA", "T1PKS"]))


def test_keyword_credit_comes_from_the_product_types_alone():
    # Category words are not class evidence: parsed end to end, a T2PKS region banks no bare "pks" or "other".
    if not os.path.exists(HUMIDA):
        pytest.skip("micromonospora_humida_JAFEUC01.zip fixture not available")
    bgc = parsers.parse_bgcs_from_zip(HUMIDA)[0]
    tokens = set(re.split(r"[^a-z0-9_]+", S.scoring_class_text(bgc)))
    assert "t2pks" in tokens and not tokens & {"pks", "other", "nrps", "ripp"}, tokens


@pytest.mark.parametrize("trigger,types,corroborated", [
    ("T43-THA_thioamide", ["T2PKS", "saccharide", "thioamide-NRP"], True),   # an NRP by family, not by name
    ("T43-LAN_lanthipeptide", ["RRE-containing", "saccharide", "terpene"], True),  # a RiPP by family
    ("T43-THA_thioamide", ["T2PKS", "saccharide"], False),
    ("T43-LAN_lanthipeptide", ["terpene"], False),
])
def test_trigger_corroboration_reads_families(trigger, types, corroborated):
    from mamey.source_scans import cctt_trigger_corroborated
    assert cctt_trigger_corroborated(trigger, types) is corroborated


def test_the_family_table_lives_in_one_module():
    from mamey import rggmci as R, source_scans as SS
    assert S.product_families is A.product_families and R.product_families is A.product_families
    assert SS.product_families is A.product_families


def test_rggmci_reads_families_where_it_compares_labels():
    from mamey import rggmci as R
    # an NRPS fragment and a PKS-family fragment are the NRPS + PKS hybrid, whichever PKS type antiSMASH gave
    for pks_side in ("arylpolyene; fatty_acid", "PKS-like; T3PKS"):
        assert R._product_class_gate("HIGH_RG_GMCI_RESCUE", "NRPS", pks_side)[0] == "HIGH_RG_GMCI_RESCUE"
    assert "pks" in R._product_tokens(["T3PKS"]) and "pks" in R._product_tokens(["T1PKS"])
    # the weak-label guards still read the types: NAPAA with fatty_acid is noise on both sides
    assert R._r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "NAPAA", "fatty_acid")[0] == "MODERATE_RG_GMCI_CANDIDATE"

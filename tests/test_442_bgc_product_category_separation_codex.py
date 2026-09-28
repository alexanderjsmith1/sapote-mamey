"""BGC product classes come from product qualifiers, not broad categories."""

import zipfile

import pytest

from mamey.parsers import parse_bgcs_from_zip


@pytest.mark.parametrize("product,category", [
    ("NRPS-like", "NRPS"),
    ("T1PKS", "PKS"),
    ("terpene", "other"),
])
def test_region_category_does_not_become_product_class(tmp_path, product, category):
    gbk = f'''LOCUS       NODE_1                   60 bp    DNA     linear   BCT 01-JAN-2026
FEATURES             Location/Qualifiers
     source          1..60
                     /organism="Fixture species"
     region          1..60
                     /product="{product}"
                     /category="{category}"
     protocluster    1..60
                     /protocluster_number="1"
                     /product="{product}"
                     /category="{category}"
ORIGIN
        1 aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa
//
'''
    archive = tmp_path / "synthetic_antismash.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("NODE_1.region001.gbk", gbk)

    bgcs = parse_bgcs_from_zip(archive)

    assert len(bgcs) == 1
    assert bgcs[0].products == [product]


def test_cds_fallback_keeps_existing_behavior(tmp_path):
    gbk = '''LOCUS       NODE_1                   60 bp    DNA     linear   BCT 01-JAN-2026
FEATURES             Location/Qualifiers
     source          1..60
                     /organism="Fixture species"
     CDS             1..60
                     /product="fallback enzyme"
ORIGIN
        1 aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa
//
'''
    archive = tmp_path / "synthetic_antismash.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("NODE_1.region001.gbk", gbk)

    bgcs = parse_bgcs_from_zip(archive)

    assert len(bgcs) == 1
    assert bgcs[0].products == ["fallback enzyme"]

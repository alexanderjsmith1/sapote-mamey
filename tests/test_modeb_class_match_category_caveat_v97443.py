"""§44 §46 §47 class matching reads a package `Products` column that can carry antiSMASH's /category.

`parsers._feature_products` wrote a region's /category beside its /product. A region whose product is
`NRPS-like` therefore lists `NRPS` too, and matches a class defined by the product `NRPS`. The emitter
cannot tell product from category in that column, so it must say the count is an upper bound whenever
the class uses a token that is both a category and a product name. Fixtures use AS-XXX.
"""
from __future__ import annotations

import json
import pathlib
import re

from mamey import modeb_template_emitter as em

INV = "BGC_ID,Contig,antiSMASH_Region,Products,KCB_top,Strain\n"
TRIAGE = ("BGC_ID,Node_ID,Contig,antiSMASH_Region,Products,Boundary,Assembly_Locator,Length_kb,"
          "Lead_tier_auto,Corrected_rank,KCB_top\n")


def _pkg(root: pathlib.Path, name: str, rows: str) -> pathlib.Path:
    pkg = root / name / "package"
    pkg.mkdir(parents=True)
    (pkg / f"{name}_1_intake.json").write_text(json.dumps({"strain_id": name, "antismash_profile": "loose"}))
    (pkg / f"{name}_2_inventory.csv").write_text(INV + rows)
    return pkg


def _s44(tmp_path: pathlib.Path, focal_products: str) -> str:
    cohort = tmp_path / "cohort"
    focal = _pkg(cohort, "AS-XXX", f"BGC001,ctg1,region001,{focal_products},,AS-XXX\n")
    (focal / "manifest.json").write_text(json.dumps({"strain_id": "AS-XXX", "taxonomy": "sp."}))
    (focal / "AS-XXX_4_triage_board.csv").write_text(
        TRIAGE + f"BGC001,NODE_1,ctg1,region001,{focal_products},Interior,x,40,HIGH,1,\n")
    # NRPS-like product with its NRPS category in the same column
    _pkg(cohort, "AS-2", "BGC001,ctgA,region001,NRPS-like; NRPS,,AS-2\n")
    em._PACKAGE_SCAN_CACHE.clear()
    card = em.emit_card_template(focal, "BGC001", sources={"cohort_dir": str(cohort)})
    parts = re.split(r"(?m)^## §(\d+) ", card)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}[44]


def test_a_class_named_by_a_category_token_is_reported_as_an_upper_bound(tmp_path):
    s44 = _s44(tmp_path, "NRPS")
    assert "**Numerator:** 2 loci in 2 of 2 packages." in s44   # the NRPS-like row matched on its category
    assert "upper bound" in s44 and "`nrps`" in s44


def test_a_class_without_category_tokens_carries_no_caveat(tmp_path):
    s44 = _s44(tmp_path, "T1PKS; PKS")                            # PKS is category-only: never widens a match
    assert "upper bound" not in s44


def test_caveat_names_only_the_ambiguous_tokens():
    line = em._category_caveat(frozenset({"nrps", "thioamide-nrp", "pks"}))
    assert "`nrps`" in line and "`pks`" not in line and "thioamide" not in line

"""Product parking matches whole antiSMASH product names, not substrings (card 09AF774E_442).

Product names are the real shapes seen in a BiG-SCAPE 2 database: hybrids joined with ".", and "-"/"_"
inside single names (terpene-precursor, fatty_acid). Parking "terpene" must not hide "terpene-precursor".
"""
import csv
import json
from pathlib import Path

import pytest

from tools import bigscape_cross_strain as cross

PRODUCTS = ["terpene", "terpene-precursor", "other.terpene-precursor", "NRPS.T1PKS.terpene",
            "saccharide.terpene", "oligosaccharide", "T2PKS.oligosaccharide", "saccharide"]


def _rows():
    return [dict(cutoff=".7", family_id=str(i), run_id="1", normalized_cutoff="0.7", qualified_family_id=f"1:0.7:{i}",
                 gcf_namespace="fixture", n_strains="2", strains="query-1,ref-1", strain_labels="query-1; ref-1",
                 n_members="2", bin="example", dominant_product=p, contains_MIBiG="no", members_locators="source-records")
            for i, p in enumerate(PRODUCTS, 1)]


def _run(monkeypatch, tmp_path, *extra):
    monkeypatch.setattr(cross, "build_rows", lambda *args: _rows())
    out = tmp_path / "families.tsv"
    assert cross.main(["--db", "unused", "--out", str(out), "--run-id", "1", "--exclude-products", "terpene,saccharide", *extra]) == 0
    kept = {r["dominant_product"] for r in csv.DictReader(out.open(), delimiter="\t")}
    parked = {r["dominant_product"] for r in csv.DictReader(Path(str(out) + ".PARKED.tsv").open(), delimiter="\t")}
    receipt = json.loads(Path(str(out) + ".FILTER.json").read_text())
    return kept, parked, receipt


def test_default_parks_only_families_made_entirely_of_named_products(monkeypatch, tmp_path):
    kept, parked, receipt = _run(monkeypatch, tmp_path)
    assert parked == {"terpene", "saccharide.terpene", "saccharide"}
    assert {"terpene-precursor", "oligosaccharide", "T2PKS.oligosaccharide", "NRPS.T1PKS.terpene"} <= kept
    assert receipt["match"] == "all-tokens" and receipt["parked"] == 3 and receipt["kept"] == 5
    assert "terpene-precursor" in receipt["kept_containing_a_token"]


def test_any_token_also_parks_a_hybrid_that_carries_a_named_product(monkeypatch, tmp_path):
    kept, parked, receipt = _run(monkeypatch, tmp_path, "--exclude-match", "any-token")
    assert parked == {"terpene", "saccharide.terpene", "saccharide", "NRPS.T1PKS.terpene"}
    assert "terpene-precursor" in kept and "oligosaccharide" in kept
    assert receipt["match"] == "any-token"


def test_contains_mode_keeps_the_legacy_substring_behaviour_and_says_so(monkeypatch, tmp_path):
    kept, parked, receipt = _run(monkeypatch, tmp_path, "--exclude-match", "contains")
    assert parked == set(PRODUCTS) and kept == set()
    assert receipt["rule"] == "case-insensitive contains match on dominant_product"


@pytest.mark.parametrize("product,tokens,mode,expected", [
    ("Terpene", ["terpene"], "all-tokens", True),
    ("terpene-precursor", ["terpene"], "all-tokens", False),
    ("fatty_acid.saccharide", ["saccharide"], "all-tokens", False),
    ("fatty_acid.saccharide", ["saccharide"], "any-token", True),
    ("", ["terpene"], "all-tokens", False),
])
def test_is_parked_token_rules(product, tokens, mode, expected):
    assert cross.is_parked(product, tokens, mode) is expected

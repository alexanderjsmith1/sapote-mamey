"""Tests for the --capacity-csv no-workbook path in cohort_synthesis."""
import csv
import pytest
from mamey.cohort_synthesis import (
    load_from_capacity_csv,
    write_synthesis_from_capacity_csv,
)

_ROWS = [
    {"strain":"DEMO_A","genus":"Streptomyces","host":"Bombus sp.","host_group":"Bombus",
     "total_bgcs_raw":"40","deeply_carded":"12","pct_carded":"30",
     "analytical_depth":"FULL","n_xstrain_flags":"3",
     "HSAF_PTM":"1","lanthipeptide":"1","phosphonate":"0"},
    {"strain":"DEMO_B","genus":"Pseudonocardia","host":"Attine","host_group":"Attine",
     "total_bgcs_raw":"20","deeply_carded":"4","pct_carded":"20",
     "analytical_depth":"NARRATIVE","n_xstrain_flags":"0",
     "HSAF_PTM":"0","lanthipeptide":"1","phosphonate":"1"},
]

@pytest.fixture
def cap_csv(tmp_path):
    p = tmp_path / "capacity.csv"
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_ROWS[0].keys())
        w.writeheader(); w.writerows(_ROWS)
    return p

def test_load_from_capacity_csv_structure(cap_csv):
    M = load_from_capacity_csv(cap_csv)
    assert M["N"] == 2
    assert "DEMO_A" in M["registry"]
    assert M["registry"]["DEMO_A"]["host_group"] == "Bombus"
    assert M["prevalence"]["HSAF_PTM"]["n_strains"] == 1
    assert M["prevalence"]["lanthipeptide"]["n_strains"] == 2

def test_write_synthesis_from_capacity_csv_runs(cap_csv):
    md = write_synthesis_from_capacity_csv(cap_csv)
    assert "Cross-Strain Capacity Synthesis" in md
    # strain IDs must not leak into the title/headline block (first 8 lines);
    # naming a carrier in the cohort-unique section (§3) is legitimate.
    headline = "\n".join(md.split("\n")[:8])
    assert "DEMO_A" not in headline
    assert "Streptomyces" in md
    assert "novelty" in md.lower()  # the absence note must be present
    assert "B1_BGC_Master" in md   # explicitly notes the missing section

def test_capacity_csv_cli_path(cap_csv, tmp_path):
    from mamey.cohort_synthesis import main
    out = tmp_path / "out.md"
    rc = main(["--capacity-csv", str(cap_csv), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    assert out.stat().st_size > 100

def test_capacity_csv_cli_requires_one_of_master_or_csv(tmp_path):
    from mamey.cohort_synthesis import main
    out = tmp_path / "out.md"
    rc = main(["--out", str(out)])
    assert rc == 2  # neither --master nor --capacity-csv


# --- Bunny Hop (v9.7.119): carrier token-match + missing-strain guard ---

def test_differentiating_carrier_token_match_not_substring():
    """§5 carrier lookup must token-match, not bare-substring: 'lanthipeptide' must NOT
    match 'class-i-lanthipeptide'. Crafted so substring picks A (wrong), token picks B (right)."""
    import re
    bgcs = [
        {"strain": "STRAIN_A", "products": "class-i-lanthipeptide; terpene"},
        {"strain": "STRAIN_B", "products": "lanthipeptide; NI-siderophore"},
    ]
    c = "lanthipeptide"
    # old (buggy) substring behaviour would pick STRAIN_A:
    substr_pick = next((b["strain"] for b in bgcs if c in b["products"]), "?")
    assert substr_pick == "STRAIN_A"  # documents the old wrong answer
    # correct token-split behaviour picks STRAIN_B:
    token_pick = next(
        (b["strain"] for b in bgcs
         if c in [t.strip() for t in re.split(r"[;,]", b["products"])]), "?")
    assert token_pick == "STRAIN_B"


def test_load_from_capacity_csv_missing_strain_column_raises(tmp_path):
    """A capacity CSV without a 'strain' column must raise ValueError (not KeyError)."""
    import csv
    p = tmp_path / "nostrain.csv"
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["genus", "host", "HSAF_PTM"])
        w.writeheader()
        w.writerow({"genus": "Streptomyces", "host": "Bombus", "HSAF_PTM": "1"})
    from mamey.cohort_synthesis import load_from_capacity_csv
    import pytest as _pt
    with _pt.raises(ValueError, match="strain"):
        load_from_capacity_csv(p)

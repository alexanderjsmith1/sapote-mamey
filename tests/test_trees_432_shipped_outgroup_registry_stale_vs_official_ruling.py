"""TREES_432 — the shipped registry (mamey/data/outgroup_registry.tsv) must agree with the ruled
OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv on every LOCKED row.

The shipped file is a verbatim snapshot of the ruled table (its own header names the snapshot
date). On a machine without the OFFICIAL_DATA table this test skips; on the owner's machine it
fails the moment the ruled table moves ahead of the snapshot, which is the signal to re-snapshot
at the next cut.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHIPPED = ROOT / "mamey" / "data" / "outgroup_registry.tsv"
OFFICIAL = ROOT.parents[2] / "OFFICIAL_DATA" / "OUTGROUP_REGISTRY.tsv"
COLS = ["tree_scope", "ingroup_taxon", "family", "outgroup_genus",
        "outgroup_species_strain", "assembly_accession", "status", "rationale"]


def _rows(path):
    rows = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#") or ln.startswith("tree_scope"):
            continue
        c = ln.split("\t") + [""] * len(COLS)
        r = dict(zip(COLS, c))
        if r["status"] == "LOCKED":
            rows[(r["tree_scope"], r["ingroup_taxon"])] = (r["outgroup_genus"], r["outgroup_species_strain"],
                                                          r["assembly_accession"])
    return rows


@pytest.mark.skipif(not OFFICIAL.is_file(), reason="OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv not on this machine")
def test_every_locked_row_agrees_with_the_official_ruling():
    shipped, official = _rows(SHIPPED), _rows(OFFICIAL)
    missing = sorted(set(official) - set(shipped))
    differing = sorted(k for k in set(official) & set(shipped) if official[k] != shipped[k])
    assert not missing, f"LOCKED rows ruled but not shipped: {missing}"
    assert not differing, "LOCKED rows that contradict the ruling: " + "; ".join(
        f"{k}: shipped={shipped[k]} official={official[k]}" for k in differing)

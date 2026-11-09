"""Extended cohort figures: missing KCB scores, unknown boundaries and missing resistance tiers
keep their own group and stay in the denominator; they are never counted as 0 or as a negative."""
import csv
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from mamey.cohort_figures_extended import fig_boundary_profile, fig_kcb_novelty, fig_resistance_map

GENE_HEADER = ["bgc_id", "locus_tag", "sec_met_domains", "bldA_tta_tier", "resistance_tier"]


def _package(root: Path, sid: str):
    pk = root / sid / "package"
    pk.mkdir(parents=True)
    with open(pk / f"{sid}_2_inventory.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Products", "Boundary", "KCB_score"])
        w.writerow(["BGC001", "NRPS", "Interior", "0"])
        w.writerow(["BGC002", "PKS", "Edge", "55"])
        w.writerow(["BGC003", "terpene", "", ""])
        w.writerow(["BGC004", "RiPP", "Weird", "nan"])
    with open(pk / f"{sid}_gene_by_gene_all_bgcs.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(GENE_HEADER)
        w.writerow(["BGC001", "g1", "", "T1", "T2_resistance_like"])
        w.writerow(["BGC002", "g2", "", "T1", "NULL_NO_SOURCE_DERIVED_RESISTANCE"])
        w.writerow(["BGC003", "g3", "", "T1", ""])
        w.writerow(["BGC004", "g4", "", "T1", "SOMETHING_NEW"])


def _sidecar(path: Path):
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def test_kcb_missing_and_nan_scores_are_their_own_group(tmp_path):
    _package(tmp_path, "EX")
    out = tmp_path / "figs"; out.mkdir()
    fig_kcb_novelty(str(tmp_path), ["EX"], str(out))
    rows = {r["kcb_tier"]: int(r["n_bgcs"]) for r in _sidecar(out / "fig6_kcb_novelty_data.csv")}
    assert rows["dark_lt1_candidate_novel"] == 1      # only the real 0
    assert rows["known_like_ge40"] == 1
    assert rows["missing_or_nonnumeric_score"] == 2   # blank and nan
    assert sum(rows.values()) == 4


def test_unknown_boundary_stays_in_the_denominator(tmp_path):
    _package(tmp_path, "EX")
    out = tmp_path / "figs"; out.mkdir()
    fig_boundary_profile(str(tmp_path), ["EX"], str(out))
    rows = {r["boundary"]: int(r["n_bgcs"]) for r in _sidecar(out / "fig8_boundary_profile_data.csv")}
    assert rows["Interior"] == 1 and rows["Edge"] == 1
    assert rows["unknown / missing"] == 2
    assert sum(rows.values()) == 4


def test_missing_or_unrecognized_tier_is_not_no_resistance_signal(tmp_path):
    _package(tmp_path, "EX")
    out = tmp_path / "figs"; out.mkdir()
    fig_resistance_map(str(tmp_path), ["EX"], str(out))
    rows = {r["resistance_tier"]: int(r["n_bgcs"]) for r in _sidecar(out / "fig10_resistance_map_data.csv")}
    assert rows["T2 resistance-like"] == 1
    assert rows["no resistance signal (scanned)"] == 1   # only the NULL tier
    assert rows["unknown / missing tier"] == 2           # blank and unrecognized

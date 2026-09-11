"""v9.7.410 — cohort-prevalence "promiscuous" gate: denominator, floor, boundary.

Closes COHORT_COMPARATIVE_LOGIC_AUDIT Finding 1 (active) and Finding 2 (latent twin).

Pre-.410 defect: ``PROMISCUOUS_DE_WEIGHT`` fired when a comparator appeared in
``>= 50%`` of cohort strains with no cohort-size floor, a ``>=`` boundary and
the focal strain counted in both numerator and denominator.  A comparator has a
coverage row only if it is in its own strain, so at N=2 every fraction is 0.5 or
1.0 and EVERY comparator (strain-unique ones included) was labeled promiscuous
(real RB68 package: 528/528 rows).

Post-.410 contract (both the evidence layer and the unwired scoring twin):
  * focal strain excluded from numerator and denominator;
  * denominator (other strains) must reach COHORT_PREVALENCE_MIN_OTHER_STRAINS
    (=3, i.e. N >= 4 with the focal strain) else NOT_ASSESSABLE_SMALL_COHORT;
  * strict ``>`` boundary;
  * deterministic; prevalence is a routing prior, never identity.

Standalone: python3 -m pytest tests/test_cohort_prevalence_denominator_v97410.py -q
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey import comparator_coverage_scoring as cc
from mamey import mibig_comparator_coverage as mcc


# ── fixtures ─────────────────────────────────────────────────────────────────
def _hit(bgc, q, acc, pid=80.0):
    return {
        "bgc_id": bgc,
        "query_gene": q,
        "subject_gene": f"{acc}_{q}",
        "mibig_accession": acc,
        "mibig_compound": "",
        "reference_type": "PKS",
        "pct_identity": pid,
        "blast_score": 300.0,
        "reference_rank": 1,
    }


def _inventory():
    return {"BGC_A": {"g1": mcc.ROLE_CORE, "g2": mcc.ROLE_CORE, "g3": mcc.ROLE_TAILORING}}


def _row(result, acc):
    for r in result["rows"]:
        if r["mibig_accession"] == acc:
            return r
    raise AssertionError(f"no row for {acc}")


def _write_runs(tmp_path: Path, cohort: dict[str, list[str]]) -> Path:
    """cohort = {strain_folder: [mibig accessions present in its per-gene CSV]}."""
    runs = tmp_path / "runs"
    for strain, accs in cohort.items():
        pkg = runs / strain / "package"
        pkg.mkdir(parents=True)
        with open(pkg / f"{strain}_3_mibig_per_gene.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(_hit("x", "g", "y").keys()))
            w.writeheader()
            for i, acc in enumerate(accs):
                w.writerow(_hit("BGC_A", f"g{i + 1}", acc))
    return runs


# ── Finding 1: evidence layer ────────────────────────────────────────────────
def test_n2_strain_unique_comparator_is_not_promiscuous(tmp_path):
    """FAIL-BEFORE / PASS-AFTER.  Two-strain cohort; BGC_UNIQ is only in the focal
    strain.  Pre-.410 it scored 1/2 >= 0.5 -> PROMISCUOUS_DE_WEIGHT (backwards)."""
    runs = _write_runs(tmp_path, {"FOCAL": ["BGC_UNIQ", "BGC_SHARED"], "OTHER": ["BGC_SHARED"]})
    prev = mcc.compute_cohort_prevalence(runs)
    assert prev["BGC_UNIQ"]["strains"] == 1 and prev["BGC_UNIQ"]["total"] == 2
    result = mcc.compute_comparator_coverage(
        [_hit("BGC_A", "g1", "BGC_UNIQ"), _hit("BGC_A", "g2", "BGC_SHARED")],
        locus_genes=_inventory(),
        cohort_prevalence=prev,
        focal_strain="FOCAL",
    )
    uniq = _row(result, "BGC_UNIQ")
    assert uniq["cohort_prevalence_flag"] != "PROMISCUOUS_DE_WEIGHT"
    assert uniq["cohort_prevalence_flag"] == "NOT_ASSESSABLE_SMALL_COHORT"
    # focal excluded: 0 of 1 other strains
    assert uniq["cohort_prevalence"] == "0/1"
    assert uniq["cohort_prevalence_basis"] == "other_strains_focal_excluded"
    # the shared comparator is ALSO not assessable at N=2 — no verdict either way
    assert _row(result, "BGC_SHARED")["cohort_prevalence_flag"] == "NOT_ASSESSABLE_SMALL_COHORT"
    assert result["summary"]["promiscuous_comparator_row_count"] == 0
    assert result["summary"]["prevalence_not_assessable_row_count"] == 2


def test_n2_no_row_is_ever_promiscuous_regardless_of_sharing(tmp_path):
    """The audit's real-data symptom (every row flagged) cannot recur at N=2."""
    accs = [f"BGC{i:04d}" for i in range(20)]
    runs = _write_runs(tmp_path, {"S1": accs, "S2": accs[:10]})
    prev = mcc.compute_cohort_prevalence(runs)
    result = mcc.compute_comparator_coverage(
        [_hit("BGC_A", f"g{i}", a) for i, a in enumerate(accs)],
        locus_genes=_inventory(),
        cohort_prevalence=prev,
        focal_strain="S1",
    )
    flags = {r["cohort_prevalence_flag"] for r in result["rows"]}
    assert flags == {"NOT_ASSESSABLE_SMALL_COHORT"}


def test_n4_genuinely_shared_comparator_still_flags(tmp_path):
    """A real cohort magnet (present in all 3 other strains) is still de-weighted;
    a strain-unique comparator in the same cohort is COHORT_TYPICAL (0/3)."""
    runs = _write_runs(
        tmp_path,
        {
            "FOCAL": ["BGC_MAGNET", "BGC_UNIQ", "BGC_HALF"],
            "O1": ["BGC_MAGNET", "BGC_HALF"],
            "O2": ["BGC_MAGNET"],
            "O3": ["BGC_MAGNET"],
        },
    )
    prev = mcc.compute_cohort_prevalence(runs)
    result = mcc.compute_comparator_coverage(
        [_hit("BGC_A", "g1", "BGC_MAGNET"), _hit("BGC_A", "g2", "BGC_UNIQ"), _hit("BGC_A", "g3", "BGC_HALF")],
        locus_genes=_inventory(),
        cohort_prevalence=prev,
        focal_strain="FOCAL",
    )
    magnet = _row(result, "BGC_MAGNET")
    assert magnet["cohort_prevalence"] == "3/3"
    assert magnet["cohort_prevalence_flag"] == "PROMISCUOUS_DE_WEIGHT"
    uniq = _row(result, "BGC_UNIQ")
    assert uniq["cohort_prevalence"] == "0/3"
    assert uniq["cohort_prevalence_flag"] == "COHORT_TYPICAL"
    # 1 of 3 others = 0.33 -> typical (and would be typical at exactly 0.5 too)
    assert _row(result, "BGC_HALF")["cohort_prevalence_flag"] == "COHORT_TYPICAL"
    assert result["summary"]["promiscuous_comparator_row_count"] == 1


def test_strict_boundary_exactly_half_is_not_promiscuous():
    """2 of 4 other strains = 0.50 exactly -> COHORT_TYPICAL (strict >)."""
    # cohort of 5; focal F + 2 others carry it -> 2 of 4 other strains
    cp = {"strains": 3, "total": 5, "fraction": 0.6, "strain_ids": ["F", "A", "B"]}
    out = mcc.assess_cohort_prevalence(cp, focal_strain="F")
    assert out["cohort_prevalence"] == "2/4"
    assert out["cohort_prevalence_flag"] == "COHORT_TYPICAL"
    # one more carrier -> 3/4 = 0.75 > 0.5 -> promiscuous
    cp2 = {"strains": 4, "total": 5, "fraction": 0.8, "strain_ids": ["F", "A", "B", "C"]}
    assert mcc.assess_cohort_prevalence(cp2, focal_strain="F")["cohort_prevalence_flag"] == "PROMISCUOUS_DE_WEIGHT"


def test_floor_is_configurable_and_n3_is_below_default_floor():
    cp = {"strains": 3, "total": 3, "fraction": 1.0, "strain_ids": ["F", "A", "B"]}
    # default floor (3 other strains): N=3 -> 2 others -> not assessable
    assert mcc.assess_cohort_prevalence(cp, focal_strain="F")["cohort_prevalence_flag"] == "NOT_ASSESSABLE_SMALL_COHORT"
    # an operator lowering the floor to 2 may assert it (2/2 > 0.5)
    assert (
        mcc.assess_cohort_prevalence(cp, focal_strain="F", min_other_strains=2)["cohort_prevalence_flag"]
        == "PROMISCUOUS_DE_WEIGHT"
    )


def test_focal_not_in_cohort_uses_all_scanned_strains_as_others():
    cp = {"strains": 3, "total": 4, "fraction": 0.75, "strain_ids": ["A", "B", "C"],
          "cohort_strain_ids": ["A", "B", "C", "D"]}
    out = mcc.assess_cohort_prevalence(cp, focal_strain="ELSEWHERE")
    assert out["cohort_prevalence"] == "3/4"
    assert out["cohort_prevalence_basis"] == "other_strains_focal_not_in_assessed_cohort"
    assert out["cohort_prevalence_flag"] == "PROMISCUOUS_DE_WEIGHT"


def test_legacy_record_without_strain_ids_still_gated():
    # legacy dict shape (no strain_ids): raw fraction, but floor + strict boundary apply
    assert mcc.assess_cohort_prevalence({"strains": 1, "total": 2, "fraction": 0.5})["cohort_prevalence_flag"] == "NOT_ASSESSABLE_SMALL_COHORT"
    assert mcc.assess_cohort_prevalence({"strains": 30, "total": 42, "fraction": 30 / 42})["cohort_prevalence_flag"] == "PROMISCUOUS_DE_WEIGHT"
    assert mcc.assess_cohort_prevalence(None)["cohort_prevalence_flag"] == "NOT_COMPUTED"


def test_run_for_package_uses_runs_folder_as_focal_and_emits_basis_column(tmp_path):
    runs = _write_runs(tmp_path, {"FOCAL": ["BGC_UNIQ", "BGC_SHARED"], "OTHER": ["BGC_SHARED"]})
    result = mcc.run_for_package(runs / "FOCAL" / "package", cohort_runs_dir=runs)
    with open(result["_written"]["csv"], newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert "cohort_prevalence_basis" in rows[0]
    by_acc = {r["mibig_accession"]: r for r in rows}
    assert by_acc["BGC_UNIQ"]["cohort_prevalence"] == "0/1"
    assert {r["cohort_prevalence_flag"] for r in rows} == {"NOT_ASSESSABLE_SMALL_COHORT"}


def test_compute_cohort_prevalence_is_deterministic(tmp_path):
    runs = _write_runs(tmp_path, {"B": ["X", "Y"], "A": ["Y"], "C": ["X"]})
    p1 = mcc.compute_cohort_prevalence(runs)
    p2 = mcc.compute_cohort_prevalence(runs)
    assert p1 == p2
    assert list(p1.keys()) == sorted(p1.keys())
    assert p1["X"]["strain_ids"] == ["B", "C"]


# ── Finding 2: latent scoring twin ───────────────────────────────────────────
def _cov(**kw):
    base = dict(coverage_all_locus=0.8, coverage_core=1.0, specificity="UNIQUE",
                collision=False, class_concordance="CONCORDANT")
    base.update(kw)
    return base


def test_scoring_twin_small_cohort_prevalence_earns_no_penalty():
    """FAIL-BEFORE / PASS-AFTER.  The pre-.410 twin returned -3 for prevalence 0.5
    with no cohort-size check.  A strain-unique comparator at N=2 (1/2 raw) must
    not be penalized; it keeps its bounded positive prior."""
    for cov in (
        _cov(cohort_prevalence=0.5),                      # bare fraction, unknown denominator
        _cov(cohort_prevalence=1.0),                      # even 1.0 without a denominator
        _cov(cohort_prevalence="1/2"),                    # evidence-layer K/N string, N=2
        _cov(cohort_prevalence=0.5, cohort_total_strains=1),
        _cov(cohort_prevalence="0/1", cohort_prevalence_flag="NOT_ASSESSABLE_SMALL_COHORT"),
    ):
        delta, _axis, note = cc.comparator_prior(cov)
        assert delta > 0.0, f"{cov} -> {delta} ({note})"
        assert delta != cc.NEG_PROMISCUOUS


def test_scoring_twin_strict_boundary():
    # exactly 0.5 over an assessable cohort is NOT promiscuous
    delta, _a, _n = cc.comparator_prior(_cov(cohort_prevalence=0.5, cohort_total_strains=4))
    assert delta > 0.0
    delta, _a, _n = cc.comparator_prior(_cov(cohort_prevalence="2/4"))
    assert delta > 0.0
    # strictly above it, over an assessable cohort, is
    delta, _a, _n = cc.comparator_prior(_cov(cohort_prevalence=0.75, cohort_total_strains=4))
    assert delta == cc.NEG_PROMISCUOUS
    delta, _a, _n = cc.comparator_prior(_cov(cohort_prevalence="3/4"))
    assert delta == cc.NEG_PROMISCUOUS


def test_scoring_twin_honours_evidence_layer_flag():
    # flag is authoritative over the number in either direction
    delta, _a, _n = cc.comparator_prior(_cov(cohort_prevalence="3/3", cohort_prevalence_flag="PROMISCUOUS_DE_WEIGHT"))
    assert delta == cc.NEG_PROMISCUOUS
    delta, _a, _n = cc.comparator_prior(_cov(cohort_prevalence="1/1", cohort_prevalence_flag="NOT_ASSESSABLE_SMALL_COHORT"))
    assert delta > 0.0
    delta, _a, _n = cc.comparator_prior(_cov(cohort_prevalence="", cohort_prevalence_flag="NOT_COMPUTED"))
    assert delta > 0.0


def test_scoring_twin_floor_matches_evidence_layer():
    assert cc.PREVALENCE_MIN_OTHER_STRAINS == mcc.COHORT_PREVALENCE_MIN_OTHER_STRAINS
    assert cc.PREVALENCE_PROMISCUOUS == mcc.COHORT_PREVALENCE_PROMISCUOUS_FRACTION


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))

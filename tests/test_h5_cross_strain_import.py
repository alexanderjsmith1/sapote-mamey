"""test_cohort_figures_cross_strain_import.py — H5 regression (v9.7.352).

`mamey/cohort_figures.py` calls `build_cross_strain_figures(...)` at its cohort-figure
entry, but the symbol lived in `cross_strain_figures.py` and was never imported. The call
sat inside a broad try/except that swallowed the resulting NameError and returned
{"status": "SKIPPED_ERROR"}, so auto cross-strain figures were silently never produced for
real >=2-strain batches. Existing tests only exercised the 0/1-strain early return, so the
bug escaped coverage. This pins the import binding.
"""
import mamey.cohort_figures as cohort_figures
from mamey.cross_strain_figures import build_cross_strain_figures as canonical


def test_cross_strain_builder_is_bound_in_cohort_module():
    # The exact symbol the cohort-figure entry calls must be importable in this namespace.
    assert hasattr(cohort_figures, "build_cross_strain_figures"), (
        "cohort_figures.build_cross_strain_figures is unbound — the missing import "
        "regressed (H5): >=2-strain cohort figures would silently SKIP with a NameError."
    )


def test_bound_symbol_is_the_canonical_one():
    assert cohort_figures.build_cross_strain_figures is canonical

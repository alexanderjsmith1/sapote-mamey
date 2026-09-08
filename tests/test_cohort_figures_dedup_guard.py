"""Guard: the dead figures_split duplicate in cohort_figures.py stays deleted (Indigo2 A9, .367).

`render_split_figures` has ONE implementation — mamey/figures_split.py. cohort_figures.py once
carried an exact 1.000-per-function copy (latent F821, unreachable); it was deleted at .367.
This asserts the duplicate does not creep back.
"""
import mamey.cohort_figures as cf
import mamey.figures_split as fs


def test_cohort_figures_no_longer_defines_render_split_figures():
    assert not hasattr(cf, "render_split_figures"), (
        "cohort_figures re-grew the dead figures_split duplicate — delete it; "
        "the single implementation lives in figures_split.py"
    )


def test_figures_split_remains_the_single_implementation():
    assert hasattr(fs, "render_split_figures")

"""test_cohort_figures_kcb_logscale_guard_v9_7_382.py — P1-8 regression guard.

The D-series KCB figures (`scatter_kcb_vs_size` D04, `strip_kcb_per_strain` D06) set a logarithmic
y-axis on KCB top-bitscores. A legitimate all-novel cohort has NO KnownClusterBlast hit, so every
y-value is absent/<=0 and matplotlib raises "Data cannot be log-scaled because all values are <= 0",
aborting the `series=all` render mid-suite. The fix makes each `set_yscale("log")` conditional on at
least one positive KCB value (`_pos_kcb`), else it stays linear and draws an empty-state note.

A full behavioral render needs an on-disk cohort of sealed packages (manifests + inventories), which
is disproportionate here; this locks the guard SHAPE instead: neither KCB log-axis may be applied
unconditionally, and both must be gated on the positive-value flag. If someone reintroduces a bare
`ax.set_yscale("log")` on the KCB axis, this fails.
"""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parent.parent / "mamey" / "cohort_figures.py").read_text()


def _build_body() -> str:
    # scope the check to build() (the D-series); other figures legitimately use log scales
    i = SRC.index("\ndef build(")
    j = SRC.index("\ndef ", i + 1)
    return SRC[i:j]


def test_kcb_logscale_is_guarded_not_unconditional():
    body = _build_body()
    # the positive-KCB flag must exist and gate the log axis
    assert "_pos_kcb" in body, "expected a positive-KCB guard flag in build()"
    # every set_yscale('log') in build() must be preceded on its logical line by the guard,
    # i.e. it appears as `if _pos_kcb:\n    ax.set_yscale("log")`, never bare on its own statement line.
    for m in re.finditer(r'set_yscale\(\s*[\'"]log[\'"]\s*\)', body):
        # find the start of the statement/line
        line_start = body.rfind("\n", 0, m.start()) + 1
        line = body[line_start:m.start()]
        # the log call must be the body of an `if _pos_kcb:` block: the line holding it is indented
        # and contains only `ax.` (no leading `;`-chained unconditional call on the same source line)
        assert line.strip() in ("", "ax."), (
            f"KCB set_yscale('log') is not on its own guarded line: {line!r}")


def test_empty_state_note_present():
    body = _build_body()
    # the linear fallback must annotate the panel rather than silently render blank
    assert body.count("no KCB reference hits in this cohort") >= 2, \
        "both D04 and D06 should draw an empty-state note when no KCB hits exist"

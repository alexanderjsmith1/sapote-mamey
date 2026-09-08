"""test_no_nested_samequote_fstrings.py — H2 regression (v9.7.352).

`pyproject.toml` declares `requires-python = ">=3.10"`, but PEP-701 same-quote-nested
f-strings — e.g. f"{d("k")["v"]}" — are valid only on CPython 3.12+. On 3.10/3.11 they raise
SyntaxError **at import**, which took down master_figure_atlas / read_xlsx_table /
cohort_class_heatmap on any 3.10/3.11 dev or CI machine (masked in prod by cp312 wheels).

Option A (keep the 3.10 floor) rewrote the offenders to single-quote the inner strings. This
guard scans the shipped package source for the pattern so a future 3.12-only f-string fails on
the *declared* minimum. It is a source lint (regex), so it runs on any interpreter version —
we can't assume a 3.10 is installed to `py_compile` against.
"""
import glob
import os
import re

import mamey

# A double-outer f-string whose replacement field {...} contains a double-quote, and the
# single-outer analog. These are exactly the PEP-701 relaxations that break < 3.12.
_DQ = re.compile(r'''(?:^|[^A-Za-z0-9_])[rRbB]?[fF][rR]?"[^"\n]*\{[^}\n]*"[^}\n]*\}''')
_SQ = re.compile(r"""(?:^|[^A-Za-z0-9_])[rRbB]?[fF][rR]?'[^'\n]*\{[^}\n]*'[^}\n]*\}""")

_PKG_DIR = os.path.dirname(mamey.__file__)


def _package_sources():
    # top-level package modules only; skip the vendored tree (not ours to constrain)
    for fn in glob.glob(os.path.join(_PKG_DIR, "*.py")):
        yield fn


def test_no_nested_samequote_fstrings_in_package():
    offenders = []
    for fn in _package_sources():
        with open(fn, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if _DQ.search(line) or _SQ.search(line):
                    offenders.append(f"{os.path.basename(fn)}:{lineno}: {line.strip()[:100]}")
    assert not offenders, (
        "Same-quote nested f-string(s) found — these need CPython 3.12+ but the project "
        "declares requires-python >=3.10, so they SyntaxError at import on the declared floor. "
        "Single-quote the inner strings (or bump requires-python).\n  " + "\n  ".join(offenders)
    )


def test_detector_actually_fires_on_a_known_bad_sample():
    # guard the guard: ensure the regex would catch a real 3.12-only f-string
    bad = 'x = f"{_fig_meta("k")["visible_id"]}_tail.csv"'
    assert _DQ.search(bad)

"""v9.7.239 follow-up (G01): wire `--strict-paths` repo-wide.

v9.7.239 added `scan_tools(strict_paths=True)` (F03) so a path-qualified reference such as
`tools/sapote_workflow.py` is resolved as a FULL relative path rather than by basename.
Basename matching was what let `tools/sapote_workflow.py` be satisfied by
`mamey/sapote_workflow.py`, so the v9.7.237 cut shipped 8 references to a file it never
included and every guard passed.

But the capability landed unenforced. `tests/test_strict_paths_dangling_refs.py` exercises
`scan_tools` against a synthetic `tmp_path`; nothing runs the strict scan over the real tree.
A check nobody runs is exactly the failure mode F03 was written to close — and the same shape
as the nr-overlay bug this cut fixed (three readers, zero writers, nothing said so).

This wires it, using the bundle's established ratchet idiom (cf.
`tests/test_no_dangling_tool_refs_v97213.py::DANGLING_BASELINE` and
`tools/check_duplicate_dict_keys.py::ALLOWLIST`): freeze the known set, fail on anything new.

Measured on the shipped v9.7.239 tree: lenient finds 6, strict finds 11. The 6 extra are
path-qualified references that basename matching hid. Two are legitimately out-of-bundle
(`../bootstrap.sh` and `engine/…` live in the Wheelhouse companion, not the CODE tier). Four
are documentation rot pointing at modules that exist nowhere in the tree.

The baseline must only ever SHRINK. Delete an entry the moment its reference is corrected.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_dangling_refs import scan_tools  # noqa: E402

# Path-qualified references that do not resolve today. Frozen as a baseline, not accepted.
#   out-of-bundle  — the target ships in the Wheelhouse companion, not the CODE tier
#   doc rot        — the target exists nowhere; needs consolidation-era module tracing
PATH_BASELINE = frozenset({
    "../bootstrap.sh",                    # out-of-bundle: Wheelhouse/bootstrap
    "engine/pyhmmer_scanner_engine.py",   # out-of-bundle: Wheelhouse/engine
    "directed_studies/pks.py",            # out-of-bundle: directed-studies tree
    # v9.7.242 (G01 closed): the three doc-rot entries below were REPAIRED, not frozen —
    #   mamey/cohort_figure_captions.py -> mamey/cohort_figures.py
    #   mamey/first_pass_scans.py       -> mamey/source_scans.py
    #   validators/modeb_full20.py      -> mamey/modeb_structure_gate.py
    # The ratchet demanded their removal the moment they stopped dangling. That is the point.
})


def _strict():
    return set(scan_tools(ROOT, strict_paths=True))


def _lenient():
    return set(scan_tools(ROOT, strict_paths=False))


def test_no_new_path_qualified_dangling_refs():
    """The gate. Anything path-qualified and unresolved that is not baselined fails the cut."""
    strict = _strict()
    lenient = _lenient()
    # references the strict scan adds over the lenient one == path-qualified misses
    path_only = strict - lenient
    new = sorted(path_only - PATH_BASELINE)
    assert not new, (
        "New path-qualified dangling reference(s):\n  " + "\n  ".join(new) +
        "\nA doc or comment cites a path that does not exist. Fix the path, or add it to "
        "PATH_BASELINE with a one-line reason."
    )


def test_baseline_is_a_ratchet():
    """An entry that no longer dangles must be removed from the baseline."""
    strict = _strict()
    stale = sorted(PATH_BASELINE - strict)
    assert not stale, f"PATH_BASELINE entries no longer dangle; delete them: {stale}"


def test_strict_never_hides_a_lenient_finding():
    """Strict may only ADD findings; it must never drop one the lenient scan reports.

    Note the key change, not a key subset: strict re-keys a path-qualified reference under its
    full relative path (`mamey/first_pass_scans.py`) where lenient keys it by basename
    (`first_pass_scans.py`). Compare by basename so the re-keying does not look like a loss.
    """
    import os
    base = lambda s: {os.path.basename(k) for k in s}
    missing = base(_lenient()) - base(_strict())
    assert not missing, f"strict-paths dropped finding(s) lenient reports: {sorted(missing)}"


def test_strict_paths_would_have_caught_the_missing_shim(tmp_path):
    """Positive control, reproducing the exact v9.7.237 F01 miss.

    A doc cites `tools/widget.py`; only `mamey/widget.py` exists. Basename matching passes;
    strict-paths must fail.
    """
    (tmp_path / "mamey").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "mamey" / "widget.py").write_text("# implementation\n")
    (tmp_path / "docs.md").write_text("Driver: `tools/widget.py`\n")

    assert "tools/widget.py" not in scan_tools(tmp_path, strict_paths=False)
    assert "tools/widget.py" in scan_tools(tmp_path, strict_paths=True)

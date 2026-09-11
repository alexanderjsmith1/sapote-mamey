"""v9.7.415 — `majority-read` must not silently overwrite a canonical dated deliverable.

The .413 canonical-overwrite guard was wired into two of three sibling deliverable tools
(surface-leads, modeb-compile). `whole_bgc_majority_read.py` was missed even though the guard's own
docstring names `whole_bgc_majority_read_` first in its list of one-off-batch folder prefixes, and
even though its default outdir is ROOT/strain_data/whole_bgc_majority_read_2026-08-05 — strain_data
being the SYMLINK to the canonical home, and that folder name matching DATED_DIR_RE exactly.

Filesystem-safety only: no score, no biology, no claim about any locus. Judgment deferred.
"""
from pathlib import Path
import ast
import pytest

from mamey.canonical_write_guard import guard_canonical_write, CanonicalOverwriteRefused

TOOL = Path(__file__).resolve().parents[1] / "deliverable_tools" / "whole_bgc_majority_read.py"


def _src():
    return TOOL.read_text(encoding="utf-8")


def test_the_tool_imports_the_guard():
    assert "from mamey.canonical_write_guard import guard_canonical_write" in _src()


def test_the_tool_offers_the_force_escape_hatch():
    """Without --force the guard is a one-way door — the same reason .413 gave for its siblings."""
    s = _src()
    assert '"--force"' in s and '"--in-place"' in s


def test_both_write_sites_are_guarded():
    """The cohort CSV and the annotated-convergence sibling both write into canonical folders."""
    s = _src()
    assert s.count("guard_canonical_write(") >= 2, "expected the cohort CSV and annotated sibling guarded"


def test_annotate_convergence_threads_force():
    """A guard the caller cannot release is a one-way door; force must reach the inner writer."""
    tree = ast.parse(_src())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "annotate_convergence")
    assert "force" in [a.arg for a in fn.args.args], "annotate_convergence must accept force"


def test_guard_refuses_the_real_default_path_shape(tmp_path):
    """End-to-end on the exact shape the tool writes when --out is omitted."""
    d = tmp_path / "strain_data" / "whole_bgc_majority_read_2026-08-05"
    d.mkdir(parents=True)
    f = d / "whole_bgc_majority_read_cohort.csv"
    f.write_text("EXISTING,DELIVERABLE\n", encoding="utf-8")
    with pytest.raises(CanonicalOverwriteRefused):
        guard_canonical_write(f, force=False)
    guard_canonical_write(f, force=True)          # the escape hatch still works
    assert f.read_text(encoding="utf-8") == "EXISTING,DELIVERABLE\n"   # guard never writes


def test_cli_declares_and_forwards_force_for_majority_read():
    cli = (Path(__file__).resolve().parents[1] / "mamey" / "cli.py").read_text(encoding="utf-8")
    assert 'mr.add_argument("--force", "--in-place", dest="force"' in cli
    seg = cli.split('if args.command == "majority-read":', 1)[1].split('elif args.command ==', 1)[0]
    assert '"--force"' in seg, "the dispatcher must forward --force to the tool"

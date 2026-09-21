"""An unusable `report_receipt` must raise the module's own typed error.

`build_activity_decision_trees` validates the locator with
``if not locator or locator.is_absolute() or ".." in locator.parts``, where
``locator`` is already a ``Path``.  ``Path("")`` normalises to ``Path(".")``,
which is truthy, so an empty field clears all three guards, resolves to the
receipt root itself, clears the escape check (it *equals* the root) and then
reaches ``read_text()`` on a directory.

The sibling module `mamey/thesis_handoff.py::_safe` already implements the
correct form: it tests the raw string for emptiness and additionally requires
``resolved.is_file()``.  These tests hold the two implementations to the same
contract, so a bad lead table fails as a governed refusal rather than an
unhandled OSError.
"""
from __future__ import annotations

import csv
import json

import pytest

from mamey.activity_decision_tree import (
    ActivityDecisionTreeError,
    build_activity_decision_trees,
)

IDENTITY = {
    "strain": "SYNTHETIC-001",
    "full_node_or_contig": "contig_demo_0001_complete",
    "region": "region001",
    "bgc_alias": "BGC007",
}


def setup(tmp_path, **changes):
    root = tmp_path / "reports"
    (root / "one").mkdir(parents=True)
    (root / "one/REPORT_RECEIPT.json").write_text(json.dumps({"identity": IDENTITY}))
    row = dict(
        IDENTITY,
        report_receipt="one/REPORT_RECEIPT.json",
        hypothesis="pigment-family chemistry",
        target_genes="gene_001",
        claim_ceiling="Class-level hypothesis only",
    )
    row.update(changes)
    leads = tmp_path / "leads.tsv"
    with leads.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=row, delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    return leads, root


@pytest.mark.parametrize(
    "locator, why",
    [
        ("", "empty field normalises to Path('.') and reads the root directory"),
        ("   ", "whitespace-only field strips to empty"),
        (".", "explicit current-directory locator names the root itself"),
        ("one", "locator names a directory, not a receipt file"),
        ("one/MISSING_RECEIPT.json", "locator names a file that does not exist"),
    ],
)
def test_unusable_locator_raises_the_typed_error(tmp_path, locator, why):
    leads, root = setup(tmp_path, report_receipt=locator)
    with pytest.raises(ActivityDecisionTreeError):
        build_activity_decision_trees(leads, root, tmp_path / "out")
    assert not (tmp_path / "out").exists(), f"output written despite refusal: {why}"


def test_previously_covered_refusals_still_hold(tmp_path):
    """Guard the guard: the existing escape check must not regress."""
    for locator in ("../escape.json", "/etc/passwd"):
        leads, root = setup(tmp_path / locator.replace("/", "_"), report_receipt=locator)
        with pytest.raises(ActivityDecisionTreeError):
            build_activity_decision_trees(
                leads, root, tmp_path / locator.replace("/", "_") / "out"
            )


def test_valid_locator_still_builds(tmp_path):
    leads, root = setup(tmp_path)
    receipt = build_activity_decision_trees(leads, root, tmp_path / "out")
    assert receipt["lead_count"] == 1
    assert (tmp_path / "out/ACTIVITY_DECISION_TREES.md").is_file()

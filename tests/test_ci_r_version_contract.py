"""Offline CI configuration contract, not an R/Linux installation or render test."""
from copy import deepcopy
from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def minimum_r(support_text):
    section = support_text.split("## R figure stack", 1)[1].split("\n## ", 1)[0]
    match = re.search(r"\bR\s*>=\s*(\d+)\.(\d+)(?:\.(\d+))?", section)
    assert match, "R support must have an explicit minimum in PREREQUISITES"
    return tuple(int(value or 0) for value in match.groups())


def validate_r_selection(workflow, support_text):
    steps = workflow["jobs"]["test"]["steps"]
    setup = [step for step in steps if str(step.get("uses", "")).startswith("r-lib/actions/setup-r@")]
    assert len(setup) == 1, "CI test job must select R once"
    version = setup[0].get("with", {}).get("r-version")
    assert isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version), "CI R selection must be an exact patch version"
    parsed = tuple(map(int, version.split(".")))
    assert parsed >= minimum_r(support_text), "CI R pin is below the documented support minimum"
    # A present-but-disabled setup step must not bypass this interpreter selection.
    assert setup[0].get("with", {}).get("install-r", True) not in (False, "false"), "CI must install its selected R"
    return version


def inputs():
    return (yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")),
            (ROOT / "docs/PREREQUISITES.md").read_text(encoding="utf-8"))


def replace_version(workflow, value):
    changed = deepcopy(workflow)
    for step in changed["jobs"]["test"]["steps"]:
        if str(step.get("uses", "")).startswith("r-lib/actions/setup-r@"):
            step.setdefault("with", {})["r-version"] = value
    return changed


def test_ci_r_pin_is_exact_and_within_declared_support():
    workflow, support = inputs()
    validate_r_selection(workflow, support)


@pytest.mark.parametrize("selector", ["release", "latest", "devel", "oldrel", "4.4.x", "4.5", "${{ matrix.r-version }}", None, 4.5])
def test_floating_or_nonliteral_r_selections_are_rejected(selector):
    workflow, support = inputs()
    with pytest.raises(AssertionError, match="exact patch version"):
        validate_r_selection(replace_version(workflow, selector), support)


def test_pin_below_declared_minimum_is_rejected():
    workflow, support = inputs()
    major, minor, patch = minimum_r(support)
    below = f"{major}.{minor - 1}.99" if minor else f"{major - 1}.99.99"
    with pytest.raises(AssertionError, match="below the documented support minimum"):
        validate_r_selection(replace_version(workflow, below), support)


@pytest.mark.parametrize("version", ["4.3.0", "4.5.3", "4.6.1"])
def test_exact_versions_satisfy_synthetic_declared_support(version):
    # This checks version admission only, not runtime/package compatibility.
    workflow, _ = inputs()
    declared = "## R figure stack\nUse R >= 4.3 for the R figure workflows.\n"
    assert validate_r_selection(replace_version(workflow, version), declared) == version


def test_future_minimum_increase_requires_ci_pin_review():
    workflow, _ = inputs()
    declared = "## R figure stack\nUse R >= 4.6 for the R figure workflows.\n"
    with pytest.raises(AssertionError, match="below the documented support minimum"):
        validate_r_selection(replace_version(workflow, "4.5.3"), declared)


def test_disabled_r_install_cannot_silently_select_runner_default():
    workflow, support = inputs()
    changed = replace_version(workflow, "4.5.3")
    step = next(step for step in changed["jobs"]["test"]["steps"] if str(step.get("uses", "")).startswith("r-lib/actions/setup-r@"))
    step["with"]["install-r"] = False
    with pytest.raises(AssertionError, match="must install its selected R"):
        validate_r_selection(changed, support)

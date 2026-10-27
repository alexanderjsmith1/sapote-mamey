"""The project registry refuses values it used to coerce silently.

target_ids given as a mapping became its keys; a non-string target became str(item);
audience_rank and replicate_count went through int(), so 1.9 became 1 and True became 1.
"""
import importlib.util
import pathlib

import pytest

from mamey.project_registry import ProjectRegistry, ProjectRegistryError

_spec = importlib.util.spec_from_file_location(
    "_registry_fixture_458", pathlib.Path(__file__).resolve().parent / "test_project_registry.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


@pytest.mark.parametrize("targets", [{"TARGET-A": 1}, ["TARGET-A", 7]])
def test_non_string_targets_are_refused(targets):
    p = _fx.payload()
    p["assays"][0]["target_ids"] = targets
    with pytest.raises(ProjectRegistryError, match="target_ids"):
        ProjectRegistry.from_dict(p)


@pytest.mark.parametrize("value", [1.9, True, "3.5"])
def test_replicate_count_is_not_truncated(value):
    p = _fx.payload()
    p["assays"][0]["replicate_count"] = value
    with pytest.raises(ProjectRegistryError, match="replicate_count"):
        ProjectRegistry.from_dict(p)


@pytest.mark.parametrize("value", [49.5, False])
def test_audience_rank_is_not_truncated(value):
    p = _fx.payload()
    p["privacy_tiers"][1]["audience_rank"] = value
    with pytest.raises(ProjectRegistryError, match="audience_rank"):
        ProjectRegistry.from_dict(p)


def test_exact_integers_still_load():
    p = _fx.payload()
    p["assays"][0]["replicate_count"] = "3"
    p["privacy_tiers"][1]["audience_rank"] = 50.0
    ProjectRegistry.from_dict(p)

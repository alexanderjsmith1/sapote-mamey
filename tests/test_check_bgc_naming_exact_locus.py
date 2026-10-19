import importlib.util
from pathlib import Path

if __package__ in (None, ""):
    from _synthetic_identity_fixture import synthetic_namespace_id
else:
    from tests._synthetic_identity_fixture import synthetic_namespace_id
_FORMAT_CASE_1 = synthetic_namespace_id('AS', width=3, case_index=802)


def _module():
    path = Path(__file__).parents[1] / "tools" / "check_bgc_naming.py"
    spec = importlib.util.spec_from_file_location("check_bgc_naming", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_full_exact_locus_filename_passes():
    mod = _module()
    name = (f"{_FORMAT_CASE_1}__NODE_26_length_91518_cov_109.342910__region001__"
            "BGC015__ModeB_SUCCESSOR_CANDIDATE__2026-08-19.md")
    assert not mod._basename_violates(name)


def test_region_alone_is_not_a_node_anchor():
    assert _module()._basename_violates(f"{_FORMAT_CASE_1}__region001__BGC015__card.md")


def test_strain_is_required_in_locus_basename():
    name = "NODE_26_length_91518_cov_109.342910__region001__BGC015__card.md"
    assert _module()._basename_violates(name)


def test_short_node_is_rejected():
    assert _module()._basename_violates(f"{_FORMAT_CASE_1}__NODE_26__region001__BGC015__card.md")

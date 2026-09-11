"""test_intake_harness_taxonomy_map.py — new in this cut.

`tools/intake_harness.py` had no way to supply per-strain genus/host when the
input GBK's ORGANISM line is empty or a placeholder (e.g. "." for a raw SPAdes
assembly, common for the AS-series draft genomes) — every strain manifest
shipped with taxonomy derived only from the GBK, with no CLI-level override,
even when the real genus/host is on record elsewhere (institutional strain
list, prior session). --taxonomy-map closes that gap: an optional JSON file
of {strain_name: taxonomy_string} overrides, applied per-strain before both
the `mamey run --taxonomy` invocation and the registry "organism" column.
Unmapped strains are unaffected (prior auto-derived behavior unchanged).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest


def _load_intake_harness():
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    path = repo_root / "tools" / "intake_harness.py"
    spec = importlib.util.spec_from_file_location("intake_harness_test_load_taxmap", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_load_taxonomy_map_returns_empty_dict_for_none():
    ih = _load_intake_harness()
    assert ih.load_taxonomy_map(None) == {}


def test_load_taxonomy_map_reads_valid_json(tmp_path):
    ih = _load_intake_harness()
    p = tmp_path / "taxmap.json"
    p.write_text(json.dumps({"AS-677": "Saccharopolyspora sp.", "AS-678": "Nocardia sp."}))
    result = ih.load_taxonomy_map(str(p))
    assert result == {"AS-677": "Saccharopolyspora sp.", "AS-678": "Nocardia sp."}


def test_load_taxonomy_map_rejects_non_object_json(tmp_path):
    ih = _load_intake_harness()
    p = tmp_path / "taxmap.json"
    p.write_text(json.dumps(["AS-677", "Saccharopolyspora sp."]))  # a list, not an object
    with pytest.raises(SystemExit):
        ih.load_taxonomy_map(str(p))


def test_load_taxonomy_map_rejects_non_string_values(tmp_path):
    ih = _load_intake_harness()
    p = tmp_path / "taxmap.json"
    p.write_text(json.dumps({"AS-677": 12345}))  # value must be a string
    with pytest.raises(SystemExit):
        ih.load_taxonomy_map(str(p))


def test_load_taxonomy_map_rejects_malformed_json(tmp_path):
    ih = _load_intake_harness()
    p = tmp_path / "taxmap.json"
    p.write_text("{not valid json")
    with pytest.raises(json.JSONDecodeError):
        ih.load_taxonomy_map(str(p))


def test_taxonomy_map_argument_registered_in_parser():
    """Source-level guard: --taxonomy-map must stay wired into the real CLI parser."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    src = (repo_root / "tools" / "intake_harness.py").read_text(encoding="utf-8")
    assert '"--taxonomy-map"' in src
    assert "load_taxonomy_map(a.taxonomy_map)" in src


def test_taxonomy_map_override_applied_before_needs_antismash_branch():
    """Source-level guard: the `if name in taxonomy_map` override must appear before the
    NEEDS_ANTISMASH branch, so the override reaches BOTH the skip-path registry row and the
    real `mamey run --taxonomy` invocation, not just one of the two call sites."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    src = (repo_root / "tools" / "intake_harness.py").read_text(encoding="utf-8")
    override_idx = src.index("if name in taxonomy_map:")
    needs_as_idx = src.index('kind == "NEEDS_ANTISMASH"')
    assert override_idx < needs_as_idx, (
        "taxonomy_map override moved after the NEEDS_ANTISMASH branch; "
        "it would no longer apply to strains that need antiSMASH run first"
    )

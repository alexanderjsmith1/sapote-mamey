"""v9.7.440 (session 9c5f37d0): load_taxonomy_map must reject placeholder / empty values.

A --taxonomy-map value of "sp." (or "", ".", "spp.") passes the flat-{str:str} shape check but is
exactly what the engine's is_placeholder_taxonomy guard rejects at run time -- and because "sp." is
truthy it also slips past the `org or "not verified"` fallback. The map route then fails every
affected strain with an unexplained rc=1. This test pins the value guard.

Fails on the .439 tool (values unchecked); passes with taxonomy_map_value_guard.diff applied.
Drop into tests/.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_BUNDLE = Path(__file__).resolve().parents[1]           # tests/ -> bundle root
_TOOL = _BUNDLE / "tools" / "intake_harness.py"


def _mod():
    for p in (str(_BUNDLE), str(_BUNDLE / "tools")):
        if p not in sys.path:
            sys.path.insert(0, p)
    spec = importlib.util.spec_from_file_location("intake_harness_taxmaptest", _TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _write(tmp_path, obj):
    p = tmp_path / "map.json"
    p.write_text(json.dumps(obj))
    return str(p)


@pytest.mark.parametrize("bad_value", ["sp.", "spp.", ".", "", "   "])
def test_placeholder_or_empty_value_is_rejected(tmp_path, bad_value):
    m = _mod()
    path = _write(tmp_path, {"AS-678": bad_value})
    with pytest.raises(SystemExit):
        m.load_taxonomy_map(path)


@pytest.mark.parametrize("ok_value", ["Nocardia sp.", "not verified", "Streptomyces", "Micromonospora sp."])
def test_real_taxonomy_and_explicit_uncertainty_pass(tmp_path, ok_value):
    m = _mod()
    path = _write(tmp_path, {"AS-678": ok_value})
    assert m.load_taxonomy_map(path) == {"AS-678": ok_value}


def test_one_bad_entry_fails_the_whole_map(tmp_path):
    # a good entry does not excuse a placeholder sibling; the map is all-or-nothing
    m = _mod()
    path = _write(tmp_path, {"AS-1": "Nocardia sp.", "AS-2": "sp."})
    with pytest.raises(SystemExit):
        m.load_taxonomy_map(path)

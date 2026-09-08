"""Test the generated marker catalog tracks the source_scans regex backend (W9).

If someone edits a regex table in mamey/source_scans.py and forgets to regenerate the
catalog, this fails — which is the whole point: the doc cannot drift from the backend.
"""
import pathlib
import importlib.util

import mamey.source_scans as ss

_TOOL = pathlib.Path(__file__).resolve().parent.parent / "tools" / "gen_marker_catalog.py"
_spec = importlib.util.spec_from_file_location("gen_marker_catalog", _TOOL)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_collect_is_deterministic():
    assert gen.collect()["sha256"] == gen.collect()["sha256"]


def test_catalog_covers_every_live_pattern_table():
    payload = gen.collect()
    live = [n for n in dir(ss)
            if n.isupper() and (n.endswith("_PATTERNS") or n.endswith("_MOTIFS") or n.endswith("_VETOES"))
            and isinstance(getattr(ss, n), dict) and getattr(ss, n)
            and all(isinstance(v, (list, tuple)) for v in getattr(ss, n).values())]
    assert set(payload["tables"]) == set(live), "catalog tables != live source_scans tables"
    # family counts match the live dicts exactly
    for name in live:
        assert len(payload["tables"][name]) == len(getattr(ss, name))


def test_committed_catalog_is_not_stale():
    """If the committed JSON exists, it must match the current regex (regenerate before commit)."""
    import json
    p = gen.JSON_OUT
    if not p.exists():
        return  # nothing committed yet; generation test above covers correctness
    committed = json.loads(p.read_text(encoding="utf-8"))
    assert committed.get("sha256") == gen.collect()["sha256"], \
        "docs/MARKER_CATALOG.generated.json is stale — run tools/gen_marker_catalog.py"

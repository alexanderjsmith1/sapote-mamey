"""Regression test — v97395 tick 20: check_registry_ids_unique.py silently PASSES an unparsed
empty CSV, the same failure shape its own v9.7.374 fix was written to eliminate.

That fix made a missing file / unsupported extension a loud error instead of a silent `return []`
that main() reported as "registry IDs unique (0 IDs)" / exit 0. A completely empty (0-byte) `.csv`
file -- no header row at all, so the 'id'-column check (`rows and "id" not in rows[0]`) never even
runs because `rows` is empty regardless of whether a header existed -- reproduces the exact same
silent-pass shape the v9.7.374 fix targeted, one edge case later.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import check_registry_ids_unique as m


def test_completely_empty_csv_is_an_error_not_a_silent_pass_v97395(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    try:
        ids = m._ids(p)
    except Exception:
        return  # correct: an unparsed file must not report a clean 0-ID pass
    raise AssertionError(
        f"_ids() silently returned {ids!r} for a completely empty CSV instead of raising"
    )


def test_header_only_csv_with_id_column_is_a_legitimate_empty_registry_v97395(tmp_path):
    """No regression: a CSV with a real header (including 'id') and zero data rows is a
    genuinely empty registry, not an unparsed file -- must still PASS with 0 IDs."""
    p = tmp_path / "header_only.csv"
    p.write_text("id,name\n", encoding="utf-8")
    assert m._ids(p) == []


def test_header_only_csv_without_id_column_still_raises_v97395(tmp_path):
    """A header lacking 'id' with zero data rows must raise, same as the existing non-empty
    case -- the schema check should not depend on there being at least one data row."""
    p = tmp_path / "no_id_col.csv"
    p.write_text("name,value\n", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError):
        m._ids(p)

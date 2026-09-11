"""Label regression_418 — the ggtree producer's failure mode is silent, and its --help describes behaviour
that was removed in the same cut.

At v9.7.417 this tool was (correctly) genericised: it must not know any workspace filename. But
`_find_host_table` became `return path or ""` while `--host-table`'s help still said "auto-located",
and a bare invocation now exits 0 and writes a well-formed annotation whose every query label is a
bare id — indistinguishable downstream from a cohort that genuinely has no metadata.

Reproduced 2026-09-08 on the sealed .417 engine: all 5 Kribbella queries rendered as bare AS-ids.
"""
import importlib.util
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mod():
    p = os.path.join(ROOT, "tools", "build_placement_ggtree_inputs.py")
    spec = importlib.util.spec_from_file_location("bpgi418", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_help_does_not_promise_auto_location_that_was_removed():
    """`_find_host_table` returns its argument unchanged; the help must not claim otherwise."""
    m = _mod()
    assert m._find_host_table("") == ""
    assert m._find_host_table("/x/y.tsv") == "/x/y.tsv"
    src = open(os.path.join(ROOT, "tools", "build_placement_ggtree_inputs.py"), encoding="utf-8").read()
    i = src.index('"--host-table"')
    help_text = src[i:i + 600]
    assert "auto-located" not in help_text, "help still promises auto-location"
    assert "BARE" in help_text or "bare" in help_text, "help must state the silent failure mode"


def test_stale_reference_to_the_removed_AUX_TABLES_constant_is_gone():
    m = _mod()
    assert not hasattr(m, "AUX_TABLES"), "constant is genuinely absent"
    src = open(os.path.join(ROOT, "tools", "build_placement_ggtree_inputs.py"), encoding="utf-8").read()
    body = src[src.index("def main("):] if "def main(" in src else src
    assert "see AUX_TABLES" not in body, "comment still points at a constant that does not exist"


def test_aux_loader_still_refuses_a_conflicting_value():
    """Guard the guard: the .417 conflict refusal must survive this card."""
    import pytest
    m = _mod()
    import tempfile
    a = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, newline="")
    a.write("strain\thost\tregion\taccession\nAS-1\tmoss\tOntario\tPX1\n"); a.close()
    b = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, newline="")
    b.write("strain\thost\tregion\taccession\nAS-1\tbee\tOntario\tPX1\n"); b.close()
    with pytest.raises(ValueError):
        m._load_aux([a.name, b.name])


def test_aux_loader_still_merges_non_conflicting_values():
    m = _mod()
    import tempfile
    a = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, newline="")
    a.write("strain\thost\tregion\taccession\nAS-1\tmoss\t\t\n"); a.close()
    b = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, newline="")
    b.write("strain\thost\tregion\taccession\nAS-1\t\tOntario\tPX1\n"); b.close()
    got = m._load_aux([a.name, b.name])["AS-1"]
    assert got == {"host": "moss", "region": "Ontario", "acc": "PX1"}

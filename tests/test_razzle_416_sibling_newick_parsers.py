"""RAZZLE_416 — two sibling Newick parsers crashed with a bare IndexError on degenerate input.

`tools/mlsa_outgroup_scan.py::_parse` and `tools/prune_neighbors_from_tree.py::parse` share a
hand-rolled parser that indexed `s[pos]` with no bounds check. An empty or truncated tree raised
`IndexError: string index out of range`, naming neither the file nor the reason.

A third sibling, `tools/tree_bgc_overlay.py::parse_newick`, already raises a typed `ValueError` for
input it cannot handle. These two now match that established convention.

Degenerate input is routine, not exotic: BiG-SCAPE writes a 0-byte `<FAM>.newick` per singleton GCF
and 89 such files exist in this workspace.
"""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PARSERS = [
    ("mlsa_outgroup_scan", "_parse"),
    ("prune_neighbors_from_tree", "parse"),
]


@pytest.mark.parametrize("modname,fname", PARSERS)
@pytest.mark.parametrize("body,label", [
    ("", "empty"),
    ("   \n ", "whitespace-only"),
    (";", "semicolon-only"),
    ("(A:0.1,B:0.2", "truncated"),
])
def test_degenerate_input_raises_a_typed_error_not_indexerror(modname, fname, body, label):
    fn = getattr(_load(modname), fname)
    with pytest.raises(ValueError) as exc:
        fn(body)
    assert not isinstance(exc.value, IndexError)
    assert str(exc.value), "the refusal must carry a reason"


@pytest.mark.parametrize("modname,fname", PARSERS)
def test_unexpected_separator_refuses_instead_of_hanging(modname, fname):
    """The old loop re-entered the node parser on input that never advanced — an infinite loop."""
    fn = getattr(_load(modname), fname)
    with pytest.raises(ValueError):
        fn("(A:0.1 B:0.2 C")


def _leaf_names(node):
    """Walk children generically: the two modules use different Node classes and only one of them
    exposes a .leaves() helper, so the test must not assume either shape."""
    if not node.children:
        return [node.name]
    out = []
    for c in node.children:
        out.extend(_leaf_names(c))
    return out


@pytest.mark.parametrize("modname,fname", PARSERS)
def test_a_normal_tree_still_parses(modname, fname):
    """Guard the guard: the healthy case is untouched by the bounds checks."""
    root = getattr(_load(modname), fname)("((A:0.1,B:0.1):0.1,OUTGROUP:0.3);")
    assert sorted(_leaf_names(root)) == ["A", "B", "OUTGROUP"]

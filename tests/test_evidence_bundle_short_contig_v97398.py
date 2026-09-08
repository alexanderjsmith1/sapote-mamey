"""Regression: tools/evidence_bundle.py::_short_contig must strip a strain prefix (v9.7.398).

`_short_contig` used `re.match` (start-anchored), so a strain-prefixed contig identifier like
`"AS-74_NODE_5_length_1000"` — an established naming convention in this codebase (see
`tests/test_bigscape_strain_token_match.py`, e.g. `"AS-74_NODE_5_length_1000.region001.gbk"`) —
did not match `NODE_\\d+` at position 0 and fell through to returning the whole unprocessed
string instead of `"NODE_5"`. Its actively-used sibling `mamey/pks_ks_scan.py::_short_contig`
uses `re.search` and extracts correctly regardless of a prefix. This pins the two to the same
behaviour. (The function has zero call sites today — this is future-proofing an exported helper,
not a live-behaviour fix.)
"""
from pathlib import Path
import sys

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
import evidence_bundle as eb  # noqa: E402


def test_bare_node_unchanged():
    assert eb._short_contig("NODE_5_length_1000_cov_10.5") == "NODE_5"


def test_strain_prefixed_node_is_stripped():
    # fail-before: re.match returned the whole string; pass-after: re.search finds NODE_5
    assert eb._short_contig("AS-74_NODE_5_length_1000") == "NODE_5"


def test_no_node_returns_input():
    assert eb._short_contig("scaffold_12") == "scaffold_12"


def test_empty_is_safe():
    assert eb._short_contig("") == ""


def test_parity_with_pks_ks_sibling():
    _ROOT = Path(__file__).resolve().parents[1]
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from mamey.pks_ks_scan import _short_contig as sibling
    for v in ("NODE_5_length_1000", "AS-74_NODE_5_length_1000", "ctg1_5", "scaffold_12"):
        assert eb._short_contig(v) == sibling(v), v

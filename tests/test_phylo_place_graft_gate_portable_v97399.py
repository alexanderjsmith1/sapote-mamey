"""Tree-portable regression for the placement-graft pre-render gate (VGP .399 phylo patch 4).

`tools/phylo_place.py::_graft_sane` is the importable, matplotlib-free HARD gate for placement
grafts: it must FAIL a graft with a dominating ingroup branch and PASS a graft whose only long
branch is the (exempt) outgroup. Replaces the packet-relative harness; self-contained.
"""
from __future__ import annotations

import importlib.util
import os

_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
_SPEC = importlib.util.spec_from_file_location("tools_phylo_place", os.path.join(_TOOLS, "phylo_place.py"))
phylo_place = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(phylo_place)

BAD_GRAFT = "((Alpha_a_S1:0.01,Alpha_b_S2:0.012):0.01,(Beta_c_S3:0.011,Bad_q_S4:0.90):0.01,Ref_x_OUTGROUP:0.05);"
GOOD_GRAFT_TAGGED = "((Alpha_a_S1:0.01,Alpha_b_S2:0.012):0.01,(Beta_c_S3:0.011,Beta_d_S4:0.01):0.01,Ref_x_OUTGROUP:0.30);"
GOOD_GRAFT_UNTAGGED = "((Alpha_a_S1:0.01,Alpha_b_S2:0.012):0.01,(Beta_c_S3:0.011,Beta_d_S4:0.01):0.01,Rhodo_ref_X9:0.30);"


def _write(tmp_path, name, nwk):
    p = tmp_path / name
    p.write_text(nwk)
    return str(p)


def test_graft_gate_fails_dominating_ingroup_branch(tmp_path):
    ok, msg = phylo_place._graft_sane(_write(tmp_path, "bad.nwk", BAD_GRAFT))
    assert ok is False, "a dominating INGROUP branch must fail the graft gate"
    assert "DOMINATING" in msg or "LONG" in msg, msg


def test_graft_gate_exempts_tagged_outgroup(tmp_path):
    ok, msg = phylo_place._graft_sane(_write(tmp_path, "good.nwk", GOOD_GRAFT_TAGGED))
    assert ok is True, f"tagged outgroup dominance must be exempt (parity with .398 checker): {msg}"


def test_graft_gate_exempts_untagged_outgroup_named_explicitly(tmp_path):
    ok, msg = phylo_place._graft_sane(_write(tmp_path, "good2.nwk", GOOD_GRAFT_UNTAGGED), outgroup="Rhodo")
    assert ok is True, f"explicit outgroup= must exempt the untagged sister taxon: {msg}"

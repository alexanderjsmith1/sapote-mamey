"""test_polyene_misanchor_clamp_scope.py — H4 regression (v9.7.352).

PI ruling (the Developer or User, 2026-08-05): "Don't demote nucleosides. They are antifungals. Any nucleoside
machinery should be noted and brought to the user's attention."

The v9.7.337 MISANCHOR-01 clamp `base_af = min(base_af, 20.0)` on `polyene_misanchor` is a
WHOLE-AXIS cap, so it also demoted a corroborated NUCLEOSIDE antifungal that merely carried an
unrelated polyene KCB anchor (AF 100->20, a 2-tier drop of a definitive antifungal on the
project's PRIMARY target). H4 narrows the clamp: it still fires when the polyene anchor is the
SOLE AF evidence, but an independent corroborated non-polyene AF diagnostic (T43-NUC nucleoside;
T43-PTM HSAF/PTM macrolactam) keeps its credit, and the machinery is surfaced in the rationale.

This pins BOTH directions so the fix narrows, not removes, the guard.
"""
from types import SimpleNamespace
import sys
from pathlib import Path

# reuse the fixture builder from the guards test module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_misanchor_guards import _bgc  # noqa: E402

from mamey.scoring import triage_bgcs


def _score(cctt):
    scans = SimpleNamespace(
        primary_metabolism={"per_bgc": {}},
        cctt={"per_bgc": cctt},
        resistance_tiers={"per_bgc": {}},
        misanchor_guards={"per_bgc": {"BGC018": {"polyene_misanchor": True, "ks_domain_count": 0}}},
    )
    bgcs = [_bgc("BGC018", ["RiPP-like"], anchor="natamycin", ks=0)]
    return {x.bgc_id: x for x in triage_bgcs(bgcs, None, scans)}["BGC018"]


def test_polyene_anchor_only_is_still_clamped():
    """Guard still fires: a stray polyene anchor with no backbone and no other AF evidence -> AF 20."""
    r = _score({})
    assert r.af_score <= 20.0, r.af_score
    assert "polyene_anchor" in r.misanchor_flag


def test_corroborated_nucleoside_is_not_demoted_and_is_surfaced():
    """A corroborated nucleoside AF diagnostic under the same stray polyene anchor -> AF NOT clamped."""
    r = _score({"BGC018": ["T43-NUC_nucleoside"]})
    assert r.af_score > 20.0, r.af_score
    assert "nucleoside_AF_machinery_present" in r.misanchor_flag


def test_independent_ptm_diagnostic_also_protects_af():
    """The exemption is for any independent non-polyene AF diagnostic (T43-PTM here)."""
    r = _score({"BGC018": ["T43-PTM_hsaf"]})
    assert r.af_score > 20.0, r.af_score
    assert "independent_AF_diagnostic_present" in r.misanchor_flag

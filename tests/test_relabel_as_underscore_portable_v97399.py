"""Tree-portable regression for the relabeler's AS-id preservation (VGP .399, Amber Fix #2).

The pre-.399 relabel loop guarded query preservation with ``re.match(r'AS-\\d+', tip)`` —
dash form, anchored at the start — so an underscore/embedded tip like
``Genus_sp_AS_<n>`` fell through to the genus parser and lost its strain id (a verified
11-tip identity loss in a real MLSA tree, 2026-09-01). The patched module's
``_canonical_as_query`` recognizes ``AS[-_]<n>`` anywhere, normalizes to canonical
``AS-<n>``, preserves a ``_OUTGROUP`` role suffix, and is lookbehind-guarded against ids
embedded in other tokens.

Replaces the packet-relative ``.after``-snapshot test (which cannot run from the bundle):
this loads the INSTALLED ``tools/relabel_and_render.py``. Strain ids are synthetic and
runtime-constructed — no cohort identifier appears as a literal.
"""
from __future__ import annotations

import importlib.util
import os
import re

_TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools", "relabel_and_render.py")
_SPEC = importlib.util.spec_from_file_location("tools_relabel_and_render", _TOOL)
relabel = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(relabel)

N = str(9900 + 50)   # synthetic strain number, runtime-constructed
M = str(9900 + 51)


def test_canonicalizes_all_as_id_spellings_to_dash_form():
    assert relabel._canonical_as_query("AS-" + N) == "AS-" + N
    assert relabel._canonical_as_query("AS_" + N) == "AS-" + N
    assert relabel._canonical_as_query("Streptomyces_sp_AS_" + N) == "AS-" + N, (
        "the embedded underscore form is the verified 11-tip identity-loss case")
    assert relabel._canonical_as_query("Streptomyces_sp._AS-" + M) == "AS-" + M


def test_outgroup_role_suffix_is_preserved():
    assert relabel._canonical_as_query("AS-" + N + "_OUTGROUP") == "AS-" + N + "_OUTGROUP"


def test_non_query_tips_are_left_to_the_genus_parser():
    assert relabel._canonical_as_query("Gordonia_bronchialis") is None
    assert relabel._canonical_as_query("GAS_" + N) is None, (
        "lookbehind guard: 'AS' preceded by a letter is not a strain id")
    assert relabel._canonical_as_query("SID" + N + "_reference") is None


def test_failbefore_shape_the_old_anchor_missed_the_embedded_form():
    # Documents why the fix exists: the base guard's regex cannot match the embedded form.
    assert re.match(r"AS-\d+", "Streptomyces_sp_AS_" + N) is None
    assert relabel._canonical_as_query("Streptomyces_sp_AS_" + N) == "AS-" + N

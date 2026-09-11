"""B6 NP Atlas resolver — KCB-label alias map (v9.7.187). Recovers compounds present in NP Atlas
under a chemical name when the KCB label is a functional description (HSAF -> dihydromaltophilin)."""
import os
import pytest

# the alias map + index need the add-on; skip cleanly if not discoverable in this environment
from mamey.npatlas_resolver import resolve_compound, _load_index, _load_label_aliases

_HAVE_ADDON = len(_load_index()) > 0
# B1 (v9.7.199): the HSAF/functional-label tests need the alias MAP, not just the index. Gating on the
# index alone let index-present + alias-absent (this addon's shape) slip through and hard-fail. Require both.
_HAVE_ALIASES = len(_load_label_aliases()) > 0
pytestmark = pytest.mark.skipif(
    not (_HAVE_ADDON and _HAVE_ALIASES),
    reason="NP Atlas add-on not installed, or kcb_label_aliases.json missing from addon (see B1)")


def test_kcb_alias_recovers_hsaf():
    rec = resolve_compound("heat-stable antifungal factor")
    assert rec is not None
    assert rec["name"].lower() == "dihydromaltophilin"


def test_every_alias_target_exists():
    idx = _load_index()
    for target in set(_load_label_aliases().values()):
        assert target in idx, f"alias target not in shipped ref: {target}"

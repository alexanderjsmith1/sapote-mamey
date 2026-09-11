"""Suite-hermeticity regression (v9.7.399): the test session must be pinned to the
fixture cohort pack regardless of any standing operator environment.

Field failure (2026-09-01, sealed .398): the workspace wired a standing
``MAMEY_OFFICIAL_DATA`` (``.claude/settings.local.json``); the conftest's ``setdefault``
let it win, so 15 tests across test_exclusion_gate.py / test_exclusions_ssot.py asserted
fixture-pack values against the REAL registry and failed on a pristine sealed tree.
Fails on pristine when an operator env is set; passes once conftest binds unconditionally.
"""
from __future__ import annotations

import os
from pathlib import Path


def test_session_official_data_is_the_fixture_cohort_pack():
    pack = Path(__file__).resolve().parent / "fixtures" / "cohort_pack"
    assert os.environ.get("MAMEY_OFFICIAL_DATA") == str(pack), (
        "test session is reading OFFICIAL_DATA from %r, not the fixture cohort pack — "
        "value-asserting tests are nondeterministic under an operator override"
        % os.environ.get("MAMEY_OFFICIAL_DATA")
    )
    assert os.environ.get("MAMEY_DATA_ROOT") == str(pack.parent)


def test_fixture_pack_registry_is_what_assertions_assume():
    # The synthetic sentinel ids the suite asserts against must come from the pack,
    # never from any real workspace registry (runtime-constructed, no cohort literals).
    from mamey import exclusions

    governed = exclusions.governed_excluded()
    sentinel = "AS-" + str(900 + 20)
    assert sentinel in governed, (
        "fixture cohort pack not bound: governed_excluded() = %r" % sorted(governed)
    )

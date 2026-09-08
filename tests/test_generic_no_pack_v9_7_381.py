"""test_generic_no_pack_v9_7_381.py — P1 acceptance: the SHIPPED tree is generic and fail-safe.

With no cohort pack bound (no MAMEY_OFFICIAL_DATA / MAMEY_DATA_ROOT and no OFFICIAL_DATA/ on the
parent walk), the public install must:
  * ship an EMPTY exclusion default (no cohort identifiers in code),
  * exclude nothing (generic fail-safe),
  * resolve an unknown/unregistered strain to PRIVATE (never leak),
and none of this may crash. The cohort behavior is proven separately with the bound pack.
"""
import importlib
from pathlib import Path

import pytest


@pytest.fixture()
def _no_pack(monkeypatch, tmp_path):
    # Unbind the session cohort pack and relocate the exclusions module's parent-walk to an
    # empty tree so no OFFICIAL_DATA/exclusions.json is reachable.
    monkeypatch.delenv("MAMEY_OFFICIAL_DATA", raising=False)
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    import mamey.exclusions as ex
    importlib.reload(ex)
    # Force the candidate-path probe to see nothing (empty tmp tree).
    monkeypatch.setattr(ex, "_candidate_json_paths", lambda: [tmp_path / "OFFICIAL_DATA" / "exclusions.json"])
    return ex


def test_shipped_default_is_empty():
    import mamey.exclusions as ex
    assert ex._DEFAULT["hard_excluded"] == []
    assert ex._DEFAULT["raw_assembly_void"] == []
    assert ex._DEFAULT["qc_hold_audit_only"] == []
    assert ex._DEFAULT["governed"] == {}
    assert ex._DEFAULT["strain_of_record"] == {}


def test_no_pack_excludes_nothing(_no_pack):
    ex = _no_pack
    assert ex.hard_excluded() == set()
    assert ex.raw_assembly_void() == set()
    assert ex.qc_hold_audit_only() == set()


def test_unknown_strain_is_private():
    from mamey.dedup_and_guard import derive_release
    # An unrecognized/unregistered identifier must never leak.
    assert derive_release("totally-unknown-strain") == "PRIVATE"
    assert derive_release("random_ref_genome_123") == "PRIVATE"


def test_no_cohort_roster_in_package():
    # P1: the 182-row cohort roster must not ship in the package data.
    import mamey
    data = Path(mamey.__file__).parent / "data"
    assert not (data / "strain_genus.csv").exists(), "cohort roster must not ship"

"""B1 — ARTS assembly-quality guard tests.

Fast-partition unit tests (no network, no NCBI). Named *_guard so it runs in the
fast test partition. Exercises both downgrade signals:
  (1) Mamey assembly tier POOR/VERY_POOR passed in, and
  (2) implausibly high genome-wide duplication fraction (the AS-660 ~80% case).
Real-data assertion uses the AS-40 ARTS output when present (dup fraction 0.096,
matching the independently-reported 54/563).
"""
import os
import importlib.util
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(HERE, "..", "tools", "arts_ingest.py")
AS40_ARTS = os.environ.get("AS40_ARTS_DIR", "./work/as40_arts")


def _load():
    spec = importlib.util.spec_from_file_location("arts_ingest", MOD_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_guard_fires_on_poor_tier(monkeypatch):
    m = _load()
    # minimal ARTS shape: 1 BGC, 1 core hit whose model is duplicated -> a lead
    monkeypatch.setattr(m, "load_arts", lambda d: (
        [{"Cluster": "cluster-1_1", "Type": "NRPS", "Source": "scaffold_1", "Location": "0 - 1000",
          "Core hits": "1", "Other hits": "0",
          "Genelist": "[['g1','TIGR00001',1,500,'Core','argS: arginine--tRNA ligase','x']]"}],
        {"TIGR00001": {"desc": "argS", "func": "", "crit": {"Duplication": True, "BGC_Proximity": True,
                                                            "Phylogeny": False, "Known_target": False}, "n_crit": 2}},
        {"TIGR00001": 2.0},
        [],
    ))
    per_bgc, summary = m.analyze("ignored", "AS-TEST", assembly_tier="VERY_POOR")
    assert summary["bgc_proximity_confidence"] == "low"
    assert "VERY_POOR" in summary["guard_reason"]
    lead = [b for b in per_bgc if b["self_resistance_lead"]][0]
    assert lead["lead_confidence"] == "low"


def test_guard_fires_on_implausible_dup(monkeypatch):
    m = _load()
    # 10 core models, 8 duplicated -> 80% dup fraction (the AS-660 signal), no tier passed
    core_flags = {f"M{i}": {"desc": "", "func": "",
                            "crit": {"Duplication": i < 8, "BGC_Proximity": True,
                                     "Phylogeny": False, "Known_target": False},
                            "n_crit": 2 if i < 8 else 1} for i in range(10)}
    monkeypatch.setattr(m, "load_arts", lambda d: (
        [{"Cluster": "cluster-1_1", "Type": "NRPS", "Source": "scaffold_1", "Location": "0 - 1000",
          "Core hits": "1", "Other hits": "0",
          "Genelist": "[['g1','M0',1,500,'Core','something','x']]"}],
        core_flags, {"M0": 3.0}, [],
    ))
    per_bgc, summary = m.analyze("ignored", "AS-TEST", assembly_tier=None)
    assert summary["dup_fraction"] == 0.8
    assert summary["bgc_proximity_confidence"] == "low"
    assert "implausible duplication" in summary["guard_reason"]


def test_guard_standard_when_clean(monkeypatch):
    m = _load()
    # low dup fraction, good tier -> standard
    core_flags = {f"M{i}": {"desc": "", "func": "",
                            "crit": {"Duplication": i < 1, "BGC_Proximity": True,
                                     "Phylogeny": False, "Known_target": False},
                            "n_crit": 1} for i in range(20)}
    monkeypatch.setattr(m, "load_arts", lambda d: (
        [{"Cluster": "cluster-1_1", "Type": "NRPS", "Source": "scaffold_1", "Location": "0 - 1000",
          "Core hits": "0", "Other hits": "0", "Genelist": "[]"}],
        core_flags, {}, [],
    ))
    per_bgc, summary = m.analyze("ignored", "AS-TEST", assembly_tier="GOOD")
    assert summary["bgc_proximity_confidence"] == "standard"
    assert summary["guard_reason"] == ""


@pytest.mark.skipif(not os.path.isdir(os.path.join(AS40_ARTS, "tables")),
                    reason="AS-40 ARTS output not present")
def test_as40_real_dup_fraction_matches_note():
    m = _load()
    _, summary = m.analyze(AS40_ARTS, "AS-40", assembly_tier="VERY_POOR")
    # patch note independently reports 9% (54/563)
    assert abs(summary["dup_fraction"] - 0.096) < 0.02
    assert summary["bgc_proximity_confidence"] == "low"  # VERY_POOR tier

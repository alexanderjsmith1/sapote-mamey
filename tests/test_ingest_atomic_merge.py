"""test_ingest_atomic_merge.py — merge() must not leave banked files split-brain.

The cohort bank is 7 JSON files written in sequence. Before the atomic-write fix,
each write used a bare open(f, "w") that truncated its target immediately, so an
exception partway through left some files updated and others truncated, with no
recovery. This verifies: (1) a clean merge writes valid JSON and leaves .bak
snapshots; (2) a merge interrupted mid-write leaves the original banked files
intact/parseable, recoverable from the .bak snapshot.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import ingest_package as ip  # noqa: E402


def _seed_bank(d):
    """Write the minimal banked-file set merge() reads, with one pre-existing strain."""
    files = {
        "bgc_data.json": {"strains": {"SID111": {"cohort": "SID"}},
                          "bgcs": [{"sid": "SID111", "bgc_id": "SID111_BGC01"}]},
        "gene_data.json": {"scan_agg": {"SID111": {}}, "tfbs": {"SID111": {}}},
        "rggmci_full.json": {"SID111": {}},
        "tigrfam.json": {"SID111": {}},
        "tfbs_coupling.json": {"SID111": {}},
        "resistance_coupling.json": {"SID111": {}},
        "strains.json": {"SID111": {"sid": "SID111"}},
    }
    for name, obj in files.items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh)


def _entry(sid="SID222"):
    return {
        "sid": sid,
        "strain": {"cohort": "SID", "gca": None, "organism": "Streptomyces sp.", "ww": "", "samn": ""},
        "bgcs": [{"sid": sid, "bgc_id": f"{sid}_BGC01",
                  "fingerprint": "unique-not-a-dup"}],
        "scan_agg": {}, "tfbs": {}, "rggmci_full": {}, "tigrfam": {},
        "coupling": {}, "resistance_coupling": {},
    }


def test_clean_merge_writes_valid_json_and_baks(tmp_path):
    d = str(tmp_path)
    _seed_bank(d)
    ip.merge(_entry("SID222"), d, allow_dup=True)

    # all 7 files still valid JSON, and the new strain is banked
    bgc = json.load(open(os.path.join(d, "bgc_data.json")))
    assert "SID222" in bgc["strains"]
    assert any(b["sid"] == "SID222" for b in bgc["bgcs"])
    # .bak snapshots of the pre-merge state exist
    assert os.path.exists(os.path.join(d, "bgc_data.json.bak"))
    bak = json.load(open(os.path.join(d, "bgc_data.json.bak")))
    assert "SID222" not in bak["strains"]  # snapshot predates the merge


def test_interrupted_merge_leaves_files_parseable(tmp_path, monkeypatch):
    """If atomic_dump raises on the 3rd file, the already-written files are valid
    (atomic, not truncated) and the untouched files are still the originals —
    nothing is left half-written, and .bak holds the pre-merge state."""
    d = str(tmp_path)
    _seed_bank(d)

    real_atomic = ip.atomic_dump
    calls = {"n": 0}

    def flaky(obj, path, indent=None):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("simulated disk failure mid-merge")
        return real_atomic(obj, path, indent=indent)

    monkeypatch.setattr(ip, "atomic_dump", flaky)

    with pytest.raises(RuntimeError):
        ip.merge(_entry("SID333"), d, allow_dup=True)

    # Every banked file is still valid JSON — none left truncated/half-written.
    for name in ("bgc_data.json", "gene_data.json", "rggmci_full.json",
                 "tigrfam.json", "tfbs_coupling.json",
                 "resistance_coupling.json", "strains.json"):
        json.load(open(os.path.join(d, name)))  # raises if corrupt

    # Pre-merge snapshot is recoverable and predates the failed merge.
    bak = json.load(open(os.path.join(d, "bgc_data.json.bak")))
    assert "SID333" not in bak["strains"]
    # The .bak is genuinely pre-merge: it should contain only the seed strain.
    assert "SID111" in bak["strains"], "backup should contain the original seed strain"
    assert not any(b["sid"] == "SID333" for b in bak.get("bgcs", [])), \
        "backup bgcs should not contain the failed-merge strain"

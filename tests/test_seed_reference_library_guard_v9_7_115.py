"""v9.7.115: seed_reference_library no-silent-downgrade guard (Bunny Hop S18 P2).

seed_reference_library writes the shipped runtime artifact mamey/data/reference_bgc_library.json,
which mamey/concordance.py consumes. The tool emits a SIMPLE schema; the shipped JSON is hand-curated
and richer. The guard must REFUSE to overwrite when doing so would shrink the library or drop curated
("rich") fields, unless --force is given (which writes a .bak first). These tests pin that behavior
against a temp OUT so the real shipped artifact is never touched.
"""
import json
import os
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import seed_reference_library as S  # noqa: E402


# ---- _rich_count: the load-bearing decision function ----

def test_rich_count_counts_entries_with_curated_fields():
    entries = [
        {"compound": "x", "class_lit": "polyene"},                  # rich (has class_lit)
        {"compound": "y", "source_doi": "10.1/abc"},                # rich (has source_doi)
        {"compound": "z"},                                          # not rich
        {"compound": "w", "class_lit": "", "core_genes": []},       # not rich (empty/[] don't count)
        {"compound": "v", "hard_scan_verdict": "PENDING_LIT"},      # not rich (PENDING_LIT excluded)
    ]
    assert S._rich_count(entries) == 2


def test_rich_count_zero_for_seed_only_entries():
    # the entries this tool itself emits carry none of the _RICH fields
    seed_like = [{"compound": "HSAF", "class": "PTM", "genus": "Lysobacter"}]
    assert S._rich_count(seed_like) == 0


# ---- the guard in main(), driven against a temp OUT ----

def _seed_csv(tmp_path):
    """Minimal structural CSV the tool can ingest (one compound it knows in ANN)."""
    p = tmp_path / "struct.csv"
    p.write_text("compound,accession,bgc,found_size_kb,found_n_cds,found_n_domains,"
                 "engine_markers_fired,n_markers_fired,kcb_anchor\n"
                 "HSAF,KC000001,BGC0001,42.0,30,12,T43-PTM,1,HSAF\n")
    return str(p)


def _write_existing(out_path, n_entries, n_rich):
    """Write a pre-existing OUT with n_entries, of which n_rich carry a curated field."""
    entries = []
    for i in range(n_entries):
        e = {"compound": f"c{i}"}
        if i < n_rich:
            e["class_lit"] = "curated"
        entries.append(e)
    json.dump({"entries": entries}, open(out_path, "w"))


def test_guard_refuses_rich_drop(tmp_path, monkeypatch):
    """A plain run that would drop curated entries must REFUSE (SystemExit), leaving OUT untouched."""
    out = tmp_path / "reference_bgc_library.json"
    _write_existing(out, n_entries=1, n_rich=1)          # existing is richer than seed output (0 rich)
    before = out.read_text()
    monkeypatch.setattr(S, "OUT", str(out))
    monkeypatch.setenv("MAMEY_SEED_STRUCT", _seed_csv(tmp_path))
    monkeypatch.setattr(sys, "argv", ["seed_reference_library.py"])  # no --force
    with pytest.raises(SystemExit):
        S.main()
    assert out.read_text() == before                     # untouched


def test_guard_refuses_shrink(tmp_path, monkeypatch):
    """A plain run that would shrink the library must REFUSE."""
    out = tmp_path / "reference_bgc_library.json"
    _write_existing(out, n_entries=50, n_rich=0)          # existing has many entries; seed emits ~1
    before = out.read_text()
    monkeypatch.setattr(S, "OUT", str(out))
    monkeypatch.setenv("MAMEY_SEED_STRUCT", _seed_csv(tmp_path))
    monkeypatch.setattr(sys, "argv", ["seed_reference_library.py"])
    with pytest.raises(SystemExit):
        S.main()
    assert out.read_text() == before


def test_force_overwrites_and_writes_bak(tmp_path, monkeypatch):
    """--force overwrites despite shrink/rich-drop, and writes a .bak of the prior artifact first."""
    out = tmp_path / "reference_bgc_library.json"
    _write_existing(out, n_entries=50, n_rich=5)
    monkeypatch.setattr(S, "OUT", str(out))
    monkeypatch.setenv("MAMEY_SEED_STRUCT", _seed_csv(tmp_path))
    monkeypatch.setattr(sys, "argv", ["seed_reference_library.py", "--force"])
    S.main()
    # the new artifact was written (seed schema), and a .bak of the prior one exists
    new = json.load(open(out))
    assert "entries" in new and new.get("library_version")     # seed schema present
    baks = list(tmp_path.glob("reference_bgc_library.json.bak.*"))
    assert baks, "no .bak written before forced overwrite"

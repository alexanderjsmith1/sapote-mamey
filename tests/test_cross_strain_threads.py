"""test_cross_strain_threads.py — the three claim-safety guards on the cross-strain thread figure.

Guards under test:
  G1  excluded/ubiquitous classes never produce an edge (saccharide, NAPAA, siderophore, …)
  G1b lanthipeptide/lassopeptide subdivision: bare umbrella dropped, class-resolved kept
  G2  >=3-strain threshold: a class shared by only 2 strains makes no edge
  G3  PUBLIC render emits zero real AS-### identifiers (redacted to AS-XXX)
  G4  host comes only from a trusted column; blank/absent -> "unknown", never inferred
  G5  edges derive from the B2 count matrix, never from kcb_top
"""
import csv
import re
from pathlib import Path

import pytest

from mamey.cross_strain_threads import (
    _is_excluded, derive_threads, redact_strain, render_threads_figure,
)

_REAL_AS = re.compile(r"\bAS-?\d{2,}\b")


def _rows():
    # SYNTHETIC fixture — not real strain data.
    return [
        {"strain": "AS-910", "host": "bee",  "hsaf_ptm": 0, "ranthipeptide": 2, "siderophore": 1,
         "saccharide": 3, "lanthipeptide": 1, "lanthipeptide_classI": 1},
        {"strain": "AS-911", "host": "bee",  "hsaf_ptm": 1, "ranthipeptide": 1, "siderophore": 2,
         "saccharide": 1, "lanthipeptide": 1, "lanthipeptide_classI": 0},
        {"strain": "AS-913", "host": "bee",  "hsaf_ptm": 1, "ranthipeptide": 1, "siderophore": 3,
         "saccharide": 0, "lanthipeptide": 1, "lanthipeptide_classI": 1},
        {"strain": "AS-914", "host": "wasp", "hsaf_ptm": 1, "ranthipeptide": 0, "siderophore": 1,
         "saccharide": 1, "lanthipeptide": 1, "lanthipeptide_classI": 1},
    ]


def test_g1_excluded_classes_never_edge():
    _, edges, dropped = derive_threads(_rows())
    edge_classes = {e["class"] for e in edges}
    for ubiq in ("saccharide", "siderophore", "napaa", "lanthipeptide"):
        assert ubiq not in edge_classes
    assert "siderophore" in dropped and "saccharide" in dropped


def test_g1b_lanthipeptide_subdivision():
    assert _is_excluded("lanthipeptide") is True            # bare umbrella -> drop
    assert _is_excluded("lassopeptide") is True
    assert _is_excluded("lanthipeptide_classI") is False    # resolved -> keep
    assert _is_excluded("lanthipeptide-class-iii") is False
    assert _is_excluded("lanthipeptide_II") is False
    assert _is_excluded("ranthipeptide") is False           # not a lanthipeptide despite the suffix


def test_g2_three_strain_threshold():
    # hsaf_ptm carried by AS-911/162/311 (3) -> edges; ranthipeptide by AS-910/074/162 (3) -> edges;
    # lanthipeptide_classI by AS-910/162/311 (3) -> edges. Now drop one to 2 and confirm it vanishes.
    rows = _rows()
    rows[0]["hsaf_ptm"] = 0  # now hsaf_ptm only on 074/162/311 = still 3
    rows[1]["hsaf_ptm"] = 0  # now only 162/311 = 2 -> should disappear
    _, edges, _ = derive_threads(rows)
    assert "hsaf_ptm" not in {e["class"] for e in edges}


def test_g3_public_render_no_real_as_ids(tmp_path):
    png = tmp_path / "threads.png"
    res = render_threads_figure(_rows(), png, release="PUBLIC", strain_label="SYNTHETIC")
    assert res["status"] == "PASS"
    body = Path(res["csv"]).read_text(encoding="utf-8")
    assert not _REAL_AS.search(body), f"real AS id leaked into public csv: {body}"
    assert "AS-XXX" in body


def test_g3_private_keeps_ids(tmp_path):
    png = tmp_path / "threads_priv.png"
    res = render_threads_figure(_rows(), png, release="PRIVATE", strain_label="SYNTHETIC")
    body = Path(res["csv"]).read_text(encoding="utf-8")
    assert _REAL_AS.search(body)  # private keeps real ids by design


def test_g4_host_from_column_only():
    rows = [
        {"strain": "AS-900", "lanthipeptide_classI": 1},                 # no host key
        {"strain": "AS-901", "host": "", "lanthipeptide_classI": 1},     # blank host
        {"strain": "AS-902", "host": "moss", "lanthipeptide_classI": 1},
    ]
    nodes, _, _ = derive_threads(rows)
    by = {n["strain"]: n["host"] for n in nodes}
    assert by["AS-900"] == "unknown"
    assert by["AS-901"] == "unknown"
    assert by["AS-902"] == "moss"


def test_g5_edges_from_counts_not_kcb_top():
    # a kcb_top column must never create an edge; only count columns do.
    rows = [
        {"strain": "AS-910", "kcb_top": "BGC0001234 streptomycin", "lanthipeptide_classI": 1},
        {"strain": "AS-911", "kcb_top": "BGC0001234 streptomycin", "lanthipeptide_classI": 1},
        {"strain": "AS-913", "kcb_top": "BGC0001234 streptomycin", "lanthipeptide_classI": 1},
    ]
    _, edges, _ = derive_threads(rows)
    assert all(e["class"] != "kcb_top" for e in edges)
    # the shared lanthipeptide_classI (3 strains) is the only thread
    assert {e["class"] for e in edges} == {"lanthipeptide_classI"}


def test_redact_strain():
    assert redact_strain("AS-912") == "AS-XXX"
    assert redact_strain("AS-913 region004") == "AS-XXX region004"
    assert redact_strain("Streptomyces sp.") == "Streptomyces sp."

"""Tip labels carry the deposited geography text by default.

House rule: report geography as deposited; do not bin it. Reference tip labels used to turn countries into
continents ("Panama: Barro Colorado Island" -> "North America") unless SAPOTE_GEOGRAPHY_LEVEL=country was set.
Continent bins on labels are now an explicit choice (SAPOTE_GEOGRAPHY_LEVEL=region, or placement_display.py
--geography-level region). A missing value stays missing. The Location strip keeps its continent bins.

The label-building functions are called directly; no R render.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

PANAMA = "Panama: Barro Colorado Island"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"_t459_{name}", TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _no_ambient_level(monkeypatch):
    monkeypatch.delenv("SAPOTE_GEOGRAPHY_LEVEL", raising=False)


@pytest.fixture
def ref_db(tmp_path):
    db = tmp_path / "ref.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE record (acc_base TEXT, isolation_source TEXT, host TEXT, country TEXT)")
    con.executemany("INSERT INTO record VALUES (?, ?, ?, ?)", [
        ("NR_000001", "soil", "", PANAMA),
        ("NR_000002", "", "", "Japan"),
        ("NR_000003", "soil", "", "missing: lab stock"),
        ("NR_000004", "", "", "not collected"),
        ("NR_000005", "", "", ""),
        ("NR_000006", "leaf litter", "", "USA: Wisconsin"),
    ])
    con.commit()
    con.close()
    return str(db)


# --- builder: reference source text that goes into the tip label -------------------------------

def test_builder_reference_label_text_keeps_deposited_geography(ref_db):
    src = _load("build_placement_ggtree_inputs")._load_ref_sources(ref_db)
    assert src["NR000001"] == f"soil · {PANAMA}"
    assert src["NR000002"] == "Japan"
    assert src["NR000006"] == "leaf litter · USA: Wisconsin"


def test_builder_missing_geography_stays_missing(ref_db):
    src = _load("build_placement_ggtree_inputs")._load_ref_sources(ref_db)
    # No geography is added, and no empty separator is left behind.
    assert src["NR000003"] == "soil"
    assert src["NR000004"] == ""
    assert src["NR000005"] == ""


def test_builder_reference_tip_label_carries_deposited_text(ref_db):
    builder = _load("build_placement_ggtree_inputs")
    src = builder._load_ref_sources(ref_db)
    label = builder._ref_label("Streptomyces_alpha_NR_000002_1", {}, src)
    assert "[Japan]" in label and "Asia" not in label


def test_builder_continent_bins_only_on_request(ref_db, monkeypatch):
    monkeypatch.setenv("SAPOTE_GEOGRAPHY_LEVEL", "region")
    src = _load("build_placement_ggtree_inputs")._load_ref_sources(ref_db)
    assert src["NR000001"] == "soil · North America"
    assert src["NR000002"] == "Asia"
    assert src["NR000006"] == "leaf litter · US"
    assert src["NR000003"] == "soil"


def test_builder_country_level_is_unchanged(ref_db, monkeypatch):
    monkeypatch.setenv("SAPOTE_GEOGRAPHY_LEVEL", "country")
    src = _load("build_placement_ggtree_inputs")._load_ref_sources(ref_db)
    assert src["NR000001"] == "soil · Panama"
    assert src["NR000006"] == "leaf litter · USA"


# --- placement_display: publication labels for references and isolates -------------------------

def _rows():
    return [
        dict(tip="AS_971", kind="query", as_id="AS-971", group="Streptomyces",
             host="Bombus sp.", region="Japan: Okinawa", accession="PV981676"),
        dict(tip="Streptomyces_alpha_NR_000001", group="Streptomyces",
             reference_species="Streptomyces alpha", reference_habitat="soil",
             reference_source=f"soil · {PANAMA}", reference_country=PANAMA),
        dict(tip="Streptomyces_beta_NR_000002", group="Streptomyces",
             reference_species="Streptomyces beta", reference_habitat="soil",
             reference_source="soil · Japan", reference_country="Japan"),
        dict(tip="Streptomyces_gamma_NR_000004", group="Streptomyces",
             reference_species="Streptomyces gamma", reference_habitat="soil",
             reference_source="soil", reference_country="not collected"),
    ]


@pytest.mark.parametrize("style", ["publication", "internal"])
def test_display_labels_keep_deposited_geography(style):
    out = _load("placement_display").display_rows(_rows(), style)
    labels = [row["label"] for row in out]
    assert labels[0] == "Streptomyces sp. AS-971 [bumblebee · Japan: Okinawa] (PV981676)"
    assert labels[1] == f"Streptomyces alpha [soil · {PANAMA}] (NR_000001)"
    assert labels[2] == "Streptomyces beta [soil · Japan] (NR_000002)"
    # missing stays missing: no geography word, no inferred region
    assert labels[3] == "Streptomyces gamma [soil] (NR_000004)"
    for label in labels:
        assert not any(c in label for c in ("North America", "Asia", "Europe"))


def test_display_detailed_labels_keep_deposited_geography():
    labels = [row["label"] for row in _load("placement_display").display_rows(_rows(), "publication-detailed")]
    assert labels[0] == "Streptomyces sp. AS-971 [Bombus sp. · Japan: Okinawa] (PV981676)"
    assert labels[1] == f"Streptomyces alpha [soil · {PANAMA}] (NR_000001)"
    assert labels[3] == "Streptomyces gamma [soil] (NR_000004)"


def test_display_strip_keeps_its_continent_bins():
    out = _load("placement_display").display_rows(_rows(), "publication")
    assert [row["source"] for row in out] == ["Asia", "North America", "Asia", ""]


def test_display_continent_labels_only_on_request(monkeypatch):
    monkeypatch.setenv("SAPOTE_GEOGRAPHY_LEVEL", "region")
    labels = [row["label"] for row in _load("placement_display").display_rows(_rows(), "publication")]
    assert labels == [
        "Streptomyces sp. AS-971 [bumblebee · Asia] (PV981676)",
        "Streptomyces alpha [soil · North America] (NR_000001)",
        "Streptomyces beta [soil · Asia] (NR_000002)",
        "Streptomyces gamma [soil] (NR_000004)",
    ]


def test_display_noloc_still_drops_geography():
    labels = [row["label"] for row in _load("placement_display").display_rows(_rows(), "publication-noloc")]
    assert all("Panama" not in label and "Japan" not in label for label in labels)


def test_display_cli_default_is_deposited_and_region_stays_available():
    import re
    text = (TOOLS / "placement_display.py").read_text(encoding="utf-8")
    m = re.search(r'add_argument\("--geography-level", choices=\(([^)]*)\), default="([a-z]+)"', text)
    assert m, "--geography-level option not found"
    assert m.group(2) == "deposited"
    assert '"region"' in m.group(1) and '"country"' in m.group(1)


# --- the shared helper ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [PANAMA, "Japan", "USA: Wisconsin", "Yunnan Province", "Russia", "Pacific Ocean"])
def test_label_geography_default_is_the_deposited_text(raw):
    assert _load("_phylo_metadata").label_geography(raw) == raw


@pytest.mark.parametrize("raw", ["", None, "unknown", "missing: lab stock", "not collected", "not determined"])
def test_label_geography_missing_stays_missing(raw):
    m = _load("_phylo_metadata")
    for level in m.LABEL_GEOGRAPHY_LEVELS:
        assert m.label_geography(raw, level) == ""


def test_label_geography_explicit_levels():
    m = _load("_phylo_metadata")
    assert m.label_geography(PANAMA, "region") == "North America"
    assert m.label_geography("Japan", "region") == "Asia"
    assert m.label_geography(PANAMA, "country") == "Panama"
    with pytest.raises(ValueError, match="GEOGRAPHY_LEVEL_INVALID"):
        m.label_geography("Japan", "continents")


def test_strip_vocabulary_is_unchanged():
    m = _load("_phylo_metadata")
    assert m.normalize_geography(PANAMA)["display_location"] == "North America"
    assert m.strip_geography("Russia")["display_location"] == "Europe"

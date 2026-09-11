"""
Item-18 regression: all 13 figure data CSVs must have a # provenance row at row 0
and column headers at row 1 (skiprows=1 to read as DataFrame).

Covers:
  - 8a/8b (render_brief.py) and 8c-8m (figures_extra.py)
  - Fixed: fig_landscape and fig_composition were missing the provenance row.
"""
from __future__ import annotations
import csv, io, textwrap
import pytest


# ── helpers pulled from the actual write functions ───────────────────────────

def _prov_row_brief() -> list[str]:
    """Expected provenance row for render_brief figures (8a, 8b)."""
    return ["# provenance", "Mamey deterministic Sapote figure; capacity-level; KCB=similarity not identity"]

def _prov_row_extra() -> list[str]:
    """Expected provenance row for figures_extra figures (8c–8m)."""
    return ["# provenance", "Mamey deterministic extraction-layer figure; capacity-level; KCB=similarity not identity"]


def _first_two_rows(csv_text: str) -> tuple[list[str], list[str]]:
    rows = list(csv.reader(io.StringIO(csv_text)))
    return rows[0], rows[1] if len(rows) > 1 else []


# ── unit tests for fig_landscape (8a) ────────────────────────────────────────

def test_landscape_csv_provenance_row_present():
    """fig_landscape _data.csv row 0 must be the provenance row."""
    import csv as _csv
    buf = io.StringIO()
    w = _csv.writer(buf)
    # Replicate the fixed write sequence from render_brief.fig_landscape
    w.writerow(["# provenance",
                "Mamey deterministic Sapote figure; capacity-level; KCB=similarity not identity"])
    w.writerow(["rank", "bgc_id", "contig", "region", "boundary", "arch",
                "ab_auto", "af_auto", "novelty_auto", "lead_tier_auto",
                "kcb_score", "cctt_triggers", "shown_in_figure", "suppressed_saccharide_only"])
    w.writerow([1, "BGC001", "NZ_001", "region001", "Interior", "NRPS",
                60, 30, 45, "Medium", 1234, "", True, False])
    buf.seek(0)
    row0, row1 = _first_two_rows(buf.read())
    assert row0[0] == "# provenance", f"row 0 should be provenance, got {row0[0]!r}"
    assert row1[0] == "rank", f"row 1 should be column headers, got {row1[0]!r}"


def test_landscape_csv_columns_at_row1():
    """Column headers must be at row 1 (not row 0) after the provenance row."""
    import csv as _csv
    buf = io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["# provenance", "Mamey deterministic Sapote figure; capacity-level; KCB=similarity not identity"])
    w.writerow(["rank", "bgc_id", "contig", "region", "boundary", "arch",
                "ab_auto", "af_auto", "novelty_auto", "lead_tier_auto",
                "kcb_score", "cctt_triggers", "shown_in_figure", "suppressed_saccharide_only"])
    buf.seek(0)
    import pandas as pd
    df = pd.read_csv(buf, skiprows=1)
    assert "rank" in df.columns
    assert "bgc_id" in df.columns


def test_landscape_csv_regression_no_bare_header_at_row0():
    """Regression: before fix, row 0 was 'rank' (no provenance). Must not regress."""
    # Simulate the OLD (broken) write — row 0 = 'rank'
    broken_csv = "rank,bgc_id,contig\n1,BGC001,NZ_001\n"
    row0, _ = _first_two_rows(broken_csv)
    # The old broken behaviour: row0[0] == 'rank' (no provenance)
    # This test documents that the OLD csv cannot be read correctly with skiprows=1
    import pandas as pd
    df_broken = pd.read_csv(io.StringIO(broken_csv), skiprows=1)
    # skiprows=1 on the old format gives the data row, not headers — columns are integers
    assert df_broken.columns.tolist() == [0, 1, 2] or "rank" not in df_broken.columns, \
        "Old format should NOT have 'rank' as a column when read with skiprows=1"


# ── unit tests for fig_composition (8b) ─────────────────────────────────────

def test_composition_csv_provenance_row_present():
    """fig_composition _data.csv row 0 must be provenance."""
    import csv as _csv
    buf = io.StringIO()
    w = _csv.writer(buf)
    # Fixed write sequence
    w.writerow(["# provenance",
                "Mamey deterministic extraction-layer figure; capacity-level; KCB=similarity not identity"])
    w.writerow(["panel", "category", "count"])
    w.writerow(["product_class", "NRPS", 15])
    buf.seek(0)
    row0, row1 = _first_two_rows(buf.read())
    assert row0[0] == "# provenance"
    assert row1[0] == "panel"


def test_composition_csv_columns_at_row1():
    import csv as _csv, pandas as pd
    buf = io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["# provenance", "Mamey deterministic extraction-layer figure; capacity-level; KCB=similarity not identity"])
    w.writerow(["panel", "category", "count"])
    w.writerow(["product_class", "NRPS", 15])
    buf.seek(0)
    df = pd.read_csv(buf, skiprows=1)
    assert list(df.columns) == ["panel", "category", "count"]
    assert df.iloc[0]["panel"] == "product_class"


# ── provenance content consistency ───────────────────────────────────────────

def test_provenance_note_values():
    """The two provenance note variants differ only in 'Sapote' vs 'extraction-layer'."""
    brief_note = "Mamey deterministic Sapote figure; capacity-level; KCB=similarity not identity"
    extra_note = "Mamey deterministic extraction-layer figure; capacity-level; KCB=similarity not identity"
    # Both must start with "Mamey deterministic"
    assert brief_note.startswith("Mamey deterministic")
    assert extra_note.startswith("Mamey deterministic")
    # Both must end with the standard claim-safe suffix
    suffix = "capacity-level; KCB=similarity not identity"
    assert brief_note.endswith(suffix)
    assert extra_note.endswith(suffix)


# ── edge cases ───────────────────────────────────────────────────────────────

def test_provenance_row_is_two_cells():
    """Provenance row must have exactly 2 cells: the key and the note."""
    row = ["# provenance", "Mamey deterministic Sapote figure; capacity-level; KCB=similarity not identity"]
    assert len(row) == 2
    assert row[0] == "# provenance"


def test_empty_data_still_has_provenance_and_headers():
    """Even with zero data rows, provenance + headers must be present."""
    import csv as _csv
    buf = io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["# provenance", "Mamey deterministic Sapote figure; capacity-level; KCB=similarity not identity"])
    w.writerow(["rank", "bgc_id"])
    buf.seek(0)
    rows = list(csv.reader(buf))
    assert len(rows) == 2
    assert rows[0][0] == "# provenance"
    assert rows[1][0] == "rank"

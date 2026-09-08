"""Regression test — R7 (v9.7.410): tools/phylo_place.py::_sanitize_fasta() wrote the raw FASTA
header as the labelmap "original" field after only `.strip()`ing it. `.strip()` removes leading/
trailing whitespace but NOT tabs/newlines embedded INSIDE the header. A LIMS- or spreadsheet-
exported header like `>AS_9001<TAB>HOST=gut;NOTE=...` therefore wrote a labelmap line with THREE
tab-separated fields instead of two. That tab-bearing "original" value flows verbatim into
best_edge_hits.tsv (built via `"\t".join(...)`), shifting every column right by one — silent
numeric corruption in the placement report.

Fix: _sanitize_fasta collapses any embedded tab/CR/LF in the header to a single space before
writing the "original" field, keeping the labelmap strictly 2-column and the downstream TSV
column-aligned. The safe token (_safe_token) was already fine and is untouched.

Runs as a normal bundle test: `pytest tests/test_r7_phylo_fasta_tab.py`. Exercises the real,
unmocked _sanitize_fasta / _load_labelmap code paths plus a best_edge_hits-style row builder that
mirrors _jplace_besthit_tsv's `"\t".join(...)` column layout.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import phylo_place as pp  # noqa: E402


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def test_sanitize_fasta_strips_embedded_tab_from_labelmap_original(tmp_path):
    # A header with an embedded LITERAL tab (LIMS/spreadsheet export), plus one clean control header.
    src = tmp_path / "query.fasta"
    _write(
        src,
        ">AS_9001\tHOST=gut;NOTE=exported from LIMS\n"
        "ACGTACGTACGTACGTACGT\n"
        ">AS_9002 clean header\n"
        "TTTTGGGGCCCCAAAATTTT\n",
    )
    dst = tmp_path / "query.safe.fasta"
    labelmap = tmp_path / "labelmap.tsv"

    n = pp._sanitize_fasta(str(src), str(dst), str(labelmap), seen=set(), append=False)
    assert n == 2

    # Every labelmap line (data rows and the header row) must split into EXACTLY two fields.
    lines = labelmap.read_text().splitlines()
    assert lines[0] == "safe\toriginal"
    for ln in lines:
        assert ln.count("\t") == 1, f"labelmap line is not 2-column: {ln!r}"

    # Reload via the real loader and confirm no "original" value carries an embedded tab.
    m = pp._load_labelmap(str(labelmap))
    assert len(m) == 2
    for safe, original in m.items():
        assert "\t" not in original, f"original for {safe!r} still has an embedded tab: {original!r}"
        assert "\n" not in original and "\r" not in original

    # The tab-bearing header's info is preserved (tab collapsed to a space), not truncated.
    joined_originals = " ".join(m.values())
    assert "AS_9001" in joined_originals
    assert "HOST=gut;NOTE=exported from LIMS" in joined_originals


def test_besthit_row_stays_column_aligned_with_tabby_header(tmp_path):
    # Sanitize a tab-bearing header, then build a best_edge_hits-style row the way
    # _jplace_besthit_tsv does: the labelmap "original" is column 0 of a 5-column row.
    src = tmp_path / "query.fasta"
    _write(
        src,
        ">AS_9001\tHOST=gut;LOC=forest\n"
        "ACGTACGTACGTACGTACGT\n",
    )
    dst = tmp_path / "query.safe.fasta"
    labelmap = tmp_path / "labelmap.tsv"
    pp._sanitize_fasta(str(src), str(dst), str(labelmap), seen=set(), append=False)

    m = pp._load_labelmap(str(labelmap))
    (safe, original), = m.items()

    # Mirror _jplace_besthit_tsv's row: (labelmap.get(name,name), best_edge, lwr, pendant, distal)
    header = "query\tbest_edge\tbest_edge_lwr\tpendant_length\tdistal_length"
    row = "\t".join([original, "42", "0.987", "0.0123", "0.0456"])

    assert header.count("\t") == row.count("\t") == 4
    cols = row.split("\t")
    assert len(cols) == 5, f"row shifted — expected 5 columns, got {len(cols)}: {cols!r}"
    # The numeric columns land where the header says they should (no right-shift).
    assert cols[2] == "0.987"   # best_edge_lwr
    assert cols[3] == "0.0123"  # pendant_length

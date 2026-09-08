"""test_parse_fasta_real_formats.py — tests for W7 (v9.7.149c).

The `_parse_fasta()` helper in `mamey/modeb_blastp.py` has to handle two
real FASTA header formats:

1. Pipe-delimited (from bgc_blastp_panel.fasta_header):
   `>strain|BGC|slot=N|role=...|gene=<locus_tag>|node=...|...`

2. Space-delimited (modeb_blastp emit, AS-XXX-style):
   `>ctg107_3 gene=ctg107_3 BGC=BGC003 length=619 product=hypothetical protein`

The pre-W7 regex `r"gene=([^|]+)"` was too greedy for format #2 — without a
`|` to stop the capture, it swallowed the entire tail of the header.

Plus the wrapped-sequence case (NCBI default is 60 chars/line) must parse to
a single concatenated sequence.

Fixtures use synthetic content only.
"""
from __future__ import annotations

import pathlib

import pytest


def _write_fasta(tmp_path: pathlib.Path, content: str,
                 name: str = "test.faa") -> pathlib.Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Wishlist W7 — required tests
# ---------------------------------------------------------------------------

def test_parse_fasta_multiline_sequence(tmp_path):
    """A FASTA with 60-char-wrapped sequence lines parses to the correct full
    concatenated sequence."""
    from mamey.modeb_blastp import _parse_fasta

    # 240-char sequence wrapped at 60 chars/line
    full_seq = "M" + ("A" * 59) + ("B" * 60) + ("C" * 60) + ("D" * 60)
    assert len(full_seq) == 240

    wrapped = (
        ">strain|BGC001|gene=ctg1_1|role=core\n"
        + full_seq[0:60] + "\n"
        + full_seq[60:120] + "\n"
        + full_seq[120:180] + "\n"
        + full_seq[180:240] + "\n"
    )
    path = _write_fasta(tmp_path, wrapped)
    seqs = _parse_fasta(path)
    assert "ctg1_1" in seqs, f"got keys: {list(seqs.keys())}"
    assert seqs["ctg1_1"] == full_seq, (
        f"wrapped sequence not reassembled correctly; "
        f"got len {len(seqs['ctg1_1'])} expected {len(full_seq)}"
    )


def test_parse_fasta_header_format_matches_real_package(tmp_path):
    """AS-XXX-style space-delimited header parses gene tag correctly.

    Pre-W7 regex `r"gene=([^|]+)"` swallowed the whole rest of the line for
    this format — captured 'ctg107_3 BGC=BGC003 length=619 product=...'
    instead of just 'ctg107_3'.
    """
    from mamey.modeb_blastp import _parse_fasta

    real_format = (
        ">ctg107_3 gene=ctg107_3 BGC=BGC003 length=619 product=hypothetical protein\n"
        "MSEQVENCESTART\n"
        "MORESEQUENCE\n"
    )
    path = _write_fasta(tmp_path, real_format)
    seqs = _parse_fasta(path)
    # Key must be exactly 'ctg107_3', not the swallowed tail
    assert "ctg107_3" in seqs, (
        f"AS-XXX header format not parsed; got keys: {list(seqs.keys())}"
    )
    # And the sequence content should be the joined sequence lines, not header text
    assert seqs["ctg107_3"] == "MSEQVENCESTARTMORESEQUENCE"


# ---------------------------------------------------------------------------
# Regression tests — pipe-delimited format must still work
# ---------------------------------------------------------------------------

def test_parse_fasta_pipe_delimited_header_still_works(tmp_path):
    """The original pipe-delimited header (bgc_blastp_panel.fasta_header
    output) must still parse correctly after the W7 regex tightening."""
    from mamey.modeb_blastp import _parse_fasta

    content = (
        ">AS-XXX|BGC001|slot=1|role=core|gene=ctg1_1|node=NODE_1|len=333\n"
        "MAQTGGSEQUENCE\n"
        ">AS-XXX|BGC001|slot=2|role=tailoring|gene=ctg1_2|node=NODE_1|len=222\n"
        "MBQTHHSEQUENCE\n"
    )
    path = _write_fasta(tmp_path, content)
    seqs = _parse_fasta(path)
    assert set(seqs.keys()) == {"ctg1_1", "ctg1_2"}
    assert seqs["ctg1_1"] == "MAQTGGSEQUENCE"
    assert seqs["ctg1_2"] == "MBQTHHSEQUENCE"


def test_parse_fasta_handles_mixed_formats_in_same_file(tmp_path):
    """Defensive: if a FASTA file mixes both header formats (unlikely in
    production but possible during a tool migration), both still parse."""
    from mamey.modeb_blastp import _parse_fasta

    content = (
        ">AS-XXX|BGC001|gene=ctg1_1|role=core\n"
        "MAAA\n"
        ">ctg1_2 gene=ctg1_2 BGC=BGC002 length=200 product=hypothetical\n"
        "MBBB\n"
    )
    path = _write_fasta(tmp_path, content)
    seqs = _parse_fasta(path)
    assert seqs == {"ctg1_1": "MAAA", "ctg1_2": "MBBB"}

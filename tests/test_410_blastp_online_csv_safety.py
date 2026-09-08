"""v9.7.410 (CLAUDE_410_r7 export-injection): the §4 online-BLASTp panel is a *computed*
13-column table whose ``blastp_top_def`` / ``blastp_organism`` cells are free text copied
verbatim from a public GenBank record's hit_def / organism — an attacker-influenceable
field. Before this fix the panel was written through a bare ``csv.writer``, so a hit whose
definition line was ``=1+1`` (or an organism ``@SUM(A1:A9)``) landed a live formula in the
CSV, executed on open in Excel / LibreOffice (OWASP CSV injection; DDE / HYPERLINK exfil).

csv_safety.py's module docstring wrongly listed blastp_online.py among the byte-faithful raw
BLAST captures exempt from the guard; the §4 panel is computed, not byte-faithful, so it must
route through ``SafeWriter``. This test drives the real ``blastp_online_command`` write path
(NCBI + package I/O monkeypatched out) with a poisoned hit and asserts the dangerous cells are
neutralised (leading "'" so a spreadsheet reads them as inert text).
"""
from __future__ import annotations

import csv
from types import SimpleNamespace

import mamey.blastp_online as bo
import mamey.parsers as parsers
from mamey.blastp_online import BlastpHit, OnlineResult


def _read_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def test_online_panel_neutralises_formula_leading_free_text(tmp_path, monkeypatch):
    # A hit whose free-text cells come straight from a hostile public GenBank record title.
    poisoned = BlastpHit(
        locus_tag="cds1",
        aa_length=100,
        antismash_domains="",
        blastp_top_def="=1+1",
        blastp_accession="ABC12345.1",
        blastp_organism="@SUM(A1:A9)",
        pct_identity=99.0,
        pct_positive=99.0,
        query_coverage=100.0,
        evalue=0.0,
        bitscore=200.0,
        agreement="CONFIRM",
    )
    feat = SimpleNamespace(locus_tag="cds1", translation="MAAAAAA", qualifiers={})

    # Monkeypatch away every external surface so the ONLY thing under test is the write path.
    monkeypatch.setattr(parsers, "extract_cds_features", lambda _pkg: [feat])
    monkeypatch.setattr(bo, "run_batches_online",
                        lambda batches, **kw: [OnlineResult(ok=True, rid="RID1", hits=[poisoned])])
    monkeypatch.setattr(bo, "_find_crosswalk", lambda args: None)
    monkeypatch.setattr(bo, "_derive_kcb_anchor", lambda args: ("", None))

    args = SimpleNamespace(
        package=str(tmp_path / "pkg"),
        bgc=None, region=None, crosswalk=None,
        database="nr", evalue="1e-5", batch_size=10,
        outdir=str(tmp_path),
    )

    rc = bo.blastp_online_command(args)
    assert rc == 0

    out_csv = tmp_path / "region_online_blastp.csv"
    assert out_csv.exists()

    rows = _read_rows(out_csv)
    header, data = rows[0], rows[1]
    # Column order / header must be unchanged by the fix.
    assert header == [
        "locus_tag", "node_region", "aa_length", "antismash_domains", "blastp_top_def",
        "blastp_accession", "blastp_organism", "pct_identity", "pct_positive", "query_coverage",
        "evalue", "bitscore", "agreement",
    ]
    assert len(data) == len(header) == 13

    def_cell = data[header.index("blastp_top_def")]
    org_cell = data[header.index("blastp_organism")]

    # The dangerous cells are neutralised: prefixed with a single quote so a spreadsheet
    # reads them as inert text, never a formula. The original content is preserved after "'".
    assert def_cell == "'=1+1", def_cell
    assert org_cell == "'@SUM(A1:A9)", org_cell

    # And crucially: no cell in the emitted table begins with a formula leader.
    for cell in data:
        assert not cell[:1] in ("=", "@", "\t", "\r"), cell

    # A benign accession (no leading formula char) is byte-identical — the guard is minimal.
    assert data[header.index("blastp_accession")] == "ABC12345.1"

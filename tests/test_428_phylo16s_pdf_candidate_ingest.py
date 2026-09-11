import sqlite3

import pytest

from tools import phylo_16s_build_db as build


def _db():
    con = sqlite3.connect(":memory:")
    con.executescript(build.SCHEMA)
    return con


def _record(accession, definition, binomial, designation, collections="[]"):
    return (
        accession, accession + ".1", "pdf_candidate", definition, binomial,
        binomial.split()[0], designation, collections, None, None, None, None,
        "fixture.tsv", 0,
    )


def test_pdf_collection_group_unions_surfaced_by_queries():
    con = _db()
    records = [
        _record("AA000001", "Example bacterium DSM 123", "Example bacterium", "DSM 123", '["DSM123"]'),
        _record("AA000002", "Example bacterium DSM 123", "Example bacterium", "DSM 123", '["DSM123"]'),
    ]
    build.upsert(con, records, "pdf_candidate")
    con.executemany(
        "INSERT INTO strain_meta VALUES (?,?,?,?)",
        [
            ("REC:AA000001", "surfaced_by_as_strains", "AS-1,AS-2", "blast_pdf_harvest"),
            ("REC:AA000002", "surfaced_by_as_strains", "AS-2,AS-3", "blast_pdf_harvest"),
        ],
    )
    _, merged = build.resolve_strains(con)
    assert merged == 1
    assert con.execute(
        "SELECT value FROM strain_meta WHERE strain_uid LIKE 'GROUP:%' "
        "AND key='surfaced_by_as_strains'"
    ).fetchone() == ("AS-1,AS-2,AS-3",)


def test_pdf_designation_without_collection_id_does_not_merge():
    con = _db()
    build.upsert(
        con,
        [
            _record("AA000001", "Examplebacterium strain Examplebacterium", "Examplebacterium strain", "Examplebacterium"),
            _record("AA000002", "Examplebacterium strain Examplebacterium", "Examplebacterium strain", "Examplebacterium"),
        ],
        "pdf_candidate",
    )
    strains, merged = build.resolve_strains(con)
    assert (strains, merged) == (2, 0)


@pytest.mark.parametrize("bad", ["not-a-number", "nan", "inf", "-1", "101"])
def test_pdf_ingest_rejects_malformed_percent_identity(tmp_path, monkeypatch, bad):
    path = tmp_path / "hits.tsv"
    path.write_text(
        "strain\taccession\tpct_identity\tsubject\tsubject_len\n"
        f"AS-1\tAA000001.1\t{bad}\tExample bacterium\t1400\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "PDFHITS", str(path))
    with pytest.raises(ValueError, match="invalid percent identity"):
        build.ingest_pdf_candidates(_db())


def test_pdf_ingest_preserves_explicitly_missing_percent_identity(tmp_path, monkeypatch):
    path = tmp_path / "hits.tsv"
    path.write_text(
        "strain\taccession\tpct_identity\tsubject\tsubject_len\n"
        "AS-1\tAA000001.1\t\tExample bacterium\t1400\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "PDFHITS", str(path))
    con = _db()
    assert build.ingest_pdf_candidates(con) == (1, 1)

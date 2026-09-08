"""HMM (PFAM/TIGRFAM) first-class table — reporting-only, additive to the structured tables."""
from mamey.antismash_tables import (
    TABLE_COLUMNS,
    HMM_COLUMNS,
    build_hmm_table,
    build_structured_tables,
)


def test_hmm_registered_in_table_columns():
    assert "hmm" in TABLE_COLUMNS
    assert TABLE_COLUMNS["hmm"] == HMM_COLUMNS
    for required in ("bgc_id", "hmm_database", "accession", "domain_name", "claim_safety"):
        assert required in HMM_COLUMNS


def test_build_hmm_table_empty_is_safe(tmp_path):
    # no zip / no bgcs must not raise, returns an empty list
    fake = tmp_path / "nope.zip"
    fake.write_bytes(b"")
    assert build_hmm_table(fake, []) == []


def test_structured_tables_exposes_hmm_key(tmp_path):
    import zipfile
    empty = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty, "w"):
        pass  # a valid but empty antiSMASH zip
    out = build_structured_tables(empty, {}, [])
    assert "hmm" in out
    assert "hmm" in out["counts"]
    assert out["hmm_status"] in {"PASS", "NULL_NO_PFAM_TIGRFAM_HITS"}
    assert isinstance(out["hmm"], list)

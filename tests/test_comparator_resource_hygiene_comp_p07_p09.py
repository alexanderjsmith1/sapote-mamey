"""COMP-P07 / COMP-P09 (v9.7.329): resource hygiene in the comparator ingest paths.

COMP-P07: ingest_comparator_inputs extracted untrusted comparator ZIPs into
`out_dir/_extracted_comparators` and never removed them, so extracted GBKs persisted in the sealed
package tree. The extracted tree must be gone once the tables are written.

COMP-P09: gcf_context opened a sqlite connection and only reached c.close() on the happy path, so any
query that raised mid-way (malformed/partial BiG-SCAPE db) leaked the handle. It must now close via a
contextlib.closing context manager even on the error path.
"""
import os
import sys
import zipfile
import sqlite3
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_comp_p07_extracted_comparators_dir_is_cleaned(tmp_path):
    from mamey.comparators.antismash_ingest import ingest_comparator_inputs
    zp = tmp_path / "comp.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("x.gbk", "LOCUS       test 100 bp DNA linear\n//\n")
    out = tmp_path / "out"
    res = ingest_comparator_inputs([zp], out)
    assert not (out / "_extracted_comparators").exists()      # extracted tree removed
    assert Path(res["comparator_gene_table"]).exists()        # outputs still written


def test_comp_p09_gcf_context_closes_connection_on_query_error(tmp_path, monkeypatch):
    import tools.bigscape_ingest_to_mamey as B
    db = tmp_path / "empty.db"
    sqlite3.connect(str(db)).close()   # valid file, but no 'run' table -> first query raises

    closed = {"n": 0}

    class TrackConn(sqlite3.Connection):
        def close(self):
            closed["n"] += 1
            super().close()

    real_connect = sqlite3.connect
    monkeypatch.setattr(B.sqlite3, "connect",
                        lambda *a, **k: real_connect(str(db), factory=TrackConn))
    with pytest.raises(sqlite3.OperationalError):
        B.gcf_context(str(db), 0.3, {})
    assert closed["n"] == 1            # connection closed despite the mid-query error

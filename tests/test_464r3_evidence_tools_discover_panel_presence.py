"""discover labels the BLASTp flag as panel-folder presence, never as an ingested result."""
from mamey import discover
from tests.test_discover import _mk_pkg


def test_worklist_message_and_table_do_not_claim_ingestion(tmp_path):
    _mk_pkg(tmp_path, "SYNTHETIC-DISCOVER-B", "1.9.111", worklist=True)
    rep = discover.run(tmp_path, max_depth=6)
    msg = next(a for a in rep["next_actions"] if "ingest-blastp" in a)
    assert "ingested panel" not in msg
    assert "folder presence only" in msg
    assert "BLASTp panel files" in discover._render(rep)

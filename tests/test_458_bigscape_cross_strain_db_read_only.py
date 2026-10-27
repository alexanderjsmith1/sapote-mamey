"""bigscape_cross_strain --db refuses a missing database and never creates one.

Before: sqlite3.connect() on a mistyped path created an empty database file, then failed.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bigscape_cross_strain_458", ROOT / "tools" / "bigscape_cross_strain.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_missing_db_is_refused_and_not_created(tmp_path, capsys):
    db = tmp_path / "typo.db"
    rc = m.main(["--db", str(db), "--out", str(tmp_path / "out.tsv"), "--run-id", "1"])
    assert rc == 2
    assert not db.exists()
    assert "CROSS_STRAIN_REFUSED" in capsys.readouterr().err

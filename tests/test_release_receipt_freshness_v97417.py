"""Guards for mamey.release_receipt_freshness.

Built from a real event: the v9.7.416 unsealed candidate shipped a validation log written
at 17:18:58 alongside source packaged at 17:24:04, so its recorded 7 failures described a
tree older than the one in the archive and none of them reproduced. A stale red receipt is
indistinguishable from a true one, which makes the archive neither sealable nor clearable
without re-running the full suite.

Every guard builds its own fixture, so none of them can quietly stop testing if the real
candidate is absent.
"""

import zipfile
from pathlib import Path

import pytest

from mamey import release_receipt_freshness as rrf


def _zip(path, entries):
    """entries: {name: (YYYY, M, D, H, M, S)}"""
    with zipfile.ZipFile(path, "w") as zf:
        for name, when in entries.items():
            zf.writestr(zipfile.ZipInfo(name, date_time=when), "x")
    return path


def test_archive_with_a_receipt_older_than_its_source_is_stale(tmp_path):
    z = _zip(tmp_path / "c.zip", {
        "bundle/mamey/cli.py": (2026, 9, 8, 17, 24, 4),
        "validation/source_full_attempt02.log": (2026, 9, 8, 17, 18, 58),
    })
    r = rrf.audit_archive(z)
    assert r["state"] == rrf.STALE
    assert len(r["stale"]) == 1
    assert r["stale"][0]["receipt"] == "validation/source_full_attempt02.log"
    assert r["newest_source"]["path"] == "bundle/mamey/cli.py"


def test_archive_with_a_receipt_newer_than_its_source_is_current(tmp_path):
    z = _zip(tmp_path / "c.zip", {
        "bundle/mamey/cli.py": (2026, 9, 8, 17, 18, 58),
        "validation/full_suite.log": (2026, 9, 8, 17, 24, 4),
    })
    assert rrf.audit_archive(z)["state"] == rrf.CURRENT


def test_an_archive_with_no_receipts_is_reported_not_silently_passed(tmp_path):
    z = _zip(tmp_path / "c.zip", {"bundle/mamey/cli.py": (2026, 9, 8, 17, 24, 4)})
    r = rrf.audit_archive(z)
    assert r["state"] == rrf.NO_RECEIPTS
    assert r["stale"] == []


def test_receipts_do_not_count_as_source(tmp_path):
    """Two receipts must be compared to code, never to each other."""
    z = _zip(tmp_path / "c.zip", {
        "bundle/mamey/cli.py": (2026, 9, 8, 10, 0, 0),
        "validation/a.log": (2026, 9, 8, 11, 0, 0),
        "validation/b.json": (2026, 9, 8, 12, 0, 0),
    })
    r = rrf.audit_archive(z)
    assert r["state"] == rrf.CURRENT
    assert r["newest_source"]["path"] == "bundle/mamey/cli.py"


def test_only_receipt_shaped_files_are_treated_as_receipts(tmp_path):
    """A .py helper living in validation/ is code, not evidence."""
    z = _zip(tmp_path / "c.zip", {
        "validation/make_report.py": (2026, 9, 8, 17, 24, 4),
        "validation/run.log": (2026, 9, 8, 17, 18, 58),
    })
    r = rrf.audit_archive(z)
    assert r["state"] == rrf.STALE
    assert r["newest_source"]["path"] == "validation/make_report.py"


def test_tree_audit_agrees_with_archive_audit(tmp_path):
    root = tmp_path / "tree"
    (root / "validation").mkdir(parents=True)
    (root / "mamey").mkdir()
    src = root / "mamey" / "cli.py"
    src.write_text("x", encoding="utf-8")
    rec = root / "validation" / "run.log"
    rec.write_text("x", encoding="utf-8")
    import os
    os.utime(rec, (1_000_000, 1_000_000))
    os.utime(src, (2_000_000, 2_000_000))
    assert rrf.audit_tree(root)["state"] == rrf.STALE
    os.utime(rec, (3_000_000, 3_000_000))
    assert rrf.audit_tree(root)["state"] == rrf.CURRENT


def test_a_missing_tree_raises_rather_than_reporting_clean(tmp_path):
    with pytest.raises(NotADirectoryError):
        rrf.audit_tree(tmp_path / "nope")


def test_module_emits_nothing_to_the_terminal():
    """print_calls has 3 counts of headroom under the signed waiver; this spends none."""
    import ast
    src = (Path(rrf.__file__)).read_text(encoding="utf-8")
    calls = [n for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call) and getattr(n.func, "id", None) in {"print", "emit"}]
    assert calls == []
